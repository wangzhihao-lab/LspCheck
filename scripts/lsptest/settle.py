"""Settle strategies: return only when a language server is idle for the current
document versions (design section 3).

- pull (the server declares or registers `textDocument/diagnostic`): pull every open
  document until two consecutive full reports are identical, with no `$/progress`
  token outstanding and no progress message, refresh request or op for
  `quiet_seconds`; a refresh during a round, or progress still running after it, restarts the count;
- push: a publishDiagnostics for the latest version of every open document (or, if
  the server omits versions, one sent after the last change) and no server message
  for `quiet_seconds`; a document that never gets one is accepted only after
  `missing_publish_grace_s` of complete silence and is listed in `assumed`;
- rust-analyzer additionally waits for `experimental/serverStatus` quiescent=true.
Every wait is capped by the caller's timeout; a run that does not settle reports
settled=False and must be discarded, never compared.

ProtocolMonitor is the incremental view of server traffic (progress tokens,
refresh requests, dynamic registrations, server status, latest publish per URI)
that both the strategies and the driver read.

Run line: imported by driver.py; not run directly.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Protocol, Tuple
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from framing import LspError  # noqa: E402

logger = logging.getLogger(__name__)

TRANSIENT_CODES = frozenset({-32801, -32802})  # ContentModified, ServerCancelled
REFRESH_METHODS = frozenset({
    "workspace/diagnostic/refresh", "workspace/semanticTokens/refresh", "workspace/inlayHint/refresh",
    "workspace/codeLens/refresh", "workspace/foldingRange/refresh", "workspace/inlineValue/refresh",
})
DEFAULT_IGNORED = frozenset({"$/logTrace", "telemetry/event"})


def uri_key(uri: str) -> str:
    """Comparison key for URIs: decoded file path, case-folded (macOS volumes are
    case-insensitive and some servers lower-case paths)."""
    if uri.startswith("file:"):
        return unquote(urlparse(uri).path).casefold()
    return uri


@dataclass(frozen=True)
class DocState:
    """What the client last sent for one open document."""

    path: str
    uri: str
    version: int
    sent_index: int  # notification count before the latest didOpen/didChange was sent


@dataclass
class Publish:
    index: int
    version: Optional[int]
    diagnostics: List[Dict[str, Any]]
    at: float


class ProtocolMonitor:
    """Incremental reader of client.notifications and client.server_requests."""

    def __init__(self, client: Any, ignored: FrozenSet[str] = DEFAULT_IGNORED) -> None:
        self.client = client
        self.ignored = ignored
        self._lock = threading.Lock()
        self._note_pos = 0
        self._req_pos = 0
        self.last_activity_at = time.monotonic()
        self.last_progress_at = 0.0
        self.last_refresh_at = 0.0
        self.progress: Dict[str, str] = {}  # token -> last kind: begin | report | end
        self.progress_at: Dict[str, float] = {}  # token -> time of its last $/progress
        self.progress_events = 0
        self.refreshes: Dict[str, int] = {}
        self.server_status: Optional[Dict[str, Any]] = None
        self.registrations: Dict[str, Tuple[str, Any]] = {}  # registration id -> (method, options)
        self.publishes: Dict[str, Publish] = {}  # uri_key -> latest publishDiagnostics

    def poll(self) -> None:
        with self._lock:
            notes = self.client.notifications[self._note_pos :]
            for i, note in enumerate(notes, start=self._note_pos):
                self._on_note(i, note)
            self._note_pos += len(notes)
            reqs = getattr(self.client, "server_requests", [])[self._req_pos :]
            for req in reqs:
                self._on_request(req)
            self._req_pos += len(reqs)

    def _on_note(self, index: int, note: Any) -> None:
        if note.method not in self.ignored:
            self.last_activity_at = max(self.last_activity_at, note.at)
        p = note.params or {}
        if note.method == "$/progress":
            kind = (p.get("value") or {}).get("kind") if isinstance(p.get("value"), dict) else None
            if kind in ("begin", "report", "end"):
                self.progress[str(p.get("token"))] = kind
                self.progress_at[str(p.get("token"))] = note.at
                self.progress_events += 1
                self.last_progress_at = max(self.last_progress_at, note.at)
        elif note.method == "textDocument/publishDiagnostics":
            self.publishes[uri_key(str(p.get("uri", "")))] = Publish(index, p.get("version"),
                                                                     p.get("diagnostics") or [], note.at)
        elif note.method == "experimental/serverStatus":
            self.server_status = dict(p)

    def _on_request(self, req: Any) -> None:
        self.last_activity_at = max(self.last_activity_at, req.at)
        p = req.params or {}
        if req.method in REFRESH_METHODS:
            self.refreshes[req.method] = self.refreshes.get(req.method, 0) + 1
            self.last_refresh_at = max(self.last_refresh_at, req.at)
        elif req.method == "client/registerCapability":
            for reg in p.get("registrations") or []:
                self.registrations[str(reg.get("id"))] = (reg.get("method", ""), reg.get("registerOptions"))
        elif req.method == "client/unregisterCapability":
            for reg in p.get("unregisterations") or p.get("unregistrations") or []:
                self.registrations.pop(str(reg.get("id")), None)

    def outstanding(self) -> List[str]:
        return sorted(t for t, k in self.progress.items() if k != "end")

    def active(self, now: float, stale_s: float) -> List[str]:
        """Outstanding tokens with a $/progress in the last stale_s seconds (a token a server leaves
        open without reports, e.g. gopls' "Error loading workspace" while go.mod is broken, is stale)."""
        return [t for t in self.outstanding() if now - self.progress_at.get(t, 0.0) < stale_s]

    def refresh_total(self) -> int:
        return sum(self.refreshes.values())

    def registered(self, method: str) -> Optional[Any]:
        """registerOptions of a dynamic registration for `method` ({} if none given), else None."""
        for m, opts in self.registrations.values():
            if m == method:
                return opts if opts is not None else {}
        return None

    def is_registered(self, method: str) -> bool:
        return self.registered(method) is not None

    def quiescent(self) -> bool:
        return bool(self.server_status) and self.server_status.get("quiescent") is True  # type: ignore[union-attr]

    def publish_for(self, uri: str) -> Optional[Publish]:
        return self.publishes.get(uri_key(uri))


def pull_supported(client: Any, monitor: ProtocolMonitor) -> bool:
    caps = getattr(client, "server_capabilities", None) or {}
    return bool(caps.get("diagnosticProvider")) or monitor.is_registered("textDocument/diagnostic")


# ------------------------------------------------------------ results and context
@dataclass
class SettleResult:
    settled: bool
    mode: str  # pull | push
    seconds: float
    reason: str
    rounds: int = 0
    refreshes: int = 0
    assumed: List[str] = field(default_factory=list)  # push: documents settled without a fresh publish
    reports: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # path -> raw diagnostics
    server_status: Optional[Dict[str, Any]] = None

    def to_json(self) -> Dict[str, Any]:
        return {"settled": self.settled, "mode": self.mode, "seconds": round(self.seconds, 3), "reason": self.reason,
                "rounds": self.rounds, "refreshes": self.refreshes, "assumed": self.assumed,
                "diagnostics": {p: len(v) for p, v in sorted(self.reports.items())},
                "server_status": self.server_status}


@dataclass(frozen=True)
class SettleContext:
    client: Any
    monitor: ProtocolMonitor
    docs: Tuple[DocState, ...]
    timeout_s: float
    last_sent_at: float  # monotonic time of the last op sent by the client


class SettleStrategy(Protocol):
    def settle(self, ctx: SettleContext) -> SettleResult: ...


def _dead(ctx: SettleContext) -> bool:
    proc = getattr(ctx.client, "proc", None)
    return proc is not None and proc.poll() is not None


def _strip_data(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{k: v for k, v in d.items() if k != "data"} if isinstance(d, dict) else d for d in items]


@dataclass(frozen=True)
class PushSettle:
    quiet_seconds: float = 2.0
    missing_publish_grace_s: float = 10.0
    wait_server_status: bool = False
    poll_s: float = 0.05

    def settle(self, ctx: SettleContext) -> SettleResult:
        mon, t0 = ctx.monitor, time.monotonic()
        deadline = t0 + ctx.timeout_s
        refresh0 = mon.refresh_total()
        while True:
            mon.poll()
            now = time.monotonic()
            missing = [d.path for d in ctx.docs if not self._fresh(mon, d)]
            busy = mon.active(now, self.missing_publish_grace_s) if not missing else mon.outstanding()
            status_ok = not self.wait_server_status or mon.quiescent()
            quiet_for = now - max(mon.last_activity_at, ctx.last_sent_at)
            if not busy and status_ok and quiet_for >= self.quiet_seconds:
                if not missing:
                    return self._result(ctx, True, "published and quiet", t0, refresh0)
                if quiet_for >= self.missing_publish_grace_s:
                    return self._result(ctx, True, "quiet; no fresh publish for some documents", t0, refresh0, missing)
            if now >= deadline or _dead(ctx):
                why = f"missing={missing[:4]} busy={busy[:3]} status_ok={status_ok} quiet_for={quiet_for:.1f}s"
                return self._result(ctx, False, ("server exited: " if _dead(ctx) else "timeout: ") + why, t0,
                                    refresh0, missing)
            time.sleep(self.poll_s)

    @staticmethod
    def _fresh(mon: ProtocolMonitor, d: DocState) -> bool:
        pub = mon.publish_for(d.uri)
        return pub is not None and pub.index >= d.sent_index and (pub.version is None or pub.version == d.version)

    @staticmethod
    def _result(ctx: SettleContext, ok: bool, why: str, t0: float, refresh0: int,
                assumed: Optional[List[str]] = None) -> SettleResult:
        mon = ctx.monitor
        reports = {}
        for d in ctx.docs:
            pub = mon.publish_for(d.uri)
            reports[d.path] = list(pub.diagnostics) if pub is not None else []
        return SettleResult(ok, "push", time.monotonic() - t0, why, 0, mon.refresh_total() - refresh0,
                            list(assumed or []), reports, mon.server_status)


@dataclass(frozen=True)
class PullSettle:
    quiet_seconds: float = 2.0
    stale_progress_s: float = 10.0  # an outstanding token silent this long no longer counts as busy
    wait_server_status: bool = False
    pull_interval_s: float = 0.5
    pull_timeout_s: float = 30.0
    poll_s: float = 0.05

    def settle(self, ctx: SettleContext) -> SettleResult:
        mon, t0 = ctx.monitor, time.monotonic()
        deadline = t0 + ctx.timeout_s
        refresh0 = mon.refresh_total()
        prev: Optional[Dict[str, List[Dict[str, Any]]]] = None
        rounds, last_end, why = 0, 0.0, "timeout before the first pull"
        while True:
            mon.poll()
            now = time.monotonic()
            if now >= deadline or _dead(ctx):
                status = "" if mon.quiescent() or not self.wait_server_status else " (server not quiescent)"
                head = "server exited" if _dead(ctx) else "timeout"
                return self._result(False, f"{head} after {rounds} rounds: {why}{status}", t0, rounds, mon, refresh0)
            quiet_for = now - max(mon.last_progress_at, mon.last_refresh_at, ctx.last_sent_at)
            status_ok = not self.wait_server_status or mon.quiescent()
            spaced = prev is None or now - last_end >= self.pull_interval_s
            if mon.active(now, self.stale_progress_s) or not status_ok or quiet_for < self.quiet_seconds or not spaced:
                time.sleep(self.poll_s)
                continue
            mark = mon.refresh_total()
            reports, err, fatal = self._pull_all(ctx, deadline)
            rounds, last_end = rounds + 1, time.monotonic()
            mon.poll()
            if fatal:
                return self._result(False, err or "pull failed", t0, rounds, mon, refresh0)
            # Progress that began and ended inside the round is the server's own work for our pulls
            # (pyright wraps every pull in work-done progress); progress still running disturbs.
            disturbed = err is not None or mon.refresh_total() != mark or bool(mon.active(time.monotonic(), self.stale_progress_s))
            if not disturbed and prev is not None and reports is not None and _same(reports, prev):
                return self._result(True, "two identical pulls, quiet", t0, rounds, mon, refresh0, reports)
            why = err or ("refresh or progress during the pull" if disturbed else "reports changed")
            prev = None if disturbed else reports

    def _pull_all(self, ctx: SettleContext, deadline: float) -> Tuple[Optional[Dict[str, Any]], Optional[str], bool]:
        """(reports, error, fatal). Content-modified, server-cancelled and timeouts are retried."""
        reports: Dict[str, List[Dict[str, Any]]] = {}
        for d in ctx.docs:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None, "deadline", False
            try:
                rep = ctx.client.request("textDocument/diagnostic", {"textDocument": {"uri": d.uri}},
                                         timeout=min(self.pull_timeout_s, remaining))
            except LspError as exc:
                if getattr(exc, "request_id", None) is not None:
                    _cancel(ctx.client, exc.request_id)
                    return None, f"pull timeout for {d.path}", False
                if getattr(exc, "code", None) in TRANSIENT_CODES:
                    return None, f"pull {d.path}: transient {exc.code}", False
                if getattr(exc, "code", None) is None:  # transport failure, not an answer
                    return None, f"pull {d.path}: {str(exc)[:200]}", True
                reports[d.path] = [{"error": exc.code}]  # a repeatable error answer (e.g. a handler panic) is an answer
                continue
            if not isinstance(rep, dict) or rep.get("kind") != "full":
                return None, f"pull {d.path}: not a full report", False
            reports[d.path] = rep.get("items") or []
        return reports, None, False

    @staticmethod
    def _result(ok: bool, why: str, t0: float, rounds: int, mon: ProtocolMonitor, refresh0: int,
                reports: Optional[Dict[str, Any]] = None) -> SettleResult:
        return SettleResult(ok, "pull", time.monotonic() - t0, why, rounds, mon.refresh_total() - refresh0,
                            [], dict(reports or {}), mon.server_status)


def _same(a: Dict[str, List[Dict[str, Any]]], b: Dict[str, List[Dict[str, Any]]]) -> bool:
    return a.keys() == b.keys() and all(_strip_data(a[k]) == _strip_data(b[k]) for k in a)


def _cancel(client: Any, request_id: Any) -> None:
    try:
        client.notify("$/cancelRequest", {"id": request_id})
    except LspError:
        pass


@dataclass(frozen=True)
class AutoSettle:
    """Pull when the server supports it, push otherwise (decided at settle time,
    so dynamic registrations are honoured)."""

    pull: PullSettle
    push: PushSettle

    def settle(self, ctx: SettleContext) -> SettleResult:
        ctx.monitor.poll()
        strategy = self.pull if pull_supported(ctx.client, ctx.monitor) else self.push
        return strategy.settle(ctx)


# ------------------------------------------------------------ registry
StrategyFactory = Callable[[float], SettleStrategy]
SETTLE_STRATEGIES: Dict[str, StrategyFactory] = {}


def register_settle(*kinds: str) -> Callable[[StrategyFactory], StrategyFactory]:
    """Register a strategy factory (quiet_seconds -> strategy) for server kinds."""

    def deco(fn: StrategyFactory) -> StrategyFactory:
        for kind in kinds:
            SETTLE_STRATEGIES[kind] = fn
        return fn

    return deco


@register_settle("default", "pyright", "ts6", "ts7", "gopls", "jdtls")
def _auto_strategy(quiet_seconds: float) -> SettleStrategy:
    return AutoSettle(PullSettle(quiet_seconds=quiet_seconds), PushSettle(quiet_seconds=quiet_seconds))


@register_settle("rust-analyzer")
def _rust_analyzer_strategy(quiet_seconds: float) -> SettleStrategy:
    return AutoSettle(PullSettle(quiet_seconds=quiet_seconds, wait_server_status=True),
                      PushSettle(quiet_seconds=quiet_seconds, wait_server_status=True))


def strategy_for(kind: str, quiet_seconds: float) -> SettleStrategy:
    return SETTLE_STRATEGIES.get(kind, SETTLE_STRATEGIES["default"])(quiet_seconds)


__all__ = [
    "AutoSettle", "DEFAULT_IGNORED", "DocState", "ProtocolMonitor", "Publish", "PullSettle", "PushSettle",
    "REFRESH_METHODS", "SETTLE_STRATEGIES", "SettleContext", "SettleResult", "SettleStrategy", "TRANSIENT_CODES",
    "pull_supported", "register_settle", "strategy_for", "uri_key",
]
