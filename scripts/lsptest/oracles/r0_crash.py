"""R0 crash check (plan/tool_design_v1.md section 11.1).

run(): one fresh pair (baseline and control, side by side) per (server, project, seed); each
session opens the targets, settles and runs the whole query suite. A candidate is a key whose
answer is a crash-type error in BOTH sessions: an internal error (-32603), another JSON-RPC
server error (-32099..-32000), a dead server, a broken transport or a request timeout. Other
error answers are ordinary refusals and never candidates (gopls answers code 0 for "cannot find
type name", servers answer -32801 ContentModified or -32602 for stale requests). A server that
fails to initialize, or dies between initialize and the first query, in both sessions gives the
pseudo keys `initialize` / `session`. The snapshot's settled flag is ignored: a dead server
never settles, and that is exactly what R0 looks for.

Violation: expected = EXPECTED (no reference answer exists), actual = the baseline's error;
signature shape `<method>:result->error:<code>`; ops = []; case = {mode, codes, seed}.
replay(): another fresh pair; settled = the key was asked in both sessions; control_stable =
both sessions answered it identically; reproduced = that answer is a crash-type error with the
same shape. Not novel (fuzzers use it): it separates crash-type bugs from functional ones.

Run line: imported through oracles.load_all() by campaign_run.py, flake.py and reduce.py; not run directly.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .base import (OracleContext, OracleResult, ReplayOutcome, case_of, difference_shape, make_violation,
                   register_oracle, session, shape_of)
from framing import LspError  # noqa: E402  (lsp_repro is on sys.path once base is imported)
from model import Op, QueryKey, Snapshot, Violation  # noqa: E402

logger = logging.getLogger(__name__)

ORACLE = "r0_crash"
EXPECTED = "an answer that is not a server error, a crash or a timeout"
INTERNAL_ERROR = -32603
SERVER_ERROR_RANGE = (-32099, -32000)  # JSON-RPC: reserved for implementation-defined server errors
LIVENESS_MARKERS = ("dead", "timeout", "transport")
INIT_KEY = QueryKey("initialize", ".")
SESSION_KEY = QueryKey("session", ".", -1, -1, "open-settle")


@dataclass
class CrashSession:
    """One fresh session of R0: its snapshot and how far it got."""

    label: str
    snap: Snapshot
    phase: str  # start | open | done
    error: str = ""
    pseudo: Dict[QueryKey, Any] = field(default_factory=dict)  # INIT_KEY / SESSION_KEY answers
    seconds: float = 0.0


def crash_code(norm: Any) -> Optional[str]:
    """The crash-type error of a normalized answer (see the module docstring), else None."""
    if not (isinstance(norm, list) and len(norm) == 2 and norm[0] == "error"):
        return None
    code = norm[1]
    if isinstance(code, str):
        return code if code in LIVENESS_MARKERS else None
    if isinstance(code, int) and not isinstance(code, bool):
        lo, hi = SERVER_ERROR_RANGE
        return str(code) if code == INTERNAL_ERROR or lo <= code <= hi else None
    return None


def _start_error(exc: BaseException) -> List[Any]:
    """Normalized answer of a failed initialize: a timeout, the server's error code, or dead."""
    if isinstance(exc, LspError) and getattr(exc, "request_id", None) is not None:
        return ["error", "timeout"]
    code = getattr(exc, "code", None)
    return ["error", code if isinstance(code, int) else "dead"]


def crash_session(ctx: OracleContext, label: str) -> CrashSession:
    """Start, open the targets, settle and run the whole suite. A protocol failure of the server
    (LspError: initialize timed out, answered an error, or the server exited) becomes a pseudo-key
    answer; anything else (a missing server build, a workspace that cannot be cloned) raises."""
    t0, phase = time.monotonic(), "start"
    out = CrashSession(label, Snapshot(label, ctx.server, False), phase)
    try:
        with session(ctx, label) as d:
            out.phase = phase = "open"
            out.pseudo[INIT_KEY] = []
            out.snap = d.snapshot(label, list(ctx.targets))
            out.phase = "done"
            out.pseudo[SESSION_KEY] = []
    except LspError as exc:
        out.error = f"{type(exc).__name__}: {exc}"[:300]
        if phase == "start":
            out.pseudo[INIT_KEY] = _start_error(exc)
        else:
            out.pseudo[SESSION_KEY] = ["error", "dead"]
        logger.warning("%s: session %s failed in phase %s: %s", ORACLE, label, phase, out.error)
    out.seconds = round(time.monotonic() - t0, 3)
    return out


