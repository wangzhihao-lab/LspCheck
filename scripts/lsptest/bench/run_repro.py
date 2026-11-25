"""Ground-truth runner of the benchmark: for the pre-fix and the post-fix build of a case,
run the case's reproduction 3 times each (fresh sessions every time, one server at a time)
and decide the case's probe on every run.

Case verdict (in this order):
- invalid             the case does not validate, a build is missing, or any run is invalid
                      (the reason of the first one);
- reproduced          pre-fix present in 3/3 runs and post-fix absent in 3/3 runs;
- not-reproduced-pre  pre-fix present in 0/3 runs;
- still-present-post  pre-fix 3/3 and post-fix 3/3 present;
- flaky               anything else (1 or 2 of 3 on either build).
Every invocation appends one line per case to data/lsp_bench/repro_results.jsonl (with a
hash of case.json and the project files, so a line is tied to one case revision) and
rewrites data/lsp_bench/repro_results.md from the whole file. Protocol logs of every session
stay under temp/lsp_bench/runs/<case>/<stamp>/.

`--smoke` only checks the harness on both builds (a fresh session on project/ with the
documents the ops open, settled; no probe is decided and nothing is recorded), so that a
build or settling problem is found before any verdict is looked at.

Run line: python3 scripts/lsptest/bench/run_repro.py <case dir> [<case dir> ...] | --all [--runs 3] [--smoke]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
for _p in (PKG, os.path.join(os.path.dirname(PKG), "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bench.case_format import Case, CaseError, list_cases, load_case, project_files, validate_case  # noqa: E402
from bench.collect import RunEnv, collect, session  # noqa: E402
from model import Op  # noqa: E402
from bench.probes import decide  # noqa: E402
from bench.filelock import locked  # noqa: E402

REPO = os.path.abspath(os.path.join(PKG, "..", ".."))
RESULTS_JSONL = os.path.join(REPO, "data", "lsp_bench", "repro_results.jsonl")
RESULTS_MD = os.path.join(REPO, "data", "lsp_bench", "repro_results.md")
RUNS_DIR = os.path.join(REPO, "temp", "lsp_bench", "runs")
PHASES = ("pre", "post")
EVIDENCE_CHARS = 1500

logger = logging.getLogger(__name__)


def case_sha(case: Case) -> str:
    """Hash of what a run depends on: case.json without the bookkeeping fields (meta.effort_minutes,
    attempts) and every project file."""
    raw = {k: v for k, v in case.raw.items() if k != "attempts"}
    raw["meta"] = {k: v for k, v in (raw.get("meta") or {}).items() if k != "effort_minutes"}
    h = hashlib.sha256(json.dumps(raw, sort_keys=True).encode("utf-8") + b"\0")
    for rel in project_files(case.project_dir):
        h.update(rel.encode("utf-8") + b"\0")
        with open(os.path.join(case.project_dir, rel), "rb") as f:
            h.update(f.read() + b"\0")
    return h.hexdigest()[:16]


def _brief(x: Any) -> Any:
    text = json.dumps(x, sort_keys=True, default=str, ensure_ascii=False)
    return x if len(text) <= EVIDENCE_CHARS else text[:EVIDENCE_CHARS] + "..."


def case_verdict(runs: Dict[str, List[Dict[str, Any]]], n: int) -> Dict[str, str]:
    """Verdict and reason from per-phase run verdicts (see the module docstring)."""
    for phase in PHASES:
        for r in runs.get(phase, []):
            if r["verdict"] == "invalid":
                return {"verdict": "invalid", "reason": f"{phase} run {r['run']}: {r['reason']}"}
    pre = sum(r["verdict"] == "present" for r in runs.get("pre", []))
    post = sum(r["verdict"] == "present" for r in runs.get("post", []))
    if len(runs.get("pre", [])) < n or len(runs.get("post", [])) < n:
        return {"verdict": "invalid", "reason": "incomplete runs"}
    if pre == n and post == 0:
        return {"verdict": "reproduced", "reason": f"pre {pre}/{n} present, post {post}/{n} present"}
    if pre == 0:
        return {"verdict": "not-reproduced-pre", "reason": f"pre 0/{n} present: {runs['pre'][0]['reason']}"}
    if pre == n and post == n:
        return {"verdict": "still-present-post", "reason": f"post {post}/{n} present: {runs['post'][0]['reason']}"}
    return {"verdict": "flaky", "reason": f"pre {pre}/{n} present, post {post}/{n} present"}


def smoke_case(case_dir: str) -> List[Dict[str, Any]]:
    """Harness check per build: start, open the documents the ops open, settle (no probe)."""
    case = load_case(case_dir)
    opens = [Op("open", path=p) for p in sorted({o.path for o in case.repro.ops if o.kind == "open"})]
    out = []
    for phase in PHASES:
        work = os.path.join(RUNS_DIR, case.case_id, "smoke-" + time.strftime("%Y%m%d-%H%M%S"), phase)
        if not _installed(case, case.build(phase)):
            out.append({"phase": phase, "build": case.build(phase), "valid": False, "reason": "not installed"})
            continue
        s = session(RunEnv(case, case.build(phase), work), f"smoke-{phase}", case.project_dir, opens, "settled", [])
        out.append({"phase": phase, "build": case.build(phase), "valid": s["valid"], "reason": s["reason"],
                    "seconds": s.get("seconds"), "log": os.path.join(work, str(s.get("log", "")))})
    return out


def run_case(case_dir: str, n: int = 3) -> Dict[str, Any]:
    """All runs of one case; returns the results line (also appended to the JSONL file)."""
    t0, stamp = time.monotonic(), time.strftime("%Y%m%d-%H%M%S")
    line: Dict[str, Any] = {"case": os.path.basename(os.path.abspath(case_dir)), "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    try:
        case = load_case(case_dir)
        errs, notes = validate_case(case)
    except CaseError as exc:
        case, errs, notes = None, [str(exc)], []
    if case is None or errs:
        line.update(verdict="invalid", reason=f"case does not validate: {errs[:3]}", runs={})
        return _finish(line, t0)
    line.update(server=case.meta.get("server"), kind=case.meta.get("kind"), oracle_class=case.meta.get("oracle_class"),
                subtype=case.meta.get("subtype"), probe=case.repro.probe.get("type"), attempt=case.repro.attempt,
                timing=case.repro.timing, builds={p: case.build(p) for p in PHASES}, case_sha=case_sha(case),
                effort_minutes=case.meta.get("effort_minutes"), notes=notes)
    missing = [b for b in (case.build(p) for p in PHASES) if not _installed(case, b)]
    if missing:
        line.update(verdict="invalid", reason=f"build not installed: {missing}", runs={})
        return _finish(line, t0)
    runs: Dict[str, List[Dict[str, Any]]] = {}
    for phase in PHASES:
        runs[phase] = []
        for i in range(1, n + 1):
            work = os.path.join(RUNS_DIR, case.case_id, stamp, f"{phase}-{i}")
            r0 = time.monotonic()
            answers = collect(RunEnv(case, case.build(phase), work))
            res = decide(case.repro.probe, answers)
            runs[phase].append({"run": i, "build": case.build(phase), "verdict": res.verdict, "reason": res.reason,
                                "evidence": _brief(res.evidence), "seconds": round(time.monotonic() - r0, 1),
                                "sessions": {k: {x: v.get(x) for x in ("valid", "reason", "seconds", "log")}
                                             for k, v in answers.items()}, "work_dir": os.path.relpath(work, REPO)})
            logger.info("%s %s run %d (%s): %s - %s", case.case_id, phase, i, case.build(phase), res.verdict,
                        res.reason[:160])
    line["runs"] = runs
    line.update(case_verdict(runs, n))
    return _finish(line, t0)


def _installed(case: Case, version: str) -> bool:
    import servers
    try:
        servers.resolve(str(case.meta["kind"]), version)
    except (FileNotFoundError, ValueError):
        return False
    return True


def _finish(line: Dict[str, Any], t0: float) -> Dict[str, Any]:
    line["minutes"] = round((time.monotonic() - t0) / 60.0, 2)
    os.makedirs(os.path.dirname(RESULTS_JSONL), exist_ok=True)
    with locked(), open(RESULTS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
    return line


# ------------------------------------------------------------------ markdown report
def load_results(path: str = RESULTS_JSONL) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def _count(line: Dict[str, Any], phase: str) -> str:
    rs = (line.get("runs") or {}).get(phase) or []
    return f"{sum(r['verdict'] == 'present' for r in rs)}/{len(rs)}" if rs else "-"


def _cell(text: Any, limit: int = 140) -> str:
    s = " ".join(str(text if text is not None else "").split()).replace("|", "\\|")
    return s if len(s) <= limit else s[: limit - 3] + "..."


def render_markdown(lines: List[Dict[str, Any]]) -> str:
    latest: Dict[str, Dict[str, Any]] = {}
    for ln in lines:
        latest[ln["case"]] = ln
    counts: Dict[str, int] = {}
    for ln in latest.values():
        counts[ln["verdict"]] = counts.get(ln["verdict"], 0) + 1
    out = ["# Benchmark ground-truth runs", "",
           "Generated by `scripts/lsptest/bench/run_repro.py` from `repro_results.jsonl` (do not edit). A case is "
           "`reproduced` only when its probe reports the bug in 3/3 fresh runs on the pre-fix build and in 0/3 on the "
           "post-fix build. `present` counts are runs whose probe said the bug is present.", "",
           "Latest verdicts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f" ({len(latest)} cases).", "",
           "## Latest run per case", "",
           "| case | class | probe | attempt / timing | pre build | post build | pre present | post present | verdict "
           "| reason | effort min | run min |", "|---|---|---|---|---|---|---|---|---|---|---:|---:|"]
    for case_id, ln in sorted(latest.items()):
        b = ln.get("builds") or {}
        out.append(f"| {case_id} | {ln.get('oracle_class', '')} {ln.get('subtype', '')} | {ln.get('probe', '')} | "
                   f"{ln.get('attempt', '')} / {ln.get('timing', '')} | {b.get('pre', '')} | {b.get('post', '')} | "
                   f"{_count(ln, 'pre')} | {_count(ln, 'post')} | **{ln['verdict']}** | {_cell(ln.get('reason'))} | "
                   f"{ln.get('effort_minutes', '')} | {ln.get('minutes', '')} |")
    out += ["", "## All runs", "", "| started | case | attempt / timing | case sha | pre | post | verdict | reason |",
            "|---|---|---|---|---|---|---|---|"]
    for ln in lines:
        out.append(f"| {ln.get('started', '')} | {ln['case']} | {ln.get('attempt', '')} / {ln.get('timing', '')} | "
                   f"{ln.get('case_sha', '')} | {_count(ln, 'pre')} | {_count(ln, 'post')} | {ln['verdict']} | "
                   f"{_cell(ln.get('reason'), 200)} |")
    out += ["", "## Per-run reasons (latest run per case)", ""]
    for case_id, ln in sorted(latest.items()):
        out.append(f"### {case_id}")
        for phase in PHASES:
            for r in (ln.get("runs") or {}).get(phase) or []:
                out.append(f"- {phase} run {r['run']} ({r['build']}, {r['seconds']} s): {r['verdict']} - "
                           f"{_cell(r['reason'], 300)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_markdown() -> str:
    with locked():
        text = render_markdown(load_results())
        with open(RESULTS_MD, "w", encoding="utf-8") as f:
            f.write(text)
    return RESULTS_MD


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Run benchmark cases on their pre-fix and post-fix builds.")
    ap.add_argument("cases", nargs="*", help="case directories")
    ap.add_argument("--all", action="store_true", help="every case under data/lsp_bench/cases")
    ap.add_argument("--runs", type=int, default=3, help="fresh runs per build (default 3)")
    ap.add_argument("--smoke", action="store_true", help="harness check only (nothing decided or recorded)")
    ap.add_argument("--report-only", action="store_true", help="only regenerate repro_results.md")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    todo = list(args.cases) + (list_cases() if args.all else [])
    if args.smoke:
        for d in todo:
            for r in smoke_case(d):
                print(f"{os.path.basename(os.path.abspath(d))} {r['phase']} {r['build']}: "
                      f"{'ok' if r['valid'] else 'FAILED ' + str(r['reason'])[:200]} ({r.get('seconds')} s)")
        return 0
    if not args.report_only:
        if not todo:
            ap.error("give case directories or --all")
        for d in todo:
            line = run_case(d, args.runs)
            print(f"{line['case']}: {line['verdict']} ({line['reason'][:160]}) in {line['minutes']} min")
    print(f"report: {os.path.relpath(write_markdown(), REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
