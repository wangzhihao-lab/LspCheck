"""Live collection of the answers a probe decides on (probes.py): one call runs a case once
on one build, with fresh sessions only, one server at a time.

Sessions (each a new server on a new APFS clone, see driver.Driver):
- "case": the case's ops on project/ in the case's timing (settled: settle after every op;
  race: each op's own delay_ms, settling only at {"kind": "wait", "text": "settle"}
  markers), a final settle, then the probe's queries; edit probes also fetch the offered
  edit (code action through codeAction[/resolve/command], a completion item with its
  additional edits, or the TextEdits of textDocument/formatting or rangeFormatting), apply
  it offline, record parse errors before and after (oracles/syntax.py) and the diagnostics
  of the edited files before the edit (of the edit's path when the edit changes no text);
  stale_code_action runs its own session instead (collect_handles.py);
- "fresh" / "control": the content the ops leave behind (oracles.base.final_state),
  materialized, with the documents open at the end of the ops opened, settled, queried;
- "after": that content plus the edit, the edited files opened, settled, their diagnostics;
- "fresh" / "control" / "transformed" (transform_differs): original and transformed copies.
A session is valid only if it started, every op applied and it settled. For kind tsserver
the TypeScript version the wrapper reports is checked against the build.

Run line: imported by run_repro.py; not run directly.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (PKG, os.path.join(os.path.dirname(PKG), "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from .case_format import SETTLE_MARK, Case  # noqa: E402
from .probes import PROBES, diag_matches, query_id  # noqa: E402

from driver import SESSION_SETTINGS, Driver, DriverConfig, clone_tree, process_tree  # noqa: E402
from servers_bench import tsserver_paths  # noqa: E402
from framing import LspError  # noqa: E402
from model import Op  # noqa: E402
from oracles.base import final_state  # noqa: E402
from oracles.r4_session import action_edits, completion, read_doc, rel_uri, resolve_item  # noqa: E402
from oracles.r4_textedits import display_order, item_edits, workspace_edit_texts  # noqa: E402
from oracles.syntax import SyntaxToolError, syntax_errors  # noqa: E402
from ops import LineIndex, OpError, deep_merge, lsp_range, read_text, write_text  # noqa: E402
from queries import LSP_METHODS, NORMALIZERS  # noqa: E402

logger = logging.getLogger(__name__)
SESSION_ERRORS = (OSError, RuntimeError, ValueError, LspError, OpError, subprocess.SubprocessError)
CONTEXTS: Dict[str, Dict[str, Any]] = {"references": {"includeDeclaration": True}, "completion": {"triggerKind": 1},
                                       "signatureHelp": {"triggerKind": 1, "isRetrigger": False}}
TS_VERSION = re.compile(r"Using Typescript version (?:\(([\w-]+)\) )?(\S+) from path")  # wrapper 0.x and 1.x+
FORMAT_METHODS = {"format": "textDocument/formatting", "range_format": "textDocument/rangeFormatting"}
FORMAT_OPTIONS: Dict[str, Any] = {"tabSize": 4, "insertSpaces": True}


@dataclass(frozen=True)
class RunEnv:
    case: Case
    version: str  # registry version string of the build under test
    work_dir: str  # per-run scratch: materialized projects, server workspaces, protocol logs

    @property
    def kind(self) -> str:
        return str(self.case.meta["kind"])

    def config(self, label: str, project_dir: str) -> DriverConfig:
        s = self.case.session
        settings = deep_merge(dict(SESSION_SETTINGS.get(self.kind, {})), dict(self.case.settings))
        return DriverConfig(self.kind, self.version, project_dir, label=label,
                            settle_timeout_s=float(s.get("settle_timeout_s", 180.0)),
                            request_timeout_s=float(s.get("request_timeout_s", 30.0)),
                            pull_diagnostics=s.get("pull_diagnostics"), extra_settings=settings,
                            runs_dir=os.path.join(self.work_dir, "sessions"), logs_dir=os.path.join(self.work_dir, "logs"))


# ------------------------------------------------------------------ helpers
def open_at_end(ops: Sequence[Op]) -> List[str]:
    """Documents open after the ops (renames carry the open state)."""
    state: Dict[str, bool] = {}
    for op in ops:
        if op.kind == "open":
            state[op.path] = True
        elif op.kind == "close":
            state[op.path] = False
        elif op.kind == "fs_rename" and state.pop(op.path, False):
            state[op.new_path] = True
    return sorted(p for p, v in state.items() if v)


def materialize(project_dir: str, files: Mapping[str, Optional[str]], dst: str) -> str:
    """APFS clone of project_dir at dst with `files` written (None: deleted)."""
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    clone_tree(project_dir, dst)
    for rel, text in files.items():
        path = os.path.join(dst, rel)
        if text is None:
            if os.path.exists(path):
                os.remove(path)
        else:
            write_text(path, text)
    return dst


def apply_ops(d: Driver, ops: Sequence[Op], timing: str) -> List[str]:
    """Apply ops in the case's timing; the first failure (op error or unsettled server) is returned."""
    for op in ops:
        if op.kind == "wait" and op.text == SETTLE_MARK:
            res = d.settle()
            if not res.settled:
                return [f"settle marker: {res.reason}"]
            continue
        try:
            out = d.apply(op)
        except OpError as exc:
            return [f"{op.kind} {op.path}: {exc}"]
        if out.error:
            return [f"{op.kind} {op.path}: {out.error}"]
        if timing == "settled" and op.kind != "wait":
            res = d.settle()
            if not res.settled:
                return [f"not settled after {op.kind} {op.path}: {res.reason}"]
    return []


