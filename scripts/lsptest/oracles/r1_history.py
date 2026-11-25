"""R1 history independence (plan/tool_design_v1.md sections 5 and 10).

run(): a fresh baseline and a fresh control on the original project give the stable keys
(equal in both, not lost to a timeout); then up to ctx.max_cases histories from
histories.py. Default mode: each history runs in its own fresh session and is compared,
on the stable keys, with the fresh sessions on final_state(history) (the original project
for a round trip). Chain mode (slow-starting servers, CHAIN_KINDS): one session runs the
prelude and the bodies H1..Hn with a snapshot after each; a difference first seen at step
k is recorded with the ops prelude + H1..Hk. Candidates carry case = {family, timing, mode,
chain_step, seed, history_seed, history_index, note}.

replay(): fresh baseline + fresh control on materialize(final_state(ops)) (the original
project when the state is a round trip; state.settings as the settings overlay otherwise),
plus a fresh session that applies the ops in the case's timing; reproduced = the key is
stable in the replay and differs with the same shape. Inside probe_scope() (used by
reduce.py) the fresh pair of an identical final state is reused across probes.
Baseline and control run side by side; every other session runs alone.

Run line: imported through oracles.load_all(); not run directly.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import logging
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set, Tuple

from .base import (  # noqa: I001  (base puts scripts/lsptest and lsp_repro on sys.path)
    MISSING, FinalState, OracleContext, OracleResult, ReplayOutcome, SessionInfo, apply_history, case_of, compare,
    difference_shape, discard, final_state, make_violation, materialize, register_oracle, run_session, session,
    shape_of, stable_keys,
)
import servers  # noqa: E402  (lsp_repro)
from driver import SESSION_SETTINGS  # noqa: E402
from histories import History, HistoryConfig, Workspace, build_workspace, generate_many, round_trip  # noqa: E402
from model import Op, QueryKey, Snapshot  # noqa: E402
from ops import OpError, deep_merge  # noqa: E402

logger = logging.getLogger(__name__)

ORACLE = "r1_history"
CHAIN_KINDS = frozenset({"rust-analyzer", "jdtls"})
SESSION_ERRORS = (RuntimeError, OSError, ValueError, subprocess.SubprocessError)  # LspError, OpError included
# Servers may react to file-system and configuration changes through their own watchers and
# queues, later than the push settle's quiet window (ts6: tsserver re-checks an open file about
# 3 s after a rename it saw by itself), and the settle waits for a fresh publish only after
# didOpen/didChange. After such ops the session therefore waits this long before the snapshot
# (which settles again); the wait is not part of the recorded ops.
GUARDED_KINDS = frozenset({"fs_write", "fs_rename", "set_config"})
GUARD_MIN_S, GUARD_QUIET_FACTOR = 6.0, 3.0


@dataclasses.dataclass
class Pair:
    baseline: Snapshot
    control: Snapshot
    stable: Set[QueryKey]

    @property
    def settled(self) -> bool:
        return self.baseline.settled and self.control.settled


def effective_settings(ctx: OracleContext) -> Dict[str, Any]:
    """The settings a session of ctx answers workspace/configuration with (launch spec + session)."""
    extra = SESSION_SETTINGS.get(ctx.server_kind, {}) if ctx.extra_settings is None else dict(ctx.extra_settings)
    try:
        spec = servers.resolve(ctx.server_kind, ctx.server_version).settings or {}
    except (FileNotFoundError, ValueError):
        spec = {}
    return deep_merge(dict(spec), dict(extra))


def guard_ops(ctx: OracleContext, ops: Sequence[Op]) -> List[Op]:
    """A wait before the snapshot when `ops` change files on disk or settings (see GUARDED_KINDS)."""
    if not any(op.kind in GUARDED_KINDS for op in ops):
        return []
    try:
        quiet = servers.resolve(ctx.server_kind, ctx.server_version).quiet_seconds
    except (FileNotFoundError, ValueError):
        quiet = 2.0
    return [Op("wait", delay_ms=int(1000 * max(GUARD_MIN_S, GUARD_QUIET_FACTOR * quiet)))]


def safe_session(ctx: OracleContext, label: str, ops: Sequence[Op] = (), project_dir: Optional[str] = None,
                 overlay: Optional[Dict[str, Any]] = None) -> Tuple[Snapshot, SessionInfo]:
    """base.run_session that turns a failed start or a dead server into an invalid session."""
    t0 = time.monotonic()
    try:
        return run_session(ctx, label, ops, project_dir, None, overlay)
    except SESSION_ERRORS as exc:
        logger.warning("session %s failed: %s: %s", label, type(exc).__name__, exc)
        return (Snapshot(label, ctx.server, False),
                SessionInfo(label, False, False, [f"{type(exc).__name__}: {exc}"[:300]], round(time.monotonic() - t0, 3)))


def fresh_pair(ctx: OracleContext, label: str, project_dir: Optional[str] = None,
               overlay: Optional[Dict[str, Any]] = None) -> Pair:
    """Fresh baseline and fresh control on the same content, side by side."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        fb = pool.submit(safe_session, ctx, f"{label}-baseline", (), project_dir, overlay)
        fc = pool.submit(safe_session, ctx, f"{label}-control", (), project_dir, overlay)
        b, c = fb.result()[0], fc.result()[0]
    return Pair(b, c, stable_keys(b, c))


