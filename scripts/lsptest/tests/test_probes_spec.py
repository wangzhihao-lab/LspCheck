"""Unit tests for the specification probe edit_text_differs (bench/probes_spec.py).

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bench.probes  # noqa: E402,F401
from bench.probes import PROBES  # noqa: E402
import bench.probes_spec  # noqa: E402,F401

PARAMS = {"edit": {"via": "completion", "path": "main.go", "position": [3, 8], "label_re": "^colorex$"},
          "expected": {"path": "main.go", "text": "x := colorex\n", "source": "issue body"}}


def answers(after: Any, offered: bool = True) -> Dict[str, Any]:
    edit = {"offered": offered, "chosen": "colorex", "via": "completion", "texts_before": {"main.go": "x := colore\n"}}
    if after is not None:
        edit["texts_after"] = {"main.go": after}
    return {"case": {"valid": True, "edit": edit}}


class EditTextDiffersTests(unittest.TestCase):
    probe = PROBES["edit_text_differs"]

    def test_wrong_text_is_present(self) -> None:
        self.assertEqual(self.probe.decide(PARAMS, answers("x := colorecolorex\n")).verdict, "present")

    def test_expected_text_is_absent_crlf_tolerant(self) -> None:
        self.assertEqual(self.probe.decide(PARAMS, answers("x := colorex\r\n")).verdict, "absent")

    def test_invalid_cases(self) -> None:
        self.assertEqual(self.probe.decide(PARAMS, answers(None, offered=False)).verdict, "invalid")
        self.assertIn("source", " ".join(self.probe.validate({"edit": PARAMS["edit"], "expected": {"path": "a", "text": ""}}, [])))


if __name__ == "__main__":
    unittest.main()
