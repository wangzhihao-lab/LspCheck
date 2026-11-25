"""R3 route equivalence (plan/tool_design_v1.md sections 5 and 10): two routes to one fact agree.

(a) Pull vs push diagnostics: a fresh pair in the server's default route gives the stable
    keys; one fresh session in the other route (DriverConfig.pull_diagnostics) must report
    the same diagnostics. Only where both routes really exist: that session must run in the
    other mode (diagnosticProvider declared exactly when asked for) and, for push, publish.
(b) semanticTokens/range over seeded ranges (around a target, one starting mid-line, the file)
    equals full restricted to the range, both sides cut to tokens lying entirely inside it.
(c) documentHighlight ranges (kind ignored) are a subset of the references ranges
    (includeDeclaration) in the same file, at identifier targets. Known legitimate extra:
    gopls highlights the printf verb that formats the argument (`%q` for `got`); kept in the data.
(d) For a target with definition set D, `definition` at each of its references (at most 10,
    its own occurrence skipped) returns D.
(b)-(d) run in both sessions of the pair (a reference's file is opened before asking there, as an
editor does); a candidate fails identically in both. Legitimate exceptions get a method (and
signature) of their own, never dropped: `definitionConsistency.shorthand` where `{ name }` names a
member and a variable (object and struct literals; binding patterns, where TypeScript answers the
member), `definitionConsistency.signature` where the answers differ only in entries wider than
the name (the call, construct or instanceof signature added at that site). The module also holds
in-session utilities shared with r2_handles and r5_transforms.

Run line: imported through oracles.load_all() by campaign.py, flake.py and reduce.py; not run directly.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .base import (MISSING, OracleContext, OracleResult, ReplayOutcome, case_of, make_violation, register_oracle,
                   session, shape_of, stable_keys)
from driver import Driver  # noqa: E402
from model import Op, QueryKey, Snapshot, Violation  # noqa: E402
from ops import LineIndex, OpError, inverse_change, lsp_range, utf16_len  # noqa: E402
from queries import LSP_METHODS, NORMALIZERS, QueryConfig  # noqa: E402
from targets import EXCLUDED_DIRS, FAMILY, SERVER_LANGUAGE, FileTargets  # noqa: E402

logger = logging.getLogger(__name__)
ORACLE = "r3_routes"
REF_CAP = 10
SESSION_ERRORS = (OSError, RuntimeError, ValueError, subprocess.SubprocessError)
INCLUDE_DECL = {"context": {"includeDeclaration": True}}


@dataclass
class Check:
    """One relation evaluated inside one session: `expected` must equal `actual`."""

    key: QueryKey
    expected: Any
    actual: Any
    case: Dict[str, Any]
    note: str = ""


@dataclass
class SessionOut:
    snap: Snapshot
    pull: bool = False
    assumed: List[str] = field(default_factory=list)  # push: documents that never got a publish
    checks: Dict[QueryKey, Check] = field(default_factory=dict)


# ------------------------------------------------------------------ pure relations
def failed(norm: Any) -> bool:
    return isinstance(norm, list) and len(norm) == 2 and norm[0] in ("error", "unnormalizable")


def tokens_inside(tokens: Any, rng: Sequence[int]) -> List[List[Any]]:
    """Decoded tokens [line, char, length, type, mods] entirely inside [sl, sc, el, ec)."""
    sl, sc, el, ec = rng
    return [list(t) for t in tokens or [] if (sl, sc) <= (t[0], t[1]) and (t[0], t[1] + t[2]) <= (el, ec)]


def highlight_check(highlights: Any, references: Any, path: str) -> Optional[Tuple[List[Any], List[Any]]]:
    """(highlight ranges that are also reference ranges in `path`, all highlight ranges); None
    when either answer failed. The relation holds when both are equal."""
    if not all(isinstance(x, list) and not failed(x) for x in (highlights, references)):
        return None
    refs = {tuple(r[1:5]) for r in references if r[0] == path}
    hl = sorted({tuple(h[:4]) for h in highlights})
    return [list(h) for h in hl if h in refs], [list(h) for h in hl]


def seeded_ranges(text: str, positions: Sequence[Tuple[int, int]], seed: int, path: str) -> List[List[int]]:
    """Whole lines around a target line, a range starting mid-line at a target, the document."""
    idx, rng = LineIndex(text), random.Random(f"r3:{seed}:{path}")
    last = len(idx.starts) - 1
    lines = sorted({p[0] for p in positions}) or [0]
    a = max(0, rng.choice(lines) - rng.randint(0, 5))
    out = [[a, 0, min(last, a + rng.randint(1, 30)), 0]]
    if positions:
        line, ch = rng.choice(list(positions))
        e = min(last, line + rng.randint(0, 10))
        out.append([line, ch, e, utf16_len(idx.line_text(e))])
    out.append([0, 0, *idx.end()])
    return [r for i, r in enumerate(out) if r not in out[:i] and (r[0], r[1]) < (r[2], r[3])]


def ref_position(loc: Sequence[Any]) -> Tuple[str, int, int]:
    """Where to ask at a reference [path, sl, sc, el, ec]: the middle of a one-line range."""
    path, sl, sc, el, ec = loc[:5]
    return path, sl, (sc + (ec - sc) // 2) if sl == el else sc


def shorthand(text: str, line: int, sc: int, ec: int) -> bool:
    """`{ name }`, `{ a, name }`, `S { name }`, `const { name } = o`: an identifier between `{`/`,`
    and `,`/`}` that is not in an import or export list."""
    idx = LineIndex(text)
    try:
        s, e = idx.offset((line, sc)), idx.offset((line, ec))
    except OpError:
        return False
    head = text[:s]
    return head.rstrip()[-1:] in ("{", ",") and text[e:].lstrip()[:1] in (",", "}") \
        and not re.search(r"\b(import|export)(\s+type)?\s*$", head[:head.rfind("{")])


def site_label(text: str, loc: Sequence[Any], defs: List[Any], actual: Any, family: str) -> str:
    """Why a definition answer at a reference may legitimately differ from the target's (see
    the module docstring): "signature", "shorthand", or "" (no known reason)."""
    if not isinstance(actual, list) or failed(actual) or actual == defs:
        return ""
    width = loc[4] - loc[2] if loc[1] == loc[3] else -1
    diff = [x for x in defs if x not in actual] + [x for x in actual if x not in defs]
    if width > 0 and any(x in actual for x in defs) and all(x[1] != x[3] or x[4] - x[2] != width for x in diff):
        return "signature"
    return "shorthand" if family in ("js", "rs") and width > 0 and shorthand(text, loc[1], loc[2], loc[4]) else ""


# ------------------------------------------------------------------ in-session utilities (shared)
def key_targets(targets: Sequence[FileTargets], key: QueryKey) -> Tuple[FileTargets, ...]:
    """The same files (the same open set) with only the key's position queried."""
    at = [(t, t.path == key.path and key.line >= 0) for t in targets]
    pos, comp = ((key.line, key.character),), key.method == "completion"
    return tuple(FileTargets(t.path, pos if a and not comp else (), pos if a and comp else (), ("",) if a else ())
                 for t, a in at)


