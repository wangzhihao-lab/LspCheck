"""pyright: map an issue to the npm releases just before / after its fix.

Fix commits, in order of preference: the squash commit of a merged closing PR
("... (#PR)") found in the local clone, the ``closer_commit``, and the
backfilled commits that mention the issue (merge commits excluded).
With fix commits: post = lowest 1.0.x/1.1.x tag containing every fix commit
(``git tag --contains``); pre = highest 1.1.x release below post containing
none of them. Without a fix commit: the maintainer's closing comment
("addressed in pyright 1.1.xxx", GitHub issue comments API) gives post; failing
that, post = first npm release published after the "addressed in next version"
label was added (issue events API; the label marks a committed fix); as a last
resort (low confidence), the latest release published before the issue closed.
Both versions are checked against ``npm view pyright time``; the npm package
only ships ``pyright-langserver`` from 1.1.52 on, so earlier windows are
marked as not obtainable from npm.

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
from paths import PYRIGHT_REPO
from versions_common import (VersionMapping, iso_date, none_mapping, npm_times,
                             previous_release, register_mapper, semver_key)

logger = logging.getLogger(__name__)

_REL = re.compile(r"^1\.[01]\.\d+$")
FIRST_NPM_LANGSERVER = "1.1.52"  # first npm release whose "bin" includes pyright-langserver
_COMMENT_VER = re.compile(r"(?:addressed|included|fixed|available|released|published)\s+in\s+(?:pyright\s+|the\s+|version\s+)?\[?(1\.[01]\.\d+)", re.I)


@lru_cache(maxsize=1)
def releases() -> Tuple[str, ...]:
    """pyright 1.0.x and 1.1.x versions published on npm, ascending."""
    return tuple(sorted((v for v in npm_times("pyright") if _REL.match(v)), key=semver_key))


def _fix_shas(issue: Issue) -> Tuple[List[str], str]:
    idx = gitq.pr_index(PYRIGHT_REPO)
    shas: List[str] = []
    how: List[str] = []
    for num, url, merged, _ in issue.closing_prs:
        if merged and num and "microsoft/pyright/pull/" in (url or ""):
            for c in idx.get(int(num), []):
                shas.append(c.sha)
                how.append(f"PR #{num}")
    if issue.closer_commit and gitq.commit_exists(PYRIGHT_REPO, issue.closer_commit):
        shas.append(issue.closer_commit)
        how.append("closer_commit")
    for c in issue.fix_commits:
        if c.subject.startswith("Merge ") or not gitq.commit_exists(PYRIGHT_REPO, c.hash):
            continue
        shas.append(c.hash)
        how.append("backfill")
    return list(dict.fromkeys(shas)), "+".join(dict.fromkeys(how))


def _first_release_containing(sha: str) -> Optional[str]:
    tags = [t for t in gitq.tags_containing(PYRIGHT_REPO, sha) if _REL.match(t)]
    return min(tags, key=semver_key) if tags else None


def _comment_version(issue: Issue) -> Optional[Tuple[str, str]]:
    url = f"https://api.github.com/repos/microsoft/pyright/issues/{issue.number}/comments?per_page=100"
    comments = get_json(url) or []
    found: Optional[Tuple[str, str]] = None
    for c in comments:
        m = _COMMENT_VER.search(c.get("body") or "")
        if m and (c.get("author_association") in ("MEMBER", "OWNER", "COLLABORATOR", "CONTRIBUTOR")):
            found = (m.group(1), (c.get("user") or {}).get("login", ""))
    return found


def _label_time(issue: Issue) -> Optional[str]:
    url = f"https://api.github.com/repos/microsoft/pyright/issues/{issue.number}/events?per_page=100"
    times = [iso_date(e.get("created_at")) or "" for e in (get_json(url) or [])
             if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == "addressed in next version"]
    return max(times) if times else None


@register_mapper("pyright")
def map_pyright(issue: Issue) -> VersionMapping:
    times: Dict[str, str] = npm_times("pyright")
    rels = releases()
    shas, how = _fix_shas(issue)
    commits = gitq.commit_index(PYRIGHT_REPO)
    fix_dates = sorted(iso_date(commits[s].date) or "" for s in shas if s in commits)
    fix_date = fix_dates[0] if fix_dates else None
    fix_ref = "; ".join(f"microsoft/pyright@{s[:10]} ({commits[s].subject[:80]})" for s in shas if s in commits) or "none"
    method: str
    conf: str
    post: Optional[str] = None
    excluded: Set[str] = set()
    extra: Dict[str, object] = {}
    if shas:
        firsts = [_first_release_containing(s) for s in shas]
        known = [f for f in firsts if f]
        if known:
            post = max(known, key=semver_key)
            early = min(known, key=semver_key)
            excluded = {v for v in rels if semver_key(early) <= semver_key(v) < semver_key(post)}
            method, conf = f"{how}; git tag --contains", "high"
            if len(set(known)) > 1:
                extra["fix_spans_releases"] = sorted(set(known), key=semver_key)
                conf = "medium"
    if post is None:
        cv = _comment_version(issue)
        if cv:
            post = cv[0]
            method, conf = f"maintainer comment by {cv[1]} naming the release", "high"
            extra["comment_version"] = cv[0]
    if post is None and shas and fix_date and fix_date > (iso_date(times.get(rels[-1])) or ""):
        return none_mapping(fix_ref, "fix committed after the latest npm release (unreleased)", fix_date, tuple(shas))
    if post is None:
        labeled = _label_time(issue)
        after = [v for v in rels if labeled and (iso_date(times.get(v)) or "") > labeled]
        if after:
            post = after[0]
            method, conf = "first npm release after the 'addressed in next version' label event", "medium"
            extra["label_time"] = labeled
    if post is None and issue.closed_at:
        closed = iso_date(issue.closed_at) or ""
        before = [v for v in rels if (iso_date(times.get(v)) or "") <= closed]
        if before:
            post = before[-1]
            method, conf = "latest npm release published before the issue was closed", "low"
    if post is None:
        return none_mapping(fix_ref, "no fix commit, release comment or close date", fix_date, tuple(shas))
    pre = previous_release(rels, post, excluded)
    in_npm = post in times and pre is not None and pre in times
    notes = f"npm pyright@{pre} ({(times.get(pre) or '')[:10]}) and pyright@{post} ({(times.get(post) or '')[:10]})"
    if not in_npm:
        notes = f"missing on npm: {post if post not in times else pre}"
    elif semver_key(pre or "0") < semver_key(FIRST_NPM_LANGSERVER):
        in_npm = False
        notes += (f"; the npm package ships pyright-langserver only from {FIRST_NPM_LANGSERVER}, so the pre-fix "
                  "language server must come from the VS Code extension of that version or a build of the git tag")
    if fix_date and post in times and (iso_date(times[post]) or "") < fix_date[:19]:
        conf = "low"
        extra["warning"] = "post-fix release published before the fix commit"
    return VersionMapping(fix_ref=fix_ref, fix_shas=tuple(shas), fix_date=fix_date or None,
                          pre_version=pre, post_version=post,
                          pre_date=iso_date(times.get(pre)) if pre else None,
                          post_date=iso_date(times.get(post)),
                          mapping_confidence=conf, mapping_method=method,
                          builds_obtainable=bool(in_npm), build_notes=notes, extra=extra)
