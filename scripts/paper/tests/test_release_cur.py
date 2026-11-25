"""Tests of the release replays of both campaigns (numbers_release_cur.py), the main-text table of bugs
(table_bugs.py) and the two-campaign appendix tables, on the repository data (one paper_numbers.compute) and on
small synthetic inputs.

- the table of bugs has one row per root cause (35), and its Check column is the evidence summaries' value;
- cur.newest counts what the newest-release results.jsonl of both campaigns hold (recounted from the raw rows), and
  its counting is release.newest's: applied to main_v1 alone it gives release.newest;
- cur.lifecycle covers every cause, and the relations' subset leaves out the crash-check causes;
- G2 and M list every cause of both campaigns;
- cur.persistence skips missing files without failing, counts only final R1 bug groups, and merges retries.

Run line: python3 -m unittest scripts/paper/tests/test_release_cur.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from typing import Any, Dict, List

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PAPER not in sys.path:
    sys.path.insert(0, PAPER)

import numbers_release_cur as nrc  # noqa: E402
import paper_numbers  # noqa: E402
import table_bugs  # noqa: E402
from numbers_io import REPO, Sources  # noqa: E402

RUNS = os.path.join(REPO, "data", "lsptest", "runs")
CAMPAIGNS = ("main_v1", "main_v2")
NEWEST = "newest-2026-11-18"


def read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def root_causes(run: str) -> Dict[str, str]:
    return {r["group"]: r["cause"] for r in read_csv(os.path.join(RUNS, run, "triage", "root_causes.csv"))}


class RepositoryTest(unittest.TestCase):
    numbers: Dict[str, Any]
    tables: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        numbers, tables = paper_numbers.compute()
        cls.numbers, cls.tables = numbers, {t.name: t for t in tables}

    def test_bug_table_rows(self) -> None:
        rows = table_bugs.table_rows()
        causes = {c for run in CAMPAIGNS for c in root_causes(run).values()}
        self.assertEqual(len(rows), 33)  # C23, C24 withdrawn 2026-11-24
        self.assertEqual(len(rows), len(causes))
        self.assertEqual([r["cause"] for r in rows], sorted(causes, key=lambda c: int(c[1:])))

    def test_bug_table_check_column(self) -> None:
        evidence = {r["cause"]: r["independent"]
                    for run, name in (("main_v1", "evidence_summary.csv"), ("main_v2", "evidence_summary_v2.csv"))
                    for r in read_csv(os.path.join(RUNS, run, "evidence", name))}
        withdrawn = {r["cause"] for r in read_csv(os.path.join(REPO, "data", "lsptest", "root_cause_withdrawn.csv"))}
        evidence = {c: v for c, v in evidence.items() if c not in withdrawn}
        self.assertEqual({r["cause"]: r["check"] for r in table_bugs.table_rows()}, evidence)

    def test_bug_table_newest_matches_numbers(self) -> None:
        """A Newest cell that is not -- agrees with cur.newest.by_cause (every group of the cause has a row)."""
        by_cause = self.numbers["cur"]["newest"]["by_cause"]
        for r in table_bugs.table_rows():
            if r["newest"] == "--":
                continue
            b = by_cause[r["cause"]]
            expected = ("yes" if b["reproducing"] == b["groups"] else "no" if b["reproducing"] == 0
                        else f"{b['reproducing']} of {b['groups']}")
            self.assertEqual(r["newest"], expected, r["cause"])

    def test_newest_counts_match_results(self) -> None:
        """cur.newest recounted from the raw rows: last row per bug group, reproduced in all, some or none."""
        last: Dict[Any, Dict[str, Any]] = {}
        for run in CAMPAIGNS:
            cause = root_causes(run)
            for r in read_jsonl(os.path.join(RUNS, run, "sweep", NEWEST, "results.jsonl")):
                if r["gid"] in cause:
                    last[(run, r["gid"])] = dict(r, cause=cause[r["gid"]])
        newest = self.numbers["cur"]["newest"]
        self.assertEqual(newest["groups"], len(last))
        self.assertEqual(newest["reproduced_all"], sum(1 for r in last.values() if r["reproduced"] == r["replays"]))
        self.assertEqual(newest["reproduced_some"],
                         sum(1 for r in last.values() if 0 < r["reproduced"] < r["replays"]))
        self.assertEqual(newest["causes"], len({r["cause"] for r in last.values()}))
        self.assertEqual(newest["causes_reproduced_all"],
                         len({r["cause"] for r in last.values() if r["reproduced"] == r["replays"]}))
        self.assertEqual(sum(b["groups"] for b in newest["by_cause"].values()), newest["groups"])
        r0 = {"C17", "C23", "C24"}  # the causes found only by the crash check
        self.assertEqual(newest["relations"]["causes_reproduced_all"],
                         len({r["cause"] for r in last.values() if r["reproduced"] == r["replays"]} - r0))

    def test_newest_counts_as_release(self) -> None:
        """replay_counts over main_v1's rows alone gives release.newest (same algorithm)."""
        src = Sources(REPO)
        cause = root_causes("main_v1")  # withdrawn causes (C23, C24) have no row and are skipped, as in release.newest
        rows = [(cause[r["gid"]], r) for r in src.jsonl(f"data/lsptest/runs/main_v1/sweep/{NEWEST}/results.jsonl")
                if r["gid"] in cause]
        mine = nrc.replay_counts(rows)
        release = self.numbers["release"]["newest"]
        # the legacy row counts still include the withdrawn causes' rows; the cause-level counts do not
        keys = [k for k in mine if k.startswith("causes") or k == "by_cause"]
        self.assertEqual({k: mine[k] for k in keys}, {k: release[k] for k in keys})

    def test_lifecycle_covers_causes(self) -> None:
        life = self.numbers["cur"]["lifecycle"]
        self.assertEqual(life["causes"], self.numbers["cur"]["root_causes"]["total"])
        self.assertEqual(life["relations"]["causes"], self.numbers["cur"]["baseline"]["relations"]["causes"])
        self.assertEqual(life["relations"]["causes"], 32)
        self.assertLessEqual(life["relations"]["older_than_year"], life["older_than_year"])

    def test_root_cause_and_evidence_tables(self) -> None:
        g2, m = self.tables["G2_root_causes"], self.tables["M_evidence"]
        self.assertEqual(len(g2.rows), self.numbers["cur"]["bug_groups"]["total"])
        self.assertEqual(len({r[0] for r in g2.rows}), self.numbers["cur"]["root_causes"]["total"])
        self.assertTrue(all(r[4].endswith((" (first)", " (second)")) for r in g2.rows))
        self.assertEqual([r[0] for r in m.rows], [f"C{i}" for i in range(1, 36) if i not in (23, 24)])


