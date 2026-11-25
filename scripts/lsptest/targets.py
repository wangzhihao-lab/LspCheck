"""Deterministic (seeded) query targets: up to N source files per project and up to
M identifier positions per file, the end-of-identifier positions used for
completion, and the distinct diagnostic ranges used for code actions.

The identifier tokenizer has one structure for all languages and per-language
rules for what is *not* code: comments (// and /* */, nested in Rust; # in
Python), string literals (TypeScript/JavaScript quotes, template literals with
${...} substitutions scanned as code, regex literals; Python prefixed and
triple-quoted strings; Rust raw strings r#"..."#, byte/C strings, char literals
versus lifetimes, raw identifiers r#name; Go interpreted strings, raw strings and
runes). Keywords are never targets. Choices depend only on the seed and the file
paths/contents, so two sessions on the same project always query the same keys.

Run line: imported by engine_smoke.py and the oracle layer; not run directly.
"""

from __future__ import annotations

import keyword
import os
import random
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from model import Pos  # noqa: E402
from ops import LineIndex, read_text  # noqa: E402

LANGUAGE_EXTENSIONS: Dict[str, Tuple[str, ...]] = {
    "typescript": (".ts", ".tsx", ".mts", ".cts"),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "python": (".py",),
    "rust": (".rs",),
    "go": (".go",),
}
SERVER_LANGUAGE: Dict[str, str] = {"pyright": "python", "ts6": "typescript", "ts7": "typescript", "tsserver": "typescript",
                                   "rust-analyzer": "rust", "gopls": "go"}  # tsserver: historical TS builds
EXCLUDED_DIRS: FrozenSet[str] = frozenset({"node_modules", "target", "vendor", "dist", "build", "out", "__pycache__",
                                           "venv", "coverage", "site-packages", "testdata"})
FAMILY: Dict[str, str] = {"typescript": "js", "javascript": "js", "typescriptreact": "js", "javascriptreact": "js",
                          "python": "py", "rust": "rs", "go": "go"}
KEYWORDS: Dict[str, FrozenSet[str]] = {
    "js": frozenset((
        "break case catch class const continue debugger default delete do else enum export extends false finally for "
        "function if import in instanceof new null return super switch this throw true try typeof var void while with "
        "yield let static implements interface package private protected public await async as declare abstract "
        "readonly keyof infer is satisfies asserts namespace any unknown never undefined boolean number string symbol "
        "bigint object").split()),
    "py": frozenset(keyword.kwlist),
    "rs": frozenset((
        "as async await break const continue crate dyn else enum extern false fn for if impl in let loop match mod move "
        "mut pub ref return self Self static struct super trait true type unsafe use where while abstract become box do "
        "final macro override priv typeof unsized virtual yield try gen").split()),
    "go": frozenset((
        "break case chan const continue default defer else fallthrough for func go goto if import interface map "
        "package range return select struct switch type var").split()),
}
PY_STRING_PREFIXES = frozenset({"r", "u", "b", "f", "t", "br", "rb", "fr", "rf", "tr", "rt"})
_IDENT = re.compile(r"[^\W\d]\w*")
_IDENT_JS = re.compile(r"(?:[^\W\d]|\$)(?:\w|\$)*")
_VALUE_END = frozenset({"id", "val", ")", "]", "}"})  # JS: a '/' after these is division, not a regex
_EOL_CHAR = re.compile(r"[\r\n]")


@dataclass(frozen=True)
class Token:
    start: int  # character offset
    end: int
    text: str


@dataclass(frozen=True)
class FileTargets:
    path: str  # workspace-relative, '/' separators
    positions: Tuple[Pos, ...]  # middle of each chosen identifier (hover, definition, ...)
    ends: Tuple[Pos, ...]  # right after each chosen identifier (completion)
    names: Tuple[str, ...]  # the chosen identifiers, same order


@dataclass(frozen=True)
class TargetConfig:
    seed: int = 0
    max_files: int = 3
    max_positions_per_file: int = 12
    max_file_bytes: int = 256_000
    min_identifiers: int = 8
    exclude_dirs: FrozenSet[str] = EXCLUDED_DIRS


