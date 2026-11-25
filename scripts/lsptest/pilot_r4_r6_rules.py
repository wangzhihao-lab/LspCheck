"""Candidate review rules for the r4_edits / r6_crossimpl pilot: each rule matches one
evidence pattern and words the verdict's evidence from the candidate's own data (first
match wins; no match: "unreviewed"). Written after inspecting the pilot's candidates;
also the tool artifacts found and fixed during the pilot, and the known limits.

Run line: imported by pilot_r4_r6_review.py; not run directly.
"""

from __future__ import annotations

import difflib
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

Cand = Dict[str, Any]


@dataclass(frozen=True)
class Verdict:
    label: str  # likely-real | legitimate-difference | tool-artifact | unreviewed
    evidence: str


def _case(c: Cand) -> Dict[str, Any]:
    return json.loads(c["violation"]["detail"]).get("case", {})


def labels(xs: Any) -> List[str]:
    return [json.loads(x) for x in xs or []]


UMD_GLOBALS = {"React": "@types/react", "ReactDOM": "@types/react-dom", "ReactDOMServer": "@types/react-dom/server",
               "babel": "@types/babel__core"}  # `export as namespace <name>` in the pilot projects' dependencies


def _umd_only(job: str, c: Cand) -> Optional[Verdict]:
    v, case = c["violation"], _case(c)
    only_ref, only_test = labels(case.get("only_reference")), labels(case.get("only_test"))
    if not v["signature"].endswith("r6_crossimpl|completion:missing") or only_test or not only_ref:
        return None
    if not all(x in UMD_GLOBALS for x in only_ref):
        return None
    names = ", ".join(f"{x} from {UMD_GLOBALS[x]}" for x in only_ref)
    return Verdict("likely-real", f"the in-scope names only ts6 offers are UMD globals ({names}, declared with "
                   "`export as namespace`); the rest of the in-scope label set is identical. TypeScript 6.0.3's "
                   "completion filter (typescript.js) drops a UMD global in a module without allowUmdGlobalAccess "
                   "only when the same symbol is also offered as an auto-import or local; otherwise it keeps it, as "
                   "ts6 does here (sortText 15). A probe after the pilot (redux scripts/clean.mts:1:23, zustand "
                   "src/vanilla/shallow.ts:22:14) found no ts7 item with these names at all, in scope or as "
                   "auto-import, so ts7 7.0.2 departs from that rule; not in CHANGES.md (upstream issues not "
                   "searched).")


_UNTYPED_CALL = re.compile(r"^\((parameter|const|let|var|property)\) [\w$.]+: \(\) => any$")


def _untyped_callee(job: str, c: Cand) -> Optional[Verdict]:
    v = c["violation"]
    exp, act = v.get("expected"), v.get("actual")
    if v["key"]["method"] != "hover" or "|r6_crossimpl|" not in v["signature"] or not isinstance(exp, str) \
            or not isinstance(act, str):
        return None
    if not (_UNTYPED_CALL.match(act) and re.search(r": (any|Function)$", exp)):
        return None
    return Verdict("likely-real", f"hover on the callee of an untyped call (its type is `any` or `Function`): ts6 shows the "
                   f"declared type ({exp!r}), ts7 shows {act!r}, the synthetic signature of untyped calls, which misstates "
                   "the type (the call may pass arguments). TypeScript 6.0.3's quick info (typescript.js, symbol display "
                   "at call expressions) drops a resolved signature that is not one of the callee type's own call "
                   "signatures, and `any`/`Function` have none; ts7 lacks that check. Not in CHANGES.md.")


def _alias_keyword(job: str, c: Cand) -> Optional[Verdict]:
    v = c["violation"]
    exp, act = v.get("expected"), v.get("actual")
    if isinstance(exp, str) and isinstance(act, str) and exp.startswith("(alias) ") and \
            act.replace("(alias) function ", "(alias) ", 1) == exp:
        return Verdict("legitimate-difference", "same signature; ts7 prints the `function` keyword after `(alias)` at a call "
                       "site, ts6 does not (presentation of the hover, not a different type).")
    return None


_TYPE_ARGS = re.compile(r"^<[^<>]*(<[^<>]*>[^<>]*)*>$")


