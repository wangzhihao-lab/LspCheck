"""Acceptance test of the paper numbers on the real evaluation data.

Runs the whole computation of scripts/paper/paper_numbers.py (nothing is written) and checks the
values the paper quotes for main_v1, the older-release sweep, the benchmark and bench_v1, and the
sections counted with the final verdicts (c1, c2, cur, agree, detection.consensus). The two
author inputs (triage/decisions.csv, detection_author.csv) may be empty or filled; their dependent
numbers are checked for consistency, and the author-dependent views are also checked on synthetic
judgements. A few helper checks cover the statistics and last-row selection.

Run line: python3 -m unittest scripts/paper/tests/test_paper_numbers.py
"""

from __future__ import annotations

import csv
import dataclasses
import json
import os
import re
import sys
import unittest
from typing import Any, Dict, List

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PAPER not in sys.path:
    sys.path.insert(0, PAPER)

import paper_numbers  # noqa: E402
from numbers_bench import after_author, load_detection  # noqa: E402
from numbers_io import Sources, describe, latest, quantile  # noqa: E402
from numbers_main import load_main, verdict_numbers  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(PAPER))
RUNS_DIR = os.path.join(REPO_DIR, "data", "lsptest", "runs")


def read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


DETECTED_BY_ORACLE = {"r4_edits": 19, "r1_history": 12, "r3_routes": 5, "r5_transforms": 3, "r2_handles": 2,
                      "r0_crash": 2}
GENERIC_BY_KIND = {"gopls": (14, 22), "rust-analyzer": (11, 15), "tsserver": (7, 23), "pyright": (4, 12),
                   "jdtls": (2, 2)}
REPRODUCED_BY_KIND = {"gopls": 23, "rust-analyzer": 20, "tsserver": 23, "pyright": 12, "jdtls": 2}


