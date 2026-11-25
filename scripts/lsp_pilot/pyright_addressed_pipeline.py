"""pyright "addressed in next version" row (coordinator addition,
2026-09-20): the pyright maintainer often closes a fixed bug by comment,
applying the "addressed in next version" label instead of linking a PR -
which is why the primary pyright row's fixed-bug-candidate rate is so low
(51/3977). This reuses the already-fetched closed "bug"-labeled pyright
rows (config.TARGET_PYRIGHT's result["all_rows"]) and filters client-side
for "addressed in next version" membership: zero extra API calls for the
fetch itself.

Unlike every other row in this pipeline, this row's evidence criterion IS
the label combination, not a linked PR/commit - closing_prs/closer_commit
stay whatever they actually are (often empty/null) and are reported as
extra context, never used to exclude a row.

Run: imported by run_pilot.py, not run directly.
"""
from __future__ import annotations

import logging

import analyze
import fetch_issues
import labels as labels_mod
from config import Target
from fetch_pipeline import new_result

logger = logging.getLogger(__name__)

ADDRESSED_LABEL = "addressed in next version"


def process_pyright_addressed(target: Target, pyright_bug_rows: list[dict]) -> dict:
    """pyright_bug_rows: the full closed 'bug'-labeled JSONL-schema rows
    already produced for config.TARGET_PYRIGHT (not just its fixed-bug
    subset) - reused here instead of a second fetch."""
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
    if ADDRESSED_LABEL not in available:
        result["error"] = f"label '{ADDRESSED_LABEL}' not found on {repo_full}"
        logger.error("%s: %s", target.key, result["error"])
        return result
    result["resolved_bug_labels"] = ["bug", ADDRESSED_LABEL]

    matched_rows = [r for r in pyright_bug_rows if ADDRESSED_LABEL in r["labels"]]
    closer_commit_count = sum(1 for r in matched_rows if r["closer_commit"] is not None)
    result["special_stats"] = {
        "closer_commit_count": closer_commit_count,
        "closer_commit_rate_pct": (
            round(100 * closer_commit_count / len(matched_rows), 1) if matched_rows else 0.0
        ),
    }
    result["notes"].append(
        "bot-closed detection not computed for this row (reuses pyright's "
        "row-schema data, which doesn't carry ClosedEvent actor login)"
    )
    yearly = analyze.yearly_distribution(matched_rows)

    try:
        total_issues, closed_issues = fetch_issues.fetch_counts(target, None)
    except Exception as exc:
        result["error"] = f"counts fetch failed: {exc}"
        logger.exception("%s: counts fetch failed", target.key)
        return result

    result["funnel"] = analyze.TargetFunnel(
        key=target.key,
        repo=repo_full,
        label_repr="bug AND addressed in next version (label evidence, not link evidence)",
        total_issues=total_issues,
        closed_issues=closed_issues,
        closed_bug_labeled=len(matched_rows),
        fixed_bug_candidates=len(matched_rows),
        yearly=yearly,
        notes=tuple(result["notes"]),
    )
    result["fixed_rows"] = matched_rows
    result["all_rows"] = matched_rows
    result["all_rows_count"] = len(matched_rows)
    result["duplicate_labeled_count"] = analyze.count_duplicate_labeled(matched_rows)
    return result
