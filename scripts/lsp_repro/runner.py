"""Run a reproduction case on its pinned pre-fix and post-fix server versions.

Run line:
  python3 scripts/lsp_repro/runner.py --case pyright_8946
  python3 scripts/lsp_repro/runner.py --all --repeat 3
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import oracle  # noqa: E402
import servers  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(REPO, "data", "lsp_repro")
LOG_DIR = os.path.join(OUT_DIR, "logs")
WS_ROOT = os.path.join(REPO, "temp", "lsp_servers", "workspaces")
CASES_DIR = os.path.join(HERE, "cases")

logger = logging.getLogger("runner")


def load_case(name: str):
    path = os.path.join(CASES_DIR, f"{name}.py")
    if not os.path.exists(path):
        raise FileNotFoundError(f"no case module: {path}")
    spec = importlib.util.spec_from_file_location(f"case_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def list_cases() -> List[str]:
    if not os.path.isdir(CASES_DIR):
        return []
    return sorted(
        f[:-3] for f in os.listdir(CASES_DIR) if f.endswith(".py") and not f.startswith("_")
    )


def case_variants(mod) -> List[str]:
    """Variant names a case offers. Convention: 'settled' waits for quiescence between
    edits; 'race*' fires the follow-up edit after a short (or zero) delay."""
    return list(getattr(mod, "VARIANTS", ["settled"]))


def build_variant(mod, variant: str):
    try:
        return mod.build(variant)
    except TypeError:
        return mod.build()


def run_case_version(
    mod, name: str, version: str, phase: str, repeat: int = 1, variants: Optional[List[str]] = None
) -> Dict[str, Any]:
    names = variants if variants is not None else case_variants(mod)
    scn = build_variant(mod, names[0])
    kind = getattr(mod, "SERVER", scn.server)
    entry: Dict[str, Any] = {
        "case": name,
        "issue": getattr(mod, "ISSUE", scn.issue),
        "title": getattr(mod, "TITLE", ""),
        "server": kind,
        "version": version,
        "phase": phase,
        "variants": {},
    }
    try:
        spec = servers.resolve(kind, version)
    except (FileNotFoundError, ValueError) as exc:
        entry["install_error"] = str(exc)
        logger.error("  cannot resolve %s %s: %s", kind, version, exc)
        return entry

    for vname in names:
        runs: List[Dict[str, Any]] = []
        for i in range(repeat):
            tag = f"{name}-{version}-{phase}-{vname}-r{i}"
            t0 = time.monotonic()
            res = oracle.path_independence(build_variant(mod, vname), spec, WS_ROOT, LOG_DIR, tag)
            present: Optional[bool] = None
            why = "no bug_present() in case module"
            if hasattr(mod, "bug_present") and res.get("replay", {}).get("ok"):
                try:
                    present, why = mod.bug_present(res["replay"], res)
                except (KeyError, TypeError, ValueError) as exc:
                    present, why = None, f"predicate error: {type(exc).__name__}: {exc}"
            res["bug_present"] = present
            res["bug_reason"] = why
            res["variant"] = vname
            res["wall_seconds"] = round(time.monotonic() - t0, 2)
            runs.append(res)
        k = sum(1 for r in runs if r.get("bug_present") is True)
        of = sum(1 for r in runs if r.get("oracle_flag") is True)
        entry["variants"][vname] = {
            "runs": runs,
            "k": k,
            "n": len(runs),
            "oracle_k": of,
            "seconds": round(sum(r.get("wall_seconds", 0) for r in runs), 1),
        }
        logger.info(
            "  %s %-9s repro %d/%d  oracle %d/%d  (%.0fs)  %s",
            version, vname, k, len(runs), of, len(runs),
            entry["variants"][vname]["seconds"], (runs[-1].get("bug_reason") or "")[:110],
        )
    return entry


def summarize(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Verdict = best variant. 'yes' only if some variant reproduces in every run."""
    vs = entry.get("variants", {})
    if not vs:
        return {"verdict": "not-run", "note": entry.get("install_error", "")}
    best = max(vs.items(), key=lambda kv: (kv[1]["k"] / max(1, kv[1]["n"]), kv[1]["k"]))
    bname, b = best
    if b["k"] == b["n"] and b["n"] > 0:
        verdict = "yes"
    elif b["k"] > 0:
        verdict = "flaky"
    else:
        verdict = "no"
    allruns = [r for v in vs.values() for r in v["runs"]]
    orc_best = max(vs.values(), key=lambda v: v["oracle_k"])
    return {
        "verdict": verdict,
        "best_variant": bname,
        "k": b["k"],
        "n": b["n"],
        "per_variant": {k: f"{v['k']}/{v['n']}" for k, v in vs.items()},
        "oracle_per_variant": {k: f"{v['oracle_k']}/{v['n']}" for k, v in vs.items()},
        "oracle_flag_any": orc_best["oracle_k"] > 0,
        "oracle_flag_all": orc_best["oracle_k"] == orc_best["n"] and orc_best["n"] > 0,
        "unstable": any(r.get("replay", {}).get("snapshot_unstable") for r in allruns),
        "seconds": round(sum(v["seconds"] for v in vs.values()), 1),
        "errors": sorted({r.get("error", "") for r in allruns if r.get("error")}),
    }


