"""Pure text-edit helpers of the r4_edits oracle (no server involved, unit-tested).

- LSP TextEdits applied with simultaneous semantics (all ranges refer to the original
  text; equal-position inserts keep array order; overlaps raise OpError). As LSP
  specifies, a character beyond the end of a line means the line end; a line beyond
  the last line means the end of the text.
- WorkspaceEdits: `documentChanges` preferred over `changes`; resource operations
  (create/rename/delete) are skipped and reported; several edits of one document in
  `documentChanges` apply in order; snippet text edits are stripped to plain text.
- Snippets: tab stops, placeholders (nested), choices and variables replaced by their
  default text; escapes resolved.
- `minimal_change`: the single change Op turning one text into another (common prefix
  and suffix removed, never splitting a CRLF), so a whole WorkspaceEdit is one
  didChange and its inverse is exact. `map_range` carries a range through the server's
  own edit spans (a diagnostic through its quick fix).
- Completion items: the edit an editor applies when the item is accepted, display order
  and the editor-style fuzzy filter by the typed identifier.

Run line: imported by oracles/r4_edits.py and oracles/r4_session.py; not run directly.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from model import Op, Pos  # noqa: E402
from ops import LineIndex, OpError, utf16_len  # noqa: E402

# Completion item kinds that name program entities (LSP CompletionItemKind): method,
# function, constructor, field, variable, class, interface, module, property, enum,
# enum member, constant, struct, type parameter. Keywords, snippets, text, files ... excluded.
IDENTIFIER_KINDS = frozenset({2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 20, 21, 22, 25})
RESOURCE_KINDS = frozenset({"create", "rename", "delete"})
Span = Tuple[int, int, str]  # original start offset, original end offset, replacement


# ------------------------------------------------------------------ positions and text edits
def clamp_offset(idx: LineIndex, pos: Mapping[str, Any]) -> int:
    """Offset of an LSP position with LSP's clamping (see the module docstring)."""
    line, char = int(pos.get("line", 0)), int(pos.get("character", 0))
    if line < 0:
        return 0
    if line >= len(idx.starts):
        return len(idx.text)
    start, end = idx.starts[line], idx.line_end(line)
    row = idx.text[start:end]
    if row.isascii():
        return start + min(max(char, 0), len(row))
    units = 0
    for i, ch in enumerate(row):
        if units >= char:
            return start + i
        units += 2 if ord(ch) > 0xFFFF else 1
    return end


def edit_text(edit: Mapping[str, Any]) -> str:
    """newText of a TextEdit / AnnotatedTextEdit, or the stripped snippet of a SnippetTextEdit."""
    if isinstance(edit.get("newText"), str):
        return edit["newText"]
    snippet = edit.get("snippet")
    return strip_snippet(str(snippet.get("value", ""))) if isinstance(snippet, dict) else ""


def text_edit_spans(text: str, edits: Sequence[Mapping[str, Any]]) -> List[Span]:
    """Edits as sorted (start, end, replacement) offsets into `text`; OpError on overlap."""
    idx = LineIndex(text)
    rows = []
    for i, e in enumerate(edits):
        r = e.get("range") or {}
        s, t = clamp_offset(idx, r.get("start") or {}), clamp_offset(idx, r.get("end") or {})
        if t < s:
            raise OpError(f"text edit {i} ends before it starts")
        rows.append((s, t, i, edit_text(e)))
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    for a, b in zip(rows, rows[1:]):
        if b[0] < a[1]:
            raise OpError(f"text edits {a[2]} and {b[2]} overlap")
    return [(s, t, new) for s, t, _, new in rows]


def apply_spans(text: str, spans: Sequence[Span]) -> str:
    out, pos = [], 0
    for s, t, new in spans:
        out.append(text[pos:s])
        out.append(new)
        pos = t
    out.append(text[pos:])
    return "".join(out)


def apply_text_edits(text: str, edits: Sequence[Mapping[str, Any]]) -> str:
    return apply_spans(text, text_edit_spans(text, edits))


