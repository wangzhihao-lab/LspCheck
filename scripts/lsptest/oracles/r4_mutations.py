"""Seeded mutations that plant a fixable error in a clean file, so that the quick fixes of
the r4_edits oracle get exercised on real projects (oracles/r4_seeded.py runs them).

- M1 remove one import: one name of a multi-name import, else the whole statement; the
  bound name must be used elsewhere in the file -> unresolved names ("add import" fixes);
- M2 misspell one use of an identifier: drop or duplicate its middle character; not the
  name's first occurrence, not a member or path segment, not a declaration or assignment
  target, and the new name must not exist -> "did you mean" / spelling fixes;
- M3 delete the last argument of a call (callees declared in the same file first), or one
  member of a TypeScript object literal / Rust struct expression -> "add missing
  argument / properties / fields" fixes;
- M4 insert an unused local binding at the top of a function body, or an unused import
  after the last top-level import -> "remove unused" fixes.

The generators are lexical and share one structure for Python, TypeScript/JavaScript,
Go and Rust (identifier tokens from targets.identifiers, which skip comments and strings;
brackets matched with literals skipped, oracles/r4_lexical.py). `plan_mutations` takes,
per kind, the first candidate in a seeded order (priority first) that adds no parse error
under the syntax classifier, so a mutation plants a semantic error only.

Run line: imported by oracles/r4_seeded.py and oracles/r4_edits.py; not run directly.
"""

from __future__ import annotations

import os
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from model import Op  # noqa: E402
from ops import LineIndex  # noqa: E402
from oracles.r4_lexical import imports, match_bracket, remove_item, split_top  # noqa: E402
from oracles.syntax import new_errors, syntax_errors  # noqa: E402
from targets import FAMILY, KEYWORDS, Token, identifiers  # noqa: E402

KINDS = ("M1", "M2", "M3", "M4")
UNUSED = {"py": "r4_unused", "js": "r4Unused", "go": "r4Unused", "rs": "r4_unused"}
_DECL_BEFORE = re.compile(r"(?:\b(?:def|class|function|const|let|var|fn|func|type|interface|struct|enum|trait|impl|"
                          r"mod|import|from|use|package|as|mut|static|namespace|module|declare)\s+|[.]\s*|::\s*)$")
# Declaration or assignment targets, also in a comma list (`a, err :=`, `for k, v := range`, `for x in`), and
# a word before a string (`from 'x'`, a contextual keyword): not uses.
_ASSIGNED = re.compile(r"\s*(?:,\s*[\w$.]+\s*)*(?::=|=(?![=>])|\bin\b)|\s*['\"`]")


@dataclass(frozen=True)
class Mutation:
    kind: str  # M1 .. M4
    what: str  # what the mutation does, for notes and reports
    start: int  # character offsets into the original text
    end: int
    text: str  # replacement
    priority: int = 1  # lower first (before the seeded order)

    def apply(self, src: str) -> str:
        return src[: self.start] + self.text + src[self.end :]

    def op(self, path: str, src: str) -> Op:
        idx = LineIndex(src)
        return Op("change", path=path, start=idx.position(self.start), end=idx.position(self.end), text=self.text)

    def to_json(self) -> Dict[str, object]:
        return {"id": self.kind, "what": self.what}


def _fam(language: str) -> str:
    return FAMILY.get(language, language)


def _counts(toks: Sequence[Token]) -> Counter:
    return Counter(t.text for t in toks)


# ------------------------------------------------------------------ M1: remove an import
def m1_candidates(text: str, language: str) -> List[Mutation]:
    fam, out = _fam(language), []
    counts = _counts(identifiers(text, language))
    for st in imports(text, fam):
        for item in st.items:
            if counts.get(item.bound, 0) < (1 if fam == "go" and "." not in item.bound else 2) \
                    or item.bound in ("_", "."):
                continue  # not used elsewhere: removing it plants no error
            if item.removal is not None:
                out.append(Mutation("M1", f"remove '{item.bound}' from an import", *item.removal, ""))
            elif len(st.items) == 1 or all(i.removal is None for i in st.items):
                out.append(Mutation("M1", f"remove the import of '{item.bound}'", *st.span, "", priority=2))
    return out