def crash_pair(ctx: OracleContext, label: str) -> Tuple[CrashSession, CrashSession]:
    """Fresh baseline and fresh control, side by side."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        fb = pool.submit(crash_session, ctx, f"{label}-baseline")
        fc = pool.submit(crash_session, ctx, f"{label}-control")
        return fb.result(), fc.result()


def answer(s: CrashSession, key: QueryKey) -> Tuple[bool, Any]:
    """(asked, normalized answer) of a key in one session; pseudo keys included."""
    if key in s.pseudo:
        return True, s.pseudo[key]
    r = s.snap.results.get(key)
    return (False, None) if r is None else (True, r.norm)


def all_keys(a: CrashSession, b: CrashSession) -> List[QueryKey]:
    keys = set(a.snap.results) | set(b.snap.results) | set(a.pseudo) | set(b.pseudo)
    return sorted(keys, key=lambda q: (q.method, q.path, q.line, q.character, q.extra))


def error_census(s: CrashSession) -> Dict[str, Dict[str, int]]:
    """Per method: error codes answered in one session (crash-type or not)."""
    out: Dict[str, Dict[str, int]] = {}
    for k, r in s.snap.results.items():
        if r.error is not None:
            row = out.setdefault(k.method, {})
            row[str(r.error[1])] = row.get(str(r.error[1]), 0) + 1
    return out


@register_oracle(ORACLE)
class CrashCheck:
    name = ORACLE

    def applies_to(self, server_kind: str) -> bool:
        return bool(server_kind)

    def run(self, ctx: OracleContext) -> OracleResult:
        t0, res = time.monotonic(), OracleResult(ORACLE, ctx.run_id)
        b, c = crash_pair(ctx, "r0")
        res.sessions, res.cases = 2, 1
        res.unsettled = int(not b.snap.settled) + int(not c.snap.settled)
        for k in all_keys(b, c):
            (ab, nb), (ac, nc) = answer(b, k), answer(c, k)
            if not (ab and ac):
                continue
            res.compared[k.method] = res.compared.get(k.method, 0) + 1
            cb, cc = crash_code(nb), crash_code(nc)
            if (cb is None) != (cc is None):
                res.unstable[k.method] = res.unstable.get(k.method, 0) + 1
                res.notes.append(f"crash in one session only: {k.method} {k.path}:{k.line}:{k.character} "
                                 f"baseline {nb!r} control {nc!r}"[:300])
            elif cb is not None:
                case = {"mode": "fresh-pair", "codes": [cb, cc], "seed": ctx.seed,
                        "phase": [b.phase, c.phase]}
                note = f"{k.method} answered {nb!r} in the fresh baseline and {nc!r} in the fresh control"
                res.candidates.append(make_violation(ctx, ORACLE, k, EXPECTED, nb, [], case, note))
        for s in (b, c):
            res.notes.append(f"{s.label}: phase {s.phase}, settled {s.snap.settled}, {len(s.snap.results)} keys, "
                             f"{s.seconds:.1f}s{', ' + s.error if s.error else ''}; errors {error_census(s)}"[:600])
        res.seconds = round(time.monotonic() - t0, 3)
        return res

    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        t0 = time.monotonic()
        b, c = crash_pair(ctx, "r0-replay")
        (ab, nb), (ac, nc) = answer(b, v.key), answer(c, v.key)
        asked, same = ab and ac, ab and ac and nb == nc
        crash = crash_code(nb) is not None
        observed = make_violation(ctx, ORACLE, v.key, EXPECTED, nb, [], case_of(v), "replay") if ab and crash else None
        reproduced = same and crash and difference_shape(v.key.method, EXPECTED, nb) == shape_of(v)
        return ReplayOutcome(asked, same, reproduced, observed, round(time.monotonic() - t0, 3))


__all__ = ["CrashCheck", "CrashSession", "EXPECTED", "INIT_KEY", "LIVENESS_MARKERS", "ORACLE", "SESSION_KEY",
           "all_keys", "answer", "crash_code", "crash_pair", "crash_session", "error_census"]
