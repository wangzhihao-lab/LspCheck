"""Unit tests for oracles/base.py: difference shapes, stable keys, comparison, final state.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import Op, QueryKey, QueryResult, Snapshot  # noqa: E402
from oracles.base import (MISSING, compare, difference_shape, final_state, make_violation,  # noqa: E402
                          OracleContext, case_of, shape_of, stable_keys)
from ops import OpError  # noqa: E402


def snap(settled: bool = True, **norms) -> Snapshot:
    res = {}
    for name, norm in norms.items():
        k = QueryKey(name.split("__")[0], "a.py", 1, 2)
        err = tuple(norm) if isinstance(norm, list) and norm[:1] == ["error"] else None
        res[k] = QueryResult(k, norm, error=err)
    return Snapshot("s", "srv-1", settled, res)


D1 = [0, 0, 0, 3, 1, "E1", "x", "bad"]
D2 = [2, 0, 2, 4, 1, "E2", "x", "worse"]


class ShapeTests(unittest.TestCase):
    def test_diagnostics(self) -> None:
        self.assertEqual(difference_shape("diagnostics", [D1, D2], [D1]), "diagnostics:missing:E2")
        self.assertEqual(difference_shape("diagnostics", [], [D1]), "diagnostics:extra:E1")
        moved = [5, 0, 5, 3] + D1[4:]
        self.assertEqual(difference_shape("diagnostics", [D1], [moved]), "diagnostics:moved:E1")
        reworded = D1[:7] + ["other"]
        self.assertEqual(difference_shape("diagnostics", [D1], [reworded]), "diagnostics:message:E1")

    def test_errors_and_missing(self) -> None:
        self.assertEqual(difference_shape("hover", ["t", None], ["error", "timeout"]), "hover:result->error:timeout")
        self.assertEqual(difference_shape("hover", ["error", -32801], ["t", None]), "hover:error:-32801->result")
        self.assertEqual(difference_shape("hover", ["t", None], MISSING), "hover:key-lost")

    def test_hover_and_lists(self) -> None:
        self.assertEqual(difference_shape("hover", ["int", [0, 0, 0, 1]], None), "hover:lost")
        self.assertEqual(difference_shape("hover", ["int", None], ["str", None]), "hover:text")
        self.assertEqual(difference_shape("hover", ["int", [0, 0, 0, 1]], ["int", [0, 0, 0, 2]]), "hover:range")
        self.assertEqual(difference_shape("completion", ["a", "b"], ["a"]), "completion:missing")
        self.assertEqual(difference_shape("definition", [], [["a.py", 0, 0, 0, 1]]), "definition:gained")
        self.assertEqual(difference_shape("references", [["a", 1]], [["b", 1]]), "references:changed")


class CompareTests(unittest.TestCase):
    def test_stable_keys_excludes_unequal_and_liveness(self) -> None:
        b = snap(hover=["t", None], definition=[["a.py", 0, 0, 0, 1]], completion=["error", "timeout"])
        c = snap(hover=["t", None], definition=[], completion=["error", "timeout"])
        self.assertEqual({k.method for k in stable_keys(b, c)}, {"hover"})
        self.assertEqual(stable_keys(b, snap(settled=False, hover=["t", None])), set())

    def test_compare_reports_missing(self) -> None:
        b = snap(hover=["t", None], definition=[["a.py", 0, 0, 0, 1]])
        s = snap(hover=["u", None])
        diffs = compare(b, s, b.results.keys())
        self.assertEqual([(k.method, a) for k, _, a in diffs], [("definition", MISSING), ("hover", ["u", None])])


class FinalStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp()
        with open(os.path.join(self.root, "a.py"), "w") as f:
            f.write("x = 1\ny = 2\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def test_round_trip_is_empty(self) -> None:
        ops = [Op("open", "a.py"), Op("change", "a.py", (0, 0), (0, 0), "# c\n"), Op("change", "a.py", (0, 0), (1, 0), "")]
        self.assertTrue(final_state(self.root, ops).empty())

    def test_unsaved_buffer_and_close(self) -> None:
        edit = Op("change", "a.py", (0, 4), (0, 5), "9")
        self.assertEqual(final_state(self.root, [Op("open", "a.py"), edit]).files, {"a.py": "x = 9\ny = 2\n"})
        self.assertTrue(final_state(self.root, [Op("open", "a.py"), edit, Op("close", "a.py")]).empty())
        saved = [Op("open", "a.py"), edit, Op("save", "a.py"), Op("close", "a.py")]
        self.assertEqual(final_state(self.root, saved).files, {"a.py": "x = 9\ny = 2\n"})

    def test_rename_settings_and_errors(self) -> None:
        st = final_state(self.root, [Op("fs_rename", "a.py", new_path="b.py"),
                                     Op("set_config", settings={"s": {"k": 1}})])
        self.assertEqual(st.files, {"a.py": None, "b.py": "x = 1\ny = 2\n"})
        self.assertEqual(st.settings, {"s": {"k": 1}})
        with self.assertRaises(OpError):
            final_state(self.root, [Op("change", "a.py", (0, 0), (0, 0), "z")])


class ViolationTests(unittest.TestCase):
    def test_detail_round_trip(self) -> None:
        ctx = OracleContext("run1", "pyright", "1.1.414", "o/r@abc", "/nonexistent", "python", 1, ())
        v = make_violation(ctx, "r1_history", QueryKey("hover", "a.py", 1, 2), ["t", None], None,
                           [Op("open", "a.py")], {"family": "H1"})
        self.assertEqual(case_of(v), {"family": "H1"})
        self.assertEqual(shape_of(v), "hover:lost")
        self.assertEqual(v.signature, "pyright|r1_history|hover:lost")
        self.assertEqual(v.server, "pyright-1.1.414")


if __name__ == "__main__":
    unittest.main()
