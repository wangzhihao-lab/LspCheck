"""Tests of the per-campaign and combined numbers of numbers_current.py and the consensus detection keys of
numbers_agree.py, on the repository data (one computation of paper_numbers.compute) and on small synthetic inputs.

- totals: every count of cur that sums the campaigns equals c1 + c2;
- detection.consensus: detected bugs per server add up to all detected bugs, every oracle is listed (zeros too),
  check_removed agrees with the final signature verdicts, the cases run before the freeze;
- the missed-case attribution lists exactly the bugs not detected under the final verdicts;
- C1 replays cover exactly the C1 groups of both root_causes.csv files;
- independent evidence: both counts (all causes, causes of R1-R5) agree with the root causes and their lists;
- classes, sensitivity and merge agree with the verdict and root-cause sections.

Run line: python3 -m unittest scripts/paper/tests/test_numbers_current.py
"""

from __future__ import annotations

import csv
import os
import sys
import unittest
from typing import Any, Dict, List

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PAPER not in sys.path:
    sys.path.insert(0, PAPER)

import numbers_current as ncur  # noqa: E402
import numbers_review as nr  # noqa: E402
import paper_numbers  # noqa: E402
from numbers_bench import load_detection  # noqa: E402
from numbers_final import load_signature_verdicts  # noqa: E402
from numbers_io import REPO, Sources  # noqa: E402

RUNS = os.path.join(REPO, "data", "lsptest", "runs")
SUMMED = ["stable_filter.compared", "stable_filter.unstable", "violations.rows", "violations.replayed",
          "violations.filtered", "two_of_three.reproduced_2_of_3", "two_of_three.not_confirmed", "reduction.groups",
          "reduction.groups_with_ops", "reduction.ops_before", "reduction.ops_after", "reduction.narrowed",
          "not_reconfirmed", "unsettled_r1.sessions", "unsettled_r1.unsettled", "evidence.c1_edit.groups",
          "evidence.c1_edit.reproduced_any", "evidence.c1_edit.reproduced_all", "evidence.c1_edit.not_restored_groups",
          "evidence.c1_external.groups", "evidence.c1_external.reproduced_any", "evidence.c1_external.reproduced_all"]


def get(d: Dict[str, Any], path: str) -> Any:
    for p in path.split("."):
        d = d[p]
    return d


def csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class CurrentNumbersTest(unittest.TestCase):
    numbers: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.numbers, _ = paper_numbers.compute()

    def test_totals_are_sums(self) -> None:
        c1, c2, cur = (self.numbers[k] for k in ("c1", "c2", "cur"))
        paths = list(SUMMED)
        for sec in ("classes", "artifact_classes"):
            paths += [f"{sec}.{k}" for k in cur[sec]]
        paths += [f"violations.by_status.{k}" for k in cur["violations"]["by_status"]]
        paths += [f"unsettled_r1.by_server.{k}.unsettled" for k in cur["unsettled_r1"]["by_server"]]
        paths += [f"run_seconds.per_oracle.{o}.total" for o in cur["run_seconds"]["per_oracle"]]
        for who in ("author", "rater2", "final"):
            paths += [f"sensitivity.bug_groups.{who}.{r}" for r in cur["sensitivity"]["bug_groups"][who]]
        for p in paths:
            with self.subTest(key=p):
                a, b = c1, c2
                for part in p.split("."):
                    a, b = a.get(part, 0) if isinstance(a, dict) else a, b.get(part, 0) if isinstance(b, dict) else b
                self.assertAlmostEqual(get(cur, p), a + b, delta=0.11)
        self.assertAlmostEqual(cur["reduction"]["compute_hours"],
                               c1["reduction"]["compute_hours"] + c2["reduction"]["compute_hours"], delta=0.011)
        self.assertEqual(cur["violations"]["filtered_pct"],
                         round(100 * cur["violations"]["filtered"] / cur["violations"]["replayed"]))
        n_runs = sum(v["n"] for v in cur["run_seconds"]["per_oracle"].values())
        self.assertEqual(n_runs, cur["runs"]["recorded"])

    def test_cost(self) -> None:
        cost, cur = self.numbers["cur"]["cost"], self.numbers["cur"]
        self.assertEqual(cost["campaign_hours"], cur["wall_clock_hours"])
        self.assertEqual(cost["bench_hours"], self.numbers["setup"]["bench_v1"]["wall_clock"]["hours"])
        self.assertEqual(cost["reduction_hours"], cur["reduction"]["compute_hours"])
        self.assertAlmostEqual(cost["total_hours"], cost["campaign_hours"] + cost["bench_hours"]
                               + cost["reduction_hours"], delta=0.011)
        self.assertEqual(cost["total_days"], round(cost["total_hours"] / 24, 1))

    def test_detection_by_kind_and_oracle(self) -> None:
        dc = self.numbers["detection"]["consensus"]
        oracles = ["r0_crash", "r1_history", "r2_handles", "r3_routes", "r4_edits", "r5_transforms"]
        self.assertEqual(sorted(dc["all"]["detected_by_oracle"]), oracles)
        self.assertEqual(sum(v["detected"] for v in dc["by_kind"]["all"].values()), dc["all"]["detected"])
        self.assertEqual(sum(v["cases"] for v in dc["by_kind"]["all"].values()), dc["all"]["cases"])
        self.assertEqual(sorted(dc["by_kind_oracle"]), ["gopls", "jdtls", "pyright", "rust-analyzer", "tsserver"])
        for o in oracles:
            self.assertEqual(sum(v[o] for v in dc["by_kind_oracle"].values()), dc["all"]["detected_by_oracle"][o])

    def test_check_removed_and_pre_freeze(self) -> None:
        src = Sources(REPO)
        dd = load_detection(src)
        final = {k: f.verdict for k, f in load_signature_verdicts(src).final.items()}
        yes = {case for case, oracle, sig in final if final[(case, oracle, sig)] == "yes"}
        removed = sorted(str(e["case"]) for e in dd.entries if e["pre_only"] and str(e["case"]) not in yes)
        dc = self.numbers["detection"]["consensus"]
        self.assertEqual(dc["check_effect"]["removed_cases"], removed)
        self.assertEqual(dc["check_removed"], len(removed))
        self.assertEqual(dc["check_effect"]["detected_after"], dc["all"]["detected"])
        held = dc["held_out"]
        self.assertEqual((held["pre_freeze_cases"], held["pre_freeze_detected"]), (6, 5))
        self.assertEqual(held["pre_freeze_detected_list"], sorted(nr.PRE_FREEZE_CASES & yes))
        self.assertEqual(held["pre_freeze_detected"] + held["held_out"]["detected"], held["all"]["detected"])

    def test_missed_attribution_lists_the_undetected(self) -> None:
        src = Sources(REPO)
        dd = load_detection(src)
        final = {k: f.verdict for k, f in load_signature_verdicts(src).final.items()}
        detected = set(nr.matched(dd.entries, final))
        cases = {str(e["case"]) for e in dd.entries}
        rows = [r["case"] for r in csv_rows(os.path.join(RUNS, "bench_v1", "missed_attribution.csv"))]
        self.assertEqual(len(rows), len(set(rows)))
        self.assertEqual(set(rows), cases - detected)
        self.assertEqual(self.numbers["detection"]["missed_attribution"]["rows"], len(cases - detected))

    def test_c1_replays_cover_the_c1_groups(self) -> None:
        for key, run in (("c1", "main_v1"), ("c2", "main_v2")):
            want = sorted(r["group"] for r in csv_rows(os.path.join(RUNS, run, "triage", "root_causes.csv"))
                          if r["cause"] == "C1")
            for mode in ("c1_edit", "c1_external"):
                self.assertEqual(self.numbers[key]["evidence"][mode]["group_list"], want)
        detail = self.numbers["cur"]["root_causes"]["detail"]["C1"]
        self.assertEqual((detail["groups"], detail["groups_c1"], detail["groups_c2"]), (20, 13, 7))

    def test_evidence_counts_and_lists(self) -> None:
        cur = self.numbers["cur"]
        ev, causes = cur["evidence"], cur["root_causes"]
        self.assertEqual(sum(ev["independent"][k] for k in ncur.EVIDENCE), causes["total"])
        self.assertEqual(ev["decisive"] + ev["partial"] + ev["none"], ev["causes"])
        self.assertEqual(ev["causes"], cur["baseline"]["relations"]["causes"])
        five = {c for c, e in causes["detail"].items() if set(e["relation"].split(", ")) & {"R1", "R2", "R3", "R4", "R5"}}
        listed = {c for k in ncur.EVIDENCE for c in ev[f"{k}_list"].split(", ") if c}
        self.assertEqual(listed, five)
        self.assertEqual({c for c in ev["excluded_list"].split(", ") if c} | five, set(causes["detail"]))
        for k in ncur.EVIDENCE:
            self.assertEqual(len([c for c in ev[f"{k}_list"].split(", ") if c]), ev[k])
        self.assertLessEqual(ev["related_none"], ev["related_none_all"])

    def test_classes_sensitivity_merge(self) -> None:
        for key in ("c1", "c2", "cur"):
            s = self.numbers[key]
            self.assertEqual(sum(s["classes"].values()), s["verdicts"]["by_verdict"]["legitimate"])
            self.assertEqual(sum(s["artifact_classes"].values()), s["verdicts"]["by_verdict"]["tool-artifact"])
            sens = s["sensitivity"]
            final = {r: v for r, v in sens["bug_groups"]["final"].items() if r != "total"}
            self.assertEqual(final, s["bug_groups"]["by_relation"])
            distinct = {r: v for r, v in sens["distinct"]["final"].items() if r != "total"}
            self.assertEqual(distinct, s["root_causes"]["by_relation"])
            self.assertEqual(sens["distinct"]["final"]["total"], s["root_causes"]["total"])
            self.assertEqual(s["merge"]["author"], s["root_causes"]["total"])
            self.assertLessEqual(s["merge"]["mechanical"], s["bug_groups"]["total"])
        ag = self.numbers["agree"]["discussion"]["changed"]
        self.assertEqual({w: self.numbers["cur"]["sensitivity"]["bug_groups"][w]["total"]
                          for w in ("author", "rater2", "final")}, ag["bug_groups"])
        self.assertEqual(self.numbers["cur"]["sensitivity"]["distinct"]["decisive"]["total"],
                         self.numbers["cur"]["evidence"]["independent"]["decisive"])