# ------------------------------------------------------------------ M2: misspell one use
def m2_candidates(text: str, language: str) -> List[Mutation]:
    fam = _fam(language)
    toks = identifiers(text, language)
    counts, names, seen, out = _counts(toks), {t.text for t in toks}, set(), []
    for t in toks:
        first = t.text not in seen
        seen.add(t.text)
        if first or len(t.text) < 4 or counts[t.text] < 2 or _DECL_BEFORE.search(text[max(0, t.start - 24) : t.start]) \
                or _ASSIGNED.match(text, t.end):
            continue
        k = len(t.text) // 2
        for new in (t.text[:k] + t.text[k + 1 :], t.text[: k + 1] + t.text[k:]):
            if new not in names and new not in KEYWORDS.get(fam, ()) and new != t.text:
                verb = "drop" if len(new) < len(t.text) else "duplicate"
                out.append(Mutation("M2", f"misspell '{t.text}' as '{new}' ({verb} a middle character)", t.start,
                                    t.end, new))
    return out


# ------------------------------------------------------------------ M3: drop an argument or a member
_DECL_KEYWORD = re.compile(r"\b(?:def|function|fn|func)\s*$")
_MODIFIERS = re.compile(r"^\s*(?:(?:public|private|protected|static|async|get|set|override|readonly|abstract)\s+)*$")


def _calls(text: str, fam: str, toks: Sequence[Token]) -> List[Mutation]:
    declared = {m.group(1) for m in re.finditer(r"\b(?:def|function|fn|func)\s+(?:\([^)]*\)\s*)?(\w+)", text)}
    out = []
    for t in toks:
        paren = t.end
        if not text.startswith("(", paren):
            continue
        head = text[text.rfind("\n", 0, t.start) + 1 : t.start]
        if _DECL_KEYWORD.search(head) or fam == "go" and re.match(r"\s*func\s*\(", head):
            continue  # def f( / function f( / fn f( / func f( / func (r T) M(
        close = match_bracket(text, paren, fam)
        if close is None:
            continue
        after = text[close + 1 : close + 40].lstrip()
        if fam == "js" and (after.startswith(("{", "=>")) or _MODIFIERS.match(head) and after.startswith(":")):
            continue  # a method or function declaration, or arrow parameters
        args = split_top(text, paren + 1, close, fam)
        if args:
            span = remove_item(args, len(args) - 1) if len(args) >= 2 else args[0]
            out.append(Mutation("M3", f"drop the last argument of '{t.text}(...)'", *span, "",
                                priority=0 if t.text in declared else 1))
    return out


_TYPED_OBJECT = re.compile(r":\s*[\w$.<>\[\], |]+\s*=\s*$")
_JS_MEMBER = re.compile(r"^(?:[\w$]+|'[^']*'|\"[^\"]*\")\s*:|^[\w$]+$")
_RS_MEMBER = re.compile(r"^[a-z_]\w*\s*(?::|$)")
_RS_PATTERN = re.compile(r"\b(?:struct|enum|impl|trait|union|type|let|for|match|mod|if\s+let|while\s+let)\s+"
                         r"[A-Z]\w*(?:::\w+)*\s*$")


def _members(text: str, fam: str) -> List[Mutation]:
    """One member of a TypeScript object literal (after =, (, , or return) or of a Rust struct
    expression; literals with spreads, methods or a struct base are skipped."""
    if fam not in ("js", "rs"):
        return []
    out = []
    for m in re.finditer(r"\{", text):
        head = text[text.rfind("\n", 0, m.start()) + 1 : m.start()]
        if fam == "js":
            if not re.search(r"(?:[^=!<>]=|\(|,|\breturn)\s*$", head) or head.rstrip().endswith("=>"):
                continue
            typed, member = bool(_TYPED_OBJECT.search(head)), _JS_MEMBER
        else:
            if not re.search(r"(?:^|[=(,{]|=>|\breturn)\s*[A-Z]\w*(?:::\w+)*\s*$", head) or _RS_PATTERN.search(head) \
                    or "->" in head:
                continue
            typed, member = True, _RS_MEMBER
        close = match_bracket(text, m.start(), fam)
        if close is None or text[close + 1 : close + 20].lstrip().startswith(("=>", "|", "=")):
            continue
        members = split_top(text, m.start() + 1, close, fam)
        if not members or not all(member.match(text[a:b]) for a, b in members):
            continue
        for k, (a, b) in enumerate(members):
            name = re.match(r"[\w$'\"]+", text[a:b]).group()  # type: ignore[union-attr]
            span = remove_item(members, k) if len(members) >= 2 else (a, b)
            out.append(Mutation("M3", f"drop member {name} of a literal", *span, "", priority=0 if typed else 1))
    return out


