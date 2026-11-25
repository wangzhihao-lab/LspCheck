"""Seeded generators of R1 edit histories (plan/tool_design_v1.md sections 5 and 10).

A History is a list of model.Op: a prelude that opens the query targets, then a body that
ends at the original content with the same documents open (a round trip), so a session
that executed it must answer like a fresh session on the project. Families, registered in
HISTORY_FAMILIES:
  H1 edit then inverse (insert / delete span / replace token);
  H2 delete a line, then retype it in k chunks (k in HistoryConfig.chunk_counts);
  H3 close and reopen, also after an unsaved edit (the edit is discarded);
  H4 configuration toggle A->B->A (history_sites.SETTING_TOGGLES; A = the effective value);
  H5 file rename round trip (fs_rename a -> a2 -> a);
  H6 edit of a depended-on non-target file then revert (in the editor or on disk), or a
     configuration-file round trip (one line deleted or duplicated, then the original back);
  H7 interleaving of H1-H6, H8, H9 on 2-3 distinct files (order-preserving shuffle, or one
     round trip nested inside another); requests follow the code through interleaved edits;
  H8 query order: request ops (no edits) at the target positions and other identifier
     positions in a shuffled order, half of the time right after an edit round trip;
  H9 edit inside a workspace window (added after known-bug validation run 1): a workspace
     change W (config-file variant; depended-on file edited on disk or in the editor, or a
     file renamed) is kept while every open target W does not touch is changed and restored
     (edit + inverse, delete + retype, close + reopen), then W is reverted.
Edit sites are weighted towards high fan-out lines (history_sites: imports, top-level
declarations). Every op carries HistoryConfig.delay_ms (0 in the settled timing, the race
delay otherwise). Nothing here is specific to a project, a server bug or a benchmark case.

Run line: imported by oracles/r1_history.py and tests/test_histories.py; not run directly.
"""

from __future__ import annotations

import logging
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from history_sites import (  # noqa: E402
    SETTING_TOGGLES, HistoryConfig, config_files, config_variant, dependency_files, edit_op, fix_requests, get_path,
    nested, pick_line, retype_ops, there_and_back, warmup_ops,
)
from model import Op, Pos  # noqa: E402
from ops import OpError, apply_change, deep_merge, read_text  # noqa: E402

logger = logging.getLogger(__name__)

SETTINGS_RESOURCE = "<settings>"
FAMILY_ORDER = ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9")
PART_FAMILIES = ("H1", "H2", "H3", "H4", "H5", "H6", "H8", "H9")  # what H7 interleaves
FAMILY_DESCRIPTIONS: Dict[str, str] = {
    "H1": "edit then inverse", "H2": "delete a line, retype it in k chunks", "H3": "close and reopen",
    "H4": "configuration toggle A->B->A", "H5": "file rename round trip", "H6": "depended-on file round trip",
    "H7": "interleaving of H1-H6, H8, H9", "H8": "query order", "H9": "edit inside a workspace window"}


@dataclass(frozen=True)
class Body:
    ops: Tuple[Op, ...]
    resources: Tuple[str, ...]  # files (or SETTINGS_RESOURCE) the body touches
    note: str = ""


@dataclass(frozen=True)
class History:
    family: str
    seed: int
    prelude: Tuple[Op, ...]  # opens the targets
    body: Tuple[Op, ...]
    resources: Tuple[str, ...] = ()
    note: str = ""

    @property
    def ops(self) -> List[Op]:
        return list(self.prelude) + list(self.body)


