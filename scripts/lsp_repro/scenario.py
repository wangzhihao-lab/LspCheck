"""Scenario abstraction: a workspace plus an ordered list of editing steps.

A Scenario is declarative so the *same* step list can be replayed against several
server versions, and so a "fresh server, final contents" run can be derived from it
automatically (that is what the path-independence oracle needs).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)

Range = Dict[str, Dict[str, int]]


# ------------------------------------------------------------------ steps
@dataclass
class Step:
    kind: str
    path: Optional[str] = None
    range_fn: Optional[Callable[[str], Range]] = None
    text: str = ""
    seconds: float = 0.0
    method: Optional[str] = None
    params_fn: Optional[Callable[["Session"], Any]] = None
    label: str = ""
    incremental: bool = True
    note: str = ""
    normalize: Optional[Callable[[Any], Any]] = None
    count: int = 1
    optional: bool = False


def open_doc(path: str, label: str = "") -> Step:
    return Step("open", path=path, label=label or f"open {path}")


def edit(path: str, range_fn: Callable[[str], Range], text: str, label: str = "", incremental: bool = True) -> Step:
    return Step("edit", path=path, range_fn=range_fn, text=text, label=label or f"edit {path}", incremental=incremental)


def multi_edit(
    path: str,
    edits_fn: Callable[[str], List[Tuple[Range, str]]],
    label: str = "",
) -> Step:
    """Several range edits in ONE didChange, the way batching editors send them.

    LSP says the changes are applied in order, each against the document as left
    by the previous one. Clients that batch (Sublime's LSP, for instance) exercise
    a different code path in the server than one change per notification, which is
    where #4248 was reported.
    """
    return Step("multi_edit", path=path, range_fn=edits_fn, label=label or f"multi_edit {path}")


def full_edit(path: str, text: str, label: str = "") -> Step:
    return Step("full_edit", path=path, text=text, label=label or f"full_edit {path}")


def undo(path: str, label: str = "", count: int = 1) -> Step:
    """Inverse of the last `count` edits (a code action can be several edits)."""
    return Step("undo", path=path, label=label or f"undo x{count} {path}", count=count)


def save(path: str, label: str = "") -> Step:
    return Step("save", path=path, label=label or f"save {path}")


def close_doc(path: str, label: str = "") -> Step:
    return Step("close", path=path, label=label or f"close {path}")


def wait(seconds: float = 2.0, label: str = "") -> Step:
    return Step("wait", seconds=seconds, label=label or f"wait {seconds}s")


def quiesce(path: Optional[str] = None, label: str = "") -> Step:
    """Wait for the server to settle. With `path`, first wait for that document's
    diagnostics to be republished at the current version (pyright reports versions)."""
    return Step("quiesce", path=path, label=label or f"quiesce {path or ''}".strip())


def request(
    method: str,
    params_fn: Callable[["Session"], Any],
    label: str = "",
    normalize: Optional[Callable[[Any], Any]] = None,
) -> Step:
    """A server request. `normalize` reduces the reply to a comparable form; a
    request used as a probe must have one, or the oracle cannot diff it."""
    return Step("request", method=method, params_fn=params_fn, label=label or method, normalize=normalize)


def snapshot(label: str = "snap") -> Step:
    return Step("snapshot", label=label)


def apply_workspace_edit(
    params_fn: Callable[["Session"], Any], label: str = "apply code action", optional: bool = False
) -> Step:
    """Apply a server-returned WorkspaceEdit to the tracked documents.

    `params_fn` digs the edit out of `sess.request_results`, so a scenario can
    apply a real code action rather than a hand-written approximation of it.
    Each applied edit is pushed on the undo stack, so `undo` reverses it. With
    `optional`, an absent or empty edit is skipped instead of failing the run --
    needed when the point of the step is that a fixed server returns no edit.
    """
    return Step("apply_workspace_edit", params_fn=params_fn, label=label, optional=optional)


def change_settings(params_fn: Callable[["Session"], Any], label: str = "didChangeConfiguration") -> Step:
    """Push new settings and update what the server sees on workspace/configuration
    pull requests, so a config change is consistent both ways."""
    return Step("change_settings", params_fn=params_fn, label=label)


def add_folder(path: str, label: str = "") -> Step:
    """Announce a new workspace folder *after* documents are already open."""
    return Step("add_folder", path=path, label=label or f"add folder {path}")


def fs_write(path: str, text: str, label: str = "") -> Step:
    """Write a file on disk (without opening it) and report it as a watched-file
    change. This is how a build file or config changes outside the editor."""
    return Step("fs_write", path=path, text=text, label=label or f"fs_write {path}")


def fs_rename(path: str, new_path: str, label: str = "") -> Step:
    return Step("fs_rename", path=path, text=new_path, label=label or f"rename {path}->{new_path}")


@dataclass
class Scenario:
    name: str
    files: Dict[str, str]
    steps: List[Step]
    server: str = "pyright"
    issue: str = ""
    description: str = ""
    quiet_seconds: float = 2.5
    quiesce_timeout: float = 120.0
    # Files whose diagnostics are compared by the oracle. Empty == all opened.
    watch: List[str] = field(default_factory=list)
    # Optional second history reaching the same final contents.
    alt_steps: Optional[List[Step]] = None
    extra_files: Dict[str, str] = field(default_factory=dict)
    # Extra workspace folders (relative to the workspace root) announced at
    # initialize, for bugs that only appear with several folders open.
    extra_folders: List[str] = field(default_factory=list)
    # Request steps replayed identically in every run just before the final
    # snapshot, so the oracle can compare definition/hover/codeAction answers
    # and not only diagnostics.
    probes: List[Step] = field(default_factory=list)
    # Deep-merged over the server's default settings for this scenario only.
    settings_override: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "Range",
    "Scenario",
    "Step",
    "apply_workspace_edit",
    "close_doc",
    "edit",
    "add_folder",
    "change_settings",
    "fs_rename",
    "fs_write",
    "full_edit",
    "multi_edit",
    "open_doc",
    "quiesce",
    "request",
    "save",
    "snapshot",
    "undo",
    "wait",
]
