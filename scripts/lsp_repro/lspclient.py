"""Minimal headless LSP client (JSON-RPC 2.0 over stdio, Content-Length framing).

Built for reproducing state-inconsistency bugs in language servers. Every message is
logged to a JSONL file so a run is auditable after the fact.

Run line: python3 scripts/lsp_repro/runner.py --case pyright_8946
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from capabilities import client_capabilities
from framing import ACTIVITY_METHODS, AUTO_REPLY_NULL, LspError, Notification, same_uri

logger = logging.getLogger(__name__)

class LspClient:
    """Spawn a language server and talk LSP to it over stdio."""

    def __init__(
        self,
        cmd: List[str],
        log_path: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.cmd = cmd
        self.log_path = log_path
        self.settings = settings or {}
        self._next_id = 1
        self._lock = threading.Lock()
        self._responses: Dict[int, Any] = {}
        self._resp_events: Dict[int, threading.Event] = {}
        self.notifications: List[Notification] = []
        # Server->client requests, in arrival order (method + params), and optional
        # per-method answer hooks consulted before the built-in replies.
        self.server_requests: List[Notification] = []
        self.request_handlers: Dict[str, Callable[[Any], Any]] = {}
        self._last_activity = time.monotonic()
        self._alive = True
        self._log_lock = threading.Lock()
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        self._log = open(log_path, "w", encoding="utf-8")

        full_env = dict(os.environ)
        if env:
            full_env.update(env)
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=full_env,
            bufsize=0,
        )
        self._record("meta", {"cmd": cmd, "cwd": cwd, "pid": self.proc.pid})
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._errreader = threading.Thread(target=self._stderr_loop, daemon=True)
        self._errreader.start()

    # ---------------------------------------------------------------- logging
    def _record(self, direction: str, payload: Any) -> None:
        with self._log_lock:
            try:
                self._log.write(
                    json.dumps(
                        {"t": round(time.monotonic(), 4), "dir": direction, "msg": payload},
                        default=str,
                    )
                    + "\n"
                )
                self._log.flush()
            except (ValueError, OSError):
                pass

    # ------------------------------------------------------------------- I/O
    def _stderr_loop(self) -> None:
        try:
            for raw in iter(self.proc.stderr.readline, b""):
                self._record("stderr", raw.decode("utf-8", "replace").rstrip())
        except (OSError, ValueError):
            pass

    def _read_message(self) -> Optional[Dict[str, Any]]:
        headers: Dict[str, str] = {}
        stream = self.proc.stdout
        while True:
            line = stream.readline()
            if not line:
                return None
            line = line.decode("utf-8", "replace").strip()
            if line == "":
                break
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        length = int(headers.get("content-length", 0))
        if length <= 0:
            return None
        buf = b""
        while len(buf) < length:
            chunk = stream.read(length - len(buf))
            if not chunk:
                return None
            buf += chunk
        try:
            return json.loads(buf.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            self._record("parse_error", buf.decode("utf-8", "replace")[:2000])
            return {}

    def _read_loop(self) -> None:
        while self._alive:
            try:
                msg = self._read_message()
            except (OSError, ValueError):
                break
            if msg is None:
                break
            if not msg:
                continue
            self._record("recv", msg)
            self._last_activity = time.monotonic()
            if "id" in msg and "method" not in msg:  # a response; lsp4j omits a null "result"
                rid = msg["id"]
                with self._lock:
                    self._responses[rid] = msg
                    ev = self._resp_events.get(rid)
                if ev:
                    ev.set()
            elif "id" in msg and "method" in msg:
                with self._lock:
                    self.server_requests.append(Notification(msg["method"], msg.get("params")))
                self._handle_server_request(msg)
            elif "method" in msg:
                with self._lock:
                    self.notifications.append(Notification(msg["method"], msg.get("params")))
        self._alive = False
        # Wake every pending request: the server is gone, so waiting out the full
        # timeout would only delay the LspError the caller gets anyway.
        with self._lock:
            pending = list(self._resp_events.values())
        for ev in pending:
            ev.set()

    def _handle_server_request(self, msg: Dict[str, Any]) -> None:
        method = msg["method"]
        handler = self.request_handlers.get(method)
        if handler is not None:
            try:
                result = handler(msg.get("params"))
            except Exception as exc:  # noqa: BLE001  (a failing hook must still answer the server)
                self._record("meta", {"request_handler_error": f"{method}: {type(exc).__name__}: {exc}"})
                result = None
        elif method == "workspace/configuration":
            items = (msg.get("params") or {}).get("items") or [{}]
            result = [self._config_for(it.get("section")) for it in items]
        elif method == "window/showMessageRequest":
            result = None
        elif method in AUTO_REPLY_NULL:
            result = None
        else:
            result = None
        self._send({"jsonrpc": "2.0", "id": msg["id"], "result": result})

    def _config_for(self, section: Optional[str]) -> Any:
        if not section:
            return self.settings
        node: Any = self.settings
        for part in section.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return {}
        return node

    def _send(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        self._record("send", payload)
        # Our own traffic counts as activity: otherwise "no message for N seconds"
        # is already true the instant we push a didChange, and quiescence is a no-op.
        self._last_activity = time.monotonic()
        try:
            self.proc.stdin.write(header + body)
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise LspError(f"server stdin closed: {exc}") from exc

    # -------------------------------------------------------------- requests
    def request(self, method: str, params: Any = None, timeout: float = 60.0) -> Any:
        with self._lock:
            rid = self._next_id
            self._next_id += 1
            ev = threading.Event()
            self._resp_events[rid] = ev
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:  # JSON-RPC: omit rather than send null (TS 7 rejects null)
            payload["params"] = params
        self._send(payload)
        if not ev.wait(timeout):
            raise LspError(f"timeout after {timeout}s waiting for {method} (id={rid})", request_id=rid)
        with self._lock:
            msg = self._responses.pop(rid, None)
            self._resp_events.pop(rid, None)
        if msg is None:
            raise LspError(f"no response recorded for {method}")
        if "error" in msg:
            err = msg["error"]
            raise LspError(f"{method} -> {err}", code=err.get("code") if isinstance(err, dict) else None)
        return msg.get("result")

    def notify(self, method: str, params: Any = None) -> None:
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    # ------------------------------------------------------------- lifecycle
    def initialize(
        self,
        root_uri: str,
        capabilities: Optional[Dict[str, Any]] = None,
        init_options: Any = None,
        timeout: float = 120.0,
        extra_folder_uris: Optional[List[str]] = None,
    ) -> Any:
        params = {
            "processId": os.getpid(),
            "clientInfo": {"name": "lsp-repro-harness", "version": "0.1"},
            "locale": "en",
            "rootPath": root_uri.replace("file://", ""),
            "rootUri": root_uri,
            "capabilities": capabilities or client_capabilities(),
            "initializationOptions": init_options,
            "trace": "off",
            "workspaceFolders": [{"uri": root_uri, "name": "root"}]
            + [
                {"uri": u, "name": u.rsplit("/", 1)[-1] or f"extra{i}"}
                for i, u in enumerate(extra_folder_uris or [])
            ],
        }
        result = self.request("initialize", params, timeout=timeout)
        self.server_capabilities = (result or {}).get("capabilities") or {}
        self.notify("initialized", {})
        if self.settings:
            self.notify("workspace/didChangeConfiguration", {"settings": self.settings})
        return result

    def shutdown(self, timeout: float = 15.0) -> None:
        try:
            self.request("shutdown", None, timeout=timeout)
        except (LspError, OSError):
            pass
        try:
            self.notify("exit")
        except (LspError, OSError):
            pass
        self.stop()

    def stop(self, grace: float = 5.0) -> None:
        self._alive = False
        deadline = time.monotonic() + grace
        while self.proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if self.proc.poll() is None:
            self._record("meta", {"kill": "terminate"})
            self.proc.terminate()
            deadline = time.monotonic() + grace
            while self.proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
        if self.proc.poll() is None:
            self._record("meta", {"kill": "kill"})
            self.proc.kill()
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            try:
                if stream:
                    stream.close()
            except OSError:
                pass
        with self._log_lock:
            try:
                self._log.close()
            except OSError:
                pass

    # -------------------------------------------------------------- waiting
    def wait_quiescent(self, quiet: float = 2.0, timeout: float = 90.0) -> bool:
        """Block until no server->client message arrives for `quiet` seconds."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self._alive and self.proc.poll() is not None:
                return False
            idle = time.monotonic() - self._last_activity
            if idle >= quiet:
                return True
            time.sleep(min(0.1, max(0.02, quiet - idle)))
        self._record("meta", {"wait_quiescent": "timeout", "quiet": quiet})
        return False

    def wait_for_notification(
        self,
        predicate: Callable[[Notification], bool],
        timeout: float = 60.0,
        since: int = 0,
    ) -> Optional[Notification]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                pool = self.notifications[since:]
            for note in pool:
                if predicate(note):
                    return note
            if self.proc.poll() is not None:
                return None
            time.sleep(0.05)
        return None

    def wait_for_diagnostics(
        self, uri: str, min_version: Optional[int] = None, timeout: float = 30.0
    ) -> Optional[Notification]:
        """Wait for a publishDiagnostics for `uri`, optionally at version >= min_version.

        Servers that omit `version` (JDT LS) satisfy any min_version.
        """

        def pred(n: Notification) -> bool:
            if n.method != "textDocument/publishDiagnostics":
                return False
            p = n.params or {}
            if not same_uri(p.get("uri", ""), uri):
                return False
            if min_version is None:
                return True
            v = p.get("version")
            return v is None or v >= min_version

        return self.wait_for_notification(pred, timeout=timeout)

    def notification_count(self) -> int:
        with self._lock:
            return len(self.notifications)

    def server_errors(self) -> List[str]:
        """Error-level window/logMessage + window/showMessage payloads.

        Some state bugs are only visible as a server-side exception: the client
        sees a valid (if wrong) protocol conversation, and the stack trace shows
        up in the log channel. Collecting those makes them assertable.
        """
        out: List[str] = []
        with self._lock:
            pool = list(self.notifications)
        for note in pool:
            if note.method not in ("window/logMessage", "window/showMessage"):
                continue
            p = note.params or {}
            msg = str(p.get("message", ""))
            if p.get("type") == 1 or "Exception" in msg or "Error:" in msg or "File not found" in msg:
                out.append(msg[:400])
        return out

    def diagnostics_for(self, uri: str) -> Optional[List[Dict[str, Any]]]:
        """Latest publishDiagnostics payload for `uri`, or None if never published."""
        latest = None
        with self._lock:
            pool = list(self.notifications)
        for note in pool:
            if note.method != "textDocument/publishDiagnostics":
                continue
            params = note.params or {}
            if same_uri(params.get("uri", ""), uri):
                latest = params.get("diagnostics", [])
        return latest


__all__ = ["LspClient", "LspError", "Notification", "client_capabilities", "ACTIVITY_METHODS"]