def m3_candidates(text: str, language: str) -> List[Mutation]:
    fam = _fam(language)
    return _calls(text, fam, identifiers(text, language)) + _members(text, fam)


# ------------------------------------------------------------------ M4: insert an unused binding
_BODY_START: Dict[str, "re.Pattern[str]"] = {
    "py": re.compile(r"^([ \t]*)(?:async[ \t]+)?def[ \t]+\w+[^\n]*:[ \t]*(?:#[^\n]*)?\n", re.M),
    "js": re.compile(r"^([ \t]*)(?!(?:if|for|while|switch|catch|else|do|try|with|return)\b)[^\n]*\)[ \t]*"
                     r"(?::[^\n{]+)?(?:=>[ \t]*)?\{[ \t]*\n", re.M),
    "go": re.compile(r"^()func\b[^\n]*\{[ \t]*\n", re.M),
    "rs": re.compile(r"^([ \t]*)(?:pub(?:\([\w ]+\))?[ \t]+)?(?:(?:async|const|unsafe)[ \t]+)*fn[ \t]+\w+[^\n]*\{[ \t]*\n",
                     re.M),
}
_LOCAL = {"py": "{i}r4_unused = 0\n", "js": "{i}const r4Unused = 0;\n", "go": "{i}r4Unused := 0\n",
          "rs": "{i}let r4_unused = 0;\n"}


def _locals(text: str, fam: str) -> List[Mutation]:
    out = []
    for m in _BODY_START[fam].finditer(text):
        nxt = re.compile(r"^([ \t]*)\S", re.M).search(text, m.end())
        if nxt is None:
            continue
        indent = nxt.group(1) if len(nxt.group(1)) > len(m.group(1)) else m.group(1) + ("\t" if fam == "go" else "    ")
        if fam == "py" and len(nxt.group(1)) <= len(m.group(1)):
            continue  # a one-line def
        out.append(Mutation("M4", "insert an unused local binding", m.end(), m.end(), _LOCAL[fam].format(i=indent)))
    return out


def _unused_import(text: str, fam: str) -> List[Mutation]:
    stmts = [s for s in imports(text, fam) if s.top]
    if not stmts:
        return []
    last = stmts[-1]
    if fam == "py":
        line = "import sys as r4_unused\n"
    elif fam == "js":
        spec = next((s.spec for s in stmts if s.spec), "")
        if not spec:
            return []
        semi = ";" if text[last.span[0] : last.span[1]].rstrip().endswith(";") else ""
        line = f"import * as r4Unused from '{spec}'{semi}\n"
    elif fam == "go":
        spec = next((s.spec for s in stmts if s.spec), "")
        if not spec:
            return []
        block = text[last.span[0] : last.span[1]]
        if block.rstrip().endswith(")"):
            at = last.span[0] + block.rstrip().rfind(")")
            return [Mutation("M4", "insert an unused import", at, at, f'\tr4unused "{spec}"\n')]
        line = f'import r4unused "{spec}"\n'
    else:
        line = "use std::fmt::Write as R4Unused;\n"
    return [Mutation("M4", "insert an unused import", last.span[1], last.span[1], line)]


def m4_candidates(text: str, language: str) -> List[Mutation]:
    fam = _fam(language)
    if fam not in _BODY_START or UNUSED[fam] in text:
        return []
    return _locals(text, fam) + _unused_import(text, fam)


GENERATORS: Dict[str, Callable[[str, str], List[Mutation]]] = {
    "M1": m1_candidates, "M2": m2_candidates, "M3": m3_candidates, "M4": m4_candidates,
}


def plan_mutations(text: str, language: str, abspath: str, seed: int, path: str,
                   kinds: Sequence[str] = KINDS, attempts: int = 8) -> List[Mutation]:
    """Per kind, the first candidate (priority, then seeded order) that adds no parse error."""
    before = syntax_errors(language, text, abspath)
    out = []
    for kind in kinds:
        rng = random.Random(f"mutation:{seed}:{path}:{kind}")
        cands = sorted(GENERATORS[kind](text, language), key=lambda m: (m.priority, rng.random()))
        for m in cands[:attempts]:
            if not new_errors(before, syntax_errors(language, m.apply(text), abspath)):
                out.append(m)
                break
    return out


__all__ = ["GENERATORS", "KINDS", "Mutation", "m1_candidates", "m2_candidates", "m3_candidates", "m4_candidates",
           "plan_mutations"]
