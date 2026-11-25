"""Client-side text document model: version tracking plus LSP range arithmetic.

The harness must know exactly what the server *should* be holding, so every edit is
applied locally too. Positions are (line, utf16-character) as LSP requires.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Position = Tuple[int, int]


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def offset_of(text: str, pos: Position) -> int:
    """Character offset in `text` of an LSP position."""
    line, char = pos
    lines = text.splitlines(keepends=True)
    off = sum(len(lines[i]) for i in range(min(line, len(lines))))
    if line < len(lines):
        row = lines[line]
        taken = 0
        for i, ch in enumerate(row):
            if taken >= char:
                return off + i
            taken += _utf16_len(ch)
        return off + len(row)
    return off


def position_of(text: str, offset: int) -> Position:
    prefix = text[: max(0, offset)]
    line = prefix.count("\n")
    last_nl = prefix.rfind("\n")
    col = prefix[last_nl + 1 :]
    return (line, _utf16_len(col))


def end_position(text: str) -> Position:
    return position_of(text, len(text))


def line_range(text: str, lineno: int, whole_line: bool = True) -> Dict[str, Dict[str, int]]:
    """Range covering line `lineno`, including its newline when `whole_line`."""
    lines = text.splitlines(keepends=True)
    if lineno >= len(lines):
        p = end_position(text)
        return _rng(p, p)
    if whole_line:
        return _rng((lineno, 0), (lineno + 1, 0)) if lineno + 1 <= len(lines) else _rng(
            (lineno, 0), (lineno, _utf16_len(lines[lineno]))
        )
    return _rng((lineno, 0), (lineno, _utf16_len(lines[lineno].rstrip("\r\n"))))


def find_range(text: str, needle: str, nth: int = 0) -> Dict[str, Dict[str, int]]:
    """Range of the `nth` occurrence of `needle`. Raises if not present."""
    start = -1
    for _ in range(nth + 1):
        start = text.find(needle, start + 1)
        if start < 0:
            raise ValueError(f"substring not found (nth={nth}): {needle!r}")
    return _rng(position_of(text, start), position_of(text, start + len(needle)))


def find_line(text: str, needle: str) -> int:
    for i, row in enumerate(text.splitlines()):
        if needle in row:
            return i
    raise ValueError(f"no line contains {needle!r}")


def _rng(start: Position, end: Position) -> Dict[str, Dict[str, int]]:
    return {
        "start": {"line": start[0], "character": start[1]},
        "end": {"line": end[0], "character": end[1]},
    }


def rng(sl: int, sc: int, el: int, ec: int) -> Dict[str, Dict[str, int]]:
    return _rng((sl, sc), (el, ec))


def apply_range_edit(text: str, r: Dict[str, Dict[str, int]], new_text: str) -> str:
    s = offset_of(text, (r["start"]["line"], r["start"]["character"]))
    e = offset_of(text, (r["end"]["line"], r["end"]["character"]))
    return text[:s] + new_text + text[e:]


def text_in_range(text: str, r: Dict[str, Dict[str, int]]) -> str:
    s = offset_of(text, (r["start"]["line"], r["start"]["character"]))
    e = offset_of(text, (r["end"]["line"], r["end"]["character"]))
    return text[s:e]


@dataclass
class Document:
    """One open text document, mirroring what we told the server."""

    uri: str
    path: str
    language_id: str
    text: str
    version: int = 1
    open: bool = False
    history: List[Tuple[Dict[str, Dict[str, int]], str, str]] = field(default_factory=list)

    def bump(self) -> int:
        self.version += 1
        return self.version

    def apply(self, r: Dict[str, Dict[str, int]], new_text: str) -> Tuple[Dict[str, Dict[str, int]], str]:
        """Apply an edit locally; return the inverse edit (range, text) for undo."""
        replaced = text_in_range(self.text, r)
        self.text = apply_range_edit(self.text, r, new_text)
        s_line = r["start"]["line"]
        s_char = r["start"]["character"]
        new_end = position_of(new_text, len(new_text))
        if new_end[0] == 0:
            inv_end = (s_line, s_char + new_end[1])
        else:
            inv_end = (s_line + new_end[0], new_end[1])
        inverse = (_rng((s_line, s_char), inv_end), replaced)
        self.history.append((r, new_text, replaced))
        return inverse


def uri_for(path: str) -> str:
    abspath = path if path.startswith("/") else "/" + path
    return "file://" + abspath


def language_for(path: str) -> str:
    if path.endswith(".py") or path.endswith(".pyi"):
        return "python"
    if path.endswith(".java"):
        return "java"
    if path.endswith(".json"):
        return "json"
    return "plaintext"


__all__ = [
    "Document",
    "apply_range_edit",
    "end_position",
    "find_line",
    "find_range",
    "language_for",
    "line_range",
    "offset_of",
    "position_of",
    "rng",
    "text_in_range",
    "uri_for",
]