def effective_edits(text: str, edits: Sequence[Mapping[str, Any]]) -> List[List[Any]]:
    """Normalized [sl, sc, el, ec, newText] of the edits that change something (sorted)."""
    idx = LineIndex(text)
    out = []
    for s, t, new in text_edit_spans(text, edits):
        if text[s:t] != new:
            a, b = idx.position(s), idx.position(t)
            out.append([a[0], a[1], b[0], b[1], new])
    return out


def is_noop(text: str, edits: Optional[Sequence[Mapping[str, Any]]]) -> bool:
    return not edits or apply_text_edits(text, edits) == text


# ------------------------------------------------------------------ workspace edits
def workspace_edit_groups(edit: Mapping[str, Any]) -> Tuple[List[Tuple[str, List[Mapping[str, Any]]]], List[str]]:
    """(uri, text edits) groups in application order, and the skipped resource operations."""
    groups: List[Tuple[str, List[Mapping[str, Any]]]] = []
    skipped: List[str] = []
    if isinstance(edit.get("documentChanges"), list):
        for ch in edit["documentChanges"]:
            if not isinstance(ch, dict):
                continue
            if ch.get("kind") in RESOURCE_KINDS:
                skipped.append(f"{ch['kind']}:{ch.get('uri') or ch.get('oldUri') or ''}")
            elif isinstance(ch.get("textDocument"), dict):
                groups.append((str(ch["textDocument"].get("uri", "")), list(ch.get("edits") or [])))
    elif isinstance(edit.get("changes"), dict):
        groups = [(str(uri), list(edits or [])) for uri, edits in edit["changes"].items()]
    return groups, skipped


@dataclass
class EditResult:
    texts: Dict[str, str] = field(default_factory=dict)  # path -> new text (changed documents only)
    before: Dict[str, str] = field(default_factory=dict)  # path -> text before the edit
    spans: Dict[str, List[Span]] = field(default_factory=dict)  # path -> the server's spans (one group)
    skipped: List[str] = field(default_factory=list)  # resource operations, outside/unreadable documents


def workspace_edit_texts(edits: Sequence[Mapping[str, Any]], read: Callable[[str], Optional[str]],
                         rel: Callable[[str], Optional[str]]) -> EditResult:
    """Texts after applying WorkspaceEdits in order. `read(path)` gives a document's current
    text (None: unreadable), `rel(uri)` its workspace-relative path (None: outside the
    workspace). A document edited by several groups gets the minimal-change span instead of
    the server's spans. Raises OpError when an edit cannot be applied (overlap, bad range)."""
    out, cur, groups_per = EditResult(), {}, {}  # type: ignore[var-annotated]
    for we in edits:
        groups, res_ops = workspace_edit_groups(we)
        out.skipped += res_ops
        for uri, tedits in groups:
            path = rel(uri)
            if path is None:
                out.skipped.append(f"outside:{uri}")
                continue
            if path not in cur:
                text = read(path)
                if text is None:
                    out.skipped.append(f"unreadable:{path}")
                    continue
                cur[path] = out.before[path] = text
            spans = text_edit_spans(cur[path], tedits)
            cur[path] = apply_spans(cur[path], spans)
            groups_per[path] = spans if path not in groups_per else None
    for path, text in cur.items():
        if text != out.before[path]:
            out.texts[path] = text
            spans = groups_per.get(path)
            if spans is None:
                op = minimal_change(path, out.before[path], text)
                spans = [change_span(out.before[path], op)] if op is not None else []
            out.spans[path] = spans
    return out


# ------------------------------------------------------------------ snippets
_TABSTOP = re.compile(r"\$(\d+|[A-Za-z_][A-Za-z0-9_]*)")
_HEAD = re.compile(r"\$\{(\d+|[A-Za-z_][A-Za-z0-9_]*)")


def _choice(s: str, i: int) -> Tuple[str, int]:
    """First option of a choice body starting at i (after '|'); returns (text, index after '|}')."""
    opts, cur = [], []
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            cur.append(s[i + 1])
            i += 2
            continue
        if c == ",":
            opts.append("".join(cur))
            cur = []
        elif c == "|" and s.startswith("|}", i):
            opts.append("".join(cur))
            return (opts[0] if opts else ""), i + 2
        else:
            cur.append(c)
        i += 1
    return (opts[0] if opts else "".join(cur)), i


