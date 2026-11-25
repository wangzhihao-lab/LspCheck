"""Keyword retrieval of candidate issues and screening sheets for manual reading.

For every issue of a server the searched sources are: title, cleaned body,
subjects of fix commits (backfill for pyright/gopls; merge or squash commits of
the closing PRs, found in the local clone, for tsserver/rust-analyzer), and
labels. An issue is *retrieved* when at least one pattern of
``patterns.py`` matches, or when a recall audit found it (``recall_audit.INCLUDE``). The screening sheet lists, per retrieved issue, the
title, labels, pattern hits, fix subject and a body excerpt, so that every
retrieved issue can be read and decided (see ``decisions_*.py``).

Run line: imported by mine_candidates.py (subcommand ``retrieve``), not run directly.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from gitq import Commit, pr_index
from issues import Issue, load_issues
from paths import RA_REPO, SHEETS_DIR, TS_REPO
from patterns import match_labels, match_text
from recall_audit import INCLUDE

logger = logging.getLogger(__name__)

PR_REPOS: Dict[str, Path] = {"tsserver": TS_REPO, "rust-analyzer": RA_REPO}


@dataclass(frozen=True)
class Retrieved:
    """One retrieved issue with its pattern hits."""

    server: str
    number: int
    title: str
    hits: tuple  # (oracle, pattern_id, source, snippet)

    @property
    def classes(self) -> List[str]:
        return sorted({h[0] for h in self.hits})

    @property
    def match_reason(self) -> str:
        return "; ".join(f"{h[1]}@{h[2]}" for h in self.hits)


def fix_subjects(issue: Issue, prs: Dict[int, List[Commit]]) -> List[Tuple[str, str]]:
    """Return (sha, subject+short body) of the fix commits known for an issue."""
    out: List[Tuple[str, str]] = []
    for c in issue.fix_commits:
        out.append((c.hash, c.subject))
    for num, url, merged, _merged_at in issue.closing_prs:
        if not merged or num is None or prs is None:
            continue
        if "/pull/" not in (url or "") or not any(s in url for s in ("microsoft/TypeScript", "rust-lang/rust-analyzer")):
            continue
        for c in prs.get(int(num), []):
            body_first = next((ln for ln in c.body.splitlines() if ln.strip()), "")
            subj = c.subject if not c.subject.startswith(("Merge pull request", "Merge #", "Auto merge")) else body_first
            out.append((c.sha, subj))
    return out


def retrieve(server: str) -> Tuple[List[Issue], List[Retrieved]]:
    """Return all issues of a server and the retrieved subset."""
    issues = load_issues(server)
    prs = pr_index(PR_REPOS[server]) if server in PR_REPOS else {}
    found: List[Retrieved] = []
    for iss in issues:
        subjects = " | ".join(s for _, s in fix_subjects(iss, prs))
        sources = [("title", iss.title.lower()), ("body", iss.clean_body.lower()), ("fix", subjects.lower())]
        hits = match_text(sources) + match_labels(server, iss.labels)
        if not hits and iss.number in INCLUDE.get(server, {}):
            hits = [(INCLUDE[server][iss.number], "audit", "audit", "found by recall audit")]
        if hits:
            found.append(Retrieved(server=server, number=iss.number, title=iss.title, hits=tuple(hits)))
    logger.info("%s: retrieved %d of %d", server, len(found), len(issues))
    return issues, found


def write_sheets(server: str, issues: List[Issue], found: List[Retrieved], chunk: int = 60,
                 body_chars: int = 700, only: Optional[Set[int]] = None, tag: str = "") -> List[Path]:
    """Write numbered text sheets (one block per retrieved issue) for reading.

    ``only`` restricts the sheets to a subset (e.g. issues newly retrieved after
    a pattern revision); ``tag`` is inserted in the sheet file names."""
    SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    by_num = {i.number: i for i in issues}
    prs = pr_index(PR_REPOS[server]) if server in PR_REPOS else {}
    blocks: List[str] = []
    for r in found:
        if only is not None and r.number not in only:
            continue
        iss = by_num[r.number]
        fixes = fix_subjects(iss, prs)
        fix_txt = " || ".join(f"{sha[:9]} {subj[:200]}" for sha, subj in fixes[:3]) or "-"
        fix_body = ""
        if server == "gopls" and iss.fix_commits:
            body = iss.fix_commits[0].body.split("Change-Id:")[0]
            fix_body = " ".join(body.split())[:450]
        excerpt = " ".join(iss.clean_body.split())[:body_chars]
        hits = ", ".join(f"{h[1]}@{h[2]}[{h[3][:40]}]" for h in r.hits)
        blocks.append(
            f"#{iss.number} {iss.title}\n"
            f"  labels: {', '.join(l for l in iss.labels if l not in ('bug', 'C-bug', 'Bug', 'gopls', 'Tools', 'FrozenDueToAge', 'addressed in next version'))}"
            f" | created {iss.created_at[:10]} closed {iss.closed_at[:10]}\n"
            f"  hits: {hits}\n  fix: {fix_txt}\n"
            + (f"  fixmsg: {fix_body}\n" if fix_body else "")
            + f"  body: {excerpt}\n"
        )
    paths: List[Path] = []
    for k in range(0, len(blocks), chunk):
        p = SHEETS_DIR / f"{server}{tag}_{k // chunk:02d}.txt"
        p.write_text("\n".join(blocks[k:k + chunk]), encoding="utf-8")
        paths.append(p)
    if only is not None:
        return paths
    index = SHEETS_DIR / f"{server}_retrieved.jsonl"
    with index.open("w", encoding="utf-8") as f:
        for r in found:
            f.write(json.dumps({**asdict(r), "hits": [list(h) for h in r.hits]}, ensure_ascii=False) + "\n")
    logger.info("%s: %d sheets written", server, len(paths))
    return paths
