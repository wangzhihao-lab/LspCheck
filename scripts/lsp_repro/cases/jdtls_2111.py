"""Eclipse JDT LS #2111 -- "Sometimes AST will not be updated after applying and
undoing a code action".

Reported repro (verbatim): "Open a Java file, focus on an unused field." /
"select the light bulb (quick fix), choose 'Generate Setter for ${name}'" /
"keep mouse not moving, undo this change" / "keep mouse not moving, select the
light bulb again, sometimes you will find there is only 'Generate Getter for
${name}' quick fix available, but it will do nothing."

Ground-truth fix: commit 9b065088 "(#2139)", 2022-06-27, released in v1.13.0.
It (a) clears `CodeActionHandler.codeActionStore` on didChange, (b) returns the
codeAction unchanged when the store is empty, and (c) waits for lifecycle jobs
before resolving. So pre-fix, a `codeAction/resolve` issued after an edit is
resolved against a stale AST snapshot held in the store.

Pre-fix 1.12.0 (2022-06-01), post-fix 1.13.0 (2022-06-30).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from javaproj import with_sources  # noqa: E402
from scenario import (  # noqa: E402
    Scenario,
    Step,
    apply_workspace_edit,
    edit,
    open_doc,
    quiesce,
    request,
    snapshot,
    undo,
    wait,
)
from snapshots import norm_code_actions, norm_resolved_action  # noqa: E402
from textdoc import find_range, rng  # noqa: E402

SERVER = "jdtls"
ISSUE = "eclipse-jdtls/eclipse.jdt.ls#2111"
TITLE = "Sometimes AST will not be updated after applying and undoing a code action"
PRE = "1.12.0"
POST = "1.13.0"
SYMPTOM = "codeAction list / resolve go stale after applying and undoing a code action"
FIX_COMMIT = "9b065088 (#2139), 2022-06-27, released in v1.13.0"

REL = "src/app/Person.java"

# The first four variants apply the code action and undo it, so the document is
# back at its original text when the old handle is resolved. That shows the store
# was not cleared, but the stale edit's ranges then coincide with a correct one,
# so it does not show a *wrong* edit. The last three variants separate the two:
# they move the insertion point (or consume it) before resolving the old handle,
# so a stale edit is detectably wrong for the current document.
VARIANTS = [
    "settled",
    "race0",
    "race200",
    "race500",
    "shift_then_stale",
    "shift_outside_then_stale",
    "apply_then_stale",
]

# Inserted at the very top, so every position below moves down. Two lines keeps
# the stale insertion point inside the class body; six lines pushes it above the
# class declaration, where a method cannot legally go.
SHIFT_2 = "// shifted header\n\n"
SHIFT_6 = "// shifted header\n//\n//\n//\n//\n\n"

SRC = """package app;

public class Person {
    private String name;
    private int age;
}
"""


def _field_pos(sess) -> Dict[str, Any]:
    d = sess.doc(REL)
    r = find_range(d.text, "name")
    return {
        "textDocument": {"uri": d.uri},
        "range": r,
        "context": {"diagnostics": []},
    }


def _pick_setter(sess) -> Any:
    """The resolved WorkspaceEdit of the 'Generate Setter' action from ca1."""
    entry = sess.find_request("resolve_setter")
    if not entry:
        raise ValueError("resolve_setter did not succeed")
    return (entry.get("raw") or {}).get("edit")


def _setter_action(sess) -> Any:
    entry = sess.find_request("ca1")
    if not entry:
        raise ValueError("ca1 did not succeed")
    actions = entry.get("raw") or []
    for want in ("Generate Setter for 'name'", "Generate Setter", "setter"):
        for a in actions:
            if isinstance(a, dict) and want.lower() in (a.get("title") or "").lower():
                return a
    raise ValueError(f"no setter action among {[a.get('title') for a in actions if isinstance(a, dict)][:12]}")


def _stale_action(sess) -> Any:
    """Re-resolve the *old* action object after the document has moved on."""
    return _setter_action(sess)


def _fresh_setter_action(sess) -> Any:
    """The setter action from `ca_fresh`, i.e. requested after the shift.

    Same preference order as `_setter_action`, so the stale and the fresh handle
    refer to the same proposal and their ranges are comparable.
    """
    entry = sess.find_request("ca_fresh")
    if not entry:
        raise ValueError("ca_fresh did not succeed")
    actions = entry.get("raw") or []
    for want in ("Generate Setter for 'name'", "Generate Setter", "setter"):
        for a in actions:
            if isinstance(a, dict) and want.lower() in (a.get("title") or "").lower():
                return a
    raise ValueError("no setter action in ca_fresh")


def _stale_edit(sess) -> Any:
    entry = sess.find_request("stale_resolve")
    return (entry.get("raw") or {}).get("edit") if entry else None


def _top_of_file(text: str) -> Dict[str, Dict[str, int]]:
    return rng(0, 0, 0, 0)


def _probe_setter(sess) -> Any:
    """The setter action from the probe's own codeAction request (not from ca1)."""
    entry = sess.find_request("probe_code_actions")
    if not entry:
        raise ValueError("probe_code_actions did not succeed")
    for a in entry.get("raw") or []:
        if isinstance(a, dict) and "setter" in (a.get("title") or "").lower():
            return a
    raise ValueError("no setter action in the probe's codeAction reply")


