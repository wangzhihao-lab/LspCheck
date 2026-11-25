"""rust-analyzer: map an issue to the weekly releases just before / after its fix.

Fix: the merged closing PR(s) in rust-lang/rust-analyzer. The merge commit
("Merge pull request #N", "Merge #N" (bors), "Auto merge of #N" (homu)) is
located in the local treeless clone; else the issue's ``closer_commit``; else
the pulls API ``merge_commit_sha``.
Weekly releases are date tags (YYYY-MM-DD). post = earliest date tag that
contains the merge commit (``git tag --contains``); pre = latest date tag
before post that does not (exact, so confidence is high whenever a pre-fix
tag exists). The date rule (first release after the merge date, last release
before it) is recorded as a cross-check and flagged when it differs. Builds: the GitHub
release of each tag must carry the asset rust-analyzer-aarch64-apple-darwin.gz;
when the exact pre or post release lacks it, the window is widened to the
nearest earlier pre-fix / later post-fix release that has it (recorded).

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple

import gitq
from httpcache import get_json
from issues import Issue
from paths import RA_REPO
from versions_common import VersionMapping, iso_date, none_mapping, register_mapper

logger = logging.getLogger(__name__)

_DATE_TAG = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ASSET = "rust-analyzer-aarch64-apple-darwin.gz"


@lru_cache(maxsize=1)
def date_tags() -> Tuple[str, ...]:
    return tuple(sorted(t for t in gitq.tag_dates(RA_REPO) if _DATE_TAG.match(t)))


@lru_cache(maxsize=1)
def release_assets() -> Dict[str, Set[str]]:
    """Map release tag -> asset names, from the GitHub releases API (all pages)."""
    out: Dict[str, Set[str]] = {}
    page = 1
    while True:
        rows = get_json(f"https://api.github.com/repos/rust-lang/rust-analyzer/releases?per_page=100&page={page}") or []
        for r in rows:
            out[r.get("tag_name", "")] = {a.get("name", "") for a in r.get("assets") or []}
        if len(rows) < 100:
            break
        page += 1
    return out


def _merge_commits(issue: Issue) -> Tuple[List[Tuple[int, str]], List[str]]:
    idx = gitq.pr_index(RA_REPO)
    found: List[Tuple[int, str]] = []
    merged_at: List[str] = []
    for num, url, merged, m_at in issue.closing_prs:
        if not merged or not num or "rust-lang/rust-analyzer/pull/" not in (url or ""):
            continue
        commits = idx.get(int(num), [])
        sha: Optional[str] = commits[0].sha if commits else None
        if sha is None and issue.closer_commit and gitq.commit_exists(RA_REPO, issue.closer_commit):
            sha = issue.closer_commit
        if sha is None:
            pr = get_json(f"https://api.github.com/repos/rust-lang/rust-analyzer/pulls/{num}") or {}
            cand = pr.get("merge_commit_sha")
            sha = cand if cand and gitq.commit_exists(RA_REPO, cand) else None
            m_at = m_at or pr.get("merged_at")
        if sha:
            found.append((int(num), sha))
        if m_at:
            merged_at.append(iso_date(m_at) or m_at)
    if not found and issue.closer_commit and gitq.commit_exists(RA_REPO, issue.closer_commit):
        found.append((0, issue.closer_commit))
    return found, merged_at


@register_mapper("rust-analyzer")
def map_ra(issue: Issue) -> VersionMapping:
    merges, merged_at = _merge_commits(issue)
    if not merges:
        elsewhere = [url for _, url, merged, _ in issue.closing_prs if merged and url and "rust-analyzer/pull/" not in url]
        if elsewhere:
            return none_mapping("; ".join(elsewhere), "fix merged outside rust-analyzer (" + ", ".join(
                "/".join(u.split("/")[3:5]) for u in elsewhere) + "), so no rust-analyzer release pair isolates it")
        return none_mapping("none", "no merged rust-analyzer PR or closer commit found locally")
    commits = gitq.commit_index(RA_REPO)
    refs = []
    for num, sha in merges:
        c = commits.get(sha)
        title = ""
        if c is not None:
            body_first = next((ln for ln in c.body.splitlines() if ln.strip()), "")
            title = body_first if c.subject.startswith(("Merge pull request", "Merge #", "Auto merge")) else c.subject
        refs.append(f"rust-lang/rust-analyzer#{num} ({title[:80]})" if num else f"commit {sha[:10]} ({title[:80]})")
    fix_date = max(merged_at) if merged_at else iso_date(commits[merges[0][1]].date) if merges[0][1] in commits else None
    shas = [s for _, s in merges]
    tags = date_tags()
    containing_sets = [set(t for t in gitq.tags_containing(RA_REPO, s) if _DATE_TAG.match(t)) for s in shas]
    containing = set.intersection(*containing_sets) if containing_sets else set()
    any_containing = set.union(*containing_sets) if containing_sets else set()
    extra: Dict[str, object] = {}
    day = (fix_date or "")[:10]
    date_post = next((t for t in tags if t > day), None)
    date_pre = next((t for t in reversed(tags) if t <= day), None)
    extra["date_rule"] = f"{date_pre} -> {date_post}"
    if not containing:
        return VersionMapping(fix_ref="; ".join(refs), fix_shas=tuple(shas), fix_date=fix_date,
                              pre_version=tags[-1] if tags else None, post_version=None,
                              pre_date=None, post_date=None, mapping_confidence="low",
                              mapping_method="no weekly release tag contains the merge commit (unreleased)",
                              builds_obtainable=False, build_notes="post-fix release not yet published", extra=extra)
    post = min(containing)
    below = [t for t in tags if t < post and t not in any_containing]
    pre = below[-1] if below else None
    if (pre, post) != (date_pre, date_post):
        extra["date_rule_differs"] = True
    assets = release_assets()
    has = lambda t: t is not None and ASSET in assets.get(t, set())  # noqa: E731
    exact = (pre, post)
    if pre is not None and not has(pre):
        pre = next((t for t in reversed(below) if has(t)), None)
    if not has(post):
        post = next((t for t in sorted(containing) if has(t)), post)
    if (pre, post) != exact:
        extra["window_widened_for_assets"] = f"{exact[0]} -> {exact[1]} lacks {ASSET}; using {pre} -> {post}"
    ok_pre, ok_post = has(pre), has(post)
    conf = "high" if pre else "medium"
    notes = f"GitHub release asset {ASSET}: pre {pre} {'present' if ok_pre else 'MISSING'}, post {post} {'present' if ok_post else 'MISSING'}"
    if "window_widened_for_assets" in extra:
        notes += f" (exact window {exact[0]} -> {exact[1]} widened: an adjacent release lacks the asset)"
    return VersionMapping(fix_ref="; ".join(refs), fix_shas=tuple(shas), fix_date=fix_date,
                          pre_version=pre, post_version=post, pre_date=pre, post_date=post,
                          mapping_confidence=conf,
                          mapping_method="merge commit; git tag --contains on weekly date tags; date rule cross-check",
                          builds_obtainable=bool(ok_pre and ok_post), build_notes=notes, extra=extra)
