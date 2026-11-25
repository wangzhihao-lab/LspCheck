"""Probe types over derived content: an edit the server offers (edit_breaks_syntax,
edit_leaves_diagnostic), a handle the server minted (stale_code_action) and a
semantics-preserving transformation of the project (transform_differs). Registered in
probes.PROBES; see probes.py for the answer format.

Edit spec (params.edit):
  {"via": "code_action", "path", "title_re", "diagnostic": {code, message_re} | "range": [sl, sc, el, ec],
   "kind": "quickfix" (optional prefix), "missing": "invalid" | "absent"}
  {"via": "completion", "path", "position": [l, c], "label_re", "missing": ...}
  {"via": "format", "path", "options"?} (textDocument/formatting) or
  {"via": "range_format", "path", "range": [sl, sc, el, ec], "options"?} (textDocument/rangeFormatting);
   options are FormattingOptions, default {"tabSize": 4, "insertSpaces": true}
collect.py records in answers["case"]["edit"]: offered, titles, chosen, via, texts_before,
texts_after (changed files only), syntax_before / syntax_after (parse errors per changed
file, "L:C: message"), error (when the edit could not be applied); and in
answers["case"]["diagnostics_before"] the normalized diagnostics of the changed files
before the edit (of the edit's path when the offered edit changes no text). `missing` says
what it means when the server offers no matching edit: "invalid" (default: the probe cannot
be evaluated) or "absent" (for bugs whose fix is to stop offering the action). An offered
edit that changes no text adds no parse error (edit_breaks_syntax: absent) and leaves the
document as it was (edit_leaves_diagnostic: present iff the target was reported before it).

Handle spec (stale_code_action, params.handle): {"path", "title_re", "range": [sl, sc, el, ec] |
"diagnostic": {...}, "kind" (optional prefix), "fresh_range" (optional: the range of the fresh
mint when the ops moved it)}; params.mint_after = the number of ops after which the handle is
minted. collect.py records answers["case"]["handle"] = {"minted", "stale", "fresh"}: minted and
fresh {offered, titles, chosen, resolvable, edit, error, outdated_version}, stale {edit, error,
outdated_version}; edit = the resolved WorkspaceEdit as sorted [path, sl, sc, el, ec, newText]
entries (None when the resolve carried no edit), error = the error code of the resolve.

Transformation spec (params.transform): {"kind": "insert_lines", "path", "line", "text"} (text
ends with a newline; positions at or below `line` shift down by its line count) or
{"kind": "crlf", "path"} (identity mapping). Query positions are given in original lines.

Run line: imported by probes.py; not run directly.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from .probes import (Answers, Probe, ProbeResult, _brief, _result, _session, absent, check_query, diag_matches,
                     error_code, invalid, lost, new_items, present, query_id, register_probe)

RANGE_FIELDS: Dict[str, Tuple[int, ...]] = {  # indexes of line numbers in one normalized item
    "diagnostics": (0, 2), "pull_diagnostics": (0, 2), "documentHighlight": (0, 2), "foldingRange": (0, 2),
    "documentSymbol": (2, 4), "semanticTokens": (0,), "inlayHint": (0,), "definition": (1, 3),
    "typeDefinition": (1, 3), "references": (1, 3)}
LOCATION_METHODS = frozenset({"definition", "typeDefinition", "references"})
EDIT_ROUTES = ("code_action", "completion", "format", "range_format")


def is_range(r: Any) -> bool:
    return isinstance(r, list) and len(r) == 4 and all(isinstance(x, int) and x >= 0 for x in r)


def check_edit(spec: Any) -> List[str]:
    if not isinstance(spec, dict):
        return ["edit: an object is required"]
    errs = []
    if spec.get("via") not in EDIT_ROUTES:
        errs.append("edit.via: " + " | ".join(EDIT_ROUTES))
    if not spec.get("path"):
        errs.append("edit.path missing")
    if spec.get("via") == "code_action" and not (spec.get("title_re") and (spec.get("range") or spec.get("diagnostic"))):
        errs.append("edit: a code action needs title_re and a range or a diagnostic match")
    if spec.get("via") == "completion" and not (spec.get("label_re") and isinstance(spec.get("position"), list)):
        errs.append("edit: a completion needs label_re and position")
    if spec.get("via") == "range_format" and not is_range(spec.get("range")):
        errs.append("edit: range_format needs range [sl, sc, el, ec]")
    if "options" in spec and not isinstance(spec.get("options"), dict):
        errs.append("edit.options: an object (FormattingOptions)")
    if spec.get("missing", "invalid") not in ("invalid", "absent"):
        errs.append("edit.missing: invalid | absent")
    return errs


def changed_lines(e: Mapping[str, Any], limit: int = 6) -> Dict[str, List[str]]:
    """The lines of each edited text that are not in the text before the edit (evidence)."""
    out = {}
    for path, after in (e.get("texts_after") or {}).items():
        before = set(str((e.get("texts_before") or {}).get(path, "")).split("\n"))
        out[path] = [ln for ln in str(after).split("\n") if ln not in before][:limit]
    return out


def _edit(params: Mapping[str, Any], answers: Answers,
          allow_empty: bool = False) -> Tuple[Optional[Mapping[str, Any]], Optional[ProbeResult]]:
    s, bad = _session(answers, "case")
    if bad:
        return None, bad
    e = s.get("edit") or {}
    if not e.get("offered"):
        why = f"no {params['edit']['via']} matching the spec was offered (offered: {list(e.get('titles') or [])[:8]})"
        return None, (absent(why) if params["edit"].get("missing") == "absent" else invalid(why))
    if e.get("error"):
        return None, invalid(f"the offered edit could not be applied: {e['error']}")
    if not e.get("texts_after") and not allow_empty:
        return None, invalid(f"the offered edit {e.get('chosen')!r} changes no text (via {e.get('via')})")
    return e, None


@register_probe("edit_breaks_syntax")
class EditBreaksSyntax(Probe):
    def queries(self, params: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        return {"case": []}

    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        return check_edit(params.get("edit"))

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        e, bad = _edit(params, answers, allow_empty=True)
        if bad:
            return bad
        if not e.get("texts_after"):
            return absent(f"the offered edit {e.get('chosen')!r} changes no text (via {e.get('via')})",
                          chosen=e.get("chosen"), changed={})
        added = {}
        for path in e["texts_after"]:
            new = new_items((e.get("syntax_before") or {}).get(path, []), (e.get("syntax_after") or {}).get(path, []),
                            key=lambda x: re.sub(r"^\d+:\d+: ", "", str(x)))
            if new:
                added[path] = new
        ev = {"chosen": e.get("chosen"), "changed": changed_lines(e)}
        if added:
            return present(f"{e.get('chosen')!r} adds parse errors {added}", errors=added, **ev)
        return absent(f"{e.get('chosen')!r} adds no parse error", **ev)


@register_probe("edit_leaves_diagnostic")
class EditLeavesDiagnostic(Probe):
    sessions = ("case", "after")

    def queries(self, params: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        return {"case": [], "after": []}  # collect.py asks diagnostics of every edited file (and the target file)

    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        t = params.get("target")
        bad = [] if isinstance(t, dict) and (t.get("code") or t.get("message_re")) else [
            "target: {code and/or message_re} of the diagnostic the edit must clear"]
        return check_edit(params.get("edit")) + bad

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        e, bad = _edit(params, answers, allow_empty=True)
        if bad:
            return bad
        if not e.get("texts_after"):
            return self._unchanged(params, answers, e)
        after, bad = _session(answers, "after")
        if bad:
            return bad
        before = answers["case"].get("diagnostics_before") or {}
        errors = lambda xs: [x for x in xs if int(x[4]) == 1]  # noqa: E731
        kept: List[Any] = []
        added: List[Any] = []
        for path, items in sorted((after.get("diagnostics") or {}).items()):
            if not isinstance(items, list) or error_code(items):
                return invalid(f"no diagnostics for {path} after the edit: {items}")
            if path == params["edit"]["path"]:
                kept += [x for x in items if diag_matches(x, params["target"])]
            added += new_items(errors(before.get(path) or []), errors(items), key=lambda x: [x[5], x[7]])
        ev = {"chosen": e.get("chosen"), "changed": changed_lines(e), "kept": kept, "added": added}
        if kept or added:
            return present(f"after {e.get('chosen')!r}: target still reported {len(kept)}x, {len(added)} new error(s)",
                           **ev)
        return absent(f"{e.get('chosen')!r} clears the target and adds no error", **ev)

    @staticmethod
    def _unchanged(params: Mapping[str, Any], answers: Answers, e: Mapping[str, Any]) -> ProbeResult:
        """An offered edit that changes no text leaves the document as it was: the target stays
        iff the case session reported it before the edit."""
        path = str(params["edit"]["path"])
        items = (answers["case"].get("diagnostics_before") or {}).get(path)
        if not isinstance(items, list) or error_code(items):
            return invalid(f"no diagnostics for {path} before the offered edit: {items}")
        kept = [x for x in items if diag_matches(x, params["target"])]
        ev = {"chosen": e.get("chosen"), "changed": {}, "kept": kept, "added": []}
        if kept:
            return present(f"{e.get('chosen')!r} changes no text: target still reported {len(kept)}x", **ev)
        return absent(f"{e.get('chosen')!r} changes no text and the target was not reported before it", **ev)


# ------------------------------------------------------------------ handles (R2)
def check_handle(spec: Any) -> List[str]:
    if not isinstance(spec, dict):
        return ["handle: an object is required"]
    errs = []
    if not spec.get("path"):
        errs.append("handle.path missing")
    if not spec.get("title_re"):
        errs.append("handle.title_re missing")
    if not (is_range(spec.get("range")) or (isinstance(spec.get("diagnostic"), dict) and spec["diagnostic"])):
        errs.append("handle: a range [sl, sc, el, ec] or a diagnostic match is required")
    if "fresh_range" in spec and not is_range(spec.get("fresh_range")):
        errs.append("handle.fresh_range: [sl, sc, el, ec]")
    return errs


@register_probe("stale_code_action")
class StaleCodeAction(Probe):
    """R2 handle validity: a code action minted after ops[:mint_after] and resolved once (as an
    editor does while browsing), the remaining ops, then the OLD action resolved again ("stale")
    and the same action minted and resolved afresh ("fresh"). A stale handle may resolve to an
    error, to no edit, to an edit naming an outdated document version (clients refuse it) or to
    the fresh edit; present iff it resolves to any other edit (also when the fresh mint offers
    no such action or its resolve carries no edit)."""

    def queries(self, params: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        return {"case": []}

    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        errs = check_handle(params.get("handle"))
        k = params.get("mint_after")
        if not (isinstance(k, int) and not isinstance(k, bool) and 1 <= k <= len(ops)):
            errs.append(f"mint_after: the number of ops before the handle is minted, in [1, {len(ops)}]")
        elif not any(o.get("kind") not in ("open", "wait", "request") for o in ops[k:]):
            errs.append("ops after mint_after: needs a change/close/save/config step (else the handle cannot go stale)")
        return errs

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        s, bad = _session(answers, "case")
        if bad:
            return bad
        h = s.get("handle") or {}
        minted, stale, fresh = (dict(h.get(k) or {}) for k in ("minted", "stale", "fresh"))
        if not minted.get("offered"):
            return invalid(f"no code action matching the handle was offered at mint time "
                           f"(offered: {list(minted.get('titles') or [])[:8]})")
        if not minted.get("resolvable"):
            return invalid(f"{minted.get('chosen')!r} carries no data to resolve (no handle)")
        if minted.get("edit") is None:
            return invalid(f"{minted.get('chosen')!r} resolves to no edit even before the ops "
                           f"(error {minted.get('error')})")
        if "edit" not in stale:
            return invalid("the stale handle was not resolved")
        ev = {"chosen": minted.get("chosen"), "minted": _brief(minted.get("edit")), "stale": _brief(stale.get("edit")),
              "fresh": _brief(fresh.get("edit")), "fresh_titles": list(fresh.get("titles") or [])[:12]}
        if stale.get("error") is not None:
            return absent(f"the stale handle is refused with error {stale['error']}", **ev)
        if not stale.get("edit"):
            return absent("the stale handle resolves to no edit", **ev)
        if stale.get("outdated_version"):
            return absent("the stale edit names an outdated document version (clients refuse it)", **ev)
        if fresh.get("edit") is not None and stale["edit"] == fresh["edit"]:
            return absent("the stale handle resolves to the fresh handle's edit", **ev)
        why = ("the fresh mint offers no such action" if not fresh.get("offered") else
               "the fresh action resolves to no edit" if fresh.get("edit") is None else "it differs from the fresh edit")
        return present(f"the stale handle resolves to an edit; {why}", **ev)


# ------------------------------------------------------------------ transformations
def line_shift(transform: Mapping[str, Any]) -> Callable[[int], Optional[int]]:
    """Transformed line -> original line (None inside an inserted block)."""
    if transform.get("kind") != "insert_lines":
        return lambda x: x
    n, at = str(transform.get("text", "")).count("\n"), int(transform.get("line", 0))
    return lambda x: x if x < at else (None if x < at + n else x - n)


def forward_position(transform: Mapping[str, Any], pos: Sequence[int]) -> List[int]:
    """An original position in the transformed copy."""
    if transform.get("kind") != "insert_lines" or pos[0] < int(transform.get("line", 0)):
        return list(pos)
    return [pos[0] + str(transform.get("text", "")).count("\n"), pos[1]]


def map_back(method: str, norm: Any, shift: Callable[[int], Optional[int]], path: str) -> Any:
    """A normalized answer of the transformed copy in original lines (items inside an inserted
    block map to None and stay, so that they still count as a difference)."""
    if method == "hover" and isinstance(norm, list) and len(norm) == 2 and isinstance(norm[1], list):
        r = list(norm[1])
        r[0], r[2] = shift(r[0]), shift(r[2])
        return [norm[0], r]
    fields = RANGE_FIELDS.get(method)
    if not fields or not isinstance(norm, list) or error_code(norm):
        return norm
    out = []
    for item in norm:
        if not isinstance(item, list) or (method in LOCATION_METHODS and item[0] != path):
            out.append(item)
            continue
        item = list(item)
        for i in fields:
            item[i] = shift(item[i])
        out.append(item)
    if method == "semanticTokens":
        return out
    return sorted(out, key=lambda x: json.dumps(x, sort_keys=True))


@register_probe("transform_differs")
class TransformDiffers(Probe):
    sessions = ("fresh", "control", "transformed")

    def queries(self, params: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        qs = list(params.get("queries") or [])
        t = params.get("transform") or {}
        moved = [dict(q, position=forward_position(t, q["position"])) if q.get("path") == t.get("path")
                 and isinstance(q.get("position"), list) else dict(q) for q in qs]
        for q, m in zip(qs, moved):
            m["id"] = query_id(q)  # answers stay keyed by the original query
        return {"fresh": qs, "control": qs, "transformed": moved}

    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        t, errs = params.get("transform"), []
        if not isinstance(t, dict) or t.get("kind") not in ("insert_lines", "crlf") or not t.get("path"):
            errs.append("transform: {kind: insert_lines | crlf, path, line, text}")
        elif t["kind"] == "insert_lines" and not (isinstance(t.get("line"), int) and str(t.get("text", "")).endswith("\n")):
            errs.append("transform.insert_lines needs line and a text ending with a newline")
        for i, q in enumerate(params.get("queries") or [None]):
            errs += check_query(q, f"queries[{i}]")
        if any(o.get("kind") not in ("open", "wait") for o in ops):
            errs.append("ops: only open/wait (the same ops run on both copies; positions are not shifted)")
        return errs

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        sess = {}
        for name in self.sessions:
            s, bad = _session(answers, name)
            if bad:
                return bad
            sess[name] = s
        t = params["transform"]
        shift = line_shift(t)
        diffs, unstable = [], []
        for q in params["queries"]:
            qid = query_id(q)
            f, k, x = (_result(sess[s], qid) for s in self.sessions)
            if lost(f) or lost(k) or lost(x):
                return invalid(f"a session lost {qid}")
            mapped = map_back(q["method"], x, shift, t["path"]) if q["path"] == t["path"] else x
            if f != k:
                unstable.append(qid)
            elif mapped != f:
                diffs.append({"query": qid, "fresh": _brief(f), "transformed": _brief(mapped)})
        if unstable:
            return invalid(f"fresh and control disagree on {unstable}", unstable=unstable)
        if diffs:
            return present(f"{len(diffs)} query(ies) change under the transformation", diffs=diffs)
        return absent("every query is invariant under the transformation")


__all__ = ["EDIT_ROUTES", "RANGE_FIELDS", "changed_lines", "check_edit", "check_handle", "forward_position", "is_range",
           "line_shift", "map_back"]
