"""Delta debugging over the ops of a violation (plan/tool_design_v1.md sections 6 and 10).

ddmin(items, test) is Zeller's minimizing delta debugging over a list: `test` receives
candidate subsequences (original order kept) and is assumed True on the whole list.
Probes are cached by subset (Prober) and charged to a Budget (probes and seconds); when
the budget runs out, the smallest passing subsequence found so far is returned.

reduce_ops(oracle, ctx, v) runs ddmin over v.ops with the predicate "one replay
(Oracle.replay with ops=subset) reproduces v". A subset whose ops cannot be applied fails:
offline (base.final_state raises OpError) without a replay and without charging the budget,
otherwise through the replay itself. "open" ops are pinned during the main pass (a change
that lost its open can only fail), then each pinned open is dropped if the violation still
reproduces without it, so the result does not depend on the pinning. An oracle may offer
probe_scope(ctx), a context manager under which replays may reuse reference sessions (R1
reuses the fresh pair of an identical final state); reduce_and_confirm() therefore
re-confirms the reduced ops with independent replays (flake.confirm, 3/3).

Run line: imported by validate_known_bugs.py and the campaign; not run directly.
"""

from __future__ import annotations

import contextlib
import dataclasses
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, TypeVar

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import flake  # noqa: E402
from model import Op, Violation  # noqa: E402
from oracles.base import Oracle, OracleContext, final_state  # noqa: E402
from ops import OpError  # noqa: E402

logger = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass(frozen=True)
class ReduceConfig:
    max_probes: int = 64  # replays charged to the budget
    max_seconds: float = 7200.0
    pin_opens: bool = True  # keep "open" ops during the main pass, try dropping them afterwards


@dataclass
class Budget:
    max_probes: int = 64
    max_seconds: float = 7200.0
    clock: Callable[[], float] = time.monotonic
    probes: int = 0
    cache_hits: int = 0
    free_rejects: int = 0  # subsets rejected offline (not charged)
    started: float = field(default=0.0)

    def __post_init__(self) -> None:
        self.started = self.clock()

    def elapsed(self) -> float:
        return self.clock() - self.started

    def exhausted(self) -> bool:
        return self.probes >= self.max_probes or self.elapsed() >= self.max_seconds


class Prober:
    """test() on index subsets with a cache; an exhausted budget makes new subsets fail."""

    def __init__(self, test: Callable[[List[int]], bool], budget: Budget,
                 precheck: Optional[Callable[[List[int]], bool]] = None) -> None:
        self.test, self.budget, self.precheck = test, budget, precheck
        self.cache: Dict[Tuple[int, ...], bool] = {}
        self.log: List[Tuple[int, bool]] = []  # (subset size, outcome) per charged probe

    def __call__(self, subset: Sequence[int]) -> bool:
        key = tuple(sorted(subset))
        if key in self.cache:
            self.budget.cache_hits += 1
            return self.cache[key]
        if self.precheck is not None and not self.precheck(list(key)):
            self.budget.free_rejects += 1
            self.cache[key] = False
            return False
        if self.budget.exhausted():
            return False  # not cached: the subset was never tried
        self.budget.probes += 1
        ok = bool(self.test(list(key)))
        self.cache[key] = ok
        self.log.append((len(key), ok))
        logger.info("probe %d: %d item(s) -> %s", self.budget.probes, len(key), ok)
        return ok


def _split(items: List[int], n: int) -> List[List[int]]:
    k, out, start = len(items), [], 0
    for i in range(n):
        stop = start + (k - start) // (n - i)
        out.append(items[start:stop])
        start = stop
    return [c for c in out if c]


def ddmin_indices(n_items: int, probe: Callable[[Sequence[int]], bool], budget: Budget) -> List[int]:
    """ddmin over range(n_items); returns the kept indices (a 1-minimal set if the budget allowed)."""
    c, n = list(range(n_items)), 2
    while len(c) >= 2 and not budget.exhausted():
        chunks = _split(c, n)
        sub = next((ch for ch in chunks if len(chunks) > 1 and probe(ch)), None)
        if sub is not None:
            c, n = sub, 2
            continue
        comp = next((co for co in ([x for j, ch in enumerate(chunks) if j != i for x in ch] for i in range(len(chunks)))
                     if len(chunks) > 2 and probe(co)), None)
        if comp is not None:
            c, n = comp, max(n - 1, 2)
            continue
        if n >= len(c):
            break
        n = min(len(c), 2 * n)
    return c


