"""The four sub-checks of the r4_edits oracle, runnable in any live session (the running
session of run(), the fresh sessions of a confirmation, the case session of a replay).

- completion: at the end of a complete identifier, every identifier-kind item among the
  top R4Config.completion_top items an editor would show (r4_textedits.display_order) is
  accepted offline (positions where renaming the word to word+"x" already breaks the
  syntax are not identifier positions, e.g. the contextual keyword `from`, and are skipped;
  so are items inserting a path prefix such as `module::`, unfinished by design): the item's edit plus additionalTextEdits (the item resolved first
  when the server resolves items and the item has none); a syntax error that the file
  did not have before (oracles/syntax.py, positions ignored) is a finding.
- format: formatting, applied, formatting again must be empty or a no-op; for ts6/ts7
  the non-whitespace character sequence must also survive the first formatting.
- organize: organize imports applied, then organize imports again must be a no-op.
- quickfix: the (resolved or command-followed) edit of a quick fix is applied and the
  session settled; a finding when a diagnostic with the targeted code (message when it
  has no code) is still at the range the edit maps the original range to, or when the
  error-severity diagnostics in the edited files (and the diagnostic's file) increase.

Each check returns Obs records; `answer` re-evaluates an Obs in another session on the
edited content (the fresh confirmation and the replay baseline/control).

Run line: imported by oracles/r4_edits.py; not run directly.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from model import Op, QueryKey  # noqa: E402
from ops import OpError  # noqa: E402
from oracles import r4_session as S  # noqa: E402
from oracles.base import OracleContext  # noqa: E402
from oracles.r4_textedits import (IDENTIFIER_KINDS, EditResult, apply_text_edits, display_order,  # noqa: E402
                                  first_difference, item_edits, map_range, minimal_change, nonws, word_range,
                                  workspace_edit_texts)
from oracles.syntax import error_message, new_errors, syntax_errors, syntax_errors_many  # noqa: E402
from queries import NORMALIZERS  # noqa: E402

logger = logging.getLogger(__name__)
NONWS_FORMAT_KINDS = frozenset({"ts6", "ts7"})  # formatters that must keep every non-whitespace character
PATH_SEPARATORS = ("::", ".", "/")  # an item inserting a trailing separator expects the path to continue


@dataclass(frozen=True)
class R4Config:
    completion_top: int = 20
    diags_per_file: int = 8
    actions_per_diag: int = 3
    mutation_diags: int = 2  # diagnostics created by one seeded mutation whose quick fixes are tried
    checks: Tuple[str, ...] = ("completion", "format", "organize", "quickfix", "mutation")


@dataclass
class Obs:
    """One finding in one session, with what a fresh session needs to re-evaluate it."""

    kind: str  # completion | formatText | format | organize | quickfix
    key: QueryKey
    expected: Any
    actual: Any
    case: Dict[str, Any]  # JSON; enough for replay
    note: str
    edited: Dict[str, str] = field(default_factory=dict)  # content after the edit (empty: judged on the original)
    history: List[Op] = field(default_factory=list)  # session ops up to and including the edit
    open_paths: List[str] = field(default_factory=list)
    check: Dict[str, Any] = field(default_factory=dict)  # quickfix: diag, edit result, base, check kind
    running: Dict[str, Any] = field(default_factory=dict)  # this session's answers, per r1 query key path
    ops: List[Op] = field(default_factory=list)  # the Violation's ops (seeded cases: mutation + fix)


@dataclass
class CheckLog:
    cases: int = 0
    invalid: int = 0
    unsettled: int = 0
    compared: Dict[str, int] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    support: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def count(self, name: str, n: int = 1) -> None:
        self.compared[name] = self.compared.get(name, 0) + n

    def seen(self, check: str, outcome: str) -> None:
        row = self.support.setdefault(check, {})
        row[outcome] = row.get(outcome, 0) + 1


def diag_norm(d: Any, items: List[Dict[str, Any]]) -> Any:
    return NORMALIZERS["diagnostics"](items, d.norm_context(50))


def change_norm(path: str, old: str, new: str) -> List[Any]:
    op = minimal_change(path, old, new)
    return [] if op is None else [path, op.start[0], op.start[1], op.end[0], op.end[1], op.text[:300], len(op.text)]  # type: ignore[index]


def _reader(d: Any) -> Tuple[Callable[[str], Optional[str]], Callable[[str], Optional[str]]]:
    return (lambda p: S.read_doc(d, p)), (lambda u: S.rel_uri(d, u))


# ------------------------------------------------------------------ completion
def check_completion(ctx: OracleContext, d: Any, editor: S.Editor, case: Mapping[str, Any], cfg: R4Config,
                     log: CheckLog, base: Mapping[str, Any]) -> List[Obs]:
    path, line, ch, name = case["path"], int(case["line"]), int(case["character"]), str(case["name"])
    text, timeout = d.text(path), ctx.request_timeout_s
    items, defaults, err = S.completion(d, path, line, ch, timeout)
    log.cases += 1
    if err is not None:
        log.invalid += 1
        log.seen("completion", f"error:{err[1]}")
        return []
    abspath, word, built = os.path.join(ctx.project_dir, path), word_range((line, ch), name), []
    before = syntax_errors(ctx.language, text, abspath)
    renamed = apply_text_edits(text, [{"range": word, "newText": name + "x"}])
    if new_errors(before, syntax_errors(ctx.language, renamed, abspath)):
        log.seen("completion", "not-an-identifier-position")  # e.g. the contextual keyword `from` of an import
        return []
    shown = display_order(items, name)[: cfg.completion_top]
    cands = [i for i in shown if i.get("kind") in IDENTIFIER_KINDS and case.get("label") in (None, i.get("label"))]
    for item in cands:
        if S.resolves_items(d) and not item.get("additionalTextEdits"):
            item, ok = S.resolve_item(d, item, timeout)
            log.seen("completion", "resolved" if ok else "resolve-failed")
        edits = item_edits(item, defaults, word)
        if edits[0]["newText"].rstrip().endswith(PATH_SEPARATORS):  # a path prefix (`module::`): unfinished by design
            log.seen("completion", "path-prefix-item")
            continue
        try:
            built.append((item, edits, apply_text_edits(text, edits)))
        except OpError as exc:
            log.notes.append(f"completion item {item.get('label')!r} at {path}:{line + 1}:{ch + 1}: {exc}")
    afters = syntax_errors_many(ctx.language, [(new, abspath) for _, _, new in built])
    log.count("completionInsert", len(built))
    log.seen("completion", "with-items" if built else "no-identifier-items")
    out = []
    for (item, edits, new), after in zip(built, afters):
        added = new_errors(before, after)
        if not added:
            continue
        label = str(item.get("label", ""))
        err_line = int(added[0].split(":", 1)[0] or 1) - 1
        excerpt = new.splitlines()[err_line] if 0 <= err_line < len(new.splitlines()) else ""
        c = {"kind": "completion", "path": path, "line": line, "character": ch, "name": name, "label": label,
             "item_kind": item.get("kind"), "edits": edits, "new_errors": added[:5], "excerpt": excerpt[:200]}
        note = (f"accepting completion item {label!r} (kind {item.get('kind')}) after {name!r} at "
                f"{path}:{line + 1}:{ch + 1} introduces {added[:2]}")
        out.append(Obs("completion", QueryKey("completionInsert", path, line, ch, label),
                       sorted(error_message(e) for e in before), sorted(error_message(e) for e in after), c, note))
    return out


# ------------------------------------------------------------------ formatting
def check_format(ctx: OracleContext, d: Any, editor: S.Editor, case: Mapping[str, Any], cfg: R4Config,
                 log: CheckLog, base: Mapping[str, Any]) -> List[Obs]:
    path, opts, timeout = case["path"], dict(case["options"]), ctx.request_timeout_s
    text0 = d.text(path)
    e1, err = S.formatting(d, path, opts, timeout)
    log.cases += 1
    if err is not None:
        log.invalid += 1
        log.seen("format", f"error:{err[1]}")
        return []
    try:
        text1 = apply_text_edits(text0, e1 or [])
    except OpError as exc:
        log.invalid += 1
        log.notes.append(f"formatting edits of {path} cannot be applied: {exc}")
        return []
    out: List[Obs] = []
    log.count("formatting")
    log.seen("format", "edits" if text1 != text0 else "no-op")
    fcase = {"kind": "format", "path": path, "options": opts}
    if ctx.server_kind in NONWS_FORMAT_KINDS:
        log.count("formattingText")
        if nonws(text0) != nonws(text1):
            a, b = first_difference(nonws(text0), nonws(text1))
            out.append(Obs("formatText", QueryKey("formattingText", path), [a], [b], dict(fcase, kind="formatText"),
                           f"formatting {path} changes non-whitespace characters: {a!r} -> {b!r}"))
    if text1 == text0 or case.get("kind") == "formatText":
        return out
    ok, applied = editor.change({path: text1})
    if ok:
        e2, err2 = S.formatting(d, path, opts, timeout)
        second = _second_format(path, text1, e2) if err2 is None else []
        if second:
            out.append(Obs("format", QueryKey("formatting", path), [], second, fcase,
                           f"formatting {path} twice: the second formatting still edits {second[:5]}",
                           edited={path: text1}, history=list(editor.history), open_paths=editor.open_paths(),
                           running={path: second}))
    else:
        log.unsettled += 1
    if not editor.revert(applied, []):
        log.unsettled += 1
    return out


def _second_format(path: str, text: str, edits: Optional[List[Dict[str, Any]]]) -> List[Any]:
    try:
        return change_norm(path, text, apply_text_edits(text, edits or []))
    except OpError as exc:
        return [path, "invalid-edits", str(exc)]


# ------------------------------------------------------------------ organize imports
def _organize_second(ctx: OracleContext, d: Any, path: str) -> List[Any]:
    edits, _ = S.organize_edits(d, ctx.server_kind, path, ctx.request_timeout_s)
    try:
        res = workspace_edit_texts(edits, *_reader(d))
    except OpError as exc:
        return [[path, "invalid-edits", str(exc)]]
    return sorted(change_norm(p, res.before[p], t) for p, t in res.texts.items())


def check_organize(ctx: OracleContext, d: Any, editor: S.Editor, case: Mapping[str, Any], cfg: R4Config,
                   log: CheckLog, base: Mapping[str, Any]) -> List[Obs]:
    path = case["path"]
    edits, via = S.organize_edits(d, ctx.server_kind, path, ctx.request_timeout_s)
    log.cases += 1
    log.seen("organize", via)
    if not edits:
        return []
    try:
        res = workspace_edit_texts(edits, *_reader(d))
    except OpError as exc:
        log.invalid += 1
        log.notes.append(f"organize imports edit of {path} cannot be applied: {exc}")
        return []
    log.count("organizeImports")
    if not res.texts:
        log.seen("organize", "no-op")
        return []
    ok, opened = editor.open(list(res.texts))
    ok2, applied = editor.change(res.texts) if ok else (False, [])
    out: List[Obs] = []
    if ok and ok2:
        second = _organize_second(ctx, d, path)
        if second:
            out.append(Obs("organize", QueryKey("organizeImports", path), [], second,
                           {"kind": "organize", "path": path, "via": via},
                           f"organize imports on {path} twice: the second application still edits {second[:3]}",
                           edited=dict(res.texts), history=list(editor.history), open_paths=editor.open_paths(),
                           running={path: second}))
    else:
        log.unsettled += 1
    if not editor.revert(applied, opened):
        log.unsettled += 1
    return out


# ------------------------------------------------------------------ quick fixes
def diag_summary(diag: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: diag.get(k) for k in ("range", "severity", "code", "message")}


def find_diag(items: List[Dict[str, Any]], summary: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    return next((x for x in items if diag_summary(x) == dict(summary)), None)


def _identity(x: Mapping[str, Any]) -> Tuple[str, str]:
    code = x.get("code")
    return ("code", str(code)) if code not in (None, "") else ("message", str(x.get("message", "")))


def _range(x: Mapping[str, Any]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    r = x.get("range") or {}
    s, e = r.get("start") or {}, r.get("end") or {}
    return (int(s.get("line", 0)), int(s.get("character", 0))), (int(e.get("line", 0)), int(e.get("character", 0)))


def evaluate_quickfix(diag: Mapping[str, Any], path: str, res: EditResult, base: Mapping[str, List[Dict[str, Any]]],
                      post: Mapping[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Persisting targeted diagnostics (at the mapped range) and error counts before/after."""
    start, end = _range(diag)
    touched = False
    if path in res.texts:
        start, end, touched = map_range(res.before[path], res.texts[path], res.spans.get(path, []), start, end)
    ident = _identity(diag)

    def at(x: Mapping[str, Any]) -> bool:
        s, e = _range(x)
        return (s, e) == (start, end) if not touched else (start <= s and e <= end)
    errors = lambda m: sum(1 for p in m for x in m[p] if x.get("severity") == 1)  # noqa: E731
    return {"persist": [x for x in post.get(path, []) if _identity(x) == ident and at(x)],
            "base_errors": errors(base), "post_errors": errors(post), "mapped": [list(start), list(end), touched]}