def key_query(ctx: OracleContext, key: QueryKey) -> QueryConfig:
    methods = (key.method, "diagnostics") if key.method == "codeAction" else (key.method,)
    return QueryConfig(methods=methods, request_timeout_s=ctx.request_timeout_s)


def rng4(r: Any) -> List[int]:
    s, e = (r or {}).get("start") or {}, (r or {}).get("end") or {}
    return [int(x.get(k, -1)) for x in (s, e) for k in ("line", "character")]


def apply_text_edits(text: str, edits: Sequence[Sequence[Any]]) -> str:
    """[sl, sc, el, ec, newText] edits on `text`, back to front (inserts at one point keep their
    array order). Raises OpError for a range outside the text, inverted or overlapping."""
    idx, bound = LineIndex(text), len(text)
    spans = [(idx.offset((e[0], e[1])), idx.offset((e[2], e[3])), i, str(e[4])) for i, e in enumerate(edits)]
    for s, t, _, new in sorted(spans, reverse=True):
        if t < s or t > bound:
            raise OpError("overlapping or inverted edit ranges")
        text, bound = text[:s] + new + text[t:], s
    return text


def raw_diagnostics(ctx: OracleContext, d: Driver, path: str) -> List[Dict[str, Any]]:
    result, err = d.diagnostics(path, ctx.request_timeout_s)
    items = result.get("items") if isinstance(result, dict) else result
    return [x for x in items or [] if isinstance(x, dict)] if err is None else []


