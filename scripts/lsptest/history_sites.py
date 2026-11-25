"""Edit sites and edit primitives for the R1 history generators (histories.py).

Where to edit: per-language line classes (import, top-level declaration, code, comment,
blank) weighted towards high fan-out lines; the depended-on non-target sources of the
targets (named in their import lines, or in their directory); the configuration files of
the language present in the project. What to edit: one insert / delete / replace edit and
its inverse, a configuration-file variant with one line deleted or duplicated, and the
per-server table of configuration toggles used by H4 (SETTING_TOGGLES). What to ask
inside a history (H8): `request` ops (request_ops.py) at target and other identifier
positions in a shuffled order; fix_requests() makes requests follow the code they point
at when they are interleaved with edits. Every choice is drawn from a caller-provided
random.Random, so a seed fixes the whole history.

Run line: imported by histories.py; not run directly.
"""

from __future__ import annotations

import dataclasses
import os
import random
import re
import sys
import zlib
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from model import Op, Pos  # noqa: E402
from ops import LineIndex, OpError, change_at_offsets, inverse_change, read_text  # noqa: E402
from request_ops import REQUEST_METHODS  # noqa: E402
from targets import EXCLUDED_DIRS, Token, identifiers  # noqa: E402

EDIT_KINDS = ("insert", "delete", "replace")
EXTENSIONS: Dict[str, Tuple[str, ...]] = {
    "python": (".py",), "typescript": (".ts", ".tsx", ".mts", ".cts"), "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "rust": (".rs",), "go": (".go",), "java": (".java",)}
TOKENIZER = {"java": "typescript"}  # C-like comments and literals
CONFIG_FILES: Dict[str, Tuple[str, ...]] = {
    "python": ("pyproject.toml", "pyrightconfig.json"), "typescript": ("tsconfig.json", "jsconfig.json", "package.json"),
    "javascript": ("jsconfig.json", "package.json"), "rust": ("Cargo.toml",), "go": ("go.mod", "go.work"),
    "java": (".classpath", ".project", "pom.xml", "build.gradle", ".settings/org.eclipse.jdt.core.prefs")}
_TS_IMPORT = r"\s*(import\b|export\s+(\*|type\s*\{|\{)[^;]*\bfrom\b|.*\brequire\()"
IMPORT_RE: Dict[str, str] = {
    "python": r"\s*(import\s+\w|from\s+\S+\s+import\b)", "typescript": _TS_IMPORT, "javascript": _TS_IMPORT,
    "rust": r"\s*(pub(\([^)]*\))?\s+)?(use|mod|extern\s+crate)\b", "go": r"\s*import\b", "java": r"\s*(import|package)\s"}
_TS_DECL = (r"(export\s+)?(default\s+)?(declare\s+)?(async\s+)?"
            r"(function|class|const|let|var|interface|type|enum|namespace|abstract)\b")
DECL_RE: Dict[str, str] = {
    "python": r"(async\s+def|def|class)\b|@|[A-Za-z_]\w*\s*(:[^=]*)?=[^=]", "typescript": _TS_DECL, "javascript": _TS_DECL,
    "rust": r"(pub(\([^)]*\))?\s+)?(fn|struct|enum|trait|impl|type|const|static|mod|union|unsafe|async|macro_rules!)\b|#\[",
    "go": r"(func|type|var|const)\b",
    "java": r"( {0,4}|\t?)(public|protected|private|abstract|final|static|class|interface|enum|record|@)\b"}
COMMENT_RE: Dict[str, str] = {"python": r"#", "default": r"(//|/\*|\*)"}
COMMENT_PREFIX: Dict[str, str] = {"python": "# "}
SNIPPETS = ("x", "_tmp", "zz", " ", "\n", "\t", "(", ")", "[", "]", "{", "}", ".", ",", ":", ";", "=", '"', "'", "0")


@dataclass(frozen=True)
class HistoryConfig:
    delay_ms: int = 0  # every op's delay: 0 in the settled timing, the race delay otherwise
    import_weight: float = 6.0  # edit-site weight of import lines (other code lines: 1)
    decl_weight: float = 4.0  # ... of top-level declarations
    comment_weight: float = 0.5
    chunk_counts: Tuple[int, ...] = (1, 2, 4)  # H2 retype chunks
    save_probability: float = 0.25  # H1/H2/H6: save after the edit and after its inverse
    warmup_requests: Tuple[int, int] = (3, 10)  # H8: number of request ops (inclusive range)
    attempts: int = 8


# ------------------------------------------------------------ configuration toggles (H4)
@dataclass(frozen=True)
class Toggle:
    """A setting that changes analysis: `paths` are set together (one key in several sections);
    A is the effective value (or `default` when absent), B the first of `choices` != A (bools: not A)."""

    paths: Tuple[Tuple[str, ...], ...]
    default: Any
    choices: Tuple[Any, ...] = ()

    def other(self, a: Any) -> Any:
        for c in self.choices:
            if c != a:
                return c
        return (not a) if isinstance(a, bool) else None


def _t(key: str, default: Any, *choices: Any, sections: Tuple[str, ...] = ("",)) -> Toggle:
    parts = tuple(key.split("."))
    return Toggle(tuple(((s,) + parts) if s else parts for s in sections), default, choices)


_TS6, _TS7 = ("typescript", "javascript"), ("typescript", "javascript", "js/ts")
SETTING_TOGGLES: Dict[str, Tuple[Toggle, ...]] = {
    "pyright": (_t("python.analysis.typeCheckingMode", "standard", "strict", "basic"),
                _t("python.analysis.autoImportCompletions", True), _t("python.analysis.useLibraryCodeForTypes", True),
                _t("python.analysis.diagnosticMode", "openFilesOnly", "workspace", "openFilesOnly")),
    "ts6": (_t("inlayHints.includeInlayParameterNameHints", "none", "none", "all", sections=_TS6),
            _t("inlayHints.includeInlayVariableTypeHints", False, sections=_TS6),
            _t("diagnostics.ignoredCodes", [], [2304, 2322, 2339, 2345, 7006], []),
            _t("implicitProjectConfiguration.strictNullChecks", True)),
    "ts7": (_t("inlayHints.parameterNames.enabled", "none", "none", "all", sections=_TS7),
            _t("inlayHints.variableTypes.enabled", False, sections=_TS7), _t("suggest.autoImports", True, sections=_TS7),
            _t("suggest.includeAutomaticOptionalChainCompletions", True, sections=_TS7)),
    "rust-analyzer": (_t("rust-analyzer.diagnostics.enable", True), _t("rust-analyzer.procMacro.enable", True),
                      _t("rust-analyzer.inlayHints.typeHints.enable", True),
                      _t("rust-analyzer.completion.autoimport.enable", True),
                      _t("rust-analyzer.cargo.buildScripts.enable", True)),
    "gopls": (_t("gopls.hints.parameterNames", False), _t("gopls.semanticTokens", False),
              _t("gopls.completeUnimported", True), _t("gopls.analyses.unusedparams", True),
              _t("gopls.staticcheck", False), _t("gopls.buildFlags", [], ["-tags=lsptest"], [])),
    "jdtls": (_t("java.autobuild.enabled", True),
              _t("java.errors.incompleteClasspath.severity", "warning", "warning", "error"),
              _t("java.completion.enabled", True), _t("java.inlayHints.parameterNames.enabled", "literals", "all", "none")),
}


def get_path(d: Mapping[str, Any], path: Sequence[str], default: Any) -> Any:
    node: Any = d
    for k in path:
        if not isinstance(node, Mapping) or k not in node:
            return default
        node = node[k]
    return node


def nested(pairs: Sequence[Tuple[Sequence[str], Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for path, value in pairs:
        node = out
        for k in path[:-1]:
            node = node.setdefault(k, {})
        node[path[-1]] = value
    return out


# ------------------------------------------------------------ project structure
def source_paths(root: str, language: str) -> List[str]:
    exts, out = EXTENSIONS.get(language, ()), []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith("."))
        out += [os.path.relpath(os.path.join(dirpath, n), root).replace(os.sep, "/") for n in sorted(filenames)
                if n.endswith(exts) and not n.endswith(".d.ts")]
    return out


def classify_lines(text: str, language: str) -> List[str]:
    """Per LSP line: import | decl | code | comment | blank (Go import blocks included)."""
    idx, out, block = LineIndex(text), [], False
    imp, decl = re.compile(IMPORT_RE.get(language, r"(?!)")), re.compile(DECL_RE.get(language, r"(?!)"))
    com = re.compile(COMMENT_RE.get(language, COMMENT_RE["default"]))
    for i in range(len(idx.starts)):
        row = idx.line_text(i)
        st = row.strip()
        if block:
            out.append("import" if st else "blank")
            block = st != ")"
        elif not st:
            out.append("blank")
        elif com.match(st):
            out.append("comment")
        elif imp.match(row):
            out.append("import")
            block = language == "go" and st.endswith("(")
        else:
            out.append("decl" if decl.match(row) else "code")
    return out


def _module_name(path: str) -> str:
    stem = os.path.splitext(os.path.basename(path))[0]
    return (os.path.basename(os.path.dirname(path)) or stem) if stem in ("__init__", "index", "mod", "lib", "main") else stem


def dependency_files(root: str, targets: Sequence[str], language: str, limit: int = 6) -> Tuple[str, ...]:
    """Non-target sources the targets depend on: named in a target's import lines (score 2)
    and/or in a target's directory (score 1: a Go or Java package, sibling modules)."""
    words, dirs = set(), {os.path.dirname(t) for t in targets}
    for t in targets:
        try:
            text = read_text(os.path.join(root, t))
        except OSError:
            continue
        idx = LineIndex(text)
        for i, kind in enumerate(classify_lines(text, language)):
            if kind == "import":
                words.update(re.findall(r"\w+", idx.line_text(i)))
    scored = []
    for p in source_paths(root, language):
        score = 2 * (_module_name(p) in words) + (os.path.dirname(p) in dirs)
        if p not in targets and score:
            scored.append((-score, zlib.crc32(p.encode("utf-8")), p))
    return tuple(p for _, _, p in sorted(scored)[:limit])


def config_files(root: str, targets: Sequence[str], language: str) -> Tuple[str, ...]:
    """Configuration files of the language in the project root and in the targets' ancestors."""
    dirs = {""}
    for t in targets:
        d = os.path.dirname(t)
        while d:
            dirs.add(d)
            d = os.path.dirname(d)
    return tuple(sorted({os.path.join(d, n).replace(os.sep, "/") for d in dirs for n in CONFIG_FILES.get(language, ())
                         if os.path.isfile(os.path.join(root, d, n))}))


# ------------------------------------------------------------ edit sites and edits
def line_weights(text: str, language: str, cfg: HistoryConfig) -> List[float]:
    w = {"import": cfg.import_weight, "decl": cfg.decl_weight, "code": 1.0, "comment": cfg.comment_weight, "blank": 0.0}
    return [w[k] for k in classify_lines(text, language)]


def pick_line(rng: random.Random, text: str, language: str, cfg: HistoryConfig,
              terminated: bool = False) -> Optional[int]:
    """A line index drawn by fan-out weight (terminated: only lines that end with a terminator)."""
    weights = line_weights(text, language, cfg)
    if terminated:
        weights[-1] = 0.0  # the last LSP line never has a terminator
    total = sum(weights)
    if total <= 0:
        return None
    r, acc = rng.random() * total, 0.0
    for i, w in enumerate(weights):
        acc += w
        if w > 0 and r < acc:
            return i
    return max(i for i, w in enumerate(weights) if w > 0)


def span(idx: LineIndex, line: int) -> Tuple[int, int, int]:
    """(line start, content end, next line start) as character offsets."""
    nxt = idx.starts[line + 1] if line + 1 < len(idx.starts) else len(idx.text)
    return idx.starts[line], idx.line_end(line), nxt


def tokens(text: str, language: str) -> List[Token]:
    try:
        return identifiers(text, TOKENIZER.get(language, language))
    except ValueError:
        return []


def edit_op(rng: random.Random, path: str, text: str, language: str, cfg: HistoryConfig) -> Tuple[Optional[Op], str]:
    """One edit at a fan-out-weighted line: insert a snippet, delete a span or whole lines, or
    replace an identifier. Returns (op, description); op is None when no line is usable."""
    line = pick_line(rng, text, language, cfg)
    if line is None:
        return None, ""
    idx = LineIndex(text)
    s, e, nxt = span(idx, line)
    kind, d = rng.choice(EDIT_KINDS), cfg.delay_ms
    if kind == "replace":
        toks = [t for t in tokens(text, language) if s <= t.start and t.end <= e]
        if toks:
            t = rng.choice(toks)
            new = rng.choice([c for c in (t.text + "_x", t.text[:-1], "zz") if c and c != t.text])
            return change_at_offsets(path, text, t.start, t.end, new, d), f"replace {t.text!r} by {new!r} on line {line}"
        kind = "insert"
    if kind == "delete":
        r = rng.random()
        if r < 0.5 and e > s:
            a = rng.randrange(s, e)
            b = rng.randint(a + 1, e)
            return change_at_offsets(path, text, a, b, "", d), f"delete {text[a:b]!r} on line {line}"
        if nxt > s:
            m = 1 if r < 0.85 else rng.randint(2, 3)
            stop = idx.starts[line + m] if line + m < len(idx.starts) else len(text)
            return change_at_offsets(path, text, s, stop, "", d), f"delete lines {line}..{line + m - 1}"
    at = rng.randint(s, e)
    toks = tokens(text, language)
    snippet = rng.choice(SNIPPETS + (COMMENT_PREFIX.get(language, "// "),) + ((rng.choice(toks).text,) if toks else ()))
    return change_at_offsets(path, text, at, at, snippet, d), f"insert {snippet!r} on line {line}"


def there_and_back(path: str, text: str, op: Op, cfg: HistoryConfig, save: bool) -> Optional[Tuple[Op, ...]]:
    """op, its inverse, and (save) a save after each so the disk ends at the original too."""
    try:
        inv = inverse_change(op, text)
    except OpError:
        return None
    sv = (Op("save", path, delay_ms=cfg.delay_ms),) if save else ()
    return (op,) + sv + (inv,) + sv


def retype_ops(rng: random.Random, path: str, text: str, line: int, cfg: HistoryConfig) -> Tuple[List[Op], int]:
    """Delete a whole line (with its terminator), then insert it again in k chunks, in order."""
    s, e, nxt = span(LineIndex(text), line)
    row, d = text[s:nxt], cfg.delay_ms
    k = min(rng.choice(cfg.chunk_counts), e - s + 1)
    bounds = [0] + sorted(rng.sample(range(1, e - s + 1), k - 1)) + [len(row)]
    ops, cur, pos = [change_at_offsets(path, text, s, nxt, "", d)], text[:s] + text[nxt:], s
    for a, b in zip(bounds, bounds[1:]):
        ops.append(change_at_offsets(path, cur, pos, pos, row[a:b], d))
        cur, pos = cur[:pos] + row[a:b] + cur[pos:], pos + b - a
    if cur != text:
        raise OpError(f"retyping line {line} of {path} did not restore it")
    return ops, k


def config_variant(rng: random.Random, text: str) -> Tuple[Optional[str], str]:
    """The text with one non-blank line deleted or duplicated."""
    idx = LineIndex(text)
    lines = [i for i in range(len(idx.starts)) if idx.line_text(i).strip()]
    if not lines:
        return None, ""
    i = rng.choice(lines)
    s, e, nxt = span(idx, i)
    if rng.random() < 0.5:
        return text[:s] + text[nxt:], f"line {i} deleted"
    return text[:s] + (text[s:nxt] if nxt > e else text[s:e] + "\n") + text[s:], f"line {i} duplicated"


# ------------------------------------------------------------ queries inside a history (H8)
def warmup_ops(rng: random.Random, texts: Mapping[str, str], positions: Mapping[str, Sequence[Pos]], language: str,
               cfg: HistoryConfig) -> List[Op]:
    """Request ops at the target positions and at as many other identifier positions of the same
    files, a random method each, in a shuffled order (a query order that differs from the suite's)."""
    pool: List[Tuple[str, Pos]] = []
    for path in sorted(texts):
        idx, tgt = LineIndex(texts[path]), list(dict.fromkeys(tuple(p) for p in positions.get(path, ())))
        seen = set(tgt)
        others = [q for q in (idx.position(t.start + (t.end - t.start) // 2) for t in tokens(texts[path], language))
                  if q not in seen]
        pool += [(path, p) for p in tgt] + [(path, p) for p in rng.sample(others, min(len(others), max(len(tgt), 4)))]
    rng.shuffle(pool)
    n = min(len(pool), rng.randint(*cfg.warmup_requests))
    return [Op("request", path, start=pos, text=rng.choice(sorted(REQUEST_METHODS)), delay_ms=cfg.delay_ms)
            for path, pos in pool[:n]]


def fix_requests(ops: Sequence[Op], original: Callable[[str], Optional[str]], open_at_start: Sequence[str]) -> List[Op]:
    """Requests written against the original texts follow the code they point at when other ops
    edit the same document first: each offset is mapped through the buffer edits made since the
    document was opened; a request on a document that is not open (closed, renamed away) at that
    point, or whose position does not exist, is dropped."""
    disk: Dict[str, Optional[str]] = {}
    buf: Dict[str, str] = {p: original(p) or "" for p in open_at_start}
    edits: Dict[str, List[Tuple[int, int, int]]] = {p: [] for p in open_at_start}
    out: List[Op] = []
    for op in ops:
        p = op.path
        if op.kind == "request":
            base = original(p)
            if p not in buf or base is None or op.start is None:
                continue
            try:
                off = LineIndex(base).offset(op.start)
            except OpError:
                continue
            for s, e, n in edits[p]:
                off = off + n - (e - s) if off >= e else (min(off, s + n) if off > s else off)
            if off <= len(buf[p]):
                out.append(dataclasses.replace(op, start=LineIndex(buf[p]).position(off)))
            continue
        out.append(op)
        if op.kind == "open":
            buf[p], edits[p] = (disk[p] if p in disk else original(p)) or "", []
        elif op.kind == "change" and p in buf and op.start is not None and op.end is not None:
            idx = LineIndex(buf[p])
            s, e = idx.offset(op.start), idx.offset(op.end)
            buf[p] = buf[p][:s] + op.text + buf[p][e:]
            edits[p].append((s, e, len(op.text)))
        elif op.kind == "close":
            buf.pop(p, None)
            edits.pop(p, None)
        elif op.kind == "save" and p in buf:
            disk[p] = buf[p]
        elif op.kind == "fs_write":
            disk[p] = op.text
        elif op.kind == "fs_rename":
            disk[op.new_path], disk[p] = (disk[p] if p in disk else original(p)), None
            if p in buf:
                buf[op.new_path], edits[op.new_path] = buf.pop(p), edits.pop(p)
    return out


__all__ = [
    "COMMENT_PREFIX", "CONFIG_FILES", "DECL_RE", "EDIT_KINDS", "EXTENSIONS", "HistoryConfig", "IMPORT_RE",
    "SETTING_TOGGLES", "SNIPPETS", "Toggle", "classify_lines", "config_files", "config_variant", "dependency_files",
    "edit_op", "fix_requests", "get_path", "line_weights", "nested", "pick_line", "retype_ops", "source_paths", "span",
    "there_and_back", "tokens", "warmup_ops",
]
