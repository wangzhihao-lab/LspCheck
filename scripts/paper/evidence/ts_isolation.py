"""Component isolation for the ts6 causes C1 and C2 (typescript-language-server 6.0.0 +
TypeScript 6.0.3 in the campaign): replay their triage groups, 3 replays each, through the
frozen version sweep on builds that change one component at a time.

Builds (sweep kind "tsserver": the pinned typescript-language-server started with the pinned
tsserver.js named explicitly):
  ctl  6.0.3+tsls6.0.0  the campaign's components through the sweep's launch kind (control)
  a    6.0.3+tsls6.0.1  newer wrapper release (2026-09-24), same TypeScript
  b    5.9.3+tsls6.0.0  older TypeScript, same wrapper
  c    6.0.3+tsls5.0.0  older wrapper, same TypeScript
The earlier sweep `older-2025` already holds 5.9.3+tsls5.0.0 (both components older).

Subcommands:
  install    npm-install the builds into temp/lsp_servers/ through install_builds.install_tsserver
             (the build status file under data/ is not written)
  run        phase 1: the C2 group on every build, one replay job at a time (C2 is a timing race,
             so nothing else runs beside it); phase 2: the C1 groups, at most --workers jobs at
             once, never two jobs of the same group (the sweep keys session directories by group)
             nor of the same label (every sweep job rewrites its label's summary.md). Resumable:
             the sweep skips groups already in its results.jsonl.
  job        one group on one build (started by `run`): the frozen sweep's replay_group logic
             (load_repro, prepare_repro_project, context_from_repro, oracle.replay x N, flake.counts,
             version_sweep.verdict/summary) with one change: the run id is iso<tag><gid[-6:]> instead
             of sw<gid[-6:]>. The frozen sweep removes every temp/lsptest_runs/*-sw<gid6>-* session
             directory when it finishes a group, so a second sweep of the same group running at the
             same time (another label) would lose its live workspaces; distinct run ids rule that out.
             The row (same schema) is appended to sweep/<label>/results.jsonl and summary.md rewritten.
  summarize  cause x group x build verdict table -> data/lsptest/runs/main_v1/evidence/ts_isolation.md;
             with --doc also replaces the table block between the markers in plan/bug_evidence.md

Outputs: data/lsptest/runs/main_v1/sweep/iso-*/ (sweep results), per-job logs in
data/lsptest/runs/main_v1/evidence/ts_isolation_logs/.

Run line: python3 scripts/paper/evidence/ts_isolation.py install && nohup python3 scripts/paper/evidence/ts_isolation.py run --workers 2 >> data/lsptest/runs/main_v1/evidence/ts_isolation_run.log 2>&1 &  (then: python3 scripts/paper/evidence/ts_isolation.py summarize)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
CAMPAIGN = "main_v1"
RUN_ROOT = os.path.join(REPO, "data", "lsptest", "runs", CAMPAIGN)
TRIAGE = os.path.join(RUN_ROOT, "triage")
SWEEP = os.path.join(RUN_ROOT, "sweep")
EVIDENCE = os.path.join(RUN_ROOT, "evidence")
LOG_DIR = os.path.join(EVIDENCE, "ts_isolation_logs")
SERVERS_DIR = os.path.join(REPO, "temp", "lsp_servers")
CAUSES = ("C1", "C2")
REFERENCE_LABEL = "older-2025"
REFERENCE_VERSION = "5.9.3+tsls5.0.0"

logger = logging.getLogger("ts_isolation")


@dataclass(frozen=True)
class Build:
    """One TypeScript + wrapper combination replayed by the sweep."""

    tag: str
    version: str
    note: str

    @property
    def label(self) -> str:
        ts, wrapper = self.version.split("+tsls")
        return f"iso-ts{ts}-tsls{wrapper}"


BUILDS: Tuple[Build, ...] = (
    Build("a", "6.0.3+tsls6.0.1", "newer wrapper, same TypeScript"),
    Build("b", "5.9.3+tsls6.0.0", "older TypeScript, same wrapper"),
    Build("c", "6.0.3+tsls5.0.0", "older wrapper, same TypeScript"),
    Build("ctl", "6.0.3+tsls6.0.0", "campaign components, sweep launch kind (control)"),
)


def cause_groups() -> Dict[str, List[str]]:
    """Triage group ids per cause for C1 and C2, from triage/root_causes.csv."""
    out: Dict[str, List[str]] = {c: [] for c in CAUSES}
    with open(os.path.join(TRIAGE, "root_causes.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["cause"] in out:
                out[row["cause"]].append(row["group"])
    return out


def read_rows(label: str) -> Dict[str, dict]:
    """gid -> last sweep row of a label (empty when the label has not run)."""
    path = os.path.join(SWEEP, label, "results.jsonl")
    rows: Dict[str, dict] = {}
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                rows[row["gid"]] = row
    return rows


def installed_versions(version: str) -> Tuple[str, str]:
    """(typescript, typescript-language-server) versions found in a build's install directory."""
    got = []
    for pkg in ("typescript", "typescript-language-server"):
        pj = os.path.join(SERVERS_DIR, f"tsserver-{version}", "node_modules", pkg, "package.json")
        try:
            with open(pj, encoding="utf-8") as f:
                got.append(str(json.load(f).get("version", "")))
        except (OSError, json.JSONDecodeError):
            got.append("")
    return got[0], got[1]


