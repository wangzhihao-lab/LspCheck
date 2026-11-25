"""Client operations: apply serializable Ops (model.Op) to a live session as LSP notifications,
keep the authoritative text of every document, invert edits, and load/save Op lists as JSON.
Positions are (line, UTF-16 character) under LSP line rules: only "\\n", "\\r\\n" and "\\r" end
a line (str.splitlines also splits on form feeds and U+2028). Invalid positions raise OpError
instead of being clamped, so the client can never drift from the server.

Run line: imported by driver.py and the oracle layer; not run directly.
"""

from __future__ import annotations

import bisect
import json
import logging
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote, unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from framing import LspError  # noqa: E402
from model import Op, Pos  # noqa: E402
from textdoc import Document  # noqa: E402
from request_ops import apply_request  # noqa: E402

logger = logging.getLogger(__name__)

OP_KINDS = ("open", "change", "close", "save", "set_config", "fs_write", "fs_rename", "wait", "request")
_EOL = re.compile(r"\r\n|\r|\n")
LANGUAGE_IDS: Dict[str, str] = {
    ".ts": "typescript", ".mts": "typescript", ".cts": "typescript", ".tsx": "typescriptreact",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascriptreact",
    ".py": "python", ".pyi": "python", ".rs": "rust", ".go": "go", ".java": "java", ".json": "json",
}
Range = Dict[str, Dict[str, int]]


class OpError(ValueError):
    """An Op that cannot be applied to the current state (unknown path, bad range, ...)."""


# ------------------------------------------------------------ text arithmetic
def utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


class LineIndex:
    """Conversion between character offsets and LSP positions for one text."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.starts: List[int] = [0] + [m.end() for m in _EOL.finditer(text)]

    def line_end(self, line: int) -> int:
        """Offset where `line`'s content ends (before its terminator)."""
        if line + 1 >= len(self.starts):
            return len(self.text)
        end = self.starts[line + 1]
        return end - 2 if self.text[end - 2 : end] == "\r\n" else end - 1

    def line_text(self, line: int) -> str:
        return self.text[self.starts[line] : self.line_end(line)]

    def offset(self, pos: Pos) -> int:
        """Offset of an LSP position; raises OpError if it is not inside the text."""
        line, char = int(pos[0]), int(pos[1])
        if line < 0 or char < 0 or line >= len(self.starts):
            raise OpError(f"position {tuple(pos)} outside the document ({len(self.starts)} lines)")
        start, end = self.starts[line], self.line_end(line)
        row = self.text[start:end]
        if row.isascii():
            if char > len(row):
                raise OpError(f"position {tuple(pos)} beyond the end of line {line}")
            return start + char
        units = 0
        for i, ch in enumerate(row):
            if units == char:
                return start + i
            units += 2 if ord(ch) > 0xFFFF else 1
            if units > char:
                raise OpError(f"position {tuple(pos)} splits a surrogate pair")
        if units == char:
            return end
        raise OpError(f"position {tuple(pos)} beyond the end of line {line}")

    def position(self, offset: int) -> Pos:
        """LSP position of a character offset (clamped to the text)."""
        offset = max(0, min(offset, len(self.text)))
        line = bisect.bisect_right(self.starts, offset) - 1
        return (line, utf16_len(self.text[self.starts[line] : offset]))

    def end(self) -> Pos:
        return self.position(len(self.text))


def lsp_range(start: Pos, end: Pos) -> Range:
    return {"start": {"line": start[0], "character": start[1]}, "end": {"line": end[0], "character": end[1]}}


def apply_change(text: str, start: Pos, end: Pos, new_text: str) -> Tuple[str, str, Pos]:
    """Apply one range edit. Returns (new text, replaced text, end of the inserted text)."""
    idx = LineIndex(text)
    s, e = idx.offset(start), idx.offset(end)
    if e < s:
        raise OpError(f"range end {tuple(end)} before start {tuple(start)}")
    out = text[:s] + new_text + text[e:]
    return out, text[s:e], LineIndex(out).position(s + len(new_text))


