"""R2 handle validity (plan/tool_design_v1.md sections 5 and 10). One session runs every case,
reverting each case's edit before the next.

(a) Code actions with `data` (codeAction/resolve) and completion items (resolveProvider): mint
handles at T0 (code actions at a target or a diagnostic range; completion at a target's end,
items matching the typed prefix and import-bearing items first) and resolve them once, as an
editor does while browsing (this picks handles whose resolve yields an edit); apply a shifting
edit E (k line breaks at the handle's line, below it, or at the end); settle (race mode: after
the stale resolves); resolve the OLD handles; mint FRESH handles at the positions mapped through
E and resolve them twice. Allowed: any error, no edit (completion: none added or changed by the
resolve), an edit naming a stale document version (clients refuse it), or the fresh handle's
edit (same title + kind, or label + kind + labelDetails + sortText, and occurrence). Violation:
a different edit. A stale edit without a comparable fresh one is applied to the current text: a
range outside it, or new syntax errors when oracles/syntax.py exists (lazy import), is a
violation under `<method>Apply`.
(b) Semantic tokens with full/delta: full at T0 with a resultId, an edit, the delta against that
resultId applied to the T0 data must equal a new full (taken twice); then the edit is reverted
and the chain checked again from the latest resultId.

Run line: imported through oracles.load_all() by campaign.py, flake.py and reduce.py; not run directly.
"""

from __future__ import annotations

import importlib
import itertools
import json
import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from .base import (OracleContext, OracleResult, ReplayOutcome, case_of, make_violation, register_oracle, session,
                   shape_of)
from .r3_routes import SESSION_ERRORS, Shifted, apply_text_edits, raw_diagnostics, rng4, tokens_options
from driver import Driver  # noqa: E402
from model import Op, QueryKey, Violation  # noqa: E402
from ops import LineIndex, OpError, inverse_change, lsp_range  # noqa: E402
from queries import NORMALIZERS  # noqa: E402
from targets import FAMILY, SERVER_LANGUAGE, diagnostic_ranges  # noqa: E402

logger = logging.getLogger(__name__)
ORACLE = "r2_handles"
PROBE_CAP, KEEP_CAP, SHIFTS = 12, 6, ("above", "top", "above", "top", "below", "end")  # top: where imports land
FULL, DELTA = "textDocument/semanticTokens/full", "textDocument/semanticTokens/full/delta"
IMPORT_HINT = re.compile(r"[Ii]mport|[Mm]odule")
Ident = Tuple[str, ...]


@dataclass
class Obs:
    key: QueryKey
    expected: Any
    actual: Any
    stable: bool = True  # the fresh reference was the same twice
    allowed: str = ""  # non-empty: an allowed outcome, and why
    note: str = ""


# ------------------------------------------------------------------ pure helpers
def edit_entries(edit: Any, rel: Callable[[str], str]) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """A WorkspaceEdit as sorted [path, sl, sc, el, ec, newText] (resource operations as
    ["<kind>", path, new path]) and the document version each TextDocumentEdit names."""
    edit, out, versions = edit if isinstance(edit, dict) else {}, [], {}
    groups = [(uri, None, edits) for uri, edits in (edit.get("changes") or {}).items()]
    for dc in (x for x in edit.get("documentChanges") or [] if isinstance(x, dict)):
        if "kind" in dc:
            out.append([f"<{dc['kind']}>", rel(str(dc.get("uri") or dc.get("oldUri") or "")),
                        rel(str(dc.get("newUri") or ""))])
        else:
            groups.append((str((dc.get("textDocument") or {}).get("uri", "")), dc.get("textDocument"), dc.get("edits")))
    for uri, doc, edits in groups:
        if isinstance(doc, dict):
            versions[rel(uri)] = doc.get("version")
        out += [[rel(uri)] + rng4(e.get("range")) + [str(e.get("newText", (e.get("snippet") or {}).get("value", "")))]
                for e in edits or [] if isinstance(e, dict)]
    return sorted(out, key=json.dumps), versions


