"""Predicate library of the benchmark: generic probe types that decide "present" (bug
present), "absent" or "invalid" from normalized answers.

A probe is {"type", "params"} in case.json. collect.py runs the sessions a type names in
`sessions` and hands over the answers; `decide(params, answers)` is pure, so every rule is
unit-tested on synthetic answers. answers: session name -> {"valid": bool, "reason": str,
"results": {query id: normalized answer}, "edit": {...} (edit probes)}. Normalized answers
are those of queries.NORMALIZERS; an error response is ["error", code], a lost request
["error", "timeout"] / ["error", "dead"].

- differs_from_fresh: queries after the ops ("case") vs a fresh session on the content the
  ops leave behind ("fresh"); a second fresh session ("control") must give the same answers,
  else invalid; present iff some query differs.
- error_response: one query after the ops ("case"); present iff it gets an error response
  (with a code in params.codes when given); a timeout or a dead server is invalid.
- edit_breaks_syntax: an edit the server offers (code action, completion item or formatting)
  applied to the text ("case"); present iff it adds a parse error (positions ignored).
- edit_leaves_diagnostic: the same edit, then a fresh session on the edited content
  ("after"); present iff the targeted diagnostic is still reported or an error appears that
  the case session did not report before the edit (code and message, positions ignored).
- diagnostic_present / diagnostic_absent: after the ops ("case"), a diagnostic matching
  params.match is present (false report) / absent (missed report).
- two_routes_differ: two queries of one session ("case") under params.relation (equal,
  subset, highlights_in_references); present iff the relation fails.
- transform_differs: a fresh session on a transformed copy ("transformed": inserted lines or
  LF->CRLF) vs fresh sessions on the original ("fresh", "control"); answers mapped back by
  the line shift; present iff some stable query differs.
- stale_code_action: a code action minted and resolved after the first ops, resolved again
  after the remaining ops ("case"); present iff that stale resolve gives an edit other than
  the one of the same action minted afresh (errors, no edit and outdated versions are allowed).
The edit, handle and transformation types live in probes_derived.py (imported at the end, so
PROBES is complete once this module is imported). `Probe.queries(params)` names the
queries collect.py runs in each session.

Run line: imported by case_format.py, collect.py and run_repro.py; not run directly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

VERDICTS = ("present", "absent", "invalid")
LIVENESS = ("timeout", "dead")
POSITION_METHODS = frozenset({"hover", "definition", "typeDefinition", "references", "documentHighlight",
                              "completion", "signatureHelp", "codeAction"})
FILE_METHODS = frozenset({"diagnostics", "pull_diagnostics", "documentSymbol", "semanticTokens", "inlayHint",
                          "foldingRange"})
QUERY_METHODS = POSITION_METHODS | FILE_METHODS
Answers = Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True)
class ProbeResult:
    verdict: str  # present | absent | invalid
    reason: str
    evidence: Dict[str, Any] = field(default_factory=dict)


def present(reason: str, **ev: Any) -> ProbeResult:
    return ProbeResult("present", reason, ev)


def absent(reason: str, **ev: Any) -> ProbeResult:
    return ProbeResult("absent", reason, ev)


def invalid(reason: str, **ev: Any) -> ProbeResult:
    return ProbeResult("invalid", reason, ev)


# ------------------------------------------------------------------ helpers on normalized answers
def query_id(q: Mapping[str, Any]) -> str:
    if q.get("id"):
        return str(q["id"])
    pos = q.get("position")
    where = f":{pos[0]}:{pos[1]}" if isinstance(pos, (list, tuple)) and len(pos) == 2 else ""
    return f"{q.get('method')}@{q.get('path')}{where}"


def error_code(norm: Any) -> Optional[str]:
    """The code of an error answer ["error", code] as a string, else None."""
    if isinstance(norm, list) and len(norm) == 2 and norm[0] in ("error", "unnormalizable"):
        return str(norm[1])
    return None


def lost(norm: Any) -> bool:
    return error_code(norm) in LIVENESS


def check_query(q: Any, where: str) -> List[str]:
    if not isinstance(q, dict):
        return [f"{where}: a query must be an object"]
    out = []
    if q.get("method") not in QUERY_METHODS:
        out.append(f"{where}: method {q.get('method')!r} not in {sorted(QUERY_METHODS)}")
    if not q.get("path"):
        out.append(f"{where}: path missing")
    pos = q.get("position")
    if q.get("method") in POSITION_METHODS and not (isinstance(pos, list) and len(pos) == 2
                                                    and all(isinstance(x, int) and x >= 0 for x in pos)):
        out.append(f"{where}: {q.get('method')} needs position [line, character]")
    return out


def diag_matches(item: Sequence[Any], match: Mapping[str, Any]) -> bool:
    """A normalized diagnostic [sl, sc, el, ec, severity, code, source, message] against a match spec."""
    if "code" in match and str(item[5]) != str(match["code"]):
        return False
    if "severity" in match and int(item[4]) != int(match["severity"]):
        return False
    if "source" in match and str(item[6]) != str(match["source"]):
        return False
    if "range" in match and list(item[:4]) != list(match["range"]):
        return False
    return not match.get("message_re") or re.search(str(match["message_re"]), str(item[7])) is not None


def new_items(before: Sequence[Any], after: Sequence[Any], key: Callable[[Any], Any]) -> List[Any]:
    """Items of `after` not accounted for by `before` (multiset on key)."""
    budget: Dict[str, int] = {}
    for x in before:
        k = json.dumps(key(x), sort_keys=True)
        budget[k] = budget.get(k, 0) + 1
    out = []
    for x in after:
        k = json.dumps(key(x), sort_keys=True)
        if budget.get(k, 0) > 0:
            budget[k] -= 1
        else:
            out.append(x)
    return out


def _session(answers: Answers, name: str) -> Tuple[Optional[Mapping[str, Any]], Optional[ProbeResult]]:
    s = answers.get(name)
    if not isinstance(s, Mapping):
        return None, invalid(f"session {name!r} missing")
    if not s.get("valid"):
        return None, invalid(f"session {name!r} invalid: {s.get('reason') or 'not settled'}")
    return s, None


def _result(s: Mapping[str, Any], qid: str) -> Any:
    return (s.get("results") or {}).get(qid, ["error", "missing"])


# ------------------------------------------------------------------ probe types
class Probe:
    name = ""
    sessions: Tuple[str, ...] = ("case",)

    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        return []

    def queries(self, params: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Session name -> the queries collect.py runs there after settling."""
        return {name: list(params.get("queries") or []) for name in self.sessions}

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        raise NotImplementedError


