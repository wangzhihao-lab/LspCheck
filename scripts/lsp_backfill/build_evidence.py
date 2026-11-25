"""Shared logic for turning a (issue, matching commit hashes) pair into a
fix-evidence record. Used identically by the pyright and gopls pipelines;
repo-specific matching (which regex patterns, which repo to diff in) is
resolved by the caller into a common shape before reaching this module.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cache import NumstatCache
from git_utils import CommitRaw

ISSUE_KEEP_FIELDS = [
    "repo",
    "number",
    "url",
    "title",
    "labels",
    "createdAt",
    "closedAt",
    "closing_prs",
    "closer_commit",
]


def load_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False))
            f.write("\n")


def parse_iso_z(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def parse_git_ci(s: str) -> datetime:
    # git %ci format: "2026-09-15 23:43:44 +0000"
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z")


def latency_days(created_iso: str, fix_ci: str) -> float | None:
    try:
        d0 = parse_iso_z(created_iso)
        d1 = parse_git_ci(fix_ci)
        return round((d1 - d0).total_seconds() / 86400.0, 3)
    except (ValueError, TypeError):
        return None


def build_commit_record(
    commits_by_hash: dict[str, CommitRaw],
    numstat_cache: NumstatCache,
    repo_dir: Path,
    commit_hash: str,
    this_issue_number: int,
    all_refs_for_commit: set[int],
    matched_patterns: list[str] | None,
) -> dict[str, Any]:
    c = commits_by_hash[commit_hash]
    is_merge = len(c.parents) >= 2
    ns = numstat_cache.get_or_fetch(repo_dir, commit_hash, is_merge)
    touches_tests = any("test" in f.lower() for f in ns.files)
    record: dict[str, Any] = {
        "hash": commit_hash,
        "date": c.date,
        "subject": c.subject,
        "body": c.body,
        "files_changed": len(ns.files),
        "insertions": ns.insertions,
        "deletions": ns.deletions,
        "touches_tests": touches_tests,
        "is_merge": is_merge,
        "numstat_fetch_failed": ns.fetch_failed,
        "other_issues_mentioned": sorted(n for n in all_refs_for_commit if n != this_issue_number),
        "multi_issue_commit": len(all_refs_for_commit) > 1,
    }
    if matched_patterns is not None:
        record["matched_patterns"] = matched_patterns
    return record


def build_issue_evidence(
    issue: dict,
    hash_entries: list[tuple[str, list[str] | None]],
    commits_by_hash: dict[str, CommitRaw],
    forward_sets: dict[str, set[int]],
    numstat_cache: NumstatCache,
    repo_dir: Path,
) -> dict[str, Any]:
    seen: set[str] = set()
    unique_entries: list[tuple[str, list[str] | None]] = []
    for h, pats in hash_entries:
        if h not in seen:
            seen.add(h)
            unique_entries.append((h, pats))

    fix_commits = [
        build_commit_record(
            commits_by_hash,
            numstat_cache,
            repo_dir,
            h,
            issue["number"],
            forward_sets.get(h, set()),
            pats,
        )
        for h, pats in unique_entries
    ]
    # Secondary key (hash) makes ties on same-second committer dates
    # deterministic and explicit rather than an accident of git log's
    # internal (reverse-chronological) traversal order.
    fix_commits.sort(key=lambda r: (parse_git_ci(r["date"]), r["hash"]))

    result: dict[str, Any] = {k: issue.get(k) for k in ISSUE_KEEP_FIELDS}
    result["fix_commits"] = fix_commits
    result["n_fix_commits"] = len(fix_commits)

    if fix_commits:
        first = fix_commits[0]
        result["first_fix_date"] = first["date"]
        result["files_changed"] = first["files_changed"]
        result["insertions"] = first["insertions"]
        result["deletions"] = first["deletions"]
        result["touches_tests"] = first["touches_tests"]
        result["fix_latency_days"] = latency_days(issue["createdAt"], first["date"])
    else:
        result["first_fix_date"] = None
        result["files_changed"] = None
        result["insertions"] = None
        result["deletions"] = None
        result["touches_tests"] = None
        result["fix_latency_days"] = None

    result["multi_issue_commit"] = any(r["multi_issue_commit"] for r in fix_commits)
    return result


def top_referenced_commits(evidence_list: list[dict], top_n: int = 20) -> list[dict]:
    """Commits that show up as a fix commit for many issues in this result
    set -- typically release-note or bulk-fix commits worth excluding from
    per-issue fix-latency analysis."""
    agg: dict[str, dict[str, Any]] = {}
    for ev in evidence_list:
        for fc in ev["fix_commits"]:
            h = fc["hash"]
            entry = agg.setdefault(
                h, {"hash": h, "date": fc["date"], "subject": fc["subject"], "issue_numbers": set()}
            )
            entry["issue_numbers"].add(ev["number"])
    ranked = sorted(agg.values(), key=lambda e: len(e["issue_numbers"]), reverse=True)[:top_n]
    return [
        {
            "hash": e["hash"],
            "date": e["date"],
            "subject": e["subject"],
            "n_issues_referenced": len(e["issue_numbers"]),
            "sample_issue_numbers": sorted(e["issue_numbers"])[:15],
        }
        for e in ranked
    ]
