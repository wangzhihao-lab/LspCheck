"""Advisory lock for the bench scripts that append to or rewrite shared files under
data/lsp_bench/ (repro_results.jsonl/.md, builds.json): several case writers may run at
the same time, and a read-modify-write or a read during an append must not interleave.

Run line: imported by run_repro.py and install_builds.py; not run directly.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
from typing import Iterator

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
LOCK_PATH = os.path.join(REPO, "temp", "lsp_bench", "write.lock")


@contextlib.contextmanager
def locked(path: str = LOCK_PATH) -> Iterator[None]:
    """Exclusive lock for the duration of the block (never nest it in one process)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


__all__ = ["LOCK_PATH", "locked"]
