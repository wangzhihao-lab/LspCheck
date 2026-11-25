"""Unit tests for ops.py: LSP position arithmetic, change application and inverses,
the OpApplier against a recording fake client, and JSON round trips.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import random
import shutil
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from model import Op  # noqa: E402
from ops import (  # noqa: E402
    DocumentStore, LineIndex, OpApplier, OpError, apply_change, change_at_offsets, deep_merge, inverse_change,
    invert_ops, load_ops, ops_from_json, ops_to_json, path_to_uri, read_text, save_ops, uri_to_path,
)


class FakeClient:
    """Records notifications and requests the way lspclient.LspClient would send them."""

    def __init__(self, caps: Optional[Dict[str, Any]] = None) -> None:
        self.sent: List[Tuple[str, Any]] = []
        self.notifications: List[Any] = []
        self.server_capabilities = caps or {}
        self.settings: Dict[str, Any] = {"a": {"b": 1, "c": 2}}
        self.request_result: Any = {"changes": {}}

    def notify(self, method: str, params: Any = None) -> None:
        self.sent.append((method, params))

    def request(self, method: str, params: Any = None, timeout: float = 0.0) -> Any:
        self.sent.append((method, params))
        return self.request_result

    def notification_count(self) -> int:
        return len(self.notifications)


class TestLineIndex(unittest.TestCase):
    def test_crlf_cr_lf_end_lines(self) -> None:
        idx = LineIndex("a\r\nbc\rd\ne")
        self.assertEqual(idx.starts, [0, 3, 6, 8])
        self.assertEqual(idx.offset((1, 1)), 4)
        self.assertEqual(idx.position(4), (1, 1))
        self.assertEqual(idx.line_text(1), "bc")
        self.assertEqual(idx.end(), (3, 1))

    def test_form_feed_and_line_separator_do_not_end_lines(self) -> None:
        text = "a\fb\u2028c\nd"
        self.assertEqual(LineIndex(text).position(text.index("d")), (1, 0))
        self.assertEqual(LineIndex(text).offset((0, 5)), 5)

    def test_utf16_units(self) -> None:
        idx = LineIndex("x\U0001F600y")
        self.assertEqual(idx.offset((0, 3)), 2)
        self.assertEqual(idx.position(2), (0, 3))
        with self.assertRaises(OpError):
            idx.offset((0, 2))  # inside the surrogate pair

    def test_invalid_positions_raise(self) -> None:
        idx = LineIndex("ab\ncd")
        for pos in ((2, 0), (0, 3), (-1, 0)):
            with self.assertRaises(OpError):
                idx.offset(pos)
        self.assertEqual(idx.offset((0, 2)), 2)  # end of line is valid


class TestChanges(unittest.TestCase):
    TEXT = "def f(x):\r\n    return x + 1  # \u00e9\U0001F600\n\nclass C:\n    pass\n"

    def test_apply_change(self) -> None:
        out, replaced, end = apply_change("hello\nworld\n", (0, 1), (1, 2), "EY\nWO")
        self.assertEqual((out, replaced, end), ("hEY\nWOrld\n", "ello\nwo", (1, 2)))

    def test_inverse_round_trip_on_random_edits(self) -> None:
        rng = random.Random(7)
        for _ in range(300):
            text = self.TEXT
            idx = LineIndex(text)
            cuts = [o for o in range(len(text) + 1) if not (0 < o < len(text) and text[o - 1] == "\r" and text[o] == "\n")]
            a, b = sorted(rng.sample(cuts, 2))
            new = rng.choice(["", "z", "\n", "\U0001F600", "ab\ncd", "  "])
            op = Op("change", "f.py", start=idx.position(a), end=idx.position(b), text=new)
            after = apply_change(text, op.start, op.end, op.text)[0]  # type: ignore[arg-type]
            inv = inverse_change(op, text)
            self.assertEqual(apply_change(after, inv.start, inv.end, inv.text)[0], text)  # type: ignore[arg-type]

    def test_inverse_rejects_joining_a_line_terminator(self) -> None:
        with self.assertRaises(OpError):
            inverse_change(Op("change", "f", start=(1, 0), end=(1, 0), text="\nX"), "a\rb")

    def test_invert_ops_over_two_files(self) -> None:
        texts = {"a.ts": "let x = 1;\nlet y = 2;\n", "b.ts": "export {}\n"}
        ops = [Op("change", "a.ts", start=(0, 4), end=(0, 5), text="xx"), Op("wait", delay_ms=5),
               Op("change", "b.ts", start=(0, 0), end=(0, 0), text="// c\n"),
               Op("change", "a.ts", start=(1, 0), end=(2, 0), text="")]
        cur = dict(texts)
        for op in ops:
            if op.kind == "change":
                cur[op.path] = apply_change(cur[op.path], op.start, op.end, op.text)[0]  # type: ignore[arg-type]
        for op in invert_ops(ops, texts):
            cur[op.path] = apply_change(cur[op.path], op.start, op.end, op.text)[0]  # type: ignore[arg-type]
        self.assertEqual(cur, texts)

    def test_change_at_offsets(self) -> None:
        op = change_at_offsets("a.py", "ab\ncd", 3, 4, "X", delay_ms=50)
        self.assertEqual((op.start, op.end, op.text, op.delay_ms), ((1, 0), (1, 1), "X", 50))


class TestApplier(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp(prefix="ops-test-")
        os.makedirs(os.path.join(self.root, "src"))
        with open(os.path.join(self.root, "src", "a.ts"), "w", encoding="utf-8", newline="") as f:
            f.write("const a = 1;\r\nexport { a };\r\n")
        self.client = FakeClient({"workspace": {"fileOperations": {"willRename": {}, "didRename": {}}}})
        self.store = DocumentStore(self.root)
        self.slept: List[float] = []
        self.ap = OpApplier(self.client, self.store, sleep=self.slept.append)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def methods(self) -> List[str]:
        return [m for m, _ in self.client.sent]

    def test_open_change_close_discards_buffer(self) -> None:
        self.ap.apply(Op("open", "src/a.ts"))
        method, params = self.client.sent[-1]
        self.assertEqual((method, params["textDocument"]["version"]), ("textDocument/didOpen", 1))
        self.assertEqual(params["textDocument"]["languageId"], "typescript")
        self.assertIn("\r\n", params["textDocument"]["text"])  # line terminators preserved
        self.assertEqual(params["textDocument"]["uri"], path_to_uri(os.path.join(self.root, "src/a.ts")))
        self.ap.apply(Op("change", "src/a.ts", start=(0, 10), end=(0, 11), text="42"))
        method, params = self.client.sent[-1]
        self.assertEqual(params["textDocument"]["version"], 2)
        self.assertEqual(params["contentChanges"][0]["range"]["start"], {"line": 0, "character": 10})
        self.assertTrue(self.store.doc("src/a.ts").text.startswith("const a = 42;"))
        with self.assertRaises(OpError):
            self.ap.apply(Op("open", "src/a.ts"))
        self.ap.apply(Op("close", "src/a.ts"))
        self.assertEqual(self.store.doc("src/a.ts").text, read_text(os.path.join(self.root, "src/a.ts")))
        self.ap.apply(Op("open", "src/a.ts"))
        self.assertEqual(self.client.sent[-1][1]["textDocument"]["version"], 1)  # reopen restarts, as VS Code

    def test_reopen_can_continue_versions(self) -> None:
        ap = OpApplier(self.client, DocumentStore(self.root, restart_version_on_reopen=False))
        for op in (Op("open", "src/a.ts"), Op("change", "src/a.ts", start=(0, 0), end=(0, 0), text="x"),
                   Op("close", "src/a.ts"), Op("open", "src/a.ts")):
            ap.apply(op)
        self.assertEqual(self.client.sent[-1][1]["textDocument"]["version"], 3)

    def test_change_requires_open_and_valid_range(self) -> None:
        with self.assertRaises(OpError):
            self.ap.apply(Op("change", "src/a.ts", start=(0, 0), end=(0, 0), text="x"))
        self.ap.apply(Op("open", "src/a.ts"))
        with self.assertRaises(OpError):
            self.ap.apply(Op("change", "src/a.ts", start=(9, 0), end=(9, 0), text="x"))
        with self.assertRaises(OpError):
            self.ap.apply(Op("bogus", "src/a.ts"))

    def test_save_config_and_fs_write(self) -> None:
        self.ap.apply(Op("open", "src/a.ts"))
        self.ap.apply(Op("change", "src/a.ts", start=(0, 0), end=(0, 0), text="// s\n"))
        self.ap.apply(Op("save", "src/a.ts"))
        self.assertTrue(read_text(os.path.join(self.root, "src/a.ts")).startswith("// s\n"))
        self.assertEqual(self.client.sent[-1][1]["text"], self.store.doc("src/a.ts").text)
        self.ap.apply(Op("set_config", settings={"a": {"c": 3}, "z": True}))
        self.assertEqual(self.client.settings, {"a": {"b": 1, "c": 3}, "z": True})
        self.assertEqual(self.client.sent[-1], ("workspace/didChangeConfiguration", {"settings": self.client.settings}))
        self.ap.apply(Op("fs_write", "src/new.ts", text="export const n = 1;\n"))
        self.ap.apply(Op("fs_write", "src/new.ts", text="export const n = 2;\n"))
        types = [p["changes"][0]["type"] for m, p in self.client.sent if m == "workspace/didChangeWatchedFiles"]
        self.assertEqual(types, [1, 2])

    def test_fs_rename_sequence(self) -> None:
        self.ap.apply(Op("open", "src/a.ts"))
        self.ap.apply(Op("change", "src/a.ts", start=(0, 0), end=(0, 0), text="/* dirty */"))
        out = self.ap.apply(Op("fs_rename", "src/a.ts", new_path="lib/b.ts"))
        self.assertEqual(out.sent, ["workspace/willRenameFiles", "textDocument/didClose", "workspace/didRenameFiles",
                                    "workspace/didChangeWatchedFiles", "textDocument/didOpen"])
        self.assertEqual(out.result, {"changes": {}})
        self.assertTrue(os.path.exists(os.path.join(self.root, "lib/b.ts")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "src/a.ts")))
        opened = self.client.sent[-1][1]["textDocument"]
        self.assertTrue(opened["uri"].endswith("/lib/b.ts") and opened["text"].startswith("/* dirty */"))
        self.assertEqual(self.store.open_paths(), ["lib/b.ts"])
        with self.assertRaises(OpError):
            self.ap.apply(Op("fs_rename", "src/a.ts", new_path="x.ts"))

    def test_delay_and_wait_sleep(self) -> None:
        self.ap.apply(Op("open", "src/a.ts", delay_ms=200))
        self.ap.apply(Op("wait", delay_ms=50))
        self.assertEqual(self.slept, [0.2, 0.05])

    def test_sent_index_is_taken_before_sending(self) -> None:
        self.client.notifications.extend(["n1", "n2"])
        self.ap.apply(Op("open", "src/a.ts"))
        self.assertEqual(self.store.sent_index["src/a.ts"], 2)


class TestJsonAndHelpers(unittest.TestCase):
    OPS = [Op("open", "a.py"), Op("change", "a.py", start=(0, 0), end=(0, 3), text=""),
           Op("set_config", settings={"python": {"analysis": {"typeCheckingMode": "strict"}}}),
           Op("fs_rename", "a.py", new_path="b.py", delay_ms=50), Op("wait", delay_ms=200)]

    def test_round_trip(self) -> None:
        self.assertEqual(ops_from_json(ops_to_json(self.OPS)), self.OPS)
        self.assertEqual(ops_from_json({"ops": ops_to_json(self.OPS)}), self.OPS)
        path = os.path.join(tempfile.mkdtemp(prefix="ops-json-"), "ops.json")
        save_ops(path, self.OPS)
        self.assertEqual(load_ops(path), self.OPS)
        shutil.rmtree(os.path.dirname(path))

    def test_rejects_bad_ops(self) -> None:
        for bad in ([{"kind": "explode"}], [{"kind": "open", "bogus": 1}], ["open"]):
            with self.assertRaises(OpError):
                ops_from_json(bad)

    def test_uri_and_merge(self) -> None:
        uri = path_to_uri("/tmp/my dir/a#b.ts")
        self.assertEqual(uri, "file:///tmp/my%20dir/a%23b.ts")
        self.assertEqual(uri_to_path(uri), "/tmp/my dir/a#b.ts")
        base = {"a": {"b": 1}}
        self.assertEqual(deep_merge(base, {"a": {"c": 2}}), {"a": {"b": 1, "c": 2}})
        self.assertEqual(base, {"a": {"b": 1}})


if __name__ == "__main__":
    unittest.main()
