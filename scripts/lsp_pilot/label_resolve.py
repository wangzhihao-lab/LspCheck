"""Resolve a requested label name against a repo's actual label list.

Falls back to a case-insensitive match and records a human-readable
anomaly note whenever the task spec's literal label spelling doesn't exist
verbatim on the repo - this is how "report any [labels] that differ" is
implemented.

Run: imported by fetch_pipeline.py / ts_pipeline.py, not run directly.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedLabel:
    requested: str
    resolved: str | None  # actual label name to query with, or None
    note: str | None


def resolve_label(available_labels: list[str], requested: str) -> ResolvedLabel:
    if requested in available_labels:
        return ResolvedLabel(requested=requested, resolved=requested, note=None)

    lower_map: dict[str, list[str]] = {}
    for a in available_labels:
        lower_map.setdefault(a.lower(), []).append(a)
    matches = lower_map.get(requested.lower(), [])

    if len(matches) == 1:
        note = (
            f"label '{requested}' not found verbatim; using case-insensitive "
            f"match '{matches[0]}' instead"
        )
        return ResolvedLabel(requested=requested, resolved=matches[0], note=note)

    if matches:
        note = f"label '{requested}' ambiguous - multiple case-insensitive matches: {matches}"
    else:
        note = f"label '{requested}' does not exist on this repo (checked case-insensitively too)"
    return ResolvedLabel(requested=requested, resolved=None, note=note)


def resolve_all(
    available_labels: list[str], requested: list[str]
) -> tuple[list[str] | None, list[str]]:
    """Resolve every requested label (they are AND-combined). Returns
    (resolved_label_list, notes). resolved_label_list is None if any
    requested label is unresolvable - the caller should skip the full
    fetch for that combination rather than silently querying a label that
    doesn't exist (which would just return zero results)."""
    resolved: list[str] = []
    notes: list[str] = []
    ok = True
    for r in requested:
        rl = resolve_label(available_labels, r)
        if rl.note:
            notes.append(rl.note)
        if rl.resolved is None:
            ok = False
        else:
            resolved.append(rl.resolved)
    return (resolved if ok else None), notes
