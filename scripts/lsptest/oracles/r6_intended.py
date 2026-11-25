"""Documented intended differences between TypeScript 6 (Strada) and TypeScript 7 (Corsa),
used by the r6_crossimpl oracle to tag its candidates.

Source: microsoft/typescript-go, CHANGES.md ("intentional changes between the Strada
(TypeScript) and Corsa (Go) compilers"), fetched 2026-09-23 from
raw.githubusercontent.com, 17102 bytes, sha256 in SOURCE. Each rule below cites the
section it encodes and matches a candidate by what the section changes: JavaScript
files using JSDoc tags, expando declarations or CommonJS syntax; conflicting-declaration
errors (skipLibCheck section); argument-count errors when "strict" is off; parse versus
grammar errors (parser section); async functions returning non-Promises in JavaScript;
template literal inference over supplementary-plane characters. The scanner's UTF-8
offsets are internal (LSP positions stay UTF-16), so no rule encodes them.

A tag means "a documented intended difference may explain this candidate"; it is a triage
hint, not a verdict. `check_source` re-fetches the document once (bounded) and reports
whether it still has the recorded hash, so the rules can be reviewed when it changes.

Run line: imported by oracles/r6_crossimpl.py; not run directly.
"""

from __future__ import annotations

import hashlib
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

SOURCE: Dict[str, str] = {
    "url": "https://raw.githubusercontent.com/microsoft/typescript-go/main/CHANGES.md",
    "sha256": "4519ec0a93607319a96f4feb967aa06a251ccc816544e2fed5c985c1d45dc11a",
    "fetched": "2026-09-23",
    "title": "CHANGES.md lists intentional changes between the Strada (TypeScript) and Corsa (Go) compilers.",
}
JS_EXTENSIONS = (".js", ".jsx", ".mjs", ".cjs")
CONFLICT_CODES = frozenset({"2300", "2393", "2395", "2403", "2428", "2440", "2451", "2687", "2717", "6200"})
ARGUMENT_CODES = frozenset({"2554", "2555", "2556"})
ASYNC_CODES = frozenset({"1055", "1064", "2705"})
_JSDOC_TAG = re.compile(r"@(type|param|returns?|typedef|callback|enum|class|constructor|template|overload|author|"
                        r"this|extends|augments|implements|satisfies|import)\b")
_EXPANDO = re.compile(r"\.prototype\b|^\s*this\.\w+\s*(=|;)|\bvoid 0\b|\b\w+\.\w+\s*=\s*\w+\.\w+\s*\|\|")
_COMMONJS = re.compile(r"\bmodule\.exports\b|\bexports\.\w+|\brequire\s*\(")
_STRICT = re.compile(r'"strict"\s*:\s*true')


@dataclass(frozen=True)
class Candidate:
    """What the rules look at: the method, the file, its text, the lines and diagnostic
    codes involved in the difference, and whether the project compiles with "strict"."""

    method: str
    path: str
    text: str
    lines: Sequence[int] = ()
    codes: Sequence[str] = ()
    strict: Optional[bool] = None

    def is_js(self) -> bool:
        return self.path.lower().endswith(JS_EXTENSIONS)

    def near(self, before: int = 10) -> str:
        rows = self.text.splitlines()
        picked = {i for ln in self.lines for i in range(max(0, ln - before), min(len(rows), ln + 1))}
        return "\n".join(rows[i] for i in sorted(picked))

    def code_set(self) -> set:
        return {str(c) for c in self.codes if str(c)}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    section: str  # heading of CHANGES.md the rule encodes
    matches: Callable[[Candidate], bool] = field(compare=False)


def _codes_within(c: Candidate, allowed: frozenset) -> bool:
    return bool(c.code_set()) and c.code_set() <= allowed


RULES: List[Rule] = [
    Rule("js-jsdoc", "JavaScript support / JSDoc Tags and Types; Checker / JSDoc Types, JSDoc Tags",
         lambda c: c.is_js() and bool(_JSDOC_TAG.search(c.near()))),
    Rule("js-expando", "JavaScript support / Expando declarations; Checker / Expandos",
         lambda c: c.is_js() and bool(_EXPANDO.search(c.near(before=3)))),
    Rule("js-commonjs", "JavaScript support / CommonJS syntax; Checker / CommonJS",
         lambda c: c.is_js() and bool(_COMMONJS.search(c.text))),
    Rule("js-arguments", "Checker / Miscellaneous: `arguments` no longer implies a rest parameter",
         lambda c: c.is_js() and "arguments" in c.text and bool(c.code_set() & ARGUMENT_CODES)),
    Rule("nonstrict-omitted-arguments", "Checker / Miscellaneous: with strict false, no omitted arguments "
         "for parameters typed undefined, unknown or any",
         lambda c: c.method == "diagnostics" and c.strict is False and _codes_within(c, ARGUMENT_CODES)),
    Rule("conflicts-under-skiplibcheck", "Checker / Miscellaneous: Error reporting under --skipLibCheck",
         lambda c: c.method == "diagnostics" and _codes_within(c, CONFLICT_CODES)),
    Rule("parse-instead-of-grammar-error", "Parser: parse errors instead of grammar errors",
         lambda c: c.method == "diagnostics" and bool(c.code_set())
         and all(code.isdigit() and 1000 <= int(code) < 2000 for code in c.code_set())),
    Rule("js-async-non-promise", "Checker / JSDoc Tags: errors on async functions returning non-Promises",
         lambda c: c.is_js() and _codes_within(c, ASYNC_CODES)),
    Rule("template-literal-code-points", "Checker / Miscellaneous: template literal inference over code points",
         lambda c: "${" in c.near(before=2) and any(ord(ch) > 0xFFFF for ch in c.near(before=2))),
]


def tag(c: Candidate) -> List[Dict[str, str]]:
    """The documented intended differences that may explain a candidate."""
    return [{"rule": r.rule_id, "section": r.section} for r in RULES if r.matches(c)]


def project_strict(project_dir: str) -> Optional[bool]:
    """Whether the project's tsconfig (or a tsconfig*.json it ships) sets "strict": true;
    None when there is no tsconfig at all."""
    names = sorted(n for n in os.listdir(project_dir) if n.startswith("tsconfig") and n.endswith(".json")) \
        if os.path.isdir(project_dir) else []
    if not names:
        return None
    for name in names:
        try:
            with open(os.path.join(project_dir, name), "r", encoding="utf-8", errors="replace") as f:
                if _STRICT.search(f.read()):
                    return True
        except OSError:
            continue
    return False


def check_source(timeout: float = 30.0) -> Dict[str, str]:
    """One bounded fetch of the source document: unchanged | changed | unavailable."""
    try:
        req = urllib.request.Request(SOURCE["url"], headers={"User-Agent": "lsptest-r6"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"[:200]}
    digest = hashlib.sha256(body).hexdigest()
    return {"status": "unchanged" if digest == SOURCE["sha256"] else "changed", "sha256": digest,
            "bytes": str(len(body))}


__all__ = ["Candidate", "RULES", "Rule", "SOURCE", "check_source", "project_strict", "tag"]
