"""Target-specific supplementary stats layered on top of the uniform
funnel (these do NOT change the fixed-bug-candidate definition, which
stays identical across every target for comparability):

- golang/go gopls: BugReport / NeedsFix / FixPending label-combo counts,
  plus a go.dev/cl / golang.org/cl comment-link scan as an alternate "was
  this linked to a fix" proxy signal, since gopls fixes land via Gerrit and
  often never produce a merged PR inside golang/go itself.
- pyright: "addressed in next version" label count, if that label exists.

Run: imported by fetch_pipeline.py, not run directly.
"""
from __future__ import annotations

import logging
import re

import fetch_issues
from config import Target

logger = logging.getLogger(__name__)

CL_LINK_RE = re.compile(r"https?://(?:go\.dev|golang\.org)/cl/\d+")


def _has_label(node: dict, label: str) -> bool:
    return any(l["name"] == label for l in (node.get("labels") or {}).get("nodes", []) or [])


def _has_closer_commit(node: dict) -> bool:
    for item in node.get("timelineItems", {}).get("nodes", []) or []:
        if item.get("__typename") != "ClosedEvent":
            continue
        closer = item.get("closer")
        if closer and closer.get("__typename") == "Commit":
            return True
    return False


def _has_cl_link_in_comments(node: dict) -> bool:
    for c in (node.get("comments") or {}).get("nodes", []) or []:
        if CL_LINK_RE.search(c.get("body") or ""):
            return True
    return False


def golang_extra_stats(target: Target, available_labels: list[str], gopls_nodes: list[dict]) -> dict:
    """gopls_nodes: the full closed 'gopls'-labeled nodes already fetched
    for the primary funnel. Every node already carries its complete label
    list, so the gopls-AND-extra_label counts below are computed by
    client-side filtering over this already-correct superset rather than a
    second API call - repository.issues(labels:[...]) is OR/union
    semantics for >1 label (verified empirically, see queries.py), so a
    naive ["gopls", "BugReport"] filter call would silently return a
    hugely inflated union count instead of the intersection."""
    stats: dict = {}
    label_set = set(available_labels)

    if "BugReport" in label_set:
        stats["gopls_and_BugReport_closed"] = sum(
            1 for n in gopls_nodes if _has_label(n, "BugReport")
        )
    else:
        stats["gopls_and_BugReport_closed"] = None
        stats["BugReport_label_missing"] = True

    for extra_label in ("NeedsFix", "FixPending"):
        key = f"gopls_and_{extra_label}_closed"
        if extra_label in label_set:
            stats[key] = sum(1 for n in gopls_nodes if _has_label(n, extra_label))
        else:
            stats[key] = None

    closer_commit_count = sum(1 for n in gopls_nodes if _has_closer_commit(n))
    cl_link_count = sum(1 for n in gopls_nodes if _has_cl_link_in_comments(n))
    both_count = sum(
        1 for n in gopls_nodes if _has_closer_commit(n) and _has_cl_link_in_comments(n)
    )
    stats["proxy_scan_population"] = len(gopls_nodes)
    stats["closer_commit_proxy_count"] = closer_commit_count
    stats["cl_link_comment_proxy_count"] = cl_link_count
    stats["both_proxies_count"] = both_count
    return stats


def pyright_extra_stats(target: Target, available_labels: list[str]) -> dict:
    label = "addressed in next version"
    if label not in set(available_labels):
        return {"addressed_in_next_version_label_exists": False}
    _total, closed = fetch_issues.fetch_counts(target, [label])
    return {
        "addressed_in_next_version_label_exists": True,
        "addressed_in_next_version_closed_count": closed,
    }
