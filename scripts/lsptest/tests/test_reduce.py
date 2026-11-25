"""Unit tests for reduce.py (ddmin on synthetic predicates, probe cache, probe and time
budgets, pinned opens, offline rejection of inapplicable subsets, probe_scope) and
flake.py (k/n counting, the retry of an unsettled replay, confirm_all per signature).

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import contextlib
import os
import shutil
import sys
import tempfile
import unittest
from typing import Iterator, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import flake  # noqa: E402
from model import Op, QueryKey, Violation  # noqa: E402
from oracles.base import OracleContext, ReplayOutcome, make_violation  # noqa: E402
from reduce import Budget, ReduceConfig, ddmin, reduce_and_confirm, reduce_ops  # noqa: E402


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class DdminTests(unittest.TestCase):
    def test_finds_the_two_needed_items(self) -> None:
        kept, prober = ddmin(list(range(10)), lambda s: 3 in s and 7 in s)
        self.assertEqual(kept, [3, 7])
        self.assertFalse(prober.budget.exhausted())

    def test_contiguous_block_and_single_item(self) -> None:
        self.assertEqual(ddmin(list(range(12)), lambda s: all(x in s for x in (4, 5, 6)))[0], [4, 5, 6])
        self.assertEqual(ddmin(list("abcdefgh"), lambda s: "f" in s)[0], ["f"])
        self.assertEqual(ddmin([1], lambda s: True)[0], [1])

    def test_order_is_kept(self) -> None:
        kept, _ = ddmin([5, 1, 4, 2, 3], lambda s: s.index(4) < s.index(2) if 4 in s and 2 in s else False)
        self.assertEqual(kept, [4, 2])

    def test_cache_never_repeats_a_subset(self) -> None:
        calls: List[tuple] = []

        def test(s: List[int]) -> bool:
            calls.append(tuple(s))
            return 2 in s and 9 in s and 11 in s

        kept, prober = ddmin(list(range(16)), test)
        self.assertEqual(kept, [2, 9, 11])
        self.assertEqual(len(calls), len(set(calls)))
        self.assertEqual(prober.budget.probes, len(calls))
        self.assertGreater(prober.budget.cache_hits, 0)

    def test_probe_budget(self) -> None:
        def test(s: List[int]) -> bool:
            return 3 in s and 7 in s

        kept, prober = ddmin(list(range(32)), test, Budget(max_probes=3))
        self.assertEqual(prober.budget.probes, 3)
        self.assertTrue(prober.budget.exhausted())
        self.assertTrue(test(kept))
        self.assertGreater(len(kept), 2)

    def test_time_budget(self) -> None:
        clock = FakeClock()

        def test(s: List[int]) -> bool:
            clock.now += 10.0
            return 1 in s and 30 in s

        kept, prober = ddmin(list(range(32)), test, Budget(max_probes=1000, max_seconds=25.0, clock=clock))
        self.assertEqual(prober.budget.probes, 3)
        self.assertTrue(test(kept))


# ------------------------------------------------------------ reduce_ops against a fake oracle
KEY = QueryKey("hover", "a.py", 0, 1)


class FakeOracle:
    """Reproduces when the ops still contain the edit X on a.py (and a.py is opened before it);
    records probes and whether they ran inside probe_scope."""

    name = "fake"

    def __init__(self, outcomes: Optional[List[ReplayOutcome]] = None) -> None:
        self.calls: List[Optional[List[Op]]] = []
        self.in_scope = False
        self.scoped_calls = 0
        self.outcomes = list(outcomes or [])

    @contextlib.contextmanager
    def probe_scope(self, ctx: OracleContext) -> Iterator[None]:
        self.in_scope = True
        try:
            yield
        finally:
            self.in_scope = False

    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        self.calls.append(None if ops is None else list(ops))
        self.scoped_calls += int(self.in_scope)
        if self.outcomes:
            return self.outcomes.pop(0)
        seq = list(v.ops if ops is None else ops)
        opened, hit = set(), False
        for op in seq:
            if op.kind == "open":
                opened.add(op.path)
            if op.kind == "change" and op.text == "X":
                hit = hit or op.path in opened
        return ReplayOutcome(True, True, hit)


def outcome(settled: bool = True, stable: bool = True, reproduced: bool = True) -> ReplayOutcome:
    return ReplayOutcome(settled, stable, reproduced)


class ReduceOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp(prefix="reduce-test-")
        for name in ("a.py", "b.py"):
            with open(os.path.join(self.root, name), "w") as f:
                f.write("x = 1\ny = 2\n")
        self.ctx = OracleContext("run", "pyright", "1", "p", self.root, "python", 1, ())
        ops = [Op("open", "a.py"), Op("open", "b.py"), Op("change", "b.py", (0, 0), (0, 0), "# b\n"),
               Op("change", "a.py", (1, 0), (1, 0), "X"), Op("change", "b.py", (0, 0), (1, 0), ""),
               Op("change", "a.py", (1, 0), (1, 1), ""), Op("close", "b.py"), Op("open", "b.py")]
        self.v = make_violation(self.ctx, "fake", KEY, ["t", None], ["u", None], ops, {"family": "H1"})

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_reduces_to_open_plus_edit_inside_probe_scope(self) -> None:
        oracle = FakeOracle()
        res = reduce_ops(oracle, self.ctx, self.v)  # type: ignore[arg-type]
        self.assertEqual([(o.kind, o.path, o.text) for o in res.ops], [("open", "a.py", ""), ("change", "a.py", "X")])
        self.assertEqual(res.original, 8)
        self.assertEqual(oracle.scoped_calls, len(oracle.calls))
        self.assertEqual(res.probes, len(oracle.calls))
        self.assertFalse(res.exhausted)

    def test_inapplicable_subsets_are_rejected_offline(self) -> None:
        oracle = FakeOracle()
        res = reduce_ops(oracle, self.ctx, self.v, ReduceConfig(pin_opens=False))  # type: ignore[arg-type]
        self.assertEqual([(o.kind, o.text) for o in res.ops], [("open", ""), ("change", "X")])
        self.assertGreater(res.free_rejects, 0)  # e.g. a change on b.py without its open
        for call in oracle.calls:
            self.assertTrue(call is not None and all(op.kind != "change" or any(
                o.kind == "open" and o.path == op.path for o in call[:call.index(op)]) for op in call))

    def test_budget_keeps_a_reproducing_superset(self) -> None:
        oracle = FakeOracle()
        res = reduce_ops(oracle, self.ctx, self.v, ReduceConfig(max_probes=2))  # type: ignore[arg-type]
        self.assertTrue(res.exhausted)
        self.assertEqual(res.probes, 2)
        self.assertTrue(oracle.replay(self.ctx, self.v, res.ops).reproduced)

    def test_reduce_and_confirm_sets_reduced_ops(self) -> None:
        v, res, reduced = reduce_and_confirm(FakeOracle(), self.ctx, self.v)  # type: ignore[arg-type]
        self.assertEqual(reduced.reproduced, "3/3")
        self.assertEqual(v.reduced_ops, res.ops)
        self.assertEqual(len(v.ops), 8)


class FlakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = OracleContext("run", "pyright", "1", "p", "/nonexistent", "python", 1, ())
        self.v = make_violation(self.ctx, "fake", KEY, ["t", None], ["u", None], [Op("open", "a.py")], {"family": "H3"})

    def test_all_reproduce(self) -> None:
        c = flake.confirm(FakeOracle([outcome()] * 3), self.ctx, self.v)  # type: ignore[arg-type]
        self.assertEqual(c.reproduced, "3/3")
        self.assertTrue(flake.is_confirmed(c))
        self.assertIn("flake 3/3", c.detail)
        self.assertEqual(c.signature, self.v.signature)

    def test_unsettled_replay_is_retried_once(self) -> None:
        o = FakeOracle([outcome(settled=False), outcome(), outcome(), outcome()])
        c = flake.confirm(o, self.ctx, self.v)  # type: ignore[arg-type]
        self.assertEqual((c.reproduced, len(o.calls)), ("3/3", 4))
        o = FakeOracle([outcome(settled=False), outcome(settled=False), outcome(), outcome()])
        c = flake.confirm(o, self.ctx, self.v)  # type: ignore[arg-type]
        self.assertEqual((c.reproduced, len(o.calls)), ("2/3", 4))
        self.assertFalse(flake.is_confirmed(c))

    def test_unstable_control_or_other_shape_does_not_count(self) -> None:
        o = FakeOracle([outcome(), outcome(stable=False, reproduced=False), outcome(reproduced=False)])
        c = flake.confirm(o, self.ctx, self.v)  # type: ignore[arg-type]
        self.assertEqual(c.reproduced, "1/3")
        self.assertIn("r1:SCR r2:Scr r3:SCr", c.detail)

    def test_confirm_all_one_per_signature(self) -> None:
        other = make_violation(self.ctx, "fake", QueryKey("definition", "a.py", 0, 1), [], [["a.py", 0, 0, 0, 1]],
                               [Op("open", "a.py")], {"family": "H1"})
        o = FakeOracle([outcome(reproduced=False)] * 3 + [outcome()] * 3)
        done, stats = flake.confirm_all(o, self.ctx, [self.v, self.v, other])  # type: ignore[arg-type]
        self.assertEqual([d.reproduced for d in done], ["0/3", "3/3"])
        self.assertEqual((stats["signatures"], stats["replayed"], stats["confirmed"]), (2, 2, 1))


if __name__ == "__main__":
    unittest.main()
