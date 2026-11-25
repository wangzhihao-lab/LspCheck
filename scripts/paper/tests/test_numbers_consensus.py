"""Tests of the counts with the final verdicts (numbers_final, numbers_campaigns, numbers_agree) on synthetic data.

- the merge rule: the consensus row wins, else the verdict both raters gave; a disagreement without a consensus row,
  a missing verdict, an unresolved bug group, an unresolved signature that is not "no", an unknown item and an
  illegal verdict stop the computation; the same through the file loaders on a temporary repository;
- root causes: root_causes.csv must list exactly the final bug groups, a missing file stops the campaign loader,
  causes merge across the campaigns by identifier (first only, second only, both) and one identifier cannot name
  two servers;
- the RQ2 baselines on the current releases and the causes per relation;
- benchmark detection with the final signature verdicts: detected bugs, held-out and strict held-out counts and
  the failing-request observer, where a consensus row turns a detection into none.

Run line: python3 -m unittest scripts/paper/tests/test_numbers_consensus.py
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

import numbers_agree as na  # noqa: E402
import numbers_campaigns as nc  # noqa: E402
import numbers_final as nf  # noqa: E402
from numbers_io import Sources  # noqa: E402


def write_csv(path: str, rows: Sequence[Dict[str, str]], fields: Sequence[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fields))
        w.writeheader()
        w.writerows(rows)


def consensus_row(verdict: str, followed: str = "author", unresolved: str = "no", cls: str = "") -> Dict[str, str]:
    return {"verdict": verdict, "class": cls, "followed": followed, "unresolved": unresolved, "reason": "r",
            "date": "2026-11-21"}


class MergeVerdictsTest(unittest.TestCase):
    """The merge rule of numbers_final.merge_verdicts."""

    def test_consensus_wins_else_both_raters(self) -> None:
        final = nf.merge_verdicts(["a", "b", "c"], {"a": "bug", "b": "legitimate", "c": "bug"},
                                  {"a": "bug", "b": "bug", "c": "tool-artifact"},
                                  {"b": consensus_row("bug", "rater2"),
                                   "c": consensus_row("legitimate", "both", cls="L4")},
                                  "group")
        self.assertEqual({k: f.verdict for k, f in final.items()}, {"a": "bug", "b": "bug", "c": "legitimate"})
        self.assertEqual((final["a"].source, final["b"].source), ("agreed", "consensus"))
        self.assertEqual((final["b"].followed, final["c"].followed, final["c"].cls), ("rater2", "both", "L4"))

    def test_disagreement_without_consensus_stops(self) -> None:
        with self.assertRaises(nf.VerdictConflict) as cm:
            nf.merge_verdicts(["a", "b"], {"a": "bug", "b": "bug"}, {"a": "bug", "b": "legitimate"}, {}, "group")
        self.assertIn("b: the author says 'bug', the second rater 'legitimate'", str(cm.exception))

    def test_missing_verdict_stops(self) -> None:
        with self.assertRaises(nf.VerdictConflict):
            nf.merge_verdicts(["a"], {"a": "bug"}, {}, {}, "group")
        with self.assertRaises(nf.VerdictConflict):
            nf.merge_verdicts(["a"], {"a": ""}, {"a": ""}, {}, "group")

    def test_unresolved_items_count_down(self) -> None:
        final = nf.merge_verdicts(["a"], {"a": "bug"}, {"a": "legitimate"},
                                  {"a": consensus_row("legitimate", "", "yes", "L1")}, "group")
        self.assertTrue(final["a"].unresolved)
        with self.assertRaises(nf.VerdictConflict):
            nf.merge_verdicts(["a"], {"a": "bug"}, {"a": "legitimate"}, {"a": consensus_row("bug", "", "yes")}, "group")
        with self.assertRaises(nf.VerdictConflict):
            nf.merge_verdicts(["s"], {"s": "yes"}, {"s": "partial"}, {"s": consensus_row("partial", "", "yes")},
                              "signature")

    def test_unknown_item_and_illegal_verdict_stop(self) -> None:
        with self.assertRaises(nf.VerdictConflict):
            nf.merge_verdicts(["a"], {"a": "bug"}, {"a": "bug"}, {"zz": consensus_row("bug")}, "group")
        with self.assertRaises(nf.VerdictConflict):
            nf.merge_verdicts(["s"], {"s": "yes"}, {"s": "no"}, {"s": consensus_row("bug")}, "signature")
        with self.assertRaises(nf.VerdictConflict):
            nf.merge_verdicts(["a"], {"a": "maybe"}, {"a": "maybe"}, {}, "group")


class LoadersTest(unittest.TestCase):
    """The file loaders on a temporary repository."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        self.tdir = os.path.join(self.repo, "data/lsptest/runs/main_v1/triage")
        os.makedirs(self.tdir)
        groups = [{"gid": "gopls-r1-a-1", "signature": "gopls|r1_history|references:lost"},
                  {"gid": "gopls-r0-b-2", "signature": "gopls|r0_crash|references:result->error:timeout"},
                  {"gid": "ts6-r6-c-3", "signature": "ts6|r6_crossimpl|definition:extra"}]
        with open(os.path.join(self.tdir, "triage.json"), "w", encoding="utf-8") as f:
            json.dump({"groups": groups}, f)
        write_csv(os.path.join(self.tdir, "decisions.csv"),
                  [{"group": "gopls-r1-a-1", "verdict": "bug"}, {"group": "gopls-r0-b-2", "verdict": "tool-artifact"},
                   {"group": "ts6-r6-c-3", "verdict": "legitimate"}], ["group", "verdict"])
        write_csv(os.path.join(self.tdir, "rater2_decisions.csv"),
                  [{"group": "gopls-r1-a-1", "verdict": "bug", "note": ""},
                   {"group": "gopls-r0-b-2", "verdict": "bug", "note": "不确定"},
                   {"group": "ts6-r6-c-3", "verdict": "legitimate", "note": ""}], ["group", "verdict", "note"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_group_loader(self) -> None:
        fields = ["group", "verdict", "class", "followed", "unresolved", "reason", "date"]
        with self.assertRaises(nf.VerdictConflict):  # disagreement and no consensus file yet
            nf.load_group_verdicts(Sources(self.repo), "main_v1")
        write_csv(os.path.join(self.tdir, "consensus.csv"),
                  [{"group": "gopls-r0-b-2", **consensus_row("bug", "rater2")}], fields)
        gv = nf.load_group_verdicts(Sources(self.repo), "main_v1")
        self.assertEqual({g: f.verdict for g, f in gv.final.items()},
                         {"gopls-r1-a-1": "bug", "gopls-r0-b-2": "bug", "ts6-r6-c-3": "legitimate"})
        self.assertEqual(gv.author["gopls-r0-b-2"], "tool-artifact")

    def test_campaign_loader_needs_root_causes(self) -> None:
        write_csv(os.path.join(self.tdir, "consensus.csv"),
                  [{"group": "gopls-r0-b-2", **consensus_row("bug", "rater2")}],
                  ["group", "verdict", "class", "followed", "unresolved", "reason", "date"])
        with open(os.path.join(self.repo, "data/lsptest/runs/main_v1/config.json"), "w", encoding="utf-8") as f:
            json.dump({"config": {"corpus": nc.CAMPAIGNS["c1"][2]}}, f)
        with self.assertRaises(FileNotFoundError):
            nc.load_campaign(Sources(self.repo), "c1")
        # a draft next to it is not read
        write_csv(os.path.join(self.tdir, "root_causes_draft.csv"),
                  [{"cause": "C1", "server": "gopls", "trigger": "t", "description": "d", "group": "gopls-r1-a-1"}],
                  ["cause", "server", "trigger", "description", "group"])
        with self.assertRaises(FileNotFoundError):
            nc.load_campaign(Sources(self.repo), "c1")
        # root_causes.csv that misses a final bug group
        write_csv(os.path.join(self.tdir, "root_causes.csv"),
                  [{"cause": "C1", "server": "gopls", "trigger": "t", "description": "d", "group": "gopls-r1-a-1"}],
                  ["cause", "server", "trigger", "description", "group"])
        with self.assertRaises(ValueError) as cm:
            nc.load_campaign(Sources(self.repo), "c1")
        self.assertIn("gopls-r0-b-2", str(cm.exception))

    def test_signature_loader(self) -> None:
        bench = os.path.join(self.repo, "data/lsptest/runs/bench_v1")
        write_csv(os.path.join(bench, "detection_author.csv"),
                  [{"case": "x-1", "oracle": "r1_history", "signature": "x|r1_history|a:lost", "author_match": "yes"},
                   {"case": "x-1", "oracle": "r4_edits", "signature": "x|r4_edits|b:extra", "author_match": "no"}],
                  ["case", "oracle", "signature", "author_match"])
        write_csv(os.path.join(bench, "detection_rater2.csv"),
                  [{"case": "x-1", "signature": "x|r1_history|a:lost", "verdict": "partial", "note": ""},
                   {"case": "x-1", "signature": "x|r4_edits|b:extra", "verdict": "no", "note": ""}],
                  ["case", "signature", "verdict", "note"])
        with self.assertRaises(nf.VerdictConflict):
            nf.load_signature_verdicts(Sources(self.repo))
        write_csv(os.path.join(bench, "detection_consensus.csv"),
                  [{"case": "x-1", "signature": "x|r1_history|a:lost", **consensus_row("partial", "rater2")}],
                  ["case", "signature", "verdict", "class", "followed", "unresolved", "reason", "date"])
        sv = nf.load_signature_verdicts(Sources(self.repo))
        self.assertEqual({k: f.verdict for k, f in sv.final.items()},
                         {("x-1", "r1_history", "x|r1_history|a:lost"): "partial",
                          ("x-1", "r4_edits", "x|r4_edits|b:extra"): "no"})


def item(campaign: str, gid: str, relation: str, verdict: str, cause: str = "", failing: bool = False,
         server: str = "gopls") -> nc.Item:
    return nc.Item(campaign, gid, relation, server, verdict, cause, failing)


ITEMS: List[nc.Item] = [
    item("c1", "g-r0-a", "R0", "bug", "C10", True, "rust-analyzer"),
    item("c1", "g-r1-b", "R1", "bug", "C1"),
    item("c2", "g-r1-b", "R1", "bug", "C1"),            # the same cause in the second campaign
    item("c2", "g-r4-c", "R4", "bug", "C2", True),      # a relation's bug group in which a request fails
    item("c2", "t-r6-d", "R6", "legitimate", server="ts7"),
    item("c1", "g-r3-e", "R3", "legitimate", failing=True),
    item("c2", "g-r3-f", "R3", "bug", "C3"),
]


class RootCauseAndBaselineTest(unittest.TestCase):
    def test_check_causes(self) -> None:
        rows = [{"cause": "C1", "server": "gopls", "trigger": "t", "group": "a"}]
        self.assertEqual(set(nc.check_causes(["a"], rows, "x")), {"a"})
        with self.assertRaises(ValueError):
            nc.check_causes(["a", "b"], rows, "x")
        with self.assertRaises(ValueError):
            nc.check_causes([], rows, "x")
        with self.assertRaises(ValueError):
            nc.check_causes(["a"], rows + rows, "x")

    def test_merge_across_campaigns(self) -> None:
        def row(cause: str, server: str = "gopls") -> Dict[str, str]:
            return {"cause": cause, "server": server, "trigger": "t"}
        merged = nc.merge_causes({"c1": {"a": row("C1"), "b": row("C2"), "b2": row("C2")},
                                  "c2": {"a": row("C1"), "c": row("C3"), "d": row("C10")}})
        self.assertEqual(list(merged), ["C1", "C2", "C3", "C10"])
        ov = nc.overlap_block(merged, ["c1", "c2"])
        self.assertEqual((ov["first_only"], ov["second_only"], ov["both"]), (1, 2, 1))
        self.assertEqual((ov["first_only_list"], ov["second_only_list"], ov["both_list"]), ("C2", "C3, C10", "C1"))
        with self.assertRaises(ValueError):
            nc.merge_causes({"c1": {"a": row("C1")}, "c2": {"b": row("C1", "pyright")}})

    def test_baselines(self) -> None:
        b = nc.baseline_section(ITEMS)
        self.assertEqual(b["crash"], {"groups": 1, "bug_groups": 1, "causes": 1, "cause_list": "C10"})
        self.assertEqual(b["cross_impl"], {"groups": 1, "bug_groups": 0, "causes": 0, "cause_list": ""})
        self.assertEqual(b["failing_request"], {"groups": 3, "bug_groups": 2, "causes": 2, "cause_list": "C2, C10"})
        self.assertEqual(b["failing_request_five"], {"groups": 2, "bug_groups": 1, "causes": 1, "cause_list": "C2"})
        self.assertEqual(b["any"], {"causes": 2, "cause_list": "C2, C10"})
        self.assertEqual(b["relations"], {"causes": 3})
        self.assertEqual(b["relations_only"], {"causes": 2, "also_baseline": 1, "also_baseline_list": "C2"})

    def test_causes_per_relation_and_totals(self) -> None:
        hours = {r: 0.0 for r in nc.RELATIONS}
        hours.update(R1=10.0, R4=3.0, R5=7.0)
        rc = nc.relation_causes(ITEMS, hours)
        self.assertEqual(rc["by_relation"], {"R0": 1, "R1": 1, "R2": 0, "R3": 1, "R4": 1, "R5": 0, "R6": 0})
        self.assertEqual(rc["only_relation"], rc["by_relation"])
        self.assertEqual(rc["hours_per_bug"], {"R0": 0.0, "R1": 10.0, "R3": 0.0, "R4": 3.0})
        cs = nc.cause_summary(ITEMS)
        self.assertEqual((cs["total"], cs["list"]), (4, "C1, C2, C3, C10"))
        self.assertEqual(cs["by_server"], {"gopls": 3, "pyright": 0, "rust-analyzer": 1, "ts6": 0, "ts7": 0})
        block = nc.group_block(ITEMS)
        self.assertEqual(block["bug_groups"]["total"], 5)
        self.assertEqual(block["five_relations"], {"groups": 5, "bugs": 4, "precision_pct": 80.0})


def entry(case: str, pre_only: List[Dict[str, Any]], probe: str = "differs_from_fresh",
          spec: bool = False) -> Dict[str, Any]:
    return {"case": case, "kind": case.split("-")[0], "class": "c", "probe": probe, "spec_probe": spec,
            "complete": True, "detected": bool(pre_only), "pre_only": pre_only}


SIG_R1 = ("gopls-1", "r1_history", "gopls|r1_history|a:lost")
SIG_R4 = ("gopls-1", "r4_edits", "gopls|r4_edits|b:extra")
SIG_PRE = ("gopls-60435", "r3_routes", "gopls|r3_routes|c:extra")      # a case run before the freeze
SIG_ERR = ("pyright-2", "r1_history", "pyright|r1_history|hover:result->error:-32603")
ENTRIES = [entry("gopls-1", [{"oracle": "r1_history", "signature": SIG_R1[2], "vids": ["v1"]},
                             {"oracle": "r4_edits", "signature": SIG_R4[2], "vids": ["v2"]}]),
           entry("gopls-60435", [{"oracle": "r3_routes", "signature": SIG_PRE[2], "vids": ["v3"]}]),
           entry("pyright-2", [{"oracle": "r1_history", "signature": SIG_ERR[2], "vids": ["v4"]}]),
           entry("ts-3", [], "edit_text_differs", True)]
VIOLATIONS = [{"vid": "v1", "case": {"family": "H5"}}, {"vid": "v2", "case": {"kind": "mutation"}},
              {"vid": "v3", "case": {"family": "D"}}, {"vid": "v4", "case": {"family": "H5"}}]
ORACLES = ["r0_crash", "r1_history", "r3_routes", "r4_edits"]


class DetectionTest(unittest.TestCase):
    def counts(self, consensus: Dict[Any, Dict[str, str]]) -> Dict[str, Any]:
        universe = [SIG_R1, SIG_R4, SIG_PRE, SIG_ERR]
        author = {SIG_R1: "no", SIG_R4: "yes", SIG_PRE: "yes", SIG_ERR: "yes"}
        rater2 = {SIG_R1: "no", SIG_R4: "yes", SIG_PRE: "partial", SIG_ERR: "yes"}
        final = nf.merge_verdicts(universe, author, rater2, consensus, "signature")
        return na.detection_counts(ENTRIES, {k: f.verdict for k, f in final.items()}, VIOLATIONS, ORACLES)

    def test_consensus_counts(self) -> None:
        out = self.counts({SIG_PRE: consensus_row("yes", "author")})
        self.assertEqual(out["values"], {"no": 1, "yes": 3})
        self.assertEqual((out["all"]["detected"], out["all"]["cases"]), (3, 4))
        self.assertEqual((out["generic"]["detected"], out["spec_probe"]["detected"]), (3, 0))
        held = out["held_out"]
        self.assertEqual(held["held_out"], {"cases": 3, "detected": 2})
        self.assertEqual(held["held_out_strict"]["detected"], 1)  # gopls-1 is found only through a seeded mutation
        self.assertEqual(held["held_out_strict"]["not_credited"], ["gopls-1"])
        self.assertEqual((out["error_oracle"]["any_error_response"], out["error_oracle"]["internal_error_or_timeout"]),
                         (1, 1))
        self.assertEqual(out["held_out_detail"]["error_response"], 1)
        self.assertEqual(out["by_probe_family"]["relation-shaped"], {"cases": 3, "detected": 3})
        self.assertIn("relation_shaped", out["intervals"])

    def test_consensus_can_remove_a_detection(self) -> None:
        out = self.counts({SIG_PRE: consensus_row("partial", "rater2")})
        self.assertEqual(out["all"]["detected"], 2)
        # the pre-freeze case is not held out, so the held-out count does not change
        self.assertEqual(out["held_out"]["held_out"], {"cases": 3, "detected": 2})
        with self.assertRaises(nf.VerdictConflict):
            self.counts({})

    def test_discussion_block(self) -> None:
        f = nf.Final
        block = na.discussion_block({"c1": [f("bug", "consensus", followed="rater2"),
                                            f("legitimate", "consensus", followed="author", unresolved=True)],
                                     "signatures": [f("partial", "consensus", followed="both")]})
        self.assertEqual(block["items"], 3)
        self.assertEqual(block["by_batch"], {"c1": 2, "signatures": 1})
        self.assertEqual(block["followed"], {"author": 1, "rater2": 1, "both": 1})
        self.assertEqual((block["unresolved"], block["unresolved_by_batch"]), (1, {"c1": 1, "signatures": 0}))


if __name__ == "__main__":
    unittest.main()
