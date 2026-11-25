"""Live-session helpers of the r4_edits oracle.

Requests against a Driver: quick fixes for one diagnostic, organize imports (a
`source.organizeImports*` code action, else a server command from ORGANIZE_COMMANDS),
formatting, completion items and their resolution. A code action without an edit is
resolved (codeAction/resolve) when the server offers resolution; a command-only action
is followed only when its command is in EDIT_ONLY_COMMANDS (commands that just compute
an edit): the command is executed and the WorkspaceEdits the server sends back through
workspace/applyEdit are taken from the driver's record of those requests (the driver
answers applied=false, the oracle then applies the recorded edit itself as ordinary
change ops; such cases carry via=command). Other commands may write files or install
packages, so those actions are skipped (via=command-not-followed:<name>). An action with
both an edit and a command uses the edit only (the command would run before the edit
reaches the server).

`Editor` applies edited texts to the live session: documents that are not open are
opened first, each changed document gets one minimal change Op (see r4_textedits), every
op goes through base.apply_history (settled after each op in the settled timing mode)
and is appended to `history`; `revert` applies the exact inverses and closes the
documents opened for the case.

Run line: imported by oracles/r4_checks.py and oracles/r4_edits.py; not run directly.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from model import Op  # noqa: E402
from ops import LineIndex, OpError, inverse_change, lsp_range, read_text  # noqa: E402
from oracles.base import OracleContext, apply_history  # noqa: E402
from oracles.r4_textedits import minimal_change  # noqa: E402

logger = logging.getLogger(__name__)

ORGANIZE_COMMANDS: Dict[str, str] = {"pyright": "pyright.organizeimports"}  # servers without the code action
# Commands known to do nothing but compute a WorkspaceEdit and send it with workspace/applyEdit (or
# return it). Other commands can write files, fetch modules or install packages, so they are not run.
EDIT_ONLY_COMMANDS = frozenset({"_typescript.applyWorkspaceEdit", "_typescript.organizeImports", "gopls.apply_fix",
                                "gopls.add_import", "pyright.organizeimports"})
APPLY_EDIT_WAIT_S = 1.0  # after executeCommand: time allowed for a late workspace/applyEdit
Error = Optional[Tuple[str, Any]]


# ------------------------------------------------------------------ capabilities and documents
def capabilities(d: Any) -> Dict[str, Any]:
    return getattr(d.client, "server_capabilities", None) or {}


def supports_formatting(d: Any) -> bool:
    return capabilities(d).get("documentFormattingProvider") not in (None, False) or d.registered(
        "textDocument/formatting")


def _dynamic_option(d: Any, method: str, key: str) -> bool:
    """An option of a dynamic registration (JDT LS registers textDocument/codeAction with
    resolveProvider after initialize, and answers initialize with codeActionProvider: null)."""
    mon = getattr(d, "monitor", None)
    if mon is None:
        return False
    mon.poll()
    opts = mon.registered(method)
    return isinstance(opts, dict) and bool(opts.get(key))


def resolves_actions(d: Any) -> bool:
    prov = capabilities(d).get("codeActionProvider")
    return (isinstance(prov, dict) and bool(prov.get("resolveProvider"))) or \
        _dynamic_option(d, "textDocument/codeAction", "resolveProvider")


def resolves_items(d: Any) -> bool:
    prov = capabilities(d).get("completionProvider")
    return (isinstance(prov, dict) and bool(prov.get("resolveProvider"))) or \
        _dynamic_option(d, "textDocument/completion", "resolveProvider")


def rel_uri(d: Any, uri: str) -> Optional[str]:
    """Workspace-relative path of a file URI; None outside the workspace or for other schemes."""
    path = d.mapper.rel(uri)
    if not path or path == "." or path.startswith("/") or "://" in path or path.startswith("<"):
        return None
    return path


def read_doc(d: Any, path: str) -> Optional[str]:
    """The session's current text of a document (open buffer, else the file in the workspace)."""
    doc = d.store.docs.get(path)
    if doc is not None:
        return doc.text
    try:
        return read_text(os.path.join(d.workspace, path))
    except OSError:
        return None


