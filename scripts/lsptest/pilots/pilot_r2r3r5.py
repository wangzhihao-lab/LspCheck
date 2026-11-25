"""Pilot driver for the R2/R3/R5 oracles: one oracle run on one (server, project), then
replay() three times per candidate. Writes one JSON record per run.

Run line: python3 scripts/lsptest/pilots/pilot_r2r3r5.py --oracle r3_routes --server ts7 --version 7.0.2 \
    --project temp/corpus/pmndrs__zustand@b57db4f86ef1 --language typescript --out out.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsp_repro"))

from oracles import get  # noqa: E402
from oracles.base import OracleContext, shape_of  # noqa: E402
from targets import EXCLUDED_DIRS, FileTargets, TargetConfig, choose_targets, targets_to_json  # noqa: E402
from ops import LineIndex  # noqa: E402

logger = logging.getLogger("pilot")
WORK = os.path.join(REPO, "temp", "lsptest_runs", "r2r3r5-pilot")
JAVA_KW = set("abstract boolean break byte case catch char class const continue default do double else enum extends "
              "final finally float for goto if implements import instanceof int interface long native new package "
              "private protected public return short static strictfp super switch synchronized this throw throws "
              "transient try void volatile while var record".split())


def java_case_project(case: str) -> Tuple[str, Tuple[FileTargets, ...]]:
    """A JDT project built only from a benchmark case's source files, and identifier targets."""
    sys.path.insert(0, os.path.join(REPO, "scripts", "lsp_repro", "cases"))
    mod = __import__(case)
    from javaproj import with_sources
    root = os.path.join(WORK, f"{case}-project")
    os.makedirs(root, exist_ok=True)
    files = with_sources({mod.REL: mod.SRC})
    for rel, text in files.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    idx = LineIndex(mod.SRC)
    toks = [m for m in re.finditer(r"[A-Za-z_]\w*", mod.SRC) if m.group() not in JAVA_KW]
    ft = FileTargets(mod.REL, tuple(idx.position((m.start() + m.end()) // 2) for m in toks),
                     tuple(idx.position(m.end()) for m in toks), tuple(m.group() for m in toks))
    return root, (ft,)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--oracle", required=True)
    ap.add_argument("--server", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--project", default="")
    ap.add_argument("--java-case", default="")
    ap.add_argument("--language", default="")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--files", type=int, default=2)
    ap.add_argument("--positions", type=int, default=8)
    ap.add_argument("--exclude", default="")
    ap.add_argument("--max-cases", type=int, default=6)
    ap.add_argument("--replays", type=int, default=3)
    ap.add_argument("--timing", default="settled")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_id = f"{args.oracle}-{args.server}-{time.strftime('%H%M%S')}"
    if args.java_case:
        project_dir, targets = java_case_project(args.java_case)
        label, language = f"case:{args.java_case}", "java"
    else:
        project_dir = os.path.join(REPO, args.project)
        language = args.language
        cfg = TargetConfig(seed=args.seed, max_files=args.files, max_positions_per_file=args.positions,
                           exclude_dirs=EXCLUDED_DIRS | frozenset(x for x in args.exclude.split(",") if x))
        targets = choose_targets(project_dir, language, cfg)
        label = os.path.basename(project_dir).replace("__", "/")
    ctx = OracleContext(run_id, args.server, args.version, label, project_dir, language, args.seed, targets,
                        timing=args.timing, max_cases=args.max_cases, work_dir=os.path.join(WORK, run_id))
    oracle = get(args.oracle)
    t0 = time.monotonic()
    res = oracle.run(ctx)
    record: Dict[str, Any] = {"oracle": args.oracle, "server": args.server, "version": args.version,
                              "project": label, "language": language, "seed": args.seed,
                              "targets": targets_to_json(targets), "max_cases": args.max_cases,
                              "timing": args.timing, "result": res.to_json(), "replays": []}
    logger.info("run: %d cases, %d candidates, %.1fs", res.cases, len(res.candidates), res.seconds)
    for i, v in enumerate(res.candidates):
        outs: List[Dict[str, Any]] = []
        for r in range(args.replays):
            o = oracle.replay(ctx, v)
            outs.append({"settled": o.settled, "control_stable": o.control_stable, "reproduced": o.reproduced,
                         "seconds": o.seconds, "observed_shape": shape_of(o.observed) if o.observed else None,
                         "observed_actual": o.observed.actual if o.observed else None,
                         "observed_expected": o.observed.expected if o.observed else None})
            logger.info("candidate %d/%d replay %d: %s", i + 1, len(res.candidates), r + 1, outs[-1]["reproduced"])
        record["replays"].append({"signature": v.signature, "key": v.key.__dict__, "outcomes": outs,
                                  "reproduced": f"{sum(o['reproduced'] for o in outs)}/{len(outs)}"})
    record["total_seconds"] = round(time.monotonic() - t0, 1)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=1, default=str)
    print(f"{args.oracle} {args.server} {label}: cases={res.cases} sessions={res.sessions} "
          f"candidates={len(res.candidates)} seconds={record['total_seconds']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
