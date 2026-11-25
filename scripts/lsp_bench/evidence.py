"""Whether a candidate's fix came with a test (a scripted specification).

pyright and golang/tools are blobless clones with trees, so changed paths come
from ``git show --name-only``. The TypeScript and rust-analyzer clones are
treeless, so their PR file lists come from the GitHub pulls/files API; for
rust-analyzer, inline ``#[test]`` additions in the patch also count, since its
tests usually live next to the code they check.

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

import gitq
from httpcache import get_json
from issues import Issue
from paths import PYRIGHT_REPO, TOOLS_REPO
from versions_common import VersionMapping

logger = logging.getLogger(__name__)

_TEST_PATH = re.compile(r"(^|/)(tests?|testdata|testing|fourslash|baselines)(/|$)|_test\.go$|\.test\.ts$|tests?\.rs$", re.I)
_RA_INLINE_TEST = re.compile(r"^\+\s*(#\[test\]|check_assist\w*\(|check_fix\w*\(|check_diagnostics\w*\(|check_edit\w*\(|check\()", re.M)


def _paths_from_git(repo: Path, shas: List[str]) -> Optional[List[str]]:
    paths: List[str] = []
    for sha in shas:
        try:
            out = gitq.run_git(repo, ["show", "--name-only", "--format=", "--no-renames", sha])
        except RuntimeError:
            return None
        paths.extend(p for p in out.splitlines() if p.strip())
    return paths


def _pr_numbers(issue: Issue, slug: str) -> List[int]:
    return [int(n) for n, url, merged, _ in issue.closing_prs if merged and n and f"{slug}/pull/" in (url or "")]


def fix_touches_tests(server: str, issue: Issue, mapping: VersionMapping) -> Optional[bool]:
    """True/False if the fix's changed files include tests; None if unknown."""
    shas = [s for s in mapping.fix_shas if s]
    if server in ("pyright", "gopls"):
        repo = PYRIGHT_REPO if server == "pyright" else TOOLS_REPO
        paths = _paths_from_git(repo, shas[:3]) if shas else None
        if paths is None:
            return None
        return any(_TEST_PATH.search(p) for p in paths)
    slug = "microsoft/TypeScript" if server == "tsserver" else "rust-lang/rust-analyzer"
    nums = _pr_numbers(issue, slug)
    if not nums:
        return None
    found = False
    for n in nums[:2]:
        files = get_json(f"https://api.github.com/repos/{slug}/pulls/{n}/files?per_page=100") or []
        for f in files:
            name = f.get("filename", "")
            if _TEST_PATH.search(name):
                found = True
            if server == "rust-analyzer" and _RA_INLINE_TEST.search(f.get("patch") or ""):
                found = True
    return found
