"""Screening decisions: gopls, issues added by the recall audit (recall_audit.INCLUDE).

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "gopls"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    35548: ("R1", "B", "Changing the env setting (GOFLAGS) through didChangeConfiguration did not recompute diagnostics; the fix returns the new view's snapshot and diagnoses its workspace packages.", "config: change env GOFLAGS (e.g. build tags) via didChangeConfiguration; compare diagnostics with a fresh session"),
}

REJECT: Dict[str, Tuple[int, ...]] = {}
