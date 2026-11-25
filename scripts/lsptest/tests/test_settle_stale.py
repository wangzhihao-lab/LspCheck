"""Unit tests: an outstanding progress token that has been silent for a long time (gopls leaves
"Error loading workspace" open while go.mod is broken) does not block settling once every
open document has a fresh publish; it still blocks while a publish is missing.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from typing import Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settle import DocState, ProtocolMonitor, PullSettle, PushSettle, SettleContext  # noqa: E402  (adds lsp_repro)
from framing import Notification  # noqa: E402

URI = "file:///w/a.go"


class Client:
    def __init__(self, notes: List[Any]) -> None:
        self.notifications = notes
        self.server_requests: List[Any] = []
        self.proc = None

    def request(self, method: str, params: Any = None, timeout: float = 0.0) -> Any:
        return {"kind": "full", "items": []}

    def notify(self, method: str, params: Any = None) -> None:
        pass


def notes(published: bool) -> List[Any]:
    old = time.monotonic() - 60
    out = [Notification("$/progress", {"token": "load", "value": {"kind": "begin"}}, at=old)]
    if published:
        out.append(Notification("textDocument/publishDiagnostics", {"uri": URI, "diagnostics": []}, at=old + 1))
    return out


def ctx(client: Client, timeout_s: float) -> SettleContext:
    return SettleContext(client, ProtocolMonitor(client), (DocState("a.go", URI, 1, 0),), timeout_s=timeout_s,
                         last_sent_at=time.monotonic() - 60)


class StaleProgressTests(unittest.TestCase):
    def test_push_settles_past_a_stale_token_when_published(self) -> None:
        res = PushSettle(quiet_seconds=0.0, poll_s=0.001).settle(ctx(Client(notes(True)), 2.0))
        self.assertTrue(res.settled, res.reason)

    def test_push_waits_while_a_publish_is_missing(self) -> None:
        res = PushSettle(quiet_seconds=0.0, poll_s=0.001).settle(ctx(Client(notes(False)), 0.5))
        self.assertFalse(res.settled)

    def test_pull_settles_past_a_stale_token(self) -> None:
        res = PullSettle(quiet_seconds=0.0, pull_interval_s=0.01, poll_s=0.001).settle(ctx(Client(notes(False)), 2.0))
        self.assertTrue(res.settled, res.reason)

    def test_recent_token_still_blocks(self) -> None:
        fresh = [Notification("$/progress", {"token": "t", "value": {"kind": "begin"}})]
        res = PullSettle(quiet_seconds=0.0, pull_interval_s=0.01, poll_s=0.001).settle(ctx(Client(fresh), 0.5))
        self.assertFalse(res.settled)


if __name__ == "__main__":
    unittest.main()
