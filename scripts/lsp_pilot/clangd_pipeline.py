"""clangd/clangd-specific orchestration (coordinator addition, 2026-09-20).

clangd's own repo is its primary issue tracker, separate from the
llvm/llvm-project label:clangd row (which is kept as-is, unchanged).
Bug-label resolution:
- if a "bug" label exists (case-insensitive) on clangd/clangd, use it as
  the closed-bug-labeled filter, same pattern as every other single-label
  target.
- otherwise, use ALL closed issues, excluding any that carry a label whose
  name contains "enhancement" or "question" (case-insensitive substring).

clangd fixes land in llvm/llvm-project (cross-repo), so closing usually
happens via a commit message "Fixes clangd/clangd#N" landing as this
issue's ClosedEvent closer commit (captured by the normal query). As a
second proxy, the last 3 comments are scanned for a
github.com/llvm/llvm-project/commit or .../pull link; both counts are
reported (mirrors the golang/go gopls Gerrit-CL proxy pattern).

Run: imported by run_pilot.py, not run directly.
"""
from __future__ import annotations

import logging
import re

import analyze
import fetch_issues
import labels as labels_mod
from config import Target
from fetch_pipeline import new_result

logger = logging.getLogger(__name__)

LLVM_LINK_RE = re.compile(r"github\.com/llvm/llvm-project/(?:commit|pull)/\S+")


def _has_link_in_comments(node: dict, pattern: re.Pattern) -> bool:
    for c in (node.get("comments") or {}).get("nodes", []) or []:
        if pattern.search(c.get("body") or ""):
            return True
    return False


def is_excluded(node: dict) -> bool:
    names = [l["name"].lower() for l in (node.get("labels") or {}).get("nodes", []) or []]
    return any("enhancement" in n or "question" in n for n in names)


def process_clangd_repo(target: Target) -> dict:
    result = new_result(target)
    repo_full = f"{target.owner}/{target.name}"

    try:
        available = labels_mod.fetch_labels(target)
    except Exception as exc:
        # Deliberate broad catch: one target's failure must not abort the
        # whole pilot run.
        result["error"] = f"label fetch failed: {exc}"
        logger.error("%s: %s", target.key, result["error"])
        return result

    result["available_label_count"] = len(available)
    bug_label = next((l for l in available if l.lower() == "bug"), None)

    try:
        total_issues, closed_issues = fetch_issues.fetch_counts(target, None)
        if bug_label:
            result["resolved_bug_labels"] = [bug_label]
            nodes = fetch_issues.fetch_closed_issues_full(target, [bug_label], subdir="issues")
            label_repr = bug_label
        else:
            result["notes"].append(
                "no 'bug' label on clangd/clangd; using all closed issues minus "
                "any labeled enhancement/question"
            )
            result["resolved_bug_labels"] = []
            all_nodes = fetch_issues.fetch_closed_issues_full(target, None, subdir="issues_all")
            nodes = [n for n in all_nodes if not is_excluded(n)]
            label_repr = "ALL CLOSED minus enhancement/question"
    except Exception as exc:
        result["error"] = f"fetch/analyze failed: {exc}"
        logger.exception("%s: fetch failed", target.key)
        return result

    rows = analyze.rows_from_nodes(repo_full, nodes)
    fixed_rows = [r for r in rows if analyze.is_fixed_bug_candidate(r)]
    yearly = analyze.yearly_distribution(fixed_rows)

    closer_commit_count = sum(1 for n in nodes if analyze.extract_closer_commit(n) is not None)
    llvm_link_count = sum(1 for n in nodes if _has_link_in_comments(n, LLVM_LINK_RE))
    both_count = sum(
        1 for n in nodes
        if analyze.extract_closer_commit(n) is not None and _has_link_in_comments(n, LLVM_LINK_RE)
    )
    result["special_stats"] = {
        "proxy_scan_population": len(nodes),
        "closer_commit_proxy_count": closer_commit_count,
        "llvm_link_comment_proxy_count": llvm_link_count,
        "both_proxies_count": both_count,
    }

    result["funnel"] = analyze.TargetFunnel(
        key=target.key,
        repo=repo_full,
        label_repr=label_repr,
        total_issues=total_issues,
        closed_issues=closed_issues,
        closed_bug_labeled=len(rows),
        fixed_bug_candidates=len(fixed_rows),
        yearly=yearly,
        notes=tuple(result["notes"]),
    )
    result["fixed_rows"] = fixed_rows
    result["all_rows_count"] = len(rows)
    result["bot_closed_count"] = analyze.count_bot_closed(nodes)
    result["duplicate_labeled_count"] = analyze.count_duplicate_labeled(rows)
    return result
