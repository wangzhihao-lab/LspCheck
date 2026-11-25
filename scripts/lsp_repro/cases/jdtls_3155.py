"""Eclipse JDT LS #3155 -- "Doesn't revalidate project files after classpath
changes if autobuild is off".

With `java.autobuild.enabled = false`, JDT LS did not re-validate already-open
files when the project classpath changed, so the diagnostics kept reflecting the
old classpath until something else forced a rebuild.

Ground-truth fix: commit bb26c98d "Revalidate open files in project when
classpath updates.", 2024-05-16, first in tag v1.37.0. (The neighbouring commit
f20d928a "Respect the autobuild setting on initialization. (#3177)" is in the
same release.) Pre-fix 1.36.0 (2024-05-28), post-fix 1.37.0 (2024-06-25).

Scenario: a project whose source references a second source folder that is not
yet on the classpath, so the reference is unresolved. Then add that folder to
.classpath on disk and notify the server through didChangeWatchedFiles. With
autobuild off, the pre-fix server should keep reporting the stale "cannot be
resolved" diagnostics, while a fresh server on the final contents resolves them.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from javaproj import CLASSPATH_XML, PREFS, PROJECT_XML  # noqa: E402
from scenario import Scenario, Step, fs_write, open_doc, quiesce, snapshot, wait  # noqa: E402

SERVER = "jdtls"
ISSUE = "eclipse-jdtls/eclipse.jdt.ls#3155"
TITLE = "Doesn't revalidate project files after classpath changes if autobuild is off"
PRE = "1.36.0"
POST = "1.37.0"
SYMPTOM = "diagnostics keep reflecting the old classpath after .classpath changes"
FIX_COMMIT = "bb26c98d, 2024-05-16, released in v1.37.0"

REL = "src/app/Main.java"
VARIANTS = ["classpath_add_settled", "classpath_add_race"]

CLASSPATH_TWO_SRC = """<?xml version="1.0" encoding="UTF-8"?>
<classpath>
  <classpathentry kind="src" path="src"/>
  <classpathentry kind="src" path="extra"/>
  <classpathentry kind="con" path="org.eclipse.jdt.launching.JRE_CONTAINER"/>
  <classpathentry kind="output" path="bin"/>
</classpath>
"""

MAIN = """package app;

import extra.Support;

public class Main {
    public static void main(String[] args) {
        System.out.println(Support.name());
    }
}
"""

SUPPORT = """package extra;

public class Support {
    public static String name() { return "support"; }
}
"""

FILES = {
    ".project": PROJECT_XML.format(name="repro"),
    ".classpath": CLASSPATH_XML,  # `extra` is NOT a source folder yet
    ".settings/org.eclipse.jdt.core.prefs": PREFS,
    REL: MAIN,
    "extra/extra/Support.java": SUPPORT,
}

# Autobuild off is the precondition named in the issue title.
SETTINGS_AUTOBUILD_OFF = {"java": {"autobuild": {"enabled": False}}}


def build(variant: str = "classpath_add_settled") -> Scenario:
    settle = variant.endswith("settled")
    steps: List[Step] = [
        open_doc(REL),
        quiesce(REL),
        snapshot("baseline"),
        # Rewrite .classpath on disk so that `extra` becomes a source folder,
        # then tell the server through didChangeWatchedFiles -- that is how a
        # build-file change reaches the server from a real editor.
        fs_write(".classpath", CLASSPATH_TWO_SRC, label="add extra/ as a source folder"),
    ]
    steps.append(quiesce(REL) if settle else wait(0.1))
    steps += [quiesce(REL), snapshot("after_classpath_change")]
    return Scenario(
        name=f"jdtls_3155[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files=FILES,
        watch=[REL],
        steps=steps,
        quiet_seconds=5.0,
        quiesce_timeout=400.0,
        settings_override=SETTINGS_AUTOBUILD_OFF,
    )


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    raw = replay.get("final_raw", {}).get(REL, [])
    unresolved = [d.get("message", "") for d in raw if "cannot be resolved" in d.get("message", "")]
    fresh_raw = ((full.get("fresh") or {}).get("final_raw") or {}).get(REL, [])
    fresh_unresolved = [d.get("message", "") for d in fresh_raw if "cannot be resolved" in d.get("message", "")]
    reasons = []
    if unresolved and not fresh_unresolved:
        reasons.append(f"stale unresolved-reference diagnostics survive the classpath change: {unresolved[:2]}")
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        reasons.append(f"replay!=fresh: {list(diff.get('files', {}))}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    if not unresolved and not fresh_unresolved:
        return False, "classpath change took effect (no unresolved references) and replay==fresh"
    return False, f"replay and fresh agree (both unresolved={bool(unresolved)}) -- scenario did not separate them"
