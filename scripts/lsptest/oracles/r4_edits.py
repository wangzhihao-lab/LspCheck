"""R4 edit validity for non-refactoring edits (plan/tool_design_v1.md sections 5 and 10).

Sub-checks (oracles/r4_checks.py): quick fixes, formatting idempotence (plus the
non-whitespace invariant for ts6/ts7), completion insertion (syntax classifier of
oracles/syntax.py) and organize imports applied twice; and seeded quick fixes
(oracles/r4_seeded.py): clean code rarely has fixable diagnostics, so a seeded mutation
M1-M4 (oracles/r4_mutations.py) plants one per case and the quick fixes offered on the
diagnostics it created are checked against the pre-mutation state. Rename, extract and
inline are not checked. R4Config.checks selects the sub-checks.

run(): one running session opens the targets and records their diagnostics (the base);
cases are planned per sub-check and ctx.max_cases is shared round-robin between the
sub-checks. Completion cases run first, while the session has no edits; every
edit-based case applies its edit as change ops, settles, checks, and reverts. Every
finding is then confirmed in a FRESH session: completion and non-whitespace findings on
the original content (re-requested), the others on the edited content (materialize).
A confirmed finding becomes an R4 candidate (Violation.ops = [] and the case holds the
edit; seeded findings: ops = open, mutation, fix); an unconfirmed edit-based finding is filed with case kind "r1-suspect": the
running session's answer after its op history differs from a fresh session on the same
content, so the incremental state was wrong, not the edit (Violation.ops = that history).
Unconfirmed completion findings are dropped with a note: the running session had no
edits then, so the difference is nondeterminism, not history.

replay(): R4 kinds re-execute the case in a fresh session (after `ops`, normally none)
and re-evaluate the finding in a fresh baseline and a fresh control, on the edited
content (quick fix, format, organize) or on the original content (completion, format
text). r1-suspects apply the history in a fresh session and compare it with a fresh
baseline and control on final_state(history). control_stable is False when the case
session did not reproduce (there is nothing to compare).

rust-analyzer formats through rustfmt; when the default rustfmt does not run (rustup
toolchain without the component) the R4 sessions override rust-analyzer's rustfmt
command with a toolchain that has it (noted in the result).

Run line: loaded by oracles.load_all(); python3 scripts/lsptest/pilot_r4_r6.py runs it.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from model import Op, QueryKey, Violation  # noqa: E402
from ops import OpError, deep_merge  # noqa: E402
from oracles import r4_session as S  # noqa: E402
from oracles.base import (FinalState, OracleContext, OracleResult, ReplayOutcome, apply_history, case_of,  # noqa: E402
                          difference_shape, discard, final_state, make_violation, materialize, register_oracle,
                          session, shape_of)
from framing import LspError  # noqa: E402  (lsp_repro is on sys.path once base is imported)
from oracles.r4_checks import (CHECKS, CheckLog, Obs, R4Config, answer, diag_norm, diag_summary,  # noqa: E402
                               change_norm)
from oracles.r4_mutations import KINDS, plan_mutations  # noqa: E402
from oracles.r4_seeded import answer_mutation, check_mutation, mutation_case_session, text_sha  # noqa: E402
from oracles.r4_textedits import apply_text_edits, format_options  # noqa: E402
from oracles.syntax import SyntaxToolError, rust_edition, rust_toolchain_with_rustfmt, rustfmt_path, supported  # noqa: E402
from targets import SERVER_LANGUAGE  # noqa: E402

logger = logging.getLogger(__name__)
ORDER = ("completion", "format", "organize", "quickfix", "mutation")
R1_QUERY = {"quickfix": "diagnostics", "format": "formatting", "organize": "organizeImports", "mutation": "diagnostics"}
ALL_CHECKS = dict(CHECKS, mutation=check_mutation)
FAILURES = (LspError, OSError, RuntimeError, OpError, SyntaxToolError, subprocess.SubprocessError)


def settings_overlay(ctx: OracleContext) -> Optional[Dict[str, Any]]:
    """rust-analyzer only: a rustfmt command that runs, when the default one does not."""
    if ctx.server_kind != "rust-analyzer" or rust_toolchain_with_rustfmt() is None:
        return None
    edition = rust_edition(os.path.join(ctx.project_dir, "Cargo.toml"))
    return {"rust-analyzer": {"rustfmt": {"overrideCommand": [rustfmt_path(), "--edition", edition]}}}


def _shape(o: Obs) -> str:
    return difference_shape(o.key.method, o.expected, o.actual)


def _by_kind(cases: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Seeded cases round-robin over the mutation kinds (files in target order within a kind), so
    that a small budget covers every kind first."""
    queues = {k: [c for c in cases if c["mutation"]["id"] == k] for k in KINDS}
    out: List[Dict[str, Any]] = []
    while any(queues.values()):
        out += [queues[k].pop(0) for k in KINDS if queues[k]]
    return out