def _zero(norm: Any) -> List[Any]:
    return sorted([0, 0, 0, 0] + list(x[4:]) for x in norm or [])


def quickfix_obs(d: Any, case: Mapping[str, Any], diag: Mapping[str, Any], res: EditResult,
                 base: Mapping[str, List[Dict[str, Any]]], post: Mapping[str, List[Dict[str, Any]]],
                 prefix: str = "") -> Tuple[List[Obs], Dict[str, Any]]:
    """Findings of one applied quick fix (persisting diagnostic; more errors than in `base`) and
    the evaluation; `prefix` starts the key extras (seeded cases: the mutation id)."""
    path, title, kind = case["path"], str(case["title"]), str(case.get("kind", "quickfix"))
    ev = evaluate_quickfix(diag, path, res, base, post)
    (sl, sc), _ = _range(diag)
    out = []
    if ev["persist"]:
        post_norm, keep = diag_norm(d, post[path]), diag_norm(d, ev["persist"])
        c = dict(case, check="persist", mapped=ev["mapped"])
        out.append(Obs(kind, QueryKey("diagnostics", path, sl, sc, f"{prefix}quickfix:{title}"),
                       [x for x in post_norm if x not in keep], post_norm, c,
                       f"quick fix {title!r} for {_identity(diag)[1]} at {path}:{sl + 1}:{sc + 1} leaves the "
                       f"diagnostic at the mapped range {ev['mapped']}"))
    if ev["post_errors"] > ev["base_errors"]:
        errs = lambda m: [x for p in sorted(m) for x in m[p] if x.get("severity") == 1]  # noqa: E731
        c = dict(case, check="errors", base_errors=ev["base_errors"], post_errors=ev["post_errors"])
        out.append(Obs(kind, QueryKey("diagnostics", path, sl, sc, f"{prefix}quickfix-errors:{title}"),
                       _zero(diag_norm(d, errs(base))), _zero(diag_norm(d, errs(post))), c,
                       f"quick fix {title!r} for {_identity(diag)[1]} at {path}:{sl + 1}:{sc + 1} raises the "
                       f"error count in the edited files from {ev['base_errors']} to {ev['post_errors']}"))
    return out, ev


