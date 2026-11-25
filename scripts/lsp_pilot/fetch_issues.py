"""Core fetch primitives: cheap totalCount-only counts, and full paginated
issue detail fetches. Both are cache-backed so a rerun with warm cache
touches zero network (idempotence).

Two families:
- repository.issues based (fetch_counts / fetch_closed_issues_full): only
  valid for ZERO or ONE label. Repository.issues(labels:[...]) is OR/union
  semantics for >1 label (verified empirically - see queries.py), so these
  raise ValueError if given more than one label, to stop that mistake from
  happening silently again.
- search based (fetch_search_count / fetch_closed_issues_search): true AND
  semantics for any number of labels, via GitHub search's multiple
  `label:"X"` qualifiers.

Run: imported by fetch_pipeline.py / ts_pipeline.py, not run directly.
"""
from __future__ import annotations

import logging
import re
from typing import Sequence

import cache
import gh_client
import queries
from config import Target, raw_target_dir

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]+")


def labels_slug(labels: Sequence[str] | None) -> str:
    if not labels:
        return "none"
    return "_".join(_SLUG_RE.sub("-", label) for label in labels)


def _check_single_label(labels: Sequence[str] | None) -> None:
    if labels and len(labels) > 1:
        raise ValueError(
            f"repository.issues(labels=...) is OR/union semantics for >1 label; "
            f"got {list(labels)}. Use fetch_search_count/fetch_closed_issues_search "
            f"for a true AND, or filter client-side over an already-fetched superset."
        )


def fetch_counts(target: Target, labels: Sequence[str] | None) -> tuple[int, int]:
    """(total_issues, closed_issues) for target.owner/name with zero or one
    label filter. labels=None means the whole repo, unfiltered."""
    _check_single_label(labels)
    cache_path = raw_target_dir(target) / "counts" / f"{labels_slug(labels)}.json"

    def _fetch():
        return gh_client.execute(
            queries.COUNTS_QUERY,
            {
                "owner": target.owner,
                "name": target.name,
                "labels": list(labels) if labels else None,
            },
        )

    data, _from_cache = cache.cached_call(cache_path, _fetch)
    repo = data["repository"]
    return repo["allIssues"]["totalCount"], repo["closedIssues"]["totalCount"]


def fetch_closed_issues_full(
    target: Target,
    labels: Sequence[str] | None,
    subdir: str,
    cache_only: bool = False,
) -> list[dict]:
    """All CLOSED issue nodes (full detail per queries.ISSUE_DETAIL_FIELDS)
    matching zero or one label, paginated 100 at a time and cached one JSON
    file per page under raw/<target>/<subdir>/page_NNNN.json.

    cache_only=True forces a pure cache replay (used by the idempotence
    validation pass) and raises if any page is missing from cache.
    """
    _check_single_label(labels)
    cursor = None
    page_idx = 0
    nodes: list[dict] = []
    label_list = list(labels) if labels else None

    while True:
        cache_path = raw_target_dir(target) / subdir / f"page_{page_idx:04d}.json"

        def _fetch(cursor=cursor):
            return gh_client.execute(
                queries.ISSUES_PAGE_QUERY,
                {
                    "owner": target.owner,
                    "name": target.name,
                    "labels": label_list,
                    "cursor": cursor,
                },
            )

        data, from_cache = cache.cached_call(cache_path, _fetch, cache_only=cache_only)
        conn = data["repository"]["issues"]
        nodes.extend(conn["nodes"])
        logger.info(
            "%s/%s %s: page %d (%s) -> %d nodes (running total %d/%d)",
            target.owner, target.name, subdir, page_idx,
            "cache" if from_cache else "network",
            len(conn["nodes"]), len(nodes), conn["totalCount"],
        )
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
        page_idx += 1

    return nodes


def build_search_query(owner: str, name: str, labels: Sequence[str]) -> str:
    label_terms = " ".join(f'label:"{label}"' for label in labels)
    return f"repo:{owner}/{name} is:issue is:closed {label_terms} sort:created-desc"


def fetch_search_count(target: Target, labels: Sequence[str]) -> int:
    """True AND count for 2+ labels via GitHub search syntax."""
    cache_path = raw_target_dir(target) / "search_counts" / f"{labels_slug(labels)}.json"
    q = build_search_query(target.owner, target.name, labels)

    def _fetch():
        return gh_client.execute(queries.SEARCH_COUNT_QUERY, {"q": q})

    data, _from_cache = cache.cached_call(cache_path, _fetch)
    return data["search"]["issueCount"]


def fetch_closed_issues_search(
    target: Target,
    labels: Sequence[str],
    subdir: str,
    cache_only: bool = False,
) -> list[dict]:
    """All CLOSED issue nodes matching the true AND of 2+ labels, via
    GitHub search, paginated 100 at a time and cached like
    fetch_closed_issues_full."""
    q = build_search_query(target.owner, target.name, labels)
    cursor = None
    page_idx = 0
    nodes: list[dict] = []

    while True:
        cache_path = raw_target_dir(target) / subdir / f"page_{page_idx:04d}.json"

        def _fetch(cursor=cursor):
            return gh_client.execute(queries.SEARCH_ISSUES_PAGE_QUERY, {"q": q, "cursor": cursor})

        data, from_cache = cache.cached_call(cache_path, _fetch, cache_only=cache_only)
        conn = data["search"]
        page_nodes = [n for n in conn["nodes"] if n.get("__typename") == "Issue"]
        nodes.extend(page_nodes)
        logger.info(
            "%s/%s %s: search page %d (%s) -> %d nodes (running total %d/%d)",
            target.owner, target.name, subdir, page_idx,
            "cache" if from_cache else "network",
            len(page_nodes), len(nodes), conn["issueCount"],
        )
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
        page_idx += 1

    return nodes
