"""Screening decisions: tsserver, second-round sheet tsserver_r2_00.txt.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "tsserver"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    42180: ("R4", "A", "Completions after 'asserts' in a return type list types and keywords with 'void' first; accepting one yields an invalid asserts predicate, and the fix limits the list to parameter names.", "completion: at 'asserts v' accept the top items; check new syntax or type errors (keyword and type items)"),
    45533: ("R4", "A", "For a variable of a string enum type, completions suggest the enum member values such as \"str\" instead of member names; accepting one gives a type error.", "completion: const es: ES = <complete>; accept the literal item; check new type error"),
    48215: ("R4", "B", "Class-member snippet completions for abstract methods whose types contain template literal types break; the fix formats the snippet text before escaping it, so the inserted text was mis-escaped.", "completion: snippet client with class member snippets; accept the method item; check syntax or type errors"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "display": (29234, 33615, 35582, 39346, 43289, 44302),
}