def raw_diagnostics(d: Driver, path: str) -> List[Dict[str, Any]]:
    result, err = d.diagnostics(path, d.cfg.request_timeout_s)
    items = result.get("items") if isinstance(result, dict) else result
    return [x for x in items or [] if isinstance(x, dict)] if err is None else []


def run_query(d: Driver, q: Mapping[str, Any]) -> Any:
    """One probe query, normalized (queries.NORMALIZERS); errors as ["error", code]."""
    method, path, timeout = str(q["method"]), str(q["path"]), d.cfg.request_timeout_s
    doc: Dict[str, Any] = {"textDocument": {"uri": d.uri(path)}}
    if method == "diagnostics":
        result, err = d.diagnostics(path, timeout)
    elif method == "pull_diagnostics":
        result, err = d.request("textDocument/diagnostic", doc, timeout)
    else:
        params = dict(doc)
        if isinstance(q.get("position"), list):
            params["position"] = {"line": q["position"][0], "character": q["position"][1]}
        if method in CONTEXTS or q.get("context"):
            params["context"] = dict(q.get("context") or CONTEXTS[method])
        if method == "inlayHint":
            params["range"] = lsp_range((0, 0), LineIndex(d.text(path)).end())
        if method == "codeAction":
            pos = tuple(q["position"])
            rng = q.get("range") or [pos[0], pos[1], pos[0], pos[1]]
            params["range"] = lsp_range((rng[0], rng[1]), (rng[2], rng[3]))
            params["context"] = {"diagnostics": raw_diagnostics(d, path), "triggerKind": 1}
        result, err = d.request(LSP_METHODS[method], params, timeout)
    if err is not None:
        return list(err)
    return NORMALIZERS["diagnostics" if method == "pull_diagnostics" else method](result, d.norm_context(50))


def run_queries(d: Driver, queries: Sequence[Mapping[str, Any]]) -> Tuple[Dict[str, Any], str]:
    """Open the queried documents (settling again when any was closed), then ask every query."""
    missing = [p for p in dict.fromkeys(str(q["path"]) for q in queries)
               if not (p in d.store.docs and d.store.docs[p].open)]
    if missing:
        d.open(*missing)
        res = d.settle()
        if not res.settled:
            return {}, f"not settled after opening {missing}: {res.reason}"
    return {query_id(q): run_query(d, q) for q in queries}, ""


def ts_version_used(d: Driver) -> str:
    for note in list(d.client.notifications):
        m = TS_VERSION.search(str((note.params or {}).get("message", ""))) if note.method == "window/logMessage" else None
        if m:
            return m.group(2)
    return ""


def _check_build(env: RunEnv, d: Driver) -> str:
    """tsserver builds: the wrapper must run the pinned TypeScript. Wrappers from 0.7 on log the
    version they use; older ones log nothing, so a child process running the pinned tsserver.js
    is the evidence instead."""
    if env.kind != "tsserver":
        return ""
    want, got = env.version.split("+tsls")[0], ts_version_used(d)
    if got:
        return "" if got == want else f"wrapper reports TypeScript {got}, build is {want}"
    pinned = tsserver_paths(env.version)[1]
    pids = process_tree(d.client.proc.pid) if d.alive() else []
    cmds = subprocess.run(["ps", "-ww", "-o", "command=", "-p", ",".join(map(str, pids))], capture_output=True,
                          text=True, timeout=10).stdout if pids else ""
    return "" if pinned in cmds else f"wrapper reports no TypeScript version and no child process runs {pinned}"


# ------------------------------------------------------------------ edits
def _pick(items: Sequence[Mapping[str, Any]], key: str, pattern: str) -> Optional[Mapping[str, Any]]:
    return next((x for x in items if re.search(pattern, str(x.get(key, "")))), None)


