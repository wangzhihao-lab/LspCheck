"""R5 semantics-preserving transformations (plan/tool_design_v1.md sections 5 and 10).

A fresh pair on the original project gives the stable keys; each case is one fresh session on a
materialized copy with one target file transformed. T1 inserts k blank lines, T2 a blank line, a
comment line and a blank line (never a doc comment, never glued to the import block), both at the
first top-level statement boundary after the import block (shebangs, encoding lines, build tags,
pragmas, triple-slash directives, package clauses, inner attributes, module docstrings stay above;
the next declaration's doc comments below). T3 appends whitespace to code line ends below that
point (not in strings or comments, not after a continuation backslash; the import block is left
alone: gopls offers Organize Imports whenever goimports would reformat it). T4 turns LF into CRLF
(files without CR; identity mapping). T5 toggles the final newline (end of file with and without
it read as one position). T6 puts `/* 注释🙂 */ ` mid-line before a target identifier (block-comment
languages; not in JSX files, not after `#@$` or a quote, not on attribute or package lines);
positions after it on that line move by its UTF-16 width, 11 (the emoji counts 2). A range end at
an insertion point stays; entries inside inserted text are dropped from the transformed answer;
digits in diagnostic messages are masked. Violation.ops rebuild the file (reduce.py shrinks T3/T4).

Run line: imported through oracles.load_all() by campaign.py, flake.py and reduce.py; not run directly.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import random
import re
import subprocess
import time
import warnings
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .base import (MISSING, OracleContext, OracleResult, ReplayOutcome, case_of, discard, final_state, fresh_pair,
                   make_violation, materialize, register_oracle, run_session, shape_of, stable_keys)
from .r3_routes import failed, key_query, key_targets
from model import Op, QueryKey, Snapshot, Violation  # noqa: E402
from ops import LineIndex, OpError, read_text, utf16_len  # noqa: E402
from queries import QueryConfig, key_sort  # noqa: E402
from targets import FAMILY, SERVER_LANGUAGE, FileTargets, identifiers  # noqa: E402

logger = logging.getLogger(__name__)
ORACLE = "r5_transforms"
KINDS = ("T1", "T2", "T3", "T4", "T5", "T6")
COMMENTS = dict({f: "// inserted comment line" for f in ("js", "go", "rs")}, py="# inserted comment line")
INLINE, WHITESPACE, SENTINEL = "/* 注释🙂 */ ", (" ", "\t", "  \t"), "ZqEolSentinel"
_DIGITS, _DIAG_EXTRA, BIG = re.compile(r"\d+"), re.compile(r"^diag:(\d+):(\d+)$"), 1 << 30


# ------------------------------------------------------------------ mapping
@dataclass(frozen=True)
class Shift:
    """Text inserted at (line, col) of `path`: n line breaks, last line w UTF-16 units (T1/T2: n
    lines at (L, 0); T6: w units at (L, C)); eof = (l, c, l2, c2) reads (l, c) as (l2, c2) (T5)."""

    path: str
    line: int = -1
    col: int = 0
    n: int = 0
    w: int = 0
    eof: Tuple[int, ...] = ()

    def pos(self, line: int, ch: int) -> Tuple[int, int]:
        if self.eof and (line, ch) == tuple(self.eof[:2]):
            return self.eof[2], self.eof[3]
        if self.line < 0 or (line, ch) < (self.line, self.col):
            return line, ch
        return (line + self.n, (ch - self.col + self.w) if self.n else ch + self.w) if line == self.line \
            else (line + self.n, ch)

    def rng(self, r: Sequence[int]) -> List[int]:
        sl, sc, el, ec = (int(x) for x in r[:4])
        keep_end = (el, ec) == (self.line, self.col) and (sl, sc) < (self.line, self.col)
        return list(self.pos(sl, sc)) + list((el, ec) if keep_end else self.pos(el, ec))

    def inserted(self, sl: int, sc: int, el: int, ec: int) -> bool:
        """Whether an entry of the transformed answer lies inside the inserted text."""
        start, end = (self.line, self.col), (self.line + self.n, self.w if self.n else self.col + self.w)
        return self.line >= 0 and start < end and start <= (sl, sc) < end and (el, ec) <= end


_LOC = (lambda x, p: (x[0], *x[1:5]), lambda x, s: [x[0]] + (s.rng(x[1:5]) if x[0] == s.path else x[1:5]))
_RANGE_FIRST = (lambda x, p: (p, *x[:4]), lambda x, s: s.rng(x[:4]) + list(x[4:]))
# method -> ((entry, key path) -> (file, sl, sc, el, ec), (entry, shift) -> mapped entry)
ENTRIES: Dict[str, Tuple[Callable[[List[Any], str], Tuple[Any, ...]], Callable[[List[Any], Shift], List[Any]]]] = {
    "diagnostics": _RANGE_FIRST, "documentHighlight": _RANGE_FIRST,
    "definition": _LOC, "typeDefinition": _LOC, "references": _LOC,
    "semanticTokens": (lambda x, p: (p, x[0], x[1], x[0], x[1] + x[2]), lambda x, s: [*s.pos(x[0], x[1]), *x[2:]]),
    "inlayHint": (lambda x, p: (p, x[0], x[1], x[0], x[1]), lambda x, s: [*s.pos(x[0], x[1]), *x[2:]]),
    "documentSymbol": (lambda x, p: (p, *x[2:6]), lambda x, s: list(x[:2]) + s.rng(x[2:6])),
    "foldingRange": (lambda x, p: (p, x[0], 0, x[2], BIG),  # end line inclusive; characters only if given (>= 0)
                     lambda x, s: [v if o >= 0 else o for v, o in zip(
                         (*s.pos(x[0], max(x[1], 0)), *s.pos(x[2], max(x[3], 0))), (0, x[1], 0, x[3]))] + x[4:]),
}
PER_FILE = frozenset(ENTRIES) - {"definition", "typeDefinition", "references"}


def map_norm(method: str, norm: Any, path: str, s: Shift) -> Any:
    """An answer expressed in the other side's coordinates."""
    if failed(norm) or not isinstance(norm, list) or (method in PER_FILE and path != s.path):
        return norm
    if method == "hover":
        return [norm[0], s.rng(norm[1]) if norm[1] and path == s.path else norm[1]]
    return [ENTRIES[method][1](x, s) for x in norm] if method in ENTRIES else norm