class Shifted:
    """Apply one edit op in a live session and settle (race mode: sleep the delay; settle_race()
    settles later); revert() applies the inverse edit and settles."""

    def __init__(self, ctx: OracleContext, d: Driver, op: Op) -> None:
        self.ctx, self.d, self.op, self.before = ctx, d, op, d.text(op.path)
        try:
            self.ok = not d.apply(op).error
        except OpError:
            self.ok = False
        if self.ok and ctx.race_delay_ms is None:
            self.ok = d.settle().settled
        elif self.ok:
            time.sleep(ctx.race_delay_ms / 1000.0)

    def settle_race(self) -> bool:
        return self.ctx.race_delay_ms is None or self.d.settle().settled

    def revert(self) -> None:
        if self.d.text(self.op.path) != self.before:
            self.d.apply(inverse_change(self.op, self.before))
            self.d.settle()


# ------------------------------------------------------------------ checks in a live session
def tokens_options(d: Driver) -> Dict[str, Any]:
    """semanticTokensProvider options, static or dynamically registered ({} when absent)."""
    prov = (getattr(d.client, "server_capabilities", None) or {}).get("semanticTokensProvider")
    if isinstance(prov, dict):
        return prov
    d.monitor.poll()
    return d.monitor.registered("textDocument/semanticTokens") or {}


def ask(ctx: OracleContext, d: Driver, method: str, path: str, pos: Sequence[int], extra: Optional[Dict] = None) -> Any:
    params = dict({"textDocument": {"uri": d.uri(path)}, "position": {"line": pos[0], "character": pos[1]}},
                  **(extra or {}))
    result, err = d.request(LSP_METHODS[method], params, ctx.request_timeout_s)
    return list(err) if err else NORMALIZERS[method](result, d.norm_context(50))


def full_tokens(ctx: OracleContext, d: Driver, path: str) -> Optional[List[Any]]:
    result, err = d.request("textDocument/semanticTokens/full", {"textDocument": {"uri": d.uri(path)}},
                            ctx.request_timeout_s)
    return None if err else NORMALIZERS["semanticTokens"](result, d.norm_context(50))


def range_check(ctx: OracleContext, d: Driver, path: str, r: List[int], full: List[Any]) -> Check:
    doc = {"textDocument": {"uri": d.uri(path)}, "range": lsp_range((r[0], r[1]), (r[2], r[3]))}
    result, err = d.request("textDocument/semanticTokens/range", doc, ctx.request_timeout_s)
    actual = list(err) if err else tokens_inside(NORMALIZERS["semanticTokens"](result, d.norm_context(50)), r)
    return Check(QueryKey("semanticTokensRange", path, r[0], r[1], f"{r[2]}:{r[3]}"), tokens_inside(full, r),
                 actual, {"sub": "b", "path": path, "range": r})


def highlight_pair(ctx: OracleContext, d: Driver, path: str, pos: Sequence[int]) -> Optional[Check]:
    refs = ask(ctx, d, "references", path, pos, INCLUDE_DECL)
    got = highlight_check(ask(ctx, d, "documentHighlight", path, pos), refs, path)
    if got is None:
        return None
    return Check(QueryKey("highlightVsReferences", path, pos[0], pos[1]), got[0], got[1],
                 {"sub": "c", "path": path, "pos": list(pos)}, f"{len(refs)} references")


def definition_pair(ctx: OracleContext, d: Driver, target: Sequence[Any], defs: List[Any], loc: List[Any]) -> Check:
    rpath, rl, rc = ref_position(loc)
    if rpath not in d.store.open_paths():  # an editor opens a file before navigating in it
        d.open(rpath)
        d.settle()
    actual = ask(ctx, d, "definition", rpath, (rl, rc))
    try:
        label = site_label(d.text(rpath), loc, defs, actual, FAMILY.get(ctx.language, ""))
    except OpError:
        label = ""
    key = QueryKey("definitionConsistency" + (f".{label}" if label else ""), rpath, rl, rc,
                   f"from:{target[0]}:{target[1]}:{target[2]}")
    return Check(key, defs, actual, {"sub": "d", "target": list(target), "loc": list(loc)}, label)