def check_quickfix(ctx: OracleContext, d: Any, editor: S.Editor, case: Mapping[str, Any], cfg: R4Config,
                   log: CheckLog, base: Mapping[str, Any]) -> List[Obs]:
    path, timeout = case["path"], ctx.request_timeout_s
    log.cases += 1
    diag = find_diag(list(base.get(path) or []), case["diag"])
    acts, _ = S.quickfixes(d, path, diag, timeout) if diag is not None else ([], None)
    act = next((a for a in acts if a.get("title") == case["title"] and str(a.get("kind") or "") == case["action_kind"]), None)
    edits, via = S.action_edits(d, act, timeout) if act is not None else ([], "gone")
    log.seen("quickfix", via if edits else f"no-edit:{via}")
    try:
        res = workspace_edit_texts(edits, *_reader(d))
    except OpError as exc:
        res = EditResult(skipped=[f"invalid:{exc}"])
    if diag is None or not res.texts:
        log.invalid += 1
        log.notes.append(f"quick fix {case['title']!r} at {path}: nothing to apply ({via}; skipped {res.skipped[:3]})")
        return []
    checked = sorted(set(res.texts) | {path})
    ok, opened = editor.open(checked)
    before = {p: list(base[p]) if p in base else S.diagnostics(d, p, timeout)[0] for p in checked}
    ok2, applied = editor.change(res.texts) if ok else (False, [])
    out: List[Obs] = []
    if ok and ok2:
        post = {p: S.diagnostics(d, p, timeout)[0] for p in checked}
        log.count("quickfix")
        found, _ = quickfix_obs(d, dict(case, via=via), diag, res, before, post)
        for o in found:
            o.edited, o.history, o.open_paths = dict(res.texts), list(editor.history), editor.open_paths()
            o.check = {"diag": diag, "res": res, "base": before, "checked": checked}
            o.running = {p: diag_norm(d, post[p]) for p in checked}
        out = found
    else:
        log.unsettled += 1
    if not editor.revert(applied, opened):
        log.unsettled += 1
    return out