@dataclass
class Workspace:
    """What the generators see of a prepared project (read-only)."""

    root: str
    language: str
    server_kind: str
    targets: Tuple[str, ...]
    deps: Tuple[str, ...] = ()  # depended-on non-target sources
    configs: Tuple[str, ...] = ()  # configuration files present
    settings: Mapping[str, Any] = field(default_factory=dict)  # effective server settings
    positions: Mapping[str, Sequence[Pos]] = field(default_factory=dict)  # query positions per target file
    texts: Dict[str, Optional[str]] = field(default_factory=dict, repr=False)

    def text(self, path: str) -> Optional[str]:
        if path not in self.texts:
            try:
                self.texts[path] = read_text(os.path.join(self.root, path))
            except OSError:
                self.texts[path] = None
        return self.texts[path]

    def exists(self, path: str) -> bool:
        return os.path.exists(os.path.join(self.root, path))


def build_workspace(root: str, targets: Sequence[str], language: str, server_kind: str,
                    settings: Optional[Mapping[str, Any]] = None,
                    positions: Optional[Mapping[str, Sequence[Pos]]] = None) -> Workspace:
    tgt = tuple(sorted(targets))
    return Workspace(root, language, server_kind, tgt, dependency_files(root, tgt, language),
                     config_files(root, tgt, language), dict(settings or {}), dict(positions or {}))


def round_trip(state: Any, settings: Mapping[str, Any]) -> bool:
    """A base.FinalState equal to the start: no file changed, every setting at its effective value."""
    base = dict(settings)
    return not state.files and (state.settings is None or deep_merge(base, state.settings) == base)


# ------------------------------------------------------------ families
FamilyFn = Callable[[Workspace, HistoryConfig, random.Random, FrozenSet[str]], Optional[Body]]
HISTORY_FAMILIES: Dict[str, FamilyFn] = {}


def register_history(name: str) -> Callable[[FamilyFn], FamilyFn]:
    def deco(fn: FamilyFn) -> FamilyFn:
        HISTORY_FAMILIES[name] = fn
        return fn
    return deco


def _files(ws: Workspace, paths: Sequence[str], exclude: FrozenSet[str]) -> List[str]:
    return [p for p in paths if p not in exclude and ws.text(p) is not None]


@register_history("H1")
def h1_edit_inverse(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Body]:
    files = _files(ws, ws.targets, exclude)
    for _ in range(cfg.attempts if files else 0):
        path = rng.choice(files)
        text = ws.text(path) or ""
        op, what = edit_op(rng, path, text, ws.language, cfg)
        ops = there_and_back(path, text, op, cfg, rng.random() < cfg.save_probability) if op else None
        if ops:
            return Body(ops, (path,), f"{path}: {what}, then its inverse" + (" (saved)" if len(ops) > 2 else ""))
    return None


@register_history("H2")
def h2_delete_retype(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Body]:
    files = _files(ws, ws.targets, exclude)
    for _ in range(cfg.attempts if files else 0):
        path = rng.choice(files)
        text = ws.text(path) or ""
        line = pick_line(rng, text, ws.language, cfg, terminated=True)
        if line is None:
            continue
        try:
            ops, k = retype_ops(rng, path, text, line, cfg)
        except OpError:
            continue
        if rng.random() < cfg.save_probability:  # save the deleted state and the restored one
            ops = ops[:1] + [Op("save", path, delay_ms=cfg.delay_ms)] + ops[1:] + [Op("save", path, delay_ms=cfg.delay_ms)]
        return Body(tuple(ops), (path,), f"{path}: delete line {line}, retype it in {k} chunk(s)")
    return None


@register_history("H3")
def h3_close_reopen(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Body]:
    files, d = _files(ws, ws.targets, exclude), cfg.delay_ms
    if not files:
        return None
    path = rng.choice(files)
    op, what = edit_op(rng, path, ws.text(path) or "", ws.language, cfg) if rng.random() < 0.5 else (None, "")
    ops = ((op,) if op else ()) + (Op("close", path, delay_ms=d), Op("open", path, delay_ms=d))
    return Body(ops, (path,), f"{path}: " + (f"unsaved edit ({what}), " if op else "") + "close, reopen")


