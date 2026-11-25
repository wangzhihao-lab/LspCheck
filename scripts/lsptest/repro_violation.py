"""Standalone replay of one violation (the command that goes into bug reports).

Reads a repro.json written by the campaign (data/lsptest/runs/<id>/violations/<vid>/repro.json)
or by triage (triage/<group>/repro.json: reduced ops, possibly line-reduced project files),
rebuilds the project (the prepared corpus clone at its commit, or the benchmark case from its
historical files) and the OracleContext of the run (server build, seed, targets, timing,
settings), and replays the case through the oracle's own replay(): fresh sessions only, no
state from the campaign. Prints the recorded expected and actual answers, then per replay
whether it settled, whether the fresh control agreed, whether the difference reproduced, and
the answers observed. Exit status 0 when every replay reproduced, 1 otherwise.

Run line: python3 scripts/lsptest/repro_violation.py <repro.json> [--replays N] [--original-ops] [--verbose]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import shutil
import sys
import time
import uuid
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import flake  # noqa: E402
import oracles  # noqa: E402
from campaign_store import (context_from_repro, load_repro, op_text, prepare_repro_project,  # noqa: E402
                            violation_from_json)
from driver import RUNS_DIR  # noqa: E402

logger = logging.getLogger("repro_violation")


def show(x: Any, limit: int = 1200) -> str:
    s = json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + f"... ({len(s)} chars)"


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay one violation from its repro.json with fresh sessions.")
    ap.add_argument("repro")
    ap.add_argument("--replays", type=int, default=1)
    ap.add_argument("--original-ops", action="store_true", help="replay the violation's original (unreduced) ops")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    doc, v = load_repro(args.repro)
    if args.original_ops:
        v = dataclasses.replace(v, ops=violation_from_json(doc["violation"]).ops)
    p, c, k = doc["project"], doc["context"], v.key
    print(f"repro: {args.repro}")
    print(f"oracle {v.oracle}; server {doc['server']['kind']} {doc['server']['version']}; project {p['name']} "
          f"({p['source']}{', commit ' + p['commit'] if p.get('commit') else ''}); timing {c['timing']}; "
          f"seed {c['seed']}")
    print(f"key: {k.method} {k.path}:{k.line}:{k.character}{' ' + k.extra if k.extra else ''}; "
          f"signature {v.signature}")
    if doc.get("project_files"):
        print(f"project files replaced (line-reduced): {sorted(doc['project_files'])}")
    print(f"ops ({len(v.ops)}):" + "".join(f"\n  {i + 1}. {op_text(o)}" for i, o in enumerate(v.ops))
          if v.ops else "ops: none (fresh sessions only)")
    print(f"expected (recorded): {show(doc.get('expected'))}")
    print(f"actual   (recorded): {show(doc.get('actual'))}")
    scratch = os.path.join(RUNS_DIR, f"repro-{doc.get('vid') or 'x'}-{uuid.uuid4().hex[:8]}")
    hits = 0
    try:
        ctx = context_from_repro(doc, prepare_repro_project(doc, scratch), os.path.join(scratch, "work"))
        oracle = oracles.get(v.oracle)
        for i in range(args.replays):
            t0 = time.monotonic()
            out = oracle.replay(ctx, v)
            hits += int(flake.counts(out))
            print(f"replay {i + 1}/{args.replays}: settled={out.settled} control_stable={out.control_stable} "
                  f"reproduced={out.reproduced} ({time.monotonic() - t0:.1f}s)")
            if out.observed is not None:
                print(f"  observed expected: {show(out.observed.expected)}")
                print(f"  observed actual:   {show(out.observed.actual)}")
            elif out.settled and out.control_stable:
                print("  observed: the case session answered the key like the fresh sessions")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    print(f"verdict: reproduced {hits}/{args.replays}")
    return 0 if hits == args.replays else 1


if __name__ == "__main__":
    raise SystemExit(main())
