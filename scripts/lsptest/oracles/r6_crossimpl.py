"""R6 cross-implementation oracle, TypeScript only (plan/tool_design_v1.md section 5).

The server under test (ts6 6.0.3 or ts7 7.0.2) and the other implementation (REFERENCE)
each get a fresh baseline and a fresh control on the same project and targets (the
fresh_pair protocol, run through base.run_session so that the query suite is limited to
the compared methods and keeps the raw answers). Keys stable in both implementations are
compared after canonicalization:

- diagnostics: code + range (severity, source and message ignored);
- hover: the type text, i.e. the first fenced code block of the hover (later blocks are
  documentation, e.g. ts6 fences JSDoc @default values), without the alias echo line
  ("import X" after an "(alias)" line; typescript-language-server prints it, TS 7 does
  not), whitespace collapsed; ranges ignored;
- definition: locations; TypeScript library files map to "<tslib>/<file name>" (TS 6
  resolves them under its install, TS 7 under its own package or as bundled URIs) and
  are compared by the declared name at the target range, since the two lib versions
  differ in line numbers;
- completion: the full label set of the in-scope items. Auto-import suggestions are
  excluded with the engine's own marker (completion_kind.is_auto_import, the rule of the
  completion normalizer): which ones a server offers depends on index warmth and on each
  implementation's auto-import policy. The note of each run counts the positions where
  the excluded auto-import sets differ.

A key counts as stable for an implementation when its compared form is equal in that
implementation's fresh baseline and control (neither lost to a timeout or a dead server).

Each difference is a candidate (expected = the reference implementation's answer,
actual = the server under test) with no ops; the case records the reference and the
documented intended differences (oracles/r6_intended.py, typescript-go CHANGES.md) that
may explain it. replay() repeats both pairs on the key's file and position only.

Run line: loaded by oracles.load_all(); python3 scripts/lsptest/pilot_r4_r6.py runs it.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from completion_kind import is_auto_import as engine_auto_import  # noqa: E402
from model import Op, QueryKey, QueryResult, Snapshot, Violation  # noqa: E402
from oracles.base import (LIVENESS_ERRORS, OracleContext, OracleResult, ReplayOutcome, SessionInfo,  # noqa: E402
                          case_of, difference_shape, make_violation, register_oracle, run_session, shape_of)
from framing import LspError  # noqa: E402  (lsp_repro is on sys.path once base is imported)
from oracles.r6_intended import SOURCE, Candidate, project_strict, tag  # noqa: E402
from queries import QueryConfig  # noqa: E402
from targets import FileTargets  # noqa: E402

logger = logging.getLogger(__name__)

REFERENCE: Dict[str, Tuple[str, str]] = {"ts7": ("ts6", "6.0.3"), "ts6": ("ts7", "7.0.2")}
R6_METHODS = ("diagnostics", "hover", "definition", "completion")
QCFG = QueryConfig(methods=R6_METHODS, keep_raw=True, completion_top=1_000_000)
REPO = os.path.abspath(os.path.join(PKG, "..", ".."))
TS_LIB_DIRS: Dict[str, str] = {  # each implementation's lib files on disk (bundled URIs are read from here)
    "ts6": os.path.join(REPO, "temp", "lsp_servers", "ts6-6.0.3", "node_modules", "typescript", "lib"),
    "ts7": os.path.join(REPO, "temp", "lsp_servers", "ts7-7.0.2", "node_modules", "@typescript",
                        "typescript-darwin-arm64", "lib"),
}
_TSLIB = re.compile(r"(?:^|/)(?:node_modules/typescript/lib|node_modules/@typescript/[^/]+/lib|bundled:/*libs?)/"
                    r"(lib(?:\.[\w-]+)*\.d\.ts)$")
_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
_ALIAS_ECHO = re.compile(r"^\s*(import|export)\b")
FAILURES = (LspError, OSError, RuntimeError, ValueError, subprocess.SubprocessError)


# ------------------------------------------------------------------ canonical forms
def tslib_name(path: str) -> Optional[str]:
    m = _TSLIB.search(path.replace("\\", "/"))
    return m.group(1) if m else None


def canon_path(path: str) -> str:
    name = tslib_name(path)
    return f"<tslib>/{name}" if name else path


def lib_text(path: str, kind: str, rng: Sequence[Any]) -> str:
    """Declared name at a location in a TypeScript lib file ("" when the file is not on disk)."""
    name = tslib_name(path) or ""
    cand = path if os.path.isabs(path) and os.path.isfile(path) else os.path.join(TS_LIB_DIRS.get(kind, ""), name)
    try:
        with open(cand, "r", encoding="utf-8", errors="replace") as f:
            rows = f.read().splitlines()
        sl, sc, el, ec = (int(x) for x in rng)
    except (OSError, ValueError):
        return ""
    return rows[sl][sc : ec if el == sl else None].strip() if 0 <= sl < len(rows) else ""


def _markup(contents: Any) -> str:
    if isinstance(contents, list):
        return "\n".join(_markup(c) for c in contents)
    if isinstance(contents, dict):
        value = str(contents.get("value", ""))
        return f"```\n{value}\n```" if "language" in contents else value
    return "" if contents is None else str(contents)


def canon_hover(res: QueryResult) -> Any:
    if not isinstance(res.raw, dict):
        norm = res.norm
        return None if norm is None else " ".join(str(norm[0] if isinstance(norm, list) else norm).split()) or None
    text = _markup(res.raw.get("contents"))
    blocks = _FENCE.findall(text)  # the first block is the signature; later ones are documentation (@default ...)
    lines = [ln for ln in (blocks[0] if blocks else text).splitlines() if ln.strip()]
    if lines and lines[0].lstrip().startswith("(alias)"):
        lines = [lines[0]] + [ln for ln in lines[1:] if not _ALIAS_ECHO.match(ln)]
    return " ".join(" ".join(lines).split()) or None


def is_auto_import(item: Dict[str, Any]) -> bool:
    """Auto-import suggestion, by the engine's marker (the completion normalizer's rule)."""
    return engine_auto_import(item)


def completion_sets(res: QueryResult) -> Tuple[List[str], List[str]]:
    """(in-scope labels, auto-import labels); without raw items every label counts as in scope."""
    raw = res.raw.get("items") if isinstance(res.raw, dict) else res.raw
    if not isinstance(raw, list):
        return sorted(set(str(x) for x in res.norm or [])), []
    items = [i for i in raw if isinstance(i, dict)]
    scope = sorted({str(i.get("label", "")) for i in items if not is_auto_import(i)})
    return scope, sorted({str(i.get("label", "")) for i in items if is_auto_import(i)})


def canonical(key: QueryKey, res: QueryResult, kind: str) -> Any:
    """The compared form of one answer; errors stay ["error", code]."""
    if res.error is not None:
        return list(res.error)
    norm = res.norm
    if key.method == "completion":
        return completion_sets(res)[0]
    if key.method == "hover":
        return canon_hover(res)
    if key.method == "diagnostics" and isinstance(norm, list):  # code + range; shape-compatible 8-field rows
        rows = {json.dumps([*d[:4], 0, d[5], "", ""]) for d in norm if isinstance(d, list) and len(d) >= 6}
        return [json.loads(x) for x in sorted(rows)]
    if key.method == "definition" and isinstance(norm, list):
        locs = [[canon_path(str(x[0])), lib_text(str(x[0]), kind, x[1:5])] if isinstance(x, list) and x and
                tslib_name(str(x[0])) else x for x in norm]
        return sorted(locs, key=lambda x: json.dumps(x))
    return norm


def canonical_stable(b: Snapshot, c: Snapshot, kind: str) -> Set[QueryKey]:
    """Keys whose compared form is equal in a fresh baseline and control (both settled; not lost
    to a timeout or a dead server)."""
    if not (b.settled and c.settled):
        return set()
    lost = lambda r: r.error is not None and r.error[1] in LIVENESS_ERRORS  # noqa: E731
    return {k for k, r in b.results.items() if k in c.results and not lost(r) and not lost(c.results[k])
            and canonical(k, r, kind) == canonical(k, c.results[k], kind)}


# ------------------------------------------------------------------ sessions
def reference_context(ctx: OracleContext) -> OracleContext:
    kind, version = REFERENCE[ctx.server_kind]
    return dataclasses.replace(ctx, server_kind=kind, server_version=version, run_id=f"{ctx.run_id}-ref")


def fresh_pair_raw(ctx: OracleContext, label: str) -> Tuple[Snapshot, Snapshot, Set[QueryKey], List[SessionInfo]]:
    """base.fresh_pair with QCFG (compared methods only, raw answers kept) and stability judged
    on the compared forms (canonical_stable)."""
    b, ib = run_session(ctx, f"{label}-baseline", qcfg=QCFG)
    c, ic = run_session(ctx, f"{label}-control", qcfg=QCFG)
    return b, c, canonical_stable(b, c, ctx.server_kind), [ib, ic]


def _differing(method: str, exp: Any, act: Any) -> Tuple[List[int], List[str]]:
    """Lines and diagnostic codes involved in a difference (for the intended-difference rules)."""
    if method != "diagnostics" or not isinstance(exp, list) or not isinstance(act, list):
        return [], []
    items = [json.loads(x) for x in sorted({json.dumps(x) for x in exp} ^ {json.dumps(x) for x in act})]
    return sorted({int(x[0]) for x in items}), sorted({str(x[5]) for x in items})


def _read(ctx: OracleContext, path: str) -> str:
    try:
        with open(os.path.join(ctx.project_dir, path), "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


@register_oracle("r6_crossimpl")
class CrossImplementation:
    name = "r6_crossimpl"

    def applies_to(self, server_kind: str) -> bool:
        return server_kind in REFERENCE

    def run(self, ctx: OracleContext) -> OracleResult:
        t0, res = time.monotonic(), OracleResult(self.name, ctx.run_id)
        if not self.applies_to(ctx.server_kind):
            res.notes.append(f"r6 applies to {sorted(REFERENCE)} only")
            return res
        ref = reference_context(ctx)
        try:
            a_b, _, stable_a, infos_a = fresh_pair_raw(ctx, "r6-test")
            b_b, _, stable_b, infos_b = fresh_pair_raw(ref, "r6-ref")
        except FAILURES as exc:
            res.notes.append(f"session failed: {type(exc).__name__}: {exc}"[:300])
            res.seconds = round(time.monotonic() - t0, 2)
            return res
        res.sessions = 4
        res.unsettled = sum(1 for i in infos_a + infos_b if not i.settled)
        strict = project_strict(ctx.project_dir)
        keys = set(a_b.results) | set(b_b.results)
        auto_diff = 0
        for k in sorted(keys, key=lambda q: (q.method, q.path, q.line, q.character, q.extra)):
            if k not in stable_a or k not in stable_b:
                res.unstable[k.method] = res.unstable.get(k.method, 0) + 1
                continue
            res.compared[k.method] = res.compared.get(k.method, 0) + 1
            exp, act = canonical(k, b_b.results[k], ref.server_kind), canonical(k, a_b.results[k], ctx.server_kind)
            if exp != act:
                res.candidates.append(self._candidate(ctx, ref, k, exp, act, strict))
            if k.method == "completion":
                auto_diff += completion_sets(b_b.results[k])[1] != completion_sets(a_b.results[k])[1]
        res.cases = len({(k.path, k.line, k.character) for k in keys})
        res.notes.append(f"reference {ref.server}; intended differences from {SOURCE['url']} "
                         f"(sha256 {SOURCE['sha256'][:12]}, fetched {SOURCE['fetched']})")
        res.notes.append(f"completion compares in-scope labels only: auto-import suggestions are excluded "
                         f"(completion_kind.is_auto_import, as the completion normalizer); their sets differed at "
                         f"{auto_diff} of {res.compared.get('completion', 0)} compared completion positions")
        res.notes.append(f"settled: test {[i.settled for i in infos_a]}, reference {[i.settled for i in infos_b]}")
        res.seconds = round(time.monotonic() - t0, 2)
        return res

    def _candidate(self, ctx: OracleContext, ref: OracleContext, k: QueryKey, exp: Any, act: Any,
                   strict: Optional[bool]) -> Violation:
        lines, codes = _differing(k.method, exp, act)
        cand = Candidate(k.method, k.path, _read(ctx, k.path), lines or ([k.line] if k.line >= 0 else []), codes, strict)
        intended = tag(cand)
        only = lambda a, b: sorted(set(map(json.dumps, a)) - set(map(json.dumps, b)))[:8] \
            if isinstance(a, list) and isinstance(b, list) else None  # noqa: E731
        case = {"reference": {"kind": ref.server_kind, "version": ref.server_version}, "method": k.method,
                "intended": intended, "intended_source": SOURCE["sha256"],
                "only_reference": only(exp, act), "only_test": only(act, exp)}
        note = (f"{ctx.server} and {ref.server} differ on {k.method} at {k.path}:{k.line + 1}:{k.character + 1}"
                + (f"; documented intended difference(s): {[t['rule'] for t in intended]}" if intended else
                   "; no documented intended difference matches"))
        return make_violation(ctx, self.name, k, exp, act, [], case, note)

    # ------------------------------------------------------------------ replay
    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        t0, query = time.monotonic(), v.key
        pos = (query.line, query.character)
        ft = FileTargets(query.path, (pos,) if query.method in ("hover", "definition") else (),
                         (pos,) if query.method == "completion" else (), ())
        test = dataclasses.replace(ctx, targets=(ft,))
        ref = dataclasses.replace(reference_context(ctx), targets=(ft,))
        try:
            a_b, _, stable_a, infos_a = fresh_pair_raw(test, "r6-replay-test")
            b_b, _, stable_b, infos_b = fresh_pair_raw(ref, "r6-replay-ref")
        except FAILURES as exc:
            logger.warning("r6 replay of %s failed: %s", v.signature, exc)
            return ReplayOutcome(False, False, False, None, round(time.monotonic() - t0, 2))
        settled = all(i.settled for i in infos_a + infos_b)
        stable = query in stable_a and query in stable_b
        if query not in a_b.results or query not in b_b.results:
            return ReplayOutcome(settled, stable, False, None, round(time.monotonic() - t0, 2))
        exp = canonical(query, b_b.results[query], ref.server_kind)
        act = canonical(query, a_b.results[query], ctx.server_kind)
        same = exp != act and difference_shape(v.key.method, exp, act) == shape_of(v)
        observed = make_violation(ctx, self.name, v.key, exp, act, [], case_of(v), "replayed") if same else None
        return ReplayOutcome(settled, stable, same, observed, round(time.monotonic() - t0, 2))


__all__ = ["CrossImplementation", "QCFG", "R6_METHODS", "REFERENCE", "canon_hover", "canon_path", "canonical",
           "canonical_stable", "completion_sets", "fresh_pair_raw", "is_auto_import", "lib_text", "reference_context",
           "tslib_name"]