CHECKS: Dict[str, Callable[..., List[Obs]]] = {
    "completion": check_completion, "format": check_format, "formatText": check_format,
    "organize": check_organize, "quickfix": check_quickfix,
}


# ------------------------------------------------------------------ re-evaluation on edited content
def answer(ctx: OracleContext, d: Any, o: Obs) -> Tuple[List[Obs], Dict[str, Any]]:
    """Re-evaluate an edit-based Obs in session `d`, which holds the edited content with
    o.open_paths open and settled: (findings with the same key, this session's answers)."""
    path = o.key.path
    if o.kind == "format":
        e2, err = S.formatting(d, path, o.case["options"], ctx.request_timeout_s)
        second = _second_format(path, d.text(path), e2) if err is None else ["error", err[1]]
        found = [] if not second or second[0] == "error" else [Obs(o.kind, o.key, [], second, o.case, o.note)]
        return found, {path: second}
    if o.kind == "organize":
        second = _organize_second(ctx, d, path)
        return ([Obs(o.kind, o.key, [], second, o.case, o.note)] if second else []), {path: second}
    post = {p: S.diagnostics(d, p, ctx.request_timeout_s)[0] for p in o.check["checked"]}
    found, _ = quickfix_obs(d, o.case, o.check["diag"], o.check["res"], o.check["base"], post)
    return [f for f in found if f.key == o.key], {p: diag_norm(d, post[p]) for p in post}


__all__ = ["CHECKS", "CheckLog", "NONWS_FORMAT_KINDS", "Obs", "R4Config", "answer", "change_norm", "diag_norm",
           "diag_summary", "evaluate_quickfix", "find_diag", "quickfix_obs"]
