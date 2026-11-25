"""Campaign runner (plan/tool_design_v1.md section 11.1).

Plans the runs of a campaign config (campaign_config.py, campaign_plan.py), skips those already in
results.jsonl (resumable; --retry-failed also reruns failed, timed-out and incomplete runs),
and executes the rest on a pool of worker processes (campaign_run.py), at most `concurrency`
at a time, each in its own process group: a run that exceeds the per-run hard timeout is
killed with its language servers, recorded with its error and the counters it had written,
and its scratch and session directories are removed. server_limits caps the concurrent runs
of one server kind (memory: a rust-analyzer session can take 3.5 GB); one scheduler per
campaign (campaign.lock). The scheduler keeps the signature-cap counts (campaign_costs.py) in
signature_counts.json. New runs stop starting once the wall-clock budget (summed over
invocations) is spent. Outputs in data/lsptest/runs/<id>/:
config.json (config, server builds, corpus commits, eligibility, plan, invocations),
results.jsonl, violations.jsonl, violations/<vid>/, candidates/, worker_logs/, progress.log.
--dry-run: one run per (oracle, server) on the smallest eligible project, max_cases=2, or the
full plan of the config's dry_run.projects, written to runs/<id>-dryrun (a config whose id ends in
"dryrun" keeps its id).

Run line: python3 scripts/lsptest/campaign.py data/lsptest/campaigns/<id>.json [--dry-run] [--concurrency N] [--retry-failed] [--limit N] [--only oracle=r1_history,server=ts7] [--plan] [--force]
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import oracles  # noqa: E402
from campaign_config import CampaignConfig, ConfigError, RunSpec, dry_run_config, load_config  # noqa: E402
from campaign_costs import COUNTS_FILE, CapConfig, confirmed_runs, write_counts  # noqa: E402
from campaign_plan import Pair, dry_run_plan, eligible_pairs, plan_runs  # noqa: E402
from campaign_store import (REPO, CampaignPaths, append_jsonl, build_case_project, case_sha, completed_runs,  # noqa: E402
                            latest_rows, machine_info, paths_for, read_jsonl, rel, server_build, sweep_session_dirs,
                            write_json)
from driver import kill_pids, pid_alive, process_tree  # noqa: E402

logger = logging.getLogger("campaign")
RETRY_STATUSES = frozenset({"failed", "timeout", "incomplete"})
Launcher = Callable[[str, str], subprocess.Popen]


def launch_worker(spec_path: str, log_path: str) -> subprocess.Popen:
    """campaign_run.py in a new session (process group) with its output in the worker log."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "ab") as log:
        return subprocess.Popen([sys.executable, os.path.join(HERE, "campaign_run.py"), spec_path], cwd=REPO,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)


def kill_group(proc: subprocess.Popen, grace: float = 5.0) -> None:
    """SIGTERM, then SIGKILL, the worker's process group and every descendant seen before."""
    pids = process_tree(proc.pid)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, sig)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=grace)
    kill_pids(pids, grace=1.0)


