"""Central path and repo constants for the LSP fix-evidence backfill pipeline.

All paths are resolved relative to the TSE2 project root so the scripts can
be invoked from any working directory.
"""

from __future__ import annotations

from pathlib import Path

# Project root: .../TSE2
ROOT = Path(__file__).resolve().parents[2]

DATA_IN_DIR = ROOT / "data" / "lsp_pilot"
DATA_OUT_DIR = ROOT / "data" / "lsp_backfill"
CLONE_DIR = ROOT / "temp" / "clones"
CACHE_DIR = CLONE_DIR / "cache"

# Input JSONL files
PYRIGHT_ALL_JSONL = DATA_IN_DIR / "pyright-addressed-in-next-version_fixed_bugs.jsonl"
PYRIGHT_LINKED_JSONL = DATA_IN_DIR / "pyright_fixed_bugs.jsonl"
GOPLS_JSONL = DATA_IN_DIR / "golang-go-gopls_fixed_bugs.jsonl"

# Output files
PYRIGHT_OUT_JSONL = DATA_OUT_DIR / "pyright_fix_evidence.jsonl"
GOPLS_OUT_JSONL = DATA_OUT_DIR / "gopls_fix_evidence.jsonl"
SUMMARY_MD = DATA_OUT_DIR / "backfill_summary.md"

# Repos
PYRIGHT_REPO_URL = "https://github.com/microsoft/pyright.git"
PYRIGHT_REPO_DIR = CLONE_DIR / "pyright.git"

TOOLS_REPO_URL = "https://github.com/golang/tools.git"
TOOLS_REPO_DIR = CLONE_DIR / "tools.git"

# Caches (derived from clones; never committed, live under temp/)
PYRIGHT_LOG_CACHE = CACHE_DIR / "pyright_full_log.jsonl"
TOOLS_LOG_CACHE = CACHE_DIR / "tools_full_log.jsonl"
PYRIGHT_NUMSTAT_CACHE = CACHE_DIR / "pyright_numstat_cache.json"
TOOLS_NUMSTAT_CACHE = CACHE_DIR / "tools_numstat_cache.json"
CLONE_REPORT_JSON = CACHE_DIR / "clone_report.json"


def ensure_dirs() -> None:
    """Create output/cache directories if they do not already exist."""
    for d in (DATA_OUT_DIR, CLONE_DIR, CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
