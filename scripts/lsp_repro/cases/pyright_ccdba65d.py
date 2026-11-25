"""pyright, commit cdba65d4c -- "Fixed a bug that caused incorrect type evaluation
because of stale module paths that are cached for specific source files. Module
paths are dependent on the list of configured import resolution paths, so when
the import resolution paths change, we may need to recompute the module path for
a source file."

No issue number; the commit message is the ground truth. Kept in the set because
it is a deterministic (non-racy) state-update omission triggered by a
configuration change while documents are open -- the same shape as the two JDT LS
classpath/sourcePath cases.

Commit cdba65d4c, 2022-08-03, first in tag 1.1.266.
Pre-fix 1.1.265 (2022-08-03), post-fix 1.1.266 (2022-08-08).

Scenario: a package under `libs/` that is only importable once `libs` is on the
import path. Open a file that imports it (error), then set
`python.analysis.extraPaths = ["libs"]` through didChangeConfiguration. The
import must resolve afterwards, and must agree with a fresh server that started
with that setting already in place.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scenario import (  # noqa: E402
    Scenario,
    Step,
    change_settings,
    open_doc,
    quiesce,
    request,
    snapshot,
    wait,
)
from snapshots import norm_hover, norm_locations  # noqa: E402
from textdoc import find_range  # noqa: E402

SERVER = "pyright"
ISSUE = "microsoft/pyright@cdba65d4c (no issue filed)"
TITLE = "Stale cached module paths when import resolution paths change"
PRE = "1.1.265"
POST = "1.1.266"
SYMPTOM = "an import stays unresolved after extraPaths is changed to make it resolvable"
FIX_COMMIT = "cdba65d4c, 2022-08-03, first in tag 1.1.266"

VARIANTS = ["extrapaths_settled", "extrapaths_race", "extrapaths_twice"]

APP = '''from mylib.core import Widget


def use() -> None:
    w = Widget()
    print(w.label())
'''

FILES = {
    "app.py": APP,
    "libs/mylib/__init__.py": "",
    "libs/mylib/core.py": 'class Widget:\n    def label(self) -> str:\n        return "w"\n',
}

WITH_PATHS = {"python": {"analysis": {"extraPaths": ["libs"]}}}
WITHOUT_PATHS = {"python": {"analysis": {"extraPaths": []}}}


def _with(sess) -> Dict[str, Any]:
    return WITH_PATHS


def _without(sess) -> Dict[str, Any]:
    return WITHOUT_PATHS


def _widget_pos(sess) -> Dict[str, Any]:
    d = sess.doc("app.py")
    r = find_range(d.text, "Widget()")
    return {"textDocument": {"uri": d.uri}, "position": r["start"]}


def build(variant: str = "extrapaths_settled") -> Scenario:
    settle = variant.endswith("settled")
    steps: List[Step] = [
        open_doc("app.py"),
        quiesce("app.py"),
        snapshot("baseline"),
        change_settings(_with, label="extraPaths = [libs]"),
    ]
    steps.append(quiesce("app.py") if settle else wait(0.1))
    if variant == "extrapaths_twice":
        # Toggle back and forth: the cached module path has to be recomputed
        # each time, not just on the first change.
        steps += [
            snapshot("after_add"),
            change_settings(_without, label="extraPaths = []"),
            quiesce("app.py"),
            change_settings(_with, label="extraPaths = [libs] again"),
            quiesce("app.py"),
        ]
    steps += [quiesce("app.py"), snapshot("after_config")]
    return Scenario(
        name=f"pyright_ccdba65d[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files=FILES,
        watch=["app.py"],
        steps=steps,
        # The fresh run must start with the final setting, otherwise the two
        # sides are not comparable.
        settings_override=WITH_PATHS,
        probes=[
            request("textDocument/hover", _widget_pos, label="hover_Widget", normalize=norm_hover),
            request("textDocument/definition", _widget_pos, label="def_Widget", normalize=norm_locations),
        ],
    )


def _unresolved(raw: Dict[str, Any]) -> List[str]:
    out = []
    for rel, diags in (raw or {}).items():
        if diags == "absent":
            continue
        for d in diags:
            code = str(d.get("code") or "")
            msg = d.get("message", "")
            if "MissingImport" in code or "could not be resolved" in msg:
                out.append(f"{rel}: {msg[:80]}")
    return out


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    replay_errs = _unresolved(replay.get("final_raw", {}))
    fresh_errs = _unresolved(((full.get("fresh") or {}).get("final_raw") or {}))
    reasons = []
    if replay_errs and not fresh_errs:
        reasons.append(f"import still unresolved after the config change: {replay_errs[:2]}")
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        probes = list((diff.get("probes") or {}).keys())
        reasons.append(f"replay!=fresh: files={list(diff.get('files', {}))} probes={probes}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    if not replay_errs and not fresh_errs:
        return False, "config change took effect (import resolves) and replay==fresh"
    return False, f"replay and fresh agree (both unresolved={bool(replay_errs)})"
