"""C1 with the willRenameFiles edits applied (post-freeze evidence, review round 2).

The frozen tool's file rename (ops.OpApplier.op_fs_rename) sends workspace/willRenameFiles but only
records the returned WorkspaceEdit; LSP 3.17 says a client applies that edit before it renames the
files. This script replays the C1 groups with a subclass of the applier that applies the edit first,
as an editor does: edits to open documents go out as didChange, edits to closed files open them
(didOpen) and change them in memory, unsaved, the way Visual Studio Code applies a workspace edit.
The rest of the rename is unchanged (didClose, move on disk, didRenameFiles, didChangeWatchedFiles,
didOpen). Each group is replayed three times through the R1 oracle's own replay().

--mode external replays the same histories as a rename made outside the editor (a terminal `git mv`,
a branch switch): no willRenameFiles and no didRenameFiles, only didClose, the move on disk, the
watched-file events and didOpen of the new path.

Recorded per group: the edits the server returned for each rename (files and edit counts), whether
every edited document ended with the text of the project file (only then does the fresh pair on the
original content remain the right reference), and the reproduction counts.

--campaign main_v2 replays the main_v2 groups that its triage/root_causes.csv assigns to C1 (the recorded
main_v2 results of 2026-11-21 were taken from the draft table, which still listed the inlay-hint group, now C31).

Writes data/lsptest/runs/<campaign>/evidence/c1_rename_<mode>.{json,log} (default campaign main_v1).

Run line: python3 scripts/paper/evidence/c1_rename_edits.py [--mode edit|external] [--only substr] [--replays 3]
          [--campaign main_v1|main_v2]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import CAMPAIGN, REPO, entry, evidence_dir, groups_of, replay_variant  # noqa: E402

from ops import OpApplier, OpOutcome, apply_change, read_text, uri_to_path  # noqa: E402  (frozen tool, read-only)
from campaign_store import load_repro  # noqa: E402
from model import Op  # noqa: E402

logger = logging.getLogger("c1_rename_edits")
SESSIONS: List["EditApplier"] = []  # every applier of the current group, for the checks after a replay


def text_edits(edit: Any) -> Dict[str, List[Dict[str, Any]]]:
    """uri -> TextEdits of a WorkspaceEdit (changes or documentChanges; resource operations ignored)."""
    out: Dict[str, List[Dict[str, Any]]] = {}
    if not isinstance(edit, dict):
        return out
    for uri, edits in (edit.get("changes") or {}).items():
        out.setdefault(uri, []).extend(edits)
    for dc in edit.get("documentChanges") or []:
        if isinstance(dc, dict) and "textDocument" in dc:
            out.setdefault(dc["textDocument"]["uri"], []).extend(dc.get("edits") or [])
    return out


def apply_text_edits(text: str, edits: List[Dict[str, Any]]) -> str:
    """Apply LSP TextEdits (positions in the original text) from the last to the first."""
    def key(e: Dict[str, Any]) -> Any:
        s = e["range"]["start"]
        return (s["line"], s["character"])
    for e in sorted(edits, key=key, reverse=True):
        r = e["range"]
        text, _, _ = apply_change(text, (r["start"]["line"], r["start"]["character"]),
                                  (r["end"]["line"], r["end"]["character"]), e["newText"])
    return text


class EditApplier(OpApplier):
    """OpApplier whose file rename applies the willRenameFiles edit before moving the file."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.renames: List[Dict[str, Any]] = []
        self.edited: Dict[str, str] = {}  # workspace-relative path -> text after the last edit
        self.skip_will_rename = False
        SESSIONS.append(self)

    def _rel(self, uri: str) -> str:
        """Workspace-relative path ('/' separators) of a file URI in this session's workspace."""
        return os.path.relpath(uri_to_path(uri), self.store.root).replace(os.sep, "/")

    def supports_file_op(self, name: str) -> bool:
        if name == "willRename" and self.skip_will_rename:
            return False
        return super().supports_file_op(name)

    def apply_workspace_edit(self, edit: Any, out: OpOutcome) -> Dict[str, int]:
        applied: Dict[str, int] = {}
        for uri, edits in text_edits(edit).items():
            if not edits:
                continue
            rel = self._rel(uri)
            d = self.store.doc(rel)
            if not d.open:  # an editor opens the file and changes it in memory
                self.send_open(out, rel, d)
            d.text = apply_text_edits(d.text, edits)
            d.version += 1
            self.notify(out, "textDocument/didChange", {"textDocument": {"uri": d.uri, "version": d.version},
                                                         "contentChanges": [{"text": d.text}]}, rel)
            self.edited[rel] = d.text
            applied[rel] = len(edits)
        return applied

    def op_fs_rename(self, op: Op, out: OpOutcome) -> None:
        files = [{"oldUri": self.store.uri(op.path), "newUri": self.store.uri(op.new_path)}]
        edit = None
        if self.supports_file_op("willRename"):
            edit = self.client.request("workspace/willRenameFiles", {"files": files}, timeout=self.request_timeout_s)
            out.sent.append("workspace/willRenameFiles")
        applied = self.apply_workspace_edit(edit, out)
        self.renames.append({"from": op.path, "to": op.new_path, "edits": applied})
        # the frozen rename without its willRenameFiles request: the edit has been applied already
        self.skip_will_rename = True
        try:
            super().op_fs_rename(op, out)
        finally:
            self.skip_will_rename = False
        for rel in list(self.edited):  # a renamed document moves with its buffer
            if rel == op.path:
                self.edited[op.new_path] = self.edited.pop(rel)


