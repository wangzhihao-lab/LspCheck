"""Pilot of the r4_edits and r6_crossimpl oracles: each job runs one oracle once on one
prepared corpus project (or on a small synthetic fixture: the support probe, whose
files contain quick-fixable diagnostics, unsorted imports and unformatted code; or with
only the seeded quick fixes of R4: the mutation jobs), then replays every candidate
REPLAYS times from fresh sessions. Jobs run on a pool of
--parallel workers; each job keeps one server session at a time. Results merge into
data/lsptest/pilot/r4_r6.json (per job) and the report data/lsptest/pilot/r4_r6.md is
rebuilt from that file, with the candidate classification of pilot_r4_r6_review.py.

Run line: python3 scripts/lsptest/pilot_r4_r6.py [--jobs all|probe|corpus|mutation|name,...] [--replays 3] [--parallel 2] [--report-only]
"""

from __future__ import annotations

import argparse
import dataclasses
import glob
import json
import logging
import os
import random
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from oracles import r4_edits, r6_crossimpl  # noqa: E402,F401  (register the two oracles; others are not loaded)
from oracles.base import ORACLES, OracleContext  # noqa: E402
from oracles.r6_intended import SOURCE, check_source  # noqa: E402
from ops import read_text  # noqa: E402
from pilot_r4_r6_review import write_report  # noqa: E402
from targets import TargetConfig, file_targets, source_files, targets_to_json  # noqa: E402

logger = logging.getLogger("pilot_r4_r6")
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CORPUS = os.path.join(REPO, "temp", "corpus")
WORK = os.path.join(REPO, "temp", "lsptest_runs", "pilot-r4r6")
OUT_JSON = os.path.join(REPO, "data", "lsptest", "pilot", "r4_r6.json")


@dataclass(frozen=True)
class Job:
    name: str
    oracle: str
    kind: str
    version: str
    project: str  # corpus directory prefix "<owner>__<repo>@", or "fixture:<name>"
    language: str
    max_cases: int = 12
    files: int = 3
    positions: int = 12
    only_dirs: Tuple[str, ...] = ()  # target files restricted to these directories
    checks: Tuple[str, ...] = ()  # r4_edits sub-checks to run (empty: all)


VERSIONS = {"pyright": "1.1.414", "ts6": "6.0.3", "ts7": "7.0.2", "gopls": "v0.23.0", "rust-analyzer": "2026-09-21"}
CORPUS_JOBS: Tuple[Job, ...] = (
    Job("r4-pyright-flask", "r4_edits", "pyright", VERSIONS["pyright"], "pallets__flask@", "python"),
    Job("r4-ts6-zustand", "r4_edits", "ts6", VERSIONS["ts6"], "pmndrs__zustand@", "typescript"),
    Job("r4-ts7-zustand", "r4_edits", "ts7", VERSIONS["ts7"], "pmndrs__zustand@", "typescript"),
    Job("r4-gopls-cobra", "r4_edits", "gopls", VERSIONS["gopls"], "spf13__cobra@", "go"),
    Job("r4-ra-rustlings", "r4_edits", "rust-analyzer", VERSIONS["rust-analyzer"], "rust-lang__rustlings@", "rust",
        max_cases=8, only_dirs=("src/",)),  # the exercises are not part of any crate (unlinked files)
    Job("r6-ts7-zustand", "r6_crossimpl", "ts7", VERSIONS["ts7"], "pmndrs__zustand@", "typescript"),
    Job("r6-ts7-redux", "r6_crossimpl", "ts7", VERSIONS["ts7"], "reduxjs__redux@", "typescript"),
)
MUTATION_JOBS: Tuple[Job, ...] = tuple(
    dataclasses.replace(j, name=j.name.replace("r4-", "mut-"), checks=("mutation",))
    for j in CORPUS_JOBS if j.oracle == "r4_edits")
PROBE_JOBS: Tuple[Job, ...] = tuple(
    Job(f"probe-{kind}", "r4_edits", kind, VERSIONS[kind], f"fixture:{lang}", lang, max_cases=40, positions=4)
    for kind, lang in (("ts6", "typescript"), ("ts7", "typescript"), ("gopls", "go"), ("pyright", "python"),
                       ("rust-analyzer", "rust")))
