"""Evidence for the main_v2 groups the first author left open pending a replay (post-freeze; the frozen
tool is only imported, as in cross_answers.py).

push-wait     For rust-analyzer r3_routes groups whose push route lacks diagnostics that the pull route
              gives: one fresh session in the push route (the client declares no pull support, as the
              oracle's route session), the oracle's own diagnostics snapshot (open the targets, settle),
              then the session stays open for --wait seconds while every publishDiagnostics for the key's
              file is recorded with its time; afterwards one fresh session in the pull route gives the
              pull answer for the same file. Answers: does the push route ever publish what the pull route
              gives, and when.
ts-definition For one TypeScript r3_routes definitionConsistency group: on each given build, one fresh
              session opens the target file and the reference file, settles, and records definition at the
              target position and at the reference position, hover at the reference position, and the
              diagnostics of the reference file on the reference line.

Writes data/lsptest/runs/<campaign>/evidence/open_groups_<subcommand>.json (rows appended per group,
replacing an earlier row of the same group and build).

Run line: python3 scripts/paper/evidence/open_groups_v2.py push-wait [--campaign main_v2] --only <gid substr> [--wait 180]
          python3 scripts/paper/evidence/open_groups_v2.py ts-definition [--campaign main_v2] --only <gid substr>
                  [--builds ts7:7.0.2,ts6:6.0.3]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))
import oracles  # noqa: E402  (frozen tool, read-only)
import version_sweep as vs  # noqa: E402
from campaign_store import context_from_repro, load_repro, prepare_repro_project, sweep_session_dirs  # noqa: E402
from driver import RUNS_DIR  # noqa: E402

logger = logging.getLogger("open_groups_v2")


def _code(d: Dict[str, Any]) -> str:
    c = d.get("code")
    if isinstance(c, dict):
        c = c.get("value")
    return f"{c}/{d.get('source', '')}"


def _codes(diags: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for d in diags:
        out[_code(d)] = out.get(_code(d), 0) + 1
    return dict(sorted(out.items()))


def _rel(uri: str, root: str) -> str:
    """Path relative to the project: the session works in a copy under <session dir>/ws/."""
    path = unquote(urlparse(uri).path)
    if path.startswith(root):
        return os.path.relpath(path, root)
    return path.split("/ws/", 1)[1] if "/ws/" in path else os.path.basename(path)


def _locations(result: Any, root: str) -> List[List[Any]]:
    if result is None:
        return []
    items = result if isinstance(result, list) else [result]
    out = []
    for it in items:
        uri = it.get("targetUri") or it.get("uri")
        rng = it.get("targetSelectionRange") or it.get("range") or {}
        s, e = rng.get("start", {}), rng.get("end", {})
        out.append([_rel(uri, root), s.get("line"), s.get("character"), e.get("line"), e.get("character")])
    return sorted(out)


def _prepare(entry: Dict[str, Any], tag: str, server: Optional[Dict[str, str]] = None) -> Tuple[Any, Any, Any, str, str]:
    doc, v = load_repro(entry["repro"])
    if server:
        doc = dict(doc, server=server)
    run_id = f"{tag}{entry['gid'][-6:]}"
    scratch = os.path.join(RUNS_DIR, f"evidence-{tag}", entry["gid"])
    shutil.rmtree(scratch, ignore_errors=True)
    root = prepare_repro_project(doc, scratch)
    ctx = context_from_repro(doc, root, os.path.join(scratch, "work"), run_id=run_id)
    return doc, v, ctx, scratch, run_id


def push_wait(entry: Dict[str, Any], wait_s: float) -> Dict[str, Any]:
    """Push-route session kept open after the snapshot; then the pull answer for the same file."""
    oracles.get("r3_routes")
    from oracles.base import session  # noqa: E402
    from oracles.r3_routes import QueryConfig  # noqa: E402
    row: Dict[str, Any] = {"gid": entry["gid"], "error": ""}
    t0 = time.monotonic()
    scratch, run_id = "", ""
    try:
        doc, v, ctx, scratch, run_id = _prepare(entry, "pw")
        path = v.key.path
        row.update(server=doc.get("server"), project=doc.get("project"), path=path, wait_s=wait_s)
        qcfg = QueryConfig(methods=("diagnostics",), request_timeout_s=ctx.request_timeout_s)
        with session(ctx, "pushwait-push", pull=False) as d:
            snap = d.snapshot("pushwait-push", list(ctx.targets), qcfg)
            row["push_settled"], row["push_pull_mode"] = bool(snap.settled), d.pull_mode()
            row["push_assumed"] = list(d.last_settle.assumed if d.last_settle else [])
            uri, start, seen, timeline = d.uri(path), time.monotonic(), None, []
            while True:
                d.monitor.poll()
                pub = d.monitor.publish_for(uri)
                state = None if pub is None else (pub.index, pub.version)
                if state != seen:
                    seen = state
                    timeline.append({"after_snapshot_s": round(time.monotonic() - start, 1),
                                     "publish_index": None if pub is None else pub.index,
                                     "version": None if pub is None else pub.version,
                                     "n": None if pub is None else len(pub.diagnostics),
                                     "codes": {} if pub is None else _codes(pub.diagnostics)})
                if time.monotonic() - start >= wait_s:
                    break
                time.sleep(5)
            row["push_timeline"] = timeline
        with session(ctx, "pushwait-pull", pull=True) as d:
            snap = d.snapshot("pushwait-pull", list(ctx.targets), qcfg)
            res, err = d.diagnostics(path, ctx.request_timeout_s)
            items = (res or {}).get("items", res) if isinstance(res, dict) else (res or [])
            row.update(pull_settled=bool(snap.settled), pull_mode=d.pull_mode(), pull_error=err,
                       pull_n=len(items or []), pull_codes=_codes(items or []))
    except Exception as exc:  # noqa: BLE001  (recorded per group, as the sweep does)
        row["error"] = f"{type(exc).__name__}: {exc}"[:400]
        logger.warning("group %s: %s", entry["gid"], row["error"])
    finally:
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)
        if run_id:
            sweep_session_dirs(run_id)
    row["seconds"] = round(time.monotonic() - t0, 1)
    return row


def ts_definition(entry: Dict[str, Any], build: Tuple[str, str]) -> Dict[str, Any]:
    """Definition at the target and at the reference, hover and diagnostics at the reference, on `build`."""
    oracles.get("r3_routes")
    from oracles.base import session  # noqa: E402
    row: Dict[str, Any] = {"gid": entry["gid"], "build": list(build), "error": ""}
    t0 = time.monotonic()
    scratch, run_id = "", ""
    try:
        doc, v, ctx, scratch, run_id = _prepare(entry, f"td{build[0][-1]}", {"kind": build[0], "version": build[1]})
        key = v.key
        frm = str(key.extra).split("from:", 1)[1]
        tpath, tline, tchar = frm.rsplit(":", 2)
        row.update(project=doc.get("project"), target=[tpath, int(tline), int(tchar)],
                   reference=[key.path, key.line, key.character])
        root = ctx.project_dir
        with session(ctx, f"tsdef-{build[0]}") as d:
            d.open(tpath, key.path)
            st = d.settle()
            row["settled"] = bool(st.settled)
            to = ctx.request_timeout_s
            pos = lambda p, l, c: {"textDocument": {"uri": d.uri(p)}, "position": {"line": l, "character": c}}  # noqa: E731
            res, err = d.request("textDocument/definition", pos(tpath, int(tline), int(tchar)), to)
            row["definition_at_target"], row["definition_at_target_error"] = _locations(res, root), err
            res, err = d.request("textDocument/definition", pos(key.path, key.line, key.character), to)
            row["definition_at_reference"], row["definition_at_reference_error"] = _locations(res, root), err
            res, err = d.request("textDocument/hover", pos(key.path, key.line, key.character), to)
            contents = (res or {}).get("contents") if isinstance(res, dict) else None
            text = contents.get("value") if isinstance(contents, dict) else json.dumps(contents, ensure_ascii=False)
            row["hover_at_reference"], row["hover_error"] = (text or "")[:400], err
            res, err = d.diagnostics(key.path, to)
            items = (res or {}).get("items", res) if isinstance(res, dict) else (res or [])
            on_line = [x for x in (items or []) if x.get("range", {}).get("start", {}).get("line") == key.line]
            row["diagnostics_on_reference_line"] = [{"code": _code(x), "message": str(x.get("message", ""))[:200]}
                                                     for x in on_line]
            row["diagnostics_reference_file_codes"] = _codes(items or [])
    except Exception as exc:  # noqa: BLE001
        row["error"] = f"{type(exc).__name__}: {exc}"[:400]
        logger.warning("group %s on %s: %s", entry["gid"], build, row["error"])
    finally:
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)
        if run_id:
            sweep_session_dirs(run_id)
    row["seconds"] = round(time.monotonic() - t0, 1)
    return row


def write_rows(campaign: str, sub: str, rows: List[Dict[str, Any]]) -> str:
    out_dir = os.path.join(REPO, "data", "lsptest", "runs", campaign, "evidence")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"open_groups_{sub}.json")
    old = json.load(open(path, encoding="utf-8"))["rows"] if os.path.exists(path) else []
    key = lambda r: (r["gid"], tuple(r.get("build") or []))  # noqa: E731
    merged = {key(r): r for r in old}
    merged.update({key(r): r for r in rows})
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"campaign": campaign, "subcommand": sub, "written": time.strftime("%Y-%m-%d %H:%M"),
                   "rows": list(merged.values())}, f, ensure_ascii=False, indent=1)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sub", choices=("push-wait", "ts-definition"))
    ap.add_argument("--campaign", default="main_v2")
    ap.add_argument("--only", required=True, help="groups whose id contains this text")
    ap.add_argument("--wait", type=float, default=180.0)
    ap.add_argument("--builds", default="ts7:7.0.2,ts6:6.0.3")
    args = ap.parse_args(argv)
    entries = [e for e in vs.group_repros(args.campaign) if args.only in e["gid"]]
    if not entries:
        logger.error("no group of %s contains %r", args.campaign, args.only)
        return 2
    rows = []
    for e in entries:
        if args.sub == "push-wait":
            logger.info("push-wait %s (%.0f s)", e["gid"], args.wait)
            rows.append(push_wait(e, args.wait))
        else:
            for b in args.builds.split(","):
                kind, _, version = b.partition(":")
                logger.info("ts-definition %s on %s %s", e["gid"], kind, version)
                rows.append(ts_definition(e, (kind, version)))
    print(write_rows(args.campaign, args.sub, rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