def reap_group(pgid: int) -> None:
    """Kill members of an exited worker's group that are still alive (a server that outlived it)."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pgid, 0)
        os.killpg(pgid, signal.SIGKILL)


def log_tail(path: str, n: int = 12) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return [ln.rstrip() for ln in f.readlines()[-n:]]
    except OSError:
        return []


@dataclass
class Active:
    spec: RunSpec
    proc: subprocess.Popen
    started: float
    started_at: str


@dataclass
class Scheduler:
    paths: CampaignPaths
    flake: Dict[str, int]
    concurrency: int
    launcher: Launcher = launch_worker
    server_limits: Dict[str, int] = field(default_factory=dict)  # kind -> most concurrent runs
    cap: CapConfig = CapConfig()
    counts: Dict[str, Set[str]] = field(default_factory=dict)  # cap key -> runs that confirmed it
    budget_s: float = 0.0  # 0: none
    spent_s: float = 0.0  # budget used by earlier invocations
    total: int = 0
    done: int = 0
    active: Dict[str, Active] = field(default_factory=dict)
    stopping: bool = False
    t0: float = field(default_factory=time.monotonic)
    walls: List[float] = field(default_factory=list)

    def over_budget(self) -> bool:
        return self.budget_s > 0 and self.spent_s + (time.monotonic() - self.t0) >= self.budget_s

    def launch(self, spec: RunSpec) -> None:
        scratch = self.paths.run_scratch(spec.run_id)
        shutil.rmtree(scratch, ignore_errors=True)
        for stale in glob.glob(self.paths.violation_dir(f"{spec.run_id}-v*")):
            shutil.rmtree(stale, ignore_errors=True)  # left by an attempt that was never recorded
        os.makedirs(scratch)
        spec_path = os.path.join(scratch, "spec.json")
        write_json(spec_path, {"spec": spec.to_json(), "root": self.paths.root, "scratch": self.paths.scratch,
                               "flake": self.flake, "soft_deadline_s": 0.9 * spec.run_timeout_s,
                               "cap": {"runs": self.cap.runs, "scope": self.cap.scope},
                               "counts_path": os.path.join(self.paths.root, COUNTS_FILE)})
        proc = self.launcher(spec_path, self.paths.worker_log(spec.run_id))
        self.active[spec.run_id] = Active(spec, proc, time.monotonic(), time.strftime("%Y-%m-%d %H:%M:%S"))

    def poll(self) -> None:
        for rid, a in list(self.active.items()):
            if a.proc.poll() is not None:
                self.finish(a, "")
            elif time.monotonic() - a.started > a.spec.run_timeout_s:
                kill_group(a.proc)
                self.finish(a, f"hard timeout after {a.spec.run_timeout_s:.0f}s")

    def finish(self, a: Active, killed: str) -> Dict[str, Any]:
        spec, scratch = a.spec, self.paths.run_scratch(a.spec.run_id)
        self.active.pop(spec.run_id, None)
        reap_group(a.proc.pid)
        result = self._read(os.path.join(scratch, "result.json"))
        row: Dict[str, Any] = dict(spec.to_json())
        if result is None:
            for stale in glob.glob(self.paths.violation_dir(f"{spec.run_id}-v*")):
                shutil.rmtree(stale, ignore_errors=True)  # written before the failure; no row refers to them
            partial = self._read(os.path.join(scratch, "run.json")) or {}
            tail = log_tail(self.paths.worker_log(spec.run_id))
            row.update(status="timeout" if killed else "failed", log_tail=tail, candidates=partial.pop("candidates", None),
                       error=killed or f"worker exited with code {a.proc.returncode}: {tail[-1] if tail else ''}",
                       counters=partial or None, confirmed=0, flaky=0, replayed=0)
        else:
            vrows = result.pop("violations", [])
            append_jsonl(self.paths.violations, vrows)
            self.count_confirmed(vrows)
            row.update(result)
        wall = time.monotonic() - a.started
        row.update(started_at=a.started_at, finished_at=time.strftime("%Y-%m-%d %H:%M:%S"), wall_seconds=round(wall, 1),
                   exit_code=a.proc.returncode, worker_log=rel(self.paths.worker_log(spec.run_id)))
        append_jsonl(self.paths.results, [row])
        shutil.rmtree(scratch, ignore_errors=True)
        sweep_session_dirs(spec.run_id)
        self.done, self.walls = self.done + 1, self.walls + [wall]
        self.progress(row)
        return row

    @staticmethod
    def _read(path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def progress(self, row: Dict[str, Any]) -> None:
        elapsed = time.monotonic() - self.t0
        left = self.total - self.done
        eta = (sum(self.walls) / len(self.walls)) * left / max(1, self.concurrency) if self.walls else 0.0
        line = (f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{self.done}/{self.total}] {row.get('status')} {row['run_id']} "
                f"{row['oracle']} {row['server_kind']}-{row['server_version']} {row['project']} seed {row['seed']} "
                f"{row['timing']}: {row.get('wall_seconds')}s, {row.get('candidates')} candidate(s), "
                f"{row.get('confirmed')} confirmed{'; ' + str(row.get('error'))[:200] if row.get('error') else ''}; "
                f"elapsed {elapsed / 3600:.2f}h, {len(self.active)} running, ~{eta / 3600:.1f}h left")
        logger.info("%s", line)
        with open(self.paths.progress, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def stop(self, *_: Any) -> None:
        self.stopping = True

    def count_confirmed(self, rows: Sequence[Dict[str, Any]]) -> None:
        """Add a run's confirmed violations to the cap counts and rewrite signature_counts.json."""
        for k, runs in confirmed_runs(rows, self.cap.scope).items():
            self.counts.setdefault(k, set()).update(runs)
        write_counts(os.path.join(self.paths.root, COUNTS_FILE), self.counts, self.cap)

    def next_index(self, queue: Sequence[RunSpec]) -> Optional[int]:
        """First queued run whose server kind is under its concurrency limit."""
        busy: Dict[str, int] = {}
        for a in self.active.values():
            busy[a.spec.server_kind] = busy.get(a.spec.server_kind, 0) + 1
        return next((i for i, s in enumerate(queue)
                     if busy.get(s.server_kind, 0) < self.server_limits.get(s.server_kind, self.concurrency)), None)

    def execute(self, todo: Sequence[RunSpec], poll_s: float = 1.0) -> int:
        """Run `todo`; returns how many runs finished. Interrupted runs are killed and not recorded."""
        queue, self.total = list(todo), len(todo)
        while (queue and not self.stopping) or self.active:
            while queue and len(self.active) < self.concurrency and not self.stopping:
                if self.over_budget():
                    logger.warning("wall-clock budget spent: %d run(s) not started", len(queue))
                    queue = []
                    break
                i = self.next_index(queue)
                if i is None:
                    break
                self.launch(queue.pop(i))
            if self.stopping:
                for a in list(self.active.values()):
                    kill_group(a.proc)
                    self.active.pop(a.spec.run_id, None)
                    shutil.rmtree(self.paths.run_scratch(a.spec.run_id), ignore_errors=True)
                    sweep_session_dirs(a.spec.run_id)
                break
            time.sleep(poll_s)
            self.poll()
        return self.done


