"""Fetch + confirm repo label names before any issue query is built.

Per task spec: "first list the repo's labels via the API and CONFIRM the
exact label names before querying; report any that differ."

Run: imported by fetch_pipeline.py, not run directly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import cache
import gh_client
import queries
from config import Target, raw_target_dir

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LabelCheck:
    requested: str
    exists: bool
    close_matches: tuple[str, ...] = ()


def fetch_labels(target: Target) -> list[str]:
    """All label names for target.owner/target.name, paginated + cached."""
    cursor = None
    page_idx = 0
    names: list[str] = []
    while True:
        cache_path = raw_target_dir(target) / "labels" / f"page_{page_idx:04d}.json"

        def _fetch(cursor=cursor):
            return gh_client.execute(
                queries.LABELS_QUERY,
                {"owner": target.owner, "name": target.name, "cursor": cursor},
            )

        data, _from_cache = cache.cached_call(cache_path, _fetch)
        conn = data["repository"]["labels"]
        names.extend(n["name"] for n in conn["nodes"])
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
        page_idx += 1
    logger.info("%s/%s: %d labels fetched", target.owner, target.name, len(names))
    return names


def confirm_labels(available: list[str], requested: list[str]) -> list[LabelCheck]:
    """Case-exact existence check; surfaces case-insensitive near-matches
    for anything that doesn't exist verbatim, so mismatches are reported
    instead of silently querying a label that returns zero results."""
    available_set = set(available)
    lower_map: dict[str, list[str]] = {}
    for a in available:
        lower_map.setdefault(a.lower(), []).append(a)

    results = []
    for r in requested:
        exists = r in available_set
        close = tuple(lower_map.get(r.lower(), [])) if not exists else ()
        results.append(LabelCheck(requested=r, exists=exists, close_matches=close))
    return results