def campaign(run: str, items: List[Any]) -> Any:
    return SimpleNamespace(run=run, items=[SimpleNamespace(gid=g, relation=rel, verdict=v, cause=c)
                                           for g, rel, v, c in items])


def persistence_doc(rows: Dict[str, Dict[int, int]], waits: List[int]) -> Dict[str, Any]:
    """rows: gid -> wait -> reproduced (0 or 1), one replay each."""
    return {"waits_s": waits, "rows": [
        {"gid": g, "by_wait": {str(w): {"verdict": "reproduced" if by[w] else "not-reproduced", "replays": 1,
                                        "reproduced": by[w], "settled": 1, "control_stable": 1} for w in waits}}
        for g, by in rows.items()]}


class PersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.src = Sources(self.tmp.name)
        self.campaigns = [campaign("main_v1", [("a", "R1", "bug", "C1"), ("b", "R1", "bug", "C2"),
                                               ("c", "R1", "legitimate", ""), ("d", "R4", "bug", "C5")]),
                          campaign("main_v2", [("a", "R1", "bug", "C9")])]

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, run: str, name: str, doc: Dict[str, Any]) -> None:
        path = os.path.join(self.tmp.name, "data", "lsptest", "runs", run, "evidence", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f)

    def test_no_file(self) -> None:
        with self.assertLogs("numbers_release_cur", level="WARNING"):
            self.assertIsNone(nrc.persistence_cur(self.src, self.campaigns))

    def test_missing_later_files(self) -> None:
        """Only main_v1/persistence.json: no error, a warning per missing file, only final R1 bug groups counted."""
        waits = [0, 5, 30, 60]
        self.write("main_v1", "persistence.json", persistence_doc(
            {"a": {0: 1, 5: 1, 30: 1, 60: 1}, "b": {0: 1, 5: 1, 30: 0, 60: 0}, "c": {0: 1, 5: 1, 30: 1, 60: 1}},
            waits))
        self.write("main_v1", "persistence_retry.json", {"waits_s": [60], "replays": 2, "rows": [
            {"gid": "b", "by_wait": {"60": {"verdict": "flaky", "replays": 2, "reproduced": 1}}}]})
        with self.assertLogs("numbers_release_cur", level="WARNING") as logs:
            out = nrc.persistence_cur(self.src, self.campaigns)
        self.assertTrue(any("persistence_new.json does not exist" in m for m in logs.output))
        self.assertTrue(any("main_v2/evidence/persistence.json does not exist" in m for m in logs.output))
        assert out is not None
        self.assertEqual((out["groups"], out["causes"]), (2, 2))  # c is not a bug, d is R4
        self.assertEqual(out["by_wait"], {"0": 2, "5": 2, "30": 1, "60": 1})
        self.assertEqual((out["still_after_longest"], out["never_after_longest"]), (2, 0))  # b: 1 of 3 after 60 s
        self.assertEqual((out["retried_groups"], out["retry_replays"], out["longest_wait_s"]), (1, 2, 60))
        self.assertNotIn("gone_causes", out)

    def test_all_files(self) -> None:
        waits = [0, 60]
        self.write("main_v1", "persistence.json", persistence_doc({"a": {0: 1, 60: 1}}, waits))
        self.write("main_v1", "persistence_new.json", persistence_doc({"b": {0: 1, 60: 0}}, waits))
        self.write("main_v2", "persistence.json", persistence_doc({"a": {0: 1, 60: 1}}, waits))
        out = nrc.persistence_cur(self.src, self.campaigns)
        assert out is not None
        self.assertEqual((out["groups"], out["causes"], out["never_after_longest"]), (3, 3, 1))
        self.assertEqual((out["gone_causes"], out["gone_last_seen_s"]), ("C2", 0))

    def test_different_waits(self) -> None:
        self.write("main_v1", "persistence.json", persistence_doc({"a": {0: 1, 60: 1}}, [0, 60]))
        self.write("main_v2", "persistence.json", persistence_doc({"a": {0: 1, 30: 1}}, [0, 30]))
        with self.assertRaises(ValueError):
            nrc.persistence_cur(self.src, self.campaigns)


if __name__ == "__main__":
    unittest.main()
