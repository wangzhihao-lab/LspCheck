"""Eclipse JDT LS #1771 -- "java.project.sourcePaths doesn't refresh diagnostics".

For a folder opened without .project/.classpath, JDT LS builds an "invisible
project" whose source roots come from the `java.project.sourcePaths` setting.
Changing that setting recomputed the classpath but did not re-publish
diagnostics for the documents already open, so wrong-package errors stayed on
screen after the setting that fixed them had been applied.

Ground-truth fix: commit 3b0045a1 "java.project.sourcePaths doesn't refresh
diagnostics (#1771)", 2021-05-26, first in tag v1.2.0. It walks
`JavaCore.getWorkingCopies(null)` in `InvisibleProjectPreferenceChangeListener`
and re-publishes diagnostics. Its own test fixture is `wrong-packagename/
src/mypackage/{Foo,Bar}.java`, which is the shape used below.

Pre-fix 1.1.0 (2021-04-29), post-fix 1.2.0 (2021-06-30).

Scenario: with the workspace root as the only source root, `src/mypackage/
Foo.java` declaring `package mypackage;` is in the wrong package. Setting
`java.project.sourcePaths = ["src"]` makes it correct, so the error must
disappear -- and a fresh server started on the same files with the same setting
reports no error, which is what the oracle compares against.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scenario import Scenario, Step, change_settings, open_doc, quiesce, snapshot, wait  # noqa: E402

SERVER = "jdtls"
ISSUE = "eclipse-jdtls/eclipse.jdt.ls#1771"
TITLE = "java.project.sourcePaths doesn't refresh diagnostics"
PRE = "1.1.0"
POST = "1.2.0"
SYMPTOM = "wrong-package diagnostics survive the sourcePaths setting that fixes them"
FIX_COMMIT = "3b0045a1 (#1771), 2021-05-26, released in v1.2.0"

REL = "src/mypackage/Foo.java"
OTHER = "src/mypackage/Bar.java"
VARIANTS = ["sourcepaths_settled", "sourcepaths_race"]

FOO = """package mypackage;

public class Foo {
    public static void main(String[] args) {
        System.out.println(new Bar().name());
    }
}
"""

BAR = """package mypackage;

public class Bar {
    public String name() { return "bar"; }
}
"""

# No .project/.classpath: JDT LS must build an invisible project.
FILES = {REL: FOO, OTHER: BAR}

SRC_PATHS = {"java": {"project": {"sourcePaths": ["src"]}}}


def _set_source_paths(sess) -> Dict[str, Any]:
    return SRC_PATHS


def build(variant: str = "sourcepaths_settled") -> Scenario:
    settle = variant.endswith("settled")
    steps: List[Step] = [
        open_doc(REL),
        quiesce(REL),
        open_doc(OTHER),
        quiesce(OTHER),
        snapshot("baseline"),
        change_settings(_set_source_paths, label="java.project.sourcePaths = [src]"),
    ]
    steps.append(quiesce(REL) if settle else wait(0.2))
    steps += [quiesce(REL), snapshot("after_setting")]
    return Scenario(
        name=f"jdtls_1771[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files=FILES,
        watch=[REL, OTHER],
        steps=steps,
        quiet_seconds=5.0,
        quiesce_timeout=400.0,
    )


_PKG_MARKS = ("declared package", "does not match the expected package", "must be defined in its own file")


def _pkg_errors(raw: Dict[str, Any]) -> List[str]:
    out = []
    for rel, diags in (raw or {}).items():
        if diags == "absent":
            continue
        for d in diags:
            msg = d.get("message", "")
            if any(k in msg for k in _PKG_MARKS):
                out.append(f"{rel}: {msg[:80]}")
    return out


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    replay_errs = _pkg_errors(replay.get("final_raw", {}))
    fresh_errs = _pkg_errors(((full.get("fresh") or {}).get("final_raw") or {}))
    reasons = []
    if replay_errs and not fresh_errs:
        reasons.append(f"wrong-package diagnostics survived the setting change: {replay_errs[:2]}")
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        reasons.append(f"replay!=fresh: {list(diff.get('files', {}))}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    if not replay_errs and not fresh_errs:
        return False, "setting change refreshed diagnostics (no wrong-package errors) and replay==fresh"
    return False, f"replay and fresh agree (both have package errors={bool(replay_errs)})"
