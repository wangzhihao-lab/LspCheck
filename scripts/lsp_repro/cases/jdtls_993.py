"""Eclipse JDT LS #993 -- "Error on document close, after renaming a file".

Reported sequence (from the issue, reporter @fbricon, 2019-04-15):
  1. invoke `textDocument/rename` on a Java class ("Bar" -> "Fooo");
  2. the server returns documentChanges with text edits *and* a file rename;
  3. the client sends `textDocument/didChange` with the new class name;
  4. the client sends `textDocument/didClose` using the **old** URI (Bar.java);
  5. the server throws: "File not found: .../Bar.java", from
     `DocumentLifeCycleHandler.handleClosed` -> `becomeWorkingCopy()` ->
     `Util.getResourceContentsAsCharArray()`.

Ground-truth fix: commit b75859a4 "Error on document close, after renaming a
file", 2019-05-13 (PR #1033). It guards `hasUnsavedChanges` with
`refreshLocal(DEPTH_ZERO)` + `exists()` so a vanished resource is not turned
back into a working copy. The issue's milestone was "Mid May 2019", which is
release 0.39.0 (2019-05-14); 0.38.0 (2019-05-02) is the last release before it.
`git tag --contains b75859a4` reports v1.0.0 as the first containing tag, which
disagrees with the milestone -- JDT LS cuts release branches, so the master
commit is not an ancestor of the 0.x tags. Both readings are recorded here and
the run decides.

2019-era builds are Eclipse 4.11 and are not expected to start on Java 24; the
runner falls back to the bundled JDK 17, and if that also fails the case is
reported as "server could not be started" rather than as a negative result.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from javaproj import with_sources  # noqa: E402
from scenario import (  # noqa: E402
    Scenario,
    Step,
    close_doc,
    edit,
    fs_rename,
    open_doc,
    quiesce,
    request,
    save,
    snapshot,
    wait,
)
from snapshots import norm_raw  # noqa: E402
from textdoc import find_range  # noqa: E402

SERVER = "jdtls"
ISSUE = "eclipse-jdtls/eclipse.jdt.ls#993"
TITLE = "Error on document close, after renaming a file"
PRE = "0.38.0"
POST = "0.39.0"
SYMPTOM = "didClose on the pre-rename URI throws and leaves diagnostics state wrong"
FIX_COMMIT = "b75859a4 (PR #1033), 2019-05-13, milestone 'Mid May 2019' = 0.39.0"

OLD = "src/app/Bar.java"
NEW = "src/app/Fooo.java"
# The fix guards `hasUnsavedChanges`, so the faithful variants keep the buffer
# dirty; the "save" variant is the control that should never trigger it.
VARIANTS = ["rename_close_settled", "rename_close_race", "rename_save_close_settled"]

SRC = """package app;

public class Bar {
    public boolean foo() {
        return x;
    }
}
"""

RENAMED = SRC.replace("class Bar", "class Fooo")


def _class_name(text: str) -> Dict[str, Dict[str, int]]:
    return find_range(text, "Bar")  # the class name (only occurrence)


def _rename_params(sess) -> Dict[str, Any]:
    d = sess.doc(OLD)
    r = find_range(d.text, "class Bar")
    return {
        "textDocument": {"uri": d.uri},
        "position": {"line": r["start"]["line"], "character": r["start"]["character"] + len("class ")},
        "newName": "Fooo",
    }


def build(variant: str = "rename_close_settled") -> Scenario:
    settle = variant.endswith("settled")
    steps: List[Step] = [
        open_doc(OLD),
        quiesce(OLD),
        snapshot("baseline"),
        # Ask the server for the rename edit, exactly as an editor would.
        request("textDocument/rename", _rename_params, label="rename", normalize=norm_raw),
        # The client applies the text edit to the still-open old document ...
        edit(OLD, _class_name, "Fooo", label="didChange with the new class name"),
    ]
    if "save" in variant:
        steps.append(save(OLD, label="save the edited text (control)"))
    steps.append(quiesce(OLD) if settle else wait(0.05))
    # ... performs the file rename on disk ...
    steps.append(fs_rename(OLD, NEW, label="rename Bar.java -> Fooo.java"))
    if not settle:
        steps.append(wait(0.05))
    # ... and then closes the OLD uri, which is the reported trigger.
    steps += [
        close_doc(OLD, label="didClose on the pre-rename uri"),
        quiesce(),
        open_doc(NEW, label="open the renamed file"),
        quiesce(NEW),
        snapshot("after_rename_close"),
    ]
    return Scenario(
        name=f"jdtls_993[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files=with_sources({OLD: SRC}),
        watch=[OLD, NEW],
        steps=steps,
        quiet_seconds=5.0,
        quiesce_timeout=400.0,
    )


_ERROR_MARKS = ("File not found", "JavaModelException", "does not exist", "ResourceException")


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    reasons = []
    errs = [t for t in replay.get("timeline_errors", [])]
    if errs:
        reasons.append(f"step failures: {[e.get('error', '')[:70] for e in errs][:2]}")
    # The reported symptom is a server-side exception on didClose.
    logged = [m for m in replay.get("server_errors", []) if any(k in m for k in _ERROR_MARKS)]
    fresh_logged = [
        m for m in ((full.get("fresh") or {}).get("server_errors") or []) if any(k in m for k in _ERROR_MARKS)
    ]
    if logged and not fresh_logged:
        reasons.append(f"server logged an error on didClose of the old uri: {logged[0][:160]}")
    fresh = (full.get("fresh") or {}).get("final", {}) or {}
    replay_final = replay.get("final", {}) or {}
    if fresh and replay_final != fresh:
        reasons.append(f"renamed file's diagnostics differ from a fresh server: replay={replay_final} fresh={fresh}")
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        reasons.append(f"replay!=fresh: files={list(diff.get('files', {}))}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    return False, "rename + didClose on the old uri left the state equal to a fresh server"
