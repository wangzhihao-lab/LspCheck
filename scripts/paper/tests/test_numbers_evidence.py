"""Tests of the evidence numbers (numbers_evidence.py) on a temporary repository with synthetic sweeps.

Builds a minimal data tree (root causes, decisions, evidence summary, two isolation sweeps, the
year-old sweep, the TypeScript 7 sweep and answers) under a temporary directory and checks the
counts, the build order and names of the isolation columns, and which answer of the tested
implementation the other implementation's answer agrees with (with a missing key and an empty answer kept apart).

Run line: python3 -m unittest scripts/paper/tests/test_numbers_evidence.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Sequence

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PAPER not in sys.path:
    sys.path.insert(0, PAPER)

import numbers_evidence as ne  # noqa: E402
from numbers_io import Sources  # noqa: E402

RUN = "data/lsptest/runs/main_v1"
G1, G2, ART = "ts6-r1-a-111111", "ts6-r1-b-222222", "ts6-r1-c-333333"


def write_csv(path: str, rows: Sequence[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def sweep_row(gid: str, verdict: str, hits: int) -> Dict[str, Any]:
    return {"gid": gid, "verdict": verdict, "reproduced": hits, "replays": 3, "settled": 3, "control_stable": 3}


def write_sweep(root: str, label: str, rows: List[Dict[str, Any]]) -> None:
    d = os.path.join(root, RUN, "sweep", label)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "results.jsonl"), "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)


class EvidenceNumbersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        write_csv(os.path.join(root, RUN, "triage/root_causes.csv"),
                  [{"cause": "C1", "server": "ts6", "trigger": "t", "description": "d", "group": G1},
                   {"cause": "C2", "server": "ts6", "trigger": "t", "description": "d", "group": G2}])
        write_csv(os.path.join(root, RUN, "triage/decisions.csv"),
                  [{"group": G1, "verdict": "bug"}, {"group": G2, "verdict": "bug"},
                   {"group": ART, "verdict": "tool-artifact"}])
        write_csv(os.path.join(root, RUN, "evidence/evidence_summary.csv"),
                  [{"cause": "C1", "independent": "none", "related_possible": ""},
                   {"cause": "C2", "independent": "decisive", "related_possible": "repo#1 (open)"}])
        write_sweep(root, "iso-ts6.0.3-tsls6.0.0", [sweep_row(G1, "reproduced", 3)])
        write_sweep(root, "iso-ts5.9.3-tsls6.0.0", [sweep_row(G1, "flaky", 2), sweep_row(G2, "reproduced", 3)])
        write_sweep(root, "older-2025", [sweep_row(G1, "reproduced", 3), sweep_row(G2, "unsettled", 0)])
        write_sweep(root, "ts6-groups-on-ts7", [sweep_row(G1, "not-reproduced", 0), sweep_row(G2, "not-reproduced", 0),
                                                sweep_row(ART, "reproduced", 3)])
        groups = []
        for gid, method, fresh, hist in (
                (G1, "references", [["a.ts", 1, 0, 1, 3]], []),
                (G2, "codeAction", [["Move to a new file", "refactor.move.newFile"]], ["missing-key"]),
                (ART, "diagnostics", [[0, 0, 0, 5, 1, "2304", "ts", "m"]], [[0, 0, 0, 5, 1, "2304", "ts", "m"]] * 2)):
            groups.append({"gid": gid, "representative": "v-" + gid})
            d = os.path.join(root, RUN, "triage", gid)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "repro.json"), "w", encoding="utf-8") as f:
                json.dump({"key": {"method": method}, "expected": fresh, "actual": hist}, f)
        with open(os.path.join(root, RUN, "triage/triage.json"), "w", encoding="utf-8") as f:
            json.dump({"groups": groups}, f)
        answers = {"source": "ts6", "build": ["ts7", "7.0.2"], "rows": [
            {"gid": G1, "error": "", "history": [["a.ts", 1, 0, 1, 3]]},
            {"gid": G2, "error": "", "history": []},
            {"gid": ART, "error": "", "history": [[0, 2, 0, 4, 1, "2304", "typescript", "m2"]] * 2}]}
        with open(os.path.join(root, RUN, "evidence/answers_ts6_on_ts7-7.0.2.json"), "w", encoding="utf-8") as f:
            json.dump(answers, f)
        self.numbers, self.tables = ne.evidence_numbers(Sources(root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_summary_counts(self) -> None:
        self.assertEqual(self.numbers["independent"], {"decisive": 1, "partial": 0, "none": 1})
        self.assertEqual((self.numbers["related_possible"], self.numbers["related_none"]), (1, 1))

    def test_isolation_columns_and_counts(self) -> None:
        iso = self.tables[0]
        self.assertEqual(iso.columns, ["cause", "group", "TS 5.9.3 + tsls 6.0.0", "TS 6.0.3 + tsls 6.0.0 (control)",
                                       "TS 5.9.3 + tsls 5.0.0 (year-old)", "TS 7.0.2"])
        self.assertEqual(iso.rows[0], ["C1", G1, "2/3", "3/3", "3/3", "0/3"])
        self.assertEqual(iso.rows[1], ["C2", G2, "3/3", "", "unsettled", "0/3"])
        iso_n = self.numbers["isolation"]
        self.assertEqual(iso_n["pairs"], 3)
        self.assertEqual(iso_n["by_cause"]["C2"], {"not_run": 1, "reproduced": 1, "unsettled": 1})
        self.assertEqual(iso_n["not_reproduced"], {"C1": 0, "C2": 0})

    def test_cross_counts_empty_answers_apart(self) -> None:
        cross = self.numbers["cross"]["ts6_on_other"]
        self.assertEqual((cross["bug_groups"], cross["bug_not_reproduced"], cross["artifact_reproduced"]), (2, 2, 1))
        self.assertEqual((cross["bug_matches_fresh"], cross["bug_no_answer"], cross["bug_matches_history"]), (1, 1, 0))
        other = self.numbers["cross"]["ts7_on_other"]  # no ts7 sweep and no recorded answers in this tree
        self.assertEqual((other["groups"], other["bug_matches_fresh"]), (0, None))
        rows = {r[0]: r for r in self.tables[1].rows}
        self.assertEqual(rows[G2][3:], ["TS 7.0.2", "0/3", 1, "missing", 0, "no answer"])
        self.assertEqual(rows[ART][8], "history")  # diagnostics compared by code and line only

    def test_canonical_forms(self) -> None:
        self.assertEqual(ne.canonical("semanticTokens", [[1, 2, 3, "member", "x"]]), [(1, 2, 3)])
        self.assertIsNone(ne.answer_size(["missing-key"]))
        self.assertEqual(ne.cross_match("hover", ["a"], ["b"], ["c"]), "neither")

    def test_persistence_cells_add_retries(self) -> None:
        first = {"verdict": "not-reproduced", "reproduced": 0}
        self.assertEqual(ne.cell_text(*ne.persistence_cell(first, None)), "no")
        self.assertEqual(ne.cell_text(*ne.persistence_cell({"verdict": "unsettled", "reproduced": 0}, None)), "unsettled")
        cell = ne.persistence_cell(first, {"verdict": "flaky", "replays": 2, "reproduced": 1})
        self.assertEqual(cell, (1, 3, "not-reproduced"))
        self.assertEqual(ne.cell_text(*cell), "1/3")

    def test_rename_cells(self) -> None:
        """A settled verdict prints the count; another verdict keeps its count beside it (b9d052: unsettled, 2/3)."""
        self.assertEqual(ne.rename_cell({"verdict": "reproduced", "reproduced": 3, "replays": 3}), "3/3")
        self.assertEqual(ne.rename_cell({"verdict": "not-reproduced", "reproduced": 0, "replays": 3}), "0/3")
        self.assertEqual(ne.rename_cell({"verdict": "unsettled", "reproduced": 2, "replays": 3}), "unsettled (2/3)")

    def test_no_summary_gives_nothing(self) -> None:
        os.remove(os.path.join(self.tmp.name, RUN, "evidence/evidence_summary.csv"))
        self.assertEqual(ne.evidence_numbers(Sources(self.tmp.name)), (None, []))


if __name__ == "__main__":
    unittest.main()