# ------------------------------------------------------------ tokenizer
def identifiers(text: str, language: str) -> List[Token]:
    """Identifier tokens outside comments and string literals, keywords excluded."""
    fam = FAMILY.get(language, language)
    if fam not in KEYWORDS:
        raise ValueError(f"no tokenizer rules for {language!r}")
    kw, ident = KEYWORDS[fam], (_IDENT_JS if fam == "js" else _IDENT)
    out: List[Token] = []
    n, i = len(text), 0
    prev = ""  # JS: kind of the previous significant token (regex detection)
    tmpl: List[int] = []  # JS: brace depth at each open ${ substitution
    depth = 0
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if fam == "py" and c == "#":
            i = _line_end(text, i)
            continue
        if fam != "py" and text.startswith("//", i):
            i = _line_end(text, i)
            continue
        if fam != "py" and text.startswith("/*", i):
            i = _block_end(text, i, nested=fam == "rs")
            continue
        m = ident.match(text, i)
        if m:
            word, j = m.group(), m.end()
            skip = _prefixed_literal(text, j, word, fam)
            if skip is not None:
                i, prev = skip, "val"
                continue
            if fam == "rs" and word == "r" and text.startswith("#", j) and _IDENT.match(text, j + 1):
                raw = _IDENT.match(text, j + 1)
                out.append(Token(raw.start(), raw.end(), raw.group()))  # type: ignore[union-attr]
                i, prev = raw.end(), "id"  # type: ignore[union-attr]
                continue
            if word not in kw:
                out.append(Token(i, j, word))
            i, prev = j, ("kw" if word in kw else "id")
            continue
        if c.isdigit() or (c == "." and i + 1 < n and text[i + 1].isdigit()):
            i, prev = _number_end(text, i), "val"
            continue
        skip = _literal(text, i, fam, prev, tmpl, depth)
        if skip is not None:
            i, prev = skip, "val"
            continue
        if fam == "js" and c == "{":
            depth += 1
        elif fam == "js" and c == "}":
            if tmpl and tmpl[-1] == depth:  # closes a ${ substitution: back into template text
                tmpl.pop()
                i, prev = _template(text, i + 1, tmpl, depth), "val"
                continue
            depth -= 1
        i, prev = i + 1, c
    return out


def _literal(text: str, i: int, fam: str, prev: str, tmpl: List[int], depth: int) -> Optional[int]:
    """End offset of a string/char/regex literal starting at i, or None."""
    c = text[i]
    if fam == "py" and c in "'\"":
        return _py_string(text, i)
    if fam == "go":
        if c in "\"'":
            return _quoted(text, i, c, multiline=False)
        if c == "`":
            j = text.find("`", i + 1)
            return len(text) if j < 0 else j + 1
    if fam == "rs":
        if c == '"':
            return _quoted(text, i, '"', multiline=True)
        if c == "'":
            return _rust_quote(text, i)
    if fam == "js":
        if c in "'\"":
            return _quoted(text, i, c, multiline=False)
        if c == "`":
            return _template(text, i + 1, tmpl, depth)
        if c == "/" and prev not in _VALUE_END:
            return _regex_end(text, i)
    return None


def _prefixed_literal(text: str, j: int, word: str, fam: str) -> Optional[int]:
    """String literals introduced by a prefix word ending at j (Python r"", Rust b"", r#""#)."""
    if j >= len(text):
        return None
    nxt = text[j]
    if fam == "py" and nxt in "'\"" and word.lower() in PY_STRING_PREFIXES:
        return _py_string(text, j)
    if fam == "rs":
        if word in ("r", "br", "cr") and nxt in '#"':
            return _rust_raw(text, j)
        if word in ("b", "c") and nxt == '"':
            return _quoted(text, j, '"', multiline=True)
        if word == "b" and nxt == "'":
            return _rust_quote(text, j)
    return None


def _line_end(text: str, i: int) -> int:
    m = _EOL_CHAR.search(text, i)
    return m.start() if m else len(text)


def _block_end(text: str, i: int, nested: bool) -> int:
    level, p, n = 1, i + 2, len(text)
    while p < n:
        if text.startswith("*/", p):
            level, p = level - 1, p + 2
            if level == 0:
                return p
        elif nested and text.startswith("/*", p):
            level, p = level + 1, p + 2
        else:
            p += 1
    return n


def _quoted(text: str, i: int, quote: str, multiline: bool) -> int:
    """End of a quoted literal; an unterminated single-line literal stops at the line end."""
    p, n = i + 1, len(text)
    while p < n:
        ch = text[p]
        if ch == "\\":
            p += 2
        elif ch == quote:
            return p + 1
        elif not multiline and ch in "\r\n":
            return p
        else:
            p += 1
    return n


def _py_string(text: str, i: int) -> int:
    q = text[i]
    if not text.startswith(q * 3, i):
        return _quoted(text, i, q, multiline=False)
    p, n = i + 3, len(text)
    while p < n:
        if text[p] == "\\":
            p += 2
        elif text.startswith(q * 3, p):
            return p + 3
        else:
            p += 1
    return n


def _rust_quote(text: str, i: int) -> int:
    """Char literal ('a', '\\n', '\\u{..}') or lifetime/label ('a, 'static): skip either."""
    n = len(text)
    if i + 1 < n and text[i + 1] == "\\":
        return _quoted(text, i, "'", multiline=False)
    if i + 2 < n and text[i + 2] == "'":
        return i + 3
    m = _IDENT.match(text, i + 1)
    return m.end() if m else i + 1


def _rust_raw(text: str, j: int) -> Optional[int]:
    hashes, n = 0, len(text)
    while j < n and text[j] == "#":
        hashes, j = hashes + 1, j + 1
    if j >= n or text[j] != '"':
        return None  # r#ident: a raw identifier, handled by the caller
    close = '"' + "#" * hashes
    k = text.find(close, j + 1)
    return n if k < 0 else k + len(close)