def completion_edits(item: Any) -> Dict[str, List[List[Any]]]:
    """textEdit ([range | insert + replace, newText]) and additionalTextEdits of an item."""
    out, item = {}, item if isinstance(item, dict) else {}
    te, extra = item.get("textEdit"), item.get("additionalTextEdits")
    if isinstance(te, dict):
        ranges = [te.get("range")] if "range" in te else [te.get("insert"), te.get("replace")]
        out["textEdit"] = [sum((rng4(r) for r in ranges), []) + [str(te.get("newText", ""))]]
    if isinstance(extra, list) and extra:
        out["additionalTextEdits"] = sorted((rng4(e.get("range")) + [str(e.get("newText", ""))] for e in extra
                                             if isinstance(e, dict)), key=json.dumps)
    return out


def resolve_produced(minted: Any, resolved: Any) -> Dict[str, List[List[Any]]]:
    """The edit fields that the resolve added or changed."""
    before = completion_edits(minted)
    return {k: v for k, v in completion_edits(resolved).items() if before.get(k) != v}


def flatten(fields: Dict[str, List[List[Any]]]) -> List[List[Any]]:
    return sorted(([k] + e for k, entries in fields.items() for e in entries), key=json.dumps)


def apply_delta(data: Sequence[int], edits: Sequence[Dict[str, Any]]) -> List[int]:
    """SemanticTokensEdits (starts index the previous array; no overlaps) applied to it."""
    out, end = list(data), len(data)
    for e in sorted(edits, key=lambda x: int(x.get("start", 0)), reverse=True):
        start, count = int(e.get("start", 0)), int(e.get("deleteCount", 0))
        if start < 0 or count < 0 or start + count > end:
            raise ValueError(f"delta edit {start}+{count} overlaps or leaves the {len(data)}-element array")
        out[start:start + count], end = list(e.get("data") or []), start
    return out


def with_occurrence(items: Sequence[Dict[str, Any]], ident: Callable[[Dict[str, Any]], Ident]) -> Dict[Ident, Dict]:
    """Items keyed by identity plus occurrence index (the n-th item with that identity)."""
    counts: Dict[Ident, Any] = {}
    return {ident(x) + (str(next(counts.setdefault(ident(x), itertools.count()))),): x for x in items}


def make_shift(text: str, line: int, variant: str, k: int) -> Dict[str, Any]:
    """k line breaks at `line` (above), the next line (below), the file start (top) or its end."""
    idx, eol = LineIndex(text), ("\r\n" if "\r\n" in text else "\n")
    variant = variant if variant in ("above", "top") or (variant == "below" and line + 1 < len(idx.starts)) else "end"
    at = {"above": (line, 0), "below": (line + 1, 0), "top": (0, 0)}.get(variant) or idx.end()
    return {"variant": variant, "line": at[0], "col": at[1], "text": eol * k}


def map_pos(pos: Sequence[int], shift: Dict[str, Any]) -> Tuple[int, int]:
    """A position through an insertion whose text ends with a line break."""
    (l, c), at, n = pos[:2], (shift["line"], shift["col"]), shift["text"].count("\n")
    return (l, c) if (l, c) < at else ((l + n, c - at[1]) if l == at[0] else (l + n, c))


def token_window(expected: List[Any], actual: List[Any]) -> Tuple[List[Any], List[Any]]:
    """Both decoded token lists restricted to the lines where they differ."""
    e, a = [json.dumps(t) for t in expected], [json.dumps(t) for t in actual]
    lines = {t[0] for t, s in list(zip(expected, e)) + list(zip(actual, a)) if e.count(s) != a.count(s)}
    return [t for t in expected if t[0] in lines], [t for t in actual if t[0] in lines]


def judge_edit(key: QueryKey, stale: List[Any], err: Any, versions: Dict[str, Any], current: Dict[str, int],
               fresh: Sequence[Optional[List[Any]]]) -> Obs:
    """Verdict on one old handle: its edit ([] = none), its error, and two fresh edits (None:
    no comparable fresh handle)."""
    if err or not stale:
        return Obs(key, None, None, allowed=f"error:{err[1]}" if err else "no edit")
    if any(v is not None and v != current.get(p) for p, v in versions.items()):
        return Obs(key, None, stale, allowed="stale version named")
    if fresh[0] is None or fresh[1] is None:
        return Obs(key, None, stale, allowed="no comparable fresh edit")
    return Obs(key, fresh[0], stale, stable=fresh[0] == fresh[1])