def _skip_braced(s: str, i: int) -> int:
    depth = 1
    while i < len(s) and depth:
        if s[i] == "\\":
            i += 2
            continue
        depth += 1 if s.startswith("${", i) else (-1 if s[i] == "}" else 0)
        i += 2 if s.startswith("${", i) else 1
    return i


def _snippet(s: str, i: int, nested: bool) -> Tuple[str, int]:
    out: List[str] = []
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s) and s[i + 1] in "$}\\":
            out.append(s[i + 1])
            i += 2
        elif nested and c == "}":
            return "".join(out), i
        elif c == "$" and (m := _HEAD.match(s, i)):
            j = m.end()
            if j < len(s) and s[j] == ":":
                inner, j = _snippet(s, j + 1, True)
                out.append(inner)
                i = j + 1
            elif j < len(s) and s[j] == "|":
                text, i = _choice(s, j + 1)
                out.append(text)
            elif j < len(s) and s[j] == "}":
                i = j + 1
            else:  # ${VAR/regex/format/} and malformed heads: drop the whole braced part
                i = _skip_braced(s, i + 2)
        elif c == "$" and (m := _TABSTOP.match(s, i)):
            i = m.end()
        else:
            out.append(c)
            i += 1
    return "".join(out), i


def strip_snippet(s: str) -> str:
    """Plain text of an LSP snippet ($1 -> "", ${1:a${2:b}} -> "ab", ${1|x,y|} -> "x")."""
    return _snippet(s, 0, False)[0]


# ------------------------------------------------------------------ change ops and mapping
def minimal_change(path: str, old: str, new: str) -> Optional[Op]:
    """One change Op turning `old` into `new` (None when equal); never splits a CRLF."""
    if old == new:
        return None
    n = min(len(old), len(new))
    p = 0
    while p < n and old[p] == new[p]:
        p += 1
    s = 0
    while s < n - p and old[len(old) - 1 - s] == new[len(new) - 1 - s]:
        s += 1
    if p > 0 and (old[p - 1 : p + 1] == "\r\n" or new[p - 1 : p + 1] == "\r\n"):
        p -= 1
    eo, en = len(old) - s, len(new) - s
    if s > 0 and (old[eo - 1 : eo + 1] == "\r\n" or new[en - 1 : en + 1] == "\r\n"):
        s -= 1
    idx = LineIndex(old)
    return Op("change", path=path, start=idx.position(p), end=idx.position(len(old) - s),
              text=new[p : len(new) - s])


def change_span(old: str, op: Op) -> Span:
    """The (start, end, replacement) offsets of a change Op applied to `old`."""
    idx = LineIndex(old)
    return idx.offset(op.start), idx.offset(op.end), op.text  # type: ignore[arg-type]


def map_range(old: str, new: str, spans: Sequence[Span], start: Pos, end: Pos) -> Tuple[Pos, Pos, bool]:
    """A range of `old` carried into `new` through sorted, non-overlapping spans. Returns
    (start, end, touched): an untouched range shifts exactly (an insertion at its start
    moves it, one at its end does not grow it); a range that a span overlaps (or an
    insertion falls inside, or lands on an empty range) becomes its union with the
    replacements."""
    oi, ni = LineIndex(old), LineIndex(new)
    a, b = oi.offset(start), oi.offset(end)
    lo, hi, shift_lo, shift_hi, touched = a, b, 0, 0, False
    for s, t, rep in sorted(spans, key=lambda x: (x[0], x[1])):
        delta = len(rep) - (t - s)
        hit = (a < s < b or a == b == s) if s == t else not (b <= s or a >= t)
        if hit:
            touched, lo, hi = True, min(lo, s), max(hi, t)
            shift_hi += delta
        elif (s <= a) if s == t else (t <= a):
            shift_lo += delta
            shift_hi += delta
    return ni.position(lo + shift_lo), ni.position(hi + shift_hi), touched