@register_history("H4")
def h4_config_toggle(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Body]:
    toggles = SETTING_TOGGLES.get(ws.server_kind, ())
    if SETTINGS_RESOURCE in exclude or not toggles:
        return None
    tg = rng.choice(toggles)
    a_vals = [get_path(ws.settings, p, tg.default) for p in tg.paths]
    b = tg.other(a_vals[0])
    if b is None:
        return None
    ops = (Op("set_config", settings=nested([(p, b) for p in tg.paths]), delay_ms=cfg.delay_ms),
           Op("set_config", settings=nested(list(zip(tg.paths, a_vals))), delay_ms=cfg.delay_ms))
    return Body(ops, (SETTINGS_RESOURCE,), f"toggle {'.'.join(tg.paths[0])}: {a_vals[0]!r} -> {b!r} -> back")


@register_history("H5")
def h5_rename(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Body]:
    targets, deps = _files(ws, ws.targets, exclude), _files(ws, ws.deps, exclude)
    pool = targets if targets and (not deps or rng.random() < 0.6) else deps
    if not pool:
        return None
    path = rng.choice(pool)
    stem, ext = os.path.splitext(path)
    new = next((c for c in (f"{stem}_rt{i or ''}{ext}" for i in range(50)) if not ws.exists(c) and c not in exclude), "")
    if not new:
        return None
    d = cfg.delay_ms
    return Body((Op("fs_rename", path, new_path=new, delay_ms=d), Op("fs_rename", new, new_path=path, delay_ms=d)),
                (path, new), f"rename {path} -> {new} -> back")


@register_history("H6")
def h6_dependency(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Body]:
    deps, confs, d = _files(ws, ws.deps, exclude), _files(ws, ws.configs, exclude), cfg.delay_ms
    modes = (["dep-editor", "dep-disk"] if deps else []) + (["config"] if confs else [])
    rng.shuffle(modes)
    for mode in modes:
        path = rng.choice(confs if mode == "config" else deps)
        text, op = ws.text(path) or "", None
        if mode == "config":
            variant, what = config_variant(rng, text)
        else:
            op, what = edit_op(rng, path, text, ws.language, cfg)
            variant = apply_change(text, op.start, op.end, op.text)[0] if op and op.start and op.end else None
        if variant is None or variant == text:
            continue
        if mode == "dep-editor" and op is not None:
            back = there_and_back(path, text, op, cfg, rng.random() < cfg.save_probability)
            if back is None:
                continue
            ops = (Op("open", path, delay_ms=d),) + back + (Op("close", path, delay_ms=d),)
        else:
            ops = (Op("fs_write", path, text=variant, delay_ms=d), Op("fs_write", path, text=text, delay_ms=d))
        return Body(ops, (path,), f"{mode} round trip on {path}: {what}")
    return None


def interleave(rng: random.Random, parts: Sequence[Sequence[Op]]) -> Tuple[List[Op], str]:
    """Order-preserving shuffle (uniform over interleavings), or nesting: each outer part is cut
    once and the rest is placed inside the cut."""
    if rng.random() < 0.5:
        order = list(range(len(parts)))
        rng.shuffle(order)
        ops = list(parts[order[-1]])
        for k in reversed(order[:-1]):
            cut = rng.randint(1, len(parts[k]) - 1) if len(parts[k]) > 1 else len(parts[k])
            ops = list(parts[k][:cut]) + ops + list(parts[k][cut:])
        return ops, "nest " + ">".join(str(k) for k in order)
    queues, ops = [list(p) for p in parts], []
    while any(queues):
        live = [i for i, q in enumerate(queues) if q]
        ops.append(queues[rng.choices(live, weights=[len(queues[i]) for i in live])[0]].pop(0))
    return ops, "shuffle"


