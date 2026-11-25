"""Turn raw GraphQL issue nodes into JSONL rows, the fixed-bug-candidate
filter, and the yearly distribution.

"fixed bug candidate" = closed bug-labeled issue with >=1 MERGED closing PR
reference OR a ClosedEvent closer commit. This definition is applied
identically for every target so the funnel numbers are comparable.

Run: imported by fetch_pipeline.py / outputs.py, not run directly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from config import BODY_TRUNCATE_CHARS, YEAR_END, YEAR_START

# Anomaly-detection helpers. These read fields that are NOT persisted into
# the JSONL rows (actor login), so they run over raw nodes before/alongside
# row-building, and only their aggregate counts get reported in
# pilot_summary.md.
_BOT_LOGIN_RE = re.compile(r"\[bot\]$|-bot$|^dependabot|^github-actions", re.IGNORECASE)


def _closer_raw(node: dict) -> dict | None:
    for item in node.get("timelineItems", {}).get("nodes", []) or []:
        if item.get("__typename") == "ClosedEvent":
            return item.get("closer")
    return None


def extract_closing_prs(node: dict) -> list[dict]:
    prs: list[dict] = []
    seen = set()
    for p in node.get("closedByPullRequestsReferences", {}).get("nodes", []) or []:
        prs.append(
            {
                "number": p["number"],
                "url": p["url"],
                "merged": bool(p["merged"]),
                "mergedAt": p.get("mergedAt"),
            }
        )
        seen.add(p["number"])
    # Defensive fold-in: the ClosedEvent closer is sometimes a PullRequest
    # not already listed under closedByPullRequestsReferences.
    closer = _closer_raw(node)
    if closer and closer.get("__typename") == "PullRequest" and closer.get("number") not in seen:
        prs.append(
            {
                "number": closer["number"],
                "url": closer["url"],
                "merged": bool(closer.get("merged", False)),
                "mergedAt": None,
            }
        )
    return prs


def extract_closer_commit(node: dict) -> dict | None:
    closer = _closer_raw(node)
    if closer and closer.get("__typename") == "Commit":
        return {"oid": closer["oid"], "url": closer["url"]}
    return None


def build_row(repo_full_name: str, node: dict) -> dict:
    """One JSONL row per task spec's field list."""
    body = node.get("body") or ""
    labels = sorted(l["name"] for l in (node.get("labels", {}).get("nodes") or []))
    return {
        "repo": repo_full_name,
        "number": node["number"],
        "url": node["url"],
        "title": node["title"],
        "labels": labels,
        "createdAt": node["createdAt"],
        "closedAt": node["closedAt"],
        "comments": (node.get("comments") or {}).get("totalCount", 0),
        "reactions": (node.get("reactions") or {}).get("totalCount", 0),
        "closing_prs": extract_closing_prs(node),
        "closer_commit": extract_closer_commit(node),
        "body_truncated": body[:BODY_TRUNCATE_CHARS],
    }


def is_fixed_bug_candidate(row: dict) -> bool:
    has_merged_pr = any(p["merged"] for p in row["closing_prs"])
    return has_merged_pr or row["closer_commit"] is not None


def yearly_distribution(rows: list[dict]) -> dict[str, int]:
    dist = {str(y): 0 for y in range(YEAR_START, YEAR_END + 1)}
    other = 0
    for r in rows:
        closed_at = r.get("closedAt")
        year = None
        if closed_at:
            try:
                year = datetime.fromisoformat(closed_at.replace("Z", "+00:00")).year
            except ValueError:
                year = None
        if year is not None and YEAR_START <= year <= YEAR_END:
            dist[str(year)] += 1
        else:
            other += 1
    dist["other_out_of_range"] = other
    return dist


@dataclass(frozen=True)
class TargetFunnel:
    key: str
    repo: str
    label_repr: str
    total_issues: int
    closed_issues: int
    closed_bug_labeled: int
    fixed_bug_candidates: int | None
    yearly: dict[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


def rows_from_nodes(repo_full_name: str, nodes: list[dict]) -> list[dict]:
    return [build_row(repo_full_name, n) for n in nodes]


def is_closed_by_bot(node: dict) -> bool:
    """True if the ClosedEvent's actor login looks like a bot account
    (e.g. a stale-bot or github-actions[bot] auto-close)."""
    for item in node.get("timelineItems", {}).get("nodes", []) or []:
        if item.get("__typename") != "ClosedEvent":
            continue
        actor = item.get("actor") or {}
        login = actor.get("login") if actor else None
        if login and _BOT_LOGIN_RE.search(login):
            return True
    return False


def count_bot_closed(nodes: list[dict]) -> int:
    return sum(1 for n in nodes if is_closed_by_bot(n))


def count_duplicate_labeled(rows: list[dict]) -> int:
    """Rows carrying a label that looks like 'duplicate' (case-insensitive
    substring match, e.g. 'duplicate', 'Duplicate issue')."""
    return sum(1 for r in rows if any("duplicate" in l.lower() for l in r["labels"]))


def dedupe_by_number(rows: list[dict]) -> list[dict]:
    """Union helper for TypeScript's per-domain sub-queries: same issue can
    carry multiple Domain: labels, so multiple sub-queries can return it."""
    by_number: dict[int, dict] = {}
    for r in rows:
        by_number[r["number"]] = r
    return [by_number[k] for k in sorted(by_number)]