def definition_checks(ctx: OracleContext, d: Driver, path: str, pos: Sequence[int], seen: Set[str]) -> List[Check]:
    defs = ask(ctx, d, "definition", path, pos)
    if not isinstance(defs, list) or not defs or failed(defs) or json.dumps(defs) in seen:
        return []
    seen.add(json.dumps(defs))
    refs = ask(ctx, d, "references", path, pos, INCLUDE_DECL)
    if not isinstance(refs, list) or failed(refs):
        return []
    own = [r for r in refs if r[0] == path and (r[1], r[2]) <= tuple(pos) <= (r[3], r[4])]
    locs = [r for r in refs if r not in own and not os.path.isabs(r[0]) and r[0] != "."
            and not EXCLUDED_DIRS & set(r[0].split("/"))][:REF_CAP]  # the project's own sources, as targets.py
    return [definition_pair(ctx, d, [path, pos[0], pos[1]], defs, loc) for loc in locs]


def session_checks(ctx: OracleContext, d: Driver) -> Dict[QueryKey, Check]:
    out: Dict[QueryKey, Check] = {}
    opts, seen = tokens_options(d), set()
    hl = d.supports("documentHighlight") and d.supports("references")
    df = d.supports("definition") and d.supports("references")
    for ft in ctx.targets:
        full = full_tokens(ctx, d, ft.path) if opts.get("range") and opts.get("full") else None
        for r in seeded_ranges(d.text(ft.path), ft.positions, ctx.seed, ft.path) if full is not None else []:
            c = range_check(ctx, d, ft.path, r, full)
            out[c.key] = c
        for pos in ft.positions:
            c = highlight_pair(ctx, d, ft.path, pos) if hl else None
            if c is not None:
                out[c.key] = c
            for c in definition_checks(ctx, d, ft.path, pos, seen) if df else []:
                out[c.key] = c
    return out


def run_route_session(ctx: OracleContext, label: str, pull: Optional[bool], checks: bool) -> SessionOut:
    """One fresh session: diagnostics snapshot of the targets, then the in-session checks."""
    qcfg = QueryConfig(methods=("diagnostics",), request_timeout_s=ctx.request_timeout_s)
    try:
        with session(ctx, label, pull=pull) as d:
            snap = d.snapshot(label, list(ctx.targets), qcfg)
            out = SessionOut(snap, d.pull_mode(), list(d.last_settle.assumed if d.last_settle else []))
            out.checks = session_checks(ctx, d) if checks and snap.settled else {}
            return out
    except SESSION_ERRORS as exc:
        logger.warning("%s: session %s failed: %s", ORACLE, label, exc)
        return SessionOut(Snapshot(label, ctx.server, False))


def compare_routes(base: Snapshot, other: SessionOut, keys: Set[QueryKey], want_pull: bool, files: int
                   ) -> Tuple[List[Tuple[QueryKey, Any, Any]], str]:
    """Diagnostics of the default route vs the other route, or why the pair is not comparable."""
    route = "pull" if want_pull else "push"
    if other.pull != want_pull:
        return [], f"(a) not applicable: asked for {route}, the server stayed in {'pull' if other.pull else 'push'}"
    if not want_pull and len(other.assumed) >= files:
        return [], "(a) not applicable: no publishDiagnostics arrived in the push route"
    if not other.snap.settled:
        return [], f"(a) the {route} session did not settle"
    out = []
    for k in sorted((k for k in keys if k.method == "diagnostics"), key=lambda q: q.path):
        r = other.snap.results.get(k)
        act = MISSING if r is None else ([] if r.norm is None and k.path in other.assumed else r.norm)
        if base.results[k].norm != act:
            out.append((QueryKey("diagnostics", k.path, -1, -1, f"route:{route}"), base.results[k].norm, act))
    return out, ""


