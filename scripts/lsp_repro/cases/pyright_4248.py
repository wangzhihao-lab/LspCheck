"""pyright #4248 -- "Document state gets de-synchronized on editing".

Reported repro (verbatim): "From (and including) build 1.1.280, the document
state gets de-synchronized easily in Sublime Text on editing the document." /
"To Reproduce: Just add some content to the document." / "Expected: Errors
reported only in expected places. Semantic highlighting properly applied to
relevant parts of the code." The reporter bisected the regression to pyright
commit 04a105837 "20221121 (#4174)"; 1.1.279 was fine.

Version pinning: 1.1.279 (2022-11-09) good, 1.1.280 (2022-11-16) first bad,
issue closed 2022-11-30 with the "addressed in next version" label, and 1.1.282
was published 2022-11-30 -- so pre = 1.1.280, post = 1.1.282. The exact fix
commit could not be identified: pyright squashes Pylance imports, and no commit
between the 1.1.281 and 1.1.282 tags mentions document synchronization.

The oracle relation used here is positional: after a sequence of incremental
range edits that returns the buffer to a known text, the diagnostic *ranges*
must be exactly those a fresh server reports for that text. A de-synchronized
document shows up as diagnostics at shifted offsets.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scenario import (  # noqa: E402
    Scenario,
    Step,
    edit,
    multi_edit,
    open_doc,
    quiesce,
    request,
    snapshot,
    undo,
    wait,
)
from snapshots import norm_hover  # noqa: E402
from textdoc import find_range, position_of, rng  # noqa: E402

SERVER = "pyright"
ISSUE = "microsoft/pyright#4248"
TITLE = "Document state gets de-synchronized on editing"
PRE = "1.1.280"
POST = "1.1.282"
SYMPTOM = "diagnostics land at wrong offsets after a run of incremental edits"
FIX_COMMIT = "not identified (regression bisected by reporter to 04a105837 #4174)"

VARIANTS = [
    "type_settled",
    "type_race",
    "block_settled",
    "block_race",
    "mixed_race",
    "batched_settled",
    "batched_race",
]

SRC = '''import os
import sys


def compute(values: list[int]) -> int:
    total = 0
    for v in values:
        total += v
    return total


def broken_one() -> int:
    return "not an int"


def broken_two(x: int) -> str:
    return x


class Holder:
    def __init__(self, name: str) -> None:
        self.name = name

    def label(self) -> str:
        return self.name


def use() -> None:
    h = Holder("a")
    print(h.label(), compute([1, 2, 3]), os.sep, sys.platform)
'''

TYPED = "def inserted_marker(q: int) -> str:\n    return q\n\n\n"


def _at_line(lineno: int):
    def fn(text: str) -> Dict[str, Dict[str, int]]:
        return rng(lineno, 0, lineno, 0)

    return fn


def _tail_of(needle: str):
    def fn(text: str) -> Dict[str, Dict[str, int]]:
        return find_range(text, needle)

    return fn


def _marker_pos(sess) -> Dict[str, Any]:
    d = sess.doc("repro.py")
    r = find_range(d.text, "def broken_one")
    return {"textDocument": {"uri": d.uri}, "position": {"line": r["start"]["line"], "character": 5}}


def _typing_steps(settle: bool) -> List[Step]:
    """Insert TYPED one character at a time at the top of the file, then remove it."""
    steps: List[Step] = []
    for i, ch in enumerate(TYPED):
        pos_line = TYPED[:i].count("\n")
        pos_col = len(TYPED[:i].split("\n")[-1])
        steps.append(
            Step(
                "edit",
                path="repro.py",
                range_fn=(lambda pl=pos_line, pc=pos_col: (lambda t: rng(pl, pc, pl, pc)))(),
                text=ch,
                label=f"type char {i}",
            )
        )
        if settle and i % 12 == 11:
            steps.append(quiesce("repro.py"))
    steps.append(quiesce("repro.py") if settle else wait(0.05))
    steps.append(snapshot("after_typing"))
    for _ in range(len(TYPED)):
        steps.append(undo("repro.py", label="untype char"))
    return steps


def _block_steps(settle: bool) -> List[Step]:
    """Paste a block, delete it again -- the shape from the linked reports."""
    steps: List[Step] = []
    for i in range(4):
        steps.append(edit("repro.py", _at_line(0), TYPED, label=f"paste block {i}"))
        if settle:
            steps.append(quiesce("repro.py"))
        steps.append(edit("repro.py", _tail_of("total += v"), "total  +=  v", label=f"widen line {i}"))
        if settle:
            steps.append(quiesce("repro.py"))
        steps.append(undo("repro.py", label=f"unwiden {i}"))
        steps.append(undo("repro.py", label=f"unpaste {i}"))
        if settle:
            steps.append(quiesce("repro.py"))
        else:
            steps.append(wait(0.02))
    return steps


def _batch(text: str) -> List[Any]:
    """Three edits in one notification, in increasing document order -- so the
    second and third ranges refer to the document as the earlier edits left it.
    Getting that wrong is exactly what "de-synchronized" looks like."""
    r1 = find_range(text, "total = 0")
    r2 = find_range(text, "return total")
    r3 = find_range(text, 'return "not an int"')
    return [(r1, "total = 0  # a"), (r2, "return total  # b"), (r3, 'return "still not an int"')]


def _unbatch(text: str) -> List[Any]:
    r1 = find_range(text, "total = 0  # a")
    r2 = find_range(text, "return total  # b")
    r3 = find_range(text, 'return "still not an int"')
    return [(r1, "total = 0"), (r2, "return total"), (r3, 'return "not an int"')]


def _batched_steps(settle: bool) -> List[Step]:
    steps: List[Step] = []
    for i in range(4):
        steps.append(multi_edit("repro.py", _batch, label=f"batched didChange {i}"))
        steps.append(quiesce("repro.py") if settle else wait(0.02))
        steps.append(multi_edit("repro.py", _unbatch, label=f"batched revert {i}"))
        steps.append(quiesce("repro.py") if settle else wait(0.02))
    return steps


def build(variant: str = "type_settled") -> Scenario:
    settle = variant.endswith("settled")
    steps: List[Step] = [open_doc("repro.py"), quiesce("repro.py"), snapshot("baseline")]
    if variant.startswith("type"):
        steps += _typing_steps(settle)
    elif variant.startswith("block"):
        steps += _block_steps(settle)
    elif variant.startswith("batched"):
        steps += _batched_steps(settle)
    else:
        steps += _typing_steps(False) + _block_steps(False)
    steps += [quiesce("repro.py"), snapshot("final_state")]
    return Scenario(
        name=f"pyright_4248[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files={"repro.py": SRC},
        watch=["repro.py"],
        steps=steps,
        probes=[request("textDocument/hover", _marker_pos, label="hover_broken_one", normalize=norm_hover)],
    )


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    snaps = {s["label"]: s["diagnostics"] for s in replay.get("snapshots", [])}
    base = {tuple(x) for x in snaps.get("baseline", {}).get("repro.py", [])}
    final = {tuple(x) for x in replay.get("final", {}).get("repro.py", [])}
    if not base:
        return False, "baseline had no diagnostics -- scenario cannot detect position drift"
    reasons = []
    if base != final:
        reasons.append(
            f"diagnostic set moved for identical text: base={sorted(base)[:2]} final={sorted(final)[:2]}"
        )
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        reasons.append(f"replay!=fresh: {diff.get('files') or diff.get('probes')}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    return False, f"stable: {len(base)} diagnostics at identical positions, replay==fresh"