def _delay_for(variant: str) -> float:
    for token, secs in (("race0", 0.0), ("race200", 0.2), ("race500", 0.5)):
        if variant.endswith(token):
            return secs
    return -1.0


def _shift_steps(shift_text: str) -> List[Step]:
    """Mint the handle, move every position below it, then resolve old vs new."""
    return [
        request("textDocument/codeAction", _field_pos, label="ca1", normalize=norm_code_actions),
        request("codeAction/resolve", _setter_action, label="resolve_setter", normalize=norm_resolved_action),
        edit(REL, _top_of_file, shift_text, label=f"insert {shift_text.count(chr(10))} lines at the top"),
        quiesce(REL),
        snapshot("after_shift"),
        # The old handle, resolved against a document whose lines have all moved.
        request("codeAction/resolve", _stale_action, label="stale_resolve", normalize=norm_resolved_action),
        # The same action requested now, as the ground truth for this document.
        request("textDocument/codeAction", _field_pos, label="ca_fresh", normalize=norm_code_actions),
        request(
            "codeAction/resolve", _fresh_setter_action, label="fresh_resolve", normalize=norm_resolved_action
        ),
        # Apply whatever the stale handle produced and see what the file becomes.
        apply_workspace_edit(_stale_edit, label="apply the stale edit", optional=True),
        quiesce(REL),
        snapshot("after_stale_apply"),
    ]


def _apply_then_stale_steps() -> List[Step]:
    """Mint the handle, consume it, and resolve it again without undoing."""
    return [
        request("textDocument/codeAction", _field_pos, label="ca1", normalize=norm_code_actions),
        request("codeAction/resolve", _setter_action, label="resolve_setter", normalize=norm_resolved_action),
        apply_workspace_edit(_pick_setter, label="apply generate-setter"),
        quiesce(REL),
        snapshot("after_apply"),
        request("codeAction/resolve", _stale_action, label="stale_resolve", normalize=norm_resolved_action),
        apply_workspace_edit(_stale_edit, label="apply the stale edit again", optional=True),
        quiesce(REL),
        snapshot("after_stale_apply"),
    ]


def build(variant: str = "settled") -> Scenario:
    delay = _delay_for(variant)
    steps: List[Step] = [open_doc(REL), quiesce(REL), snapshot("baseline")]
    if variant == "shift_then_stale":
        return _scenario(variant, steps + _shift_steps(SHIFT_2))
    if variant == "shift_outside_then_stale":
        return _scenario(variant, steps + _shift_steps(SHIFT_6))
    if variant == "apply_then_stale":
        return _scenario(variant, steps + _apply_then_stale_steps())
    steps += [
        request("textDocument/codeAction", _field_pos, label="ca1", normalize=norm_code_actions),
        request("codeAction/resolve", _setter_action, label="resolve_setter", normalize=norm_resolved_action),
        apply_workspace_edit(_pick_setter, label="apply generate-setter"),
    ]
    if delay < 0:
        steps += [quiesce(REL), snapshot("after_apply")]
    else:
        if delay > 0:
            steps.append(wait(delay, label=f"race delay {int(delay * 1000)}ms"))
        steps.append(snapshot("after_apply"))
    steps += [
        undo(REL, label="undo the code action", count=0),
        quiesce(REL),
        request("codeAction/resolve", _stale_action, label="stale_resolve"),
        request("textDocument/codeAction", _field_pos, label="ca2", normalize=norm_code_actions),
        snapshot("after_undo"),
    ]
    return _scenario(variant, steps)


def _scenario(variant: str, steps: List[Step]) -> Scenario:
    return Scenario(
        name=f"jdtls_2111[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files=with_sources({REL: SRC}),
        watch=[REL],
        steps=steps,
        quiet_seconds=4.0,
        quiesce_timeout=400.0,
        probes=[
            # The oracle compares the request answers the scenario exercises, not
            # just diagnostics: the action list, and a *freshly requested* action
            # resolved into its edit.
            request(
                "textDocument/codeAction", _field_pos, label="probe_code_actions", normalize=norm_code_actions
            ),
            request(
                "codeAction/resolve",
                _probe_setter,
                label="probe_resolved_setter",
                normalize=norm_resolved_action,
            ),
        ],
    )


def _norm_of(replay: Dict[str, Any], label: str) -> Optional[List]:
    for q in replay.get("requests", []):
        if q["label"] == label and q.get("ok"):
            return q.get("norm")
    return None


def _entry(replay: Dict[str, Any], label: str) -> Optional[Dict[str, Any]]:
    for q in replay.get("requests", []):
        if q["label"] == label and q.get("ok"):
            return q
    return None