class ExternalRenameApplier(OpApplier):
    """OpApplier whose file rename is a move outside the editor: file-system events only."""

    def supports_file_op(self, name: str) -> bool:
        return False if name in ("willRename", "didRename") else super().supports_file_op(name)


MODES = {"edit": ("rne", EditApplier), "external": ("rnx", ExternalRenameApplier)}


def restored(project_dir: str) -> Dict[str, bool]:
    """For every document an edit touched: does it end with the project file's text?"""
    out: Dict[str, bool] = {}
    for s in SESSIONS:
        for rel, text in s.edited.items():
            path = os.path.join(project_dir, rel)
            out[rel] = os.path.exists(path) and read_text(path) == text
    return out


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default="", help="groups whose id contains this text")
    ap.add_argument("--replays", type=int, default=3)
    ap.add_argument("--mode", choices=sorted(MODES), default="edit")
    ap.add_argument("--campaign", default=CAMPAIGN)
    args = ap.parse_args()
    prefix, applier = MODES[args.mode]
    evidence = evidence_dir(args.campaign)
    rows = []
    for gid in groups_of(["C1"], args.campaign):
        if args.only not in gid:
            continue
        SESSIONS.clear()
        logger.info("group %s", gid)
        row = replay_variant(gid, prefix, replays=args.replays, applier=applier, campaign=args.campaign)
        row["renames"] = [r for s in SESSIONS for r in s.renames]
        doc, _ = load_repro(entry(gid, args.campaign)["repro"])
        row["edited_restored"] = restored(os.path.join(REPO, doc["project"]["ref"]))
        rows.append(row)
        logger.info("  -> %s %s/%s; renames with edits: %s; restored: %s", row["verdict"], row["reproduced"],
                    row["replays"], sum(1 for r in row["renames"] if r["edits"]), row["edited_restored"])
    os.makedirs(evidence, exist_ok=True)
    with open(os.path.join(evidence, f"c1_rename_{args.mode}.json"), "w", encoding="utf-8") as f:
        json.dump({"mode": args.mode, "rows": rows}, f, ensure_ascii=False, indent=1)
    lines = [f"{r['gid']}: {r['verdict']} ({r['reproduced']}/{r['replays']}); renames {len(r['renames'])}, with edits "
             f"{sum(1 for x in r['renames'] if x['edits'])}; edited files restored {r['edited_restored']} {r['error']}"
             for r in rows]
    with open(os.path.join(evidence, f"c1_rename_{args.mode}.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