def diagnostics(d: Any, path: str, timeout: float) -> Tuple[List[Dict[str, Any]], Error]:
    result, err = d.diagnostics(path, timeout)
    items = result.get("items") if isinstance(result, dict) else result
    return [x for x in items or [] if isinstance(x, dict)], err


# ------------------------------------------------------------------ code actions
def _is_workspace_edit(x: Any) -> bool:
    return isinstance(x, dict) and ("changes" in x or "documentChanges" in x)


def follow_command(d: Any, command: Mapping[str, Any], timeout: float) -> Tuple[List[Dict[str, Any]], Error]:
    """Execute a command; the WorkspaceEdits the server asked the client to apply (or a
    WorkspaceEdit returned as the command result when it sent none)."""
    mark = len(d.server_edits)
    result, err = d.request("workspace/executeCommand", {"command": command.get("command"),
                                                         "arguments": command.get("arguments") or []}, timeout)
    deadline = time.monotonic() + APPLY_EDIT_WAIT_S
    while len(d.server_edits) == mark and time.monotonic() < deadline:
        time.sleep(0.05)
    recorded = [p["edit"] for p in d.server_edits[mark:] if isinstance(p, dict) and isinstance(p.get("edit"), dict)]
    if recorded:
        return recorded, err
    return ([result] if _is_workspace_edit(result) else []), err


def action_edits(d: Any, action: Mapping[str, Any], timeout: float) -> Tuple[List[Dict[str, Any]], str]:
    """(WorkspaceEdits, via) for one code action: via = edit | resolve | command | none."""
    if _is_workspace_edit(action.get("edit")):
        return [dict(action["edit"])], "edit"
    if "data" in action and resolves_actions(d):
        res, err = d.request("codeAction/resolve", dict(action), timeout)
        if err is None and isinstance(res, dict):
            if _is_workspace_edit(res.get("edit")):
                return [res["edit"]], "resolve"
            action = res
    cmd: Any = action.get("command")
    if isinstance(cmd, str):
        cmd = action  # a bare Command
    if isinstance(cmd, dict) and cmd.get("command") in EDIT_ONLY_COMMANDS:
        edits, _ = follow_command(d, cmd, timeout)
        return edits, "command"
    return [], f"command-not-followed:{cmd.get('command')}" if isinstance(cmd, dict) else "none"


def quickfixes(d: Any, path: str, diag: Mapping[str, Any], timeout: float) -> Tuple[List[Dict[str, Any]], Error]:
    params = {"textDocument": {"uri": d.uri(path)}, "range": diag.get("range"),
              "context": {"diagnostics": [dict(diag)], "only": ["quickfix"], "triggerKind": 1}}
    res, err = d.request("textDocument/codeAction", params, timeout)
    kinds = lambda a: str(a.get("kind") or "")  # noqa: E731
    return [a for a in res or [] if isinstance(a, dict) and (kinds(a) == "quickfix" or kinds(a).startswith("quickfix."))], err


def organize_edits(d: Any, server_kind: str, path: str, timeout: float) -> Tuple[List[Dict[str, Any]], str]:
    """(WorkspaceEdits, via) of organize imports on one document; via "none" when not offered."""
    whole = lsp_range((0, 0), LineIndex(d.text(path)).end())
    params = {"textDocument": {"uri": d.uri(path)}, "range": whole,
              "context": {"diagnostics": [], "only": ["source.organizeImports"], "triggerKind": 1}}
    res, err = d.request("textDocument/codeAction", params, timeout)
    acts = [a for a in res or [] if isinstance(a, dict) and str(a.get("kind") or "").startswith("source.organizeImports")]
    if acts:
        edits, via = action_edits(d, acts[0], timeout)
        return edits, f"action:{via}"
    if server_kind in ORGANIZE_COMMANDS:
        edits, cerr = follow_command(d, {"command": ORGANIZE_COMMANDS[server_kind], "arguments": [d.uri(path)]}, timeout)
        return edits, "command" if cerr is None else f"command-error:{cerr[1]}"
    return [], "none" if err is None else f"error:{err[1]}"


