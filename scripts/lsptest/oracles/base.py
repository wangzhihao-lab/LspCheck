"""Oracle layer contract and shared helpers (plan/tool_design_v1.md sections 5, 6, 10).

Fixed contract: OracleContext, OracleResult, ReplayOutcome, FinalState, the Oracle
protocol, the ORACLES registry and the signatures of the helpers below. Oracle modules
(r1_history.py ... r6_crossimpl.py) implement and register oracles and may add helpers
of their own, but must not change these fields or signatures.

Every oracle is ground-truth free: it compares two answers that must agree by
construction (two routes to the same content, an old and a fresh handle for the same
action, ...). A candidate violation is a *stable* key (equal in a fresh baseline and a
fresh control) whose two answers differ; flake.py re-runs it from scratch and keeps it
only on 3/3 reproduction. Violation.detail holds JSON {"case", "shape", "note"}: `case`
is whatever the oracle needs to replay it, `shape` the difference shape of the signature.

Run line: imported by the oracle modules, flake.py, reduce.py and campaign.py; not run directly.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Set, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (PKG, os.path.join(os.path.dirname(PKG), "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from driver import RUNS_DIR, SESSION_SETTINGS, Driver, DriverConfig, clone_tree  # noqa: E402
from model import Op, QueryKey, Snapshot, Violation  # noqa: E402
from ops import OpError, apply_change, deep_merge, read_text, write_text  # noqa: E402
from queries import QueryConfig  # noqa: E402
from targets import FileTargets  # noqa: E402

logger = logging.getLogger(__name__)

TIMINGS: Dict[str, Optional[int]] = {"settled": None, "race0": 0, "race50": 50, "race200": 200}
LIVENESS_ERRORS = ("timeout", "dead")  # a key lost this way in a fresh session is not comparable
MISSING = ["missing-key"]  # norm used when the compared snapshot lacks a key
SCALAR_METHODS = ("hover", "signatureHelp")


# ------------------------------------------------------------------ contract
@dataclass(frozen=True)
class OracleContext:
    """Everything one oracle run needs; campaign.py builds it from a model.RunConfig."""

    run_id: str
    server_kind: str
    server_version: str
    project: str  # "<owner>/<repo>@<sha12>" or a benchmark case id
    project_dir: str  # prepared project; never modified
    language: str  # python | typescript | rust | go | java
    seed: int
    targets: Tuple[FileTargets, ...]
    timing: str = "settled"  # a key of TIMINGS
    settle_timeout_s: float = 300.0
    request_timeout_s: float = 30.0
    extra_settings: Optional[Mapping[str, Any]] = None  # None: driver.SESSION_SETTINGS for the kind
    max_cases: int = 12  # histories / handles / transformations ... per run
    work_dir: str = ""  # per-run scratch (materialized projects, session logs); "" -> RUNS_DIR/<run_id>-work
    pull_diagnostics: Optional[bool] = None  # default diagnostics route of every session (None: server default)

    @property
    def server(self) -> str:
        return f"{self.server_kind}-{self.server_version}"

    @property
    def race_delay_ms(self) -> Optional[int]:
        """None in the settled mode, else the delay every op of a history carries."""
        return TIMINGS[self.timing]

    def scratch(self) -> str:
        return self.work_dir or os.path.join(RUNS_DIR, f"{self.run_id}-work")


@dataclass
class OracleResult:
    oracle: str
    run_id: str
    candidates: List[Violation] = field(default_factory=list)  # before flake.py confirmation
    cases: int = 0  # cases executed (histories, handles, transformations, route pairs ...)
    invalid_cases: int = 0  # cases whose ops could not be applied
    sessions: int = 0  # server sessions started
    unsettled: int = 0  # snapshots discarded because the server did not settle
    compared: Dict[str, int] = field(default_factory=dict)  # per method: stable keys compared
    unstable: Dict[str, int] = field(default_factory=dict)  # per method: keys excluded (baseline != control)
    seconds: float = 0.0
    notes: List[str] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        d = {k: v for k, v in asdict(self).items() if k != "candidates"}
        d["candidates"] = [json.loads(v.to_json()) for v in self.candidates]
        return d


@dataclass
class ReplayOutcome:
    settled: bool  # every session of the replay settled and every op applied
    control_stable: bool  # the key was equal in the replay's fresh baseline and fresh control
    reproduced: bool  # the key differs again with the same difference shape
    observed: Optional[Violation] = None
    seconds: float = 0.0


class Oracle(Protocol):
    name: str

    def applies_to(self, server_kind: str) -> bool:
        """Whether the oracle can run on this server kind (e.g. r6 only on ts6/ts7)."""

    def run(self, ctx: OracleContext) -> OracleResult:
        """Generate up to ctx.max_cases cases, execute them, return candidate violations."""

    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        """Re-execute the case of `v` with fresh sessions only (`ops` replaces v.ops when given;
        reduce.py passes subsets) and report whether v.key shows the same difference shape."""


ORACLES: Dict[str, Oracle] = {}


def register_oracle(name: str) -> Callable[[type], type]:
    """Class decorator: instantiate with no arguments and register under `name`."""
    def deco(cls: type) -> type:
        inst = cls()
        inst.name = name
        ORACLES[name] = inst
        return cls
    return deco


# ------------------------------------------------------------------ sessions
@dataclass
class SessionInfo:
    label: str
    valid: bool  # settled and every op applied
    settled: bool
    op_errors: List[str]
    seconds: float
    stats: Dict[str, Any] = field(default_factory=dict)


def driver_config(ctx: OracleContext, label: str, project_dir: Optional[str] = None, pull: Optional[bool] = None,
                  settings_overlay: Optional[Mapping[str, Any]] = None) -> DriverConfig:
    base = SESSION_SETTINGS.get(ctx.server_kind, {}) if ctx.extra_settings is None else ctx.extra_settings
    settings = deep_merge(dict(base), dict(settings_overlay or {}))
    return DriverConfig(ctx.server_kind, ctx.server_version, project_dir or ctx.project_dir,
                        label=f"{ctx.run_id}-{label}", settle_timeout_s=ctx.settle_timeout_s,
                        request_timeout_s=ctx.request_timeout_s,
                        pull_diagnostics=ctx.pull_diagnostics if pull is None else pull, extra_settings=settings,
                        logs_dir=os.path.join(ctx.scratch(), "logs"))


def session(ctx: OracleContext, label: str, project_dir: Optional[str] = None, pull: Optional[bool] = None,
            settings_overlay: Optional[Mapping[str, Any]] = None) -> Driver:
    """A Driver for ctx; `with session(ctx, "baseline") as d:` starts and always closes it."""
    return Driver(driver_config(ctx, label, project_dir, pull, settings_overlay))


def apply_history(ctx: OracleContext, d: Driver, ops: Sequence[Op]) -> List[str]:
    """Apply ops in ctx.timing (settled: settle after every op; race: each op's own delay_ms).
    Stops at the first op that cannot be applied; returns the error messages (empty = all applied)."""
    for op in ops:
        try:
            out = d.apply(op)
        except OpError as exc:
            return [f"{op.kind} {op.path}: {exc}"]
        if out.error:
            return [f"{op.kind} {op.path}: {out.error}"]
        if ctx.race_delay_ms is None and op.kind != "wait":
            d.settle()
    return []


def run_session(ctx: OracleContext, label: str, ops: Sequence[Op] = (), project_dir: Optional[str] = None,
                pull: Optional[bool] = None, settings_overlay: Optional[Mapping[str, Any]] = None,
                targets: Optional[Sequence[FileTargets]] = None,
                qcfg: Optional[QueryConfig] = None) -> Tuple[Snapshot, SessionInfo]:
    """One fresh session: start, apply ops, snapshot the targets (default ctx.targets), close."""
    t0 = time.monotonic()
    with session(ctx, label, project_dir, pull, settings_overlay) as d:
        errors = apply_history(ctx, d, ops)
        snap = d.snapshot(label, list(targets or ctx.targets), qcfg) if not errors else Snapshot(label, ctx.server, False)
        stats = d.last_stats.to_json() if not errors and d.last_stats is not None else {}
    info = SessionInfo(label, snap.settled and not errors, snap.settled, errors, round(time.monotonic() - t0, 3), stats)
    return snap, info


def fresh_pair(ctx: OracleContext, label: str, project_dir: Optional[str] = None, pull: Optional[bool] = None,
               settings_overlay: Optional[Mapping[str, Any]] = None
               ) -> Tuple[Snapshot, Snapshot, Set[QueryKey]]:
    """Fresh baseline and fresh control on the same content; returns both and the stable keys."""
    b, _ = run_session(ctx, f"{label}-baseline", (), project_dir, pull, settings_overlay)
    c, _ = run_session(ctx, f"{label}-control", (), project_dir, pull, settings_overlay)
    return b, c, stable_keys(b, c)


# ---------------------------------------------------------------- comparison
def _liveness_lost(snap: Snapshot, key: QueryKey) -> bool:
    r = snap.results.get(key)
    return r is not None and r.error is not None and r.error[1] in LIVENESS_ERRORS


def stable_keys(baseline: Snapshot, control: Snapshot) -> Set[QueryKey]:
    """Keys answered in both settled fresh snapshots, equal, and not lost to a timeout or dead server."""
    if not (baseline.settled and control.settled):
        return set()
    return {k for k, r in baseline.results.items()
            if k in control.results and r.norm == control.results[k].norm
            and not _liveness_lost(baseline, k) and not _liveness_lost(control, k)}


def compare(expected: Snapshot, actual: Snapshot, keys: Iterable[QueryKey]) -> List[Tuple[QueryKey, Any, Any]]:
    """(key, expected norm, actual norm) for every key in `keys` whose answers differ; a key the
    actual snapshot lacks is reported with MISSING. Timeouts in `actual` are kept (shape error:timeout)."""
    out = []
    for k in sorted(keys, key=lambda q: (q.method, q.path, q.line, q.character, q.extra)):
        e = expected.results[k].norm
        a = actual.results[k].norm if k in actual.results else MISSING
        if e != a:
            out.append((k, e, a))
    return out


def _error_code(x: Any) -> Optional[str]:
    return str(x[1]) if isinstance(x, list) and len(x) == 2 and x[0] == "error" else None


def _empty(method: str, x: Any) -> bool:
    if x is None or x == [] or x == "":
        return True
    return method == "hover" and isinstance(x, list) and not (x[0] if x else None)


def _items(x: Any) -> Set[str]:
    return {json.dumps(i, sort_keys=True) for i in x} if isinstance(x, list) else set()


def _diag_shape(expected: List[Any], actual: List[Any], kind: str) -> str:
    """Diagnostics: codes of the differing items; `moved` when only ranges differ, `message` when only texts do."""
    e, a = _items(expected), _items(actual)
    codes = sorted({str(json.loads(i)[5]) or "?" for i in (e ^ a)})[:3]
    if kind == "changed":
        if sorted(d[4:] for d in expected) == sorted(d[4:] for d in actual):
            kind = "moved"
        elif sorted(d[:7] for d in expected) == sorted(d[:7] for d in actual):
            kind = "message"
    return f"diagnostics:{kind}:{','.join(codes)}"


def difference_shape(method: str, expected: Any, actual: Any) -> str:
    """Short, stable description of how two normalized answers differ (used in signatures)."""
    ee, ae = _error_code(expected), _error_code(actual)
    if actual == MISSING:
        return f"{method}:key-lost"
    if ee is not None or ae is not None:
        return f"{method}:{'error:' + ee if ee else 'result'}->{'error:' + ae if ae else 'result'}"
    lists = isinstance(expected, list) and isinstance(actual, list)
    if method == "diagnostics" and lists:
        missing, extra = _items(expected) - _items(actual), _items(actual) - _items(expected)
        kind = "missing" if missing and not extra else "extra" if extra and not missing else "changed"
        return _diag_shape(expected, actual, kind)
    if _empty(method, expected) != _empty(method, actual):
        return f"{method}:{'gained' if _empty(method, expected) else 'lost'}"
    if method == "hover" and lists:
        return "hover:text" if expected[:1] != actual[:1] else "hover:range"
    if method in SCALAR_METHODS or not lists:
        return f"{method}:changed"
    missing, extra = _items(expected) - _items(actual), _items(actual) - _items(expected)
    kind = "missing" if missing and not extra else "extra" if extra and not missing else "changed"
    return f"{method}:{kind}"


def signature(server_kind: str, oracle: str, shape: str) -> str:
    return f"{server_kind}|{oracle}|{shape}"


def make_violation(ctx: OracleContext, oracle: str, key: QueryKey, expected: Any, actual: Any,
                   ops: Sequence[Op], case: Mapping[str, Any], note: str = "") -> Violation:
    shape = difference_shape(key.method, expected, actual)
    detail = json.dumps({"case": dict(case), "shape": shape, "note": note}, sort_keys=True, default=str)
    return Violation(oracle, ctx.server, ctx.project, key, expected, actual, ops=list(ops), detail=detail,
                     signature=signature(ctx.server_kind, oracle, shape), run_id=ctx.run_id)


def case_of(v: Violation) -> Dict[str, Any]:
    return json.loads(v.detail).get("case", {}) if v.detail else {}


def shape_of(v: Violation) -> str:
    return json.loads(v.detail).get("shape", "") if v.detail else ""


# ------------------------------------------------------- content after a history
@dataclass
class FinalState:
    files: Dict[str, Optional[str]]  # workspace-relative path -> final text (None: deleted); changed paths only
    settings: Optional[Dict[str, Any]]  # accumulated set_config overlay (None: never changed)

    def empty(self) -> bool:
        return not self.files and self.settings is None


def final_state(project_dir: str, ops: Sequence[Op]) -> FinalState:
    """Offline replay of what `ops` leave behind: the content a fresh session must see to be
    comparable with a session that executed them. Unsaved open buffers count as content (the
    fresh session gets them on disk). Raises OpError when an op cannot apply."""
    def original(p: str) -> Optional[str]:
        try:
            return read_text(os.path.join(project_dir, p))
        except OSError:
            return None

    disk: Dict[str, Optional[str]] = {}
    buf: Dict[str, str] = {}
    settings: Optional[Dict[str, Any]] = None
    now = lambda p: disk[p] if p in disk else original(p)  # noqa: E731
    for op in ops:
        if op.kind == "open":
            if op.path in buf or now(op.path) is None:
                raise OpError(f"cannot open {op.path}")
            buf[op.path] = now(op.path) or ""
        elif op.kind == "change":
            if op.path not in buf or op.start is None or op.end is None:
                raise OpError(f"change on a closed document {op.path}")
            buf[op.path] = apply_change(buf[op.path], op.start, op.end, op.text)[0]
        elif op.kind == "close":
            buf.pop(op.path, None)
        elif op.kind == "save":
            if op.path not in buf:
                raise OpError(f"save of a closed document {op.path}")
            disk[op.path] = buf[op.path]
        elif op.kind == "fs_write":
            disk[op.path] = op.text
        elif op.kind == "fs_rename":
            disk[op.new_path], disk[op.path] = now(op.path), None
            if op.path in buf:
                buf[op.new_path] = buf.pop(op.path)
        elif op.kind == "set_config":
            settings = deep_merge(settings or {}, op.settings or {})
    files = dict(disk)
    files.update(buf)
    return FinalState({p: t for p, t in files.items() if t != original(p)}, settings)


def materialize(ctx: OracleContext, state: FinalState, tag: str) -> str:
    """APFS clone of ctx.project_dir under ctx.scratch()/tag with state.files applied; the caller
    removes it with discard(). Settings are not files: pass state.settings as settings_overlay."""
    dst = os.path.join(ctx.scratch(), "materialized", tag)
    discard(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    clone_tree(ctx.project_dir, dst)
    for rel, text in state.files.items():
        path = os.path.join(dst, rel)
        if text is None:
            if os.path.exists(path):
                os.remove(path)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write_text(path, text)
    return dst


def discard(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)


__all__ = [
    "FinalState", "LIVENESS_ERRORS", "MISSING", "ORACLES", "Oracle", "OracleContext", "OracleResult",
    "ReplayOutcome", "SessionInfo", "TIMINGS", "apply_history", "case_of", "compare", "difference_shape",
    "discard", "driver_config", "final_state", "fresh_pair", "make_violation", "materialize",
    "register_oracle", "run_session", "session", "shape_of", "signature", "stable_keys",
]
