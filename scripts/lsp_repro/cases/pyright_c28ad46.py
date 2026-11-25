"""pyright, commit 28ad46148 -- "Fixed recent regression that caused unnecessary
reanalysis when closing a file when using pyright as an LSP. The regression also
sometimes resulted in unexpected errors from reanalyzed files including
diagnostics about unaccessed variables."

No issue number: the maintainer found and fixed this himself, so the commit
message is the only ground truth. It is kept in the set because it is a pure
didClose state bug with a scriptable shape, and because it lets the oracle be
tested on a case whose trigger is closing rather than editing a document.

Commit 28ad46148, 2022-02-22, first in tag 1.1.224.
Pre-fix 1.1.223 (2022-02-20), post-fix 1.1.224 (2022-02-23).

Scenario: two files where B imports A. Open both, edit B, close B, and check
that A's diagnostics (and a fresh server's view of the same final contents)
have not changed.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scenario import Scenario, Step, close_doc, edit, open_doc, quiesce, snapshot, wait  # noqa: E402
from textdoc import find_range  # noqa: E402

SERVER = "pyright"
ISSUE = "microsoft/pyright@28ad46148 (no issue filed)"
TITLE = "Unexpected errors from files reanalyzed on didClose"
PRE = "1.1.223"
POST = "1.1.224"
SYMPTOM = "closing one open file changes the diagnostics reported for another"
FIX_COMMIT = "28ad46148, 2022-02-22, first in tag 1.1.224"

VARIANTS = ["close_settled", "close_race", "close_reopen_race"]

LIB = '''from __future__ import annotations


def helper(x: int) -> str:
    unused_local = 1
    return str(x)


class Thing:
    def __init__(self, n: int) -> None:
        self.n = n
'''

APP = '''from __future__ import annotations

from lib import Thing, helper


def go() -> None:
    t = Thing(1)
    also_unused = 2
    print(helper(t.n))
'''


def _n_ref(text: str) -> Dict[str, Dict[str, int]]:
    return find_range(text, "Thing(1)")


def build(variant: str = "close_settled") -> Scenario:
    settle = variant.endswith("settled")
    steps: List[Step] = [
        open_doc("lib.py"),
        quiesce("lib.py"),
        open_doc("app.py"),
        quiesce("app.py"),
        snapshot("baseline"),
        edit("app.py", _n_ref, "Thing(2)", label="edit app.py"),
    ]
    steps.append(quiesce("app.py") if settle else wait(0.03))
    steps.append(close_doc("app.py", label="close app.py"))
    if not settle:
        steps.append(wait(0.03))
    if variant == "close_reopen_race":
        steps += [open_doc("app.py", label="reopen app.py"), wait(0.03), close_doc("app.py")]
    steps += [quiesce("lib.py"), snapshot("after_close")]
    return Scenario(
        name=f"pyright_c28ad46[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files={"lib.py": LIB, "app.py": APP},
        # Only lib.py stays open, so only its diagnostics are comparable.
        watch=["lib.py"],
        steps=steps,
        # The commit names "diagnostics about unaccessed variables", which are
        # off in basic mode, so they have to be switched on to be observable.
        settings_override={
            "python": {
                "analysis": {
                    "diagnosticSeverityOverrides": {
                        "reportUnusedVariable": "warning",
                        "reportUnusedImport": "warning",
                        "reportUnusedFunction": "warning",
                    }
                }
            }
        },
    )


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    snaps = {s["label"]: s["diagnostics"] for s in replay.get("snapshots", [])}
    base = {tuple(x) for x in snaps.get("baseline", {}).get("lib.py", [])}
    final = {tuple(x) for x in replay.get("final", {}).get("lib.py", [])}
    reasons = []
    if base != final:
        reasons.append(f"lib.py diagnostics changed on didClose of app.py: lost={sorted(base-final)[:2]} gained={sorted(final-base)[:2]}")
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        reasons.append(f"replay!=fresh: {list(diff.get('files', {}))}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    return False, f"lib.py stable across the close ({len(base)} diagnostics), replay==fresh"