FIXTURES: Dict[str, Dict[str, str]] = {
    "typescript": {
        "tsconfig.json": '{"compilerOptions": {"strict": true, "noUnusedLocals": true, "target": "es2022",'
                         ' "module": "esnext", "moduleResolution": "bundler"}, "include": ["src"]}\n',
        "src/util.ts": "export function helper(n: number): number { return n + 1; }\nexport const VALUE = 3;\n"
                       "export const unusedThing = 4;\nexport function otherHelper(s: string): string { return s; }\n",
        "src/main.ts": 'import { unusedThing, VALUE, helper } from "./util";\n\nconst value = 1;\nconsole.log(valeu);\n'
                       "const total = helpr(VALUE) ;\nfunction   badlyFormatted( a:number ){return a*2}\n"
                       'console.log(otherHelper("x"));\nexport { total, badlyFormatted };\n',
    },
    "go": {
        "go.mod": "module example.com/fix\n\ngo 1.21\n",
        "main.go": 'package main\n\nimport (\n\t"os"\n\t"fmt"\n)\n\nfunc main() {\n\tx :=  1\n'
                   '\tfmt.Println(strings.ToUpper("a"))\n}\n',
    },
    "python": {
        "app.py": "import sys\nimport os\nfrom typing import Optional\n\n\ndef f(x: int = None) -> int:\n"
                  "    return len(os.sep) + x\n\n\nprint(f(), sys.argv, undefined_name)\n",
    },
    "rust": {
        "Cargo.toml": '[package]\nname = "rsfix"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n',
        "src/main.rs": "mod missing_module;\n\nstruct Point {\n    x: i32,\n    y: i32,\n}\n\nfn MakeValue() -> i32 {\n"
                       "    return 3;\n}\n\nfn main() {\n    let p = Point { x: 1 };\n    let o: Option<i32> = 5;\n"
                       "    let mut v: Vec<i32> = Vec::new();\n"
                       "    println!(\"{} {:?} {}\", p.x, o, v.len() + MakeValue() as usize);\n}\n",
    },
}