def _printed_type_args(job: str, c: Cand) -> Optional[Verdict]:
    v = c["violation"]
    exp, act = v.get("expected"), v.get("actual")
    if not isinstance(exp, str) or not isinstance(act, str) or len(act) <= len(exp):
        return None
    ops = difflib.SequenceMatcher(None, exp, act, autojunk=False).get_opcodes()
    inserted = [act[j1:j2] for tag, _, _, j1, j2 in ops if tag != "equal"]
    if all(tag in ("equal", "insert") for tag, *_ in ops) and inserted and all(_TYPE_ARGS.match(x) for x in inserted):
        return Verdict("legitimate-difference", f"ts7 prints type arguments {inserted} that ts6 leaves implicit (the default type "
                       "arguments of the same generic type); same type, different printing.")
    return None


def _ra_macro(job: str, c: Cand) -> Optional[Verdict]:
    v, case = c["violation"], _case(c)
    if "rust-analyzer|r4_edits|completionInsert" not in v["signature"] or not str(case.get("label", "")).startswith("vec!"):
        return None
    return Verdict("likely-real", f"rust-analyzer offers the macro item {case.get('label')!r} after {case.get('name')!r}, where "
                   f"a macro call cannot stand ({case.get('excerpt', '').strip()!r}: {case.get('new_errors')}); accepting it "
                   "yields a parse error. Low severity: completion context, not a wrong edit.")


_TOKEN = re.compile(r"\w+|[^\w\s]")
CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "temp", "corpus")


def _hover_pair(c: Cand) -> Optional[Tuple[str, str]]:
    v = c["violation"]
    exp, act = v.get("expected"), v.get("actual")
    if v["key"]["method"] != "hover" or not isinstance(exp, str) or not isinstance(act, str):
        return None
    return exp, act


def _alias_declaration(project: str, name: str) -> Optional[str]:
    """`type name = ...` (single line) in the project's TypeScript sources, as written."""
    rx = re.compile(rf"^\s*(?:export\s+)?type\s+{re.escape(name)}\s*=\s*(.+?)\s*;?\s*$")
    for dirpath, dirnames, files in os.walk(os.path.join(CORPUS, project)):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "dist")]
        for f in files:
            if f.endswith((".ts", ".tsx", ".mts", ".cts")) and not f.endswith(".d.ts"):
                try:
                    with open(os.path.join(dirpath, f), encoding="utf-8", errors="replace") as fh:
                        for line in fh:
                            m = rx.match(line)
                            if m:
                                return f"{os.path.relpath(os.path.join(dirpath, f), os.path.join(CORPUS, project))}: {m.group(1)}"
                except OSError:
                    continue
    return None


def _alias_expanded(job: str, c: Cand, project: str = "") -> Optional[Verdict]:
    pair = _hover_pair(c)
    if pair is None:
        return None
    e, a = _TOKEN.findall(pair[0]), _TOKEN.findall(pair[1])
    ops = difflib.SequenceMatcher(None, e, a, autojunk=False).get_opcodes()
    reps = {(" ".join(e[i1:i2]), " ".join(a[j1:j2])) for tag, i1, i2, j1, j2 in ops if tag != "equal"}
    if len(reps) != 1 or any(tag not in ("equal", "replace") for tag, *_ in ops):
        return None
    name, expansion = next(iter(reps))
    decl = _alias_declaration(project, name) if re.fullmatch(r"\w+", name) else None
    if not decl or " ".join(_TOKEN.findall(decl.split(": ", 1)[1])) != expansion:
        return None
    return Verdict("legitimate-difference", f"same type: ts6 prints the alias `{name}`, ts7 prints its expansion "
                   f"(declared in {decl}); alias preservation in type printing, not a different type.")


def _constraint_repeated(job: str, c: Cand, project: str = "") -> Optional[Verdict]:
    pair = _hover_pair(c)
    m = re.match(r"^\(type parameter\) (\w+) extends (.+?) in ", pair[1]) if pair else None
    if not m or pair[1].replace(f" {m.group(1)} extends {m.group(2)} in ", f" {m.group(1)} in ", 1) != pair[0]:
        return None
    return Verdict("legitimate-difference", f"ts7 repeats the constraint `extends {m.group(2)}` after the type "
                   "parameter; ts6 shows it only in the declaration that follows. Same information.")