# ------------------------------------------------------------------ handles in a live session
def handle_caps(d: Driver) -> Dict[str, bool]:
    caps, full = getattr(d.client, "server_capabilities", None) or {}, tokens_options(d).get("full")
    opts = {m: caps.get(f"{m}Provider") if isinstance(caps.get(f"{m}Provider"), dict)
            else (d.monitor.registered(f"textDocument/{m}") or {}) for m in ("codeAction", "completion")}
    return {"codeAction": bool(opts["codeAction"].get("resolveProvider")),
            "completion": bool(opts["completion"].get("resolveProvider")),
            "delta": isinstance(full, dict) and bool(full.get("delta"))}


def mint_actions(ctx: OracleContext, d: Driver, case: Dict[str, Any], r: Sequence[int]) -> Dict[Ident, Dict]:
    """Code actions with `data` and no edit, at a position (extra "pos") or a diagnostic range."""
    at = lambda x: rng4(x.get("range")) == list(r) if case["extra"] == "diag" else \
        rng4(x.get("range"))[:2] <= list(r[:2]) <= rng4(x.get("range"))[2:]  # noqa: E731
    params = {"textDocument": {"uri": d.uri(case["path"])}, "range": lsp_range(tuple(r[:2]), tuple(r[2:4])),
              "context": {"diagnostics": [x for x in raw_diagnostics(ctx, d, case["path"]) if at(x)], "triggerKind": 1}}
    result, err = d.request("textDocument/codeAction", params, ctx.request_timeout_s)
    acts = [a for a in (result if isinstance(result, list) and not err else [])
            if isinstance(a, dict) and "data" in a and not a.get("edit") and isinstance(a.get("title"), str)]
    return with_occurrence(acts, lambda a: (str(a.get("title", "")), str(a.get("kind", ""))))


def mint_items(ctx: OracleContext, d: Driver, case: Dict[str, Any], pos: Sequence[int]) -> Dict[Ident, Dict]:
    """Completion items as an editor lists them: those matching the typed prefix, then those
    hinting at an import, each group in display order (sortText, else label)."""
    params = {"textDocument": {"uri": d.uri(case["path"])}, "position": {"line": pos[0], "character": pos[1]},
              "context": {"triggerKind": 1}}
    result, err = d.request("textDocument/completion", params, ctx.request_timeout_s)
    items = [] if err else (result.get("items") if isinstance(result, dict) else result) or []
    idx = LineIndex(d.text(case["path"]))
    prefix = re.search(r"[\w$]*$", d.text(case["path"])[idx.starts[pos[0]]:idx.offset(tuple(pos))]).group()
    hint = lambda i: IMPORT_HINT.search(json.dumps([i.get("labelDetails"), i.get("detail"), i.get("data")]))  # noqa
    order = lambda i: (not str(i.get("filterText") or i.get("label", "")).startswith(prefix), not hint(i),  # noqa: E731
                       str(i.get("sortText") or i.get("label", "")), str(i.get("label", "")))
    return with_occurrence(sorted((i for i in items if isinstance(i, dict)), key=order),
                           lambda i: (str(i.get("label", "")), str(i.get("kind", "")),
                                      json.dumps(i.get("labelDetails"), sort_keys=True), str(i.get("sortText", ""))))


def handle_edit(sub: str, d: Driver, minted: Dict, resolved: Any, fields: Optional[Set[str]]
                ) -> Tuple[List, Dict, Set[str]]:
    """(edit entries, versions named, fields). Completion, stale side (fields None): what the
    resolve produced; fresh side: the same fields of the fresh item."""
    if sub == "codeAction":
        return (*edit_entries(resolved.get("edit") if isinstance(resolved, dict) else None, d.mapper.rel), set())
    got = resolve_produced(minted, resolved) if fields is None else \
        {k: v for k, v in completion_edits(resolved).items() if k in fields}
    return flatten(got), {}, set(got) if fields is None else fields


