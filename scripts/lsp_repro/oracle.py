"""Path-independence oracle.

Claim under test: for a document whose final contents are C, the server's answers
should not depend on *how* the editor got to C. So we compare

  S_replay  -- snapshot after executing the scenario's edit history, and
  S_fresh   -- snapshot from a brand-new server that opens C directly,

and, in two-histories mode, S_hist1 vs S_hist2 for two different edit sequences that
reach the same C. A non-empty set difference is an oracle flag.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Tuple

import servers
from lspclient import LspClient, LspError
from scenario import Scenario, Step, open_doc
from session import Session
from textdoc import uri_for

logger = logging.getLogger(__name__)


def prepare_workspace(
    scn: Scenario,
    root: str,
    contents: Optional[Dict[str, str]] = None,
    replace_all: bool = False,
) -> str:
    """Materialize the scenario's files under `root`. Returns the workspace path.

    With `replace_all`, `contents` *is* the whole workspace (used by the fresh
    run, whose starting point must be the replay's final on-disk state).
    """
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)
    if replace_all and contents:
        files = dict(contents)
    else:
        files = dict(scn.files)
        files.update(scn.extra_files)
        if contents:
            files.update(contents)
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return root


@dataclass
class RunResult:
    label: str
    ok: bool = True
    error: str = ""
    snapshots: List[Dict[str, Any]] = field(default_factory=list)
    final_snapshot: Dict[str, Any] = field(default_factory=dict)
    final_contents: Dict[str, str] = field(default_factory=dict)
    open_at_end: List[str] = field(default_factory=list)
    requests: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    seconds: float = 0.0
    quiesced: bool = True
    snapshot_unstable: bool = False
    server_errors: List[str] = field(default_factory=list)
    log: str = ""


def _stable_snapshot(sess: Session, label: str) -> Tuple[Dict[str, Any], bool]:
    """Snapshot after quiescence, retried once: transient states must not leak in."""
    for rel in sess.watched():
        sess.quiesce(rel)
    sess.run_probes()
    first = sess.take_snapshot(label + "#1")
    time.sleep(max(1.0, sess.quiet))
    sess.quiesce()
    sess.run_probes()
    second = sess.take_snapshot(label)
    unstable = (first["diagnostics"] != second["diagnostics"]) or (first["probes"] != second["probes"])
    if unstable:
        logger.warning("snapshot %s changed between two quiescent reads", label)
    return second, unstable


def run_history(
    scn: Scenario,
    spec: servers.ServerSpec,
    workspace: str,
    log_path: str,
    steps: Optional[List[Step]] = None,
    label: str = "replay",
) -> RunResult:
    """Start a fresh server on `workspace` and execute a step list."""
    res = RunResult(label=label, log=log_path)
    t0 = time.monotonic()
    client: Optional[LspClient] = None
    spec = _isolate_data_dir(spec, workspace)
    if scn.settings_override:
        spec = replace(spec, settings=_deep_merge(spec.settings, scn.settings_override))
    try:
        if scn.settings_override and isinstance(spec.init_options, dict) and "settings" in spec.init_options:
            io = dict(spec.init_options)
            io["settings"] = spec.settings
            spec = replace(spec, init_options=io)
        client = servers.start(
            spec,
            uri_for(workspace),
            log_path,
            cwd=workspace,
            extra_folder_uris=[uri_for(os.path.join(workspace, f)) for f in scn.extra_folders],
        )
        sess = Session(scn, workspace, client, quiet=spec.quiet_seconds)
        sess.quiesce()
        sess.run_steps(steps if steps is not None else scn.steps)
        snap, unstable = _stable_snapshot(sess, "final")
        res.final_snapshot = snap
        res.snapshot_unstable = unstable
        res.snapshots = sess.snapshots
        res.requests = sess.request_results
        res.timeline = sess.timeline
        # Only still-open buffers override the on-disk state. Including closed
        # documents would resurrect files that the scenario deleted or renamed.
        res.final_contents = {rel: d.text for rel, d in sess.docs.items() if d.open}
        res.open_at_end = [rel for rel, d in sess.docs.items() if d.open]
        res.server_errors = client.server_errors()
    except (LspError, OSError, ValueError, RuntimeError) as exc:
        res.ok = False
        res.error = f"{type(exc).__name__}: {exc}"
        logger.error("run_history(%s) failed: %s", label, res.error)
    finally:
        if client is not None:
            client.shutdown()
        res.seconds = round(time.monotonic() - t0, 2)
    return res


def _deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _isolate_data_dir(spec: "servers.ServerSpec", workspace: str) -> "servers.ServerSpec":
    """Give JDT LS a private, empty -data directory per run.

    A reused Eclipse workspace carries project metadata, a build state and an
    index across runs, which is exactly the cross-run state the oracle must not
    see. pyright has no equivalent on-disk state.
    """
    if "-data" not in spec.cmd:
        return spec
    data = workspace.rstrip("/") + "-jdtls-data"
    if os.path.isdir(data):
        shutil.rmtree(data)
    os.makedirs(data, exist_ok=True)
    cmd = list(spec.cmd)
    cmd[cmd.index("-data") + 1] = data
    return replace(spec, cmd=cmd)


SKIP_DIRS = {"bin", ".metadata", "__pycache__", ".git", "node_modules", ".jdt"}


def disk_contents(root: str, limit: int = 2_000_000) -> Dict[str, str]:
    """Every text file under `root`, so a fresh run starts from the *whole* final
    state and not only from the buffers that happened to be open. Build outputs
    and server-private state are skipped."""
    out: Dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            try:
                if os.path.getsize(full) > limit:
                    continue
                with open(full, "r", encoding="utf-8") as f:
                    out[rel] = f.read()
            except (OSError, UnicodeDecodeError):
                continue
    return out


def run_fresh(
    scn: Scenario,
    spec: servers.ServerSpec,
    contents: Dict[str, str],
    workspace: str,
    log_path: str,
    opened: Optional[List[str]] = None,
    label: str = "fresh",
) -> RunResult:
    """Fresh server, files already holding the final contents, plain didOpen only."""
    prepare_workspace(scn, workspace, contents=contents, replace_all=True)
    to_open = opened if opened is not None else (list(contents.keys()) or list(scn.files.keys()))
    steps: List[Step] = [open_doc(rel) for rel in to_open]
    return run_history(scn, spec, workspace, log_path, steps=steps, label=label)


def diff_snapshots(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Per-file set difference between two normalized snapshots."""
    da = a.get("diagnostics", {}) or {}
    db = b.get("diagnostics", {}) or {}
    out: Dict[str, Any] = {"flagged": False, "files": {}, "probes": {}}
    for rel in sorted(set(da) | set(db)):
        va, vb = da.get(rel, []), db.get(rel, [])
        if va == "absent" or vb == "absent":
            if va != vb:
                out["flagged"] = True
                out["files"][rel] = {"only_in_first": [], "only_in_second": [], "note": f"{va} vs {vb}"}
            continue
        sa = set(map(tuple, va))
        sb = set(map(tuple, vb))
        only_a = sorted(sa - sb)
        only_b = sorted(sb - sa)
        if only_a or only_b:
            out["flagged"] = True
            out["files"][rel] = {
                "only_in_first": [list(x) for x in only_a],
                "only_in_second": [list(x) for x in only_b],
                "n_first": len(sa),
                "n_second": len(sb),
            }
    pa = a.get("probes", {}) or {}
    pb = b.get("probes", {}) or {}
    for key in sorted(set(pa) | set(pb)):
        va, vb = pa.get(key), pb.get(key)
        if va != vb:
            out["flagged"] = True
            out["probes"][key] = {"first": va, "second": vb}
    return out


def path_independence(
    scn: Scenario,
    spec: servers.ServerSpec,
    ws_root: str,
    log_dir: str,
    tag: str,
) -> Dict[str, Any]:
    """Full oracle: replay history, then a fresh server on the same final contents."""
    os.makedirs(log_dir, exist_ok=True)
    ws_replay = os.path.join(ws_root, f"{tag}-replay")
    prepare_workspace(scn, ws_replay)
    replay = run_history(
        scn, spec, ws_replay, os.path.join(log_dir, f"{tag}-replay.jsonl"), label="replay"
    )
    out: Dict[str, Any] = {
        "tag": tag,
        "server": spec.label,
        "replay": _summary(replay),
        "oracle_flag": None,
        "diff": None,
        "seconds": replay.seconds,
    }
    if not replay.ok:
        out["error"] = replay.error
        return out

    # Final state C = everything on disk after the replay, with the unsaved
    # buffer text of still-open documents taking precedence.
    contents = disk_contents(ws_replay)
    contents.update(replay.final_contents)
    ws_fresh = os.path.join(ws_root, f"{tag}-fresh")
    fresh = run_fresh(
        scn,
        spec,
        contents,
        ws_fresh,
        os.path.join(log_dir, f"{tag}-fresh.jsonl"),
        opened=replay.open_at_end,
        label="fresh",
    )
    out["fresh"] = _summary(fresh)
    out["seconds"] = round(replay.seconds + fresh.seconds, 2)
    if not fresh.ok:
        out["error"] = fresh.error
        return out
    d = diff_snapshots(replay.final_snapshot, fresh.final_snapshot)
    out["diff"] = d
    out["oracle_flag"] = bool(d["flagged"])

    if scn.alt_steps:
        ws_alt = os.path.join(ws_root, f"{tag}-alt")
        prepare_workspace(scn, ws_alt)
        alt = run_history(
            scn, spec, ws_alt, os.path.join(log_dir, f"{tag}-alt.jsonl"), steps=scn.alt_steps, label="alt"
        )
        out["alt"] = _summary(alt)
        if alt.ok:
            alt_all = disk_contents(ws_alt)
            alt_all.update(alt.final_contents)
            same_contents = alt_all == contents
            out["two_histories"] = {
                "same_final_contents": same_contents,
                "diff": diff_snapshots(replay.final_snapshot, alt.final_snapshot),
            }
            out["seconds"] = round(out["seconds"] + alt.seconds, 2)
    return out


def _summary(r: RunResult) -> Dict[str, Any]:
    return {
        "label": r.label,
        "ok": r.ok,
        "error": r.error,
        "seconds": r.seconds,
        "snapshot_unstable": r.snapshot_unstable,
        "server_errors": r.server_errors[:8],
        "final": r.final_snapshot.get("diagnostics", {}),
        "final_raw": r.final_snapshot.get("raw", {}),
        "final_probes": r.final_snapshot.get("probes", {}),
        "final_text": {k: v[:4000] for k, v in r.final_contents.items()},
        "snapshots": [{"label": s["label"], "diagnostics": s["diagnostics"]} for s in r.snapshots],
        "requests": [{k: v for k, v in q.items() if k != "raw"} for q in r.requests],
        "log": os.path.basename(r.log),
        "timeline_errors": [t for t in r.timeline if not t.get("ok", True)],
    }


__all__ = ["RunResult", "diff_snapshots", "path_independence", "prepare_workspace", "run_fresh", "run_history"]
