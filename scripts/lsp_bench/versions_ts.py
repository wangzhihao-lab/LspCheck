"""tsserver: map a microsoft/TypeScript issue to TypeScript npm releases.

Fix: the merged closing PR(s). The squash commit on main ("title (#PR)") and
any release-branch picks ("Pick PR #PR ... into release-X.Y", "Cherry-pick PR
#PR ...") are located in the local treeless clone; if the squash commit is not
found locally, the pulls API gives ``merge_commit_sha``.
Stable window: post = lowest vX.Y.Z tag containing the squash commit or a
pick; pre = highest stable release below post containing none (only the
JavaScript implementation, versions < 7, is in scope). The two nearest tags
are confirmed with the GitHub compare API (base=tag, head=squash commit).
Nightly window: pre/post nightly = the last / first ``X.Y.Z-dev.YYYYMMDD``
published before / after the merge, checked with the published ``gitHead``
(registry metadata) by git ancestry. tsserver speaks its own protocol, so the
notes name the typescript-language-server release contemporary with the
post-fix build as the suggested LSP wrapper (pairing not tested).

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import gitq
from httpcache import get_json
from issues import Issue
from paths import TS_REPO
from versions_common import (VersionMapping, compare_status, contains_by_compare, iso_date,
                             none_mapping, npm_times, register_mapper, semver_key)

logger = logging.getLogger(__name__)

_STABLE = re.compile(r"^v(\d+)\.\d+\.\d+$")
_DEV = re.compile(r"^(\d+)\.\d+\.\d+-dev\.\d{8}(\.\d+)?$")
_PICK = re.compile(r"(?:Pick PR|[Cc]herry-?pick(?:ed)?(?: of)?(?: PR)?)\s+#(\d+)")


@lru_cache(maxsize=1)
def _picks() -> Dict[int, List[str]]:
    idx: Dict[int, List[str]] = {}
    for c in gitq.full_log(TS_REPO):
        for m in _PICK.finditer(c.subject + "\n" + c.body[:400]):
            idx.setdefault(int(m.group(1)), []).append(c.sha)
    return idx


@lru_cache(maxsize=1)
def stable_tags() -> Tuple[str, ...]:
    tags = [t for t in gitq.tag_dates(TS_REPO) if _STABLE.match(t)]
    return tuple(sorted(tags, key=semver_key))


def _pr_commits(issue: Issue) -> Tuple[List[Tuple[int, str]], List[str], List[str]]:
    """Return ([(pr, squash_sha)], [pick shas], [merged_at])."""
    idx = gitq.pr_index(TS_REPO)
    squash: List[Tuple[int, str]] = []
    picks: List[str] = []
    merged_at: List[str] = []
    for num, url, merged, m_at in issue.closing_prs:
        if not merged or not num or "microsoft/TypeScript/pull/" not in (url or ""):
            continue
        found = [c for c in idx.get(int(num), []) if not _PICK.search(c.subject)]
        if found:
            squash.append((int(num), found[0].sha))
        else:
            pr = get_json(f"https://api.github.com/repos/microsoft/TypeScript/pulls/{num}") or {}
            sha = pr.get("merge_commit_sha")
            if sha and gitq.commit_exists(TS_REPO, sha):
                squash.append((int(num), sha))
            m_at = m_at or pr.get("merged_at")
        picks.extend(_picks().get(int(num), []))
        if m_at:
            merged_at.append(iso_date(m_at) or m_at)
    return squash, picks, merged_at


def _nightly_window(fix_sha: str, merged: str) -> Dict[str, Optional[str]]:
    times = npm_times("typescript")
    devs = sorted((v for v in times if _DEV.match(v) and int(_DEV.match(v).group(1)) < 7),
                  key=lambda v: times[v])
    before = [v for v in devs if (iso_date(times[v]) or "") < merged]
    after = [v for v in devs if (iso_date(times[v]) or "") >= merged]
    out: Dict[str, Optional[str]] = {"pre_nightly": None, "post_nightly": None}
    for label, seq in (("pre_nightly", reversed(before[-3:])), ("post_nightly", after[:4])):
        for v in seq:
            meta = get_json(f"https://registry.npmjs.org/typescript/{v}") or {}
            head = meta.get("gitHead")
            if not head or not gitq.commit_exists(TS_REPO, head):
                continue
            has = gitq.is_ancestor(TS_REPO, fix_sha, head)
            if (label == "pre_nightly" and has is False) or (label == "post_nightly" and has is True):
                out[label] = v
                break
    return out


def lsp_wrapper_for(date: str) -> Optional[str]:
    """Latest stable typescript-language-server published on or before ``date``."""
    times = npm_times("typescript-language-server")
    vs = [v for v in times if re.fullmatch(r"\d+\.\d+\.\d+", v) and (iso_date(times[v]) or "") <= date]
    return max(vs, key=semver_key) if vs else None


@register_mapper("tsserver")
def map_ts(issue: Issue) -> VersionMapping:
    squash, picks, merged_at = _pr_commits(issue)
    if not squash:
        return none_mapping("none", "no merged microsoft/TypeScript PR with a locatable merge commit")
    commits = gitq.commit_index(TS_REPO)
    fix_ref = "; ".join(f"microsoft/TypeScript#{n} ({commits[s].subject[:80] if s in commits else s[:10]})" for n, s in squash)
    fix_date = min(merged_at) if merged_at else iso_date(commits[squash[0][1]].date)
    shas = [s for _, s in squash] + picks
    containing = set()
    for s in shas:
        containing.update(t for t in gitq.tags_containing(TS_REPO, s) if _STABLE.match(t))
    tags = stable_tags()
    times = npm_times("typescript")
    js_tags = [t for t in containing if int(_STABLE.match(t).group(1)) < 7]
    extra: Dict[str, object] = {"picks": [p[:10] for p in picks]}
    extra.update(_nightly_window(squash[0][1], fix_date or ""))
    if not js_tags:
        reason = "fix only in TypeScript 7 (native) releases" if containing else "no released TypeScript contains the fix"
        return VersionMapping(fix_ref=fix_ref, fix_shas=tuple(shas), fix_date=fix_date, pre_version=None,
                              post_version=None, pre_date=None, post_date=None, mapping_confidence="low",
                              mapping_method=reason, builds_obtainable=False, build_notes=reason, extra=extra)
    post_tag = min(js_tags, key=semver_key)
    below = [t for t in tags if semver_key(t) < semver_key(post_tag) and t not in containing]
    pre_tag = below[-1] if below else None
    pre, post = (pre_tag[1:] if pre_tag else None), post_tag[1:]
    agree = True
    for label, tag, expect in (("post", post_tag, True), ("pre", pre_tag, False)):
        if tag is None:
            continue
        status = compare_status("microsoft/TypeScript", tag, squash[0][1])
        extra[f"compare_{label}"] = status
        verdict = contains_by_compare(status)
        if verdict is not None and verdict != expect and not (label == "post" and picks):
            agree = False
    date_ok = bool(fix_date) and (iso_date(times.get(post)) or "") >= (fix_date or "")[:10]
    conf = "high" if agree and date_ok and pre else "medium"
    in_npm = post in times and pre is not None and pre in times
    notes = f"npm typescript@{pre} ({(times.get(pre) or '')[:10]}) and typescript@{post} ({(times.get(post) or '')[:10]})"
    if extra.get("pre_nightly") and extra.get("post_nightly"):
        notes += f"; nightly window {extra['pre_nightly']} -> {extra['post_nightly']}"
    wrapper = lsp_wrapper_for(iso_date(times.get(post)) or "")
    if wrapper:
        notes += f"; LSP access via typescript-language-server@{wrapper} (latest release before the post build; untested pairing)"
    method = "squash commit" + (" + release-branch pick" if picks else "") + "; git tag --contains"
    method += "; compare API agrees" if agree else "; compare API disagrees on a nearest tag"
    return VersionMapping(fix_ref=fix_ref, fix_shas=tuple(shas), fix_date=fix_date, pre_version=pre,
                          post_version=post, pre_date=iso_date(times.get(pre)) if pre else None,
                          post_date=iso_date(times.get(post)), mapping_confidence=conf,
                          mapping_method=method, builds_obtainable=bool(in_npm), build_notes=notes,
                          extra=extra)