class PaperNumbersTest(unittest.TestCase):
    numbers: Dict[str, Any]
    tables: List[Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.numbers, cls.tables = paper_numbers.compute()

    def test_main_runs(self) -> None:
        runs = self.numbers["main"]["runs"]
        self.assertEqual(runs["total"], 720)
        self.assertEqual(runs["by_status"], {"ok": 718, "timeout": 1, "incomplete": 1})
        self.assertEqual(self.numbers["setup"]["main_v1"]["runs_planned"], 720)

    def test_signatures_and_groups(self) -> None:
        main = self.numbers["main"]
        self.assertEqual(main["confirmed_signatures"]["total"], 98)
        self.assertEqual(main["triage_groups"]["total"], 106)
        self.assertEqual(main["triage_groups"]["by_oracle"]["r1_history"], 29)
        self.assertEqual(main["triage_groups"]["r1_history"]["groups"], 29)

    def test_reduction(self) -> None:
        red = self.numbers["main"]["reduction"]
        self.assertEqual(red["groups_with_ops"], 64)
        self.assertEqual((red["ops_before"], red["ops_after"]), (671, 188))
        self.assertEqual(red["narrowed"], 98)
        self.assertEqual(red["reduced_confirmed"]["3/3"], 98)
        self.assertEqual(red["ops_differ_from_triage_json"], [])

    def test_sweep_older_2025(self) -> None:
        sweep = self.numbers["main"]["sweep_older_2025"]
        self.assertEqual({k: v for k, v in sweep["by_verdict"].items() if v},
                         {"reproduced": 63, "not-reproduced": 12, "flaky": 4, "unsettled": 3, "skipped": 24})
        self.assertEqual(sweep["replayed"], 106 - 24)

    def test_bench_runs(self) -> None:
        runs = self.numbers["detection"]["runs"]
        self.assertEqual(runs["recorded"]["total"], 2232)
        self.assertEqual(runs["planned"]["total"] + runs["recorded_outside_plan"]["total"], 2232)

    def test_detection(self) -> None:
        det = self.numbers["detection"]
        g, s = det["generic"], det["spec_probe"]
        self.assertEqual((g["detected"], g["cases"], g["complete"]), (38, 74, 69))
        self.assertEqual((s["detected"], s["cases"], s["complete"]), (1, 6, 5))
        self.assertEqual(g["detected_by_oracle"], DETECTED_BY_ORACLE)
        by_kind = {k: (v["detected"], v["cases"]) for k, v in det["by_kind"]["generic"].items()}
        self.assertEqual(by_kind, GENERIC_BY_KIND)
        self.assertEqual(det["pre_only_signatures"]["total"], 77)
        self.assertEqual(det["r0_crash"]["detected_by_r0_alone"], 0)
        self.assertTrue(det["consistency"]["matches_detection_json"], det["consistency"]["cases_differing"])

    def test_benchmark(self) -> None:
        bench = self.numbers["benchmark"]
        self.assertEqual(bench["funnel"]["attempted"], 92)
        self.assertEqual(bench["funnel"]["reproduced"], 80)
        self.assertEqual(bench["reproduced_by_kind"], REPRODUCED_BY_KIND)
        self.assertEqual(bench["funnel"]["spec_probe_reproduced"], 6)
        self.assertEqual(len(bench["not_reproduced"]), 12)

    def test_author_dependent_numbers(self) -> None:
        verdicts = self.numbers["main"]["verdicts"]
        if verdicts["judged"]:
            self.assertAlmostEqual(verdicts["precision"], verdicts["by_verdict"]["bug"] / verdicts["judged"], places=3)
        else:
            self.assertIsNone(verdicts["precision"])
        det = self.numbers["detection"]
        if det["pre_only_signatures"]["author_match_filled"]:
            self.assertIsNotNone(det["after_author"])
        else:
            self.assertIsNone(det["after_author"])

    def test_tables(self) -> None:
        rows = {t.name: len(t.rows) for t in self.tables if t.name not in ("J_cost", "N1_lifecycle", "N2_newest",
                                                                            "N3_upstream")}
        self.assertEqual(rows, {"D_corpus": 80, "E_benchmark": 92, "F_detection": 80, "G_groups": 227,
                                "G3_sensitivity": 4, "G4_rater2": 18, "G5_rater2_disagreements": 35, "I_sweep": 227,
                                "K_freeze": 3, "M2_isolation": 15, "M3_cross": 21, "M4_c1_checks": 24,
                                "G2_root_causes": 83, "M_evidence": 33})  # C23, C24 withdrawn 2026-11-24
        cost = next(t for t in self.tables if t.name == "J_cost")
        runs = {c: sum(r[3] for r in cost.rows if r[0] == c) for c in ("main_v1", "main_v2", "bench_v1")}
        self.assertEqual(runs, {"main_v1": 720, "main_v2": 690, "bench_v1": 2232})

    def test_release_tables(self) -> None:
        """The replay tables of both campaigns, counted from the replay data: N1 one row per build of every cause's
        lifecycle (figure data), N2 the newest-release rows of both campaigns' bug groups (last row per group) and
        main_v1's gopls development head, N3 the upstream reports."""
        with open(os.path.join(REPO_DIR, "data", "lsptest", "figure_data.json"), encoding="utf-8") as f:
            life = json.load(f)["lifecycle_cur"]
        newest = 0
        for run in ("main_v1", "main_v2"):
            groups = {r["group"] for r in read_csv(os.path.join(RUNS_DIR, run, "triage", "root_causes.csv"))}
            newest += len({r["gid"] for r in read_jsonl(os.path.join(RUNS_DIR, run, "sweep", "newest-2026-11-18",
                                                                     "results.jsonl")) if r["gid"] in groups})
        head = len(read_jsonl(os.path.join(RUNS_DIR, "main_v1", "sweep", "head-2026-11-18", "results.jsonl")))
        upstream = len(read_csv(os.path.join(RUNS_DIR, "main_v1", "upstream", "feedback.csv")))
        rows = {t.name: len(t.rows) for t in self.tables if t.name in ("N1_lifecycle", "N2_newest", "N3_upstream")}
        self.assertEqual(rows, {"N1_lifecycle": sum(len(v["cells"]) for v in life.values()),
                                "N2_newest": newest + head, "N3_upstream": upstream})
        self.assertEqual(len(life), self.numbers["cur"]["root_causes"]["total"])

    def test_tables_follow_final_verdicts(self) -> None:
        """The two-corpus tables count what the final-verdict sections count."""
        t = {x.name: x for x in self.tables}
        cur, agree = self.numbers["cur"], self.numbers["agree"]
        groups = t["G_groups"]
        col = {c: i for i, c in enumerate(groups.columns)}
        verdicts: Dict[str, int] = {}
        for r in groups.rows:
            verdicts[r[col["verdict"]]] = verdicts.get(r[col["verdict"]], 0) + 1
        self.assertEqual(verdicts, cur["verdicts"]["by_verdict"])
        self.assertEqual(sum(1 for r in groups.rows if r[col["discussed"]] == "yes"),
                         agree["discussion"]["by_batch"]["c1"] + agree["discussion"]["by_batch"]["c2"])
        self.assertEqual(len(t["G5_rater2_disagreements"].rows), agree["discussion"]["items"])
        det = t["F_detection"]
        jv = det.columns.index("joint_verdicts")
        self.assertEqual(sum(1 for r in det.rows if "yes" in r[jv].split()),
                         self.numbers["detection"]["consensus"]["all"]["detected"])
        g4 = {(r[0], r[1]): r for r in t["G4_rater2"].rows}
        self.assertEqual((g4[("second corpus", "all")][2], g4[("second corpus", "all")][3]), (121, 116))
        self.assertEqual(g4[("benchmark signatures", "without practice cases")][2], 62)
        m4 = t["M4_c1_checks"]
        second = {r[1]: r[2] for r in m4.rows if r[0] == "second"}
        self.assertEqual(len(second), 8)
        self.assertEqual(second["ts6-r1-inlayhint-changed-h9-b9d052"], "C31")

    def test_figure_data_matches_numbers(self) -> None:
        """The figures count the same bugs as the text: detections under the joint verdicts, and bug groups and
        distinct bugs per oracle over both corpora under the final verdicts."""
        with open(os.path.join(PAPER, "..", "..", "data", "lsptest", "figure_data.json"), encoding="utf-8") as f:
            fig = json.load(f)
        rows = fig["benchmark_overlap"]["rows"]
        relations = {"R1", "R2", "R3", "R4", "R5"}
        dc = self.numbers["detection"]["consensus"]
        self.assertEqual(sum(1 for r in rows if relations & set(r["oracles"])), dc["all"]["detected"])
        self.assertEqual(sum(1 for r in rows if r["held_out"] and relations & set(r["oracles"])),
                         dc["held_out"]["held_out"]["detected"])
        cur = self.numbers["cur"]
        for key in ("R0", "R1", "R2", "R3", "R4", "R5", "R6"):
            last = fig["bugs_over_time"][key]["points"][-1]
            self.assertEqual(last["bug_groups"], cur["bug_groups"]["by_relation"][key])
            self.assertEqual(last["bugs"], cur["root_causes"]["by_relation"][key])
            self.assertEqual(last["groups"], cur["groups"]["by_relation"][key])
            self.assertAlmostEqual(fig["bugs_over_time"][key]["hours"], cur["run_hours"]["by_relation"][key], delta=0.006)
            self.assertAlmostEqual(fig["bugs_over_time"][key]["campaign_start_hours"]["main_v2"],
                                   self.numbers["c1"]["run_hours"]["by_relation"][key], delta=0.006)

    def test_release_matches_root_causes(self) -> None:
        """release covers the causes of main_v1's replays (counted from its root-cause table and replay rows);
        cur.newest and cur.lifecycle cover the causes of both campaigns."""
        cause = {r["group"]: r["cause"] for r in read_csv(os.path.join(RUNS_DIR, "main_v1", "triage", "root_causes.csv"))}
        rows = read_jsonl(os.path.join(RUNS_DIR, "main_v1", "sweep", "newest-2026-11-18", "results.jsonl"))
        release = self.numbers["release"]
        self.assertEqual(release["newest"]["causes"], len({cause[r["gid"]] for r in rows if r["gid"] in cause}))
        with open(os.path.join(RUNS_DIR, "main_v1", "sweep", "lifecycle", "releases.json"), encoding="utf-8") as f:
            planned = {g["cause"] for g in json.load(f)["groups"]}
        self.assertEqual(release["lifecycle"]["causes"], len(planned))
        cur = self.numbers["cur"]
        self.assertEqual(cur["lifecycle"]["causes"], cur["root_causes"]["total"])
        self.assertLessEqual(cur["newest"]["causes"], cur["root_causes"]["total"])

    def test_final_verdict_sections(self) -> None:
        """c1, c2 and cur count with the final verdicts (the discussion's, else both raters')."""
        c1, c2, cur = (self.numbers[k] for k in ("c1", "c2", "cur"))
        self.assertEqual((c1["runs"]["planned"], c1["runs"]["recorded"], c1["runs"]["ok"]), (720, 720, 718))
        self.assertEqual((c2["runs"]["planned"], c2["runs"]["recorded"], c2["runs"]["ok"]), (690, 690, 689))
        self.assertEqual((c1["groups"]["total"], c2["groups"]["total"], cur["groups"]["total"]), (106, 121, 227))
        self.assertEqual((c1["bug_groups"]["total"], c2["bug_groups"]["total"], cur["bug_groups"]["total"]),
                         (34, 49, 83))  # two first-corpus groups re-judged after the discussion (triage/rejudged.csv)
        self.assertEqual(c1["bug_groups"]["by_relation"],
                         {"R0": 0, "R1": 17, "R2": 2, "R3": 5, "R4": 10, "R5": 0, "R6": 0})  # R0 timeouts re-judged
        self.assertEqual(c2["bug_groups"]["by_relation"],
                         {"R0": 1, "R1": 23, "R2": 2, "R3": 3, "R4": 17, "R5": 3, "R6": 0})
        self.assertEqual((c1["five_relations"]["bugs"], c1["five_relations"]["groups"]), (34, 91))
        self.assertEqual((c2["five_relations"]["bugs"], c2["five_relations"]["groups"]), (48, 110))
        self.assertEqual((cur["five_relations"]["bugs"], cur["five_relations"]["groups"]), (82, 201))
        self.assertEqual(c1["confirmed_signatures"], self.numbers["main"]["confirmed_signatures"]["total"])
        self.assertAlmostEqual(c1["run_hours"]["total"], self.numbers["main"]["run_seconds"]["total_hours"], delta=0.011)
        self.assertEqual((c1["corpus"]["projects"], c2["corpus"]["projects"], cur["projects_distinct"]), (40, 40, 80))
        rc = cur["root_causes"]
        self.assertEqual(rc["total"], rc["first_only"] + rc["second_only"] + rc["both"])
        self.assertEqual(sum(rc["by_server"].values()), rc["total"])
        self.assertEqual(c1["root_causes"]["total"], rc["first_only"] + rc["both"])
        self.assertEqual(c2["root_causes"]["total"], rc["second_only"] + rc["both"])
        base = cur["baseline"]
        self.assertEqual((base["crash"]["groups"], base["crash"]["bug_groups"]), (3, 1))  # two timeouts re-judged
        self.assertEqual((base["cross_impl"]["groups"], base["cross_impl"]["bug_groups"]), (23, 0))
        self.assertEqual(base["relations_only"]["causes"] + base["relations_only"]["also_baseline"],
                         base["relations"]["causes"])
        # the older sections keep the first author's verdicts and the first campaign's 11 causes
        self.assertEqual(self.numbers["main"]["verdicts"]["by_verdict"]["bug"], 29)
        self.assertEqual(self.numbers["main"]["root_causes"]["groups"], 29)

    def test_agreement_and_discussion(self) -> None:
        ag = self.numbers["agree"]
        self.assertAlmostEqual(ag["c1"]["three_class"]["kappa"], self.numbers["rater2"]["three_class"]["kappa"])
        self.assertEqual((ag["c1"]["three_class"]["agree"], ag["c1"]["three_class"]["n"]), (83, 106))
        self.assertEqual((ag["c2"]["three_class"]["agree"], ag["c2"]["three_class"]["n"]), (116, 121))
        self.assertEqual((ag["signatures"]["all"]["n"], ag["signatures"]["without_practice"]["n"]), (77, 62))
        disc = ag["discussion"]
        self.assertEqual((disc["items"], disc["by_batch"]), (35, {"c1": 23, "c2": 5, "signatures": 7}))
        self.assertEqual(disc["unresolved"], 0)
        ch = disc["changed"]
        self.assertEqual(ch["c1_bug_groups"], {"author": 29, "rater2": 38, "final": 34})
        self.assertEqual(ch["c2_bug_groups"], {"author": 49, "rater2": 52, "final": 49})
        self.assertEqual(ch["signatures_yes"]["final"], 54)  # item 35 (rust-analyzer-21173) yes since 11-21
        self.assertEqual(ch["detected"], {"author": 33, "rater2": 31, "final": 32})
        self.assertEqual(ch["detected"]["author"], self.numbers["detection"]["after_author"]["all"]["detected"])

    def test_detection_consensus(self) -> None:
        dc = self.numbers["detection"]["consensus"]
        self.assertEqual(dc["values"], {"no": 17, "partial": 6, "yes": 54})
        self.assertEqual((dc["all"]["detected"], dc["all"]["cases"]), (32, 80))
        self.assertEqual(dc["held_out"]["held_out"], {"cases": 74, "detected": 27})
        self.assertEqual(dc["from_consensus"], 7)

    def test_sources(self) -> None:
        sources = self.numbers["sources"]
        self.assertIn("data/lsptest/runs/bench_v1/detection_author.csv", sources)
        self.assertIn("data/lsptest/runs/main_v1/triage/decisions.csv", sources)
        for run in ("main_v1", "main_v2"):
            for name in ("consensus.csv", "rater2_decisions.csv", "root_causes.csv"):
                self.assertIn(f"data/lsptest/runs/{run}/triage/{name}", sources)
        self.assertIn("data/lsptest/runs/bench_v1/detection_consensus.csv", sources)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{16}", v) for v in sources.values()))


class AuthorViewsTest(unittest.TestCase):
    """The author-dependent numbers on synthetic judgements (the real files are never touched)."""

    def test_after_author_counts_only_yes(self) -> None:
        dd = load_detection(Sources())
        values = {(e["case"], p["oracle"], p["signature"]): "no" for e in dd.entries for p in e["pre_only"]}
        target = next(e for e in dd.entries if not e["spec_probe"] and e["pre_only"])
        first = target["pre_only"][0]
        values[(target["case"], first["oracle"], first["signature"])] = "yes"
        out = after_author(dd.entries, values, sorted(dd.config["config"]["oracles"]))
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual((out["judged"], out["pending"]), (77, 0))
        self.assertEqual(out["generic"]["detected"], 1)
        self.assertEqual(out["generic"]["detected_by_oracle"], {first["oracle"]: 1})
        self.assertEqual(out["spec_probe"]["detected"], 0)
        self.assertIsNone(after_author(dd.entries, {k: "" for k in values}, ["r0_crash"]))

    def test_verdicts_precision_and_minutes(self) -> None:
        main = load_main(Sources())
        gids = [g["gid"] for g in main.groups]
        fake = {gid: {**main.decisions[gid], "verdict": "", "minutes_spent": ""} for gid in gids}
        fake[gids[0]].update(verdict="bug", minutes_spent="12")
        fake[gids[1]].update(verdict="legitimate", minutes_spent="3.5")
        out = verdict_numbers(dataclasses.replace(main, decisions=fake))
        self.assertEqual(out["judged"], 2)
        self.assertEqual(out["precision"], 0.5)
        self.assertEqual(out["minutes_total"], 15.5)


class HelperTest(unittest.TestCase):
    def test_quantile_and_describe(self) -> None:
        self.assertEqual(quantile([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0], 0.9), 10.0)
        self.assertEqual(quantile([5.0], 0.9), 5.0)
        self.assertEqual(describe([1.0, 2.0, 3.0, 10.0]),
                         {"n": 4, "total": 16.0, "mean": 4.0, "median": 2.5, "p90": 7.9})
        self.assertIsNone(describe([])["mean"])

    def test_latest_keeps_last_row_in_first_seen_order(self) -> None:
        rows = [{"id": "a", "v": 1}, {"id": "b", "v": 2}, {"id": "a", "v": 3}]
        self.assertEqual(latest(rows, "id"), [{"id": "a", "v": 3}, {"id": "b", "v": 2}])


if __name__ == "__main__":
    unittest.main()