# sub -> (key method, resolve request, mint, a fresh handle resolving to no edit is comparable)
HANDLES: Dict[str, Tuple[str, str, Callable[..., Dict[Ident, Dict]], bool]] = {
    "codeAction": ("codeActionResolve", "codeAction/resolve", mint_actions, False),
    "completion": ("completionResolve", "completionItem/resolve", mint_items, True)}


def apply_check(ctx: OracleContext, d: Driver, key: QueryKey, path: str, edits: List[List[Any]]) -> Optional[Obs]:
    """A stale edit without a comparable fresh one, applied to the current text of `path`."""
    k2, text = QueryKey(key.method + "Apply", key.path, key.line, key.character, key.extra), d.text(path)
    try:
        after, mod = apply_text_edits(text, edits), importlib.import_module(f"{__package__}.syntax")
    except OpError as exc:
        return Obs(k2, [], ["cannot apply: " + str(exc)[:120]], note="stale edit does not fit the current text")
    except ImportError:
        return None
    try:  # syntax.syntax_errors -> ["L:C: message"]; syntax.new_errors ignores positions
        before, now = ([str(x) for x in mod.syntax_errors(ctx.language, t, path) or []] for t in (text, after))
    except (OSError, ValueError, RuntimeError, AttributeError) as exc:
        logger.warning("syntax check failed on %s: %s", path, exc)
        return None
    worse = mod.new_errors(before, now) if hasattr(mod, "new_errors") else now[len(before):]
    return Obs(k2, before[:5], (before + list(worse))[:5] if worse else before[:5], note="syntax after the stale edit")


def edit_op(path: str, s: Dict[str, Any]) -> Op:
    return Op("change", path, (s["line"], s["col"]), (s["line"], s["col"]), s["text"])


def handle_case(ctx: OracleContext, d: Driver, case: Dict[str, Any]) -> Optional[List[Obs]]:
    """One code-action or completion case; None when its edit could not be applied or settled."""
    (method, res, mint, empty_counts), sub = HANDLES[case["sub"]], case["sub"]
    path, sh, where, t = case["path"], case["shift"], list(case["where"]), ctx.request_timeout_s
    probed = []
    for ident, h in list(mint(ctx, d, case, where).items())[:PROBE_CAP]:
        result, err = d.request(res, h, t)
        probed.append((ident, h, [] if err else handle_edit(sub, d, h, result, None)[0]))
    keep = [p for p in probed if p[2]][:KEEP_CAP] or probed[:2]
    if not keep:
        return []
    e = Shifted(ctx, d, edit_op(path, sh))
    stale = [(ident, h, *d.request(res, h, t)) for ident, h, _ in keep] if e.ok else []
    if not (e.ok and e.settle_race()):
        e.revert()
        return None
    olds = {ident: ([], {}, set()) if err else handle_edit(sub, d, h, result, None) for ident, h, result, err in stale}
    fresh: Dict[Ident, List[Optional[List[Any]]]] = {ident: [] for ident in olds}
    for _ in range(2):  # mint, then resolve at once: a server may keep only its latest list resolvable
        minted = mint(ctx, d, case, [x for i in range(0, len(where), 2) for x in map_pos(where[i:i + 2], sh)])
        for ident, got in olds.items():
            fres, ferr = d.request(res, minted[ident], t) if ident in minted else (None, ("error", "absent"))
            new = None if ferr else handle_edit(sub, d, minted[ident], fres, got[2])[0]
            fresh[ident].append(new if new or (new is not None and empty_counts) else None)
    current, obs = {p: d.store.docs[p].version for p in d.store.open_paths()}, []
    tag = [case["extra"] + "".join(f":{x}" for x in where[2:]), f"{sh['variant']}{sh['text'].count(chr(10))}"]
    for ident, h, result, err in stale:
        key = QueryKey(method, path, where[0], where[1], "|".join(tag + list(ident)))
        entries, versions, fields = olds[ident]
        obs.append(judge_edit(key, entries, err, versions, current, fresh[ident]))
        if obs[-1].allowed == "no comparable fresh edit":
            mine = [x[1:5] + [x[-1]] for x in entries if x[0] in (path, "textEdit", "additionalTextEdits")]
            obs += [a for a in [apply_check(ctx, d, key, path, mine)] if a]
    e.revert()
    return obs


