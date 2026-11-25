"""Unit tests for PullSettle's handling of error answers (settle.py).

A repeatable error answer to textDocument/diagnostic (e.g. a handler panic) is an answer:
the session settles and the error is recorded; a transport failure is still fatal.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from typing import Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settle import DocState, ProtocolMonitor, PullSettle, SettleContext  # noqa: E402  (adds lsp_repro to the path)
from framing import LspError, Notification  # noqa: E402


class Client:
    def __init__(self, code: Optional[int]) -> None:
        self.notifications: List[Any] = []
        self.server_requests: List[Any] = []
        self.proc = None
        self.code = code
        self.calls = 0

    def request(self, method: str, params: Any = None, timeout: float = 0.0) -> Any:
        self.calls += 1
        raise LspError("boom", code=self.code)

    def notify(self, method: str, params: Any = None) -> None:
        pass


class ProgressClient(Client):
    """Answers every pull with an empty full report wrapped in its own work-done progress
    (as pyright does); with `leave_running`, a background progress begins and never ends."""

    def __init__(self, leave_running: bool = False) -> None:
        super().__init__(code=None)
        self.leave_running = leave_running

    def request(self, method: str, params: Any = None, timeout: float = 0.0) -> Any:
        self.calls += 1
        tok = f"pull-{self.calls}"
        for kind in ("begin", "report", "end"):
            self.notifications.append(Notification("$/progress", {"token": tok, "value": {"kind": kind}}))
        if self.leave_running and self.calls == 1:
            self.notifications.append(Notification("$/progress", {"token": "index", "value": {"kind": "begin"}}))
        return {"kind": "full", "items": []}


def settle(client: Client, timeout_s: float = 5.0) -> Any:
    ctx = SettleContext(client, ProtocolMonitor(client), (DocState("a.rs", "file:///w/a.rs", 1, 0),),
                        timeout_s=timeout_s, last_sent_at=time.monotonic() - 10)
    return PullSettle(quiet_seconds=0.0, pull_interval_s=0.01, poll_s=0.001).settle(ctx)


class PullErrorTests(unittest.TestCase):
    def test_repeatable_error_answer_settles(self) -> None:
        c = Client(code=-32603)
        res = settle(c)
        self.assertTrue(res.settled, res.reason)
        self.assertEqual(res.reports, {"a.rs": [{"error": -32603}]})
        self.assertGreaterEqual(c.calls, 2)

    def test_transport_failure_is_fatal(self) -> None:
        res = settle(Client(code=None))
        self.assertFalse(res.settled)


class PullProgressTests(unittest.TestCase):
    def test_progress_inside_the_round_does_not_disturb(self) -> None:
        res = settle(ProgressClient())
        self.assertTrue(res.settled, res.reason)

    def test_progress_still_running_blocks_settling(self) -> None:
        res = settle(ProgressClient(leave_running=True), timeout_s=1.0)
        self.assertFalse(res.settled)


if __name__ == "__main__":
    unittest.main()