def ddmin(items: Sequence[T], test: Callable[[List[T]], bool], budget: Optional[Budget] = None) -> Tuple[List[T], Prober]:
    """Minimize `items` under `test` (True on the whole list); returns (kept items, prober)."""
    budget = budget or Budget()
    prober = Prober(lambda idx: test([items[i] for i in idx]), budget)
    return [items[i] for i in ddmin_indices(len(items), prober, budget)], prober


@dataclass
class ReduceResult:
    ops: List[Op]
    original: int  # ops before reduction
    probes: int
    cache_hits: int
    free_rejects: int
    seconds: float
    exhausted: bool
    log: List[Tuple[int, bool]] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["ops"] = [o.to_json() for o in self.ops]
        return d


def reproduces(oracle: Oracle, ctx: OracleContext, v: Violation, ops: Sequence[Op]) -> bool:
    out = oracle.replay(ctx, v, ops)
    return flake.counts(out)


def reduce_ops(oracle: Oracle, ctx: OracleContext, v: Violation, cfg: ReduceConfig = ReduceConfig(),
               clock: Callable[[], float] = time.monotonic,
               predicate: Optional[Callable[[List[Op]], bool]] = None) -> ReduceResult:
    """ddmin over v.ops with "one replay reproduces v" (or `predicate`, for tests)."""
    ops = list(v.ops)
    budget = Budget(cfg.max_probes, cfg.max_seconds, clock)
    test = predicate or (lambda sub: reproduces(oracle, ctx, v, sub))

    def applicable(idx: List[int]) -> bool:
        try:
            final_state(ctx.project_dir, [ops[i] for i in idx])
        except OpError:
            return False
        return True

    prober = Prober(lambda idx: test([ops[i] for i in idx]), budget, applicable)
    pinned = [i for i, o in enumerate(ops) if o.kind == "open"] if cfg.pin_opens else []
    free = [i for i in range(len(ops)) if i not in pinned]
    scope = getattr(oracle, "probe_scope", None)
    with scope(ctx) if callable(scope) else contextlib.nullcontext():
        kept_free = ddmin_indices(len(free), lambda sub: prober(pinned + [free[j] for j in sub]), budget)
        kept = sorted(pinned + [free[j] for j in kept_free])
        dropped = False
        for i in pinned:
            trial = [k for k in kept if k != i]
            if not budget.exhausted() and trial and prober(trial):
                kept, dropped = trial, True
        if dropped and len(kept) > 1:  # ops that only a dropped open needed (e.g. a close before it)
            base = list(kept)
            kept = [base[j] for j in ddmin_indices(len(base), lambda sub: prober([base[j] for j in sub]), budget)]
    logger.info("reduced %d -> %d ops in %d probes (%d cached, %d rejected offline)%s", len(ops), len(kept),
                budget.probes, budget.cache_hits, budget.free_rejects, " [budget exhausted]" if budget.exhausted() else "")
    return ReduceResult([ops[i] for i in kept], len(ops), budget.probes, budget.cache_hits, budget.free_rejects,
                        round(budget.elapsed(), 3), budget.exhausted(), prober.log)


def reduce_and_confirm(oracle: Oracle, ctx: OracleContext, v: Violation, cfg: ReduceConfig = ReduceConfig(),
                       n: int = 3) -> Tuple[Violation, ReduceResult, Violation]:
    """Reduce v, then confirm the reduced ops with n independent replays. Returns (v with
    reduced_ops set when the reduced case reproduced n/n, the reduction, the reduced confirmation)."""
    res = reduce_ops(oracle, ctx, v, cfg)
    reduced = flake.confirm(oracle, ctx, dataclasses.replace(v, ops=list(res.ops), reduced_ops=[]), n)
    return dataclasses.replace(v, reduced_ops=list(res.ops) if flake.is_confirmed(reduced) else []), res, reduced


__all__ = ["Budget", "Prober", "ReduceConfig", "ReduceResult", "ddmin", "ddmin_indices", "reduce_and_confirm",
           "reduce_ops", "reproduces"]
