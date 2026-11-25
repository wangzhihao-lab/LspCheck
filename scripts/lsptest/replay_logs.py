"""Which session logs each replay wrote, a soft deadline for replays, and log excerpts.

ReplayRecorder wraps an oracle for flake.confirm_all / reduce.reduce_and_confirm: replay()
delegates to the oracle and records the session logs that appeared in the logs directory
during the call (one replay runs at a time in a worker, so the difference of two listings is
exactly that replay's sessions); any other attribute (probe_scope ...) is the oracle's. After
the soft deadline a replay is not started: it returns an unsettled outcome at once and is
recorded as skipped, so confirm_all still finishes and the skipped candidates can be flagged
incomplete. `last_confirming_logs(v)` gives the logs of the last replay of v that counted as a
reproduction (flake.counts). keep_logs() gzips logs into a violation directory; excerpt() pulls
error responses, error log messages and stderr lines out of session logs for report drafts.

Run line: imported by campaign_run.py and triage.py; not run directly.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import flake  # noqa: E402
from model import Op, Violation  # noqa: E402
from oracles.base import Oracle, OracleContext, ReplayOutcome  # noqa: E402

logger = logging.getLogger(__name__)


@dataclass
class ReplayCall:
    violation: Violation  # the object that was replayed (identity matters)
    outcome: ReplayOutcome
    logs: List[str] = field(default_factory=list)  # absolute paths of the session logs it wrote
    ops: Optional[int] = None  # len(ops) when the caller passed a subset (reduction probes)
    skipped: bool = False  # not started: the soft deadline had passed


class ReplayRecorder:
    """Oracle proxy that records every replay (see the module docstring)."""

    def __init__(self, oracle: Oracle, logs_dir: str, deadline: Optional[float] = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._oracle, self.logs_dir, self.deadline, self.clock = oracle, logs_dir, deadline, clock
        self.calls: List[ReplayCall] = []

    @property
    def name(self) -> str:
        return self._oracle.name

    def applies_to(self, server_kind: str) -> bool:
        return self._oracle.applies_to(server_kind)

    def run(self, ctx: OracleContext) -> Any:
        return self._oracle.run(ctx)

    def _listing(self) -> set:
        try:
            return {e.path for e in os.scandir(self.logs_dir) if e.is_file()}
        except FileNotFoundError:
            return set()

    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        n_ops = None if ops is None else len(ops)
        if self.deadline is not None and self.clock() >= self.deadline:
            out = ReplayOutcome(False, False, False, None, 0.0)
            self.calls.append(ReplayCall(v, out, [], n_ops, skipped=True))
            return out
        before = self._listing()
        out = self._oracle.replay(ctx, v, ops)
        self.calls.append(ReplayCall(v, out, sorted(self._listing() - before), n_ops))
        return out

    def incomplete(self, v: Violation) -> bool:
        """Whether a replay of v was skipped because of the deadline."""
        return any(c.skipped for c in self.calls_for(v))

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._oracle, attr)

    def calls_for(self, v: Violation) -> List[ReplayCall]:
        return [c for c in self.calls if c.violation is v]

    def last_confirming_logs(self, v: Violation) -> List[str]:
        hits = [c for c in self.calls_for(v) if flake.counts(c.outcome)]
        return list(hits[-1].logs) if hits else []

    def replayed_in_order(self) -> List[Violation]:
        """The distinct violations replayed, in first-replay order (confirm_all's order)."""
        out: List[Violation] = []
        for c in self.calls:
            if not any(c.violation is x for x in out):
                out.append(c.violation)
        return out

    def discard_logs(self, keep: Iterable[str] = ()) -> int:
        """Delete recorded logs except `keep` (keeps a long reduction from filling the disk)."""
        keep_set, n = set(keep), 0
        for c in self.calls:
            for p in c.logs:
                if p not in keep_set and os.path.exists(p):
                    os.remove(p)
                    n += 1
        return n


def keep_logs(paths: Iterable[str], dest_dir: str) -> List[str]:
    """gzip session logs into dest_dir; returns the stored file names."""
    names = []
    for p in paths:
        if not os.path.exists(p):
            continue
        os.makedirs(dest_dir, exist_ok=True)
        name = os.path.basename(p) + ".gz"
        with open(p, "rb") as src, gzip.open(os.path.join(dest_dir, name), "wb") as dst:
            shutil.copyfileobj(src, dst)
        names.append(name)
    return names


def _records(path: str) -> Iterable[Dict[str, Any]]:
    opener = gzip.open if path.endswith(".gz") else open
    try:
        with opener(path, "rt", encoding="utf-8", errors="replace") as f:  # type: ignore[operator]
            for line in f:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        logger.warning("cannot read log %s: %s", path, exc)


def error_messages(paths: Sequence[str], method: str) -> List[str]:
    """Messages of the error responses the server sent to requests of an LSP method."""
    out: List[str] = []
    for path in paths:
        methods: Dict[Any, str] = {}
        for rec in _records(path):
            d, msg = rec.get("dir"), rec.get("msg")
            if d == "send" and isinstance(msg, dict) and "id" in msg and "method" in msg:
                methods[msg["id"]] = str(msg["method"])
            elif d == "recv" and isinstance(msg, dict) and "error" in msg and methods.get(msg.get("id")) == method:
                text = str((msg.get("error") or {}).get("message", "")).strip()
                if text and text not in out:
                    out.append(text)
    return out


def excerpt(paths: Sequence[str], limit: int = 24, width: int = 300) -> List[str]:
    """Error responses (with their request method), error/warning log messages and stderr lines."""
    out: List[str] = []
    for path in paths:
        methods: Dict[Any, str] = {}
        label = os.path.basename(path).replace(".jsonl", "").replace(".gz", "")
        for rec in _records(path):
            d, msg = rec.get("dir"), rec.get("msg")
            if d == "send" and isinstance(msg, dict) and "id" in msg and "method" in msg:
                methods[msg["id"]] = str(msg["method"])
            elif d == "recv" and isinstance(msg, dict) and "error" in msg and "method" not in msg:
                err = msg.get("error") or {}
                out.append(f"[{label}] {methods.get(msg.get('id'), '?')} -> error {err.get('code')}: "
                           f"{' '.join(str(err.get('message', '')).split())}"[:width])
            elif d == "recv" and isinstance(msg, dict) and msg.get("method") in ("window/logMessage", "window/showMessage"):
                p = msg.get("params") or {}
                if p.get("type") in (1, 2):
                    out.append(f"[{label}] {msg['method']} type {p.get('type')}: "
                               f"{' '.join(str(p.get('message', '')).split())}"[:width])
            elif d == "stderr" and isinstance(msg, str) and msg.strip():
                out.append(f"[{label}] stderr: {msg.strip()}"[:width])
            elif d == "meta" and isinstance(msg, dict) and "kill" in msg:
                out.append(f"[{label}] client: server {msg['kill']}"[:width])
    if len(out) > limit:
        out = out[: limit // 2] + [f"... {len(out) - limit} lines omitted ..."] + out[-(limit - limit // 2):]
    return out


__all__ = ["ReplayCall", "ReplayRecorder", "error_messages", "excerpt", "keep_logs"]
