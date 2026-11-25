"""Freeze the tool before an evaluation: a sha256 manifest of every source file of the tool
(scripts/lsptest and scripts/lsp_repro, tests included) plus a source archive, so that every
evaluation run can be tied to one frozen version, and a check that the working tree still
matches a freeze. The repository has no version control, so this is the record.

  python3 scripts/lsptest/freeze_tool.py freeze v1 --note "..."   writes data/lsptest/freeze/<id>.{json,tar.gz}
  python3 scripts/lsptest/freeze_tool.py check v1                 exit 1 and list files if the tree differs

Run line: python3 scripts/lsptest/freeze_tool.py check v1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import tarfile
import time
from typing import Dict, List

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ROOTS = ("scripts/lsptest", "scripts/lsp_repro")
FREEZE_DIR = os.path.join(REPO, "data", "lsptest", "freeze")
SUFFIXES = (".py", ".js", ".json", ".md")

logger = logging.getLogger(__name__)


def source_files() -> List[str]:
    """Repository-relative tool sources, sorted (caches and bytecode skipped)."""
    out = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, root)):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__" and not d.startswith("."))
            out += [os.path.relpath(os.path.join(dirpath, f), REPO) for f in filenames if f.endswith(SUFFIXES)]
    return sorted(out)


def manifest() -> Dict[str, str]:
    digests = {}
    for rel in source_files():
        with open(os.path.join(REPO, rel), "rb") as f:
            digests[rel] = hashlib.sha256(f.read()).hexdigest()
    return digests


def tree_digest(files: Dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16]


def freeze(fid: str, note: str) -> str:
    os.makedirs(FREEZE_DIR, exist_ok=True)
    path = os.path.join(FREEZE_DIR, f"{fid}.json")
    if os.path.exists(path):
        raise SystemExit(f"freeze {fid} already exists: {path}")
    files = manifest()
    record = {"id": fid, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "note": note,
              "tree_digest": tree_digest(files), "files": files}
    with tarfile.open(os.path.join(FREEZE_DIR, f"{fid}.tar.gz"), "w:gz") as tar:
        for rel in files:
            tar.add(os.path.join(REPO, rel), arcname=rel)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1, sort_keys=True)
    return record["tree_digest"]


def check(fid: str) -> List[str]:
    """Files added, removed or changed since the freeze (empty: the tree matches)."""
    with open(os.path.join(FREEZE_DIR, f"{fid}.json"), encoding="utf-8") as f:
        frozen = json.load(f)["files"]
    now = manifest()
    return sorted([f"changed {p}" for p in now if p in frozen and now[p] != frozen[p]]
                  + [f"added {p}" for p in now if p not in frozen] + [f"removed {p}" for p in frozen if p not in now])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("freeze", "check"))
    ap.add_argument("id")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.action == "freeze":
        logger.info("froze %s: tree %s, %d files", args.id, freeze(args.id, args.note), len(source_files()))
        return 0
    diffs = check(args.id)
    for d in diffs:
        logger.info(d)
    logger.info("tree matches freeze %s" % args.id if not diffs else f"{len(diffs)} difference(s) from freeze {args.id}")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