def tokens_case(ctx: OracleContext, d: Driver, case: Dict[str, Any]) -> Optional[List[Obs]]:
    """Two rounds (the edit, then its inverse) of delta-vs-full; None if the edit did not settle."""
    path, ed, t, original = case["path"], case["shift"], ctx.request_timeout_s, d.text(case["path"])
    doc, ntx = {"textDocument": {"uri": d.uri(path)}}, d.norm_context(50)
    first, err = d.request(FULL, doc, t)
    if err or not isinstance(first, dict) or not first.get("resultId") or not isinstance(first.get("data"), list):
        return []
    prev, rid, op, obs = first["data"], first["resultId"], edit_op(path, ed), []
    for rnd in (0, 1):
        e = Shifted(ctx, d, op)
        delta, derr = d.request(DELTA, dict(doc, previousResultId=rid), t) if e.ok else (None, None)
        if not (e.ok and e.settle_race()):
            break
        fa, fb = (d.request(FULL, doc, t)[0] for _ in range(2))
        key = QueryKey("semanticTokensDelta", path, ed["line"], ed["col"], f"{ed['variant']}|round{rnd}")
        full = fa.get("data") if isinstance(fa, dict) else None
        want = NORMALIZERS["semanticTokens"]({"data": full}, ntx) or []
        try:
            data = apply_delta(prev, delta["edits"]) if "edits" in delta else delta["data"]
            got: Any = NORMALIZERS["semanticTokens"]({"data": data}, ntx)
        except (ValueError, TypeError, KeyError) as exc:
            got = None if derr or delta is None else ["invalid-delta", str(exc)[:120]]
        if got is None:
            obs.append(Obs(key, None, None, allowed=f"error:{derr[1]}" if derr else "null delta"))
        else:
            exp, act = token_window(want, got) if got[:1] != ["invalid-delta"] else (want[:5], got)
            obs.append(Obs(key, exp, act, isinstance(fb, dict) and fb.get("data") == full, note=f"{len(want)} tokens"))
        if not (isinstance(fb, dict) and fb.get("resultId") and isinstance(fb.get("data"), list)):
            break
        prev, rid, op = fb["data"], fb["resultId"], inverse_change(op, e.before)  # round 1 reverts the edit
    if d.text(path) != original:  # an interrupted round: put the original text back
        d.apply(Op("change", path, (0, 0), LineIndex(d.text(path)).end(), original))
        d.settle()
    return obs or None


CASES: Dict[str, Callable[[OracleContext, Driver, Dict[str, Any]], Optional[List[Obs]]]] = {
    "codeAction": handle_case, "completion": handle_case, "tokens": tokens_case}


def plan_cases(ctx: OracleContext, d: Driver, caps: Dict[str, bool]) -> List[Dict[str, Any]]:
    """One token case per file first, then handle cases alternating kinds, up to max_cases."""
    rng, tokens = random.Random(f"r2:{ctx.seed}"), []
    lanes: Dict[str, List[Dict[str, Any]]] = {"codeAction": [], "completion": []}
    for ft in ctx.targets:
        text, eol = d.text(ft.path), ("\r\n" if "\r\n" in d.text(ft.path) else "\n")
        shift = lambda line: make_shift(text, line, rng.choice(SHIFTS), rng.randint(1, 2))  # noqa: E731
        if caps["delta"] and ft.positions:
            i, variant = rng.randrange(len(ft.positions)), rng.choice(("blank", "comment", "ident"))
            ed = {"line": ft.ends[i][0], "col": ft.ends[i][1], "text": "Zq"} if variant == "ident" else \
                {"line": ft.positions[i][0], "col": 0, "text": eol * rng.randint(1, 2) if variant == "blank" else
                 ("# probe" if FAMILY.get(ctx.language) == "py" else "// probe") + eol}
            tokens.append({"sub": "tokens", "path": ft.path, "shift": dict(ed, variant=variant)})
        for pos, end in zip(ft.positions, ft.ends):
            lanes["codeAction"] += [{"sub": "codeAction", "path": ft.path, "where": [*pos, *pos], "extra": "pos",
                                     "shift": shift(pos[0])}] if caps["codeAction"] else []
            lanes["completion"] += [{"sub": "completion", "path": ft.path, "where": list(end), "extra": "end",
                                     "shift": shift(end[0])}] if caps["completion"] else []
        for r in diagnostic_ranges(raw_diagnostics(ctx, d, ft.path)) if caps["codeAction"] else ():
            lanes["codeAction"].append({"sub": "codeAction", "path": ft.path, "where": list(r), "extra": "diag",
                                        "shift": shift(r[0])})
    for lane in lanes.values():
        rng.shuffle(lane)
    mixed = [c for pair in itertools.zip_longest(*lanes.values()) for c in pair if c]
    return tokens[:ctx.max_cases] + mixed[:max(0, ctx.max_cases - len(tokens))]


