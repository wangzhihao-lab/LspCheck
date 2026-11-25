"""Triage of a campaign's confirmed violations (plan/tool_design_v1.md section 11.2).

Groups the confirmed violations of data/lsptest/runs/<campaign>/violations.jsonl by signature,
method and case family (triage_group.py); for each group takes the representative (fewest
ops), rebuilds its project and context from its repro.json, narrows the query targets to the
key when that still reproduces, reduces the ops with reduce.reduce_and_confirm under the group
budget and, with --lines, the touched files line by line (triage_reduce.py); searches the
server's issue tracker for related issues (triage_issues.py; read-only, cached); and writes
triage/<group>/{report.md, repro.json (reduced), reduction.json, issues.json, logs/}, plus
triage/index.md, triage/triage.json and triage/decisions.csv (template; the author's rows are
never changed). A group already reduced is reused unless --redo. Nothing is filed or posted.

Run line: python3 scripts/lsptest/triage.py <campaign-id> [--lines] [--no-issues] [--no-reduce] [--redo] [--only <group substring>] [--probes 32] [--seconds 1800] [--line-probes 40] [--line-seconds 3600]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import shutil
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import flake  # noqa: E402
import oracles  # noqa: E402
from campaign_store import (REPO, CampaignPaths, context_from_repro, load_repro, paths_for, prepare_repro_project,  # noqa: E402
                            read_jsonl, rel, repro_document, sweep_session_dirs, write_json)
from driver import RUNS_DIR  # noqa: E402
from model import Violation  # noqa: E402
from ops import read_text  # noqa: E402
from queries import LSP_METHODS  # noqa: E402
from reduce import ReduceConfig  # noqa: E402
from replay_logs import ReplayRecorder, error_messages, excerpt, keep_logs  # noqa: E402
from triage_group import Group, group_rows  # noqa: E402
from triage_issues import GitHubSearch, error_phrase, search_group  # noqa: E402
from triage_reduce import LineConfig, narrow_targets, reduce_group, reduce_lines  # noqa: E402
from triage_report import render_index, render_report, write_decisions  # noqa: E402

logger = logging.getLogger("triage")


def evidence(rec: ReplayRecorder, upto: Optional[int] = None) -> Tuple[List[str], Optional[Violation]]:
    """Logs and observed violation of the last counting replay that ran the case's own ops
    (flake confirmations and the narrowing check, not reduction probes)."""
    calls = [c for c in rec.calls[:upto] if c.ops is None and flake.counts(c.outcome)]
    return (list(calls[-1].logs), calls[-1].outcome.observed) if calls else ([], None)


def project_texts(root: str, doc: Mapping[str, Any], v: Violation, reduced: Mapping[str, str]) -> Dict[str, str]:
    """Files shown in the report: the line-reduced files, all files of a small case project, or
    the key's file (the report shows the lines around the key and the ops)."""
    if reduced:
        return dict(reduced)
    paths = [v.key.path] if v.key.path not in ("", ".") else []
    if doc["project"]["source"] in ("case", "dir"):  # a small known-bug or benchmark case project: every file
        paths = sorted(os.path.relpath(os.path.join(d, n), root) for d, _, ns in os.walk(root) for n in ns)
    out = {}
    for p in paths:
        try:
            text = read_text(os.path.join(root, p))
        except OSError:
            continue
        if len(text) < 200_000:
            out[p] = text
    return out


