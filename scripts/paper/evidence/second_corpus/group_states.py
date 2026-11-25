"""Rebuild the file states of a triage group offline (shared by the second-corpus evidence checks).

What it does: for a group's repro.json (read with the frozen tool's load_repro, read-only) it gives the file
as committed (base), the state before the fix or completion (pre: the reduced ops without the fix ops) and
after it (post: all ops, or the completion/quick-fix edit applied to pre). The edit of a quick fix that is
not in the ops (case kind 'quickfix') is read from the codeAction answer in the group's case replay log.

Reads: data/lsptest/runs/<campaign>/triage/<gid>/repro.json and its replay logs; the corpus clones the
repro names (read-only). Writes nothing.

Run line: imported by the other scripts in scripts/paper/evidence/second_corpus/; not run directly.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))

from campaign_store import load_repro  # noqa: E402  (frozen tool, read-only)
from oracles.base import final_state  # noqa: E402
from ops import apply_change, read_text  # noqa: E402

RUNS = os.path.join(REPO, "data", "lsptest", "runs")
OUT = os.path.join(RUNS, "main_v2", "evidence", "checks")
SCRATCH = os.path.join(REPO, "temp", "evidence_scratch_v2")


def scrub(text: str) -> str:
    """Replace local absolute paths by the placeholders <scratch>, <repo> and ~.

    Args:
        text: any text that may hold local paths.

    Returns:
        The text with the scratch directory, the repository and the home directory replaced.
    """
    return text.replace(SCRATCH, "<scratch>").replace(REPO, "<repo>").replace(os.path.expanduser("~"), "~")


def group_dir(campaign: str, gid: str) -> str:
    """Triage directory of a group.

    Args:
        campaign: campaign name (main_v1, main_v2).
        gid: triage group id.

    Returns:
        Absolute path of the group's triage directory.
    """
    return os.path.join(RUNS, campaign, "triage", gid)


def apply_lsp_edits(text: str, edits: Sequence[Dict[str, Any]]) -> str:
    """Apply LSP TextEdits ({range, newText}) from the last to the first.

    Args:
        text: document text.
        edits: LSP TextEdit objects.

    Returns:
        The edited text.
    """
    out = text

    def key(e: Dict[str, Any]) -> Tuple[int, int]:
        return e["range"]["start"]["line"], e["range"]["start"]["character"]

    for e in sorted(edits, key=key, reverse=True):
        r = e["range"]
        out = apply_change(out, (r["start"]["line"], r["start"]["character"]),
                           (r["end"]["line"], r["end"]["character"]), e["newText"])[0]
    return out


def logged_fix_edit(campaign: str, gid: str, title: str, path: str) -> List[Dict[str, Any]]:
    """Edits of the code action `title` for `path` from the case replay log (first answer that has it).

    Args:
        campaign: campaign name.
        gid: triage group id.
        title: code action title.
        path: project-relative path of the edited file.

    Returns:
        The TextEdits of that code action for that file.

    Raises:
        LookupError: no logged answer carries the edit.
    """
    d = group_dir(campaign, gid)
    with open(os.path.join(d, "repro.json"), encoding="utf-8") as f:
        doc = json.load(f)
    logs = [p for p in doc.get("replay_logs", []) if "-case-" in p]
    for rel in logs:
        with gzip.open(os.path.join(d, rel), "rt", encoding="utf-8") as f:
            for line in f:
                msg = json.loads(line).get("msg", {})
                res = msg.get("result") if isinstance(msg, dict) else None
                if not isinstance(res, list):
                    continue
                for act in res:
                    if not isinstance(act, dict) or act.get("title") != title or "edit" not in act:
                        continue
                    for ch in act["edit"].get("documentChanges", []):
                        if ch.get("textDocument", {}).get("uri", "").endswith("/" + path):
                            return list(ch["edits"])
    raise LookupError(f"no logged edit for {title!r} in {gid}")


def _content(files: Dict[str, Optional[str]], path: str, base: str) -> Optional[str]:
    """Final content of `path`: final_state lists changed paths only, so an absent path is unchanged."""
    return files[path] if path in files else base


def states(campaign: str, gid: str) -> Tuple[Dict[str, Any], str, str, Dict[str, Optional[str]]]:
    """Base, pre and post content of the case file of a quick-fix, mutation or completion group.

    Args:
        campaign: campaign name.
        gid: triage group id.

    Returns:
        (repro document, project directory, case path, {"base", "pre", "post"} contents).

    Raises:
        ValueError: the case kind is not mutation, completion or quickfix.
    """
    doc, v = load_repro(os.path.join(group_dir(campaign, gid), "repro.json"))
    project = os.path.join(REPO, doc["project"]["ref"])
    case = doc["case"]
    path = case["path"]
    ops = list(v.ops)
    base = read_text(os.path.join(project, path))
    if case.get("kind") == "mutation":
        n_fix = len(case["fix_ops"])
        pre = _content(final_state(project, ops[:len(ops) - n_fix]).files, path, base)
        post = _content(final_state(project, ops).files, path, base)
    elif case.get("kind") == "completion":
        pre = _content(final_state(project, ops).files, path, base)
        post = apply_lsp_edits(pre or "", case["edits"])
    elif case.get("kind") == "quickfix":
        pre = _content(final_state(project, ops).files, path, base)
        post = apply_lsp_edits(pre or "", logged_fix_edit(campaign, gid, case["title"], path))
    else:
        raise ValueError(f"{gid}: unsupported case kind {case.get('kind')!r}")
    return doc, project, path, {"base": base, "pre": pre, "post": post}


def final_files(campaign: str, gid: str) -> Tuple[Dict[str, Any], str, Dict[str, Optional[str]]]:
    """Final content of an R1 history: what the fresh session sees on disk.

    Args:
        campaign: campaign name.
        gid: triage group id.

    Returns:
        (repro document, project directory, {path: final content or None if deleted}) for changed paths.
    """
    doc, v = load_repro(os.path.join(group_dir(campaign, gid), "repro.json"))
    project = os.path.join(REPO, doc["project"]["ref"])
    return doc, project, dict(final_state(project, list(v.ops)).files)


def snippet(text: str, first: int, last: int) -> List[str]:
    """Numbered lines first..last (0-based, inclusive), shown 1-based.

    Args:
        text: document text.
        first: first line (0-based).
        last: last line (0-based, inclusive).

    Returns:
        Lines formatted as '<1-based number> | <text>'.
    """
    lines = text.split("\n")
    lo, hi = max(0, first), min(len(lines) - 1, last)
    return [f"{i + 1:5d} | {lines[i]}" for i in range(lo, hi + 1)]


def setup_logging(name: str) -> None:
    """Log to stderr and to <OUT>/<name>.log (appended; one block per run).

    Args:
        name: log file stem.
    """
    os.makedirs(OUT, exist_ok=True)
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=[
        logging.StreamHandler(), logging.FileHandler(os.path.join(OUT, f"{name}.log"), encoding="utf-8")])
