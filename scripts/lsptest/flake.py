"""Stability protocol for candidate violations (plan/tool_design_v1.md sections 6 and 10).

confirm(oracle, ctx, v, n=3): n independent replays of v's case, each with a fresh
baseline, a fresh control and a fresh case session (Oracle.replay). A replay that does not
settle (a session timed out, an op could not be applied) is retried once. A replay counts
only if it settled, the key was stable in its own baseline/control pair, and the difference
showed the same shape. The returned violation carries reproduced = "k/n"; it is confirmed
only at "n/n" (is_confirmed); anything less is returned with the observed count so that the
campaign can log it as flaky. Each replay is summarized in the note of Violation.detail.
confirm_all() confirms a list of candidates, at most `per_signature` per signature.

Run line: imported by reduce.py, validate_known_bugs.py and the campaign; not run directly.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from model import Op, Violation  # noqa: E402
from oracles.base import Oracle, OracleContext, ReplayOutcome  # noqa: E402

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class FlakeConfig:
    n: int = 3  # independent replays
    unsettled_retries: int = 1  # extra attempts for a replay that did not settle
    per_signature: int = 1  # confirm_all: candidates confirmed per signature (the rest are skipped)


def counts(outcome: ReplayOutcome) -> bool:
    """A replay counts as a reproduction: settled, control stable on the key, same shape."""
    return outcome.settled and outcome.control_stable and outcome.reproduced


def replay_once(oracle: Oracle, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None,
                retries: int = 1) -> Tuple[ReplayOutcome, int]:
    """One replay, retried while it does not settle (at most `retries` times); (outcome, attempts)."""
    attempts = 0
    while True:
        attempts += 1
        out = oracle.replay(ctx, v, ops)
        if out.settled or attempts > retries:
            return out, attempts


def _with_note(v: Violation, text: str) -> str:
    try:
        detail = json.loads(v.detail) if v.detail else {}
    except json.JSONDecodeError:
        detail = {"note": v.detail}
    note = str(detail.get("note", ""))
    detail["note"] = f"{note}; {text}" if note else text
    return json.dumps(detail, sort_keys=True, default=str)


def confirm(oracle: Oracle, ctx: OracleContext, v: Violation, n: int = 3, cfg: FlakeConfig = FlakeConfig()) -> Violation:
    """n independent replays of v; returns a copy with reproduced "k/n" (confirmed when k == n)."""
    t0 = time.monotonic()
    hits, rows = 0, []
    for i in range(n):
        out, attempts = replay_once(oracle, ctx, v, None, cfg.unsettled_retries)
        ok = counts(out)
        hits += int(ok)
        rows.append(f"r{i + 1}:{'S' if out.settled else 's'}{'C' if out.control_stable else 'c'}"
                    f"{'R' if out.reproduced else 'r'}{'+retry' if attempts > 1 else ''}")
        logger.info("replay %d/%d of %s: settled=%s control_stable=%s reproduced=%s (%.1fs)", i + 1, n, v.signature,
                    out.settled, out.control_stable, out.reproduced, out.seconds)
    summary = f"flake {hits}/{n} [{' '.join(rows)}] in {time.monotonic() - t0:.0f}s"
    return dataclasses.replace(v, reproduced=f"{hits}/{n}", detail=_with_note(v, summary))


def is_confirmed(v: Violation) -> bool:
    k, _, n = v.reproduced.partition("/")
    return k.isdigit() and n.isdigit() and int(n) > 0 and k == n


def confirm_all(oracle: Oracle, ctx: OracleContext, candidates: Sequence[Violation],
                cfg: FlakeConfig = FlakeConfig()) -> Tuple[List[Violation], Dict[str, Any]]:
    """Confirm candidates, at most cfg.per_signature per signature (stop a signature at its first
    confirmation). Returns (every violation that was replayed, with its count; statistics)."""
    done: List[Violation] = []
    tried: Dict[str, int] = {}
    confirmed: Dict[str, bool] = {}
    for v in candidates:
        sig = v.signature
        if confirmed.get(sig) or tried.get(sig, 0) >= cfg.per_signature:
            continue
        tried[sig] = tried.get(sig, 0) + 1
        c = confirm(oracle, ctx, v, cfg.n, cfg)
        done.append(c)
        confirmed[sig] = confirmed.get(sig, False) or is_confirmed(c)
    stats = {"candidates": len(candidates), "signatures": len({v.signature for v in candidates}),
             "replayed": len(done), "confirmed": sum(is_confirmed(v) for v in done),
             "flaky": sum(not is_confirmed(v) and not v.reproduced.startswith("0/") for v in done)}
    return done, stats


__all__ = ["FlakeConfig", "confirm", "confirm_all", "counts", "is_confirmed", "replay_once"]
