"""Eclipse JDT LS, commit 25b9fdd4 -- "Always dispose AST on didClose".

Before this change JDT LS did not unconditionally dispose the cached AST of a
document when the client closed it, so a document that was closed while dirty
and then reopened could be served from an AST built from the *previous*
contents. No issue was filed; the commit message is the only ground truth.

Commit 25b9fdd4, 2024-08, first in tag v1.39.0.
Pre-fix 1.38.0 (2024-07-30), post-fix 1.39.0 (2024-08-27).

Scenario: open a file, edit it without saving, close it (so the buffer is
discarded and the on-disk contents are authoritative again), reopen it, and ask
for documentSymbol plus diagnostics. The reopened view must match what a fresh
server reports for the on-disk text.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from javaproj import with_sources  # noqa: E402
from scenario import (  # noqa: E402
    Scenario,
    Step,
    close_doc,
    edit,
    open_doc,
    quiesce,
    request,
    snapshot,
    wait,
)
from textdoc import find_range  # noqa: E402

SERVER = "jdtls"
ISSUE = "eclipse-jdtls/eclipse.jdt.ls@25b9fdd4 (no issue filed)"
TITLE = "AST not disposed on didClose"
PRE = "1.38.0"
POST = "1.39.0"
SYMPTOM = "a document closed while dirty and reopened is served from the pre-close AST"
FIX_COMMIT = "25b9fdd4, 2024-08, first in tag v1.39.0"

REL = "src/app/Shape.java"
VARIANTS = ["close_dirty_settled", "close_dirty_race", "close_dirty_race_fast"]

SRC = """package app;

public class Shape {
    private int width;

    public int area() {
        return width * width;
    }

    public int perimeter() {
        return 4 * width;
    }
}
"""

# The dirty edit adds a method and breaks a type, so a stale AST is visible both
# in documentSymbol (extra member) and in diagnostics (bogus error).
DIRTY = """
    public String broken() {
        return width;
    }
"""


def _before_close_brace(text: str) -> Dict[str, Dict[str, int]]:
    idx = text.rindex("}\n")
    lines = text[:idx].count("\n")
    return {"start": {"line": lines, "character": 0}, "end": {"line": lines, "character": 0}}


def _doc(sess) -> Dict[str, Any]:
    return {"textDocument": {"uri": sess.doc(REL).uri}}


def _norm_symbols(result: Any) -> Any:
    """Flatten (hierarchical) documentSymbol to a sorted name/kind list."""
    out = []

    def walk(items):
        for it in items or []:
            if not isinstance(it, dict):
                continue
            out.append((it.get("name"), it.get("kind")))
            walk(it.get("children"))

    walk(result if isinstance(result, list) else [])
    return sorted(out)


def build(variant: str = "close_dirty_settled") -> Scenario:
    settle = variant.endswith("settled")
    gap = 0.0 if variant.endswith("race_fast") else 0.1
    steps: List[Step] = [
        open_doc(REL),
        quiesce(REL),
        snapshot("baseline"),
        edit(REL, _before_close_brace, DIRTY, label="dirty edit (never saved)"),
    ]
    steps.append(quiesce(REL) if settle else wait(gap))
    steps.append(close_doc(REL, label="close while dirty"))
    steps.append(quiesce() if settle else wait(gap))
    steps.append(open_doc(REL, label="reopen from disk"))
    steps += [quiesce(REL), snapshot("after_reopen")]
    return Scenario(
        name=f"jdtls_c25b9fd[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files=with_sources({REL: SRC}),
        watch=[REL],
        steps=steps,
        quiet_seconds=4.0,
        quiesce_timeout=400.0,
        probes=[
            request("textDocument/documentSymbol", _doc, label="probe_symbols", normalize=_norm_symbols)
        ],
    )


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    # Reopening restores the on-disk text, so the state must equal the baseline.
    snaps = {s["label"]: s["diagnostics"] for s in replay.get("snapshots", [])}
    base = {tuple(x) for x in snaps.get("baseline", {}).get(REL, [])}
    final = {tuple(x) for x in replay.get("final", {}).get(REL, [])}
    probes = replay.get("final_probes", {}) or {}
    fresh_probes = ((full.get("fresh") or {}).get("final_probes") or {})
    reasons = []
    if base != final:
        reasons.append(f"diagnostics differ from the pre-edit state: gained={sorted(final-base)[:2]}")
    if probes.get("probe_symbols") and fresh_probes.get("probe_symbols"):
        if probes["probe_symbols"] != fresh_probes["probe_symbols"]:
            extra = [n for n in probes["probe_symbols"] if n not in fresh_probes["probe_symbols"]]
            reasons.append(f"documentSymbol carries pre-close members: {extra[:3]}")
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        reasons.append(f"replay!=fresh: files={list(diff.get('files', {}))} probes={list(diff.get('probes') or {})}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    return False, "reopened document matches the on-disk text and a fresh server"