class HelperTest(unittest.TestCase):
    def test_add_sums_nested_and_missing_keys(self) -> None:
        out = ncur.add([{"a": 1, "b": {"x": 2.5}, "s": "text"}, {"a": 2, "b": {"x": 1.0, "y": 4}, "c": 3}])
        self.assertEqual(out, {"a": 3, "b": {"x": 3.5, "y": 4}, "c": 3})

    def test_evidence_block(self) -> None:
        ev = {"C1": {"independent": "decisive", "related_possible": ""},
              "C2": {"independent": "partial", "related_possible": "x#1"},
              "C3": {"independent": "none", "related_possible": ""}}
        out = ncur.evidence_block(ev, ["C1", "C2", "C3"], {"C1": {"R1"}, "C2": {"R0"}, "C3": {"R4", "R0"}})
        self.assertEqual(out["independent"], {"decisive": 1, "partial": 1, "none": 1, "causes": 3})
        self.assertEqual((out["causes"], out["decisive"], out["partial"], out["none"]), (2, 1, 0, 1))
        self.assertEqual((out["excluded_list"], out["related_none"], out["related_none_all"]), ("C2", 2, 2))
        self.assertEqual(out["by_relation"]["R0"], {"decisive": 0, "partial": 1, "none": 1})
        with self.assertRaises(ValueError):
            ncur.evidence_block(ev, ["C1", "C2"], {"C1": {"R1"}, "C2": {"R1"}})


if __name__ == "__main__":
    unittest.main()


class LowerBoundTest(unittest.TestCase):
    def test_union_of_overlapping_sets(self) -> None:
        from numbers_current import lower_bound
        causes = [f"C{i}" for i in range(1, 8)]
        self.assertEqual(lower_bound(causes, [["C1", "C2"], ["C2", "C3"], ["C5", "C6"]]), 4)
        self.assertEqual(lower_bound(causes, []), 7)
        with self.assertRaises(ValueError):
            lower_bound(causes, [["C1", "C99"]])
