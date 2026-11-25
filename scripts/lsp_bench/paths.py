"""Path and constant definitions for the LSP bug-benchmark candidate miner.

Every path is resolved from the TSE2 project root, so the scripts can be run
from any working directory. Inputs are read-only; outputs go to
``data/lsp_bench``; caches and git clones live under ``temp/lsp_bench`` and can
be deleted at any time (they are rebuilt on the next run).

Run line: imported by the other scripts in scripts/lsp_bench, not run directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

ROOT: Path = Path(__file__).resolve().parents[2]

PILOT_DIR: Path = ROOT / "data" / "lsp_pilot"
BACKFILL_DIR: Path = ROOT / "data" / "lsp_backfill"
OUT_DIR: Path = ROOT / "data" / "lsp_bench"
TEMP_DIR: Path = ROOT / "temp" / "lsp_bench"
CACHE_DIR: Path = TEMP_DIR / "cache"
HTTP_CACHE_DIR: Path = CACHE_DIR / "http"
SHEETS_DIR: Path = TEMP_DIR / "sheets"

# Existing blobless clones (read-only use) and the treeless clones this miner adds.
PYRIGHT_REPO: Path = ROOT / "temp" / "clones" / "pyright.git"
TOOLS_REPO: Path = ROOT / "temp" / "clones" / "tools.git"
TS_REPO: Path = TEMP_DIR / "clones" / "TypeScript.git"
RA_REPO: Path = TEMP_DIR / "clones" / "rust-analyzer.git"
CLONE_URLS: Dict[str, str] = {
    str(TS_REPO): "https://github.com/microsoft/TypeScript.git",
    str(RA_REPO): "https://github.com/rust-lang/rust-analyzer.git",
}

SERVERS: List[str] = ["pyright", "tsserver", "rust-analyzer", "gopls"]

ISSUE_FILES: Dict[str, List[Path]] = {
    "pyright": [
        PILOT_DIR / "pyright_fixed_bugs.jsonl",
        PILOT_DIR / "pyright-addressed-in-next-version_fixed_bugs.jsonl",
    ],
    "tsserver": [PILOT_DIR / "microsoft-typescript_fixed_bugs.jsonl"],
    "rust-analyzer": [PILOT_DIR / "rust-analyzer_fixed_bugs.jsonl"],
    "gopls": [PILOT_DIR / "golang-go-gopls_fixed_bugs.jsonl"],
}

FIX_EVIDENCE_FILES: Dict[str, Path] = {
    "pyright": BACKFILL_DIR / "pyright_fix_evidence.jsonl",
    "gopls": BACKFILL_DIR / "gopls_fix_evidence.jsonl",
}

REPO_SLUG: Dict[str, str] = {
    "pyright": "microsoft/pyright",
    "tsserver": "microsoft/TypeScript",
    "rust-analyzer": "rust-lang/rust-analyzer",
    "gopls": "golang/go",
}

CODE_REPO_SLUG: Dict[str, str] = {
    "pyright": "microsoft/pyright",
    "tsserver": "microsoft/TypeScript",
    "rust-analyzer": "rust-lang/rust-analyzer",
    "gopls": "golang/tools",
}

MIN_CREATED_AT: str = "2019-01-01"

CANDIDATES_JSONL: Path = OUT_DIR / "candidates.jsonl"
CANDIDATES_MD: Path = OUT_DIR / "candidates.md"


def ensure_dirs() -> None:
    """Create the output and cache directories if they are missing."""
    for d in (OUT_DIR, TEMP_DIR, CACHE_DIR, HTTP_CACHE_DIR, SHEETS_DIR):
        d.mkdir(parents=True, exist_ok=True)