PROBES: Dict[str, Probe] = {}


def register_probe(name: str) -> Callable[[type], type]:
    def deco(cls: type) -> type:
        inst = cls()
        inst.name = name
        PROBES[name] = inst
        return cls
    return deco


def _history(ops: Sequence[Mapping[str, Any]]) -> bool:
    return any(o.get("kind") not in ("open", "wait") for o in ops)


@register_probe("differs_from_fresh")
class DiffersFromFresh(Probe):
    sessions = ("case", "fresh", "control")

    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        qs = params.get("queries")
        errs = [] if isinstance(qs, list) and qs else ["queries: a non-empty list is required"]
        for i, q in enumerate(qs or []):
            errs += check_query(q, f"queries[{i}]")
        return errs + ([] if _history(ops) else ["ops: needs an edit/close/config/request step (else trivially equal)"])

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        sess = {}
        for name in self.sessions:
            s, bad = _session(answers, name)
            if bad:
                return bad
            sess[name] = s
        diffs, unstable, seen = [], [], []
        for q in params["queries"]:
            qid = query_id(q)
            c, f, k = (_result(sess[n], qid) for n in self.sessions)
            if lost(f) or lost(k):
                return invalid(f"fresh session lost {qid}: {f if lost(f) else k}")
            if f != k:
                unstable.append(qid)
            elif c != f:
                diffs.append({"query": qid, "fresh": f, "case": c})
            seen.append({"query": qid, "answer": _brief(c, 300)})
        if unstable:
            return invalid(f"fresh and control disagree on {unstable}", unstable=unstable)
        if diffs:
            return present(f"{len(diffs)} query(ies) differ from a fresh session: {[d['query'] for d in diffs]}",
                           diffs=diffs)
        return absent("every query equals the fresh session", answers=seen)