def reduce_one(g: Group, doc: Dict[str, Any], v: Violation, gdir: str, args: argparse.Namespace
               ) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Narrow, reduce ops, optionally reduce lines; writes the group's repro.json and keeps logs."""
    scratch = os.path.join(RUNS_DIR, f"triage-{doc['campaign']}", g.gid)
    shutil.rmtree(scratch, ignore_errors=True)
    t0, red = time.monotonic(), {"vid": doc["vid"], "ops_before": len(v.ops), "narrowed": False}
    run_id = f"tr{g.gid[-6:]}"
    try:
        root = prepare_repro_project(doc, scratch)
        ctx = context_from_repro(doc, root, os.path.join(scratch, "work"), run_id=run_id)
        rec = ReplayRecorder(oracles.get(v.oracle), os.path.join(ctx.scratch(), "logs"))
        if not args.no_narrow:
            ctx, red["narrowed"] = narrow_targets(rec, ctx, v)
        ops = list(v.ops)
        if not args.no_reduce:
            ops, rres, red["reduced_confirmed"] = reduce_group(rec, ctx, v, ReduceConfig(args.probes, args.seconds))
            red.update(probes=rres.probes, cache_hits=rres.cache_hits, reduce_seconds=rres.seconds,
                       budget_exhausted=rres.exhausted, probe_log=rres.log)
        mark, files = len(rec.calls), {}
        if args.lines:
            lres = reduce_lines(rec, ctx, dataclasses.replace(v, ops=ops),
                                LineConfig(args.line_probes, args.line_seconds))
            files = dict(lres.files)
            red.update(lines={p: f"{a}/{b} non-blank lines kept" for p, (a, b) in lres.lines.items()} if files else {},
                       line_probes=lres.probes, line_seconds=lres.seconds, lines_confirmed=lres.confirmed,
                       line_skipped=lres.skipped, line_budget_exhausted=lres.exhausted)
        logs, observed = evidence(rec, None if files else mark)
        shutil.rmtree(os.path.join(gdir, "logs"), ignore_errors=True)  # logs of an earlier reduction
        red["logs"] = keep_logs(logs, os.path.join(gdir, "logs"))
        if observed is not None:
            red["observed"] = {"expected": observed.expected, "actual": observed.actual}
        rdoc = repro_document(ctx, v, campaign=doc["campaign"], vid=doc["vid"], source=doc["project"]["source"],
                              project_ref=doc["project"]["ref"], commit=doc["project"].get("commit", ""),
                              logs=[f"logs/{n}" for n in red["logs"]], files=files,
                              extra={"group": g.gid, "ops": [o.to_json() for o in ops], "reduced": True})
        if observed is not None:
            rdoc.update(expected=observed.expected, actual=observed.actual)
        write_json(os.path.join(gdir, "repro.json"), rdoc)
        shown = project_texts(root, doc, v, files)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        sweep_session_dirs(run_id)
    red.update(ops_after=len(ops), total_seconds=round(time.monotonic() - t0, 1))
    return red, shown