def formatting(d: Any, path: str, options: Mapping[str, Any], timeout: float) -> Tuple[Optional[List[Dict[str, Any]]], Error]:
    res, err = d.request("textDocument/formatting", {"textDocument": {"uri": d.uri(path)}, "options": dict(options)}, timeout)
    return ([e for e in res if isinstance(e, dict)] if isinstance(res, list) else None), err


def completion(d: Any, path: str, line: int, char: int, timeout: float
               ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Error]:
    params = {"textDocument": {"uri": d.uri(path)}, "position": {"line": line, "character": char},
              "context": {"triggerKind": 1}}
    res, err = d.request("textDocument/completion", params, timeout)
    items = res.get("items") if isinstance(res, dict) else res
    defaults = res.get("itemDefaults") if isinstance(res, dict) else None
    return [i for i in items or [] if isinstance(i, dict)], dict(defaults or {}), err


def resolve_item(d: Any, item: Dict[str, Any], timeout: float) -> Tuple[Dict[str, Any], bool]:
    """(item, resolved): the resolved item when resolution succeeds, else the item itself."""
    res, err = d.request("completionItem/resolve", item, timeout)
    return (res, True) if err is None and isinstance(res, dict) else (item, False)


# ------------------------------------------------------------------ applying edits to the session
Applied = List[Tuple[str, str, Op]]  # (path, text before, change op)


class Editor:
    """Applies edited texts to a live session through ops, recording them in `history`."""

    def __init__(self, ctx: OracleContext, d: Any, history: Optional[List[Op]] = None) -> None:
        self.ctx, self.d = ctx, d
        self.history: List[Op] = history if history is not None else []
        self.failures: List[str] = []

    def run_ops(self, ops: Sequence[Op]) -> bool:
        """Apply ops (base.apply_history), record them, settle; False if an op failed or it did not settle."""
        if not ops:
            return True
        for op in ops:  # one at a time, so `history` holds exactly the ops that were applied
            errors = apply_history(self.ctx, self.d, [op])
            if errors:
                self.failures.append(errors[0])
                return False
            self.history.append(op)
        res = self.d.last_settle if self.ctx.race_delay_ms is None and self.d.last_settle is not None else self.d.settle()
        if not res.settled:
            self.failures.append(f"not settled: {res.reason}")
        return bool(res.settled)

    def open(self, paths: Sequence[str]) -> Tuple[bool, List[str]]:
        docs = self.d.store.docs
        missing = [p for p in dict.fromkeys(paths) if not (p in docs and docs[p].open)]
        return self.run_ops([Op("open", path=p) for p in missing]), missing

    def change(self, texts: Mapping[str, str]) -> Tuple[bool, Applied]:
        applied: Applied = []
        for path in sorted(texts):
            before = self.d.text(path)
            op = minimal_change(path, before, texts[path])
            if op is not None:
                applied.append((path, before, op))
        return self.run_ops([op for _, _, op in applied]), applied

    def revert(self, applied: Applied, opened: Sequence[str]) -> bool:
        ops: List[Op] = []
        for path, before, op in reversed(applied):
            try:
                ops.append(inverse_change(op, before))
            except OpError:
                after = self.d.text(path)
                ops.append(Op("change", path=path, start=(0, 0), end=LineIndex(after).end(), text=before))
        ok = self.run_ops(ops)
        ok = self.run_ops([Op("close", path=p) for p in opened]) and ok
        return ok and all(self.d.store.docs[p].text == before for p, before, _ in applied if p in self.d.store.docs)

    def open_paths(self) -> List[str]:
        return self.d.store.open_paths()


__all__ = [
    "APPLY_EDIT_WAIT_S", "Applied", "EDIT_ONLY_COMMANDS", "Editor", "ORGANIZE_COMMANDS", "action_edits", "capabilities", "completion",
    "diagnostics", "follow_command", "formatting", "organize_edits", "quickfixes", "read_doc", "rel_uri",
    "resolve_item", "resolves_actions", "resolves_items", "supports_formatting",
]
