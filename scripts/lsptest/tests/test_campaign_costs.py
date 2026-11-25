"""Unit tests for the campaign cost controls: the legitimate-difference label registry, the
signature cap (keys by scope, counts over distinct runs, capped keys, the counts file), the split
of a run's candidates, the per-run counters, and the worker path with a fake oracle (labelled,
capped and replayed candidates; rows and results), plus the scheduler's count bookkeeping.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from typing import Any, List, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import campaign  # noqa: E402
import campaign_estimate  # noqa: E402
import campaign_run  # noqa: E402
import flake  # noqa: E402
from campaign_config import RunSpec  # noqa: E402
from campaign_costs import (COUNTS_FILE, LABELS, CapConfig, cap_key, capped_keys, confirmed_runs, label_of,  # noqa: E402
                            parse_cap, read_capped, register_label, replay_status, signature_label, skip_counts,
                            split_candidates, write_counts)
from campaign_store import CampaignPaths, read_jsonl  # noqa: E402
from model import Op, QueryKey, Violation  # noqa: E402
from oracles.base import ORACLES, OracleContext, OracleResult, ReplayOutcome, difference_shape, make_violation  # noqa: E402

CTX = OracleContext("r1", "ts6", "6", "p@1", "/nonexistent", "typescript", 1, ())


def cand(method: str, oracle: str = "r3_routes", shape_actual: Any = [["b", 1, 1, 1, 2]]) -> Violation:
    return make_violation(CTX, oracle, QueryKey(method, "a.ts", 1, 2), [["a", 1, 1, 1, 2]], shape_actual, [], {"sub": "d"})


class LabelTests(unittest.TestCase):
    def test_registry(self) -> None:
        self.assertTrue(label_of("r3_routes", "definitionConsistency.signature"))
        self.assertTrue(label_of("r3_routes", "definitionConsistency.shorthand"))
        self.assertEqual(label_of("r3_routes", "definitionConsistency"), "")  # unlabelled: never skipped
        self.assertEqual(label_of("r1_history", "definitionConsistency.shorthand"), "")
        self.assertTrue(signature_label("ts6|r3_routes|definitionConsistency.shorthand:extra"))
        self.assertEqual(signature_label("ts6|r3_routes|definitionConsistency:changed"), "")
        register_label("t_extend", "hover.known", "a test label")
        try:
            self.assertEqual(label_of("t_extend", "hover.known"), "a test label")
        finally:
            LABELS.pop("t_extend", None)


class CapTests(unittest.TestCase):
    def test_keys_counts_and_file(self) -> None:
        self.assertEqual(cap_key("s", "p", "v", "campaign"), "s")
        self.assertEqual(cap_key("s", "p", "v", "build"), "s@p@v")
        rows = [{"signature": "s", "run_id": "a", "confirmed": True, "project": "p", "server_version": "v"},
                {"signature": "s", "run_id": "a", "confirmed": True, "project": "p", "server_version": "v"},
                {"signature": "s", "run_id": "b", "confirmed": True, "project": "q", "server_version": "v"},
                {"signature": "s", "run_id": "c", "confirmed": False, "project": "p", "server_version": "v"},
                {"signature": "t", "run_id": "d", "confirmed": True, "incomplete": True}]
        counts = confirmed_runs(rows, "campaign")
        self.assertEqual({k: len(v) for k, v in counts.items()}, {"s": 2})
        self.assertEqual(capped_keys(counts, CapConfig(2)), {"s"})
        self.assertEqual(capped_keys(counts, CapConfig(3)), set())
        self.assertEqual(capped_keys(counts, CapConfig(0)), set())
        self.assertEqual(set(confirmed_runs(rows, "build")), {"s@p@v", "s@q@v"})
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, COUNTS_FILE)
            write_counts(path, counts, CapConfig(2))
            self.assertEqual(read_capped(path), {"s"})
            self.assertEqual(read_capped(os.path.join(tmp, "absent.json"), ["x"]), {"x"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(parse_cap(None), CapConfig(3, "campaign"))
        self.assertEqual(parse_cap({"runs": 0, "scope": "build"}), CapConfig(0, "build"))
        with self.assertRaises(ValueError):
            parse_cap({"scope": "galaxy"})

    def test_split_and_counters(self) -> None:
        a, b = cand("definitionConsistency.signature"), cand("definitionConsistency.signature")
        c, d = cand("definitionConsistency"), cand("highlightVsReferences")
        keep, skipped = split_candidates([a, c, b, d], {d.signature}, "campaign", "p@1", "6")
        self.assertEqual(keep, [c])
        self.assertEqual([(s.status, len(s.violations)) for s in skipped], [("labelled-legitimate", 2), ("capped", 1)])
        self.assertEqual(skip_counts(skipped), {"labelled_legitimate": 1, "labelled_candidates": 2, "capped": 1,
                                                "capped_candidates": 1})
        keep, _ = split_candidates([d], {cap_key(d.signature, "p@1", "6", "build")}, "build", "p@2", "6")
        self.assertEqual(keep, [d])  # capped only for its own build
        self.assertEqual([replay_status(x, False) for x in ("3/3", "1/3", "0/3", "0/0")],
                         ["confirmed", "flaky", "not-reproduced", "not-reproduced"])
        self.assertEqual(replay_status("3/3", True), "incomplete")


class EstimateTests(unittest.TestCase):
    def test_labels_and_cap_in_the_projection(self) -> None:
        rows = [{"run_id": "a", "oracle": "r3_routes", "server_kind": "ts6", "wall_seconds": 110.0, "run_seconds": 100.0,
                 "confirm_seconds": 8.0, "replayed": 4, "confirmed": 4, "candidates": 9, "max_cases": 2,
                 "project": "p@1", "status": "ok", "counters": {"sessions": 3}},
                {"run_id": "b", "oracle": "r0_crash", "server_kind": "ts6", "wall_seconds": 20.0, "run_seconds": 20.0,
                 "confirm_seconds": 0.0, "replayed": 0, "max_cases": 2, "project": "p@1", "status": "ok"}]
        violations = [{"vid": f"a-v0{i}", "run_id": "a", "status": "confirmed", "signature": sig} for i, sig in
                      enumerate(["ts6|r3_routes|definitionConsistency.signature:extra", "ts6|r3_routes|x:changed",
                                 "ts6|r3_routes|definitionConsistency.shorthand:extra", "ts6|r3_routes|y:changed"])]
        table = campaign_estimate.dry_table(rows, violations)
        self.assertEqual(table[("r3_routes", "ts6")]["labelled_replayed"], 2.0)
        spec = RunSpec("c", "r3_routes", "ts6", "6", "p@1", "corpus", "x", "typescript", 1, max_cases=12)
        lo, hi = campaign_estimate.estimate_run(spec, table, {}, CapConfig(3), 6, {})
        self.assertAlmostEqual(hi, 2.0 + 100.0 + 4.0)  # overhead + run + half the confirmation (2 of 4 labelled)
        self.assertAlmostEqual(lo, 2.0 + 100.0 + 4.0 * 3 / 6)  # the cap: confirmations in 3 of the 6 queue runs
        other = RunSpec("c", "r3_routes", "gopls", "1", "p@1", "corpus", "x", "go", 1)
        self.assertEqual(campaign_estimate.estimate_run(other, table, {}, CapConfig(3), 6, {"gopls": "ts6"}), (lo, hi))
        self.assertEqual(campaign_estimate.estimate_run(other, table, {}, CapConfig(3), 6, {}), (0.0, 0.0))


class FakeOracle:
    """Candidates: a labelled one, a capped one and a plain one; every replay reproduces."""

    name = "t_costs"

    def applies_to(self, kind: str) -> bool:
        return True

    def run(self, ctx: OracleContext) -> OracleResult:
        res = OracleResult(self.name, ctx.run_id, sessions=1, cases=1)
        for method in ("hover.known", "hover.capped", "hover"):
            res.candidates.append(make_violation(ctx, self.name, QueryKey(method, "m.py", 0, 1), ["x", None],
                                                 ["y", None], [Op("open", "m.py")], {"family": "H1"}))
        return res

    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        return ReplayOutcome(True, True, True, v)


class WorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.proj = os.path.join(self.tmp, "proj")
        os.makedirs(self.proj)
        with open(os.path.join(self.proj, "m.py"), "w", encoding="utf-8") as f:
            f.write("value = 1\nprint(value)\n")
        self.paths = CampaignPaths(os.path.join(self.tmp, "out"), os.path.join(self.tmp, "scratch"))
        ORACLES["t_costs"] = FakeOracle()
        register_label("t_costs", "hover.known", "test label")

    def tearDown(self) -> None:
        ORACLES.pop("t_costs", None)
        LABELS.pop("t_costs", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_labelled_capped_and_replayed(self) -> None:
        spec = RunSpec("c", "t_costs", "pyright", "1", "proj", "dir", self.proj, "python", 1, min_identifiers=1)
        capped_sig = f"pyright|t_costs|{difference_shape('hover.capped', ['x', None], ['y', None])}"
        counts = os.path.join(self.tmp, COUNTS_FILE)
        write_counts(counts, {capped_sig: {"r1", "r2", "r3"}}, CapConfig(3))
        out = campaign_run.execute(spec, self.paths, flake.FlakeConfig(), 1e9, CapConfig(3), counts)
        self.assertEqual((out["status"], out["candidates"], out["replayed"], out["confirmed"]), ("ok", 3, 1, 1))
        self.assertEqual((out["labelled_legitimate"], out["capped"]), (1, 1))
        by_status = {r["status"]: r for r in out["violations"]}
        self.assertEqual(set(by_status), {"confirmed", "labelled-legitimate", "capped"})
        self.assertEqual(by_status["capped"]["signature"], capped_sig)
        self.assertFalse(by_status["labelled-legitimate"]["confirmed"])
        self.assertEqual(by_status["labelled-legitimate"]["reason"], "test label")
        self.assertTrue(os.path.exists(by_status["confirmed"]["repro"]))  # outside the repository: an absolute path
        self.assertEqual(len(read_jsonl(self.paths.candidates(spec.run_id))), 3)
        out = campaign_run.execute(spec, self.paths, flake.FlakeConfig(), 1e9, CapConfig(0), counts)
        self.assertEqual((out["replayed"], out["capped"]), (2, 0))  # cap off: only the label skips

    def test_scheduler_counts(self) -> None:
        os.makedirs(self.paths.root)
        s = campaign.Scheduler(self.paths, {"n": 3}, 1, cap=CapConfig(2))
        rows: List[Any] = [{"signature": "x", "run_id": r, "confirmed": True} for r in ("a", "b")]
        s.count_confirmed(rows[:1])
        self.assertEqual(read_capped(os.path.join(self.paths.root, COUNTS_FILE)), set())
        s.count_confirmed(rows[1:])
        self.assertEqual(read_capped(os.path.join(self.paths.root, COUNTS_FILE)), {"x"})
        with open(os.path.join(self.paths.root, COUNTS_FILE), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["counts"], {"x": 2})


if __name__ == "__main__":
    unittest.main()