# ------------------------------------------------------------------ projects and targets
def project_dir(job: Job) -> str:
    if job.project.startswith("fixture:"):
        root = os.path.join(WORK, "fixtures", job.project.split(":", 1)[1])
        if not os.path.isdir(root):
            for rel, text in FIXTURES[job.language].items():
                path = os.path.join(root, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
        return root
    found = sorted(glob.glob(os.path.join(CORPUS, job.project + "*")))
    if not found:
        raise FileNotFoundError(f"{job.project}* not prepared under {CORPUS}")
    return found[0]


def pick_targets(root: str, job: Job, seed: int = 1) -> tuple:
    """choose_targets (seeded) restricted to job.only_dirs; fixtures take every source file."""
    cfg = TargetConfig(seed=seed, max_files=job.files, max_positions_per_file=job.positions)
    files = [f for f in source_files(root, job.language, cfg) if not job.only_dirs or f.startswith(job.only_dirs)]
    random.Random(f"files:{seed}:{job.language}").shuffle(files)
    need = 1 if job.project.startswith("fixture:") else min(cfg.min_identifiers, cfg.max_positions_per_file)
    chosen = []
    for rel in files:
        if len(chosen) >= job.files:
            break
        ft = file_targets(rel, read_text(os.path.join(root, rel)), job.language, seed, job.positions)
        if len(ft.positions) >= need:
            chosen.append(ft)
    return tuple(sorted(chosen, key=lambda f: f.path))


# ------------------------------------------------------------------ one job
def run_job(job: Job, replays: int) -> Dict[str, Any]:
    t0 = time.monotonic()
    root = project_dir(job)
    targets = pick_targets(root, job)
    ctx = OracleContext(f"pilot-{job.name}", job.kind, job.version, os.path.basename(root), root, job.language, 1,
                        targets, max_cases=job.max_cases, work_dir=os.path.join(WORK, job.name))
    oracle = ORACLES[job.oracle]
    if job.checks:  # a private instance, so that the registered oracle keeps all sub-checks
        oracle = type(oracle)()
        oracle.cfg = dataclasses.replace(oracle.cfg, checks=job.checks)  # type: ignore[attr-defined]
    logger.info("%s: %s on %s (%d files)", job.name, job.oracle, ctx.server, len(targets))
    res = oracle.run(ctx)
    out = {"job": job.name, "oracle": job.oracle, "server": ctx.server, "project": ctx.project,
           "fixture": job.project.startswith("fixture:"), "checks": list(job.checks), "targets": targets_to_json(targets),
           "result": {k: v for k, v in res.to_json().items() if k != "candidates"}, "candidates": []}
    replay_sessions = 0
    for v in res.candidates:
        runs = []
        for i in range(replays):
            o = oracle.replay(ctx, v)
            runs.append({"settled": o.settled, "control_stable": o.control_stable, "reproduced": o.reproduced,
                         "seconds": o.seconds, "observed_actual": _short(o.observed.actual) if o.observed else None})
            logger.info("%s: replay %d/%d of %s -> %s", job.name, i + 1, replays, v.signature, runs[-1])
        replay_sessions += replays * (4 if job.oracle == "r6_crossimpl" else 3)
        ok = sum(1 for r in runs if r["settled"] and r["reproduced"] and r["control_stable"])
        out["candidates"].append({"violation": json.loads(v.to_json()), "replays": runs,
                                  "reproduced": f"{sum(1 for r in runs if r['reproduced'])}/{replays}",
                                  "confirmed": f"{ok}/{replays}"})
    out["replay_sessions_approx"] = replay_sessions
    out["seconds_total"] = round(time.monotonic() - t0, 1)
    return out


def _short(x: Any, limit: int = 400) -> Any:
    s = json.dumps(x, ensure_ascii=False, default=str)
    return x if len(s) <= limit else s[:limit] + "..."


# ------------------------------------------------------------------ main
def select(spec: str) -> List[Job]:
    every = list(CORPUS_JOBS) + list(PROBE_JOBS) + list(MUTATION_JOBS)
    groups = {"all": every, "probe": list(PROBE_JOBS), "corpus": list(CORPUS_JOBS), "mutation": list(MUTATION_JOBS)}
    if spec in groups:
        return groups[spec]
    by_name = {j.name: j for j in every}
    return [by_name[n] for n in spec.split(",") if n in by_name]  # in the order given (longest first balances)


def load(path: str) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": {}}


def main() -> int:
    ap = argparse.ArgumentParser(description="Pilot of r4_edits and r6_crossimpl (see the module docstring).")
    ap.add_argument("--jobs", default="all")
    ap.add_argument("--replays", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--keep-work", action="store_true")
    ap.add_argument("--check-source", action="store_true", help="re-fetch the typescript-go CHANGES.md once (bounded)")
    args = ap.parse_args()
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    if not args.report_only:
        os.makedirs(WORK, exist_ok=True)
        handlers.append(logging.FileHandler(os.path.join(WORK, "pilot.log")))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", handlers=handlers)
    data = load(args.out)
    if not args.report_only:
        jobs = select(args.jobs)
        if any(j.oracle == "r6_crossimpl" for j in jobs):
            check = check_source(timeout=30.0) if args.check_source else {"status": "not re-fetched (rules written from the fetch above)"}
            data["intended_source"] = dict(SOURCE, check=check)
        with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
            futures = {pool.submit(run_job, j, args.replays): j for j in jobs}
            for fut in as_completed(futures):
                try:
                    out = fut.result()
                except Exception as exc:  # noqa: BLE001  (one failing job must not lose the others' results)
                    logger.exception("job %s failed", futures[fut].name)
                    data.setdefault("failed_jobs", {})[futures[fut].name] = f"{type(exc).__name__}: {exc}"[:300]
                    continue
                data["jobs"][out["job"]] = out
                data.update(generated=time.strftime("%Y-%m-%d %H:%M"), replays_per_candidate=args.replays)
                os.makedirs(os.path.dirname(args.out), exist_ok=True)
                with open(args.out, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1, default=str)
                print(f"{out['job']:22} cases={out['result']['cases']} candidates={len(out['candidates'])} "
                      f"confirmed={[c['confirmed'] for c in out['candidates']]} s={out['seconds_total']}")
    write_report(data, args.out, os.path.splitext(args.out)[0] + ".md")
    if not args.keep_work and not args.report_only:
        shutil.rmtree(WORK, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