def state_key(st: FinalState, settings: Dict[str, Any]) -> str:
    """"" for a round trip (compare with the original project), else the canonical final state."""
    return "" if round_trip(st, settings) else json.dumps({"files": st.files, "settings": st.settings}, sort_keys=True)


def pair_for_state(ctx: OracleContext, st: FinalState, key: str, label: str) -> Pair:
    """Fresh pair on the content a history leaves behind (materialized only when files differ)."""
    tmp = materialize(ctx, st, f"{label}-{uuid.uuid4().hex[:8]}") if key and st.files else ""
    try:
        return fresh_pair(ctx, label, tmp or None, st.settings if key else None)
    finally:
        if tmp:
            discard(tmp)


class _Run:
    """State of one R1 run: counters, reference pairs per final state, chain dedup."""

    def __init__(self, ctx: OracleContext, res: OracleResult, settings: Dict[str, Any]) -> None:
        self.ctx, self.res, self.settings = ctx, res, settings
        self.pairs: Dict[str, Pair] = {}
        self.seen: Set[Tuple[QueryKey, str]] = set()

    def pair(self, st: FinalState) -> Pair:
        key = state_key(st, self.settings)
        if key not in self.pairs:
            p = pair_for_state(self.ctx, st, key, f"pair{len(self.pairs)}")
            self.res.sessions += 2
            if not (p.baseline.settled and p.control.settled):  # load can stall a fresh pair: retry it once
                self.res.unsettled += int(not p.baseline.settled) + int(not p.control.settled)
                p = pair_for_state(self.ctx, st, key, f"pair{len(self.pairs)}-retry")
                self.res.sessions += 2
            self.res.unsettled += int(not p.baseline.settled) + int(not p.control.settled)
            for k in p.baseline.results:
                if k not in p.stable:
                    self.res.unstable[k.method] = self.res.unstable.get(k.method, 0) + 1
            if key:
                self.res.notes.append(f"extra reference pair for a non-round-trip final state: {key[:200]}")
            self.pairs[key] = p
        return self.pairs[key]

    def check(self, snap: Snapshot, ops: Sequence[Op], h: History, index: int, step: int,
              families: Sequence[str] = ()) -> None:
        pair = self.pair(final_state(self.ctx.project_dir, ops))
        if not pair.stable:  # nothing comparable for this step: record the coverage loss
            self.res.notes.append(f"no stable keys: {h.family} history {index} step {step} (seed {self.ctx.seed})")
        for k in pair.stable:
            self.res.compared[k.method] = self.res.compared.get(k.method, 0) + 1
        for key, exp, act in compare(pair.baseline, snap, pair.stable):
            shape = difference_shape(key.method, exp, act)
            if step and (key, shape) in self.seen:
                continue  # chain: the same difference is already recorded at an earlier step
            self.seen.add((key, shape))
            case = {"family": h.family, "timing": self.ctx.timing, "mode": "chain" if step else "fresh",
                    "chain_step": step, "seed": self.ctx.seed, "history_seed": h.seed, "history_index": index,
                    "note": h.note[:600], "families": list(families)}
            self.res.candidates.append(make_violation(self.ctx, ORACLE, key, exp, act, ops, case,
                                                      note=f"{h.family}: {h.note[:200]}"))

    def each(self, histories: Sequence[History]) -> None:
        for i, h in enumerate(histories):
            snap, info = safe_session(self.ctx, f"h{i:02d}-{h.family}", h.ops + guard_ops(self.ctx, h.ops))
            self.res.sessions += 1
            self.res.cases += 1
            if info.op_errors:
                self.res.invalid_cases += 1
                self.res.notes.append(f"h{i} {h.family} invalid: {info.op_errors[0][:200]}")
            elif not snap.settled:
                self.res.unsettled += 1
            else:
                self.check(snap, h.ops, h, i, 0)

    def chain(self, histories: Sequence[History]) -> None:
        ctx = self.ctx
        ops: List[Op] = list(histories[0].prelude) if histories else []
        prefix = list(ops)
        for h in histories:  # reference pairs first: never more than two sessions at a time
            prefix += list(h.body)
            self.pair(final_state(ctx.project_dir, prefix))
        try:
            with session(ctx, "chain") as d:
                self.res.sessions += 1
                if apply_history(ctx, d, ops):
                    self.res.invalid_cases += 1
                    return
                for k, h in enumerate(histories, start=1):
                    self.res.cases += 1
                    errors = apply_history(ctx, d, h.body)
                    if errors:
                        self.res.invalid_cases += 1
                        self.res.notes.append(f"chain step {k} {h.family} invalid, chain stopped: {errors[0][:200]}")
                        return
                    ops += list(h.body)
                    for g in guard_ops(ctx, h.body):
                        d.apply(g)
                    snap = d.snapshot(f"chain-{k}", list(ctx.targets))
                    if not snap.settled:
                        self.res.unsettled += 1
                        continue
                    self.check(snap, list(ops), h, k - 1, k, [x.family for x in histories[:k]])
        except SESSION_ERRORS as exc:
            self.res.notes.append(f"chain session failed: {type(exc).__name__}: {str(exc)[:200]}")


