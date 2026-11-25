"""Release sweep: replay the bug groups of a campaign (--campaign, default main_v1) on other releases of their server
lines through the frozen version sweep's replay path (post-freeze evidence; the frozen tool is only imported).

Labels (data/lsptest/runs/main_v1/sweep/<label>/; rules in release_builds.RULES, fixed before any result):
  newest-2026-09-28  every bug group of triage/root_causes.csv on the newest release of its server line published
                     up to 2026-09-28 (a fresh replay where the campaign release is still the newest)
  lifecycle          one representative group per cause on older releases of its line
  newest-<date>      a refresh of newest-2026-09-28 with a later cut-off: run every subcommand with the environment
                     variable RELEASE_SWEEP_AS_OF=<date> (release_builds.AS_OF); only this label is planned and run
Server lines: gopls; rust-analyzer; ts6 = TypeScript <= 6 behind typescript-language-server, replayed through the
frozen sweep's kind "tsserver" (<typescript>+tsls<wrapper>) as older-2025 and ts_isolation.py did; ts7 = the
TypeScript 7 native server (kind "ts7", npm typescript@7.x under temp/lsp_servers/ts7-<v>/); pyright (npm pyright@<v>
under temp/lsp_servers/pyright-<v>/, installed as the benchmark installs it). A plan lists only the lines its groups
need (main_v1: gopls, rust-analyzer, ts6, ts7, as before).

Campaigns (--campaign; release_builds.set_campaign):
  main_v1    the default: groups of data/lsptest/runs/main_v1/triage/root_causes.csv, output under
             data/lsptest/runs/main_v1/sweep/<label>/; behaviour and files as before this option existed
  main_v2    groups of data/lsptest/runs/main_v2/triage/root_causes.csv, output under data/lsptest/runs/main_v2/sweep/
             <label>/; labels: lifecycle (default cut-off; the causes first listed in main_v2's table) and, with
             RELEASE_SWEEP_AS_OF, newest-<date> (every group); its builds must equal main_v1's plan of the same label on
             the lines both plan (checked by plan); run ids end in "mainv2"
Representatives (lifecycle): release_builds.REP_RULE: C1-C11 keep the groups chosen for the first sweep (REPS); a later
cause gets its first group in row order of the first campaign's table that lists it (main_v1 before main_v2).
Groups added to a root-cause table after its plan: plan --extend appends them (newest: every new group; lifecycle: the
representative of each new cause) to the existing releases.json, keeping its groups, builds and install records and
recording the addition under "extended"; run then replays only the jobs without a row.

Subcommands:
  plan       release lists -> sweep/<label>/releases.json (release_builds.plan; --force overwrites)
  install    the planned builds under temp/lsp_servers/, launch-checked; outcome in releases.json
             (release_builds.install)
  run        the jobs of the given lines, newest label first, one at a time: load_repro, prepare_repro_project,
             context_from_repro, oracle.replay x N, flake.counts, version_sweep.verdict, as the frozen sweep's
             replay_group, with run ids rl<label initial><build tag><gid6> (the frozen sweep uses sw<gid6>, so live
             session directories never collide); one row per group and build (sweep schema plus line, build_tag,
             release) appended to sweep/<label>/results.jsonl; resumable (written rows are skipped). The C2 group
             (a timing race) runs alone, as in ts_isolation.py: the other processes start no job while it is pending
             (lock temp/release_sweep.lock).
  summarize  sweep/<label>/summary.md: per line, group x build table of reproduced/replays and verdict

Run line: python3 scripts/paper/evidence/release_sweep.py plan && python3 scripts/paper/evidence/release_sweep.py install
  && nohup python3 scripts/paper/evidence/release_sweep.py run --lines gopls >> data/lsptest/runs/main_v1/evidence/release_sweep_gopls.log 2>&1 &
  (likewise --lines rust-analyzer and --lines ts6,ts7; then: python3 scripts/paper/evidence/release_sweep.py summarize)
Refresh line (label newest-2026-11-18): export RELEASE_SWEEP_AS_OF=2026-11-18, then the same plan, install, run
  (logs data/lsptest/runs/main_v1/evidence/release_sweep_<lines>_2026-11-18.log) and summarize.
Root causes of 2026-11-21 (plan/release_sweep_v2_2026-11-21.md): RELEASE_SWEEP_AS_OF=2026-11-18 ... plan --extend;
  ... plan --extend --label lifecycle; ... plan --campaign main_v2 (with and without RELEASE_SWEEP_AS_OF=2026-11-18);
  then install --campaign main_v2 and run/summarize per campaign and label, chained in temp/release_sweep_v2_chain.sh.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import logging
import os
import re
import shutil
import sys
import time
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True  # no new bytecode caches inside the frozen tree

import release_builds as rb  # noqa: E402  (CAMPAIGN and SWEEP are read through rb: --campaign rebinds them)
from release_builds import (CAMPAIGNS, FIRST_CAMPAIGN, LABELS, LIFECYCLE, LINES, NEWEST, REPO, install,  # noqa: E402
                            load_plan, plan, write_text)
import flake  # noqa: E402  (frozen tool, read-only; on sys.path through release_builds)
import oracles  # noqa: E402
import version_sweep as vs  # noqa: E402
from campaign_store import context_from_repro, load_repro, prepare_repro_project, rel, sweep_session_dirs  # noqa: E402
from driver import RUNS_DIR  # noqa: E402

logger = logging.getLogger("release_sweep")
LOCK = os.path.join(REPO, "temp", "release_sweep.lock")
SOLO = frozenset({"ts6-r1-diagnostics-extra-2304-h7-8ca52f"})  # C2: a query race right after didOpen
SOLO_CAUSE = "C2"  # every group of this cause in a plan runs alone (main_v1: the one group above)


def read_rows(label: str) -> List[Dict[str, Any]]:
    path = os.path.join(rb.SWEEP, label, "results.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def solo_pending(marker: str) -> bool:
    """True while a live process waits for or runs a solo job."""
    try:
        with open(marker, encoding="utf-8") as f:
            pid = int(f.read().strip() or "0")
        if pid > 0:
            os.kill(pid, 0)
            return True
    except (OSError, ValueError):
        pass
    return False


@contextlib.contextmanager
def slot(solo: bool) -> Iterator[None]:
    """A shared lock per job; an exclusive one for a solo job, whose marker holds new jobs of other processes back."""
    marker = LOCK + ".solo"
    if solo:
        write_text(marker, str(os.getpid()))
    else:
        while solo_pending(marker):
            time.sleep(5)
    with open(LOCK, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX if solo else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            if solo:
                with contextlib.suppress(OSError):
                    os.remove(marker)


def replay(label: str, b: Dict[str, Any], gid: str, replays: int) -> Dict[str, Any]:
    """The frozen sweep's replay_group for one group on one build, with a run id of this script."""
    entry = next(e for e in vs.group_repros(rb.CAMPAIGN) if e["gid"] == gid)
    doc, v = load_repro(entry["repro"])
    source_kind = doc["server"]["kind"]
    doc = dict(doc, server={"kind": b["kind"], "version": b["version"]})
    row: Dict[str, Any] = {"gid": gid, "signature": entry["signature"], "oracle": v.oracle, "from": source_kind,
                           "build": {"kind": b["kind"], "version": b["version"]}, "repro": rel(entry["repro"]),
                           "reduced": entry["reduced"], "replays": replays, "settled": 0, "control_stable": 0,
                           "reproduced": 0, "seconds": 0.0, "error": "", "line": b["line"], "build_tag": b["tag"],
                           "release": b["release"]}
    other = "" if rb.CAMPAIGN == FIRST_CAMPAIGN else re.sub(r"[^0-9a-z]", "", rb.CAMPAIGN)  # e.g. mainv2
    run_id = f"rl{label[0]}{b['tag']}{gid[-6:]}{other}"
    scratch = os.path.join(RUNS_DIR, f"sweep-rl-{label}-{b['tag']}" + (f"-{other}" if other else ""), gid)
    shutil.rmtree(scratch, ignore_errors=True)
    t0 = time.monotonic()
    try:
        root = prepare_repro_project(doc, scratch)
        ctx = context_from_repro(doc, root, os.path.join(scratch, "work"), run_id=run_id)
        oracle = oracles.get(v.oracle)
        for _ in range(replays):
            out = oracle.replay(ctx, v)
            row["settled"] += int(bool(out.settled))
            row["control_stable"] += int(bool(out.control_stable))
            row["reproduced"] += int(flake.counts(out))
    except Exception as exc:  # noqa: BLE001  (recorded in the row, as the frozen sweep does)
        row["error"] = f"{type(exc).__name__}: {exc}"[:400]
        logger.warning("group %s on %s %s: %s", gid, b["kind"], b["version"], row["error"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        sweep_session_dirs(run_id)
        with contextlib.suppress(OSError):
            os.rmdir(os.path.dirname(scratch))
    row["seconds"] = round(time.monotonic() - t0, 1)
    row["verdict"] = vs.verdict(row)
    return row


def solo_groups(doc: Dict[str, Any]) -> frozenset:
    """Groups of a plan that run alone: SOLO and every group of SOLO_CAUSE."""
    return SOLO | {g["gid"] for g in doc["groups"] if g["cause"] == SOLO_CAUSE}


def jobs(lines: Sequence[str], labels: Sequence[str], only: str) -> List[Tuple[str, Dict[str, Any], str, bool]]:
    """(label, build, gid, solo) in run order: label, the solo groups last, then build and group order."""
    out = []
    for li, label in enumerate(labels):
        doc = load_plan(label)
        solo = solo_groups(doc)
        for bi, b in enumerate(doc["builds"]):
            if b["line"] not in lines or b["status"] != "ok":
                continue
            for gi, g in enumerate(doc["groups"]):
                if g["line"] == b["line"] and only in g["gid"] and g["gid"] not in b.get("skip", {}):
                    out.append(((li, g["gid"] in solo, bi, gi), label, b, g["gid"]))
    return [(label, b, gid, key[1]) for key, label, b, gid in sorted(out, key=lambda x: x[0])]


def run(lines: Sequence[str], labels: Sequence[str], only: str, replays: int) -> int:
    """Run the jobs one at a time; append each row and refresh the label's summary."""
    todo = jobs(lines, labels, only)
    logger.info("%d job(s) for %s", len(todo), ",".join(lines))
    for label, b, gid, solo in todo:
        if any(r["gid"] == gid and r["build"]["version"] == b["version"] for r in read_rows(label)):
            continue
        logger.info("%s: %s on %s %s", label, gid, b["kind"], b["version"])
        with slot(solo):
            row = replay(label, b, gid, replays)
        with open(os.path.join(rb.SWEEP, label, "results.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        summarize(label)
        logger.info("  -> %s (%d/%d, %.0fs) %s", row["verdict"], row["reproduced"], replays, row["seconds"],
                    row["error"])
    logger.info("all jobs of %s done", ",".join(lines))
    return 0


def cell(b: Dict[str, Any], gid: str, rows: Dict[Tuple[str, str], Dict[str, Any]]) -> str:
    if b["status"] != "ok":
        return "unavailable"
    if gid in b.get("skip", {}):
        return "n/a (Go)"
    r = rows.get((gid, b["version"]))
    if r is None:
        return "not run"
    return f"error: {r['error'][:60]}" if r.get("error") else f"{r['reproduced']}/{r['replays']} {r['verdict']}"


def summarize(label: str) -> str:
    """Write sweep/<label>/summary.md (per line: group x build table) and return it."""
    doc = load_plan(label)
    rows = {(r["gid"], r["build"]["version"]): r for r in read_rows(label)}
    out = [f"# Release sweep `{label}` (releases published up to {doc['as_of']})", "",
           "Cell: reproduced/replays and the frozen sweep's verdict; n/a (Go) = not replayable (the project needs a "
           "newer Go than the build runs); unavailable = not installable or not launchable; not run = pending. "
           "Rules, release dates and install details: releases.json.", ""]
    for line in LINES:
        builds = [b for b in doc["builds"] if b["line"] == line]
        groups = [g for g in doc["groups"] if g["line"] == line]
        if not builds or not groups:
            continue
        out += [f"## {line}", "", f"Rule: {doc['rule'][line]}.", ""]
        for b in builds:
            extra = (f"; wrapper released {b['wrapper_released']}" if b.get("wrapper_released") else "") \
                + (f"; runs {b['go']}" if b.get("go") else "")
            state = "" if b["status"] == "ok" else f" - {b['status'].upper()}: {b.get('reason', '')[:160]}"
            out.append(f"- {b['version']} (released {b['released']}; {', '.join(b['roles'])}{extra}){state}")
        head = ["cause", "group"] + [b["version"] for b in builds]
        out += ["", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        out += ["| " + " | ".join([g["cause"], f"`{g['gid']}`"] + [cell(b, g["gid"], rows) for b in builds]) + " |"
                for g in groups]
        out.append("")
    text = "\n".join(out)
    write_text(os.path.join(rb.SWEEP, label, "summary.md"), text)
    return text


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Replay the bug groups of a campaign on other releases of their server "
                                             "lines.")
    ap.add_argument("command", choices=("plan", "install", "run", "summarize"))
    ap.add_argument("--campaign", default=FIRST_CAMPAIGN, choices=CAMPAIGNS,
                    help="whose groups and sweep directory (default main_v1)")
    ap.add_argument("--lines", default=",".join(LINES), help="comma-separated server lines (install, run)")
    ap.add_argument("--label", default="", choices=("",) + tuple(dict.fromkeys(LABELS + (NEWEST, LIFECYCLE))),
                    help="plan/run/summarize: one label only")
    ap.add_argument("--only", default="", help="run: groups whose id contains this text")
    ap.add_argument("--replays", type=int, default=3)
    ap.add_argument("--force", action="store_true", help="plan: overwrite the releases.json files")
    ap.add_argument("--extend", action="store_true",
                    help="plan: add to the existing releases.json the groups the rules now select (kept: groups, "
                         "builds, install records)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    rb.set_campaign(args.campaign)
    lines = [x for x in args.lines.split(",") if x]
    if set(lines) - set(LINES):
        ap.error(f"--lines takes {','.join(LINES)}")
    if args.label and args.label not in rb.labels():
        ap.error(f"--label takes {', '.join(rb.labels())} for {args.campaign} with this RELEASE_SWEEP_AS_OF")
    labels = [args.label] if args.label else list(rb.labels())
    if args.command == "plan":
        return plan(args.force, [args.label] if args.label else (), args.extend)
    if args.command == "install":
        return install(lines)
    if args.command == "run":
        return run(lines, labels, args.only, args.replays)
    for label in labels:
        summarize(label)
        logger.info("wrote %s", rel(os.path.join(rb.SWEEP, label, "summary.md")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