def offered_edit(d: Driver, spec: Mapping[str, Any]) -> Dict[str, Any]:
    """The edit a code action or completion item makes (texts before/after), and what was offered."""
    path, timeout = str(spec["path"]), d.cfg.request_timeout_s
    out: Dict[str, Any] = {"offered": False, "titles": []}
    if spec["via"] == "code_action":
        diags = raw_diagnostics(d, path)
        if spec.get("diagnostic"):
            norm = [NORMALIZERS["diagnostics"]([x], d.norm_context(50))[0] for x in diags]
            hit = next((raw for raw, n in zip(diags, norm) if diag_matches(n, spec["diagnostic"])), None)
            if hit is None:
                out["titles"] = [f"<no diagnostic matching {spec['diagnostic']}; have {[n[5] for n in norm]}>"]
                return out
            rng, context_diags = hit["range"], [hit]
        else:
            r = spec["range"]
            rng = lsp_range((r[0], r[1]), (r[2], r[3]))
            context_diags = diags
        ctx: Dict[str, Any] = {"diagnostics": context_diags, "triggerKind": 1}
        if spec.get("kind"):
            ctx["only"] = [spec["kind"]]
        res, err = d.request("textDocument/codeAction", {"textDocument": {"uri": d.uri(path)}, "range": rng,
                                                         "context": ctx}, timeout)
        actions = [a for a in res or [] if isinstance(a, dict)] if err is None else []
        out["titles"] = [str(a.get("title", "")) for a in actions] or ([f"<error {err[1]}>"] if err else [])
        chosen = _pick([a for a in actions if str(a.get("kind") or "").startswith(spec.get("kind", ""))],
                       "title", str(spec["title_re"]))
        if chosen is None:
            return out
        edits, via = action_edits(d, chosen, timeout)
        out.update(offered=True, chosen=str(chosen.get("title", "")), via=via)
    elif spec["via"] in FORMAT_METHODS:
        params: Dict[str, Any] = {"textDocument": {"uri": d.uri(path)}, "options": dict(spec.get("options") or FORMAT_OPTIONS)}
        if spec["via"] == "range_format":
            r = spec["range"]
            params["range"] = lsp_range((r[0], r[1]), (r[2], r[3]))
        method = FORMAT_METHODS[spec["via"]]
        res, err = d.request(method, params, timeout)
        out["titles"] = [method] if err is None else [f"<error {err[1]}>"]
        if err is not None:
            return out
        edits, via = [{"changes": {d.uri(path): [e for e in res or [] if isinstance(e, dict)]}}], str(spec["via"])
        out.update(offered=True, chosen=method, via=via)
    elif spec["via"] == "completion":
        line, ch = spec["position"]
        items, defaults, err = completion(d, path, line, ch, timeout)
        typed = re.search(r"[\w$]*$", LineIndex(d.text(path)).line_text(line)[:ch]).group()  # type: ignore[union-attr]
        shown = display_order(items, typed)
        out["titles"] = [str(i.get("label", "")) for i in shown[:50]] or ([f"<error {err[1]}>"] if err else [])
        chosen = _pick(shown, "label", str(spec["label_re"]))
        if chosen is None:
            return out
        item, _ = resolve_item(d, dict(chosen), timeout)
        word = {"start": {"line": line, "character": ch - len(typed)}, "end": {"line": line, "character": ch}}
        edits, via = [{"changes": {d.uri(path): item_edits(item, defaults, word)}}], "completion"
        out.update(offered=True, chosen=str(chosen.get("label", "")), via=via)
    else:
        out["titles"] = [f"<no edit route {spec['via']!r}>"]
        return out
    try:
        res_edit = workspace_edit_texts(edits, lambda p: read_doc(d, p), lambda u: rel_uri(d, u))
    except OpError as exc:
        out["error"] = str(exc)
        return out
    out.update(texts_before=res_edit.before, texts_after=res_edit.texts, skipped=res_edit.skipped)
    return out


def add_syntax(env: RunEnv, d: Driver, edit: Dict[str, Any]) -> None:
    before, after = {}, {}
    try:
        for path, text in edit.get("texts_after", {}).items():
            abs_path = os.path.join(d.workspace, path)
            before[path] = syntax_errors(env.case.language, edit["texts_before"][path], abs_path)
            after[path] = syntax_errors(env.case.language, text, abs_path)
    except SyntaxToolError as exc:
        edit["error"] = f"syntax classifier: {exc}"
    edit.update(syntax_before=before, syntax_after=after)