def _template(text: str, p: int, tmpl: List[int], depth: int) -> int:
    """Scan template-literal text from p to the closing backtick or the next ${."""
    n = len(text)
    while p < n:
        ch = text[p]
        if ch == "\\":
            p += 2
        elif ch == "`":
            return p + 1
        elif ch == "$" and text.startswith("{", p + 1):
            tmpl.append(depth)
            return p + 2
        else:
            p += 1
    return n


def _regex_end(text: str, i: int) -> Optional[int]:
    p, n, in_class = i + 1, len(text), False
    while p < n:
        ch = text[p]
        if ch in "\r\n":
            return None
        if ch == "\\":
            p += 2
            continue
        if ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False
        elif ch == "/" and not in_class:
            p += 1
            while p < n and (text[p].isalnum() or text[p] == "_"):
                p += 1
            return p
        p += 1
    return None


def _number_end(text: str, i: int) -> int:
    p, n = i, len(text)
    while p < n and (text[p].isalnum() or text[p] == "_" or (text[p] == "." and p + 1 < n and text[p + 1].isdigit())):
        p += 1
    return p


# ------------------------------------------------------------ selection
def source_files(root: str, language: str, cfg: TargetConfig = TargetConfig()) -> List[str]:
    """Sorted workspace-relative source files of a language (hidden and excluded dirs skipped)."""
    exts = LANGUAGE_EXTENSIONS[language]
    out: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in cfg.exclude_dirs and not d.startswith("."))
        for name in filenames:
            if name.endswith(exts) and not name.endswith(".d.ts"):
                out.append(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
    return sorted(out)


def file_targets(path: str, text: str, language: str, seed: int, max_positions: int) -> FileTargets:
    """Up to max_positions identifier occurrences of one file, chosen by (seed, path)."""
    toks = identifiers(text, language)
    rng = random.Random(f"positions:{seed}:{path}")
    picked = sorted(rng.sample(range(len(toks)), min(max_positions, len(toks))))
    idx = LineIndex(text)
    chosen = [toks[k] for k in picked]
    return FileTargets(
        path=path,
        positions=tuple(idx.position(t.start + (t.end - t.start) // 2) for t in chosen),
        ends=tuple(idx.position(t.end) for t in chosen),
        names=tuple(t.text for t in chosen),
    )


def choose_targets(root: str, language: str, cfg: TargetConfig = TargetConfig()) -> Tuple[FileTargets, ...]:
    """Up to cfg.max_files files (seeded shuffle, eligible = small enough and with enough
    identifiers), each with up to cfg.max_positions_per_file positions. Sorted by path."""
    files = source_files(root, language, cfg)
    random.Random(f"files:{cfg.seed}:{language}").shuffle(files)
    chosen: List[FileTargets] = []
    need = min(cfg.min_identifiers, cfg.max_positions_per_file)
    for rel in files:
        if len(chosen) >= cfg.max_files:
            break
        path = os.path.join(root, rel)
        try:
            if os.path.getsize(path) > cfg.max_file_bytes:
                continue
            text = read_text(path)
        except OSError:
            continue
        ft = file_targets(rel, text, language, cfg.seed, cfg.max_positions_per_file)
        if len(ft.positions) >= need:
            chosen.append(ft)
    return tuple(sorted(chosen, key=lambda f: f.path))


def diagnostic_ranges(diagnostics: Optional[Iterable[Dict[str, Any]]], limit: int = 10) -> List[Tuple[int, int, int, int]]:
    """Distinct (start line, start char, end line, end char) of raw diagnostics, sorted, capped."""
    seen = set()
    for d in diagnostics or []:
        r = d.get("range") if isinstance(d, dict) else None
        if not isinstance(r, dict):
            continue
        s, e = r.get("start") or {}, r.get("end") or {}
        seen.add((int(s.get("line", 0)), int(s.get("character", 0)), int(e.get("line", 0)), int(e.get("character", 0))))
    return sorted(seen)[:limit]


def targets_to_json(files: Sequence[FileTargets]) -> List[Dict[str, Any]]:
    return [{"path": f.path, "positions": [list(p) for p in f.positions], "ends": [list(p) for p in f.ends],
             "names": list(f.names)} for f in files]


def targets_from_json(items: Sequence[Dict[str, Any]]) -> Tuple[FileTargets, ...]:
    return tuple(FileTargets(d["path"], tuple(tuple(p) for p in d["positions"]), tuple(tuple(p) for p in d["ends"]),
                             tuple(d.get("names", []))) for d in items)  # type: ignore[misc]


__all__ = [
    "EXCLUDED_DIRS", "FileTargets", "KEYWORDS", "LANGUAGE_EXTENSIONS", "SERVER_LANGUAGE", "TargetConfig", "Token",
    "choose_targets", "diagnostic_ranges", "file_targets", "identifiers", "source_files", "targets_from_json",
    "targets_to_json",
]