def triage_group(g: Group, paths: CampaignPaths, cfg_doc: Mapping[str, Any], args: argparse.Namespace,
                 fetch: Optional[GitHubSearch]) -> Dict[str, Any]:
    rep = g.representative
    doc, v = load_repro(os.path.join(REPO, rep["repro"]))
    gdir = os.path.join(paths.triage, g.gid)
    os.makedirs(gdir, exist_ok=True)
    red_path, shown_path = os.path.join(gdir, "reduction.json"), os.path.join(gdir, "files.json")
    if os.path.exists(red_path) and os.path.exists(shown_path) and not args.redo:
        with open(red_path, "r", encoding="utf-8") as f:
            red = json.load(f)
        with open(shown_path, "r", encoding="utf-8") as f:
            shown = json.load(f)
        logger.info("group %s: reusing the earlier reduction", g.gid)
    else:
        logger.info("group %s: %d member(s); representative %s with %d op(s)", g.gid, len(g.members), rep["vid"],
                    len(v.ops))
        red, shown = reduce_one(g, doc, v, gdir, args)
        write_json(red_path, red)
        write_json(shown_path, shown)
    t0 = time.monotonic()
    logs = [os.path.join(gdir, "logs", n) for n in red.get("logs") or []]
    errors = error_messages(logs, LSP_METHODS.get(g.method, g.method)) if "->error:" in g.shape else []
    phrase = error_phrase(errors[0]) if errors else ""
    issues = search_group(g.server_kind, g.oracle, g.method, g.shape, g.family, fetch, phrase=phrase) if fetch else \
        {"queries": [], "matches": [], "notes": ["issue search skipped (--no-issues)"]}
    write_json(os.path.join(gdir, "issues.json"), issues)
    rdoc, _ = load_repro(os.path.join(gdir, "repro.json"))
    build = next((b for b in cfg_doc.get("server_builds") or [] if b.get("kind") == doc["server"]["kind"]
                  and b.get("version") == doc["server"]["version"]), {})
    lines = excerpt(logs)
    cmd = f"python3 scripts/lsptest/repro_violation.py {rel(os.path.join(gdir, 'repro.json'))}"
    text = render_report(g, rdoc, red, issues, build, cfg_doc.get("machine") or {}, shown, lines, cmd)
    with open(os.path.join(gdir, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return {"gid": g.gid, "signature": g.signature, "method": g.method, "family": g.family,
            "members": len(g.members), "summary": g.summary(), "representative": rep["vid"],
            "ops_before": red.get("ops_before"), "ops_after": red.get("ops_after"),
            "lines": "; ".join(f"{p}: {s}" for p, s in (red.get("lines") or {}).items()),
            "matches": len(issues.get("matches") or []), "top_match": (issues.get("matches") or [{}])[0].get("url", ""),
            "seconds": {"reduction": red.get("total_seconds"), "issues": round(time.monotonic() - t0, 1)},
            "report": rel(os.path.join(gdir, "report.md"))}


def main() -> int:
    ap = argparse.ArgumentParser(description="Group, reduce and draft reports for confirmed violations.")
    ap.add_argument("campaign")
    ap.add_argument("--lines", action="store_true", help="also reduce the touched files line by line")
    ap.add_argument("--no-issues", action="store_true")
    ap.add_argument("--no-reduce", action="store_true")
    ap.add_argument("--no-narrow", action="store_true", help="keep every query target in the replays")
    ap.add_argument("--redo", action="store_true", help="reduce again even when a reduction exists")
    ap.add_argument("--only", default="", help="groups whose id contains this text")
    ap.add_argument("--probes", type=int, default=32)
    ap.add_argument("--seconds", type=float, default=1800.0)
    ap.add_argument("--line-probes", type=int, default=40)
    ap.add_argument("--line-seconds", type=float, default=3600.0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    paths = paths_for(args.campaign)
    with open(paths.config, "r", encoding="utf-8") as f:
        cfg_doc = json.load(f)
    groups = [g for g in group_rows(read_jsonl(paths.violations)) if args.only in g.gid]
    fetch = None if args.no_issues else GitHubSearch()
    rows = []
    for g in groups:
        rows.append(triage_group(g, paths, cfg_doc, args, fetch))
        print(f"{g.gid}: {rows[-1]['members']} member(s), ops {rows[-1]['ops_before']} -> {rows[-1]['ops_after']}"
              f"{', lines ' + rows[-1]['lines'] if rows[-1]['lines'] else ''}; {rows[-1]['matches']} issue match(es)")
    os.makedirs(paths.triage, exist_ok=True)
    index_path = os.path.join(paths.triage, "triage.json")
    everything: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(index_path):  # groups triaged earlier (e.g. with --only) stay in the index
        with open(index_path, "r", encoding="utf-8") as f:
            everything = {r["gid"]: r for r in json.load(f).get("groups", [])}
    everything.update({r["gid"]: r for r in rows})
    ordered = [everything[k] for k in sorted(everything)]
    write_json(index_path, {"campaign": args.campaign, "groups": ordered, "date": time.strftime("%Y-%m-%d %H:%M")})
    with open(os.path.join(paths.triage, "index.md"), "w", encoding="utf-8") as f:
        f.write(render_index(args.campaign, ordered))
    added = write_decisions(os.path.join(paths.triage, "decisions.csv"), [r["gid"] for r in ordered])
    for g in groups:  # only this invocation's scratch: other --only invocations may still be running
        shutil.rmtree(os.path.join(RUNS_DIR, f"triage-{args.campaign}", g.gid), ignore_errors=True)
    print(f"triage {args.campaign}: {len(rows)} group(s) processed, {len(ordered)} in the index; "
          f"{len(added)} new row(s) in decisions.csv; see {rel(paths.triage)}/index.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