@register_history("H7")
def h7_interleave(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Body]:
    want, parts, used = rng.choice((2, 3)), [], set(exclude)
    for _ in range(want * cfg.attempts):
        if len(parts) == want:
            break
        fam = rng.choice(PART_FAMILIES)
        body = HISTORY_FAMILIES[fam](ws, cfg, rng, frozenset(used))
        if body is not None:
            parts.append((fam, body))
            used.update(body.resources)
    if len(parts) < 2:
        return None
    ops, how = interleave(rng, [b.ops for _, b in parts])
    ops = fix_requests(ops, ws.text, [p for p in ws.targets if ws.text(p) is not None])
    return Body(tuple(ops), tuple(sorted(used - set(exclude))), f"{how}: " + " | ".join(f"{f} {b.note}" for f, b in parts))


@register_history("H8")
def h8_query_order(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Body]:
    texts = {p: t for p in ws.targets if (t := ws.text(p)) is not None}
    files = [p for p in texts if p not in exclude]
    lead: Tuple[Op, ...] = ()
    note, res = "", ()
    if files and rng.random() < 0.5:
        path = rng.choice(files)
        op, what = edit_op(rng, path, texts[path], ws.language, cfg)
        back = there_and_back(path, texts[path], op, cfg, False) if op else None
        if back:
            lead, note, res = back, f"after {path}: {what} and its inverse, ", (path,)
    reqs = warmup_ops(rng, texts, ws.positions, ws.language, cfg)
    if not reqs:
        return None
    asked = ", ".join(f"{o.text}@{o.path}:{o.start[0]}:{o.start[1]}" for o in reqs[:5] if o.start is not None)
    return Body(lead + tuple(reqs), res, f"{note}{len(reqs)} requests in a shuffled order: {asked}"
                + (", ..." if len(reqs) > 5 else ""))


Change = Tuple[Tuple[Op, ...], Tuple[Op, ...], Tuple[str, ...], str]  # (apply, revert, files, description)


def workspace_change(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Change]:
    """H9's W: a configuration-file variant, a depended-on file edited on disk or in the editor,
    or a depended-on file or target renamed (kind drawn uniformly among those the project has)."""
    deps, confs, d = _files(ws, ws.deps, exclude), _files(ws, ws.configs, exclude), cfg.delay_ms
    movable = [p for p in ws.deps + ws.targets if p not in exclude and ws.exists(p)]
    kinds = (["config"] if confs else []) + (["dep-disk", "dep-editor"] if deps else []) + (["rename"] if movable else [])
    kind = rng.choice(kinds) if kinds else ""
    if kind == "rename":
        path = rng.choice(movable)
        stem, ext = os.path.splitext(path)
        new = next((c for c in (f"{stem}_rt{i or ''}{ext}" for i in range(50)) if not ws.exists(c) and c not in exclude), "")
        return ((Op("fs_rename", path, new_path=new, delay_ms=d),), (Op("fs_rename", new, new_path=path, delay_ms=d),),
                (path, new), f"rename {path} -> {new}") if new else None
    if not kind:
        return None
    path = rng.choice(confs if kind == "config" else deps)
    text = ws.text(path) or ""
    if kind == "config":
        variant, what = config_variant(rng, text)
        return None if variant is None or variant == text else (
            (Op("fs_write", path, text=variant, delay_ms=d),), (Op("fs_write", path, text=text, delay_ms=d),), (path,),
            f"{path}: {what}")
    op, what = edit_op(rng, path, text, ws.language, cfg)
    if op is None or op.start is None or op.end is None:
        return None
    if kind == "dep-disk":
        variant = apply_change(text, op.start, op.end, op.text)[0]
        return ((Op("fs_write", path, text=variant, delay_ms=d),), (Op("fs_write", path, text=text, delay_ms=d),),
                (path,), f"{path} on disk: {what}")
    back = there_and_back(path, text, op, cfg, rng.random() < cfg.save_probability)
    if back is None:
        return None
    half = len(back) // 2  # (edit[, save]) | (inverse[, save])
    return ((Op("open", path, delay_ms=d),) + back[:half], back[half:] + (Op("close", path, delay_ms=d),), (path,),
            f"{path} in the editor: {what}")


