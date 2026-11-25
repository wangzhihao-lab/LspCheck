"""pyright #4994 -- "pyright-lsp may enter a strange state reporting library not
found when there are sub-project inside a folder".

Reported repro (verbatim): project tree with a root `example.py`,
`pyproject.toml`, and `projects/{example.py,requirements.txt,sac/{__init__.py,
datasets.py}}`; then "1. enable pyright in nvim / 2. `nvim projects/example.py
example.py` / 3. switch to next buffer / 4. switch back / 5. perform a format
operation using isort inside vim / 6. pyright-lsp will enter a strange state
reporting `os` not found." The reporter adds: "step 5 is needed to trigger
`textDocument/didChange`" and "If I delete `projects/requirements.txt`, then
this bug is not reproducible."

Ground-truth fix: commit 06fc24c9a, 2023-04-27, first in tag 1.1.306: "Added a
map of open documents to the languageServerBase class. It is responsible for
applying any delta changes and updating the contents for each of the workspaces
associated with that file. ... It also eliminates a correctness issue that can
occur if new workspaces are added after files are open."

That mechanism is about *several workspaces holding the same open file*, so the
scenario announces two workspace folders (root and root/projects) and edits a
file that both of them can claim.

Pre-fix 1.1.305 (2023-04-26), post-fix 1.1.306 (2023-05-03).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scenario import (  # noqa: E402
    Scenario,
    Step,
    add_folder,
    edit,
    open_doc,
    quiesce,
    request,
    snapshot,
    wait,
)
from snapshots import norm_hover  # noqa: E402
from textdoc import find_range, rng  # noqa: E402

SERVER = "pyright"
ISSUE = "microsoft/pyright#4994"
TITLE = "pyright-lsp may enter a strange state reporting library not found with sub-projects"
PRE = "1.1.305"
POST = "1.1.306"
SYMPTOM = "spurious reportMissingImports/reportMissingModuleSource after a didChange with two workspaces"
FIX_COMMIT = "06fc24c9a, 2023-04-27, first in tag 1.1.306"

VARIANTS = [
    "two_folders_settled",
    "two_folders_race",
    "one_folder_settled",
    "late_folder_settled",
    "late_folder_race",
]

ROOT_EXAMPLE = '''import os
import sys

from projects.sac.datasets import Dataset


def main() -> None:
    print(os.sep, sys.platform, Dataset)
'''

SUB_EXAMPLE = '''import os
import sys

from sac.datasets import Dataset


def run() -> None:
    print(os.getcwd(), sys.argv, Dataset)
'''

# isort reorders the import block; that is the didChange the reporter needed.
SUB_EXAMPLE_SORTED = '''import os
import sys
from sac.datasets import Dataset


def run() -> None:
    print(os.getcwd(), sys.argv, Dataset)
'''

FILES = {
    "pyproject.toml": "[tool.pyright]\ninclude = [\".\"]\n",
    "example.py": ROOT_EXAMPLE,
    "projects/requirements.txt": "numpy\n",
    "projects/example.py": SUB_EXAMPLE,
    "projects/sac/__init__.py": "",
    "projects/sac/datasets.py": "class Dataset:\n    pass\n",
}


def _import_block(text: str) -> Dict[str, Dict[str, int]]:
    """The whole leading import block of projects/example.py."""
    end = text.index("\n\n\ndef ")
    return rng(0, 0, text[:end].count("\n") + 1, 0)


def _os_pos(sess) -> Dict[str, Any]:
    d = sess.doc("projects/example.py")
    r = find_range(d.text, "os.getcwd")
    return {"textDocument": {"uri": d.uri}, "position": r["start"]}


def build(variant: str = "two_folders_settled") -> Scenario:
    settle = variant.endswith("settled")
    steps: List[Step] = [
        open_doc("projects/example.py"),
        quiesce("projects/example.py"),
        open_doc("example.py"),
        quiesce("example.py"),
        snapshot("baseline"),
    ]
    if variant.startswith("late_folder"):
        # "a correctness issue that can occur if new workspaces are added after
        # files are open" -- announce the sub-folder only now.
        steps += [add_folder("projects", label="add projects/ as a workspace"), quiesce()]
    steps += [
        # "switch buffers" has no protocol footprint, so the isort-style
        # didChange on the already-open sub-project file is the real trigger.
        edit(
            "projects/example.py",
            _import_block,
            SUB_EXAMPLE_SORTED[: SUB_EXAMPLE_SORTED.index("\n\n\ndef ") + 1],
            label="isort the import block",
        ),
    ]
    steps.append(quiesce("projects/example.py") if settle else wait(0.05))
    steps += [quiesce("projects/example.py"), snapshot("after_didchange")]
    folders = [] if variant.startswith(("one_folder", "late_folder")) else ["projects"]
    return Scenario(
        name=f"pyright_4994[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files=FILES,
        watch=["projects/example.py", "example.py"],
        extra_folders=folders,
        steps=steps,
        probes=[request("textDocument/hover", _os_pos, label="hover_os", normalize=norm_hover)],
    )


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    raw = replay.get("final_raw", {})
    missing = []
    for rel, diags in raw.items():
        for d in diags:
            code = str(d.get("code") or "")
            msg = d.get("message", "")
            if "MissingImport" in code or "MissingModuleSource" in code or "could not be resolved" in msg:
                missing.append(f"{rel}: {msg[:70]}")
    reasons = []
    if missing:
        reasons.append(f"spurious unresolved imports: {missing[:3]}")
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        reasons.append(f"replay!=fresh: {list(diff.get('files', {}))} probes={list((diff.get('probes') or {}))}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    return False, "no unresolved-import diagnostics and replay==fresh"