_SYNTAX_MARKS = (
    "Syntax error",
    "cannot be resolved",
    "must be defined in its own file",
    "Duplicate method",
    "expected",
    "misplaced construct",
)


def _ranges(norm: Any) -> Any:
    """The edit ranges of a normalized resolved action, or None if it carried none."""
    if not isinstance(norm, dict) or not norm.get("has_edit"):
        return None
    return norm.get("edits") or None


def _wrong_edit_verdict(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    """For the shift variants: is the stale edit wrong for the *current* document?"""
    stale = _entry(replay, "stale_resolve")
    fresh = _entry(replay, "fresh_resolve")
    if stale is None or fresh is None:
        return False, "stale_resolve or fresh_resolve failed -- variant did not arm"
    st_norm, fr_norm = stale.get("norm") or {}, fresh.get("norm") or {}
    sr, fr = _ranges(st_norm), _ranges(fr_norm)
    if st_norm.get("title") and fr_norm.get("title") and st_norm["title"] != fr_norm["title"]:
        return False, (
            f"stale and fresh handles refer to different proposals "
            f"({st_norm['title']!r} vs {fr_norm['title']!r}) -- not comparable"
        )
    if sr is None:
        return False, f"stale resolve returned no edit (store cleared); fresh edit at {fr}"
    if fr is None:
        return False, f"fresh resolve returned no edit -- cannot compare (stale at {sr})"
    reasons = []
    if sr != fr:
        reasons.append(f"stale edit targets {sr} while the correct edit for this document is {fr}")
    applied = [
        d.get("message", "")
        for d in (replay.get("final_raw", {}).get(REL) or [])
        if isinstance(d, dict) and any(k in d.get("message", "") for k in _SYNTAX_MARKS)
    ]
    if applied:
        reasons.append(f"applying it leaves the file broken: {applied[:2]}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    return False, f"stale edit identical to the fresh edit at {sr} -- correct for the current document"


def _duplicate_verdict(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    """For apply_then_stale: would re-resolving the consumed handle add a second setter?"""
    first = _entry(replay, "resolve_setter")
    stale = _entry(replay, "stale_resolve")
    if first is None or stale is None:
        return False, "resolve_setter or stale_resolve failed -- variant did not arm"
    fe, se = _ranges(first.get("norm")), _ranges(stale.get("norm"))
    if se is None:
        return False, f"stale resolve returned no edit (store cleared); the initial edit was at {fe}"
    text = (replay.get("final_text") or {}).get(REL, "")
    setters = text.count("setName")
    dupes = [
        d.get("message", "")
        for d in (replay.get("final_raw", {}).get(REL) or [])
        if isinstance(d, dict) and "Duplicate method" in d.get("message", "")
    ]
    if se == fe:
        return True, (
            f"consumed handle re-resolved to the same edit {se} although the document already "
            f"contains the setter; after applying it the file has {setters} setName members"
            + (f" and reports {dupes[:1]}" if dupes else " (no duplicate-method diagnostic)")
        )
    return True, f"consumed handle still returned an edit, at {se} (initial was {fe})"


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    tag = str(full.get("tag") or "")
    if "shift_then_stale" in tag or "shift_outside_then_stale" in tag:
        return _wrong_edit_verdict(replay, full)
    if "apply_then_stale" in tag:
        return _duplicate_verdict(replay, full)
    # Primary observable: the fix clears `codeActionStore` on didChange and then
    # returns the action untouched, so a resolve whose request id predates the
    # edits must NOT come back carrying an edit. Pre-fix it does, computed from
    # the AST snapshot that the store still held.
    stale = _entry(replay, "stale_resolve")
    if stale is not None:
        res = stale.get("result")
        has_edit = isinstance(res, dict) and bool(res.get("edit"))
        if has_edit:
            changes = (res.get("edit") or {}).get("changes") or (res.get("edit") or {}).get("documentChanges")
            return True, (
                "codeAction/resolve on a request id that predates the apply+undo returned an "
                f"edit from the retained AST: {str(changes)[:180]}"
            )
    ca1 = _norm_of(replay, "ca1")
    ca2 = _norm_of(replay, "ca2")
    if ca1 is None:
        return False, "ca1 request failed -- scenario did not arm"
    if ca2 is None:
        return False, "ca2 request failed"
    s1, s2 = {tuple(x) for x in ca1}, {tuple(x) for x in ca2}
    if s1 != s2:
        missing = sorted(t[0] for t in s1 - s2)
        extra = sorted(t[0] for t in s2 - s1)
        return True, f"codeAction set changed for identical contents; missing={missing[:4]} extra={extra[:4]}"
    if stale is not None and not (isinstance(stale.get("result"), dict) and stale["result"].get("edit")):
        return False, (
            f"stale resolve returned no edit (store cleared) and codeAction set identical ({len(s1)} actions)"
        )
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        return True, f"replay/fresh differ: {list((diff.get('probes') or {}).keys()) or list(diff.get('files', {}))}"
    return False, f"codeAction set identical before/after ({len(s1)} actions) and replay==fresh"
