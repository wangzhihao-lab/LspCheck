"""Snapshot normalization.

A snapshot is what the server *says* about a workspace at one instant. For the
path-independence oracle to be meaningful, two snapshots must be comparable as
sets, so every server answer is reduced to an order-insensitive canonical form
with volatile fields (ids, absolute paths, request-scoped `data` blobs) stripped.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple


def short(msg: str) -> str:
    """First line of a message, whitespace-collapsed and length-capped."""
    if not msg:
        return ""
    return " ".join(msg.strip().splitlines()[0].split())[:180]


def normalize_diagnostics(diags: Optional[List[Dict[str, Any]]]) -> List[Tuple]:
    """(range, code-or-message, severity) tuples, sorted."""
    if diags is None:
        return []
    out = []
    for d in diags:
        r = d.get("range", {})
        s, e = r.get("start", {}), r.get("end", {})
        code = d.get("code")
        out.append(
            (
                s.get("line"),
                s.get("character"),
                e.get("line"),
                e.get("character"),
                str(code) if code is not None else short(d.get("message", "")),
                d.get("severity"),
            )
        )
    return sorted(out)


def normalize_with_message(diags: Optional[List[Dict[str, Any]]]) -> List[Tuple]:
    """Same, but keyed on the message text instead of the rule code."""
    if diags is None:
        return []
    out = []
    for d in diags:
        r = d.get("range", {})
        s, e = r.get("start", {}), r.get("end", {})
        out.append(
            (
                s.get("line"),
                s.get("character"),
                e.get("line"),
                e.get("character"),
                short(d.get("message", "")),
                d.get("severity"),
            )
        )
    return sorted(out)


# -------------------------------------------------------------- probe results
def norm_code_actions(result: Any) -> List[Tuple]:
    """Sorted (title, kind) pairs. Ignores `data`/`command` ids, which are
    request-scoped and therefore never comparable across sessions."""
    if not isinstance(result, list):
        return []
    out = []
    for a in result:
        if not isinstance(a, dict):
            continue
        out.append((short(a.get("title", "")), a.get("kind") or ""))
    return sorted(out)


def norm_hover(result: Any) -> List[str]:
    if not isinstance(result, dict):
        return []
    c = result.get("contents")
    if isinstance(c, dict):
        return [short(str(c.get("value", "")))]
    if isinstance(c, list):
        vals = []
        for item in c:
            vals.append(short(str(item.get("value", "") if isinstance(item, dict) else item)))
        return sorted(v for v in vals if v)
    return [short(str(c))] if c else []


def norm_locations(result: Any) -> List[Tuple]:
    """Definition/references: (file basename, range), path-prefix independent."""
    items = result if isinstance(result, list) else ([result] if isinstance(result, dict) else [])
    out = []
    for loc in items:
        if not isinstance(loc, dict):
            continue
        uri = loc.get("uri") or loc.get("targetUri") or ""
        rng = loc.get("range") or loc.get("targetSelectionRange") or loc.get("targetRange") or {}
        s, e = rng.get("start", {}), rng.get("end", {})
        out.append(
            (
                os.path.basename(uri),
                s.get("line"),
                s.get("character"),
                e.get("line"),
                e.get("character"),
            )
        )
    return sorted(out)


def norm_completion(result: Any, limit: int = 200) -> List[str]:
    items = result.get("items") if isinstance(result, dict) else result
    if not isinstance(items, list):
        return []
    labels = sorted({short(str(i.get("label", ""))) if isinstance(i, dict) else short(str(i)) for i in items})
    return labels[:limit]


def norm_resolved_action(result: Any) -> Any:
    """A resolved code action reduced to (title, edits) with absolute URIs and
    request-scoped ids removed, so two sessions' answers are comparable."""
    if not isinstance(result, dict):
        return None
    edit = result.get("edit") or {}
    per_file = {}
    for uri, edits in (edit.get("changes") or {}).items():
        per_file[os.path.basename(uri)] = [
            (
                (e.get("range") or {}).get("start", {}).get("line"),
                (e.get("range") or {}).get("start", {}).get("character"),
                (e.get("range") or {}).get("end", {}).get("line"),
                (e.get("range") or {}).get("end", {}).get("character"),
                short(e.get("newText", "")),
            )
            for e in edits
        ]
    for dc in edit.get("documentChanges") or []:
        uri = (dc.get("textDocument") or {}).get("uri") or dc.get("uri") or "?"
        per_file.setdefault(os.path.basename(uri), []).extend(
            (
                (e.get("range") or {}).get("start", {}).get("line"),
                (e.get("range") or {}).get("start", {}).get("character"),
                (e.get("range") or {}).get("end", {}).get("line"),
                (e.get("range") or {}).get("end", {}).get("character"),
                short(e.get("newText", "")),
            )
            for e in (dc.get("edits") or [])
        )
    return {
        "title": short(result.get("title", "")),
        "has_edit": bool(edit),
        "edits": {k: sorted(v) for k, v in sorted(per_file.items())},
    }


def norm_raw(result: Any) -> Any:
    """Fallback: anything JSON-ish, with lists sorted by their repr."""
    if isinstance(result, list):
        return sorted((str(x) for x in result))
    return result


__all__ = [
    "norm_code_actions",
    "norm_completion",
    "norm_hover",
    "norm_locations",
    "norm_resolved_action",
    "norm_raw",
    "normalize_diagnostics",
    "normalize_with_message",
    "short",
]
