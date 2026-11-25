"""Recognize completion items that suggest a symbol not yet imported ("auto-import" items).

Which such items a server offers depends on how warm its symbol index is (pyright, for
example, bounds auto-import lookups by time and count; tsserver and rust-analyzer fill
their import candidates lazily), so they differ between a cold fresh session and a session
that has already answered other queries. That is a legitimate difference, not a history
bug, so the completion normalizer keeps only the other items (design section 10). The
price is that R1 cannot see staleness of auto-import candidates; R4 still checks the edits
of auto-import items from raw responses.

Markers observed per server (any one is enough):
- additionalTextEdits in the unresolved item (pyright; gopls unimported packages);
- data.autoImportText or detail "Auto-import" (pyright);
- data.imports non-empty (rust-analyzer flyimport);
- data.autoImport or data.source (TypeScript 7);
- data.entryNames[*].source (typescript-language-server over tsserver);
- sortText "16", TypeScript's auto-import sort group, together with labelDetails.description;
- sortText "\uffff16" or "\uffffz16" (deprecated): typescript-language-server prefixes tsserver's
  sort text with U+FFFF, and its unresolved items carry only data.cacheId and the module as detail.

Run line: imported by queries.py (norm_completion); not run directly.
"""

from __future__ import annotations

from typing import Any, Dict


def is_auto_import(item: Dict[str, Any]) -> bool:
    """Whether a raw completion item suggests a symbol that is not imported yet."""
    if item.get("additionalTextEdits") or item.get("detail") == "Auto-import":
        return True
    data = item.get("data") if isinstance(item.get("data"), dict) else {}
    if data.get("autoImportText") or data.get("imports") or data.get("autoImport") or data.get("source"):
        return True
    names = data.get("entryNames")
    if isinstance(names, list) and any(isinstance(n, dict) and n.get("source") for n in names):
        return True
    sort = str(item.get("sortText") or "")
    if sort.startswith("\uffff") and sort.lstrip("\uffff").lstrip("z").startswith("16"):
        return True
    return bool((item.get("labelDetails") or {}).get("description")) and sort.startswith("16")


__all__ = ["is_auto_import"]
