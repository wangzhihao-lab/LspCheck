"""Unit tests for the `request` op (request_ops.py via OpApplier.op_request).

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from typing import Any, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framing import LspError  # noqa: E402
from model import Op  # noqa: E402
from ops import DocumentStore, OpApplier, OpError, invert_ops, ops_from_json, ops_to_json  # noqa: E402


class Client:
    def __init__(self, fail: bool = False) -> None:
        self.sent: List[Tuple[str, Any]] = []
        self.requests: List[Tuple[str, Any]] = []
        self.server_capabilities: dict = {}
        self.settings: dict = {}
        self.fail = fail

    def notify(self, method: str, params: Any = None) -> None:
        self.sent.append((method, params))

    def notification_count(self) -> int:
        return 0

    def request(self, method: str, params: Any = None, timeout: float = 0.0) -> Any:
        self.requests.append((method, params))
        if self.fail:
            raise LspError("boom")
        return {"contents": "int"}


class RequestOpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp()
        with open(os.path.join(self.root, "a.py"), "w") as f:
            f.write("x = 1\ny = x\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def applier(self, client: Client) -> OpApplier:
        ap = OpApplier(client, DocumentStore(self.root), request_timeout_s=1.0, sleep=lambda s: None)
        ap.apply(Op("open", "a.py"))
        return ap

    def test_sends_query_and_keeps_result(self) -> None:
        c = Client()
        out = self.applier(c).apply(Op("request", "a.py", start=(1, 4), text="references"))
        method, params = c.requests[-1]
        self.assertEqual(method, "textDocument/references")
        self.assertEqual(params["position"], {"line": 1, "character": 4})
        self.assertEqual(params["context"], {"includeDeclaration": True})
        self.assertEqual(out.result, {"contents": "int"})
        self.assertEqual(out.error, "")

    def test_error_answer_is_a_result(self) -> None:
        out = self.applier(Client(fail=True)).apply(Op("request", "a.py", start=(0, 0), text="hover"))
        self.assertIn("error", out.result)
        self.assertEqual(out.error, "")

    def test_invalid_requests_raise(self) -> None:
        ap = self.applier(Client())
        with self.assertRaises(OpError):
            ap.apply(Op("request", "a.py", start=(9, 0), text="hover"))
        with self.assertRaises(OpError):
            ap.apply(Op("request", "a.py", start=(0, 0), text="rename"))

    def test_json_and_inversion_skip(self) -> None:
        ops = [Op("request", "a.py", start=(0, 0), text="hover"), Op("change", "a.py", (0, 0), (0, 0), "z")]
        self.assertEqual(ops_from_json(ops_to_json(ops)), ops)
        inv = invert_ops(ops, {"a.py": "x = 1\ny = x\n"})
        self.assertEqual([o.kind for o in inv], ["change"])


if __name__ == "__main__":
    unittest.main()