def _signature_display(job: str, c: Cand, project: str = "") -> Optional[Verdict]:
    pair = _hover_pair(c)
    if pair is None or not re.search(r" \(\+\d+ overloads?\)$", pair[0]) or re.search(r"\(\+\d+ overload", pair[1]):
        return None
    exp = re.sub(r" \(\+\d+ overloads?\)$", "", pair[0])
    lost = [f"the overload count {re.search(r'[(][+][0-9]+ overloads?[)]', pair[0]).group(0)}"]
    typed = re.match(r"^((?:var|let|const) [\w$]+: )([\w$.]+) (new |\()", exp)
    if typed and pair[1].startswith(typed.group(1) + typed.group(3)):
        exp = typed.group(1) + exp[len(typed.group(1)) + len(typed.group(2)) + 1:]
        lost.append(f"the declared type `{typed.group(2)}`")
    order = exp != pair[1] and sorted(exp.replace(" ", "")) == sorted(pair[1].replace(" ", ""))
    if exp != pair[1] and not order:
        return None
    return Verdict("likely-real", "quick info at a call or `new` of an overloaded callee: ts7 prints only the resolved "
                   f"signature and drops {' and '.join(lost)}, which TypeScript 6.0.3 prints (declared type line, then "
                   "the signature with the overload count), so the callee reads as if it had that one signature. "
                   "Low severity (presentation)"
                   + ("; the union members are also printed in another order (same type)." if order else "."))


def _seeded_case(c: Cand) -> Optional[Dict[str, Any]]:
    case = _case(c)
    return case if case.get("kind") == "mutation" else None


def _mutation_leftover(job: str, c: Cand) -> Optional[Verdict]:
    case = _seeded_case(c)
    if not case or case.get("check") != "errors" or case.get("fix_introduced_errors"):
        return None
    return Verdict("legitimate-difference", f"the fix {case.get('title')!r} for {case['diag'].get('code')} does what it says; "
                   f"the errors left are other diagnostics the mutation ({case['mutation']['what']}) created, which "
                   f"this fix does not target (errors before the mutation {case.get('base_errors')}, after the fix "
                   f"{case.get('post_errors')}; none introduced by the fix).")


def _gopls_zero_variable(job: str, c: Cand) -> Optional[Verdict]:
    case = _seeded_case(c)
    fix_text = " ".join(str(o.get("text", "")) for o in (case or {}).get("fix_ops") or [])
    if not case or not str(case.get("title", "")).startswith("Create variable") or ":= 0" not in fix_text \
            or not case.get("fix_introduced_errors"):
        return None
    intro = [f"{e.get('code')}: {e.get('message')}" for e in case["fix_introduced_errors"]][:2]
    return Verdict("likely-real", f"gopls's undeclared-name fix {case.get('title')!r} declares the variable as `... := 0` "
                   f"(type int) because it infers no type from the use, and the fix itself then produces {intro}; "
                   "here the use is a two-variable range clause over a map. A development run hit the same fallback "
                   "for an argument of append on a []string. Low severity: the offered declaration cannot fit the use.")


def _mutation_introduced(job: str, c: Cand) -> Optional[Verdict]:
    case = _seeded_case(c)
    if not case or case.get("check") != "errors" or not case.get("fix_introduced_errors"):
        return None
    intro = [f"{e.get('code')}: {e.get('message')}" for e in case["fix_introduced_errors"]][:3]
    return Verdict("likely-real", f"the fix {case.get('title')!r} for {case['diag'].get('code')} ({case['diag'].get('message')}) "
                   f"introduces errors the mutated state did not have: {intro} (errors before the mutation "
                   f"{case.get('base_errors')}, after the fix {case.get('post_errors')}; seeded by {case['mutation']['what']}).")


REVIEW: List[Callable[..., Optional[Verdict]]] = [
    _umd_only, _untyped_callee, _alias_keyword, _printed_type_args, _alias_expanded, _constraint_repeated,
    _signature_display, _ra_macro, _mutation_leftover, _gopls_zero_variable, _mutation_introduced]


def classify(job: str, c: Cand, project: str = "") -> Verdict:
    for rule in REVIEW:
        verdict = rule(job, c, project=project) if rule in PROJECT_RULES else rule(job, c)
        if verdict is not None:
            return verdict
    return Verdict("unreviewed", "no review rule matches this candidate")


PROJECT_RULES = (_alias_expanded, _constraint_repeated, _signature_display)


