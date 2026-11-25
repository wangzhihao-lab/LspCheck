"""Session: a live language server plus the workspace it is looking at.

Executes the declarative steps of a Scenario and records what the server said,
so the same step list can be replayed against several server versions.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

from lspclient import LspClient, LspError
from scenario import Range, Scenario, Step
from snapshots import normalize_diagnostics, short as _short
from textdoc import Document, language_for, uri_for

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ session
class Session:
    """A live server plus the workspace it is looking at."""

    def __init__(
        self,
        scenario: Scenario,
        workspace: str,
        client: LspClient,
        quiet: Optional[float] = None,
    ) -> None:
        self.scenario = scenario
        self.workspace = workspace
        self.client = client
        self.quiet = quiet if quiet is not None else scenario.quiet_seconds
        self.docs: Dict[str, Document] = {}
        self.undo_stack: Dict[str, List[Tuple[Range, str]]] = {}
        self.snapshots: List[Dict[str, Any]] = []
        self.request_results: List[Dict[str, Any]] = []
        self.probe_results: Dict[str, Any] = {}
        self.timeline: List[Dict[str, Any]] = []

    # ---- helpers
    def abspath(self, rel: str) -> str:
        return os.path.join(self.workspace, rel)

    def uri(self, rel: str) -> str:
        return uri_for(self.abspath(rel))

    def doc(self, rel: str) -> Document:
        if rel not in self.docs:
            path = self.abspath(rel)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            self.docs[rel] = Document(uri=uri_for(path), path=path, language_id=language_for(path), text=text)
        return self.docs[rel]

    def watched(self) -> List[str]:
        return self.scenario.watch or list(self.docs.keys())

    # ---- protocol operations
    def do_open(self, rel: str) -> None:
        d = self.doc(rel)
        if d.version == 0:
            d.version = 1
        self.client.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": d.uri,
                    "languageId": d.language_id,
                    "version": d.version,
                    "text": d.text,
                }
            },
        )
        d.open = True

    def do_edit(self, rel: str, r: Range, new_text: str, incremental: bool = True) -> None:
        d = self.doc(rel)
        inverse = d.apply(r, new_text)
        self.undo_stack.setdefault(rel, []).append(inverse)
        version = d.bump()
        if incremental:
            changes = [{"range": r, "text": new_text}]
        else:
            changes = [{"text": d.text}]
        self.client.notify(
            "textDocument/didChange",
            {"textDocument": {"uri": d.uri, "version": version}, "contentChanges": changes},
        )

    def do_multi_edit(self, rel: str, edits: List[Tuple[Range, str]]) -> None:
        """Apply a batch locally in order and send it as one didChange."""
        d = self.doc(rel)
        inverses: List[Tuple[Range, str]] = []
        changes: List[Dict[str, Any]] = []
        for r, new_text in edits:
            inverses.append(d.apply(r, new_text))
            changes.append({"range": r, "text": new_text})
        # Undo reverses the batch, last edit first.
        for inv in reversed(inverses):
            self.undo_stack.setdefault(rel, []).append(inv)
        version = d.bump()
        self.client.notify(
            "textDocument/didChange",
            {"textDocument": {"uri": d.uri, "version": version}, "contentChanges": changes},
        )

    def do_full_edit(self, rel: str, new_text: str) -> None:
        d = self.doc(rel)
        old = d.text
        d.text = new_text
        self.undo_stack.setdefault(rel, []).append((_whole(new_text), old))
        version = d.bump()
        self.client.notify(
            "textDocument/didChange",
            {"textDocument": {"uri": d.uri, "version": version}, "contentChanges": [{"text": new_text}]},
        )

    def do_undo(self, rel: str) -> None:
        stack = self.undo_stack.get(rel) or []
        if not stack:
            raise LspError(f"nothing to undo for {rel}")
        r, text = stack.pop()
        d = self.doc(rel)
        d.apply(r, text)
        version = d.bump()
        self.client.notify(
            "textDocument/didChange",
            {"textDocument": {"uri": d.uri, "version": version}, "contentChanges": [{"range": r, "text": text}]},
        )

    def do_save(self, rel: str) -> None:
        d = self.doc(rel)
        with open(d.path, "w", encoding="utf-8") as f:
            f.write(d.text)
        self.client.notify("textDocument/didSave", {"textDocument": {"uri": d.uri}, "text": d.text})

    def do_close(self, rel: str) -> None:
        """Close the document and discard the buffer.

        An editor that closes a file without saving throws the unsaved text
        away; the next open reads from disk. Keeping the dirty text in the
        client model would make the harness disagree with the server about what
        a reopen means, so the mirror is reloaded from disk here.
        """
        d = self.doc(rel)
        self.client.notify("textDocument/didClose", {"textDocument": {"uri": d.uri}})
        d.open = False
        try:
            with open(d.path, "r", encoding="utf-8") as f:
                on_disk = f.read()
        except OSError:
            return
        if on_disk != d.text:
            d.text = on_disk
            self.undo_stack.pop(rel, None)
            d.version = 0  # the next didOpen starts a new version sequence

    def run_probes(self) -> Dict[str, Any]:
        """Execute the scenario's probe requests and normalize the replies."""
        out: Dict[str, Any] = {}
        for st in self.scenario.probes:
            try:
                res = self.client.request(st.method, st.params_fn(self), timeout=60.0)
                out[st.label] = st.normalize(res) if st.normalize else _trim(res)
                # Recorded so a later probe can build its params from an earlier
                # probe's reply (codeAction -> codeAction/resolve, for instance).
                self.request_results.append(
                    {"label": st.label, "method": st.method, "ok": True, "result": _trim(res), "raw": res,
                     "norm": out[st.label]}
                )
            except (LspError, ValueError, OSError) as exc:
                out[st.label] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
                self.request_results.append(
                    {"label": st.label, "method": st.method, "ok": False, "error": str(exc)[:200]}
                )
        self.probe_results = out
        return out

    def do_apply_workspace_edit(self, edit: Any, optional: bool = False) -> bool:
        if not isinstance(edit, dict):
            if optional:
                logger.info("no WorkspaceEdit to apply (%s) -- skipped", type(edit).__name__)
                return False
            raise ValueError(f"not a WorkspaceEdit: {type(edit).__name__}")
        per_uri: Dict[str, List[Dict[str, Any]]] = {}
        for dc in edit.get("documentChanges") or []:
            uri = (dc.get("textDocument") or {}).get("uri")
            if uri and dc.get("edits"):
                per_uri.setdefault(uri, []).extend(dc["edits"])
        for uri, edits in (edit.get("changes") or {}).items():
            per_uri.setdefault(uri, []).extend(edits)
        if not per_uri:
            if optional:
                logger.info("WorkspaceEdit carried no text edits -- skipped")
                return False
            raise ValueError("WorkspaceEdit carried no text edits")
        by_uri = {d.uri: rel for rel, d in self.docs.items()}
        for uri, edits in per_uri.items():
            rel = by_uri.get(uri)
            if rel is None:
                logger.warning("edit for untracked document %s -- skipped", uri)
                continue
            # Apply bottom-up so earlier ranges stay valid.
            ordered = sorted(
                edits,
                key=lambda e: (e["range"]["start"]["line"], e["range"]["start"]["character"]),
                reverse=True,
            )
            for e in ordered:
                self.do_edit(rel, e["range"], e.get("newText", ""))
        return True

    def find_request(self, label: str) -> Optional[Dict[str, Any]]:
        for r in reversed(self.request_results):
            if r["label"] == label and r.get("ok"):
                return r
        return None

    def take_snapshot(self, label: str) -> Dict[str, Any]:
        snap = {"label": label, "diagnostics": {}, "raw": {}, "probes": dict(self.probe_results)}
        for rel in self.watched():
            if not os.path.exists(self.abspath(rel)) and not (
                rel in self.docs and self.docs[rel].open
            ):
                # A watched path can be absent -- the target of a rename that has
                # not happened yet, or the source of one that has. Absence is
                # itself state, and recording it keeps the replay and the fresh
                # run comparable instead of diffing different file sets.
                snap["diagnostics"][rel] = "absent"
                snap["raw"][rel] = "absent"
                continue
            try:
                d = self.doc(rel)
            except OSError:
                snap["diagnostics"][rel] = "absent"
                snap["raw"][rel] = "absent"
                continue
            raw = self.client.diagnostics_for(d.uri)
            snap["diagnostics"][rel] = normalize_diagnostics(raw)
            snap["raw"][rel] = [
                {"range": x.get("range"), "message": _short(x.get("message", "")), "severity": x.get("severity"), "code": x.get("code")}
                for x in (raw or [])
            ]
        self.snapshots.append(snap)
        return snap

    def has_doc(self, rel: str) -> bool:
        return rel in self.docs or os.path.exists(self.abspath(rel))

    def quiesce(self, rel: Optional[str] = None, quiet: Optional[float] = None) -> bool:
        q = quiet if quiet is not None else self.quiet
        targets = [rel] if rel else []
        for t in targets:
            d = self.docs.get(t)
            if d is not None and d.open:
                self.client.wait_for_diagnostics(
                    d.uri, min_version=d.version, timeout=min(45.0, self.scenario.quiesce_timeout)
                )
        return self.client.wait_quiescent(quiet=q, timeout=self.scenario.quiesce_timeout)

    # ---- driver
    def run_steps(self, steps: List[Step]) -> None:
        for i, st in enumerate(steps):
            t0 = time.monotonic()
            entry: Dict[str, Any] = {"i": i, "kind": st.kind, "label": st.label}
            try:
                self._exec(st)
                entry["ok"] = True
            except (LspError, ValueError, OSError) as exc:
                entry["ok"] = False
                entry["error"] = f"{type(exc).__name__}: {exc}"
                self.timeline.append(entry)
                raise
            entry["dt"] = round(time.monotonic() - t0, 3)
            self.timeline.append(entry)

    def _exec(self, st: Step) -> None:
        k = st.kind
        if k == "open":
            self.do_open(st.path)
        elif k == "edit":
            d = self.doc(st.path)
            self.do_edit(st.path, st.range_fn(d.text), st.text, st.incremental)
        elif k == "multi_edit":
            self.do_multi_edit(st.path, st.range_fn(self.doc(st.path).text))
        elif k == "full_edit":
            self.do_full_edit(st.path, st.text)
        elif k == "undo":
            n = st.count if st.count and st.count > 0 else len(self.undo_stack.get(st.path) or [])
            for _ in range(n):
                self.do_undo(st.path)
        elif k == "save":
            self.do_save(st.path)
        elif k == "close":
            self.do_close(st.path)
        elif k == "wait":
            time.sleep(st.seconds)
        elif k == "quiesce":
            self.quiesce(st.path)
        elif k == "snapshot":
            self.take_snapshot(st.label)
        elif k == "change_settings":
            new = st.params_fn(self)
            merged = _merge(self.client.settings, new)
            self.client.settings = merged
            self.client.notify("workspace/didChangeConfiguration", {"settings": merged})
        elif k == "add_folder":
            uri = uri_for(self.abspath(st.path))
            self.client.notify(
                "workspace/didChangeWorkspaceFolders",
                {"event": {"added": [{"uri": uri, "name": st.path}], "removed": []}},
            )
        elif k == "fs_write":
            path = self.abspath(st.path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            existed = os.path.exists(path)
            with open(path, "w", encoding="utf-8") as f:
                f.write(st.text)
            self.client.notify(
                "workspace/didChangeWatchedFiles",
                {"changes": [{"uri": uri_for(path), "type": 2 if existed else 1}]},
            )
        elif k == "fs_rename":
            src, dst = self.abspath(st.path), self.abspath(st.text)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            self.client.notify(
                "workspace/didChangeWatchedFiles",
                {"changes": [{"uri": uri_for(src), "type": 3}, {"uri": uri_for(dst), "type": 1}]},
            )
        elif k == "apply_workspace_edit":
            try:
                edit = st.params_fn(self)
            except (ValueError, KeyError, TypeError):
                if not st.optional:
                    raise
                edit = None
            self.do_apply_workspace_edit(edit, optional=st.optional)
        elif k == "request":
            params = st.params_fn(self)
            try:
                res = self.client.request(st.method, params, timeout=60.0)
                self.request_results.append(
                    {
                        "label": st.label,
                        "method": st.method,
                        "ok": True,
                        "result": _trim(res),
                        "raw": res,
                        "norm": st.normalize(res) if st.normalize else None,
                    }
                )
            except LspError as exc:
                self.request_results.append({"label": st.label, "method": st.method, "ok": False, "error": str(exc)})
        else:
            raise ValueError(f"unknown step kind: {k}")


def _merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _whole(text: str) -> Range:
    lines = text.split("\n")
    return {"start": {"line": 0, "character": 0}, "end": {"line": len(lines) - 1, "character": len(lines[-1])}}


def _trim(obj: Any, limit: int = 4000) -> Any:
    try:
        s = json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return str(obj)[:limit]
    return json.loads(s) if len(s) <= limit else s[:limit] + "...<trimmed>"


__all__ = ["Session"]
