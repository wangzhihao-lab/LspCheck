"""Engine smoke (design 9.1): for each first-batch server, one small real project; a
baseline snapshot and a second, fresh control snapshot on the same seeded targets;
per method the share of keys where baseline == control (stability), timings and
settle status. Writes data/lsptest/engine_smoke.json and data/lsptest/engine_smoke.md.

Fixtures are shallow fetches of pinned commits into temp/lsptest_fixtures/<owner>__<repo>
(commits from data/lsptest/corpus.json; sharkdp/fd is not in the corpus and is pinned
below), plus `cargo fetch` and `cargo check` (Rust: sessions clone the warm target/)
and `go mod download` (Go). TypeScript fixtures get no node_modules; the
unresolved-module diagnostics this causes are counted as noise.

Run line: python3 scripts/lsptest/engine_smoke.py [--servers ts6,ts7] [--seed 1] [--files 3] [--positions 12]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from driver import REPO, Driver, DriverConfig, diff_keys, pid_alive, stability  # noqa: E402
from framing import LspError  # noqa: E402
from model import Snapshot  # noqa: E402
from queries import key_sort  # noqa: E402
from servers_extra import CARGO_HOME, GOPATH_DIR, RUSTUP_BIN  # noqa: E402
from targets import FileTargets, TargetConfig, choose_targets, targets_to_json  # noqa: E402

logger = logging.getLogger("engine_smoke")
FIXTURES = os.path.join(REPO, "temp", "lsptest_fixtures")
CORPUS = os.path.join(REPO, "data", "lsptest", "corpus.json")
OUT_JSON = os.path.join(REPO, "data", "lsptest", "engine_smoke.json")
OUT_MD = os.path.join(REPO, "data", "lsptest", "engine_smoke.md")
EXTRA_PINS = {"sharkdp/fd": "9e8927e8f3ee7bb699df55cb0b440f848dce6857"}  # master HEAD on 2026-09-23
# Diagnostics caused by the missing dependency install rather than by the code.
NOISE_CODES = {
    "typescript": {"2307", "2792", "7016", "2875", "2688"},  # cannot find module / type definitions
    "python": {"reportMissingImports", "reportMissingModuleSource"},
}


@dataclass(frozen=True)
class SmokeCase:
    kind: str
    version: str
    repo: str
    language: str
    deps: str = ""  # cargo | go | "" (none)


CASES: Tuple[SmokeCase, ...] = (
    SmokeCase("pyright", "1.1.414", "pallets/flask", "python"),
    SmokeCase("ts6", "6.0.3", "pmndrs/zustand", "typescript"),
    SmokeCase("ts7", "7.0.2", "pmndrs/zustand", "typescript"),
    SmokeCase("rust-analyzer", "2026-09-21", "sharkdp/fd", "rust", "cargo"),
    SmokeCase("gopls", "v0.23.0", "spf13/cobra", "go", "go"),
)


# ------------------------------------------------------------ fixtures
def pinned_commit(repo: str) -> str:
    if repo in EXTRA_PINS:
        return EXTRA_PINS[repo]
    with open(CORPUS, "r", encoding="utf-8") as f:
        corpus = json.load(f)["corpus"]
    for entries in corpus.values():
        for e in entries:
            if e["repo"] == repo:
                return e["commit"]
    raise KeyError(f"{repo} not pinned in {CORPUS}")


def _run(cmd: Sequence[str], cwd: str, env: Optional[Dict[str, str]] = None, timeout: float = 900) -> str:
    full = dict(os.environ, **(env or {}))
    res = subprocess.run(list(cmd), cwd=cwd, env=full, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} failed: {res.stderr.strip()[-300:]}")
    return res.stdout.strip()


def prepare_fixture(case: SmokeCase) -> Tuple[str, Dict[str, Any]]:
    """Clone the pinned commit (once) and fetch dependencies (once, recorded in a marker
    file next to the fixture, not inside it)."""
    commit = pinned_commit(case.repo)
    root = os.path.join(FIXTURES, case.repo.replace("/", "__"))
    marker = root + ".prepared.json"
    t0 = time.monotonic()
    if not os.path.isdir(os.path.join(root, ".git")):
        os.makedirs(root, exist_ok=True)
        _run(["git", "init", "-q"], root)
        _run(["git", "remote", "add", "origin", f"https://github.com/{case.repo}.git"], root)
        _run(["git", "fetch", "-q", "--depth", "1", "origin", commit], root)
        _run(["git", "checkout", "-q", "FETCH_HEAD"], root)
    head = _run(["git", "rev-parse", "HEAD"], root)
    if head != commit:
        raise RuntimeError(f"{root} is at {head}, expected {commit}")
    if case.deps and not os.path.exists(marker):
        if case.deps == "cargo":
            env = {"PATH": os.pathsep.join([RUSTUP_BIN, os.path.join(CARGO_HOME, "bin"), os.environ.get("PATH", "")]),
                   "CARGO_HOME": CARGO_HOME}
            _run(["cargo", "fetch"], root, env)
            _run(["cargo", "check", "--workspace", "--all-targets", "--quiet"], root, env, timeout=1800)
        elif case.deps == "go":
            env = {"GOPATH": GOPATH_DIR, "GOMODCACHE": os.path.join(GOPATH_DIR, "pkg", "mod"), "GOFLAGS": "-modcacherw",
                   "GOTOOLCHAIN": "local"}
            _run(["go", "mod", "download"], root, env)
        with open(marker, "w", encoding="utf-8") as f:
            json.dump({"repo": case.repo, "commit": commit, "deps": case.deps}, f)
    return root, {"repo": case.repo, "commit": commit, "prepare_s": round(time.monotonic() - t0, 2)}


# ------------------------------------------------------------ sessions and comparison
def run_session(case: SmokeCase, root: str, targets: Sequence[FileTargets], label: str,
                args: argparse.Namespace) -> Tuple[Optional[Snapshot], Dict[str, Any]]:
    cfg = DriverConfig(case.kind, case.version, root, label=label, settle_timeout_s=args.settle_timeout,
                       request_timeout_s=args.request_timeout)
    drv, info, snap = Driver(cfg), {"label": label}, None
    t0 = time.monotonic()
    try:
        drv.start()
        snap = drv.snapshot(label, targets)
        stats = drv.last_stats.to_json() if drv.last_stats else {}
        info.update(init_s=round(drv.init_seconds, 2), settle=drv.last_settle.to_json() if drv.last_settle else {},
                    suite_s=stats.get("seconds"), errors=stats.get("errors"), unsupported=stats.get("unsupported"),
                    mean_ms={m: round(1000 * s / max(1, stats["method_counts"].get(m, 1)), 1)
                             for m, s in stats.get("method_seconds", {}).items()},
                    keys=len(snap.results), settled=snap.settled, session=drv.session_id)
    except (OSError, RuntimeError, ValueError, LspError, subprocess.SubprocessError) as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"[:300]
        logger.error("%s %s failed: %s", case.kind, label, info["error"])
    finally:
        info["close"] = drv.close()
        info["total_s"] = round(time.monotonic() - t0, 2)
    return snap, info


def _short(value: Any, limit: int = 300) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s if len(s) <= limit else s[:limit] + "..."


def _informative(method: str, norm: Any) -> bool:
    """A non-empty, non-error result (so that equality is not trivially met)."""
    if not norm or (isinstance(norm, list) and norm[:1] in (["error"], ["unnormalizable"])):
        return False
    return bool(norm[0]) if method == "hover" else True


def compare(base: Snapshot, ctrl: Snapshot, per_method: int = 3) -> Dict[str, Any]:
    """Stability per method (plus the share of informative baseline results), overall,
    and a few differing keys per method."""
    stab = stability(base, ctrl)
    for k, r in base.results.items():
        row = stab[k.method]
        row["informative"] = row.get("informative", 0) + int(_informative(k.method, r.norm))
    keys = sum(r["keys"] for r in stab.values())
    equal = sum(r["equal"] for r in stab.values())
    examples: Dict[str, List[Dict[str, Any]]] = {}
    for k in diff_keys(base, ctrl):
        rows = examples.setdefault(k.method, [])
        if len(rows) < per_method:
            b, c = base.results.get(k), ctrl.results.get(k)
            rows.append({"key": list(key_sort(k)), "baseline": _short(b.norm if b else "<missing>"),
                         "control": _short(c.norm if c else "<missing>")})
    return {"per_method": stab, "overall": round(equal / keys, 4) if keys else 1.0, "examples": examples}


def diagnostic_noise(snap: Snapshot, language: str) -> Dict[str, Any]:
    """Diagnostics in the snapshot, by code, and how many are missing-dependency noise."""
    by_code: Dict[str, int] = {}
    for k, r in snap.results.items():
        if k.method == "diagnostics" and isinstance(r.norm, list) and r.error is None:
            for d in r.norm:
                by_code[d[5] or "<none>"] = by_code.get(d[5] or "<none>", 0) + 1
    noise = sum(n for code, n in by_code.items() if code in NOISE_CODES.get(language, set()))
    return {"total": sum(by_code.values()), "unresolved_module": noise, "by_code": dict(sorted(by_code.items()))}


def smoke_case(case: SmokeCase, args: argparse.Namespace) -> Dict[str, Any]:
    out: Dict[str, Any] = {"server": case.kind, "version": case.version, "language": case.language}
    try:
        root, fixture = prepare_fixture(case)
    except (OSError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        return dict(out, error=f"fixture: {type(exc).__name__}: {exc}"[:300])
    targets = choose_targets(root, case.language, TargetConfig(seed=args.seed, max_files=args.files,
                                                                max_positions_per_file=args.positions))
    out.update(fixture=fixture, targets=targets_to_json(targets))
    logger.info("%s: %s@%s, %d files", case.kind, case.repo, fixture["commit"][:12], len(targets))
    base, out["baseline"] = run_session(case, root, targets, "baseline", args)
    ctrl, out["control"] = run_session(case, root, targets, "control", args)
    if base is not None and ctrl is not None:
        out["stability"] = compare(base, ctrl)
        out["noise"] = diagnostic_noise(base, case.language)
    return out


# ------------------------------------------------------------ report
def leftover_processes(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    pids = sorted({p for r in results for s in ("baseline", "control")
                   for p in (r.get(s) or {}).get("close", {}).get("server_pids", [])})
    try:
        pgrep = subprocess.run(["pgrep", "-fl", "lsp_servers|proc-macro-srv"], capture_output=True, text=True,
                               timeout=10).stdout.strip().splitlines()
    except (OSError, subprocess.SubprocessError):
        pgrep = []
    return {"session_pids": len(pids), "alive": [p for p in pids if pid_alive(p)], "pgrep": pgrep}


def write_markdown(report: Dict[str, Any], path: str) -> None:
    lines = [f"# Engine smoke ({report['date']})", "",
             f"Seed {report['seed']}, up to {report['files']} files x {report['positions']} positions per project. "
             "Stability = share of keys whose normalized result is equal in two fresh sessions (baseline, control).", "",
             "| server | project@commit | settled B/C | settle s B/C | keys B/C | stability | total s B/C |",
             "|---|---|---|---|---|---|---|"]
    for r in report["servers"]:
        b, c = r.get("baseline", {}), r.get("control", {})
        st = r.get("stability", {})
        fx = r.get("fixture", {})
        lines.append(f"| {r['server']} {r['version']} | {fx.get('repo', '?')}@{fx.get('commit', '?')[:12]} | "
                     f"{b.get('settled')}/{c.get('settled')} | {b.get('settle', {}).get('seconds')}/"
                     f"{c.get('settle', {}).get('seconds')} | {b.get('keys')}/{c.get('keys')} | "
                     f"{st.get('overall')} | {b.get('total_s')}/{c.get('total_s')} |")
    lines += ["", "## Stability per method: equal/keys (informative baseline results)", ""]
    methods = sorted({m for r in report["servers"] for m in r.get("stability", {}).get("per_method", {})})
    lines += ["| server | " + " | ".join(methods) + " |", "|---|" + "---|" * len(methods)]
    for r in report["servers"]:
        pm = r.get("stability", {}).get("per_method", {})
        cells = [f"{pm[m]['equal']}/{pm[m]['keys']} ({pm[m].get('informative', 0)})" if m in pm else "-" for m in methods]
        lines.append(f"| {r['server']} | " + " | ".join(cells) + " |")
    lines += ["", "## Notes", ""]
    for r in report["servers"]:
        noise = r.get("noise", {})
        err = r.get("error") or r.get("baseline", {}).get("error") or r.get("control", {}).get("error")
        lines.append(f"- {r['server']}: diagnostics in baseline {noise.get('total')}, of which unresolved-module "
                     f"noise {noise.get('unresolved_module')}; settle mode {r.get('baseline', {}).get('settle', {}).get('mode')}"
                     + (f"; error: {err}" if err else ""))
        for method, rows in r.get("stability", {}).get("examples", {}).items():
            lines.append(f"  - unstable {method}: {len(rows)} example(s), first key {rows[0]['key']}")
    left = report["leftover"]
    lines.append(f"- server processes after the run: {len(left['alive'])} of {left['session_pids']} still alive; "
                 f"pgrep matches: {len(left['pgrep'])}")
    notes = report.get("interpretation", [])
    lines += (["", "## Interpretation", ""] + [f"- {n}" for n in notes]) if notes else []
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Engine smoke: baseline vs fresh control per server (design 9.1).")
    ap.add_argument("--servers", default=",".join(c.kind for c in CASES))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--files", type=int, default=3)
    ap.add_argument("--positions", type=int, default=12)
    ap.add_argument("--settle-timeout", type=float, default=300.0)
    ap.add_argument("--request-timeout", type=float, default=60.0)
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--md", default=OUT_MD)
    ap.add_argument("--note", action="append", default=[], help="interpretation note for the markdown (repeatable)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    wanted = set(args.servers.split(","))
    results = [smoke_case(c, args) for c in CASES if c.kind in wanted]
    report = {"date": time.strftime("%Y-%m-%d %H:%M"), "seed": args.seed, "files": args.files,
              "positions": args.positions, "servers": results, "leftover": leftover_processes(results),
              "interpretation": list(args.note)}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    write_markdown(report, args.md)
    for r in results:
        b, c = r.get("baseline", {}), r.get("control", {})
        print(f"{r['server']:14} settled={b.get('settled')}/{c.get('settled')} "
              f"settle_s={b.get('settle', {}).get('seconds')}/{c.get('settle', {}).get('seconds')} "
              f"keys={b.get('keys')}/{c.get('keys')} stability={r.get('stability', {}).get('overall')} "
              f"{r.get('error', '')}")
    print(f"leftover server processes alive: {report['leftover']['alive']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
