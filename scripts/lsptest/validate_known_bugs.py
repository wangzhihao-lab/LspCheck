"""Known-bug validation of the R1 oracle (plan/tool_design_v1.md section 9.2), and the R1 pilot.

Each benchmark case becomes a project built from its historical case files only (pyright
#8946: the issue source as repro.py; JDT LS #3155: the case's FILES), with the settings named
in the issue in OracleContext.extra_settings (#3155: autobuild off). The generic R1 oracle
runs with fixed seeds and budget on the pre-fix and the post-fix build; candidates are
confirmed with flake.confirm (3/3); then one violation per history among the signatures
confirmed on the pre-fix build only is reduced and re-confirmed (reduce.reduce_and_confirm).
Verdicts: strict (flag pre-fix, silent post-fix) and the benchmark criterion (a signature
confirmed pre-fix only). --pilot runs the same pipeline on one prepared corpus project per
first-batch server and reduces every confirmed history.

Outputs: data/lsptest/validation/known_bugs.{json,md}; --pilot: data/lsptest/pilot/r1.json.
Run line: python3 scripts/lsptest/validate_known_bugs.py [--cases pyright_8946,jdtls_3155] [--pilot [--only ts7]]
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import logging
import os
import random
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import flake  # noqa: E402
import oracles.r1_history  # noqa: E402,F401  (registers r1_history; other oracle modules are not needed)
from driver import REPO, RUNS_DIR, SESSION_SETTINGS  # noqa: E402
from histories import FAMILY_ORDER  # noqa: E402
from history_sites import source_paths  # noqa: E402
from model import Op, QueryKey, Violation  # noqa: E402
from oracles.base import ORACLES, OracleContext, case_of, shape_of  # noqa: E402
from ops import LineIndex, deep_merge, read_text, write_text  # noqa: E402
from reduce import ReduceConfig, reduce_and_confirm  # noqa: E402
from targets import FileTargets, TargetConfig, choose_targets, identifiers  # noqa: E402

logger = logging.getLogger("validate_known_bugs")
CASES_DIR = os.path.join(REPO, "scripts", "lsp_repro", "cases")
WORK = os.path.join(RUNS_DIR, "r1_validation")
OUT_JSON = os.path.join(REPO, "data", "lsptest", "validation", "known_bugs.json")
PILOT_JSON = os.path.join(REPO, "data", "lsptest", "pilot", "r1.json")
GENERATOR = f"{FAMILY_ORDER[0]}-{FAMILY_ORDER[-1]}"
GENERATOR_CHANGE = (
    "After run 1 (generator H1-H8) one family was added, H9 \"edit inside a workspace window\": a workspace change W "
    "(configuration-file variant; depended-on file edited on disk or in the editor, or a file renamed) is kept while "
    "every open target that W does not touch is changed and restored, then W is reverted. Motivation: edits made in "
    "a changed workspace are a bug class of their own (configuration and dependency-edit subtypes in the benchmark "
    "mining); run 1 missed JDT LS #3155 for want of such a history, and the ts6 pilot artifact had the same shape. "
    "Seeds, the budget of 16 histories per seed, and confirmation are unchanged; with nine families the seeded order "
    "changes, so run 2 executes different histories. Run 2 reduces only violations whose signature is confirmed on "
    "the pre-fix build alone (run 1 reduced every confirmed history). The R1 tool is frozen after this change.")
JAVA_KEYWORDS = frozenset((
    "abstract assert boolean break byte case catch char class const continue default do double else enum extends final "
    "finally float for goto if implements import instanceof int interface long native new package private protected "
    "public return short static strictfp super switch synchronized this throw throws transient try void volatile while "
    "var record yield sealed permits true false null").split())


@dataclass(frozen=True)
class KnownBug:
    case: str  # module under scripts/lsp_repro/cases (PRE, POST, ISSUE, TITLE, FIX_COMMIT; FILES or SRC)
    kind: str
    language: str
    seeds: Tuple[int, ...]
    max_cases: int
    reduce: ReduceConfig
    settings_attr: str = ""  # module attribute holding the project settings named in the issue
    timing: str = "settled"


KNOWN_BUGS: Dict[str, KnownBug] = {
    "pyright_8946": KnownBug("pyright_8946", "pyright", "python", (1, 2, 3, 4, 5), 16, ReduceConfig(64, 3600.0)),
    "jdtls_3155": KnownBug("jdtls_3155", "jdtls", "java", (1, 2, 3), 16, ReduceConfig(24, 5400.0), "SETTINGS_AUTOBUILD_OFF"),
}


@dataclass(frozen=True)
class PilotRun:
    kind: str
    version: str
    project: str  # temp/corpus/<owner>__<repo>@<sha12>
    language: str
    timing: str = "settled"
    seed: int = 2  # seed 1 picks only rustlings exercise files, which belong to no crate
    max_cases: int = 6
    reduce: ReduceConfig = ReduceConfig(32, 3600.0)


PILOT: Tuple[PilotRun, ...] = (
    PilotRun("pyright", "1.1.414", "pallets__flask@d73fa1cdcbd8", "python"),
    PilotRun("pyright", "1.1.414", "pallets__flask@d73fa1cdcbd8", "python", timing="race0"),
    PilotRun("ts6", "6.0.3", "pmndrs__zustand@b57db4f86ef1", "typescript"),
    PilotRun("ts7", "7.0.2", "pmndrs__zustand@b57db4f86ef1", "typescript"),
    PilotRun("gopls", "v0.23.0", "spf13__cobra@adbc8813901b", "go"),
    PilotRun("rust-analyzer", "2026-09-21", "rust-lang__rustlings@a650509c789d", "rust", reduce=ReduceConfig(12, 3600.0)),
)


# ------------------------------------------------------------ projects and targets
def load_case(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"case_{name}", os.path.join(CASES_DIR, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def build_project(mod: Any, dest: str) -> str:
    """The case's historical files only: FILES when the case has several, else its SRC as repro.<ext>."""
    shutil.rmtree(dest, ignore_errors=True)
    files = dict(getattr(mod, "FILES", None) or {f"repro.{'py' if mod.SERVER == 'pyright' else 'java'}": mod.SRC})
    for rel, text in files.items():
        write_text(os.path.join(dest, rel), text)
    return dest


