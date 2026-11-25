"""microsoft/TypeScript-specific orchestration.

Per coordinator direction (2026-09-20, superseding the pipeline's earlier
"Domain: LS: *" guess): enumerate EVERY "Domain:" label on the live repo
with its closed-issue count, report which of the task spec's original 13
example domain labels exist verbatim (most don't), then define the
language-service subset as domain labels whose name mentions any of
config.TS_LANGUAGE_SERVICE_KEYWORDS (case-insensitive substring match).
Run one closed-issue fetch per (Bug AND domain) combination in that
subset and union the results by issue number.

repository.issues(labels:[...]) is OR/union semantics for >1 label
(verified empirically, see queries.py). Each Bug-AND-domain fetch below
tries the GraphQL `search` root first (true AND via multiple label:
qualifiers); if search keeps failing, it falls back to fetching the
domain alone (single label, always safe) and filtering for the Bug label
client-side.

Run: imported by run_pilot.py, not run directly.
"""
from __future__ import annotations

import logging

import analyze
import fetch_issues
import labels as labels_mod
from config import TS_LANGUAGE_SERVICE_KEYWORDS, TASK_SPEC_GUESS_DOMAINS, Target
from fetch_issues import labels_slug
from fetch_pipeline import new_result
from label_resolve import resolve_label

logger = logging.getLogger(__name__)


def _node_has_label(node: dict, label: str) -> bool:
    return any(l["name"] == label for l in (node.get("labels") or {}).get("nodes", []) or [])


def _matches_keywords(domain_label: str) -> bool:
    lowered = domain_label.lower()
    return any(kw.lower() in lowered for kw in TS_LANGUAGE_SERVICE_KEYWORDS)


def process_typescript(target: Target) -> dict:
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

    bug_resolved = resolve_label(available, target.bug_labels[0])
    if bug_resolved.note:
        result["notes"].append(bug_resolved.note)
    if bug_resolved.resolved is None:
        result["error"] = f"base label '{target.bug_labels[0]}' not found on {repo_full}"
        logger.error("%s: %s", target.key, result["error"])
        return result
    bug_label = bug_resolved.resolved
    result["resolved_bug_labels"] = [bug_label]

    all_domains = sorted(l for l in available if l.startswith("Domain:"))
    result["all_domain_labels"] = all_domains
    result["spec_guess_check"] = [(d, d in available) for d in TASK_SPEC_GUESS_DOMAINS]

    keyword_matched = [d for d in all_domains if _matches_keywords(d)]
    result["keyword_matched_domains"] = keyword_matched
    if not keyword_matched:
        result["notes"].append("no Domain: label matched the language-service keyword list")

    try:
        all_domain_counts = {d: fetch_issues.fetch_counts(target, [d])[1] for d in all_domains}
        per_domain_counts, union_rows, bot_closed_count = _fetch_domain_union(
            target, repo_full, bug_label, keyword_matched
        )
        total_issues, closed_issues = fetch_issues.fetch_counts(target, None)
    except Exception as exc:
        result["error"] = f"fetch/analyze failed: {exc}"
        logger.exception("%s: fetch failed", target.key)
        return result

    result["all_domain_counts"] = all_domain_counts
    result["per_domain_counts"] = per_domain_counts
    # Approximate: summed per-domain sub-query before union dedup, so an
    # issue carrying >1 matched domain label could be counted more than once.
    result["bot_closed_count"] = bot_closed_count
    result["duplicate_labeled_count"] = analyze.count_duplicate_labeled(union_rows)
    fixed_rows = [r for r in union_rows if analyze.is_fixed_bug_candidate(r)]
    yearly = analyze.yearly_distribution(fixed_rows)

    result["funnel"] = analyze.TargetFunnel(
        key=target.key,
        repo=repo_full,
        label_repr=f"{bug_label} AND ({' OR '.join(keyword_matched)})",
        total_issues=total_issues,
        closed_issues=closed_issues,
        closed_bug_labeled=len(union_rows),
        fixed_bug_candidates=len(fixed_rows),
        yearly=yearly,
        notes=tuple(result["notes"]),
    )
    result["fixed_rows"] = fixed_rows
    result["all_rows_count"] = len(union_rows)
    return result


def fetch_bug_domain_rows(
    target: Target, bug_label: str, domain: str, cache_only: bool = False
) -> list[dict]:
    """True Bug-AND-domain intersection. Tries GraphQL `search` first (see
    module docstring); on repeated failure, falls back to fetching the
    domain alone (single label, always safe) and filtering for the Bug
    label client-side - no multi-label OR-semantics pitfall either way.

    cache_only=True forces pure cache replay on both paths (used by the
    idempotence validation pass, which must prove a rerun touches no
    network - it mirrors whichever path the original run actually took)."""
    search_subdir = f"issues_search_{labels_slug([domain])}"
    try:
        return fetch_issues.fetch_closed_issues_search(
            target, [bug_label, domain], subdir=search_subdir, cache_only=cache_only
        )
    except Exception as exc:
        # In cache_only mode this is expected whenever the ORIGINAL run
        # itself used the fallback below (no issues_search_* cache to
        # replay) - fall through and try the fallback's cache instead of
        # giving up immediately; only propagate if that also misses.
        logger.warning(
            "%s: search-based fetch failed for domain %r (%s); falling back to "
            "single-label fetch + client-side Bug filter", target.key, domain, exc,
        )

    fallback_subdir = f"issues_domainonly_{labels_slug([domain])}"
    domain_nodes = fetch_issues.fetch_closed_issues_full(
        target, [domain], subdir=fallback_subdir, cache_only=cache_only
    )
    return [n for n in domain_nodes if _node_has_label(n, bug_label)]


def _fetch_domain_union(
    target: Target, repo_full: str, bug_label: str, domains: list[str]
) -> tuple[dict[str, int], list[dict], int]:
    per_domain_counts: dict[str, int] = {}
    all_rows: list[dict] = []
    bot_closed_total = 0
    for domain in domains:
        nodes = fetch_bug_domain_rows(target, bug_label, domain)
        rows = analyze.rows_from_nodes(repo_full, nodes)
        per_domain_counts[domain] = len(rows)
        all_rows.extend(rows)
        bot_closed_total += analyze.count_bot_closed(nodes)
    union_rows = analyze.dedupe_by_number(all_rows)
    return per_domain_counts, union_rows, bot_closed_total
