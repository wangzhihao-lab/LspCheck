"""Manual corrections found while checking individual candidates.

FIX_OVERRIDES replaces the fix commit chosen automatically when the linked
commit is demonstrably not the fix. NO_RELEASED_BUG lists regressions whose
introducing change and fix both landed between two consecutive releases, so no
released pre-fix build carries the bug (a build of the fix's parent commit
would); such candidates keep their mapping but are excluded from the top 80.

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

from typing import Dict, Tuple

FIX_OVERRIDES: Dict[Tuple[str, int], Tuple[str, str]] = {
    ("gopls", 54147): (
        "a2a24778ba9562d210892fad5bf136c0bdbd233c",
        "closing commit 310ea71b7 only adds a test; the fix is CL 417576 (a2a24778b)",
    ),
}

NO_RELEASED_BUG: Dict[Tuple[str, int], str] = {
    ("gopls", 39147): "confirmed: introducing CL 233117 (8979540587) first ships in v0.4.2, the same release as the fix",
    ("gopls", 59587): "confirmed: introducing CL 477979 (d52bc56893) first ships in v0.12.0, the same release as the fix",
    ("gopls", 59851): "likely: the report describes a regression on tip after the #58506 fix, before any release",
    ("gopls", 61512): "likely: the report describes a crash on tools tip from the last few days",
    ("gopls", 36224): "likely: screening notes describe a short-lived regression fixed within a day",
    ("pyright", 9015): "likely: the report places the bug on main after 1.1.380 and the fix before 1.1.381",
}
