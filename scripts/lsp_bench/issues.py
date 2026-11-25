"""Load fixed-bug issues per server, join backfilled fix evidence, clean bodies.

The pilot files hold one GitHub issue per line (number, title, labels,
createdAt, closedAt, closing_prs, closer_commit, body_truncated). pyright is
split over two files (linked-PR bugs and "addressed in next version" bugs);
they are merged by issue number. The backfill files add ``fix_commits`` found
by searching commit messages for the issue number (pyright, gopls).

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from paths import FIX_EVIDENCE_FILES, ISSUE_FILES, MIN_CREATED_AT

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FixCommit:
    """One commit that references the issue (from the backfill search)."""

    hash: str
    date: str
    subject: str
    body: str
    touches_tests: Optional[bool]


@dataclass(frozen=True)
class Issue:
    """A fixed bug report as used by the miner."""

    server: str
    number: int
    url: str
    title: str
    labels: tuple
    created_at: str
    closed_at: str
    body: str
    closing_prs: tuple
    closer_commit: Optional[str]
    fix_commits: tuple = field(default_factory=tuple)

    @property
    def clean_body(self) -> str:
        return clean_body(self.body)


_HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.S)
_DROP_LINE = re.compile(
    r"^\s*(set\s+)?[A-Z][A-Z0-9_]*=.*$"  # go env dumps
    r"|^\s+[\w./~-]+@v[\w.+-]+(\s+h1:\S+)?\s*$"  # module lines of gopls build info
    r"|^\s*(Build info|-{3,}|go: go[0-9.]+.*|golang\.org/x/tools/gopls v\S+)\s*$"
    r"|^(Info|Perf|Err)\s+\d+\s+\[.*$"  # tsserver log lines
)
_TEMPLATE_LINE = re.compile(
    r"^\s*(#+\s*)?(\*\*)?\s*(\W{0,3}\s*)?(Describe the bug|To Reproduce|Expected behaviou?r|Screenshots or Code|"
    r"VS Code extension or command-line|Additional context|rust-analyzer version|rustc version|"
    r"editor or extension|relevant settings|repository link[^\n]*|code snippet to reproduce|"
    r"What version of Go[^\n]*|What operating system[^\n]*|Does this issue reproduce[^\n]*|What did you do\??|"
    r"What did you expect to see\??|What did you see instead\??|gopls version|go env|Go version|"
    r"Output of `go env`[^\n]*|Editor and settings|Logs|Bug Report|Search Terms|"
    r"Version & Regression Information|Playground Link|Code|Actual behaviou?r|"
    r"Additional information about the issue)(\*\*)?:?\s*$",
    re.I,
)


def clean_body(body: str) -> str:
    """Strip issue-template boilerplate, env dumps and logs from a body (line based)."""
    text = _HTML_COMMENT.sub("", body or "")
    text = re.sub(r"!\[[^\]\n]*\]\([^)\n]*\)", "[image]", text)
    text = re.sub(r"<img[^>\n]*>", "[image]", text)
    kept: List[str] = []
    for line in text.splitlines():
        if _DROP_LINE.match(line) or _TEMPLATE_LINE.match(line):
            continue
        kept.append(" ".join(line.split()))
    out = "\n".join(kept)
    out = re.sub(r"```[a-z]*\n?\s*```", "", out)  # fences emptied by the filter
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _read_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_fix_evidence(server: str) -> Dict[int, List[FixCommit]]:
    path = FIX_EVIDENCE_FILES.get(server)
    if path is None or not path.exists():
        return {}
    out: Dict[int, List[FixCommit]] = {}
    for row in _read_jsonl(path):
        commits = [
            FixCommit(
                hash=c["hash"],
                date=c["date"],
                subject=c.get("subject", ""),
                body=c.get("body", ""),
                touches_tests=c.get("touches_tests"),
            )
            for c in row.get("fix_commits") or []
        ]
        out[int(row["number"])] = commits
    return out


def load_issues(server: str) -> List[Issue]:
    """Return the deduplicated issues of one server created on/after the cutoff."""
    merged: Dict[int, dict] = {}
    for path in ISSUE_FILES[server]:
        for row in _read_jsonl(path):
            num = int(row["number"])
            prev = merged.get(num)
            if prev is None:
                merged[num] = row
                continue
            # Keep the richer record: union of labels and closing PRs.
            labels = list(dict.fromkeys(list(prev.get("labels", [])) + list(row.get("labels", []))))
            prs = {p["url"]: p for p in (prev.get("closing_prs") or []) + (row.get("closing_prs") or [])}
            prev = dict(prev)
            prev["labels"] = labels
            prev["closing_prs"] = list(prs.values())
            prev["closer_commit"] = prev.get("closer_commit") or row.get("closer_commit")
            merged[num] = prev
    evidence = _load_fix_evidence(server)
    issues: List[Issue] = []
    for num, row in sorted(merged.items()):
        if (row.get("createdAt") or "") < MIN_CREATED_AT:
            continue
        cc = row.get("closer_commit")
        issues.append(
            Issue(
                server=server,
                number=num,
                url=row["url"],
                title=row.get("title") or "",
                labels=tuple(row.get("labels") or []),
                created_at=row.get("createdAt") or "",
                closed_at=row.get("closedAt") or "",
                body=row.get("body_truncated") or "",
                closing_prs=tuple(
                    (p.get("number"), p.get("url"), bool(p.get("merged")), p.get("mergedAt"))
                    for p in row.get("closing_prs") or []
                ),
                closer_commit=cc.get("oid") if isinstance(cc, dict) else None,
                fix_commits=tuple(evidence.get(num, [])),
            )
        )
    logger.info("%s: %d issues created on/after %s", server, len(issues), MIN_CREATED_AT)
    return issues
