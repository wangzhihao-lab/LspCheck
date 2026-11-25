"""Unit tests: workspace-level ops (fs_write, fs_rename, set_config) require a fresh publish
for every open document before a push settle counts it as settled.

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

from model import Op  # noqa: E402
from ops import DocumentStore, OpApplier  # noqa: E402


class Client:
    def __init__(self) -> None:
        self.sent: List[Tuple[str, Any]] = []
        self.count = 0  # notifications received from the server so far
        self.server_capabilities: dict = {}
        self.settings: dict = {}

    def notify(self, method: str, params: Any = None) -> None:
        self.sent.append((method, params))

    def notification_count(self) -> int:
        return self.count


class WorkspaceOpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp()
        for name in ("a.py", "b.py", "c.py"):
            with open(os.path.join(self.root, name), "w") as f:
                f.write("x = 1\n")
        self.client = Client()
        self.store = DocumentStore(self.root)
        self.ap = OpApplier(self.client, self.store, request_timeout_s=1.0, sleep=lambda s: None)
        self.ap.apply(Op("open", "a.py"))
        self.ap.apply(Op("open", "b.py"))

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def test_each_workspace_op_marks_every_open_document(self) -> None:
        for n, op in enumerate([Op("fs_write", "c.py", text="y = 2\n"), Op("set_config", settings={"a": 1}),
                                Op("fs_rename", "c.py", new_path="d.py")], start=1):
            self.client.count = 10 * n
            self.ap.apply(op)
            self.assertEqual(self.store.sent_index["a.py"], 10 * n, op.kind)
            self.assertEqual(self.store.sent_index["b.py"], 10 * n, op.kind)

    def test_document_edit_marks_only_that_document(self) -> None:
        self.client.count = 7
        self.ap.apply(Op("change", "a.py", (0, 0), (0, 0), "# c\n"))
        self.assertEqual(self.store.sent_index["a.py"], 7)
        self.assertNotEqual(self.store.sent_index.get("b.py"), 7)


if __name__ == "__main__":
    unittest.main()