def _interleave(groups: Sequence[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i in range(max((len(g) for g in groups), default=0)):
        out += [g[i] for g in groups if i < len(g)]
    return out


@register_oracle("r4_edits")
class EditValidity:
    name = "r4_edits"
    cfg = R4Config()

    def applies_to(self, server_kind: str) -> bool:
        # Only languages with lexical rules and a syntax classifier (the study's four); Java has neither.
        return server_kind in SERVER_LANGUAGE

    # ------------------------------------------------------------------ run
    def run(self, ctx: OracleContext) -> OracleResult:
        t0, res, log, obs = time.monotonic(), OracleResult(self.name, ctx.run_id), CheckLog(), []  # type: ignore[var-annotated]
        overlay = settings_overlay(ctx)
        if overlay:
            res.notes.append(f"rust-analyzer rustfmt command overridden: {json.dumps(overlay)}")
        try:
            with session(ctx, "r4-running", settings_overlay=overlay) as d:
                res.sessions += 1
                editor = S.Editor(ctx, d)
                if not editor.open([t.path for t in ctx.targets])[0]:
                    res.unsettled += 1
                    res.notes.append(f"running session did not settle: {editor.failures[:2]}")
                else:
                    base = {t.path: S.diagnostics(d, t.path, ctx.request_timeout_s)[0] for t in ctx.targets}
                    for case in self._plan(ctx, d, base, log):
                        if not d.alive():
                            res.notes.append("server exited; remaining cases skipped")
                            break
                        try:
                            obs += ALL_CHECKS[case["kind"]](ctx, d, editor, case, self.cfg, log, base)
                        except SyntaxToolError as exc:
                            log.notes.append(f"syntax classifier failed on {case['path']}: {exc}"[:300])
        except FAILURES as exc:
            res.notes.append(f"running session failed: {type(exc).__name__}: {exc}"[:300])
        try:
            res.candidates = self._confirm(ctx, obs, overlay, res)
        except FAILURES as exc:
            res.notes.append(f"confirmation failed: {type(exc).__name__}: {exc}"[:300])
        res.cases, res.invalid_cases, res.unsettled = log.cases, log.invalid, res.unsettled + log.unsettled
        res.compared = dict(sorted(log.compared.items()))
        res.notes += [f"support {json.dumps(log.support, sort_keys=True)}"] + log.notes[:20]
        res.seconds = round(time.monotonic() - t0, 2)
        return res

    def _plan(self, ctx: OracleContext, d: Any, base: Mapping[str, List[Dict[str, Any]]],
              log: CheckLog) -> List[Dict[str, Any]]:
        comp, fmt, org, fix, mut = [], [], [], [], []  # type: ignore[var-annotated]
        caps = {"formatting": S.supports_formatting(d), "codeActionResolve": S.resolves_actions(d),
                "completionResolve": S.resolves_items(d), "syntaxClassifier": supported(ctx.language)}
        log.support["capabilities"] = {k: int(v) for k, v in caps.items()}
        for ft in ctx.targets:
            text = d.text(ft.path)
            if d.supports("completion") and caps["syntaxClassifier"]:
                comp.append([{"kind": "completion", "path": ft.path, "line": p[0], "character": p[1], "name": n}
                             for p, n in zip(ft.ends, ft.names)])
            if caps["formatting"]:
                fmt.append([{"kind": "format", "path": ft.path, "options": format_options(text, ctx.language)}])
            org.append([{"kind": "organize", "path": ft.path}])
            rows, seen = [], set()
            for diag in base.get(ft.path, [])[: self.cfg.diags_per_file] if "quickfix" in self.cfg.checks else []:
                acts, _ = S.quickfixes(d, ft.path, diag, ctx.request_timeout_s)
                log.seen("quickfix-offered", "diagnostic-with-fixes" if acts else "diagnostic-without-fixes")
                for a in acts[: self.cfg.actions_per_diag]:
                    sig = (str(diag.get("code")), a.get("title"))
                    rows.append((sig in seen, {"kind": "quickfix", "path": ft.path, "diag": diag_summary(diag),
                                               "title": a.get("title"), "action_kind": str(a.get("kind") or "")}))
                    seen.add(sig)
            fix.append([c for _, c in sorted(rows, key=lambda r: r[0])])  # distinct (code, title) first
            if "mutation" in self.cfg.checks:
                mut += self._mutations(ctx, ft.path, text, log)
        lists = {"completion": _interleave(comp), "format": _interleave(fmt), "organize": _interleave(org),
                 "quickfix": _interleave(fix), "mutation": _by_kind(mut)}
        lists = {k: (v if k in self.cfg.checks else []) for k, v in lists.items()}
        chosen: Dict[str, List[Dict[str, Any]]] = {k: [] for k in ORDER}
        n = 0
        while n < ctx.max_cases and any(len(chosen[k]) < len(lists[k]) for k in ORDER):
            for k in ORDER:
                if n < ctx.max_cases and len(chosen[k]) < len(lists[k]):
                    chosen[k].append(lists[k][len(chosen[k])])
                    n += 1
        log.support["planned"] = {k: len(chosen[k]) for k in ORDER}
        log.support["available"] = {k: len(lists[k]) for k in ORDER}
        return [c for k in ORDER for c in chosen[k]]

    @staticmethod
    def _mutations(ctx: OracleContext, path: str, text: str, log: CheckLog) -> List[Dict[str, Any]]:
        """Seeded mutation cases of one file (at most one per kind)."""
        try:
            muts = plan_mutations(text, ctx.language, os.path.join(ctx.project_dir, path), ctx.seed, path)
        except SyntaxToolError as exc:
            log.notes.append(f"no mutations for {path}: {exc}"[:300])
            return []
        for kind in KINDS:
            log.seen("mutation-planned", kind if any(m.kind == kind for m in muts) else f"{kind}:none")
        return [{"kind": "mutation", "path": path,
                 "mutation": dict(m.to_json(), start=list(m.op(path, text).start), end=list(m.op(path, text).end),
                                  text=m.text, offsets=[m.start, m.end], sha=text_sha(text))} for m in muts]

    # ------------------------------------------------------------------ confirmation
    def _violation(self, ctx: OracleContext, o: Obs, note: str) -> Violation:
        return make_violation(ctx, self.name, o.key, o.expected, o.actual, o.ops, o.case, f"{o.note}; {note}")

    def _confirm(self, ctx: OracleContext, obs: List[Obs], overlay: Optional[Dict[str, Any]],
                 res: OracleResult) -> List[Violation]:
        out: List[Violation] = []
        on_original = [o for o in obs if not o.edited]
        if on_original:
            with session(ctx, "r4-confirm", settings_overlay=overlay) as d:
                res.sessions += 1
                editor = S.Editor(ctx, d)
                editor.open([t.path for t in ctx.targets])
                base = {p: S.diagnostics(d, p, ctx.request_timeout_s)[0] for p in editor.open_paths()}
                for o in on_original:
                    again = [a for a in ALL_CHECKS[o.kind](ctx, d, editor, o.case, self.cfg, CheckLog(), base)
                             if a.key == o.key and _shape(a) == _shape(o)]
                    if again:
                        out.append(self._violation(ctx, o, "confirmed in a fresh session on the original content"))
                    else:
                        res.notes.append(f"not reproduced in a fresh session (no edits preceded it): {o.note}"[:300])
        for o in (o for o in obs if o.edited):
            res.sessions += 1
            ok, found, answers = self._fresh_answer(ctx, o, overlay, FinalState(dict(o.edited), None), "confirm")
            if ok and any(_shape(f) == _shape(o) for f in found):
                out.append(self._violation(ctx, o, "confirmed in a fresh session on the edited content"))
            elif ok:
                out += self._r1_suspects(ctx, o, answers)
            else:
                res.notes.append(f"fresh confirmation did not settle: {o.note}"[:300])
        return out

    def _fresh_answer(self, ctx: OracleContext, o: Obs, overlay: Optional[Dict[str, Any]], state: FinalState,
                      label: str) -> Tuple[bool, List[Obs], Dict[str, Any]]:
        """A fresh session on the edited content with o.open_paths open: (settled, findings, answers)."""
        tag = f"{ctx.run_id}-{label}-{uuid.uuid4().hex[:8]}"
        root = materialize(ctx, state, tag)
        try:
            with session(ctx, f"r4-{label}", project_dir=root, settings_overlay=overlay) as d:
                editor = S.Editor(ctx, d)
                if not editor.open(o.open_paths)[0]:
                    return False, [], {}
                found, answers = (answer_mutation if o.kind == "mutation" else answer)(ctx, d, o)
                return True, found, answers
        finally:
            discard(root)

    def _r1_suspects(self, ctx: OracleContext, o: Obs, answers: Mapping[str, Any]) -> List[Violation]:
        method = R1_QUERY[o.kind]
        for path in sorted(o.running):
            fresh, running = answers.get(path), o.running[path]
            if fresh is None or fresh == running:
                continue
            case = {"kind": "r1-suspect", "origin": o.kind, "query": method, "path": path, "open": o.open_paths,
                    "options": o.case.get("options"), "origin_case": o.case}
            note = (f"{o.note}; NOT shown by a fresh session on the same content: the running session's "
                    f"{method} answer for {path} after {len(o.history)} ops differs from a fresh session "
                    f"(incremental state, filed as r1-suspect, not an edit defect)")
            return [make_violation(ctx, self.name, QueryKey(method, path), fresh, running, o.history, case, note)]
        return []

    # ------------------------------------------------------------------ replay
    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        t0, case = time.monotonic(), case_of(v)
        pre, overlay = list(v.ops if ops is None else ops), settings_overlay(ctx)
        try:
            if case.get("kind") == "r1-suspect":
                out = self._replay_r1(ctx, v, case, pre, overlay)
            else:
                out = self._replay_r4(ctx, v, case, pre, overlay)
        except FAILURES as exc:
            logger.warning("r4 replay of %s failed: %s", v.signature, exc)
            out = ReplayOutcome(False, False, False)
        out.seconds = round(time.monotonic() - t0, 2)
        return out

    def _case_session(self, ctx: OracleContext, case: Mapping[str, Any], pre: Sequence[Op], key: QueryKey,
                      overlay: Optional[Dict[str, Any]], label: str) -> Tuple[bool, List[Obs]]:
        with session(ctx, label, settings_overlay=overlay) as d:
            editor = S.Editor(ctx, d)
            ok = editor.run_ops(pre) and editor.open(sorted({t.path for t in ctx.targets} | {case["path"]}))[0]
            base = {p: S.diagnostics(d, p, ctx.request_timeout_s)[0] for p in editor.open_paths()}
            found = ALL_CHECKS[case["kind"]](ctx, d, editor, case, self.cfg, CheckLog(), base) if ok else []
            return ok and not editor.failures, [o for o in found if o.key == key]

    def _replay_r4(self, ctx: OracleContext, v: Violation, case: Mapping[str, Any], pre: Sequence[Op],
                   overlay: Optional[Dict[str, Any]]) -> ReplayOutcome:
        want = shape_of(v)
        if case["kind"] == "mutation":  # the ops hold the mutation and the fix (see r4_seeded)
            ok, found = mutation_case_session(ctx, case, pre, v.key, overlay, "r4-replay-case")
        else:
            ok, found = self._case_session(ctx, case, pre, v.key, overlay, "r4-replay-case")
        if case["kind"] in ("completion", "formatText"):  # judged on the original content: case session = baseline
            ok_c, control = self._case_session(ctx, case, pre, v.key, overlay, "r4-replay-control")
            first = lambda f: f[0].actual if f else None  # noqa: E731
            stable = ok and ok_c and first(found) == first(control)
            hit = [f for f in found if _shape(f) == want]
            return ReplayOutcome(ok and ok_c, stable, bool(hit),
                                 self._violation(ctx, hit[0], "replayed") if hit else None)
        hit = [f for f in found if _shape(f) == want]
        if not (ok and hit):
            return ReplayOutcome(ok, False, False)
        state = final_state(ctx.project_dir, pre)
        files = dict(state.files)
        files.update(hit[0].edited)
        runs = [self._fresh_answer(ctx, hit[0], overlay, FinalState(files, None), f"replay-{lbl}")
                for lbl in ("baseline", "control")]
        (ok_b, found_b, ans_b), (ok_c, _, ans_c) = runs
        stable = ok_b and ok_c and ans_b == ans_c
        again = [f for f in found_b if _shape(f) == want]
        return ReplayOutcome(ok_b and ok_c, stable, bool(again),
                             self._violation(ctx, again[0], "replayed") if again else None)

    def _r1_answer(self, ctx: OracleContext, d: Any, case: Mapping[str, Any]) -> Any:
        path, method = case["path"], case["query"]
        if method == "diagnostics":
            return diag_norm(d, S.diagnostics(d, path, ctx.request_timeout_s)[0])
        if method == "formatting":
            e2, err = S.formatting(d, path, case.get("options") or {}, ctx.request_timeout_s)
            if err is not None:
                return ["error", err[1]]
            text = d.text(path)
            return change_norm(path, text, apply_text_edits(text, e2 or []))
        o = Obs("organize", QueryKey("organizeImports", path), [], [], {}, "")
        return answer(ctx, d, o)[1].get(path)

    def _replay_r1(self, ctx: OracleContext, v: Violation, case: Mapping[str, Any], pre: Sequence[Op],
                   overlay: Optional[Dict[str, Any]]) -> ReplayOutcome:
        with session(ctx, "r4-replay-history", settings_overlay=overlay) as d:
            errors = apply_history(ctx, d, pre)
            ok = not errors and d.settle().settled
            actual = self._r1_answer(ctx, d, case) if ok else None
        state = final_state(ctx.project_dir, pre)
        root = materialize(ctx, state, f"{ctx.run_id}-r1s-{uuid.uuid4().hex[:8]}")
        fresh: List[Tuple[bool, Any]] = []
        try:
            for lbl in ("baseline", "control"):
                with session(ctx, f"r4-replay-{lbl}", project_dir=root,
                             settings_overlay=deep_merge(overlay or {}, state.settings or {})) as d:
                    editor = S.Editor(ctx, d)
                    okf = editor.open(case.get("open") or [case["path"]])[0]
                    fresh.append((okf, self._r1_answer(ctx, d, case) if okf else None))
        finally:
            discard(root)
        (ok_b, exp), (ok_c, ctl) = fresh
        stable = ok_b and ok_c and exp == ctl
        same = ok and ok_b and actual != exp and difference_shape(case["query"], exp, actual) == shape_of(v)
        observed = make_violation(ctx, self.name, v.key, exp, actual, pre, case, "replayed") if same else None
        return ReplayOutcome(ok and ok_b and ok_c, stable, same, observed)


__all__ = ["ALL_CHECKS", "EditValidity", "ORDER", "R1_QUERY", "settings_overlay"]
