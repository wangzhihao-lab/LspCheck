"""Replays of the TypeScript 6 history bugs with the wrapper options its maintainer suggested (upstream replies).

The typescript-language-server maintainer answered the two reports (typescript-language-server
#1135 and #1136) with a setting each:
- C1 (#1135): the default mode leaves file watching to tsserver and ignores
  workspace/didChangeWatchedFiles; with `tsserver.useClientFileWatcher: true` and a client that
  supports dynamic registration and relative patterns for didChangeWatchedFiles, the wrapper forwards
  the client's file events and the answers should be right after the same steps;
- C2 (#1136): the server initializes asynchronously by default; `tsserver.useSyntaxServer: "never"`
  might avoid the early partial answers.
This script replays the groups with those settings through the frozen replay path
(replay_common.replay_variant): C1 as a rename outside the editor (file-system events only, as
c1_rename_edits.py --mode external), for the groups that reproduced that way, and C2 as recorded.
The ts6 launch spec is wrapped in-process to add the option (and, for C1, `relativePatternSupport`
in the client capabilities); nothing in the frozen tree changes.

Writes data/lsptest/runs/main_v1/evidence/ts_wrapper_options.{json,log}.

Run line: python3 scripts/paper/evidence/ts_wrapper_options.py [--case c1|c2|both] [--replays 3]
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import logging
import os
import sys
from typing import Any, Callable, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c1_rename_edits import ExternalRenameApplier  # noqa: E402
from replay_common import EVIDENCE, groups_of, replay_variant  # noqa: E402

import servers  # noqa: E402  (frozen tool, read-only)
import servers_extra  # noqa: E402,F401  (registers ts6 before it is wrapped)

logger = logging.getLogger("ts_wrapper_options")
# the C1 groups that reproduced 3 of 3 as a rename outside the editor (c1_rename_external.json)
C1_EXTERNAL = ("4f92e2", "fa501c", "898f29", "d24ca6", "591c42", "d686b3", "7bd793")


def wrap_ts6(tsserver_extra: Dict[str, Any], relative_patterns: bool) -> Callable[[], None]:
    """Replace the ts6 spec factory by one that adds `tsserver_extra` to the init options; returns an undo."""
    original = servers.SERVER_FACTORY["ts6"]

    def patched(version: str) -> Any:
        spec = original(version)
        init = copy.deepcopy(spec.init_options)
        init.setdefault("tsserver", {}).update(tsserver_extra)
        caps = copy.deepcopy(spec.capabilities) if spec.capabilities else None
        if relative_patterns and caps is not None:
            caps.setdefault("workspace", {}).setdefault("didChangeWatchedFiles", {}).update(
                {"dynamicRegistration": True, "relativePatternSupport": True})
        return dataclasses.replace(spec, init_options=init, capabilities=caps)

    servers.SERVER_FACTORY["ts6"] = patched

    def undo() -> None:
        servers.SERVER_FACTORY["ts6"] = original
    return undo


def run_case(case: str, replays: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if case == "c1":
        undo = wrap_ts6({"useClientFileWatcher": True}, relative_patterns=True)
        try:
            for gid in groups_of(["C1"]):
                if gid[-6:] in C1_EXTERNAL:
                    row = replay_variant(gid, "cw", replays=replays, applier=ExternalRenameApplier)
                    row.update({"case": "c1", "setting": "tsserver.useClientFileWatcher=true, relativePatternSupport"})
                    rows.append(row)
                    logger.info("%s: %s (%s/%s)", gid, row["verdict"], row["reproduced"], row["replays"])
        finally:
            undo()
    else:
        undo = wrap_ts6({"useSyntaxServer": "never"}, relative_patterns=False)
        try:
            for gid in groups_of(["C2"]):
                row = replay_variant(gid, "ss", replays=replays)
                row.update({"case": "c2", "setting": "tsserver.useSyntaxServer=never"})
                rows.append(row)
                logger.info("%s: %s (%s/%s)", gid, row["verdict"], row["reproduced"], row["replays"])
        finally:
            undo()
    return rows


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", choices=("c1", "c2", "both"), default="both")
    ap.add_argument("--replays", type=int, default=3)
    args = ap.parse_args()
    rows = []
    for case in (("c1", "c2") if args.case == "both" else (args.case,)):
        rows += run_case(case, args.replays)
    with open(os.path.join(EVIDENCE, "ts_wrapper_options.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows}, f, ensure_ascii=False, indent=1)
    lines = [f"{r['case']} {r['gid']} [{r['setting']}]: {r['verdict']} ({r['reproduced']}/{r['replays']}) {r['error']}" for r in rows]
    with open(os.path.join(EVIDENCE, "ts_wrapper_options.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.info("\n%s", "\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