def workspace_for(ctx: OracleContext, settings: Dict[str, Any]) -> Workspace:
    positions = {t.path: tuple(t.positions) + tuple(t.ends) for t in ctx.targets}  # H8 asks where the suite asks
    return build_workspace(ctx.project_dir, [t.path for t in ctx.targets], ctx.language, ctx.server_kind, settings,
                           positions)


def histories_for(ctx: OracleContext, settings: Optional[Dict[str, Any]] = None) -> List[History]:
    """The histories run() executes for ctx (deterministic in ctx.seed and the project)."""
    ws = workspace_for(ctx, effective_settings(ctx) if settings is None else settings)
    return generate_many(ws, HistoryConfig(delay_ms=ctx.race_delay_ms or 0), ctx.seed, ctx.max_cases)


@register_oracle(ORACLE)
class R1History:
    name = ORACLE

    def __init__(self) -> None:
        self._probe_pairs: Optional[Dict[str, Pair]] = None  # set inside probe_scope()

    def applies_to(self, server_kind: str) -> bool:
        return True

    def run(self, ctx: OracleContext) -> OracleResult:
        t0 = time.monotonic()
        res = OracleResult(ORACLE, ctx.run_id)
        settings = effective_settings(ctx)
        histories = histories_for(ctx, settings)
        run = _Run(ctx, res, settings)
        chain = ctx.server_kind in CHAIN_KINDS
        res.notes.append(f"{'chain' if chain else 'fresh'} mode; histories: "
                         + ", ".join(f"{h.family}" for h in histories))
        try:
            if not run.pair(FinalState({}, None)).stable:
                res.notes.append("no stable keys: the baseline or the control did not settle")
            elif chain:
                run.chain(histories)
            else:
                run.each(histories)
        finally:
            res.seconds = round(time.monotonic() - t0, 3)
        return res

    @contextlib.contextmanager
    def probe_scope(self, ctx: OracleContext) -> Iterator[None]:
        """Replays inside the scope reuse the fresh pair of an identical final state (reduce.py);
        flake.confirm replays outside it, so its replays stay independent."""
        outer = self._probe_pairs
        self._probe_pairs = {} if outer is None else outer
        try:
            yield
        finally:
            self._probe_pairs = outer

    def replay(self, ctx: OracleContext, v: Any, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        t0 = time.monotonic()
        case = case_of(v)
        rctx = dataclasses.replace(ctx, timing=case.get("timing", ctx.timing))
        ops = list(v.ops if ops is None else ops)
        try:
            st = final_state(ctx.project_dir, ops)
        except OpError:
            return ReplayOutcome(False, False, False, None, round(time.monotonic() - t0, 3))
        key = state_key(st, effective_settings(ctx))
        cache = self._probe_pairs
        pair = cache.get(key) if cache is not None else None
        if pair is None:
            pair = pair_for_state(rctx, st, key, "replay")
            if cache is not None and pair.settled:
                cache[key] = pair
        snap, info = safe_session(rctx, "replay-history", ops + guard_ops(rctx, ops))
        secs = round(time.monotonic() - t0, 3)
        settled, stable = pair.settled and info.valid, v.key in pair.stable
        if not (settled and stable):
            return ReplayOutcome(settled, stable, False, None, secs)
        exp = pair.baseline.results[v.key].norm
        act = snap.results[v.key].norm if v.key in snap.results else MISSING
        if exp == act:
            return ReplayOutcome(True, True, False, None, secs)
        observed = make_violation(rctx, ORACLE, v.key, exp, act, ops, case, note="replay")
        return ReplayOutcome(True, True, difference_shape(v.key.method, exp, act) == shape_of(v), observed, secs)


__all__ = ["CHAIN_KINDS", "GUARDED_KINDS", "ORACLE", "Pair", "R1History", "effective_settings", "fresh_pair",
           "guard_ops", "histories_for", "pair_for_state", "safe_session", "state_key", "workspace_for"]