def java_targets(root: str, seed: int, max_files: int = 3, max_positions: int = 12) -> Tuple[FileTargets, ...]:
    """targets.choose_targets for Java: C-family tokenizer, Java keywords excluded, same seeding."""
    files = source_paths(root, "java")
    random.Random(f"files:{seed}:java").shuffle(files)
    out = []
    for rel in files[:max_files]:
        text = read_text(os.path.join(root, rel))
        toks = [t for t in identifiers(text, "typescript") if t.text not in JAVA_KEYWORDS]
        picked = sorted(random.Random(f"positions:{seed}:{rel}").sample(range(len(toks)), min(max_positions, len(toks))))
        idx, chosen = LineIndex(text), [toks[k] for k in picked]
        out.append(FileTargets(rel, tuple(idx.position(t.start + (t.end - t.start) // 2) for t in chosen),
                               tuple(idx.position(t.end) for t in chosen), tuple(t.text for t in chosen)))
    return tuple(sorted(out, key=lambda f: f.path))


def targets_for(root: str, language: str, seed: int) -> Tuple[FileTargets, ...]:
    return java_targets(root, seed) if language == "java" else choose_targets(root, language, TargetConfig(seed=seed))


# ------------------------------------------------------------ pipeline: run, confirm, reduce
def short(x: Any, limit: int = 400) -> str:
    s = json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + "..."


def compact(v: Violation) -> Dict[str, Any]:
    c = case_of(v)
    return {"signature": v.signature, "key": dataclasses.asdict(v.key), "shape": shape_of(v), "family": c.get("family"),
            "history_index": c.get("history_index"), "chain_step": c.get("chain_step"), "note": c.get("note", "")[:300],
            "reproduced": v.reproduced, "ops": len(v.ops), "expected": short(v.expected), "actual": short(v.actual)}


def pipeline(ctx: OracleContext, reduce_cfg: ReduceConfig, skip: Set[str], do_reduce: bool = True) -> Dict[str, Any]:
    """R1 run; confirm candidates (at most 2 per signature, signatures in `skip` excluded); reduce
    and re-confirm one confirmed violation per history (its other signatures share the ops)."""
    oracle = ORACLES["r1_history"]
    t0 = time.monotonic()
    res = oracle.run(ctx)
    todo = [v for v in res.candidates if v.signature not in skip]
    done, stats = flake.confirm_all(oracle, ctx, todo, flake.FlakeConfig(per_signature=2))
    confirmed = [x for x in done if flake.is_confirmed(x)]
    reductions = reduce_each_history(ctx, confirmed, reduce_cfg) if do_reduce else []
    run = {k: val for k, val in res.to_json().items() if k != "candidates"}
    return {"run_id": ctx.run_id, "seed": ctx.seed, "timing": ctx.timing, "targets": [t.path for t in ctx.targets],
            "run": run, "candidates": [compact(v) for v in res.candidates], "flake": stats,
            "confirmations": [dict(compact(v), detail_note=json.loads(v.detail).get("note", "")) for v in done],
            "confirmed": [json.loads(v.to_json()) for v in confirmed],
            "reductions": reductions, "seconds": round(time.monotonic() - t0, 1)}


def reduce_each_history(ctx: OracleContext, confirmed: Sequence[Violation], cfg: ReduceConfig,
                        only: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """Reduce and re-confirm one confirmed violation per history (its other signatures share the ops),
    optionally only for the signatures in `only`."""
    out, seen = [], set()
    for v in confirmed:
        case = (case_of(v).get("history_index"), case_of(v).get("chain_step"))
        if case not in seen and (only is None or v.signature in only):
            seen.add(case)
            v2, rres, rconf = reduce_and_confirm(ORACLES["r1_history"], ctx, v, cfg)
            out.append({"signature": v.signature, "family": case_of(v).get("family"), "reduction": rres.to_json(),
                        "reduced_confirmed": rconf.reproduced, "violation": json.loads(v2.to_json())})
    return out


def violation_from_json(d: Dict[str, Any]) -> Violation:
    return Violation(**dict(d, key=QueryKey(**d["key"]), ops=[Op.from_json(o) for o in d["ops"]],
                            reduced_ops=[Op.from_json(o) for o in d.get("reduced_ops") or []]))


def context(run_id: str, kind: str, version: str, project: str, root: str, language: str, seed: int, timing: str,
            max_cases: int, extra: Optional[Dict[str, Any]] = None) -> OracleContext:
    return OracleContext(run_id, kind, version, project, root, language, seed, targets_for(root, language, seed),
                         timing=timing, extra_settings=extra, max_cases=max_cases,
                         work_dir=os.path.join(WORK, f"{run_id}-work"))


# ------------------------------------------------------------ known bugs
def validate(bug: KnownBug, do_reduce: bool = True,
             progress: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """Both builds, every seed; `progress` receives the partial case after each seed."""
    mod = load_case(bug.case)
    root = build_project(mod, os.path.join(WORK, bug.case, "project"))
    issue_settings = getattr(mod, bug.settings_attr, None) if bug.settings_attr else None
    extra = deep_merge(SESSION_SETTINGS.get(bug.kind, {}), issue_settings) if issue_settings else None
    out: Dict[str, Any] = {"case": bug.case, "issue": mod.ISSUE, "title": mod.TITLE, "fix": mod.FIX_COMMIT,
                           "project_files": sorted(os.path.relpath(os.path.join(d, n), root)
                                                   for d, _, names in os.walk(root) for n in names),
                           "extra_settings": extra, "seeds": list(bug.seeds), "max_cases": bug.max_cases,
                           "timing": bug.timing, "reduce_budget": dataclasses.asdict(bug.reduce), "builds": {}}
    for phase, version in (("pre", mod.PRE), ("post", mod.POST)):
        confirmed: Set[str] = set()
        runs = []
        for seed in bug.seeds:
            ctx = context(f"kb-{bug.case}-{version}-s{seed}", bug.kind, version, bug.case, root, bug.language, seed,
                          bug.timing, bug.max_cases, extra)
            logger.info("%s %s seed %d: %d target file(s)", bug.case, version, seed, len(ctx.targets))
            r = pipeline(ctx, bug.reduce, confirmed, False)  # reductions follow once both builds are confirmed
            confirmed |= {c["signature"] for c in r["confirmed"]}
            runs.append(r)
            if progress is not None:
                progress(dict(out, partial=f"{phase} {version} seed {seed}", builds=dict(out["builds"], **{phase: {
                    "version": version, "runs": runs, "confirmed_signatures": sorted(confirmed)}})))
        out["builds"][phase] = {"version": version, "runs": runs, "confirmed_signatures": sorted(confirmed),
                                "histories": sum(r["run"]["cases"] for r in runs),
                                "sessions": sum(r["run"]["sessions"] for r in runs),
                                "candidates": sum(len(r["candidates"]) for r in runs),
                                "families": sorted({c["family"] for r in runs for c in r["confirmations"]
                                                    if c["reproduced"] == "3/3"})}
    out.update(criterion(out))
    pre = out["builds"]["pre"]
    for r in pre["runs"] if do_reduce else []:  # reduce what the benchmark counts: confirmed pre-fix only
        ctx = context(r["run_id"], bug.kind, pre["version"], bug.case, root, bug.language, r["seed"], bug.timing,
                      bug.max_cases, extra)
        r["reductions"] = reduce_each_history(ctx, [violation_from_json(d) for d in r["confirmed"]], bug.reduce,
                                              set(out["detected_signatures"]))
    return out


def criterion(c: Dict[str, Any]) -> Dict[str, Any]:
    """Strict verdict (flag pre-fix, silent post-fix) and the benchmark criterion: detected when a
    signature is confirmed on the pre-fix build and not on the post-fix build."""
    pre, post = (set(c["builds"][p]["confirmed_signatures"]) for p in ("pre", "post"))
    return {"pass": bool(pre) and not post, "detected": bool(pre - post), "detected_signatures": sorted(pre - post),
            "shared_signatures": sorted(pre & post), "post_only_signatures": sorted(post - pre)}


def summary(c: Dict[str, Any]) -> Dict[str, Any]:
    """A case reduced to its numbers and notes (kept in previous_runs)."""
    keep = ("version", "histories", "sessions", "candidates", "confirmed_signatures", "families")
    return dict({k: c[k] for k in ("case", "issue", "seeds", "max_cases") if k in c}, **criterion(c),
                builds={p: {k: b.get(k) for k in keep} for p, b in c["builds"].items()},
                **{k: c[k] for k in ("analysis", "earlier_runs", "sanity_check") if k in c})


def sigs(xs: Sequence[str]) -> str:
    return ", ".join(x.replace("|", "\\|") for x in xs) or "-"


def ops_text(ops: Sequence[Dict[str, Any]]) -> str:
    def one(o: Dict[str, Any]) -> str:
        extra = {"change": f" {o.get('start')}-{o.get('end')} {json.dumps(o.get('text', ''))}",
                 "fs_write": f" ({len(o.get('text', ''))} chars)", "request": f" {o.get('start')} {o.get('text', '')}",
                 "set_config": f" {json.dumps(o.get('settings'))}", "fs_rename": f" -> {o.get('new_path', '')}"}
        return f"{o['kind']} {o.get('path', '')}".strip() + extra.get(o["kind"], "")
    return "; ".join(one(o) for o in ops)


def write_markdown(report: Dict[str, Any], path: str) -> None:
    lines = [f"# Known-bug validation of R1 ({report['date']})", "",
             f"Generic R1 oracle (histories {report.get('generator', GENERATOR)}, no case-specific steps) on projects built "
             "from the historical case files only; candidates confirmed 3/3 (fresh baseline, fresh control, fresh history "
             "session per replay); one confirmed violation per history reduced by ddmin and re-confirmed 3/3 (from run 2 "
             "on, only for signatures confirmed on the pre-fix build alone).", "",
             "| case | build | seeds x budget | histories | sessions | candidates | confirmed 3/3 | family | reduced ops | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for c in report["cases"]:
        for phase in ("pre", "post"):
            b = c["builds"][phase]
            red = [r for run in b["runs"] for r in run["reductions"] if r["reduced_confirmed"].startswith("3/")]
            red_s = "<br>".join(f"`{ops_text(r['reduction']['ops'])}`" for r in red[:2]) or "-"
            verdict = ("flagged" if b["confirmed_signatures"] else "silent") + (
                f" ({'PASS' if c['pass'] else 'FAIL'})" if phase == "post" else "")
            lines.append(f"| {c['case']} | {phase} {b['version']} | {len(c['seeds'])} x {c['max_cases']} | {b['histories']} | "
                         f"{b['sessions']} | {b['candidates']} | {len(b['confirmed_signatures'])} "
                         f"{sigs(b['confirmed_signatures']).strip('-')} | {', '.join(b['families']) or '-'} | {red_s} | {verdict} |")
    lines += ["", "Benchmark criterion: a case is detected when a signature is confirmed on the pre-fix build and not on "
              "the post-fix build; signatures confirmed on both builds are not the bug but findings of their own.", "",
              "| case | detected | confirmed pre-fix only | confirmed on both builds | confirmed post-fix only |", "|---|---|---|---|---|"]
    for c in report["cases"]:
        k = criterion(c)
        lines.append(f"| {c['case']} | {'yes' if k['detected'] else 'no'} | {sigs(k['detected_signatures'])} | "
                     f"{sigs(k['shared_signatures'])} | {sigs(k['post_only_signatures'])} |")
    lines += previous_runs_section(report)
    for c in report["cases"]:
        lines += ["", f"## {c['case']} ({c['issue']}: {c['title']})", "",
                  f"- fix: {c['fix']}; project files: {', '.join(c['project_files'])}; "
                  f"extra settings: `{json.dumps(c['extra_settings'])}`; timing {c['timing']}",
                  f"- verdict: strict {'PASS' if c['pass'] else 'FAIL'}; benchmark criterion: "
                  f"{'detected' if criterion(c)['detected'] else 'not detected'}. " + c.get("analysis", "")]
        lines += [f"- {ph} seed {run['seed']}: `{v['signature']}` {v['reproduced']} at {v['key']['method']} "
                  f"{v['key']['path']}:{v['key']['line']}:{v['key']['character']} (family {v['family']}: {v['note'][:160]}); "
                  f"expected `{v['expected'][:160]}`, actual `{v['actual'][:160]}`"
                  for ph in ("pre", "post") for run in c["builds"][ph]["runs"] for v in run["confirmations"]]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def previous_runs_section(report: Dict[str, Any]) -> List[str]:
    """Run 1 (archived in previous_runs) next to the current run."""
    prev = report.get("previous_runs", {}).get("run1")
    if not prev:
        return []
    now = {c["case"]: c for c in report["cases"]}
    cell = lambda b: f"{b['histories']} / {b['candidates']} / {len(b['confirmed_signatures'])}"  # noqa: E731
    verdict = lambda k: f"strict {'PASS' if k['pass'] else 'FAIL'}; detected: {'yes' if k['detected'] else 'no'}"  # noqa: E731
    lines = ["", "## Generator change after validation run 1", "", GENERATOR_CHANGE, "",
             f"| case | build | run 1 ({prev['generator']}): histories / candidates / confirmed | run 2 "
             f"({report.get('generator', GENERATOR)}): histories / candidates / confirmed |", "|---|---|---|---|"]
    for p in prev["cases"]:
        c = now.get(p["case"])
        for phase in ("pre", "post"):
            lines.append(f"| {p['case']} | {phase} {p['builds'][phase]['version']} | {cell(p['builds'][phase])} | "
                         f"{cell(c['builds'][phase]) if c else 'not rerun'} |")
        lines.append(f"| {p['case']} | verdict | {verdict(p)} | {verdict(criterion(c)) if c else '-'} |")
    lines += ["", f"Run 1 ({prev['date']}) notes:"] + [f"- {p['case']}: {p.get('analysis', '')}" for p in prev["cases"]]
    return lines


# ------------------------------------------------------------ pilot
def pilot(runs: Sequence[PilotRun], out_path: str, do_reduce: bool = True) -> Dict[str, Any]:
    report: Dict[str, Any] = {"date": time.strftime("%Y-%m-%d %H:%M"), "runs": []}
    for p in runs:
        root = os.path.join(REPO, "temp", "corpus", p.project)
        ctx = context(f"pilot-{p.kind}-{p.timing}-s{p.seed}", p.kind, p.version, p.project.replace("__", "/"), root,
                      p.language, p.seed, p.timing, p.max_cases)
        logger.info("pilot %s %s on %s", p.kind, p.timing, p.project)
        r = pipeline(ctx, p.reduce, set(), do_reduce)
        report["runs"].append(dict(r, server=p.kind, version=p.version, project=p.project, max_cases=p.max_cases))
        save_json(report, out_path)
    return report


def save_json(obj: Any, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)


def main() -> int:
    ap = argparse.ArgumentParser(description="Known-bug validation of R1 (design 9.2), or the R1 pilot.")
    ap.add_argument("--cases", default=",".join(KNOWN_BUGS))
    ap.add_argument("--pilot", action="store_true", help="run the pilot on prepared corpus projects instead")
    ap.add_argument("--only", default="", help="pilot: comma-separated server kinds (optionally kind:timing)")
    ap.add_argument("--no-reduce", action="store_true")
    ap.add_argument("--archive", default="", help="first move the current results into previous_runs[ARCHIVE]")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.pilot:
        only = {x for x in args.only.split(",") if x}
        runs = [p for p in PILOT if not only or p.kind in only or f"{p.kind}:{p.timing}" in only]
        for r in pilot(runs, args.out or PILOT_JSON, not args.no_reduce)["runs"]:
            print(f"{r['server']:14} {r['timing']:8} cases={r['run']['cases']} candidates={len(r['candidates'])} "
                  f"confirmed={len(r['confirmed'])}")
        return 0
    out_json = args.out or OUT_JSON
    report: Dict[str, Any] = {"date": time.strftime("%Y-%m-%d %H:%M"), "generator": GENERATOR, "cases": [],
                              "previous_runs": {}}
    if os.path.exists(out_json):  # keep earlier runs, and the other cases' results when re-running one case
        with open(out_json, "r", encoding="utf-8") as f:
            old = json.load(f)
        report["previous_runs"] = old.get("previous_runs", {})
        if args.archive:
            report["previous_runs"][args.archive] = {"date": old.get("date"), "generator": old.get("generator", "H1-H8"),
                                                     "cases": [summary(c) for c in old.get("cases", [])]}
        else:
            report["cases"] = [c for c in old.get("cases", []) if c["case"] not in args.cases.split(",")]
    for name in args.cases.split(","):
        done = list(report["cases"])
        report["cases"] = done + [validate(KNOWN_BUGS[name], not args.no_reduce,
                                           lambda partial: save_json(dict(report, cases=done + [partial]), out_json))]
        report["cases"].sort(key=lambda c: c["case"])
        save_json(report, out_json)
        write_markdown(report, os.path.splitext(out_json)[0] + ".md")
    for c, k in ((c, criterion(c)) for c in report["cases"]):
        print(f"{c['case']:14} strict {'PASS' if k['pass'] else 'FAIL'}; detected {'yes' if k['detected'] else 'no'} "
              f"({len(k['detected_signatures'])} pre-only, {len(k['shared_signatures'])} on both builds, "
              f"{len(k['post_only_signatures'])} post-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
