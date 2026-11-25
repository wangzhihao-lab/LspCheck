"""Lexical helpers for the seeded mutations of the r4_edits oracle (oracles/r4_mutations.py):
bracket matching and top-level comma splitting that skip string literals and comments,
and the import statements of a file for Python, TypeScript/JavaScript, Go and Rust.

`imports(text, family)` returns ImportStmt records: the statement's span (whole lines,
trailing newline included), each bound name with the span that removes it alone (an item
of a list with two or more items, or a spec line of a Go import block; None when only the
whole statement can go), and the module specifier (TypeScript, Go). Families follow
targets.FAMILY: py, js, go, rs.

Run line: imported by oracles/r4_mutations.py; not run directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

OPEN, CLOSE = "([{", ")]}"
Span = Tuple[int, int]


# ------------------------------------------------------------------ scanning
def skip_quote(text: str, j: int, fam: str) -> int:
    """Index just after the string / char literal starting at text[j] (a lifetime tick in Rust
    is one character; an unterminated single-line literal stops at the line end)."""
    q, n = text[j], len(text)
    if fam == "py" and text.startswith(q * 3, j):
        k = text.find(q * 3, j + 3)
        return n if k < 0 else k + 3
    if q == "'" and fam == "rs":
        if j + 2 < n and text[j + 2] == "'" and text[j + 1] != "\\":
            return j + 3
        if j + 1 < n and text[j + 1] == "\\":
            k = text.find("'", j + 2)
            return j + 1 if k < 0 or k - j > 12 else k + 1
        return j + 1  # lifetime or label
    multiline = q == "`" or (fam == "rs" and q == '"')
    k = j + 1
    while k < n:
        c = text[k]
        if c == "\\":
            k += 2
            continue
        if c == q:
            return k + 1
        if c == "\n" and not multiline:
            return k
        k += 1
    return n


def _comment_end(text: str, j: int, fam: str) -> Optional[int]:
    """End of a comment starting at j, or None when no comment starts there."""
    if fam == "py":
        if text[j] == "#":
            k = text.find("\n", j)
            return len(text) if k < 0 else k
        return None
    if text.startswith("//", j):
        k = text.find("\n", j)
        return len(text) if k < 0 else k
    if text.startswith("/*", j):
        k = text.find("*/", j + 2)
        return len(text) if k < 0 else k + 2
    return None


def match_bracket(text: str, i: int, fam: str, limit: int = 6000) -> Optional[int]:
    """Index of the bracket that closes text[i] (strings and comments skipped), or None."""
    depth, j, n = 0, i, min(len(text), i + limit)
    while j < n:
        c = text[j]
        end = _comment_end(text, j, fam)
        if end is not None:
            j = end
            continue
        if c in "\"'`":
            j = skip_quote(text, j, fam)
            continue
        if c in OPEN:
            depth += 1
        elif c in CLOSE:
            depth -= 1
            if depth == 0:
                return j
            if depth < 0:
                return None
        j += 1
    return None


def split_top(text: str, a: int, b: int, fam: str) -> List[Span]:
    """Spans of the comma-separated items of text[a:b] at bracket depth 0, whitespace trimmed;
    empty items (a trailing comma) are dropped."""
    items, depth, start, j = [], 0, a, a
    while j < b:
        c = text[j]
        end = _comment_end(text, j, fam)
        if end is not None:
            j = min(end, b)
            continue
        if c in "\"'`":
            j = skip_quote(text, j, fam)
            continue
        if c in OPEN:
            depth += 1
        elif c in CLOSE:
            depth -= 1
        elif c == "," and depth == 0:
            items.append((start, j))
            start = j + 1
        j += 1
    items.append((start, b))
    out = []
    for s, e in items:
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e > s:
            out.append((s, e))
    return out


def line_span(text: str, a: int, b: int) -> Span:
    """From the start of a's line to just after the newline that ends b's line."""
    s = text.rfind("\n", 0, a) + 1
    e = text.find("\n", b)
    return s, len(text) if e < 0 else e + 1


def remove_item(items: List[Span], k: int) -> Span:
    """Span that removes item k of a comma list together with one separating comma."""
    if k + 1 < len(items):
        return items[k][0], items[k + 1][0]
    return items[k - 1][1], items[k][1]


# ------------------------------------------------------------------ imports
@dataclass
class ImportItem:
    bound: str  # the name the item binds in the file
    removal: Optional[Span] = None  # what to delete to remove this item alone (None: the whole statement)


@dataclass
class ImportStmt:
    span: Span  # whole lines of the statement, trailing newline included
    items: List[ImportItem] = field(default_factory=list)
    spec: str = ""  # module specifier (TypeScript, Go)
    top: bool = True  # starts in column 0


def listed(text: str, spans: List[Span], bound: Callable[[str], str]) -> List[ImportItem]:
    """Items of a comma list; each removable alone when the list has two or more items."""
    return [ImportItem(bound(text[s:e]), remove_item(spans, k) if len(spans) >= 2 else None)
            for k, (s, e) in enumerate(spans)]


def _bound_py(item: str) -> str:
    parts = item.split()
    return parts[-1] if len(parts) >= 3 and parts[-2] == "as" else item.split(".")[0].strip()


_PY_IMPORT = re.compile(r"^([ \t]*)(import|from)[ \t]+", re.M)


def _py_imports(text: str) -> List[ImportStmt]:
    out = []
    for m in _PY_IMPORT.finditer(text):
        line_end = text.find("\n", m.start())
        line_end = len(text) if line_end < 0 else line_end
        if m.group(2) == "import":
            items = split_top(text, m.end(), _code_end(text, m.end(), line_end), "py")
            stmt = ImportStmt(line_span(text, m.start(), m.start()))
        else:
            k = text.find(" import", m.end(), line_end)
            if k < 0 or text[m.end():k].strip() == "__future__":
                continue
            rest = k + len(" import")
            while rest < line_end and text[rest] in " \t":
                rest += 1
            if text.startswith("(", rest):
                close = match_bracket(text, rest, "py")
                if close is None:
                    continue
                items, stmt_end = split_top(text, rest + 1, close, "py"), close
            else:
                items, stmt_end = split_top(text, rest, _code_end(text, rest, line_end), "py"), rest
            stmt = ImportStmt(line_span(text, m.start(), stmt_end))
        stmt.top = not m.group(1)
        stmt.items = [i for i in listed(text, items, _bound_py) if i.bound != "*"]
        out.append(stmt)
    return out


def _code_end(text: str, a: int, line_end: int) -> int:
    k = text.find("#", a, line_end)
    return line_end if k < 0 else k


_JS_IMPORT = re.compile(r"^([ \t]*)import[ \t]+(?!['\"(])", re.M)
_JS_FROM = re.compile(r"\bfrom\s*(['\"])([^'\"\n]+)\1[ \t]*;?")


def _js_imports(text: str) -> List[ImportStmt]:
    out = []
    for m in _JS_IMPORT.finditer(text):
        f = _JS_FROM.search(text, m.end(), m.end() + 3000)
        if f is None or re.search(r"^[ \t]*import\b", text[m.end():f.start()], re.M):
            continue
        clause_a, clause_b = m.end(), f.start()
        if text.startswith("type ", clause_a):
            clause_a += 5
        stmt = ImportStmt(line_span(text, m.start(), f.end() - 1), spec=f.group(2), top=not m.group(1))
        brace = text.find("{", clause_a, clause_b)
        head_end = brace if brace >= 0 else clause_b
        for s, e in split_top(text, clause_a, head_end, "js"):
            if text[s:e].split():
                stmt.items.append(ImportItem(text[s:e].split()[-1]))
        if brace >= 0:
            close = match_bracket(text, brace, "js")
            if close is None:
                continue
            stmt.items += listed(text, split_top(text, brace + 1, close, "js"), lambda t: t.split()[-1])
        out.append(stmt)
    return out


_GO_SINGLE = re.compile(r'^import[ \t]+(?:([\w.]+)[ \t]+)?"([^"\n]+)"', re.M)
_GO_BLOCK = re.compile(r"^import[ \t]*\(", re.M)
_GO_SPEC = re.compile(r'^[ \t]*(?:([\w.]+)[ \t]+)?"([^"\n]+)"[ \t]*(?://.*)?$', re.M)


def go_package(path: str, alias: Optional[str]) -> str:
    """The name an import binds: its alias, else the last path element without version
    suffixes and go- prefixes (a heuristic; the package clause is not read)."""
    if alias:
        return alias
    parts = path.split("/")
    last = parts[-2] if re.fullmatch(r"v\d+", parts[-1]) and len(parts) > 1 else parts[-1]
    last = re.sub(r"\.v\d+$", "", last)
    return re.sub(r"^go-|-go$", "", last).replace("-", "")


def _go_imports(text: str) -> List[ImportStmt]:
    out = []
    for m in _GO_SINGLE.finditer(text):
        stmt = ImportStmt(line_span(text, m.start(), m.start()), spec=m.group(2))
        stmt.items = [ImportItem(go_package(m.group(2), m.group(1)))]
        out.append(stmt)
    for m in _GO_BLOCK.finditer(text):
        close = match_bracket(text, m.end() - 1, "go")
        if close is None:
            continue
        stmt = ImportStmt(line_span(text, m.start(), close))
        for spec in _GO_SPEC.finditer(text, m.end(), close):
            stmt.items.append(ImportItem(go_package(spec.group(2), spec.group(1)),
                                         line_span(text, spec.start(), spec.start())))
            stmt.spec = stmt.spec or spec.group(2)
        out.append(stmt)
    return out


_RS_USE = re.compile(r"^([ \t]*)(?:pub(?:\([\w ]+\))?[ \t]+)?use[ \t]+", re.M)


def _rs_bound(item: str) -> str:
    parts = item.split()
    if len(parts) >= 3 and parts[-2] == "as":
        return parts[-1]
    return item.split("::")[-1].strip()


def _rs_imports(text: str) -> List[ImportStmt]:
    out = []
    for m in _RS_USE.finditer(text):
        semi, j = None, m.end()
        while j < min(len(text), m.end() + 3000):
            if text[j] == "{":
                j = (match_bracket(text, j, "rs") or len(text)) + 1
                continue
            if text[j] == ";":
                semi = j
                break
            j += 1
        if semi is None:
            continue
        stmt = ImportStmt(line_span(text, m.start(), semi), top=not m.group(1))
        brace = text.find("{", m.end(), semi)
        if brace < 0:
            stmt.items = [ImportItem(_rs_bound(text[m.end():semi]))]
        else:
            close = match_bracket(text, brace, "rs") or semi
            spans = split_top(text, brace + 1, close, "rs")
            stmt.items = [i for i, (s, e) in zip(listed(text, spans, _rs_bound), spans) if "{" not in text[s:e]]
        stmt.items = [i for i in stmt.items if i.bound not in ("*", "self", "")]
        out.append(stmt)
    return out


IMPORT_PARSERS = {"py": _py_imports, "js": _js_imports, "go": _go_imports, "rs": _rs_imports}


def imports(text: str, fam: str) -> List[ImportStmt]:
    return sorted(IMPORT_PARSERS[fam](text), key=lambda s: s.span) if fam in IMPORT_PARSERS else []


__all__ = ["ImportItem", "ImportStmt", "go_package", "imports", "line_span", "listed", "match_bracket",
           "remove_item", "skip_quote", "split_top"]