@register_probe("error_response")
class ErrorResponse(Probe):
    def queries(self, params: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        return {"case": [dict(params["query"])]}

    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        codes = params.get("codes", [])
        bad = [] if isinstance(codes, list) else ["codes: must be a list"]
        return check_query(params.get("query"), "query") + bad

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        s, bad = _session(answers, "case")
        if bad:
            return bad
        qid = query_id(params["query"])
        ans = _result(s, qid)
        code = error_code(ans)
        if code in LIVENESS or code == "missing":
            return invalid(f"{qid}: no answer ({code})")
        codes = [str(c) for c in params.get("codes") or []]
        if code is not None and (not codes or code in codes):
            return present(f"{qid} answered with error {code}", answer=ans)
        return absent(f"{qid} answered {'error ' + code if code else 'normally'}", answer=_brief(ans))


def _brief(x: Any, limit: int = 600) -> Any:
    text = json.dumps(x, sort_keys=True, default=str)
    return x if len(text) <= limit else text[:limit] + "..."


def _diag_items(params: Mapping[str, Any], answers: Answers) -> Tuple[Optional[List[Any]], Optional[ProbeResult]]:
    s, bad = _session(answers, "case")
    if bad:
        return None, bad
    items = _result(s, query_id({"method": "diagnostics", "path": params["path"]}))
    if not isinstance(items, list) or error_code(items):
        return None, invalid(f"no diagnostics for {params['path']}: {items}")
    return [x for x in items if diag_matches(x, params["match"])], None


def _check_diag(params: Mapping[str, Any]) -> List[str]:
    ok = params.get("path") and isinstance(params.get("match"), dict) and params["match"]
    return [] if ok else ["path and a non-empty match {code, message_re, severity, range, source} are required"]


class _DiagnosticProbe(Probe):
    def queries(self, params: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        return {"case": [{"method": "diagnostics", "path": params["path"]}]}


@register_probe("diagnostic_present")
class DiagnosticPresent(_DiagnosticProbe):
    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        return _check_diag(params)

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        hits, bad = _diag_items(params, answers)
        if bad:
            return bad
        return present(f"{len(hits)} matching diagnostic(s)", hits=hits) if hits else absent("no matching diagnostic")


@register_probe("diagnostic_absent")
class DiagnosticAbsent(_DiagnosticProbe):
    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        return _check_diag(params)

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        hits, bad = _diag_items(params, answers)
        if bad:
            return bad
        return absent(f"{len(hits)} matching diagnostic(s)", hits=hits) if hits else present("no matching diagnostic")


def _ranges_in(path: str, refs: Sequence[Any]) -> set:
    return {tuple(r[1:5]) for r in refs if isinstance(r, list) and r and r[0] == path}


RELATIONS: Dict[str, Callable[[Any, Any, Mapping[str, Any]], Tuple[bool, Any]]] = {
    "equal": lambda a, b, p: (a == b, None),
    "subset": lambda a, b, p: (not new_items(b, a, key=lambda x: x), new_items(b, a, key=lambda x: x)),
    "highlights_in_references": lambda a, b, p: (
        not [h for h in a if tuple(h[:4]) not in _ranges_in(p["a"]["path"], b)],
        [h for h in a if tuple(h[:4]) not in _ranges_in(p["a"]["path"], b)]),
}


@register_probe("two_routes_differ")
class TwoRoutesDiffer(Probe):
    def queries(self, params: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        return {"case": [dict(params["a"]), dict(params["b"])]}

    def validate(self, params: Mapping[str, Any], ops: Sequence[Mapping[str, Any]]) -> List[str]:
        errs = check_query(params.get("a"), "a") + check_query(params.get("b"), "b")
        if params.get("relation") not in RELATIONS:
            errs.append(f"relation: one of {sorted(RELATIONS)}")
        if params.get("a") == params.get("b"):
            errs.append("a and b are the same query (trivially related)")
        return errs

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        s, bad = _session(answers, "case")
        if bad:
            return bad
        a, b = _result(s, query_id(params["a"])), _result(s, query_id(params["b"]))
        for name, x in (("a", a), ("b", b)):
            if error_code(x) or not isinstance(x, list):
                return invalid(f"route {name} failed or is not a list: {_brief(x)}")
        ok, witness = RELATIONS[params["relation"]](a, b, params)
        ev = {"a": _brief(a), "b": _brief(b)}
        if ok:
            return absent(f"{params['relation']} holds", **ev)
        return present(f"{params['relation']} fails; witness {witness}", witness=witness, **ev)


def decide(probe: Mapping[str, Any], answers: Answers) -> ProbeResult:
    """Dispatch on probe["type"]."""
    p = PROBES.get(str(probe.get("type")))
    if p is None:
        return invalid(f"unknown probe type {probe.get('type')!r}")
    return p.decide(probe.get("params") or {}, answers)


from . import probes_derived  # noqa: E402,F401  (registers the edit and transformation probes)
from . import probes_spec  # noqa: E402,F401  (registers the specification probe edit_text_differs)

__all__ = ["PROBES", "Probe", "ProbeResult", "QUERY_METHODS", "RELATIONS", "VERDICTS", "absent", "check_query",
           "decide", "diag_matches", "error_code", "invalid", "lost", "new_items", "present", "query_id",
           "register_probe"]
