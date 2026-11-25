"""Aggregate pilot run records (pilot_r2r3r5.py outputs), a hand-written classification file
and a notes file into data/lsptest/pilot/r2_r3_r5.json and r2_r3_r5.md.

Run line: python3 scripts/lsptest/pilots/aggregate_r2r3r5.py --runs 'data/lsptest/pilot/r2_r3_r5_inputs/runs/run_*.json' --known 'data/lsptest/pilot/r2_r3_r5_inputs/known/jdtls_2111_*.json' --classes data/lsptest/pilot/r2_r3_r5_inputs/classes.json --extra data/lsptest/pilot/r2_r3_r5_inputs/extra.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import time
from typing import Any, Dict, List

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.join(REPO, "data", "lsptest", "pilot", "r2_r3_r5")


def short(x: Any, n: int = 160) -> str:
    s = json.dumps(x, ensure_ascii=False)
    s = s if len(s) <= n else s[:n] + "..."
    return s.replace("|", "\\|")


def ident(c: Dict[str, Any]) -> str:
    k = c["key"]
    return f"{c['signature']}|{k['path']}|{k['line']}|{k['character']}|{k['extra']}"


def load(paths: List[str], classes: Dict[str, Dict[str, str]]) -> Dict[str, List[Dict[str, Any]]]:
    runs, cands = [], []
    for path in paths:
        rec = json.load(open(path))
        res, reps = rec["result"], rec.get("replays", [])
        runs.append({"oracle": rec["oracle"], "server": f"{rec['server']} {rec['version']}", "project": rec["project"],
                     "cases": res["cases"], "invalid_cases": res["invalid_cases"], "sessions": res["sessions"],
                     "unsettled": res["unsettled"], "seconds_run": res["seconds"],
                     "seconds_with_replays": rec["total_seconds"], "candidates": len(res["candidates"]),
                     "reproduced_3of3": sum(1 for r in reps if r["reproduced"] == "3/3"),
                     "compared": res["compared"], "unstable": res["unstable"], "notes": res["notes"],
                     "targets": rec["targets"], "max_cases": rec["max_cases"], "source": os.path.basename(path)})
        for c, r in zip(res["candidates"], reps):
            det = json.loads(c["detail"])
            cl = classes.get(ident(c)) or classes.get(f"{c['server']}|{c['signature']}") or \
                classes.get(c["signature"]) or {"class": "unclassified", "evidence": ""}
            cands.append({"oracle": c["oracle"], "server": c["server"], "project": c["project"],
                          "signature": c["signature"], "key": c["key"], "expected": c["expected"],
                          "actual": c["actual"], "note": det.get("note", ""), "case": det.get("case"),
                          "ops": c["ops"], "replays": r["reproduced"], "replay_outcomes": r["outcomes"],
                          "class": cl["class"], "evidence": cl["evidence"]})
    return {"runs": runs, "candidates": cands}


def markdown(rep: Dict[str, Any]) -> str:
    x = rep["extra"]
    lines = [f"# Pilot: R2 handles, R3 routes, R5 transformations ({rep['date']})", "", x["setup"], "",
             "## Runs", "", "| oracle | server | project | cases | sessions | seconds (run / with replays) | "
             "candidates | reproduced 3/3 |", "|---|---|---|---|---|---|---|---|"]
    for r in rep["runs"]:
        lines.append(f"| {r['oracle']} | {r['server']} | {r['project']} | {r['cases']} | {r['sessions']} | "
                     f"{r['seconds_run']:.0f} / {r['seconds_with_replays']:.0f} | {r['candidates']} | "
                     f"{r['reproduced_3of3']} |")
    lines += ["", "Keys or checks compared (stable) per run:", ""]
    for r in rep["runs"]:
        comp = ", ".join(f"{k} {v}" for k, v in sorted(r["compared"].items())) or "none"
        uns = ", ".join(f"{k} {v}" for k, v in sorted(r["unstable"].items()))
        notes = "; ".join(r["notes"])
        lines.append(f"- {r['oracle']} / {r['server']}: {comp}" + (f"; unstable {uns}" if uns else "") +
                     (f". Notes: {notes}" if notes else ""))
    lines += ["", "## Known-bug check: JDT LS #2111 with R2", "", x["known_bug"], "",
              "| build | cases | candidates | reproduced 3/3 | signatures | notes |", "|---|---|---|---|---|---|"]
    for r in rep["known_bug_runs"]:
        sigs = ", ".join(sorted({c["signature"].split("|")[-1] for c in rep["known_bug_candidates"]
                                 if c["server"] == r["server"].replace(" ", "-")})) or "-"
        lines.append(f"| {r['server']} | {r['cases']} | {r['candidates']} | {r['reproduced_3of3']} | {sigs} | "
                     f"{'; '.join(r['notes'])} |")
    lines += ["", "## Candidates and classification", "", "One row per (oracle, server, signature); every candidate "
              "with its expected/actual answers, case and replay outcomes is in r2_r3_r5.json.", "",
              "| oracle | server | signature (shape) | candidates | replays 3/3 | example keys | class | evidence |",
              "|---|---|---|---|---|---|---|---|"]
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for c in rep["candidates"] + rep["known_bug_candidates"]:
        groups.setdefault((c["oracle"], c["server"], c["signature"]), []).append(c)
    for (oracle, server, sig), cs in groups.items():
        keys = "; ".join(f"{c['key']['path']}:{c['key']['line']}:{c['key']['character']}" for c in cs[:3])
        full = sum(1 for c in cs if c["replays"] == "3/3")
        lines.append(f"| {oracle} | {server} | {sig.split('|')[-1]} | {len(cs)} | {full} | {keys}"
                     f"{' ...' if len(cs) > 3 else ''} | {cs[0]['class']} | {cs[0]['evidence'].replace('|', '/')} |")
    lines += ["", "## Which servers support which sub-checks", "", x["support"], "",
              "## Tool artifacts found and fixed", ""] + [f"- {a}" for a in x["artifacts"]] + \
             ["", "Runs before the fixes (kept in r2_r3_r5.json under extra.before_fix_runs):", ""] + \
             [f"- {b['oracle']} / {b['server']} ({b['run_id']}): {b['candidates']} candidates "
              f"{json.dumps(b['signatures'])}" for b in x.get("before_fix_runs", [])] + \
             ["", "## Known limits", ""] + [f"- {a}" for a in x["limits"]] + \
             ["", "## Reproduce", "", x["reproduce"], ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--known", required=True)
    ap.add_argument("--classes", required=True)
    ap.add_argument("--extra", required=True)
    args = ap.parse_args()
    classes = json.load(open(args.classes))
    main_runs = load(sorted(glob.glob(args.runs)), classes)
    known = load(sorted(glob.glob(args.known), key=lambda f: ("pre" not in f, "post" not in f, f)), classes)
    rep = {"date": time.strftime("%Y-%m-%d %H:%M"), "runs": main_runs["runs"], "candidates": main_runs["candidates"],
           "known_bug_runs": known["runs"], "known_bug_candidates": known["candidates"],
           "extra": json.load(open(args.extra))}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + ".json", "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1, default=str)
    with open(OUT + ".md", "w", encoding="utf-8") as f:
        f.write(markdown(rep))
    print(f"{len(rep['runs'])} runs, {len(rep['candidates'])} candidates, {len(rep['known_bug_runs'])} known-bug runs")
    for c in rep["candidates"] + rep["known_bug_candidates"]:
        if c["class"] == "unclassified":
            print("UNCLASSIFIED", ident(c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