@register_oracle(ORACLE)
class R3Routes:
    name = ORACLE

    def applies_to(self, server_kind: str) -> bool:
        return server_kind in SERVER_LANGUAGE or server_kind == "jdtls"

    def run(self, ctx: OracleContext) -> OracleResult:
        t0, res = time.monotonic(), OracleResult(ORACLE, ctx.run_id)
        base = run_route_session(ctx, "r3-baseline", None, True)
        ctrl = run_route_session(ctx, "r3-control", None, True)
        res.sessions, res.unsettled = 2, int(not base.snap.settled) + int(not ctrl.snap.settled)
        for key, b in sorted(base.checks.items(), key=lambda kv: json.dumps(kv[0].__dict__, sort_keys=True)):
            c, m = ctrl.checks.get(key), key.method
            if c is None or (c.expected, c.actual) != (b.expected, b.actual):
                res.unstable[m] = res.unstable.get(m, 0) + 1
                continue
            res.cases, res.compared[m] = res.cases + 1, res.compared.get(m, 0) + 1
            if b.expected != b.actual:
                res.candidates.append(make_violation(ctx, ORACLE, key, b.expected, b.actual, [], b.case, b.note))
        stable = stable_keys(base.snap, ctrl.snap)
        if stable:
            other = run_route_session(ctx, "r3-route", not base.pull, False)
            res.sessions += 1
            diffs, why = compare_routes(base.snap, other, stable, not base.pull, len(ctx.targets))
            res.notes += [why] if why else []
            if not why:
                res.cases += 1
                res.compared["diagnostics:route"] = sum(1 for k in stable if k.method == "diagnostics")
            for key, exp, act in diffs:
                case = {"sub": "a", "path": key.path, "want_pull": not base.pull}
                res.candidates.append(make_violation(ctx, ORACLE, key, exp, act, [], case, "pull vs push"))
        res.seconds = round(time.monotonic() - t0, 3)
        return res

    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        t0, case = time.monotonic(), case_of(v)
        if case.get("sub") == "a":
            b = run_route_session(ctx, "r3-replay-baseline", None, False)
            c = run_route_session(ctx, "r3-replay-control", None, False)
            k = QueryKey("diagnostics", v.key.path)
            stable = {k} & stable_keys(b.snap, c.snap)
            other = run_route_session(ctx, "r3-replay-route", bool(case["want_pull"]), False)
            diffs, _ = compare_routes(b.snap, other, stable, bool(case["want_pull"]), len(ctx.targets))
            obs = [make_violation(ctx, ORACLE, key, e, a, [], case, "replay") for key, e, a in diffs]
            settled = b.snap.settled and c.snap.settled and other.snap.settled
            return ReplayOutcome(settled, bool(stable), bool(obs) and shape_of(obs[0]) == shape_of(v),
                                 obs[0] if obs else None, round(time.monotonic() - t0, 3))
        runs: List[Tuple[bool, Optional[Check]]] = []
        for label in ("r3-replay-baseline", "r3-replay-control"):
            try:
                with session(ctx, label) as d:
                    d.open(*[t.path for t in ctx.targets])
                    ok = d.settle().settled
                    runs.append((ok, self._recheck(ctx, d, case) if ok else None))
            except SESSION_ERRORS as exc:
                logger.warning("%s replay session failed: %s", ORACLE, exc)
                runs.append((False, None))
        (ok_b, b), (ok_c, c) = runs
        stable = b is not None and c is not None and (b.expected, b.actual) == (c.expected, c.actual)
        obs = make_violation(ctx, ORACLE, b.key, b.expected, b.actual, [], case, b.note) \
            if b is not None and b.expected != b.actual else None
        return ReplayOutcome(ok_b and ok_c, stable, obs is not None and shape_of(obs) == shape_of(v), obs,
                             round(time.monotonic() - t0, 3))

    @staticmethod
    def _recheck(ctx: OracleContext, d: Driver, case: Dict[str, Any]) -> Optional[Check]:
        sub, target = case.get("sub"), case.get("target") or []
        if sub == "b":
            full = full_tokens(ctx, d, case["path"])
            return None if full is None else range_check(ctx, d, case["path"], list(case["range"]), full)
        if sub == "c":
            return highlight_pair(ctx, d, case["path"], case["pos"])
        defs = ask(ctx, d, "definition", target[0], target[1:3]) if sub == "d" else ["error", "no case"]
        return None if failed(defs) else definition_pair(ctx, d, target, defs, case["loc"])


__all__ = ["Check", "R3Routes", "Shifted", "apply_text_edits", "compare_routes", "definition_checks", "failed",
           "highlight_check", "key_query", "key_targets", "raw_diagnostics", "ref_position", "rng4", "seeded_ranges",
           "session_checks", "shorthand", "site_label", "tokens_inside", "tokens_options"]
