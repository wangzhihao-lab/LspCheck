"""Oracle registry (plan/tool_design_v1.md section 5). `load_all()` imports every oracle
module present so that each registers itself in ORACLES; `get(name)` returns one.

Modules: r0_crash (internal errors / hangs on fresh sessions), r1_history (history independence), r2_handles (handle validity), r3_routes
(route equivalence), r4_edits (non-refactoring edit validity; syntax.py classifies
syntax errors), r5_transforms (semantics-preserving transformations), r6_crossimpl
(TypeScript 6 vs 7).

Run line: imported by campaign.py, flake.py and reduce.py; not run directly.
"""

from __future__ import annotations

import importlib
import os

from .base import ORACLES, Oracle

ORACLE_MODULES = ("r0_crash", "r1_history", "r2_handles", "r3_routes", "r4_edits", "r5_transforms", "r6_crossimpl")


def load_all() -> dict:
    """Import every oracle module that exists; returns the registry."""
    here = os.path.dirname(os.path.abspath(__file__))
    for mod in ORACLE_MODULES:
        if os.path.exists(os.path.join(here, f"{mod}.py")):
            importlib.import_module(f"{__name__}.{mod}")
    return ORACLES


def get(name: str) -> Oracle:
    load_all()
    if name not in ORACLES:
        raise KeyError(f"unknown oracle {name!r}; registered: {sorted(ORACLES)}")
    return ORACLES[name]


__all__ = ["ORACLES", "ORACLE_MODULES", "get", "load_all"]