def drop_inserted(method: str, norm: Any, path: str, s: Shift) -> Any:
    """A transformed answer without the entries that lie inside the inserted text."""
    if method not in ENTRIES or failed(norm) or not isinstance(norm, list):
        return norm
    at = ENTRIES[method][0]
    return [x for x in norm if not (at(x, path)[0] == s.path and s.inserted(*at(x, path)[1:]))]


def canonical(method: str, norm: Any) -> Any:
    """Digits masked in diagnostic messages; entry lists in one order for both sides."""
    if failed(norm) or not isinstance(norm, list) or method == "hover":
        return norm
    if method == "diagnostics":
        norm = [list(x[:7]) + [_DIGITS.sub("#", str(x[7]))] for x in norm]
    return sorted(norm, key=lambda x: json.dumps(x, sort_keys=True))


def map_key(k: QueryKey, s: Shift) -> QueryKey:
    if k.path != s.path or k.line < 0:
        return k
    m = _DIAG_EXTRA.match(k.extra)
    extra = "diag:{}:{}".format(*s.rng([k.line, k.character, int(m.group(1)), int(m.group(2))])[2:]) if m else k.extra
    return QueryKey(k.method, k.path, *s.pos(k.line, k.character), extra)


def map_targets(targets: Sequence[FileTargets], s: Shift) -> Tuple[FileTargets, ...]:
    return tuple(FileTargets(t.path, tuple(s.pos(*p) for p in t.positions), tuple(s.pos(*p) for p in t.ends), t.names)
                 if t.path == s.path else t for t in targets)


def compare_mapped(base: Snapshot, trans: Snapshot, keys: Iterable[QueryKey], s: Shift, back: Optional[Shift] = None
                   ) -> List[Tuple[QueryKey, Any, Any]]:
    """(original key, mapped expected, transformed actual read back) for every key that differs."""
    out, back = [], back or Shift("")
    for k in sorted(keys, key=key_sort):
        exp = canonical(k.method, map_norm(k.method, base.results[k].norm, k.path, s))
        r = trans.results.get(map_key(k, s))
        act = MISSING if r is None else \
            canonical(k.method, map_norm(k.method, drop_inserted(k.method, r.norm, k.path, s), k.path, back))
        if exp != act:
            out.append((k, exp, act))
    return out


# ------------------------------------------------------------------ where to transform
def _py_insertion(text: str) -> Optional[int]:
    """After the module docstring and the leading imports; else before the first statement."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            body = ast.parse(text).body
    except (SyntaxError, ValueError):
        return None
    i = int(bool(body) and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0].value, "value", None), str))
    while i < len(body) and isinstance(body[i], (ast.Import, ast.ImportFrom)):
        i += 1
    if i > 0:
        return body[i - 1].end_lineno  # 1-based last line == 0-based index of the next line
    return min([body[0].lineno] + [d.lineno for d in getattr(body[0], "decorator_list", [])]) - 1 if body else None


def _strip_comment(line: str) -> str:
    """The line up to a // comment that is not inside a quoted string."""
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            quote = "" if ch == quote and line[i - 1] != "\\" else quote
        elif ch in "'\"`":
            quote = ch
        elif line.startswith("//", i):
            return line[:i]
    return line