TOOL_ARTIFACTS = [
    "Contextual keywords were targets: the tokenizer knows only reserved words, so `from` in `import {...} from "
    "'./util'` became a completion target and every identifier replacing it broke the import (16 findings on the "
    "ts6/ts7 fixture). Fixed: a position where renaming the word to word+'x' already breaks the syntax is not an "
    "identifier position and is skipped.",
    "The editor filter accepted any subsequence (`from` matched `CSSTransformComponent`); it now requires the "
    "first typed character at a word start of the label, as editors do.",
    "Module items insert a path prefix (`i32::`), unfinished by design, and were flagged as syntax errors; "
    "items whose inserted text ends in `::`, `.` or `/` are now skipped (path-prefix-item).",
    "R6 hover: typescript-language-server echoes `import X` after an `(alias)` line; the echo is dropped from "
    "the compared type text.",
    "R6 hover: ts6 renders JSDoc @default values in a second code fence, ts7 as text; comparing every fence gave "
    "4 false differences on redux. Only the first fence (the signature) is compared now.",
    "R6 completion: auto-import suggestions differed at most completion positions (both directions: ts6 offered "
    "exports of `typescript` and of Node's ambient modules, ts7 package subpaths such as vitest/node and rolldown) "
    "and masked the in-scope labels. They are now excluded from the comparison with the engine's marker "
    "(completion_kind.is_auto_import, which the completion normalizer also uses since this pilot; its ts6 case, "
    "unresolved typescript-language-server items marked only by sortText U+FFFF+'16', was added from this pilot's "
    "data); each run notes at how many positions the excluded sets differ.",
    "Command-only quick fixes: pyright's createtypestub writes stub files; only commands known to compute an "
    "edit and nothing else are followed (EDIT_ONLY_COMMANDS).",
    "rust-analyzer could not format: the default rustup toolchain lacks the rustfmt component. R4 sessions "
    "override rust-analyzer's rustfmt command with the rustfmt of the installed 1.98.1 toolchain (same rustc "
    "build as stable) and the project's edition.",
    "The first Rust fixture had only rustc-lint diagnostics (unused variables/imports), which rust-analyzer does "
    "not report with checkOnSave off; the fixture now has diagnostics rust-analyzer computes itself.",
    "Seeded M2 misspelled declaration targets in comma lists (`output, err :=`, `for name, ok := range`), which "
    "declares a new name instead of breaking a use; the findings were the mutation's own leftover errors. "
    "Comma-list assignment targets and loop variables (`:=`, `=`, `in`) are no longer M2 sites.",
    "Seeded replay compared the recorded fix ops read back from JSON (lists) with Op.to_json() (tuples) and never "
    "reproduced; it now compares Op objects.",
]
LIMITS = [
    "No corpus target file had a diagnostic with a quick fix, so quick fixes were exercised on the fixtures only.",
    "Python's parser reports the first syntax error only; before/after comparison is by message, positions ignored.",
    "Completion findings are confirmed in a fresh session on the original content; the running session had no edits "
    "then, so an unconfirmed one is dropped as nondeterminism rather than filed as r1-suspect.",
    "No edit-based finding occurred, so r1-suspect filing ran only in unit tests and a synthetic replay.",
    "R6 intended-difference rules encode CHANGES.md (compiler changes: JavaScript/JSDoc, checker, parser); it says "
    "nothing about language-service presentation, so no pilot candidate matched a rule.",
    "R6 does not compare auto-import suggestions (see above), so a server that loses an auto-import source "
    "entirely goes unnoticed by R6.",
    "Seeded quick fixes: rust-analyzer's own diagnostics (checkOnSave off) do not report unresolved imports or "
    "names or unused bindings, so M1, M2 and M4 create no diagnostic there; only M3 (missing arguments, missing "
    "fields) does. pyright offers no quick fix for the diagnostics the mutations create.",
    "The seeded errors check compares with the pre-mutation error count, as specified, so a fix that leaves "
    "another error of the same mutation is reported; the case records the errors the fix itself introduced, "
    "and findings without any are classified legitimate.",
    "Mutations are lexical (per-language patterns, validated by the syntax classifier); a mutation that creates no "
    "diagnostic is counted and skipped.",
]


__all__ = ["LIMITS", "PROJECT_RULES", "REVIEW", "TOOL_ARTIFACTS", "Verdict", "classify", "labels"]
