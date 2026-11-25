"""Reduction of a group's representative (plan/tool_design_v1.md sections 6 and 11.2).

narrow_targets(): one replay with the key's position as the only query target (other target
files stay open, with file-level queries only); when it reproduces, the reduction and the
report use that context (fewer queries per probe, fewer steps for a maintainer).
reduce_group(): reduce.reduce_and_confirm over the ops under the group's budget; the reduced
ops are used only when they reproduced 3/3 again.
reduce_lines() (optional): ddmin over the lines of the touched files (the files the ops edit or
open, and the key's file). A line is dropped by blanking it, keeping its line break, so every
position in the ops, the key and the targets stays valid; lines that the ops or the key refer
to are pinned (followed through the edits of the ops), and files written or renamed on disk by
the ops are left alone. Each probe materializes the project with the blanked files (base.
materialize) and replays once; the result is confirmed 3/3 again, else discarded. Only for
oracles whose positions are all in the ops and the key (LINE_ORACLES). With keep_syntax, a
reduction that gives the file a parse error the original lacks (oracles/syntax.py) is rejected
offline, so reports show valid code.

Run line: imported by triage.py and tests/test_triage.py; not run directly.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import flake  # noqa: E402
from model import Op, QueryKey, Violation  # noqa: E402
from oracles.base import FinalState, OracleContext, discard, final_state, materialize  # noqa: E402
from oracles.r3_routes import key_targets  # noqa: E402
from oracles.syntax import SyntaxToolError, new_errors, supported, syntax_errors  # noqa: E402
from ops import LineIndex, OpError, read_text  # noqa: E402
from reduce import Budget, Prober, ReduceConfig, ReduceResult, ddmin_indices, reduce_and_confirm  # noqa: E402

logger = logging.getLogger(__name__)
LINE_ORACLES = frozenset({"r0_crash", "r1_history", "r5_transforms", "r6_crossimpl"})


@dataclass(frozen=True)
class LineConfig:
    max_probes: int = 40
    max_seconds: float = 3600.0
    max_lines: int = 400  # longer files are skipped (ddmin would need too many probes)
    keep_syntax: bool = True  # reject (offline) reductions with a parse error the original file lacks


@dataclass
class LineResult:
    files: Dict[str, str] = field(default_factory=dict)  # path -> blanked text (only when confirmed)
    lines: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # path -> (non-blank lines kept, before)
    probes: int = 0
    seconds: float = 0.0
    exhausted: bool = False
    confirmed: str = ""  # k/n of the final confirmation
    skipped: List[str] = field(default_factory=list)


# ------------------------------------------------------------------ pure helpers
def line_texts(text: str) -> List[str]:
    """The lines of `text` with their line breaks (as LineIndex counts lines)."""
    idx = LineIndex(text)
    ends = list(idx.starts[1:]) + [len(text)]
    return [text[s:e] for s, e in zip(idx.starts, ends)]


def blank_lines(text: str, keep: Set[int]) -> str:
    """Every line not in `keep` emptied, its line break kept."""
    out = []
    for i, line in enumerate(line_texts(text)):
        body = line.rstrip("\r\n")
        out.append(line if i in keep else line[len(body):])
    return "".join(out)


def pinned_lines(path: str, text: str, ops: Sequence[Op], key: Optional[QueryKey]) -> Optional[Set[int]]:
    """Original lines of `path` that a change, a request or the key refers to, followed through the
    ops' edits (a change of k line breaks over lines sl..el keeps the origins of sl and el).
    None when the ops write or rename the file on disk (it cannot be reduced)."""
    disk: List[Optional[int]] = list(range(len(line_texts(text)) or 1))
    buf: Optional[List[Optional[int]]] = None
    pins: Set[int] = set()

    def pin(rows: Optional[List[Optional[int]]], line: int) -> None:
        if rows is not None and 0 <= line < len(rows) and rows[line] is not None:
            pins.add(rows[line])  # type: ignore[arg-type]

    for op in ops:
        if path not in (op.path, op.new_path):
            continue
        if op.kind in ("fs_write", "fs_rename"):
            return None
        if op.kind == "open":
            buf = list(disk)
        elif op.kind == "close":
            buf = None
        elif op.kind == "save" and buf is not None:
            disk = list(buf)
        elif op.kind == "request" and op.start is not None:
            pin(buf, op.start[0])
        elif op.kind == "change" and buf is not None and op.start is not None and op.end is not None:
            sl, el = op.start[0], op.end[0]
            for line in range(sl, el + 1):
                pin(buf, line)
            k = op.text.count("\n") + op.text.replace("\r\n", "").count("\r")
            first = buf[sl] if sl < len(buf) else None
            last = buf[el] if el < len(buf) else None
            buf[sl:el + 1] = [first] if k == 0 else [first] + [None] * (k - 1) + [last]
    if key is not None and key.path == path and key.line >= 0:
        pin(buf if buf is not None else disk, key.line)
    return pins


def touched_files(ops: Sequence[Op], key: Optional[QueryKey]) -> List[str]:
    """Files the ops open or edit, and the key's file, in first-use order."""
    out: List[str] = []
    for p in [o.path for o in ops if o.kind in ("open", "change", "save", "request")] + ([key.path] if key else []):
        if p and p != "." and p not in out:
            out.append(p)
    return out