def _until(lines: List[str], i: int, done: Callable[[str, int], bool], cap: int = 400) -> Optional[int]:
    """First j >= i where done(accumulated code, bracket depth) holds."""
    acc, depth = "", 0
    for j in range(i, min(len(lines), i + cap)):
        code = _strip_comment(lines[j])
        acc, depth = acc + code + "\n", depth + sum(code.count(c) for c in "([{") - sum(code.count(c) for c in ")]}")
        if done(acc, depth):
            return j
    return None


def _comment_end(lines: List[str], i: int) -> int:
    return next((j for j in range(i, len(lines)) if "*/" in (lines[j][lines[j].find("/*") + 2:] if j == i
                                                            else lines[j])), len(lines) - 1)


_TS_FROM = re.compile(r"""\bfrom\s*(['"])[^'"\n]*\1|^\s*import\s*(['"])|\brequire\s*\(\s*['"]""")
_TS_PRAGMA = re.compile(r"""(//|/\*+)\s*(@ts-|@jsx|@flow|@format|eslint|jshint|global\s)|(['"])use [\w -]+\3;?$""")
_RS_IMPORT = re.compile(r"(pub(\s*\([^)]*\))?\s+)?(use\s|extern\s+crate\s|mod\s+\w+\s*;)")


def _ts_import_end(lines: List[str], i: int) -> Optional[int]:
    """Last line of an import (or a re-export `export ... from`); None for `export { a }`."""
    is_export = lines[i].strip().startswith("export")
    j = _until(lines, i, lambda acc, depth: depth <= 0 and (bool(_TS_FROM.search(acc)) or is_export))
    if j is None or (is_export and not _TS_FROM.search("\n".join(_strip_comment(x) for x in lines[i:j + 1]))):
        return None
    return j


# family -> (directive(stripped, index), import start(stripped), import end(lines, i) -> last line or None)
LineRules = Tuple[Callable[[str, int], bool], Callable[[str], bool], Callable[[List[str], int], Optional[int]]]
LINE_RULES: Dict[str, LineRules] = {
    "js": (lambda s, i: (i == 0 and s.startswith("#!")) or s.startswith("///") or bool(_TS_PRAGMA.match(s)),
           lambda s: bool(re.match(r"""import(\s+|\s*[{*'"])|export\s*(\*|\{|type\s*[{*])""", s)), _ts_import_end),
    "go": (lambda s, i: s.startswith(("package ", "//go:build", "// +build")),
           lambda s: bool(re.match(r'import(\s|\(|")', s)), lambda lines, i: _until(lines, i, lambda a, d: d <= 0)),
    "rs": (lambda s, i: s.startswith(("#![", "//!", "/*!")) or (i == 0 and s.startswith("#!")),
           lambda s: bool(_RS_IMPORT.match(s)), lambda lines, i: _until(lines, i, lambda a, d: d <= 0 and ";" in a)),
}


def _scan_header(lines: List[str], rules: LineRules) -> int:
    """The line after the last directive or import; comments, attributes and decorators are
    skipped without moving the point, so they stay attached to the item below."""
    directive, import_start, import_end = rules
    last, i = -1, 0
    while i < len(lines):
        s = lines[i].strip()
        if s and directive(s, i):
            end = _comment_end(lines, i) if s.startswith("/*") else \
                (_until(lines, i, lambda a, d: d <= 0) if s.startswith("#![") else i)
            last = i = end if end is not None else i
        elif s.startswith("/*"):
            i = _comment_end(lines, i)
        elif s.startswith(("#[", "@")):
            i = _until(lines, i, lambda a, d: d <= 0) or i
        elif s and not s.startswith("//"):
            end = import_end(lines, i) if import_start(s) else None
            if end is None:
                break
            last = i = end
        i += 1
    return last + 1


def insertion_line(text: str, language: str) -> Optional[int]:
    """0-based line L: T1/T2 insert at (L, 0). None when the file offers no safe point."""
    fam, idx = FAMILY.get(language, language), LineIndex(text)
    lines = [idx.line_text(i) for i in range(len(idx.starts))]
    line = _py_insertion(text) if fam == "py" else (_scan_header(lines, LINE_RULES[fam]) if fam in LINE_RULES else None)
    return line if line is not None and line < len(idx.starts) else None