def document_change(ws: Workspace, cfg: HistoryConfig, rng: random.Random, path: str) -> Tuple[Tuple[Op, ...], str]:
    """H9's D on one open target: edit + inverse, delete + retype a line, or close + reopen
    (after an unsaved edit half of the time); falls back to close + reopen."""
    text, kind = ws.text(path) or "", rng.choice(("edit", "retype", "reopen"))
    if kind == "edit":
        op, what = edit_op(rng, path, text, ws.language, cfg)
        ops = there_and_back(path, text, op, cfg, rng.random() < cfg.save_probability) if op else None
        if ops:
            return ops, f"{path}: {what}, then its inverse"
    line = pick_line(rng, text, ws.language, cfg, terminated=True) if kind == "retype" else None
    if line is not None:
        try:
            ops2, k = retype_ops(rng, path, text, line, cfg)
            return tuple(ops2), f"{path}: line {line} deleted and retyped in {k} chunk(s)"
        except OpError:
            pass
    op, what = edit_op(rng, path, text, ws.language, cfg) if rng.random() < 0.5 else (None, "")
    return ((op,) if op else ()) + (Op("close", path, delay_ms=cfg.delay_ms), Op("open", path, delay_ms=cfg.delay_ms)), (
        f"{path}: " + (f"unsaved edit ({what}), " if op else "") + "close, reopen")


@register_history("H9")
def h9_edit_in_window(ws: Workspace, cfg: HistoryConfig, rng: random.Random, exclude: FrozenSet[str]) -> Optional[Body]:
    for _ in range(cfg.attempts):
        w = workspace_change(ws, cfg, rng, exclude)
        docs = [p for p in _files(ws, ws.targets, exclude) if w is not None and p not in w[2]]
        if w is None or not docs:
            continue
        rng.shuffle(docs)
        inside = [document_change(ws, cfg, rng, p) for p in docs]
        return Body(w[0] + tuple(op for ops, _ in inside for op in ops) + w[1], tuple(sorted(set(w[2]) | set(docs))),
                    f"window: {w[3]}; inside: " + "; ".join(n for _, n in inside) + "; then W reverted")
    return None


# ------------------------------------------------------------ histories
def prelude(ws: Workspace, cfg: HistoryConfig) -> Tuple[Op, ...]:
    return tuple(Op("open", p, delay_ms=cfg.delay_ms) for p in ws.targets if ws.text(p) is not None)


def generate(family: str, ws: Workspace, cfg: HistoryConfig, seed: int) -> Optional[History]:
    """One history of a family; the same (family, project, cfg, seed) always gives the same ops."""
    body = HISTORY_FAMILIES[family](ws, cfg, random.Random(f"history:{family}:{seed}"), frozenset())
    return None if body is None else History(family, seed, prelude(ws, cfg), body.ops, body.resources, body.note)


def generate_many(ws: Workspace, cfg: HistoryConfig, seed: int, n: int,
                  families: Sequence[str] = FAMILY_ORDER) -> List[History]:
    """Up to n histories, families in a seeded round-robin order (a family that does not
    apply to the project is skipped)."""
    order = list(families)
    random.Random(f"families:{seed}").shuffle(order)
    out: List[History] = []
    tries = 0
    while len(out) < n and tries < 4 * n + len(order):
        fam = order[tries % len(order)]
        tries += 1
        h = generate(fam, ws, cfg, seed * 1000 + tries)
        if h is not None:
            out.append(h)
    return out


__all__ = [
    "Body", "FAMILY_DESCRIPTIONS", "FAMILY_ORDER", "HISTORY_FAMILIES", "History", "HistoryConfig", "PART_FAMILIES",
    "SETTINGS_RESOURCE", "Workspace", "build_workspace", "document_change", "generate", "generate_many", "interleave",
    "prelude", "register_history", "round_trip", "workspace_change",
]
