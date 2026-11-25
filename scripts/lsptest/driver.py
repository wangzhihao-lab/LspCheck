"""Driver: one live language server on one isolated copy of a prepared project.

The workspace is an APFS clone (`cp -cR`) under temp/lsptest_runs/<session>/ws (removed
on close unless keep=True); the server is launched through lsp_repro/servers.py;
protocol messages and driver events (ops, settles, snapshots) go to
data/lsptest/logs/<session>.jsonl. Every wait is bounded (requests, settling,
shutdown, then kill of the server and its descendants; timers kill a wedged server).
Use: `with Driver(DriverConfig("ts7", "7.0.2", dir)) as drv: drv.apply(op);
snap = drv.snapshot("history", targets)`; snap.settled says whether it may be compared.

Run line: imported by engine_smoke.py and the oracle layer; not run directly.
"""

from __future__ import annotations

import contextlib
import copy
import dataclasses
import hashlib
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import servers  # noqa: E402  (lsp_repro: resolve, start, SERVER_FACTORY)
from capabilities import client_capabilities  # noqa: E402
from framing import LspError  # noqa: E402
from model import Op, QueryKey, Snapshot  # noqa: E402
from ops import DocumentStore, OpApplier, OpOutcome, deep_merge, path_to_uri  # noqa: E402
from queries import NormContext, PathMapper, QueryConfig, SuiteStats, provider_enabled, run_suite  # noqa: E402
from settle import DocState, ProtocolMonitor, SettleContext, SettleResult, pull_supported, strategy_for  # noqa: E402
from targets import FileTargets  # noqa: E402

