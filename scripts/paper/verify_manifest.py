"""Check every file of the replication package against MANIFEST.sha256 (and report files it does not list).

MANIFEST.sha256 has one line per file, `<sha256>  <path relative to the package root>`, written when the package
was built. Files the scripts write when they are rerun (paper_numbers.json,
the appendix tables) change when they are regenerated; the check reports them as changed.

Run line: python3 scripts/paper/verify_manifest.py [package root, default: the root this script is in]
"""

from __future__ import annotations

import hashlib
import os
import sys
from typing import Dict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
IGNORED_DIRS = {"__pycache__", "temp", ".git"}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(root: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    with open(os.path.join(root, "MANIFEST.sha256"), encoding="utf-8") as f:
        for line in f:
            digest, _, rel = line.rstrip("\n").partition("  ")
            if rel:
                out[rel] = digest
    return out


def main() -> int:
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    listed = read_manifest(root)
    missing = changed = 0
    for rel, digest in sorted(listed.items()):
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            missing += 1
            print(f"missing: {rel}")
        elif sha256(path) != digest:
            changed += 1
            print(f"changed: {rel}")
    extra = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            if rel != "MANIFEST.sha256" and rel not in listed:
                extra.append(rel)
    for rel in sorted(extra):
        print(f"not in manifest: {rel}")
    print(f"{len(listed)} files listed: {missing} missing, {changed} changed, {len(extra)} not in the manifest")
    return 0 if not (missing or changed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
