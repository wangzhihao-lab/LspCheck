"""Screening decisions: rust-analyzer, second-round sheet rust-analyzer_r2_00.txt.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "rust-analyzer"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    11005: ("R4", "A", "On-type formatting after typing '=' inserts a semicolon inside the parameter list of a function being turned into a closure, producing '(char, char);, u64>'; the fix skips insertion on parse errors.", "format: on-type formatting (typing '='), outside the designed textDocument/formatting check; check new syntax errors"),
    11357: ("R1", "C", "Checking out a much older git revision under a running server panics with 'no value set for FileSourceRootQuery'; the fix handles files whose source root is not yet set.", "file-op: replace many files on disk (adds and removes) via didChangeWatchedFiles; later requests must not panic"),
    12975: ("R4", "C", "After completion is requested at 'match e' and a space is typed, the reused list offers record items such as '&Enum::Var {...}' whose insertion is invalid; a fresh request after the space is fine.", "completion: reuse the list from 'match e$0' after typing a space; accept a record item; check syntax errors"),
    15626: ("R4", "B", "Completion after 'for foo.' offers a synthetic local named '<ra@gennew>N'; accepting it inserts text that is not valid Rust, where the document already has a syntax error.", "completion: complete after 'for foo.' in a fn body; compare syntax errors after accepting the synthetic item"),
    18130: ("R4", "A", "Completing a unit-returning function as the expression body of a closure appends ';', which breaks the closure when it is passed as an argument.", "completion: v.iter().for_each(|x| unit_f$0); accept the fn item; check syntax errors"),
    19694: ("R4", "A", "Completing the label 'r#break after break ' inserts 'break instead of 'r#break, which does not name the declared label.", "completion: accept the label item in the reported snippet; check new errors"),
    20998: ("R4", "A", "The .unsafe postfix completion on 'const { 1 }' produces 'unsafe const { 1 }', which is invalid Rust.", "completion: accept .unsafe postfix after const { 1 }; check syntax errors"),
    21461: ("R4", "A", "The remove-redundant-parentheses action on '(1 as u32) << 10' removes needed parentheses and the result no longer parses; the action is an assist, not a diagnostic fix.", "codeaction-other: apply remove parentheses on (1 as u32) << 10; check syntax errors"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "display": (12079, 12165, 12259, 12483, 13738, 18834, 18883, 18888, 21142, 21476, 22487),
    "type": (12505, 13757, 14701, 14871, 15943, 17458, 18445, 19637, 22007, 22573),
    "crash": (21237, 22262),
    "cli": (17739, 20067, 20113),
    "semantic_edit": (13370, 17540, 17895),
    "ui": (17036,),
    "feature": (17477,),
    "other": (15831, 18847, 19895),
}
