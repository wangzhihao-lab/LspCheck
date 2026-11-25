"""Unit tests: code-action / completion resolve support is read from the static capability or
from a dynamic registration (oracles/r4_session.py).

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oracles.r4_session import resolves_actions, resolves_items  # noqa: E402


class Monitor:
    def __init__(self, regs: Dict[str, Any]) -> None:
        self.regs = regs

    def poll(self) -> None:
        pass

    def registered(self, method: str) -> Optional[Any]:
        return self.regs.get(method)


class Session:
    def __init__(self, caps: Dict[str, Any], regs: Optional[Dict[str, Any]] = None) -> None:
        self.client = type("C", (), {"server_capabilities": caps})()
        self.monitor = Monitor(regs or {})


class ResolveSupportTests(unittest.TestCase):
    def test_static_capability(self) -> None:
        self.assertTrue(resolves_actions(Session({"codeActionProvider": {"resolveProvider": True}})))
        self.assertFalse(resolves_actions(Session({"codeActionProvider": True})))
        self.assertTrue(resolves_items(Session({"completionProvider": {"resolveProvider": True}})))

    def test_dynamic_registration(self) -> None:
        jdtls = Session({"codeActionProvider": None},
                        {"textDocument/codeAction": {"resolveProvider": True, "codeActionKinds": ["quickfix"]}})
        self.assertTrue(resolves_actions(jdtls))
        self.assertFalse(resolves_items(jdtls))
        self.assertFalse(resolves_actions(Session({}, {"textDocument/codeAction": {}})))

    def test_no_monitor(self) -> None:
        bare = type("S", (), {"client": type("C", (), {"server_capabilities": {}})()})()
        self.assertFalse(resolves_actions(bare))


if __name__ == "__main__":
    unittest.main()
