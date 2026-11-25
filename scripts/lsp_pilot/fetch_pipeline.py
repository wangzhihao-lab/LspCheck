"""Per-target orchestration for every target EXCEPT TypeScript (which needs
the domain-union logic in ts_pipeline.py): labels -> resolve -> counts ->
full fetch -> funnel. Handles both standalone repos and the two
monorepo label-scoped targets (golang/go gopls, llvm/llvm-project clangd),
and the counts-only tier-7 targets.

Run: imported by run_pilot.py, not run directly.
"""
from __future__ import annotations

import logging

import analyze
import fetch_issues
import labels as labels_mod
import special_stats
from config import Target
from label_resolve import resolve_all

logger = logging.getLogger(__name__)


def new_result(target: Target) -> dict:
    return {
        "target": target,
        "notes": [],
        "error": None,
        "special_stats": {},
        "funnel": None,
        "fixed_rows": [],
        "all_rows": [],
        "all_rows_count": 0,
        "available_label_count": 0,
    }


def process_target(target: Target) -> dict:
    result = new_result(target)
    repo_full = f"{target.owner}/{target.name}"

    try:
        available = labels_mod.fetch_labels(target)
    except Exception as exc:
        # Deliberate broad catch: one target's failure must not abort the
        # whole pilot run. Every other target still needs to complete.
        result["error"] = f"label fetch failed: {exc}"
        logger.error("%s: %s", target.key, result["error"])
        return result

    result["available_label_count"] = len(available)
    resolved_bug_labels, notes = resolve_all(available, list(target.bug_labels))
    result["notes"].extend(notes)
    result["resolved_bug_labels"] = resolved_bug_labels

    if resolved_bug_labels is None:
        result["error"] = (
            f"required label(s) {target.bug_labels} not found on {repo_full}; "
            "skipping this target"
        )
        logger.error("%s: %s", target.key, result["error"])
        return result

    try:
        _process_counts_and_fetch(target, repo_full, available, resolved_bug_labels, result)
    except Exception as exc:
        result["error"] = f"fetch/analyze failed: {exc}"
        logger.exception("%s: fetch failed", target.key)

    return result


def _process_counts_and_fetch(
    target: Target,
    repo_full: str,
    available: list[str],
    resolved_bug_labels: list[str],
    result: dict,
) -> None:
    # Scope for total/closed counts: the identifying label itself for the
    # two monorepo targets (there is no dedicated sub-repo to count
    # against, per task spec), otherwise the whole repo (labels=None).
    count_scope_labels = resolved_bug_labels if target.monorepo_label_scope else None
    total_issues, closed_issues = fetch_issues.fetch_counts(target, count_scope_labels)

    if target.counts_only:
        # repository.issues(labels:[...]) is OR/union semantics for >1
        # label (verified empirically, see queries.py); use the search-
        # based AND count whenever more than one label is combined.
        if len(resolved_bug_labels) > 1:
            closed_bug_labeled = fetch_issues.fetch_search_count(target, resolved_bug_labels)
        else:
            _unused_total, closed_bug_labeled = fetch_issues.fetch_counts(target, resolved_bug_labels)
        result["funnel"] = analyze.TargetFunnel(
            key=target.key,
            repo=repo_full,
            label_repr=" AND ".join(resolved_bug_labels),
            total_issues=total_issues,
            closed_issues=closed_issues,
            closed_bug_labeled=closed_bug_labeled,
            fixed_bug_candidates=None,
            yearly={},
            notes=tuple(result["notes"]),
        )
        return

    nodes = fetch_issues.fetch_closed_issues_full(target, resolved_bug_labels, subdir="issues")
    rows = analyze.rows_from_nodes(repo_full, nodes)
    fixed_rows = [r for r in rows if analyze.is_fixed_bug_candidate(r)]
    yearly = analyze.yearly_distribution(fixed_rows)

    result["funnel"] = analyze.TargetFunnel(
        key=target.key,
        repo=repo_full,
        label_repr=" AND ".join(resolved_bug_labels),
        total_issues=total_issues,
        closed_issues=closed_issues,
        closed_bug_labeled=len(rows),
        fixed_bug_candidates=len(fixed_rows),
        yearly=yearly,
        notes=tuple(result["notes"]),
    )
    result["fixed_rows"] = fixed_rows
    # Full closed bug-labeled set (not just the fixed subset), kept so
    # other targets can reuse it without a second fetch - e.g. the pyright
    # "addressed in next version" row filters this client-side instead of
    # re-querying the API.
    result["all_rows"] = rows
    result["all_rows_count"] = len(rows)
    result["bot_closed_count"] = analyze.count_bot_closed(nodes)
    result["duplicate_labeled_count"] = analyze.count_duplicate_labeled(rows)

    if target.key == "golang-go-gopls":
        result["special_stats"] = special_stats.golang_extra_stats(target, available, nodes)
    elif target.key == "pyright":
        result["special_stats"] = special_stats.pyright_extra_stats(target, available)