logger = logging.getLogger(__name__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RUNS_DIR = os.path.join(REPO, "temp", "lsptest_runs")
LOGS_DIR = os.path.join(REPO, "data", "lsptest", "logs")
PULL_DIAGNOSTICS: Dict[str, Any] = {"dynamicRegistration": True, "relatedDocumentSupport": True}

# Client settings the tool adds to each server's defaults, so that features that are
# off by default (inlay hints; gopls semantic tokens) are produced. typescript-
# language-server (ts6) reads the includeInlay* keys, TS 7 the VS Code style keys.
TS_INLAY_HINTS: Dict[str, Any] = dict(
    {f"includeInlay{k}": True for k in ("ParameterNameHintsWhenArgumentMatchesName", "FunctionParameterTypeHints",
     "VariableTypeHints", "VariableTypeHintsWhenTypeMatchesName", "PropertyDeclarationTypeHints",
     "FunctionLikeReturnTypeHints", "EnumMemberValueHints")}, includeInlayParameterNameHints="all",
    parameterNames={"enabled": "all", "suppressWhenArgumentMatchesName": False}, parameterTypes={"enabled": True},
    variableTypes={"enabled": True, "suppressWhenTypeMatchesName": False}, propertyDeclarationTypes={"enabled": True},
    functionLikeReturnTypes={"enabled": True}, enumMemberValues={"enabled": True})
_TS = {"typescript": {"inlayHints": TS_INLAY_HINTS}, "javascript": {"inlayHints": TS_INLAY_HINTS}}
SESSION_SETTINGS: Dict[str, Dict[str, Any]] = {
    "ts6": dict(_TS), "ts7": dict(_TS, **{"js/ts": {"inlayHints": TS_INLAY_HINTS}}),
    "gopls": {"gopls": {"semanticTokens": True, "hints": {k: True for k in (
        "assignVariableTypes", "compositeLiteralFields", "compositeLiteralTypes", "constantValues",
        "functionTypeParameters", "parameterNames", "rangeVariableTypes")}}},
}


def _jdtls_session_data(spec: servers.ServerSpec, session_dir: str) -> servers.ServerSpec:
    """Per-kind rewrite of the launch spec for session isolation: a private -data dir."""
    cmd = list(spec.cmd)
    if "-data" in cmd:
        cmd[cmd.index("-data") + 1] = os.path.join(session_dir, "jdtls-data")
    return dataclasses.replace(spec, cmd=cmd)


SPEC_ADAPTERS: Dict[str, Callable[[servers.ServerSpec, str], servers.ServerSpec]] = {"jdtls": _jdtls_session_data}


@dataclass(frozen=True)
class DriverConfig:
    server_kind: str
    server_version: str
    project_dir: str  # prepared project; never modified (the session works on a clone)
    label: str = "session"
    keep: bool = False  # keep the session directory after close
    settle_timeout_s: float = 300.0
    request_timeout_s: float = 30.0
    shutdown_timeout_s: float = 10.0
    hard_timeout_s: float = 3600.0  # watchdog: kill the server if the session is still open after this
    pull_diagnostics: Optional[bool] = None  # None: server default; True/False: declare/withhold the capability
    extra_settings: Optional[Mapping[str, Any]] = None  # None: SESSION_SETTINGS for the kind
    restart_version_on_reopen: bool = True  # reopen at version 1, as VS Code does
    runs_dir: str = RUNS_DIR
    logs_dir: str = LOGS_DIR


def clone_tree(src: str, dst: str) -> None:
    """Copy a directory tree with APFS clones (`cp -cR`: cheap even with node_modules/target)."""
    if os.path.exists(dst):
        raise FileExistsError(dst)
    subprocess.run(["cp", "-cR", src, dst], check=True, capture_output=True, timeout=900)


def process_tree(root_pid: int) -> List[int]:
    """Live descendants of a process, from one `ps` snapshot."""
    try:
        out = subprocess.run(["ps", "-axo", "pid=,ppid="], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    children: Dict[int, List[int]] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            children.setdefault(int(parts[1]), []).append(int(parts[0]))
    found, stack = [], [root_pid]
    while stack:
        for child in children.get(stack.pop(), []):
            found.append(child)
            stack.append(child)
    return found


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


def kill_pids(pids: Sequence[int], grace: float = 2.0) -> List[int]:
    """SIGTERM, then SIGKILL after `grace`, every pid still alive; returns those signalled."""
    alive = [p for p in pids if pid_alive(p)]
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for p in [q for q in alive if pid_alive(q)]:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(p, sig)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline and any(pid_alive(p) for p in alive):
            time.sleep(0.05)
    return alive


class Driver:
    """One live server on one isolated workspace copy (see the module docstring).
    Implements queries.QuerySession, so run_suite can query it directly."""

    def __init__(self, cfg: DriverConfig) -> None:
        self.cfg = cfg
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.session_id = f"{cfg.server_kind}-{cfg.server_version}-{cfg.label}-{stamp}-{uuid.uuid4().hex[:6]}"
        self.session_dir = os.path.join(cfg.runs_dir, self.session_id)
        self.workspace = os.path.join(self.session_dir, "ws")
        self.log_path = os.path.join(cfg.logs_dir, f"{self.session_id}.jsonl")
        self.spec: Any = None  # servers.ServerSpec
        self.client: Any = None  # lspclient.LspClient
        self.monitor: ProtocolMonitor = None  # type: ignore[assignment]  (set by start)
        self.store: DocumentStore = None  # type: ignore[assignment]
        self.applier: OpApplier = None  # type: ignore[assignment]
        self.mapper: PathMapper = None  # type: ignore[assignment]
        self.settler: Any = None
        self.last_settle: Optional[SettleResult] = None
        self.last_stats: Optional[SuiteStats] = None
        self.server_edits: List[Any] = []  # workspace/applyEdit requests (answered applied=false)
        self.settle_failures, self.init_seconds, self._closed = 0, 0.0, False
        self.close_info: Dict[str, Any] = {}
        self._watchdog: Optional[threading.Timer] = None

    # ------------------------------------------------------------ lifecycle
    def __enter__(self) -> "Driver":
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def start(self) -> "Driver":
        t0 = time.monotonic()
        try:
            os.makedirs(self.cfg.runs_dir, exist_ok=True)
            os.makedirs(self.session_dir)
            clone_tree(os.path.abspath(self.cfg.project_dir), self.workspace)
            self.spec = self._session_spec()
            self.client = servers.start(self.spec, path_to_uri(self.workspace), self.log_path, cwd=self.workspace)
        except BaseException:
            self.close()
            raise
        self.client.request_handlers["workspace/applyEdit"] = self._on_apply_edit
        self._watchdog = self._arm(self.cfg.hard_timeout_s)
        self.monitor = ProtocolMonitor(self.client)
        self.store = DocumentStore(self.workspace, self.cfg.restart_version_on_reopen)
        self.applier = OpApplier(self.client, self.store, self.cfg.request_timeout_s, registered=self.registered)
        self.mapper = PathMapper(self.workspace)
        self.settler = strategy_for(self.spec.kind, self.spec.quiet_seconds)
        if self.cfg.pull_diagnostics is False and hasattr(self.settler, "push"):
            self.settler = self.settler.push  # push-only client: never pull, even if the server offers it
        self.init_seconds = time.monotonic() - t0
        self._event("start", {"session": self.session_id, "server": self.spec.label, "pid": self.client.proc.pid,
                              "project": self.cfg.project_dir, "init_s": round(self.init_seconds, 3)})
        return self

    def _session_spec(self) -> Any:
        cfg = self.cfg
        spec = servers.resolve(cfg.server_kind, cfg.server_version)
        extra = SESSION_SETTINGS.get(spec.kind, {}) if cfg.extra_settings is None else dict(cfg.extra_settings)
        caps = copy.deepcopy(spec.capabilities) if spec.capabilities is not None else client_capabilities()
        if cfg.pull_diagnostics is True:
            caps.setdefault("textDocument", {})["diagnostic"] = dict(PULL_DIAGNOSTICS)
        elif cfg.pull_diagnostics is False:
            caps.get("textDocument", {}).pop("diagnostic", None)
        spec = dataclasses.replace(spec, settings=deep_merge(spec.settings or {}, dict(extra)), capabilities=caps)
        adapter = SPEC_ADAPTERS.get(spec.kind)
        return adapter(spec, self.session_dir) if adapter else spec

    def close(self) -> Dict[str, Any]:
        """Shut the server down (bounded), kill leftovers, remove the session dir unless kept."""
        if self._closed:
            return self.close_info
        self._closed = True
        if self._watchdog is not None:
            self._watchdog.cancel()
        info: Dict[str, Any] = {"session": self.session_id, "log": self.log_path}
        if self.client is not None:
            pids = process_tree(self.client.proc.pid)
            self._event("close", {"descendants": pids})
            guard = self._arm(self.cfg.shutdown_timeout_s + 15.0)  # shutdown + exit + stop() grace periods
            try:
                self.client.shutdown(timeout=self.cfg.shutdown_timeout_s)
            except (LspError, OSError) as exc:
                info["shutdown_error"] = str(exc)[:200]
                self.client.stop(grace=2.0)
            finally:
                guard.cancel()
            info.update(exit_code=self.client.proc.poll(), server_pids=[self.client.proc.pid] + pids,
                        killed=kill_pids(pids))
        if not self.cfg.keep:
            shutil.rmtree(self.session_dir, ignore_errors=True)
        self.close_info = dict(info, kept=self.session_dir if self.cfg.keep else "")
        return self.close_info

    def alive(self) -> bool:
        return self.client is not None and not self._closed and self.client.proc.poll() is None

    def _require(self) -> None:
        if self.client is None or self._closed:
            raise RuntimeError("driver not started, or already closed")

    def _event(self, kind: str, payload: Dict[str, Any]) -> None:
        if self.client is not None:
            self.client._record("driver", dict(payload, event=kind))  # same JSONL log as the protocol

    def _arm(self, seconds: float) -> threading.Timer:
        """Kill the server and its descendants after `seconds` unless cancelled (wedged server)."""
        pid = self.client.proc.pid
        timer = threading.Timer(seconds, lambda: kill_pids(process_tree(pid) + [pid]))
        timer.daemon = True
        timer.start()
        return timer

    def _on_apply_edit(self, params: Any) -> Dict[str, Any]:
        self.server_edits.append(params)
        return {"applied": False, "failureReason": "this client does not apply server-initiated edits"}

    # ------------------------------------------------------------ ops and settling
    def open(self, *paths: str) -> None:
        for p in paths:
            if not (p in self.store.docs and self.store.docs[p].open):
                self.apply(Op("open", path=p))

    def apply(self, op: Op) -> OpOutcome:
        self._require()
        out = self.applier.apply(op)
        self._event("op", {"op": op.to_json(), "sent": out.sent, "seconds": out.seconds, "error": out.error})
        return out

    def apply_ops(self, ops: Sequence[Op], settle_between: bool = False) -> List[OpOutcome]:
        """Apply ops in order; with settle_between (the `settled` timing mode) settle after each."""
        outs = []
        for op in ops:
            outs.append(self.apply(op))
            if settle_between and op.kind != "wait":
                self.settle()
        return outs

    def settle(self, timeout_s: Optional[float] = None) -> SettleResult:
        self._require()
        docs = tuple(DocState(p, self.store.docs[p].uri, self.store.docs[p].version, self.store.sent_index.get(p, 0))
                     for p in self.store.open_paths())
        ctx = SettleContext(self.client, self.monitor, docs, timeout_s or self.cfg.settle_timeout_s,
                            self.store.last_sent_at)
        res = self.settler.settle(ctx)
        if not self.alive():
            res.settled, res.reason = False, f"server exited ({res.reason})"
        self.settle_failures += 0 if res.settled else 1
        self.last_settle = res
        self._event("settle", res.to_json())
        return res

    def contents_sha(self) -> str:
        h = hashlib.sha256()
        for p in self.store.open_paths():
            h.update(p.encode("utf-8") + b"\0" + self.store.docs[p].text.encode("utf-8", "surrogatepass") + b"\0")
        return h.hexdigest()

    def snapshot(self, label: str, targets: Sequence[FileTargets], qcfg: Optional[QueryConfig] = None,
                 settle: bool = True, max_requery: int = 2) -> Snapshot:
        """Open the targets, settle, run the query suite (again, after settling, if a
        workspace/*/refresh arrives during it; at most max_requery times)."""
        self._require()
        qcfg = qcfg or QueryConfig(request_timeout_s=self.cfg.request_timeout_s)
        self.open(*[t.path for t in targets])
        res = self.settle() if settle or self.last_settle is None else self.last_settle
        ok = res.settled
        for attempt in range(max_requery + 1):
            self.monitor.poll()
            mark = self.monitor.refresh_total()
            results, stats = run_suite(self, targets, qcfg)
            self.monitor.poll()
            if self.monitor.refresh_total() == mark:
                break
            self._event("requery", {"attempt": attempt, "refreshes": self.monitor.refresh_total() - mark})
            ok = attempt < max_requery and self.settle().settled  # refreshed on the last attempt: unusable
        ok = ok and not stats.tripped and self.alive()
        self.last_stats = stats
        snap = Snapshot(label, self.spec.label, ok, results, self.contents_sha())
        self._event("snapshot", {"label": label, "settled": ok, "keys": len(results), "suite": stats.to_json()})
        return snap

    # ------------------------------------------------------------ queries.QuerySession
    def request(self, method: str, params: Any, timeout: float) -> Tuple[Any, Optional[Tuple[str, Any]]]:
        if not self.alive():
            return None, ("error", "dead")
        try:
            return self.client.request(method, params, timeout=timeout), None
        except LspError as exc:
            if exc.request_id is not None:
                with contextlib.suppress(LspError):
                    self.client.notify("$/cancelRequest", {"id": exc.request_id})
                return None, ("error", "timeout")
            return None, ("error", exc.code if exc.code is not None else ("transport" if self.alive() else "dead"))

    def uri(self, path: str) -> str:
        return self.store.uri(path)

    def text(self, path: str) -> str:
        return self.store.doc(path).text

    def registered(self, method: str) -> bool:
        self.monitor.poll()
        return self.monitor.is_registered(method)

    def supports(self, method: str) -> bool:
        return provider_enabled(getattr(self.client, "server_capabilities", None) or {}, self.registered, method)

    def pull_mode(self) -> bool:
        self.monitor.poll()  # a push-only client (pull_diagnostics=False) never pulls
        return self.cfg.pull_diagnostics is not False and pull_supported(self.client, self.monitor)

    def diagnostics(self, path: str, timeout: float) -> Tuple[Any, Optional[Tuple[str, Any]]]:
        """Pull servers: a fresh textDocument/diagnostic. Push servers: the latest publish."""
        if self.pull_mode():
            return self.request("textDocument/diagnostic", {"textDocument": {"uri": self.uri(path)}}, timeout)
        pub = self.monitor.publish_for(self.uri(path))
        return ([] if pub is None else pub.diagnostics), None  # never published: the client shows nothing

    def norm_context(self, completion_top: int) -> NormContext:
        prov = (getattr(self.client, "server_capabilities", None) or {}).get("semanticTokensProvider")
        legend = (prov.get("legend") if isinstance(prov, dict) else None) or \
            (self.monitor.registered("textDocument/semanticTokens") or {}).get("legend") or {}
        types, mods = tuple(legend.get("tokenTypes") or ()), tuple(legend.get("tokenModifiers") or ())
        return NormContext(self.mapper, types, mods, completion_top)


# ------------------------------------------------------------ comparing snapshots
def diff_keys(a: Snapshot, b: Snapshot) -> List[QueryKey]:
    """Keys present in only one snapshot or whose normalized results differ."""
    keys = set(a.results) | set(b.results)
    return sorted((k for k in keys if k not in a.results or k not in b.results
                   or a.results[k].norm != b.results[k].norm), key=dataclasses.astuple)


def stability(a: Snapshot, b: Snapshot) -> Dict[str, Dict[str, Any]]:
    """Per method: keys in either snapshot, keys equal in both, and the equal share."""
    out: Dict[str, Dict[str, Any]] = {}
    differing = set(diff_keys(a, b))
    for k in set(a.results) | set(b.results):
        row = out.setdefault(k.method, {"keys": 0, "equal": 0})
        row["keys"] += 1
        row["equal"] += 0 if k in differing else 1
    for row in out.values():
        row["share"] = round(row["equal"] / row["keys"], 4) if row["keys"] else 1.0
    return dict(sorted(out.items()))


__all__ = [
    "Driver", "DriverConfig", "LOGS_DIR", "RUNS_DIR", "SESSION_SETTINGS", "SPEC_ADAPTERS", "clone_tree", "diff_keys",
    "kill_pids", "pid_alive", "process_tree", "stability",
]