def code_line_ends(text: str, language: str) -> Set[int]:
    """Lines whose end lies in code: a sentinel identifier appended to every line survives the
    targets.py tokenizer exactly where the line does not end inside a string or comment."""
    idx, parts = LineIndex(text), []
    for ln, start in enumerate(idx.starts):
        end, nxt = idx.line_end(ln), (idx.starts[ln + 1] if ln + 1 < len(idx.starts) else len(text))
        parts.append(f"{text[start:end]} {SENTINEL}{ln}x{text[end:nxt]}")
    found = {int(t.text[len(SENTINEL):-1]) for t in identifiers("".join(parts), language)
             if t.text.startswith(SENTINEL)}
    return {ln for ln in found if idx.line_text(ln).strip() and not idx.line_text(ln).rstrip().endswith("\\")
            and not (ln == 0 and idx.line_text(0).startswith("#!"))}  # a shebang is not code


def comment_spots(text: str, language: str, ft: Optional[FileTargets]) -> List[Tuple[int, int]]:
    """T6 insertion points: starts of target identifiers with code before them on the line."""
    if ft is None or FAMILY.get(language, language) not in ("js", "go", "rs", "java") or ft.path.endswith("x"):
        return []  # no block comments in Python; JSX text would take the comment literally
    idx, out = LineIndex(text), set()
    for end, name in zip(ft.ends, ft.names):
        start = (end[0], end[1] - utf16_len(name))
        line, before = idx.line_text(end[0]).lstrip(), text[idx.starts[end[0]]:idx.offset(start)]
        if before.strip() and before[-1:] not in "#@$'\"`\\" and not line.startswith(("#", "@", "package", "/")):
            out.add(start)
    return sorted(out)


# ------------------------------------------------------------------ transformations
@dataclass(frozen=True)
class Transform:
    kind: str  # T1 ... T6
    path: str
    edits: Tuple[Tuple[Any, ...], ...]  # (sl, sc, el, ec, text), applied in order
    shift: Shift  # original answers into transformed coordinates
    back: Shift  # transformed answers read back (T5 adding a final newline)

    def ops(self) -> List[Op]:
        return [Op("open", self.path)] + [Op("change", self.path, (e[0], e[1]), (e[2], e[3]), e[4]) for e in self.edits]

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "Transform":
        sh = [Shift(**dict(d[k], eof=tuple(d[k].get("eof", ())))) for k in ("shift", "back")]
        return Transform(d["kind"], d["path"], tuple(tuple(e) for e in d["edits"]), sh[0], sh[1])


def make_transform(kind: str, path: str, text: str, language: str, rng: random.Random,
                   ft: Optional[FileTargets] = None) -> Optional[Transform]:
    idx, eol, same = LineIndex(text), ("\r\n" if "\r\n" in text else "\n"), Shift(path)
    last, end = len(idx.starts) - 1, idx.end()
    if kind in ("T3", "T4"):  # insertions at line ends: T3 whitespace on code lines, T4 a CR before every LF
        lines = sorted(x for x in code_line_ends(text, language) if x >= (insertion_line(text, language) or 0)) \
            if kind == "T3" else [] if "\r" in text else range(last)
        at = [(ln, utf16_len(idx.line_text(ln))) for ln in lines]
        piece = rng.choice(WHITESPACE) if kind == "T3" else "\r"
        return Transform(kind, path, tuple((*p, *p, piece) for p in at), same, same) if at else None
    if kind == "T5" and last > 0 and not idx.line_text(last):  # remove the final line break
        prev = (last - 1, utf16_len(idx.line_text(last - 1)))
        return Transform(kind, path, ((*prev, last, 0, ""),), Shift(path, eof=(last, 0, *prev)), same)
    if kind == "T5":  # add one
        return Transform(kind, path, ((*end, *end, eol),), same, Shift(path, eof=(end[0] + 1, 0, *end)))
    spots = comment_spots(text, language, ft) if kind == "T6" else []
    at = rng.choice(spots) if spots else (insertion_line(text, language), 0) if kind != "T6" else (None, 0)
    body = INLINE if kind == "T6" else eol * rng.randint(1, 3) if kind == "T1" else \
        eol + COMMENTS[FAMILY.get(language, language)] + eol + eol
    shift = Shift(path, at[0], at[1], body.count("\n"), 0 if body.endswith("\n") else utf16_len(body))
    return None if at[0] is None else Transform(kind, path, ((*at, *at, body),), shift, same)


