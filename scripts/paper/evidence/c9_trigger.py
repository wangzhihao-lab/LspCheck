"""Which operations of C9's reduced history make the difference (post-freeze evidence, review round 2).

C9 (gopls-r1-references-extra-h9-0290a7, bubbletea): references of tea.Model from examples/http/main.go
include the package's test files after the reduced history and exclude them in a fresh session. The
reduced history has seven operations: open examples/http/main.go, open examples/set-window-title/main.go,
open termios_unix.go (package tea), insert "(" in it, close and reopen set-window-title, close
termios_unix.go without saving. The query step of both sessions opens mouse.go (package tea) as well.
This script replays subsets of the seven operations, three times each, through the R1 oracle's own
replay(), to find the operations the extra answer needs. Every subset leaves the same final content.

Writes data/lsptest/runs/main_v1/evidence/c9_trigger.{json,log}.

Run line: python3 scripts/paper/evidence/c9_trigger.py [--replays 3]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import EVIDENCE, original_ops, replay_variant  # noqa: E402

logger = logging.getLogger("c9_trigger")
GID = "gopls-r1-references-extra-h9-0290a7"
# indices into the reduced history: 0 open http, 1 open set-window-title, 2 open termios_unix.go,
# 3 edit termios_unix.go, 4 close set-window-title, 5 reopen set-window-title, 6 close termios_unix.go
VARIANTS: Tuple[Tuple[str, List[int]], ...] = (
    ("all seven operations", [0, 1, 2, 3, 4, 5, 6]),
    ("without the edit of termios_unix.go", [0, 1, 2, 4, 5, 6]),
    ("open, edit and close termios_unix.go only", [0, 2, 3, 6]),
    ("open and close termios_unix.go only", [0, 2, 6]),
    ("without termios_unix.go", [0, 1, 4, 5]),
    ("open examples/http/main.go only", [0]),
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--replays", type=int, default=3)
    args = ap.parse_args()
    ops = original_ops(GID)
    if len(ops) != 7:
        raise SystemExit(f"expected the seven reduced operations, got {len(ops)}")
    rows: List[Dict] = []
    for name, idx in VARIANTS:
        logger.info("variant: %s", name)
        row = replay_variant(GID, "c9t", ops=[ops[i] for i in idx], replays=args.replays)
        row.update(variant=name, ops=[ops[i].to_json() for i in idx])
        rows.append(row)
        logger.info("  -> %s (%s/%s)", row["verdict"], row["reproduced"], row["replays"])
    with open(os.path.join(EVIDENCE, "c9_trigger.json"), "w", encoding="utf-8") as f:
        json.dump({"group": GID, "rows": rows}, f, ensure_ascii=False, indent=1)
    lines = [f"{r['variant']}: {r['verdict']} ({r['reproduced']}/{r['replays']}) {r['error']}" for r in rows]
    with open(os.path.join(EVIDENCE, "c9_trigger.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
