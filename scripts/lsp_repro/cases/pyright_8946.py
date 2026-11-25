"""pyright #8946 -- "Type error after undo".

Reported repro (verbatim from the issue): open the file, remove the line
`from multiprocessing import Pool` (errors appear), then undo the delete -- the
errors do not go away ("Pool is not a recognized type, etc...").

Reported on pyright 1.1.379 (issue opened and closed 2024-09-10).
Ground-truth fix: commit edaeab2bc "Mutate sourceFile imports list whenever it
changes (#8986)", 2024-09-13, first contained in tag 1.1.381. Mechanism, from the
commit message: when the new import list was a subset of the old one,
`_updateSourceFileImports` skipped `sourceFileInfo.mutate()`, so restoring the
import never re-registered the importing buffer in the stub's `importedBy` list;
the stub was then garbage-collected as "not needed" and its symbols stopped
resolving.

What that means for a headless client: the observable symptom is not
necessarily an *extra* diagnostic. Once `Pool` resolves to Unknown, pyright
*suppresses* the diagnostics that depend on it -- so the file ends up with
FEWER diagnostics than the identical text had at the start. The predicate below
therefore uses the metamorphic relation "a self-inverse edit sequence must leave
the diagnostic set unchanged", plus hover/definition probes on the restored
symbol.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scenario import Scenario, Step, edit, open_doc, quiesce, request, snapshot, undo, wait  # noqa: E402
from snapshots import norm_hover, norm_locations  # noqa: E402
from textdoc import find_range, line_range  # noqa: E402

SERVER = "pyright"
ISSUE = "microsoft/pyright#8946"
TITLE = "Type error after undo"
PRE = "1.1.380"
POST = "1.1.381"
SYMPTOM = "after delete+undo of an import line the diagnostic set for identical text changes"
FIX_COMMIT = "edaeab2bc (#8986), 2024-09-13, first in tag 1.1.381"

VARIANTS = [
    "sentinel_settled",
    "sentinel_race0",
    "sentinel_race200",
    "sentinel_race500",
    "plain_settled",
    "plain_race200",
]

# Verbatim from the issue body.
SRC = '''from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime

import os
from multiprocessing import Pool
from typing import Callable


def execute_shell_commands(
    dates: list[datetime.date],
    cmd: Callable[[datetime.date], str],
    workers: int = 1,
) -> list[tuple[int, datetime.date]]:
    with Pool(workers) as po:
        exit_codes = po.map(os.system, [cmd(d) for d in dates])
        return [ret for ret in zip(exit_codes, dates) if ret[0] != 0]
'''

# Sentinel: an error that exists only while `Pool` resolves to a real symbol.
# If the import breaks, `Pool` becomes Unknown and pyright stops reporting it,
# which makes the loss of server state directly observable in the diagnostics.
SENTINEL = '\n\n_check: int = Pool\n'


def _import_line(text: str) -> Dict[str, Dict[str, int]]:
    for i, row in enumerate(text.splitlines()):
        if row.strip() == "from multiprocessing import Pool":
            return line_range(text, i, whole_line=True)
    raise ValueError("import line not found")


def _pool_use_pos(sess) -> Dict[str, Any]:
    d = sess.doc("repro.py")
    r = find_range(d.text, "Pool(workers)")
    return {"textDocument": {"uri": d.uri}, "position": r["start"]}


def _delay_for(variant: str) -> float:
    for token, secs in (("race0", 0.0), ("race200", 0.2), ("race500", 0.5)):
        if variant.endswith(token):
            return secs
    return -1.0


def build(variant: str = "sentinel_settled") -> Scenario:
    src = SRC + SENTINEL if variant.startswith("sentinel") else SRC
    delay = _delay_for(variant)
    steps: List[Step] = [
        open_doc("repro.py"),
        quiesce("repro.py"),
        snapshot("baseline"),
        edit("repro.py", _import_line, "", label="delete import line"),
    ]
    if delay < 0:
        steps += [quiesce("repro.py"), snapshot("after_delete")]
    else:
        if delay > 0:
            steps.append(wait(delay, label=f"race delay {int(delay * 1000)}ms"))
        steps.append(snapshot("after_delete"))
    steps += [undo("repro.py", label="undo delete"), quiesce("repro.py"), snapshot("after_undo")]
    return Scenario(
        name=f"pyright_8946[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files={"repro.py": src},
        watch=["repro.py"],
        steps=steps,
        probes=[
            request("textDocument/hover", _pool_use_pos, label="hover_Pool", normalize=norm_hover),
            request("textDocument/definition", _pool_use_pos, label="def_Pool", normalize=norm_locations),
        ],
    )


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    snaps = {s["label"]: s["diagnostics"] for s in replay.get("snapshots", [])}
    base = {tuple(x) for x in snaps.get("baseline", {}).get("repro.py", [])}
    final = {tuple(x) for x in replay.get("final", {}).get("repro.py", [])}
    reasons = []
    if base != final:
        lost = sorted(t[4] for t in base - final)
        gained = sorted(t[4] for t in final - base)
        reasons.append(f"diagnostics changed for identical text (lost={lost[:3]} gained={gained[:3]})")
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        probes = list((diff.get("probes") or {}).keys())
        reasons.append(f"replay!=fresh (files={list(diff.get('files', {}))}, probes={probes})")
    if reasons:
        return True, "; ".join(reasons)
    return False, f"stable: {len(base)} diagnostics before and after, replay==fresh"