# ------------------------------------------------------------------ sessions
def session(env: RunEnv, label: str, project_dir: str, ops: Sequence[Op], timing: str,
            queries: Sequence[Mapping[str, Any]], edit_spec: Optional[Mapping[str, Any]] = None,
            diag_paths: Sequence[str] = ()) -> Dict[str, Any]:
    """One fresh session; returns {valid, reason, results, edit?, diagnostics_before?, ...}."""
    t0 = time.monotonic()
    out: Dict[str, Any] = {"valid": False, "reason": "", "results": {}}
    try:
        with Driver(env.config(label, project_dir)) as d:
            out["log"] = os.path.relpath(d.log_path, env.work_dir)
            errors = apply_ops(d, ops, timing)
            res = d.settle() if not errors else None
            if errors or res is None or not res.settled:
                out["reason"] = errors[0] if errors else f"not settled: {res.reason if res else '?'}"
                return out
            out["results"], why = run_queries(d, queries)
            if why:
                out["reason"] = why
                return out
            if edit_spec is not None:
                edit = offered_edit(d, edit_spec)
                if edit.get("texts_after"):
                    add_syntax(env, d, edit)
                    out["diagnostics_before"], why = run_queries(d, [{"id": p, "method": "diagnostics", "path": p}
                                                                     for p in edit["texts_after"]])
                elif edit.get("offered") and not edit.get("error"):  # the edit changes no text
                    p = str(edit_spec["path"])
                    out["diagnostics_before"], why = run_queries(d, [{"id": p, "method": "diagnostics", "path": p}])
                out["edit"] = edit
            if diag_paths:
                out["diagnostics"], why = run_queries(d, [{"id": p, "method": "diagnostics", "path": p}
                                                          for p in diag_paths])
            out["reason"] = why or _check_build(env, d)
            out["valid"] = not out["reason"] and d.alive()
            if not d.alive():
                out["reason"] = out["reason"] or "server exited during the session"
    except SESSION_ERRORS as exc:
        out["reason"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    out["seconds"] = round(time.monotonic() - t0, 2)
    return out


def collect(env: RunEnv) -> Dict[str, Dict[str, Any]]:
    """All sessions the case's probe needs, sequentially; returns the answers."""
    case, probe = env.case, env.case.repro.probe
    kind = PROBES[str(probe["type"])]
    params = probe.get("params") or {}
    plan = kind.queries(params)
    ops, timing, proj = list(case.repro.ops), case.repro.timing, case.project_dir
    answers: Dict[str, Dict[str, Any]] = {}
    if probe["type"] == "stale_code_action":
        from .collect_handles import handle_session  # late: collect_handles imports this module
        answers["case"] = handle_session(env, proj, ops, timing, params)
        return answers
    if probe["type"] == "transform_differs":
        t = params["transform"]
        text = read_text(os.path.join(proj, t["path"]))
        if t["kind"] == "crlf":
            new = text.replace("\r\n", "\n").replace("\n", "\r\n")
        else:
            starts = LineIndex(text).starts
            cut = starts[t["line"]] if t["line"] < len(starts) else len(text)
            new = text[:cut] + t["text"] + text[cut:]
        variant = materialize(proj, {t["path"]: new}, os.path.join(env.work_dir, "transformed"))
        for name, where in (("fresh", proj), ("control", proj), ("transformed", variant)):
            answers[name] = session(env, name, where, ops, timing, plan[name])
        return answers
    edit_spec = params.get("edit") if "edit" in params else None
    answers["case"] = session(env, "case", proj, ops, timing, plan.get("case", []), edit_spec)
    if not answers["case"]["valid"]:
        return answers  # the probe is invalid anyway; no reference sessions needed
    state = final_state(proj, ops)
    reopen = [Op("open", path=p) for p in open_at_end(ops)]
    if "fresh" in kind.sessions:
        fresh_dir = materialize(proj, state.files, os.path.join(env.work_dir, "final"))
        overlay = state.settings or {}
        for name in ("fresh", "control"):
            case_env = env if not overlay else RunEnv(_with_settings(case, overlay), env.version, env.work_dir)
            answers[name] = session(case_env, name, fresh_dir, reopen, "settled", plan.get(name, []))
    if "after" in kind.sessions:
        edit = answers["case"].get("edit") or {}
        if not edit.get("texts_after"):
            answers["after"] = {"valid": False, "reason": "no edit to apply", "results": {}}
            return answers
        edited = dict(state.files, **edit["texts_after"])
        after_dir = materialize(proj, edited, os.path.join(env.work_dir, "edited"))
        paths = sorted(set(edit["texts_after"]) | {str(params["edit"]["path"])})
        opens = reopen + [Op("open", path=p) for p in paths if p not in open_at_end(ops)]
        answers["after"] = session(env, "after", after_dir, opens, "settled", [], diag_paths=paths)
    return answers


def _with_settings(case: Case, overlay: Mapping[str, Any]) -> Case:
    """The case with the settings the ops left behind (set_config) as its session settings."""
    return replace(case, settings=deep_merge(dict(case.settings), dict(overlay)))


__all__ = ["FORMAT_METHODS", "RunEnv", "apply_ops", "collect", "materialize", "offered_edit", "open_at_end",
           "run_query", "session", "ts_version_used"]