def change_at_offsets(path: str, text: str, start: int, end: int, new_text: str, delay_ms: int = 0) -> Op:
    """A change Op replacing text[start:end] (character offsets) with `new_text`."""
    idx = LineIndex(text)
    return Op("change", path=path, start=idx.position(start), end=idx.position(end), text=new_text, delay_ms=delay_ms)


def inverse_change(op: Op, text_before: str) -> Op:
    """The change that undoes `op` when applied right after it to the edited text."""
    if op.kind != "change" or op.start is None or op.end is None:
        raise OpError(f"only change ops with a range have an inverse, got {op.kind!r}")
    after, replaced, new_end = apply_change(text_before, op.start, op.end, op.text)
    inv = Op("change", path=op.path, start=tuple(op.start), end=new_end, text=replaced, delay_ms=op.delay_ms)
    if apply_change(after, inv.start, inv.end, inv.text)[0] != text_before:  # type: ignore[arg-type]
        raise OpError("edit joins or splits a line terminator; no single-range inverse")
    return inv


def invert_ops(ops: Sequence[Op], texts: Dict[str, str]) -> List[Op]:
    """Inverse of a sequence of change ops (waits are skipped), given each path's text
    before the first op: the per-op inverses in reverse order."""
    cur = dict(texts)
    inverses: List[Op] = []
    for op in ops:
        if op.kind in ("wait", "request"):
            continue
        if op.path not in cur:
            raise OpError(f"no starting text for {op.path}")
        inverses.append(inverse_change(op, cur[op.path]))
        cur[op.path] = apply_change(cur[op.path], op.start, op.end, op.text)[0]  # type: ignore[arg-type]
    return list(reversed(inverses))


# ------------------------------------------------------------ files and URIs
def path_to_uri(path: str) -> str:
    """file:// URI of an absolute path, percent-encoded the way editors send it."""
    return "file://" + quote(os.path.abspath(path), safe="/")


def uri_to_path(uri: str) -> str:
    return unquote(urlparse(uri).path)


def language_id(path: str) -> str:
    return LANGUAGE_IDS.get(os.path.splitext(path)[1].lower(), "plaintext")


def read_text(path: str) -> str:
    """File contents with line terminators preserved exactly."""
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    """Recursive dict merge; `over` wins. Inputs are not modified."""
    out = dict(base)
    for k, v in over.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


class DocumentStore:
    """Authoritative client-side text of every document a session has touched,
    keyed by workspace-relative path ('/' separators)."""

    def __init__(self, root: str, restart_version_on_reopen: bool = True) -> None:
        self.root = os.path.abspath(root)
        self.restart_version_on_reopen = restart_version_on_reopen
        self.docs: Dict[str, Document] = {}
        self.sent_index: Dict[str, int] = {}  # notification count before the latest didOpen/didChange
        self.last_sent_at = time.monotonic()

    def abspath(self, path: str) -> str:
        return os.path.join(self.root, path)

    def uri(self, path: str) -> str:
        return path_to_uri(self.abspath(path))

    def doc(self, path: str) -> Document:
        d = self.docs.get(path)
        if d is None:
            try:
                text = read_text(self.abspath(path))
            except OSError as exc:
                raise OpError(f"cannot read {path}: {exc}") from exc
            d = Document(self.uri(path), self.abspath(path), language_id(path), text, version=0)
            self.docs[path] = d
        return d

    def require_open(self, path: str) -> Document:
        d = self.docs.get(path)
        if d is None or not d.open:
            raise OpError(f"{path} is not open")
        return d

    def open_paths(self) -> List[str]:
        return sorted(p for p, d in self.docs.items() if d.open)

    def reload(self, path: str) -> None:
        """Replace the buffer with the file on disk; forget the document if it is gone."""
        try:
            self.docs[path].text = read_text(self.abspath(path))
        except OSError:
            self.docs.pop(path, None)