# ------------------------------------------------------------------ planning and bookkeeping
def applies(name: str, kind: str) -> bool:
    return oracles.get(name).applies_to(kind)


def load_plan(cfg: CampaignConfig, dry_run: bool) -> Tuple[CampaignConfig, List[RunSpec], List[Pair], List[Dict]]:
    records: List[Dict[str, Any]] = []
    if cfg.corpus:
        with open(os.path.join(REPO, cfg.corpus), "r", encoding="utf-8") as f:
            records = json.load(f)
    pairs, excluded = eligible_pairs(cfg, records, lambda p: os.path.isdir(os.path.join(REPO, p)))
    if dry_run:
        cfg = dry_run_config(cfg)
        return cfg, dry_run_plan(cfg, pairs, applies), pairs, excluded
    return cfg, plan_runs(cfg, pairs, applies), pairs, excluded


def select(runs: Sequence[RunSpec], only: str) -> List[RunSpec]:
    """--only oracle=a|b,server=k,project=substring"""
    rules = [r.split("=", 1) for r in only.split(",") if "=" in r]
    field_of = {"oracle": lambda s: s.oracle, "server": lambda s: s.server_kind, "project": lambda s: s.project,
                "timing": lambda s: s.timing}
    out = list(runs)
    for name, want in rules:
        if name not in field_of:
            raise ConfigError(f"--only: unknown field {name!r}")
        opts = want.split("|")
        out = [s for s in out if any(o == field_of[name](s) or (name == "project" and o in s.project) for o in opts)]
    return out


def resume_conflicts(runs: Sequence[RunSpec], done: Dict[str, Dict[str, Any]]) -> List[str]:
    """Run ids recorded with different result-affecting parameters than planned now."""
    out = []
    for s in runs:
        row = done.get(s.run_id)
        if row is not None:
            old = RunSpec.from_json(row).result_affecting()
            if old != s.result_affecting():
                out.append(s.run_id)
    return out


def write_config(paths: CampaignPaths, cfg: CampaignConfig, config_path: str, runs: Sequence[RunSpec],
                 pairs: Sequence[Pair], excluded: Sequence[Dict[str, Any]], dry_run: bool) -> Dict[str, Any]:
    old = {}
    if os.path.exists(paths.config):
        with open(paths.config, "r", encoding="utf-8") as f:
            old = json.load(f)
    commits = {p.project: {"repo": p.repo, "commit": p.commit, "dir": p.project_ref, "language": p.language,
                           "size_kb": p.size_kb} for p in pairs if p.source == "corpus"}
    commits.update({p.project: {"case": p.project_ref, "case_sha256": case_sha(p.project_ref), "language": p.language}
                    for p in pairs if p.source == "case"})
    for p in (p for p in pairs if p.source == "dir"):
        entry = commits.setdefault(p.project, {"dir": p.project_ref, "language": p.language, "builds": {}})
        entry["builds"][p.phase or "build"] = p.version
    per: Dict[str, int] = {}
    for s in runs:
        per[f"{s.oracle} {s.server_kind}"] = per.get(f"{s.oracle} {s.server_kind}", 0) + 1
    doc = {"campaign": cfg.id, "config_file": rel(config_path), "dry_run": dry_run, "config": dict(cfg.raw),
           "server_builds": [server_build(k, v) for k, v in dict.fromkeys((s.server_kind, s.server_version) for s in runs)],
           "machine": machine_info(),
           "projects": dict(sorted(commits.items())),
           "eligible_pairs": [{"server": p.server_kind, "project": p.project, "forced": p.forced} for p in pairs],
           "excluded_pairs": list(excluded), "plan": {"runs": len(runs), "per_oracle_server": per},
           "invocations": list(old.get("invocations", []))}
    write_json(paths.config, doc)
    return doc