def install() -> int:
    """Install every build (npm); return the number of failures."""
    sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))
    from bench.install_builds import InstallError, install_tsserver  # noqa: E402  (frozen tool, read-only)
    failed = 0
    for b in BUILDS:
        try:
            res = install_tsserver(b.version)
            logger.info("%s %s: %s", b.tag, b.version, res.detail)
        except (InstallError, OSError, subprocess.SubprocessError) as exc:
            failed += 1
            logger.error("%s %s: install failed: %s", b.tag, b.version, exc)
    return failed


def job(tag: str, gid: str, replays: int) -> int:
    """Replay one group on one build with a run id of its own; append the row; 0 when it ran."""
    sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))
    import shutil  # noqa: E402
    import flake  # noqa: E402  (frozen tool, read-only)
    import oracles  # noqa: E402
    import version_sweep as vs  # noqa: E402
    from campaign_store import context_from_repro, load_repro, prepare_repro_project, sweep_session_dirs  # noqa: E402
    from driver import RUNS_DIR  # noqa: E402
    b = next(x for x in BUILDS if x.tag == tag)
    entry = next(e for e in vs.group_repros(CAMPAIGN) if e["gid"] == gid)
    doc, v = load_repro(entry["repro"])
    doc = dict(doc, server={"kind": "tsserver", "version": b.version})
    row = {"gid": gid, "signature": entry["signature"], "oracle": v.oracle, "from": "ts6",
           "build": {"kind": "tsserver", "version": b.version}, "repro": os.path.relpath(entry["repro"], REPO),
           "reduced": entry["reduced"], "replays": replays, "settled": 0, "control_stable": 0, "reproduced": 0,
           "seconds": 0.0, "error": ""}
    run_id = f"iso{b.tag}{gid[-6:]}"
    scratch = os.path.join(RUNS_DIR, f"sweep-{b.label}", gid)
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
        logger.warning("group %s on %s: %s", gid, b.version, row["error"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        sweep_session_dirs(run_id)
    row["seconds"] = round(time.monotonic() - t0, 1)
    row["verdict"] = vs.verdict(row)
    out_dir = os.path.join(SWEEP, b.label)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(vs.summary(list(read_rows(b.label).values()), b.label, {"ts6": ("tsserver", b.version)}))
    print(f"{gid}: {row['verdict']} ({row['reproduced']}/{replays}, {row['seconds']}s) {row['error']}")
    return 0


def start_job(b: Build, gid: str, replays: int) -> subprocess.Popen:
    """Start one job (one group on one build) as a child process; its output goes to a log file."""
    os.makedirs(LOG_DIR, exist_ok=True)
    cmd = [sys.executable, os.path.abspath(__file__), "job", "--tag", b.tag, "--gid", gid, "--replays", str(replays)]
    log = open(os.path.join(LOG_DIR, f"{b.label}__{gid}.log"), "a", encoding="utf-8")
    log.write(f"$ {' '.join(os.path.relpath(c, REPO) if c.startswith(REPO) else c for c in cmd[1:])}\n")
    log.flush()
    logger.info("start %s on %s", gid, b.version)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.Popen(cmd, cwd=REPO, stdout=log, stderr=subprocess.STDOUT, env=env)


def expected_seconds() -> Dict[str, float]:
    """Per-group duration in the reference sweep (orders phase 2 slowest first)."""
    return {gid: float(r.get("seconds") or 0.0) for gid, r in read_rows(REFERENCE_LABEL).items()}


def run(workers: int, replays: int) -> int:
    """Phase 1 (C2 alone, sequential) then phase 2 (C1, bounded parallel); return 0."""
    groups = cause_groups()
    for b in BUILDS:
        for gid in groups["C2"]:
            if gid not in read_rows(b.label):
                start_job(b, gid, replays).wait()
    secs = expected_seconds()
    order = sorted(groups["C1"], key=lambda g: -secs.get(g, 120.0))
    todo: List[Tuple[Build, str]] = [(b, g) for g in order for b in BUILDS if g not in read_rows(b.label)]
    running: List[Tuple[subprocess.Popen, Build, str]] = []
    while todo or running:
        running = [r for r in running if r[0].poll() is None]
        busy_groups = {r[2] for r in running}
        busy_labels = {r[1].label for r in running}
        for item in list(todo):
            if len(running) >= workers:
                break
            b, gid = item
            if gid in busy_groups or b.label in busy_labels:
                continue
            running.append((start_job(b, gid, replays), b, gid))
            busy_groups.add(gid)
            busy_labels.add(b.label)
            todo.remove(item)
        time.sleep(5)
    logger.info("all jobs finished")
    return 0


def cell(row: Optional[dict]) -> str:
    """Verdict cell: verdict (reproduced/replays), or the error text."""
    if not row:
        return "not run"
    if row.get("error"):
        return f"error: {row['error'][:120]}"
    return f"{row['verdict']} ({row['reproduced']}/{row['replays']})"


DOC = os.path.join(REPO, "plan", "bug_evidence.md")
DOC_START, DOC_END = "<!-- ts_isolation table start -->", "<!-- ts_isolation table end -->"


def update_doc(text: str) -> bool:
    """Replace the table block between the markers in plan/bug_evidence.md; False when absent."""
    try:
        with open(DOC, encoding="utf-8") as f:
            doc = f.read()
    except OSError:
        return False
    i, j = doc.find(DOC_START), doc.find(DOC_END)
    if i < 0 or j < i:
        return False
    stamp = time.strftime("%Y-%m-%d %H:%M")
    block = f"{DOC_START}\nGenerated {stamp} by `python3 scripts/paper/evidence/ts_isolation.py summarize --doc`.\n\n{text}"
    with open(DOC, "w", encoding="utf-8") as f:
        f.write(doc[:i] + block + doc[j:])
    return True


def summarize() -> str:
    """Markdown table of the verdicts per cause, group and build; written to the evidence dir."""
    groups = cause_groups()
    ref = read_rows(REFERENCE_LABEL)
    per_build = {b.tag: read_rows(b.label) for b in BUILDS}
    head = ["cause", "group", f"ts6 campaign (6.0.3+tsls6.0.0)"] + \
        [f"{b.tag}: {b.version}" for b in BUILDS] + [f"{REFERENCE_LABEL}: {REFERENCE_VERSION}"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for cause in CAUSES:
        for gid in groups[cause]:
            cells = [cause, f"`{gid}`", "reproduced (3/3, triage)"] + [cell(per_build[b.tag].get(gid)) for b in BUILDS] \
                + [cell(ref.get(gid))]
            lines.append("| " + " | ".join(cells) + " |")
    tally = ["", "Per build (C1 groups; C2 group):", ""]
    for b in list(BUILDS) + [Build("ref", REFERENCE_VERSION, "both older")]:
        rows = ref if b.tag == "ref" else per_build[b.tag]
        for cause in CAUSES:
            verdicts = [(rows.get(g) or {}).get("verdict", "not run") for g in groups[cause]]
            counts = {v: verdicts.count(v) for v in sorted(set(verdicts))}
            ts, wr = installed_versions(b.version) if b.tag != "ref" else ("5.9.3", "5.0.0")
            tally.append(f"- {b.tag} {b.version} ({b.note}; installed typescript {ts or '-'}, wrapper {wr or '-'}) "
                         f"{cause}: " + ", ".join(f"{k} {n}" for k, n in counts.items()))
    text = "\n".join(lines + tally) + "\n"
    os.makedirs(EVIDENCE, exist_ok=True)
    with open(os.path.join(EVIDENCE, "ts_isolation.md"), "w", encoding="utf-8") as f:
        f.write("# C1/C2 component isolation (version sweep, 3 replays per group)\n\n" + text)
    return text


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="C1/C2 component isolation through the version sweep.")
    ap.add_argument("command", choices=("install", "run", "job", "summarize"))
    ap.add_argument("--tag", default="")
    ap.add_argument("--gid", default="")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--replays", type=int, default=3)
    ap.add_argument("--doc", action="store_true", help="summarize: also refresh the table in plan/bug_evidence.md")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "install":
        return 1 if install() else 0
    if args.command == "run":
        return run(args.workers, args.replays)
    if args.command == "job":
        return job(args.tag, args.gid, args.replays)
    text = summarize()
    print(text)
    if args.doc and not update_doc(text):
        logger.error("no table markers in %s", os.path.relpath(DOC, REPO))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