# ------------------------------------------------------------ applying ops
@dataclass
class OpOutcome:
    op: Op
    sent: List[str] = field(default_factory=list)  # LSP methods sent, in order
    seconds: float = 0.0
    result: Any = None  # e.g. the willRenameFiles WorkspaceEdit (recorded, not applied)
    error: str = ""


class OpApplier:
    """Applies Ops to one session; the handler for kind K is the method `op_K`, so a
    subclass can add kinds. `client` needs notify/request/notification_count,
    `server_capabilities` and `settings` (lspclient.LspClient has all of them)."""

    def __init__(self, client: Any, store: DocumentStore, request_timeout_s: float = 30.0,
                 registered: Optional[Callable[[str], bool]] = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.client = client
        self.store = store
        self.request_timeout_s = request_timeout_s
        self.registered = registered
        self.sleep = sleep

    def apply(self, op: Op) -> OpOutcome:
        handler = getattr(self, f"op_{op.kind}", None)
        if handler is None:
            raise OpError(f"unknown op kind {op.kind!r}")
        t0, out = time.monotonic(), OpOutcome(op)
        handler(op, out)
        if op.delay_ms > 0:
            self.sleep(op.delay_ms / 1000.0)
        out.seconds = round(time.monotonic() - t0, 4)
        return out

    def notify(self, out: OpOutcome, method: str, params: Any, path: Optional[str] = None,
               workspace: bool = False) -> None:
        """Counted *before* sending: any later publish is at or after the index. A workspace-level
        change (files, settings) may change every open document's diagnostics, so all need a new one."""
        mark = self.client.notification_count()
        for p in ([path] if path is not None else []) + (self.store.open_paths() if workspace else []):
            self.store.sent_index[p] = mark
        self.client.notify(method, params)
        self.store.last_sent_at = time.monotonic()
        out.sent.append(method)

    def supports_file_op(self, name: str) -> bool:
        """name: willRename | didRename | ... (static capability or dynamic registration)."""
        caps = getattr(self.client, "server_capabilities", None) or {}
        static = ((caps.get("workspace") or {}).get("fileOperations") or {}).get(name)  # an empty {} counts
        return static not in (None, False) or bool(self.registered and self.registered(f"workspace/{name}Files"))

    def send_open(self, out: OpOutcome, path: str, d: Document) -> None:
        d.version = 1 if d.version == 0 or self.store.restart_version_on_reopen else d.version + 1
        item = {"uri": d.uri, "languageId": d.language_id, "version": d.version, "text": d.text}
        self.notify(out, "textDocument/didOpen", {"textDocument": item}, path)
        d.open = True

    def op_open(self, op: Op, out: OpOutcome) -> None:
        d = self.store.doc(op.path)
        if d.open:
            raise OpError(f"{op.path} is already open")
        self.send_open(out, op.path, d)

    def op_change(self, op: Op, out: OpOutcome) -> None:
        d = self.store.require_open(op.path)
        if op.start is None or op.end is None:
            raise OpError("change needs start and end")
        d.text, replaced, _ = apply_change(d.text, op.start, op.end, op.text)
        rng = lsp_range(op.start, op.end)
        d.version += 1
        d.history.append((rng, op.text, replaced))
        changes = [{"range": rng, "text": op.text}]
        self.notify(out, "textDocument/didChange", {"textDocument": {"uri": d.uri, "version": d.version},
                                                     "contentChanges": changes}, op.path)

    def op_close(self, op: Op, out: OpOutcome) -> None:
        d = self.store.require_open(op.path)
        self.notify(out, "textDocument/didClose", {"textDocument": {"uri": d.uri}})
        d.open = False
        self.store.reload(op.path)  # closing without saving discards the buffer, as an editor does

    def op_save(self, op: Op, out: OpOutcome) -> None:
        d = self.store.require_open(op.path)
        write_text(d.path, d.text)
        self.notify(out, "textDocument/didSave", {"textDocument": {"uri": d.uri}, "text": d.text})

    def op_set_config(self, op: Op, out: OpOutcome) -> None:
        merged = deep_merge(getattr(self.client, "settings", None) or {}, op.settings or {})
        self.client.settings = merged  # workspace/configuration answers come from here
        self.notify(out, "workspace/didChangeConfiguration", {"settings": merged}, workspace=True)

    def op_fs_write(self, op: Op, out: OpOutcome) -> None:
        path = self.store.abspath(op.path)
        existed = os.path.exists(path)
        write_text(path, op.text)
        d = self.store.docs.get(op.path)
        if d is not None and d.open:
            logger.warning("fs_write on open document %s: editor buffer kept", op.path)
        elif d is not None:
            d.text = op.text
        change = {"uri": self.store.uri(op.path), "type": 2 if existed else 1}
        self.notify(out, "workspace/didChangeWatchedFiles", {"changes": [change]}, workspace=True)

    def op_fs_rename(self, op: Op, out: OpOutcome) -> None:
        """willRenameFiles (edit recorded, not applied), didClose, move on disk,
        didRenameFiles, didChangeWatchedFiles, then didOpen of the new path with the buffer."""
        old, new = op.path, op.new_path
        src, dst = self.store.abspath(old), self.store.abspath(new)
        if not new or not os.path.exists(src) or os.path.exists(dst):
            raise OpError(f"cannot rename {old!r} to {new!r}")
        files = [{"oldUri": self.store.uri(old), "newUri": self.store.uri(new)}]
        if self.supports_file_op("willRename"):
            try:
                out.result = self.client.request("workspace/willRenameFiles", {"files": files},
                                                 timeout=self.request_timeout_s)
                out.sent.append("workspace/willRenameFiles")
            except LspError as exc:
                out.error = f"willRenameFiles: {exc}"[:300]
        d = self.store.docs.pop(old, None)
        if d is not None and d.open:
            self.notify(out, "textDocument/didClose", {"textDocument": {"uri": d.uri}})
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        if self.supports_file_op("didRename"):
            self.notify(out, "workspace/didRenameFiles", {"files": files})
        changes = [{"uri": files[0]["oldUri"], "type": 3}, {"uri": files[0]["newUri"], "type": 1}]
        self.notify(out, "workspace/didChangeWatchedFiles", {"changes": changes}, workspace=True)
        if d is not None:
            moved = Document(uri=self.store.uri(new), path=dst, language_id=language_id(new), text=d.text,
                             version=d.version)
            self.store.docs[new] = moved
            if d.open:
                self.send_open(out, new, moved)

    op_request = apply_request  # a position query inside a history (request_ops.py)

    def op_wait(self, op: Op, out: OpOutcome) -> None:
        """Nothing to send: the delay_ms sleep that follows every op is the wait."""


# ------------------------------------------------------------ JSON
def ops_to_json(ops: Sequence[Op]) -> List[Dict[str, Any]]:
    return [o.to_json() for o in ops]


def ops_from_json(data: Any) -> List[Op]:
    """Ops from a JSON list (or an object with an "ops" list); validates kinds and fields."""
    items = data.get("ops", []) if isinstance(data, dict) else data
    out: List[Op] = []
    for d in items or []:
        if not isinstance(d, dict) or d.get("kind") not in OP_KINDS:
            raise OpError(f"not an op: {d!r}")
        try:
            out.append(Op.from_json(d))
        except TypeError as exc:
            raise OpError(f"bad op fields in {d!r}: {exc}") from exc
    return out


def save_ops(path: str, ops: Sequence[Op]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ops_to_json(ops), f, ensure_ascii=False, indent=1)


def load_ops(path: str) -> List[Op]:
    with open(path, "r", encoding="utf-8") as f:
        return ops_from_json(json.load(f))


__all__ = [
    "LANGUAGE_IDS", "LineIndex", "OP_KINDS", "DocumentStore", "OpApplier", "OpError", "OpOutcome",
    "apply_change", "change_at_offsets", "deep_merge", "inverse_change", "invert_ops",
    "language_id", "load_ops", "lsp_range", "ops_from_json", "ops_to_json", "path_to_uri", "read_text",
    "save_ops", "uri_to_path", "utf16_len", "write_text",
]