@contextlib.contextmanager
def campaign_lock(paths: CampaignPaths) -> Iterator[None]:
    """One scheduler per campaign: <root>/campaign.lock holds the pid (a stale lock is taken over)."""
    path = os.path.join(paths.root, "campaign.lock")
    os.makedirs(paths.root, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        with open(path, "r", encoding="utf-8") as f:
            pid = int(f.read().strip() or 0)
        if pid and pid_alive(pid):
            raise ConfigError(f"campaign {paths.root} is already running (pid {pid})")
        os.remove(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as f:
        f.write(str(os.getpid()))
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(path)


def record_invocation(paths: CampaignPaths, started: str, elapsed: float, finished_runs: int) -> None:
    with open(paths.config, "r", encoding="utf-8") as f:
        doc = json.load(f)
    doc.setdefault("invocations", []).append({"started": started, "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
                                              "elapsed_s": round(elapsed, 1), "runs": finished_runs})
    write_json(paths.config, doc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run an LSP oracle campaign (design section 11.1).")
    ap.add_argument("config")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--concurrency", type=int, default=0)
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="start at most N runs in this invocation")
    ap.add_argument("--only", default="", help="filter: oracle=a|b,server=k,project=substring,timing=t")
    ap.add_argument("--plan", action="store_true", help="print the plan and exit")
    ap.add_argument("--force", action="store_true", help="resume although run parameters changed")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    cfg = load_config(args.config)
    args.dry_run = args.dry_run or cfg.dry_run_only
    cfg, runs, pairs, excluded = load_plan(cfg, args.dry_run)
    runs = select(runs, args.only)
    paths = paths_for(cfg.id)
    done = completed_runs(paths.results)
    conflicts = resume_conflicts(runs, done)
    if conflicts and not args.force:
        logger.error("%d recorded run(s) differ from the plan (e.g. %s); use --force or a new id", len(conflicts),
                     conflicts[0])
        return 2
    todo = [s for s in runs if s.run_id not in done
            or (args.retry_failed and done[s.run_id].get("status") in RETRY_STATUSES)]
    todo = todo[: args.limit] if args.limit else todo
    print(f"campaign {cfg.id}: {len(runs)} planned run(s), {len(runs) - len(todo)} done or skipped, "
          f"{len(todo)} to run; {len(pairs)} eligible pair(s), {len(excluded)} excluded")
    if args.plan:
        for s in todo[:40]:
            print(f"  {s.run_id} {s.oracle:14} {s.server_kind:14} {s.project:45} seed {s.seed} {s.timing}")
        return 0
    with campaign_lock(paths):
        doc = write_config(paths, cfg, args.config, runs, pairs, excluded, args.dry_run)
        for case in sorted({s.project_ref for s in todo if s.source == "case"}):
            dest = os.path.join(paths.projects(), case)
            if not os.path.isdir(dest):
                build_case_project(case, dest)
        sched = Scheduler(paths, {"n": cfg.flake_n, "per_signature": cfg.per_signature},
                          args.concurrency or cfg.concurrency, server_limits=dict(cfg.server_limits), cap=cfg.cap,
                          counts=confirmed_runs(latest_rows(read_jsonl(paths.violations)), cfg.cap.scope),
                          budget_s=cfg.wall_clock_budget_s,
                          spent_s=sum(float(i.get("elapsed_s", 0)) for i in doc.get("invocations", [])))
        sched.count_confirmed([])
        signal.signal(signal.SIGINT, sched.stop)
        signal.signal(signal.SIGTERM, sched.stop)
        started = time.strftime("%Y-%m-%d %H:%M:%S")
        finished = sched.execute(todo)
        record_invocation(paths, started, time.monotonic() - sched.t0, finished)
        shutil.rmtree(paths.scratch, ignore_errors=True)
    rows = [r for r in read_jsonl(paths.results) if r["run_id"] in {s.run_id for s in runs}]
    print(f"campaign {cfg.id}: {finished} run(s) finished in this invocation; {len(rows)}/{len(runs)} recorded; "
          f"confirmed violations {sum(int(r.get('confirmed') or 0) for r in rows)}; "
          f"failed {sum(r.get('status') in RETRY_STATUSES for r in rows)}; results in {rel(paths.root)}")
    return 130 if sched.stopping else 0


if __name__ == "__main__":
    raise SystemExit(main())
