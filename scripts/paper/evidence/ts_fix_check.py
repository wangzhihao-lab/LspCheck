"""Check of the TypeScript finding C11 with the TypeScript compiler (post-freeze evidence, review round 2).

Group ts6-r4-diagnostics-extra-2322-mutation-m3-1879f3 (pmndrs/zustand, src/middleware/devtools.ts):
the seeded mutation deletes the member `stores` of an object literal; the quick fix 'Add missing
properties' inserts `stores: undefined`. As in gopls_fix_check.py, the file is rebuilt offline from the
reduced ops in three states (base = the file as committed, mutated, fixed) and written into an APFS
clone of the project under temp/evidence_scratch/ (the corpus clone is never written); for each state
`tsc --noEmit -p tsconfig.json` of TypeScript 6.0.3 (the build the campaign used) runs, and its errors
in the target file are kept. The compiler shares its checker with the server, so the check is
independent of the session's state, not of the implementation.

Writes data/lsptest/runs/main_v1/evidence/ts_fix_check.{json,log}.

Run line: python3 scripts/paper/evidence/ts_fix_check.py
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))

from campaign_store import load_repro  # noqa: E402  (frozen tool, read-only)
from driver import clone_tree  # noqa: E402
from oracles.base import final_state  # noqa: E402
from ops import read_text, write_text  # noqa: E402

logger = logging.getLogger("ts_fix_check")
GID = "ts6-r4-diagnostics-extra-2322-mutation-m3-1879f3"
RUN = os.path.join(REPO, "data", "lsptest", "runs", "main_v1")
SCRATCH = os.path.join(REPO, "temp", "evidence_scratch")
TSC = os.path.join(REPO, "temp", "lsp_servers", "ts6-6.0.3", "node_modules", "typescript", "bin", "tsc")
TIMEOUT_S = 900


def tsc_errors(project: str, rel: str) -> Dict[str, Any]:
    """`tsc --noEmit -p tsconfig.json`; the error lines that name the target file."""
    p = subprocess.run(["node", TSC, "--noEmit", "--pretty", "false", "-p", "tsconfig.json"], cwd=project,
                       capture_output=True, text=True, timeout=TIMEOUT_S)
    lines = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.startswith(rel + "(")]
    return {"exit": p.returncode, "errors_in_file": lines,
            "codes": sorted({m.group(1) for ln in lines for m in [re.search(r"error TS(\d+)", ln)] if m})}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    doc, v = load_repro(os.path.join(RUN, "triage", GID, "repro.json"))
    project = os.path.join(REPO, doc["project"]["ref"])
    rel = doc["case"]["path"]
    ops = list(v.ops)
    n_fix = len(doc["case"]["fix_ops"])
    texts = {"base": read_text(os.path.join(project, rel)),
             "mutated": final_state(project, ops[:len(ops) - n_fix]).files.get(rel),
             "fixed": final_state(project, ops).files.get(rel)}
    scratch = os.path.join(SCRATCH, GID)
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(SCRATCH, exist_ok=True)
    clone_tree(project, scratch)
    states: Dict[str, Any] = {}
    try:
        for state, text in texts.items():
            write_text(os.path.join(scratch, rel), text or "")
            states[state] = tsc_errors(scratch, rel)
            logger.info("%s: %s", state, states[state]["codes"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    new_codes = sorted(set(states["fixed"]["codes"]) - set(states["mutated"]["codes"]) - set(states["base"]["codes"]))
    result = {"group": GID, "project": doc["project"]["name"], "path": rel, "fix_title": doc["case"].get("title"),
              "states": states, "codes_added_by_fix": new_codes,
              "tsc": subprocess.run(["node", TSC, "--version"], capture_output=True, text=True).stdout.strip()}
    with open(os.path.join(RUN, "evidence", "ts_fix_check.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    lines = [f"== C11 {GID} ({result['project']}, {rel}); {result['tsc']}"]
    for state in ("base", "mutated", "fixed"):
        lines.append(f"[{state}] tsc exit {states[state]['exit']}; errors in {rel}: {len(states[state]['errors_in_file'])}")
        lines += ["   " + ln for ln in states[state]["errors_in_file"][:12]]
    lines.append(f"error codes added by the fix: {new_codes}")
    with open(os.path.join(RUN, "evidence", "ts_fix_check.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