@register_oracle(ORACLE)
class R2Handles:
    name = ORACLE

    def applies_to(self, server_kind: str) -> bool:
        return server_kind in SERVER_LANGUAGE or server_kind == "jdtls"

    def run(self, ctx: OracleContext) -> OracleResult:
        t0, res, allowed = time.monotonic(), OracleResult(ORACLE, ctx.run_id), {}  # type: ignore[var-annotated]
        try:
            with session(ctx, "r2") as d:
                res.sessions += 1
                d.open(*[t.path for t in ctx.targets])
                caps = handle_caps(d) if d.settle().settled else None
                res.unsettled += int(caps is None)
                res.notes.append(f"handle kinds: {caps}")
                for case in plan_cases(ctx, d, caps) if caps else []:
                    res.cases += 1
                    obs = CASES[case["sub"]](ctx, d, case)
                    res.invalid_cases += int(obs is None)
                    for o in obs or []:
                        self._tally(ctx, res, case, o, allowed)
        except SESSION_ERRORS as exc:
            res.notes.append(f"session failed: {type(exc).__name__}: {exc}"[:300])
        res.notes += [f"allowed {k}: {n}" for k, n in sorted(allowed.items())]
        res.seconds = round(time.monotonic() - t0, 3)
        return res

    @staticmethod
    def _tally(ctx: OracleContext, res: OracleResult, case: Dict[str, Any], o: Obs, allowed: Dict[str, int]) -> None:
        m = o.key.method
        if o.allowed:
            allowed[f"{m} {o.allowed}"] = allowed.get(f"{m} {o.allowed}", 0) + 1
        elif not o.stable:
            res.unstable[m] = res.unstable.get(m, 0) + 1
        else:
            res.compared[m] = res.compared.get(m, 0) + 1
            if o.expected != o.actual:
                ops = [Op("open", case["path"]), edit_op(case["path"], case["shift"])]
                res.candidates.append(make_violation(ctx, ORACLE, o.key, o.expected, o.actual, ops, case, o.note))

    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        t0, case, obs, ok = time.monotonic(), case_of(v), None, False
        if ops is not None and not any(o.kind == "change" for o in ops):  # without its edit the case cannot arm
            return ReplayOutcome(True, True, False, None, 0.0)
        try:
            with session(ctx, "r2-replay") as d:
                d.open(*[t.path for t in ctx.targets])
                ok = d.settle().settled
                obs = CASES[case["sub"]](ctx, d, case) if ok else None
        except SESSION_ERRORS as exc:
            logger.warning("%s replay failed: %s", ORACLE, exc)
        o = next((x for x in obs or [] if x.key == v.key), None)
        diff = o is not None and not o.allowed and o.stable and o.expected != o.actual
        seen = make_violation(ctx, ORACLE, v.key, o.expected, o.actual, v.ops, case, "replay") if diff else None
        return ReplayOutcome(ok and obs is not None, o is not None and o.stable, seen is not None and
                             shape_of(seen) == shape_of(v), seen, round(time.monotonic() - t0, 3))


__all__ = ["HANDLES", "Obs", "R2Handles", "apply_delta", "completion_edits", "edit_entries", "flatten",
           "handle_edit", "judge_edit", "make_shift", "map_pos", "plan_cases", "resolve_produced", "token_window",
           "with_occurrence"]
