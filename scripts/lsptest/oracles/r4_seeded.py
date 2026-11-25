"""Seeded quick fixes for the r4_edits oracle: a mutation (oracles/r4_mutations.py) plants a
fixable error in a clean target file; the quick fixes offered on the diagnostics it
created are applied one at a time and checked.

Running session (check_mutation): the mutation is applied as one change op and settled;
the diagnostics it created are those of the mutated file that no diagnostic of the
fresh pre-mutation base accounts for (same code, or message without one, at the range
carried through the mutation). Pre-existing diagnostics are never targeted. For up to
R4Config.mutation_diags created diagnostics (errors first) and R4Config.actions_per_diag
quick fixes each, the fix's edit is applied (r4_session.action_edits: edit, resolve, or
an edit-only command), settled and checked; then the fix and at last the mutation are
reverted. A finding is:
- persist: the targeted diagnostic is still at the range the fix maps it to;
- errors: the error-severity diagnostics of the edited files (and the target) exceed
  their count BEFORE the mutation (both counts recorded as base_errors / post_errors);
- syntax: the syntax classifier reports a parse error the pre-mutation text did not have.

The Violation's ops are the whole case: open of the target, the mutation op, then the
fix's ops (opens of other edited files and one change op per edited document); the case
records how many trailing ops are the fix. mutation_case_session replays such ops in a
fresh session: it applies the ops before the fix (the pre-mutation base is taken after
the opens), finds the targeted diagnostic, asks for the same action (title and kind),
applies the server's current edit and checks; ops that do not end with the recorded fix
cannot reproduce the case, so reduce.py keeps the fix.

Run line: imported by oracles/r4_edits.py; not run directly.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from model import Op, QueryKey  # noqa: E402
from ops import OpError  # noqa: E402
from oracles import r4_session as S  # noqa: E402
from oracles.base import OracleContext, session  # noqa: E402
from oracles.r4_checks import (CheckLog, Obs, R4Config, _identity, _range, _reader, diag_norm,  # noqa: E402
                               diag_summary, find_diag, quickfix_obs)
from oracles.r4_textedits import EditResult, Span, map_range, workspace_edit_texts  # noqa: E402
from oracles.syntax import error_message, new_errors, syntax_errors  # noqa: E402

logger = logging.getLogger(__name__)


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]


def created_diagnostics(before: Sequence[Mapping[str, Any]], after: Sequence[Dict[str, Any]], old: str, new: str,
                        spans: Sequence[Span]) -> List[Dict[str, Any]]:
    """Diagnostics of the edited text that no diagnostic of the text before accounts for (same
    identity at its range carried through the edit spans), errors first, then by position."""
    pool = []
    for b in before:
        s, e = _range(b)
        ms, me, _ = map_range(old, new, spans, s, e)
        pool.append((_identity(b), (ms, me)))
    out = []
    for a in after:
        key = (_identity(a), _range(a))
        if key in pool:
            pool.remove(key)
        else:
            out.append(a)
    return sorted(out, key=lambda x: (int(x.get("severity") or 9), _range(x)))


def syntax_obs(ctx: OracleContext, case: Mapping[str, Any], diag: Mapping[str, Any], fixed: Mapping[str, str],
               originals: Mapping[str, str], prefix: str) -> List[Obs]:
    """A finding when a fixed text has a parse error its pre-mutation text did not have."""
    (sl, sc), _ = _range(diag)
    for p in sorted(fixed):
        abspath = os.path.join(ctx.project_dir, p)
        before = syntax_errors(ctx.language, originals.get(p, ""), abspath)
        after = syntax_errors(ctx.language, fixed[p], abspath)
        added = new_errors(before, after)
        if added:
            c = dict(case, check="syntax", syntax_path=p, new_errors=added[:5])
            key = QueryKey("syntax", case["path"], sl, sc, f"{prefix}quickfix-syntax:{case['title']}")
            return [Obs(str(case["kind"]), key, sorted(error_message(e) for e in before),
                        sorted(error_message(e) for e in after), c,
                        f"quick fix {case['title']!r} for {_identity(diag)[1]} leaves parse errors {added[:2]} in {p}")]
    return []


def _errors(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [x for x in items if x.get("severity") == 1]


def new_error_sites(before: Sequence[Dict[str, Any]], after: Sequence[Dict[str, Any]], old: str, new: str,
                    spans: Sequence[Span], target: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    """Errors of `after` the fix introduced. An error at a place where `before` had an error
    (ranges carried through the spans; inside a range the edit touched counts as the same
    place) is a leftover whatever its code, except at the targeted diagnostic's own place:
    there only the same diagnostic (it persisted) is not new, since the fix was to resolve it."""
    sites = []
    for b in _errors(before):
        s, e = _range(b)
        own = target is not None and diag_summary(b) == diag_summary(target)
        sites.append((map_range(old, new, spans, s, e), _identity(b) if own else None))

    def known(a: Mapping[str, Any]) -> bool:
        s, e = _range(a)
        return any(((s, e) == (ms, me) if not touched else ms <= s and e <= me) and ident in (None, _identity(a))
                   for (ms, me, touched), ident in sites)
    return [a for a in _errors(after) if not known(a)]


def fix_and_check(ctx: OracleContext, d: Any, editor: S.Editor, case: Mapping[str, Any], log: CheckLog,
                  base: Mapping[str, List[Dict[str, Any]]], originals: Mapping[str, str], diag: Dict[str, Any],
                  action: Mapping[str, Any], prefix_ops: Sequence[Op], revert: bool = True) -> List[Obs]:
    """Apply one quick fix to the mutated session, check it, revert it (unless revert=False).
    Besides the counts, the case lists the errors the fix itself introduced (new_error_sites)."""
    path, timeout = case["path"], ctx.request_timeout_s
    mutated = {path: S.diagnostics(d, path, timeout)[0]}
    edits, via = S.action_edits(d, action, timeout)
    log.seen("mutation-fix", via if edits else f"no-edit:{via}")
    try:
        res = workspace_edit_texts(edits, *_reader(d))
    except OpError as exc:
        res = EditResult(skipped=[f"invalid:{exc}"])
    if not res.texts:
        return []
    checked = sorted(set(res.texts) | {path})
    mark = len(editor.history)
    ok, opened = editor.open(checked)
    before = {p: list(base[p]) if p in base else S.diagnostics(d, p, timeout)[0] for p in checked}
    mutated.update({p: before[p] for p in checked if p != path})
    texts_before = {p: d.text(p) for p in checked}
    orig = {p: originals.get(p, res.before.get(p, "")) for p in res.texts}
    ok2, fixed = editor.change(res.texts) if ok else (False, [])
    fix_ops, out = list(editor.history[mark:]), []  # type: ignore[var-annotated]
    if ok and ok2:
        log.count("mutationFixesApplied")
        post = {p: S.diagnostics(d, p, timeout)[0] for p in checked}
        prefix = f"{case['mutation']['id']}:"
        introduced = [dict(diag_summary(x), path=p) for p in checked for x in new_error_sites(
            mutated[p], post[p], texts_before[p], d.text(p), res.spans.get(p, []), diag if p == path else None)]
        c = dict(case, diag=diag_summary(diag), title=action.get("title"), action_kind=str(action.get("kind") or ""),
                 via=via, fix_ops=[o.to_json() for o in fix_ops], n_fix_ops=len(fix_ops),
                 fix_introduced_errors=introduced[:10])
        found, _ = quickfix_obs(d, c, diag, res, before, post, prefix)
        found += syntax_obs(ctx, c, diag, {p: d.text(p) for p in res.texts}, orig, prefix)
        for o in found:
            o.ops = list(prefix_ops) + fix_ops
            o.edited = {path: d.text(path), **{p: d.text(p) for p in res.texts}}
            o.history, o.open_paths = list(editor.history), editor.open_paths()
            o.check = {"diag": diag, "res": res, "base": before, "checked": checked, "prefix": prefix, "originals": orig}
            o.running = {p: diag_norm(d, post[p]) for p in checked}
            o.note += (f" (seeded by {case['mutation']['id']}: {case['mutation']['what']}; errors before the "
                       f"mutation {sum(1 for p in before for x in before[p] if x.get('severity') == 1)}, after the fix "
                       f"{sum(1 for p in post for x in post[p] if x.get('severity') == 1)})")
        out = found
    else:
        log.unsettled += 1
    if revert and not editor.revert(fixed, opened):
        log.unsettled += 1
    return out


def check_mutation(ctx: OracleContext, d: Any, editor: S.Editor, case: Mapping[str, Any], cfg: R4Config,
                   log: CheckLog, base: Mapping[str, Any]) -> List[Obs]:
    path, m, timeout = case["path"], case["mutation"], ctx.request_timeout_s
    text0 = d.text(path)
    log.cases += 1
    if text_sha(text0) != m["sha"]:
        log.invalid += 1
        log.notes.append(f"mutation {m['id']} on {path} skipped: the session's text is not the planned one")
        return []
    mut = Op("change", path=path, start=tuple(m["start"]), end=tuple(m["end"]), text=m["text"])  # type: ignore[arg-type]
    ok = editor.run_ops([mut])
    applied = [(path, text0, mut)] if editor.history and editor.history[-1] is mut else []
    out: List[Obs] = []
    if ok:
        log.count("mutations")
        log.seen("mutation", f"{m['id']}:applied")
        post = S.diagnostics(d, path, timeout)[0]
        span = (m["offsets"][0], m["offsets"][1], m["text"])
        created = created_diagnostics(base.get(path) or [], post, text0, d.text(path), [span])
        log.count("mutationDiagnostics", len(created))
        log.seen("mutation", f"{m['id']}:{'created-diagnostics' if created else 'no-new-diagnostic'}")
        for diag in created[: cfg.mutation_diags]:
            acts, _ = S.quickfixes(d, path, diag, timeout)
            log.count("mutationFixesOffered", len(acts))
            if acts:
                log.seen("mutation", f"{m['id']}:fixes-offered")
            for act in acts[: cfg.actions_per_diag]:
                out += fix_and_check(ctx, d, editor, case, log, base, {path: text0}, diag, act,
                                     [Op("open", path=path), mut])
    else:
        log.unsettled += 1
    if not editor.revert(applied, []):
        log.unsettled += 1
    return out


def answer_mutation(ctx: OracleContext, d: Any, o: Obs) -> Tuple[List[Obs], Dict[str, Any]]:
    """Re-evaluate a seeded finding in a session that holds the mutated and fixed content."""
    post = {p: S.diagnostics(d, p, ctx.request_timeout_s)[0] for p in o.check["checked"]}
    found, _ = quickfix_obs(d, o.case, o.check["diag"], o.check["res"], o.check["base"], post, o.check["prefix"])
    texts = {p: d.text(p) for p in o.check["res"].texts if p in d.store.docs}
    found += syntax_obs(ctx, o.case, o.check["diag"], texts, o.check["originals"], o.check["prefix"])
    return [f for f in found if f.key == o.key], {p: diag_norm(d, post[p]) for p in post}


def mutation_case_session(ctx: OracleContext, case: Mapping[str, Any], ops: Sequence[Op], key: QueryKey,
                          overlay: Optional[Dict[str, Any]], label: str) -> Tuple[bool, List[Obs]]:
    """A fresh session running the ops before the fix, then the same action; (settled, findings with `key`)."""
    n, fix = int(case.get("n_fix_ops") or 0), [Op.from_json(o) for o in case.get("fix_ops") or []]
    if n <= 0 or len(ops) < n or list(ops[len(ops) - n :]) != fix:
        return True, []  # without the fix at the end there is no fix to check
    prefix = list(ops[: len(ops) - n])
    split = next((i for i, o in enumerate(prefix) if o.kind != "open"), len(prefix))
    timeout = ctx.request_timeout_s
    with session(ctx, label, settings_overlay=overlay) as d:
        editor = S.Editor(ctx, d)
        if not editor.run_ops(prefix[:split]):
            return False, []
        base = {p: S.diagnostics(d, p, timeout)[0] for p in editor.open_paths()}
        originals = {p: d.text(p) for p in editor.open_paths()}
        if not editor.run_ops(prefix[split:]):
            return False, []
        diag = find_diag(S.diagnostics(d, case["path"], timeout)[0], case["diag"])
        acts = S.quickfixes(d, case["path"], diag, timeout)[0] if diag is not None else []
        act = next((a for a in acts if a.get("title") == case["title"]
                    and str(a.get("kind") or "") == case["action_kind"]), None)
        if diag is None or act is None:
            return True, []
        found = fix_and_check(ctx, d, editor, case, CheckLog(), base, originals, diag, act, prefix, revert=False)
        return not editor.failures, [o for o in found if o.key == key]


__all__ = ["answer_mutation", "check_mutation", "created_diagnostics", "fix_and_check", "mutation_case_session",
           "new_error_sites", "syntax_obs", "text_sha"]