# ------------------------------------------------------------------ formatting helpers
def format_options(text: str, language: str) -> Dict[str, Any]:
    """FormattingOptions matching the file's own indentation (tabs, or 2/4 spaces)."""
    tabs = sum(1 for ln in text.splitlines() if ln.startswith("\t"))
    lead = [len(ln) - len(ln.lstrip(" ")) for ln in text.splitlines() if ln.startswith(" ") and ln.strip()]
    if language == "go" or tabs > len(lead):
        return {"tabSize": 4, "insertSpaces": False}
    two = sum(1 for n in lead if n % 4 == 2)
    return {"tabSize": 2 if lead and two >= max(1, len(lead) // 10) else 4, "insertSpaces": True}


def nonws(text: str) -> str:
    return re.sub(r"\s+", "", text)


def first_difference(a: str, b: str, width: int = 30) -> Tuple[str, str]:
    """Excerpts of two strings around their first difference."""
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    lo = max(0, i - width)
    return a[lo : i + width], b[lo : i + width]


# ------------------------------------------------------------------ completion items
WORD_SEPARATORS = "_.$-0123456789 ()[]{}<>,:;'\"/\\&*!"  # a word starts after one of these (as editors score)


def word_starts(cand: str) -> List[int]:
    """Indices where a word starts in a label: the first character, after a WORD_SEPARATORS
    character (underscore, dot, digits, space, brackets, quotes, ':' ...), and camelCase humps."""
    return [i for i, ch in enumerate(cand) if i == 0 or cand[i - 1] in WORD_SEPARATORS
            or (ch.isupper() and cand[i - 1].islower())]


def fuzzy_match(typed: str, cand: str) -> bool:
    """Editor-style filter: the first typed character matches at a word start of the label
    (case-insensitive), the rest follows as a subsequence."""
    if not typed:
        return True
    t, low = typed.lower(), cand.lower()
    for i in word_starts(cand):
        if low[i] != t[0]:
            continue
        pos = i + 1
        for ch in t[1:]:
            pos = low.find(ch, pos) + 1
            if pos == 0:
                break
        else:
            return True
    return False


def display_order(items: Sequence[Mapping[str, Any]], typed: str) -> List[Mapping[str, Any]]:
    """Items an editor shows after `typed` (fuzzy_match on filterText or label), ordered by
    sortText (else label), then label."""
    shown = [it for it in items if isinstance(it, dict) and fuzzy_match(typed, str(it.get("filterText") or it.get("label", "")))]
    return sorted(shown, key=lambda i: (str(i.get("sortText") or i.get("label", "")), str(i.get("label", ""))))


def item_edits(item: Mapping[str, Any], defaults: Mapping[str, Any], word: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """TextEdits an editor applies when accepting `item`: the main edit (textEdit, using
    `replace` of an InsertReplaceEdit; else itemDefaults.editRange with textEditText /
    insertText / label; else the typed word replaced by insertText or label), snippet
    placeholders stripped, followed by the additionalTextEdits."""
    fmt = item.get("insertTextFormat") or defaults.get("insertTextFormat") or 1
    te = item.get("textEdit")
    if isinstance(te, dict):
        rng, new = te.get("replace") or te.get("range"), str(te.get("newText", ""))
    else:
        rng = defaults.get("editRange") if isinstance(defaults.get("editRange"), dict) else word
        rng = rng.get("replace", rng) if isinstance(rng, dict) and "replace" in rng else rng
        new = str(item.get("textEditText") or item.get("insertText") or item.get("label", ""))
    main = {"range": rng, "newText": strip_snippet(new) if fmt == 2 else new}
    extra = [dict(e) for e in item.get("additionalTextEdits") or [] if isinstance(e, dict)]
    return [main] + extra


def word_range(end: Pos, name: str) -> Dict[str, Any]:
    line, ch = end
    return {"start": {"line": line, "character": ch - utf16_len(name)}, "end": {"line": line, "character": ch}}


__all__ = [
    "EditResult", "IDENTIFIER_KINDS", "WORD_SEPARATORS", "RESOURCE_KINDS", "Span", "apply_spans", "apply_text_edits", "change_span", "clamp_offset",
    "display_order", "edit_text", "effective_edits", "first_difference", "format_options", "fuzzy_match", "is_noop",
    "item_edits",
    "map_range", "minimal_change", "nonws", "strip_snippet", "text_edit_spans", "word_range", "word_starts",
    "workspace_edit_groups",
    "workspace_edit_texts",
]