def plan_cases(ctx: OracleContext) -> List[Transform]:
    """Kinds round robin over rotating files (a kind that does not apply to a file tries the
    next one), so the first six cases differ in kind; further rounds draw new parameters."""
    files, out = {t.path: t for t in ctx.targets}, []
    for rep, (j, kind) in ((rep, jk) for rep in range(3) for jk in enumerate(KINDS)):
        for path in (list(files)[(rep + j + f) % len(files)] for f in range(len(files))):
            t = make_transform(kind, path, read_text(os.path.join(ctx.project_dir, path)), ctx.language,
                               random.Random(f"r5:{ctx.seed}:{path}:{kind}:{rep}"), files[path])
            if t is not None and t not in out and len(out) < ctx.max_cases:
                out.append(t)
                break
    return out


# ------------------------------------------------------------------ oracle
def transformed(ctx: OracleContext, t: Transform, ops: Sequence[Op], label: str, targets: Sequence[FileTargets],
                qcfg: Optional[QueryConfig] = None) -> Snapshot:
    changes = [o for o in ops if o.kind == "change"]
    dst = materialize(ctx, final_state(ctx.project_dir, [Op("open", t.path)] + changes), f"{ctx.run_id}-{label}")
    try:
        return run_session(ctx, label, (), dst, targets=map_targets(targets, t.shift), qcfg=qcfg)[0]
    finally:
        discard(dst)


@register_oracle(ORACLE)
class R5Transforms:
    name = ORACLE

    def applies_to(self, server_kind: str) -> bool:
        return server_kind in SERVER_LANGUAGE

    def run(self, ctx: OracleContext) -> OracleResult:
        t0, res = time.monotonic(), OracleResult(ORACLE, ctx.run_id)
        base, ctrl, stable = fresh_pair(ctx, "r5")
        res.sessions, res.unsettled = 2, int(not base.settled) + int(not ctrl.settled)
        for k in (k for k in base.results if k not in stable):
            res.unstable[k.method] = res.unstable.get(k.method, 0) + 1
        for i, t in enumerate(plan_cases(ctx) if stable else []):
            res.cases += 1
            try:
                snap = transformed(ctx, t, t.ops(), f"r5-case{i}", ctx.targets)
            except (OpError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
                res.invalid_cases += 1
                res.notes.append(f"case {i} {t.kind} {t.path}: {type(exc).__name__}: {exc}"[:300])
                continue
            res.sessions, res.unsettled = res.sessions + 1, res.unsettled + int(not snap.settled)
            for k in stable if snap.settled else ():
                res.compared[k.method] = res.compared.get(k.method, 0) + 1
            for k, exp, act in compare_mapped(base, snap, stable, t.shift, t.back) if snap.settled else ():
                case = {"transform": asdict(t), "mapped_key": list(key_sort(map_key(k, t.shift)))}
                note = f"{t.kind} {t.path}: {len(t.edits)} edit(s), first {list(t.edits[0][:4])}"
                res.candidates.append(make_violation(ctx, ORACLE, k, exp, act, t.ops(), case, note))
        res.notes += [] if stable else ["original pair not settled or empty: nothing compared"]
        res.seconds = round(time.monotonic() - t0, 3)
        return res

    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        t0, case = time.monotonic(), case_of(v)
        t = Transform.from_json(case["transform"])
        changes = [o for o in (v.ops if ops is None else ops) if o.kind == "change"]
        if not changes:  # nothing transformed: the case cannot arm
            return ReplayOutcome(True, True, False, None, 0.0)
        targets, qcfg = key_targets(ctx.targets, v.key), key_query(ctx, v.key)
        b, _ = run_session(ctx, "r5-replay-baseline", targets=targets, qcfg=qcfg)
        c, _ = run_session(ctx, "r5-replay-control", targets=targets, qcfg=qcfg)
        stable = v.key in stable_keys(b, c)
        snap = transformed(ctx, t, changes, "r5-replay-case", targets, qcfg)
        seen = [make_violation(ctx, ORACLE, k, e, a, changes, case, "replay")
                for k, e, a in compare_mapped(b, snap, [v.key] if stable and snap.settled else [], t.shift, t.back)]
        return ReplayOutcome(b.settled and c.settled and snap.settled, stable,
                             bool(seen) and shape_of(seen[0]) == shape_of(v), seen[0] if seen else None,
                             round(time.monotonic() - t0, 3))


__all__ = ["ENTRIES", "INLINE", "KINDS", "LINE_RULES", "R5Transforms", "Shift", "Transform", "canonical",
           "code_line_ends", "comment_spots", "compare_mapped", "drop_inserted", "insertion_line", "make_transform",
           "map_key", "map_norm", "map_targets", "plan_cases", "transformed"]
