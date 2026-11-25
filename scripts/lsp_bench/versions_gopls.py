"""gopls: map a golang/go issue to the gopls releases just before / after its fix.

Fix commit: the issue's ``closer_commit`` (golang/tools) if present locally,
else the backfilled commit whose message says "Fixes golang/go#N", else the
latest backfilled commit. Cherry-picks onto ``gopls-release-branch.*`` are
found by subject ("[gopls-release-branch.0.X] <subject>").

A gopls release is (a) the gopls/ subtree at its tag and (b) golang.org/x/tools
at the pseudo-version pinned in gopls/go.mod. A release *contains* a fix when
the fix (or its cherry-pick) is an ancestor of the tag commit and, if the fix
touches files outside gopls/, also of the pinned x/tools commit (for v0.1.x,
which have no tag in the repository, only the pinned commit is used).
post = lowest stable release containing it; pre = highest stable release below
post not containing it. The two nearest tags are confirmed with the GitHub
compare API (base=tag, head=fix: behind/identical = contained).
Build notes: module versions from proxy.golang.org (installable with
``go install golang.org/x/tools/gopls@vX.Y.Z``), the ``go`` directive of each
release's go.mod and the newest Go release at the tag date.

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import gitq
from httpcache import get_json, get_text
from issues import Issue
from overrides import FIX_OVERRIDES
from paths import TOOLS_REPO
from versions_common import (VersionMapping, compare_status, contains_by_compare, iso_date,
                             none_mapping, register_mapper, semver_key)

logger = logging.getLogger(__name__)

PROXY = "https://proxy.golang.org/golang.org/x/tools/gopls/@v"
GO_RELEASES: List[Tuple[str, str]] = [  # (major version, first release date)
    ("1.11", "2018-08-24"), ("1.12", "2019-02-25"), ("1.13", "2019-09-03"), ("1.14", "2020-02-25"),
    ("1.15", "2020-08-11"), ("1.16", "2021-02-16"), ("1.17", "2021-08-16"), ("1.18", "2022-03-15"),
    ("1.19", "2022-08-02"), ("1.20", "2023-02-01"), ("1.21", "2023-08-08"), ("1.22", "2024-02-06"),
    ("1.23", "2024-08-13"), ("1.24", "2025-02-11"),
]
_TOOLCHAIN_INFO = "https://proxy.golang.org/golang.org/toolchain/@v/v0.0.1-go{v}.0.darwin-arm64.info"


@dataclass(frozen=True)
class GoplsRelease:
    version: str
    date: str
    tag_commit: Optional[str]
    pinned_commit: Optional[str]
    go_directive: Optional[str]
    has_replace: bool = False


def _resolve(prefix: str) -> Optional[str]:
    try:
        return gitq.run_git(TOOLS_REPO, ["rev-parse", "--verify", "--quiet", prefix + "^{commit}"]).strip() or None
    except RuntimeError:
        return None


@lru_cache(maxsize=1)
def releases() -> Tuple[GoplsRelease, ...]:
    """All stable gopls releases known to the Go module proxy, ascending."""
    listing = get_text(f"{PROXY}/list") or ""
    versions = sorted((v for v in listing.split() if re.fullmatch(r"v\d+\.\d+\.\d+", v)), key=semver_key)
    tags = gitq.tag_dates(TOOLS_REPO)
    out: List[GoplsRelease] = []
    for v in versions:
        info = get_json(f"{PROXY}/{v}.info") or {}
        mod = get_text(f"{PROXY}/{v}.mod") or ""
        go = re.search(r"^go (\S+)", mod, re.M)
        pin = re.search(r"golang\.org/x/tools v\S+-([0-9a-f]{12})\b", mod)
        tag = f"gopls/{v}"
        tag_commit = _resolve(tag) if tag in tags else (info.get("Origin") or {}).get("Hash")
        out.append(GoplsRelease(version=v, date=iso_date(info.get("Time")) or "", tag_commit=tag_commit,
                                pinned_commit=_resolve(pin.group(1)) if pin else None,
                                go_directive=go.group(1) if go else None,
                                has_replace=bool(re.search(r"^replace\b", mod, re.M))))
    return tuple(out)


@lru_cache(maxsize=1)
def go_release_dates() -> Tuple[Tuple[str, str], ...]:
    """Go major releases with dates; 1.25+ read from the toolchain module on the proxy."""
    rows = list(GO_RELEASES)
    for minor in range(25, 30):
        info = get_json(_TOOLCHAIN_INFO.format(v=f"1.{minor}"))
        if not info:
            break
        rows.append((f"1.{minor}", (iso_date(info.get("Time")) or "")[:10]))
    return tuple(rows)


def go_era(date: str) -> Optional[str]:
    """Newest Go major version released on or before ``date``."""
    era = None
    for ver, d in go_release_dates():
        if d <= (date or "")[:10]:
            era = ver
    return era


@lru_cache(maxsize=1)
def _pick_index() -> Dict[str, List[str]]:
    idx: Dict[str, List[str]] = {}
    for c in gitq.full_log(TOOLS_REPO):
        m = re.match(r"\[gopls-release-branch\.[\d.]+\]\s*(.*)$", c.subject)
        if m:
            idx.setdefault(m.group(1).strip(), []).append(c.sha)
    return idx


@lru_cache(maxsize=4096)
def _touches_outside_gopls(sha: str) -> bool:
    try:
        out = gitq.run_git(TOOLS_REPO, ["show", "--name-only", "--format=", "--no-renames", sha])
    except RuntimeError:
        return True
    paths = [p for p in out.splitlines() if p.strip()]
    return any(not p.startswith("gopls/") for p in paths) if paths else True


def _contains(rel: GoplsRelease, sha: str) -> Optional[bool]:
    outside = _touches_outside_gopls(sha)
    checks: List[Optional[bool]] = []
    if rel.tag_commit:
        checks.append(gitq.is_ancestor(TOOLS_REPO, sha, rel.tag_commit))
    if outside and rel.pinned_commit:
        checks.append(gitq.is_ancestor(TOOLS_REPO, sha, rel.pinned_commit))
    if not checks or any(c is None for c in checks):
        return None
    return all(checks)


def _fix_commits(issue: Issue) -> Tuple[List[str], str]:
    tag = f"golang/go#{issue.number}"
    override = FIX_OVERRIDES.get(("gopls", issue.number))
    if override:
        return [override[0]], "manual override: " + override[1]
    if issue.closer_commit and gitq.commit_exists(TOOLS_REPO, issue.closer_commit):
        return [issue.closer_commit], "closer_commit"
    fixes = [c for c in issue.fix_commits if re.search(rf"Fixes\s+{re.escape(tag)}\b", c.body + c.subject)]
    if fixes:
        return [fixes[-1].hash], "backfill commit with 'Fixes golang/go#N'"
    if issue.fix_commits:
        return [sorted(issue.fix_commits, key=lambda c: c.date)[-1].hash], "latest backfill commit referencing the issue"
    return [], "no fix commit"


def _containing_releases(rels: Tuple[GoplsRelease, ...], shas: List[str], fix_date: str) -> List[GoplsRelease]:
    """Releases containing any of ``shas``, ascending by version.

    Tagged releases come from one ``git tag --contains`` per commit; walking up
    from the lowest one, the pinned x/tools commit is also checked until a
    release passes both (later releases are accepted on tag ancestry alone).
    v0.1.x releases have no tag in the repository and use the pinned commit."""
    tagged = set()
    for s in shas:
        tagged.update(t for t in gitq.tags_containing(TOOLS_REPO, s) if t.startswith("gopls/v"))
    out: List[GoplsRelease] = []
    confirmed = False
    for rel in rels:
        if rel.tag_commit is None:
            if rel.date and fix_date and rel.date[:10] < fix_date[:10]:
                continue
            if rel.pinned_commit and any(gitq.is_ancestor(TOOLS_REPO, s, rel.pinned_commit) for s in shas):
                out.append(rel)
                confirmed = True
            continue
        if f"gopls/{rel.version}" not in tagged:
            continue
        if not confirmed:
            checks = [_contains(rel, s) for s in shas]
            if not (any(c is True for c in checks) or all(c is None for c in checks)):
                continue
            confirmed = True
        out.append(rel)
    return out


@register_mapper("gopls")
def map_gopls(issue: Issue) -> VersionMapping:
    shas, how = _fix_commits(issue)
    if not shas:
        return none_mapping("none", "no golang/tools fix commit found")
    sha = shas[0]
    commit = gitq.commit_index(TOOLS_REPO).get(sha)
    subject = commit.subject if commit else ""
    fix_date = iso_date(commit.date) if commit else None
    picks = _pick_index().get(subject.strip(), []) if subject else []
    rels = releases()
    containing = _containing_releases(rels, [sha] + picks, fix_date or "")
    unknown = 0
    fix_ref = f"golang/tools@{sha[:12]} ({subject[:90]})" + (f"; cherry-picks {', '.join(p[:10] for p in picks)}" if picks else "")
    if not containing:
        return VersionMapping(fix_ref=fix_ref, fix_shas=tuple([sha] + picks), fix_date=fix_date,
                              pre_version=rels[-1].version if rels else None, post_version=None,
                              pre_date=rels[-1].date if rels else None, post_date=None,
                              mapping_confidence="low", mapping_method=f"{how}; no released gopls contains the fix (master only)",
                              builds_obtainable=False, build_notes="post-fix build unreleased (only a master pseudo-version)")
    post = min(containing, key=lambda r: semver_key(r.version))
    below = [r for r in rels if semver_key(r.version) < semver_key(post.version) and r not in containing]
    pre = below[-1] if below else None
    extra: Dict[str, object] = {"cherry_picks": [p[:12] for p in picks], "releases_unknown": unknown}
    agree = True
    for label, rel, expect in (("post", post, True), ("pre", pre, False)):
        if rel is None or not rel.tag_commit:
            continue
        status = compare_status("golang/tools", f"gopls/{rel.version}", sha)
        extra[f"compare_{label}"] = status
        verdict = contains_by_compare(status)
        if verdict is not None and verdict != expect and not (label == "post" and picks):
            agree = False
    conf = "high" if agree and pre is not None else "medium"
    notes = []
    for label, rel in (("pre", pre), ("post", post)):
        if rel is not None:
            rep = " (go.mod has a replace directive: build in a wrapper module)" if rel.has_replace else ""
            notes.append(f"{label} {rel.version}: go.mod go {rel.go_directive}, Go era go{go_era(rel.date)}{rep}")
    method = f"{how}; git ancestry of tag and pinned x/tools commit" + ("; compare API agrees" if agree else "; compare API disagrees on a nearest tag")
    return VersionMapping(fix_ref=fix_ref, fix_shas=tuple([sha] + picks), fix_date=fix_date,
                          pre_version=pre.version if pre else None, post_version=post.version,
                          pre_date=pre.date if pre else None, post_date=post.date,
                          mapping_confidence=conf, mapping_method=method,
                          builds_obtainable=pre is not None,
                          build_notes="; ".join(notes) + "; install: go install golang.org/x/tools/gopls@<version>",
                          extra=extra)
