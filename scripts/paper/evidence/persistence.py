"""Does the wrong answer persist? (post-freeze evidence, review round 2)

The harness declares a push-diagnostics session settled after 2 s without a message from the server.
If a server finished updating its state later, a history answer could be late rather than wrong.
For every history group judged a bug, this script replays the reduced history four ways, once each,
through the R1 oracle's own replay(): as recorded, and followed by 5, 30 and 60 s in which the client
sends nothing before the answers are compared with a fresh session. A wrong answer that still differs
after 60 s is a persistent state, not a late one.

A single replay can miss a reproduction that the three-replay rule would catch, so a group that does
not reproduce after the longest wait can be replayed again with only that wait (--waits 60 --replays 2
--groups ... --out persistence_retry); numbers_evidence.py adds those replays to the group's row.

Writes data/lsptest/runs/<campaign>/evidence/<out>.{json,log} (default campaign main_v1, default out: persistence).
--campaign main_v2 takes the groups of the causes from main_v2/triage/root_causes.csv.

Run line: python3 scripts/paper/evidence/persistence.py [--causes C1 C2 C9 C10] [--waits 0 5 30 60]
          [--replays 1] [--groups GID ...] [--out persistence] [--campaign main_v1|main_v2]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import CAMPAIGN, evidence_dir, groups_of, original_ops, replay_variant  # noqa: E402

from model import Op  # noqa: E402  (frozen tool, read-only)

logger = logging.getLogger("persistence")
WAITS_S = (0, 5, 30, 60)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--causes", nargs="*", default=["C1", "C2", "C9", "C10"])
    ap.add_argument("--waits", nargs="*", type=int, default=list(WAITS_S))
    ap.add_argument("--replays", type=int, default=1)
    ap.add_argument("--groups", nargs="*", default=None, help="only these groups (default: all of --causes)")
    ap.add_argument("--out", default="persistence")
    ap.add_argument("--campaign", default=CAMPAIGN)
    args = ap.parse_args()
    evidence = evidence_dir(args.campaign)
    gids = [g for g in groups_of(args.causes, args.campaign) if args.groups is None or g in args.groups]
    rows: List[Dict] = []
    for gid in gids:
        ops = original_ops(gid, args.campaign)
        row: Dict = {"gid": gid, "by_wait": {}}
        for wait in args.waits:
            variant = ops + ([Op(kind="wait", delay_ms=wait * 1000)] if wait else [])
            r = replay_variant(gid, f"pw{wait}", ops=variant, replays=args.replays, campaign=args.campaign)
            row["by_wait"][str(wait)] = {k: r[k] for k in ("verdict", "replays", "reproduced", "settled",
                                                           "control_stable", "seconds", "error")}
            logger.info("%s wait %ss: %s", gid, wait, r["verdict"])
        rows.append(row)
    with open(os.path.join(evidence, f"{args.out}.json"), "w", encoding="utf-8") as f:
        json.dump({"waits_s": list(args.waits), "replays": args.replays, "rows": rows}, f, ensure_ascii=False, indent=1)
    lines = [f"{r['gid']}: " + ", ".join(f"{w}s {v['verdict']}" for w, v in r["by_wait"].items()) for r in rows]
    with open(os.path.join(evidence, f"{args.out}.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