# ------------------------------------------------------------------ with replays
def narrow_targets(oracle: Any, ctx: OracleContext, v: Violation) -> Tuple[OracleContext, bool]:
    """(context, narrowed): the key-only targets when one replay reproduces with them."""
    small = key_targets(ctx.targets, v.key)
    if small == ctx.targets:
        return ctx, False
    nctx = dataclasses.replace(ctx, targets=small)
    ok = flake.counts(oracle.replay(nctx, v))
    logger.info("key-only targets %s for %s", "reproduce" if ok else "do not reproduce", v.signature)
    return (nctx, True) if ok else (ctx, False)


def reduce_group(oracle: Any, ctx: OracleContext, v: Violation, cfg: ReduceConfig) -> Tuple[List[Op], ReduceResult, str]:
    """(ops to report, the reduction, k/n of the reduced ops' confirmation)."""
    v2, res, conf = reduce_and_confirm(oracle, ctx, v, cfg)
    return (list(v2.reduced_ops) if v2.reduced_ops or not v.ops else list(v.ops)), res, conf.reproduced


def syntax_guard(language: str, path: str, text: str) -> Optional[Callable[[str], bool]]:
    """A check that a reduced text has no parse error the original lacks (oracles/syntax.py);
    None when the language has no classifier or its parser cannot run."""
    if not supported(language):
        return None
    try:
        before = syntax_errors(language, text, path)
    except SyntaxToolError:
        return None

    def ok(reduced: str) -> bool:
        try:
            return not new_errors(before, syntax_errors(language, reduced, path))
        except SyntaxToolError:
            return True
    return ok


def _probe_project(ctx: OracleContext, files: Dict[str, str]) -> str:
    return materialize(ctx, FinalState(dict(files), None), f"lines-{uuid.uuid4().hex[:8]}")


def replay_with_files(oracle: Any, ctx: OracleContext, v: Violation, files: Dict[str, str]) -> bool:
    """One replay on the project with `files` replaced; False when an op no longer applies."""
    root = _probe_project(ctx, files)
    try:
        try:
            final_state(root, v.ops)
        except OpError:
            return False
        return flake.counts(oracle.replay(dataclasses.replace(ctx, project_dir=root), v, list(v.ops)))
    finally:
        discard(root)


def reduce_lines(oracle: Any, ctx: OracleContext, v: Violation, cfg: LineConfig = LineConfig(),
                 clock: Callable[[], float] = time.monotonic) -> LineResult:
    """Line-level ddmin of the touched files (see the module docstring)."""
    out, budget = LineResult(), Budget(cfg.max_probes, cfg.max_seconds, clock)
    if v.oracle not in LINE_ORACLES:
        out.skipped.append(f"{v.oracle}: case positions are not in the ops and the key")
        return out
    files: Dict[str, str] = {}
    for path in touched_files(v.ops, v.key):
        full = os.path.join(ctx.project_dir, path)
        try:
            text = read_text(full)
        except OSError:
            out.skipped.append(f"{path}: not a project file")
            continue
        lines = line_texts(text)
        pins = pinned_lines(path, text, v.ops, v.key)
        if pins is None or len(lines) > cfg.max_lines:
            out.skipped.append(f"{path}: {'written or renamed by the ops' if pins is None else f'{len(lines)} lines'}")
            continue
        free = [i for i, ln in enumerate(lines) if i not in pins and ln.strip()]
        guard = syntax_guard(ctx.language, full, text) if cfg.keep_syntax else None

        def reduced(idx: List[int], text: str = text, pins: Set[int] = pins, free: List[int] = free) -> str:
            return blank_lines(text, pins | {free[i] for i in idx})

        def test(idx: List[int], path: str = path, reduced: Callable[[List[int]], str] = reduced) -> bool:
            return replay_with_files(oracle, ctx, v, dict(files, **{path: reduced(idx)}))

        pre = (lambda idx, guard=guard, reduced=reduced: guard(reduced(idx))) if guard else None
        prober = Prober(test, budget, pre)
        kept = ddmin_indices(len(free), prober, budget) if free else []
        if free and len(kept) == len(free) and not prober(list(range(len(free)))):
            out.skipped.append(f"{path}: blanking nothing does not reproduce")
            continue
        files[path] = blank_lines(text, pins | {free[i] for i in kept})
        out.lines[path] = (sum(1 for ln in line_texts(files[path]) if ln.strip()), sum(1 for ln in lines if ln.strip()))
    out.exhausted, out.probes = budget.exhausted(), budget.probes
    if files and any(files[p] != read_text(os.path.join(ctx.project_dir, p)) for p in files):
        root = _probe_project(ctx, files)
        try:
            conf = flake.confirm(oracle, dataclasses.replace(ctx, project_dir=root), v)
        finally:
            discard(root)
        out.confirmed = conf.reproduced
        out.files = files if flake.is_confirmed(conf) else {}
    out.seconds = round(budget.elapsed(), 1)
    return out


__all__ = ["LINE_ORACLES", "LineConfig", "LineResult", "blank_lines", "line_texts", "narrow_targets",
           "pinned_lines", "reduce_group", "reduce_lines", "replay_with_files", "syntax_guard", "touched_files"]