def _merge_record(path: str, fresh: Dict[str, Any]) -> Dict[str, Any]:
    """Merge newly run variants into an existing result file and re-summarize."""
    if not os.path.exists(path):
        return fresh
    try:
        with open(path, "r", encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return fresh
    merged = dict(old)
    merged.update({k: v for k, v in fresh.items() if k != "phases"})
    phases = dict(old.get("phases") or {})
    for phase, node in (fresh.get("phases") or {}).items():
        entry = dict(node.get("entry") or {})
        old_entry = ((phases.get(phase) or {}).get("entry")) or {}
        variants = dict(old_entry.get("variants") or {})
        variants.update(entry.get("variants") or {})
        entry["variants"] = variants
        phases[phase] = {"entry": entry, "summary": summarize(entry)}
    merged["phases"] = phases
    return merged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--phase", choices=["pre", "post", "both"], default="both")
    ap.add_argument("--version", default=None, help="override version (single run)")
    ap.add_argument("--variant", action="append", default=[], help="restrict to these variants")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    for d in (OUT_DIR, LOG_DIR, WS_ROOT):
        os.makedirs(d, exist_ok=True)

    names = list_cases() if args.all else args.case
    if not names:
        print("cases:", ", ".join(list_cases()))
        return 1

    all_out: List[Dict[str, Any]] = []
    for name in names:
        try:
            mod = load_case(name)
        except (FileNotFoundError, ImportError) as exc:
            logger.error("skip %s: %s", name, exc)
            continue
        logger.info("=== case %s (%s)", name, getattr(mod, "ISSUE", "?"))
        record: Dict[str, Any] = {
            "case": name,
            "issue": getattr(mod, "ISSUE", ""),
            "title": getattr(mod, "TITLE", ""),
            "server": getattr(mod, "SERVER", "?"),
            "pre": getattr(mod, "PRE", ""),
            "post": getattr(mod, "POST", ""),
            "symptom": getattr(mod, "SYMPTOM", ""),
            "phases": {},
        }
        if args.version:
            phases = [(args.phase if args.phase != "both" else "pre", args.version)]
        else:
            phases = []
            if args.phase in ("pre", "both"):
                phases.append(("pre", record["pre"]))
            if args.phase in ("post", "both"):
                phases.append(("post", record["post"]))
        for phase, version in phases:
            if not version:
                continue
            entry = run_case_version(
                mod, name, version, phase, repeat=args.repeat,
                variants=args.variant or None,
            )
            record["phases"][phase] = {"entry": entry, "summary": summarize(entry)}
        out_path = os.path.join(OUT_DIR, f"result-{name}.json")
        if args.variant:
            # A restricted run must not throw away the variants it did not run.
            record = _merge_record(out_path, record)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=1, default=str)
        logger.info("wrote %s", out_path)
        all_out.append(record)

    print()
    print(f"{'case':24} {'pre':9} {'repro-pre':12} {'orc-pre':8} {'post':9} {'fixed-post':11} {'orc-post':8} best-variant")
    for r in all_out:
        pre = r["phases"].get("pre", {}).get("summary", {})
        post = r["phases"].get("post", {}).get("summary", {})
        fixed = {"no": "yes", "yes": "no", "flaky": "partial"}.get(
            post.get("verdict", ""), post.get("verdict", "-")
        )
        pk = f"{pre.get('verdict','-')} {pre.get('k','')}/{pre.get('n','')}".strip()
        print(
            f"{r['case']:24} {r['pre']:9} {pk:12} "
            f"{str(pre.get('oracle_flag_any','-')):8} {r['post']:9} {fixed:11} "
            f"{str(post.get('oracle_flag_any','-')):8} {pre.get('best_variant','-')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
