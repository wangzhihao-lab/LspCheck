"""One campaign run in its own process (plan/tool_design_v1.md section 11.1).

campaign.py starts this worker once per run, in a process group of its own, so that a run
that exceeds its hard timeout is killed together with its language servers. The worker
reads <scratch>/spec.json ({spec: RunSpec, root, scratch, flake: {n, per_signature},
soft_deadline_s}), builds the OracleContext (project dir, targets from targets.choose_targets
with the run's seed, extra settings, scratch = temp/lsptest_runs/<campaign>/<run_id>),
calls oracle.run(ctx), writes every candidate to candidates/<run_id>.jsonl.gz, then confirms
them with flake.confirm_all (no reduction: triage reduces one violation per group), except
candidates skipped by the cost controls (campaign_costs.py): a registered legitimate-difference
label ("labelled-legitimate") or a signature already confirmed in the cap number of runs
("capped", counts read from the campaign's signature_counts.json just before confirming); one
violations row per skipped signature, no replay. Each replayed candidate gets
violations/<vid>/repro.json (vid = <run_id>-v<k>); a confirmed one also keeps the gzipped session
logs of its last confirming replay. Replays that would start after the soft deadline are
skipped and their candidates flagged incomplete. The worker writes <scratch>/result.json;
campaign.py appends the results and violations rows.

Run line: python3 scripts/lsptest/campaign_run.py <temp/lsptest_runs/<campaign>/<run_id>/spec.json>
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from typing import Any, Dict, List, Mapping, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import flake  # noqa: E402
import oracles  # noqa: E402
from campaign_config import RunSpec  # noqa: E402
from campaign_costs import (CapConfig, Skipped, read_capped, replay_status, skip_counts,  # noqa: E402
                            split_candidates)
from campaign_store import (CampaignPaths, choose_run_targets, project_dir, rel, repro_document,  # noqa: E402
                            run_settings, violation_to_json, write_json)
from model import Violation  # noqa: E402
from oracles.base import OracleContext, OracleResult, case_of, shape_of  # noqa: E402
from replay_logs import ReplayRecorder, keep_logs  # noqa: E402

logger = logging.getLogger("campaign_run")


def build_context(spec: RunSpec, paths: CampaignPaths) -> OracleContext:
    root = project_dir(spec.source, spec.project_ref, paths.projects())
    targets = choose_run_targets(root, spec.language, spec.seed, spec.max_files, spec.max_positions_per_file,
                                 spec.max_file_bytes, spec.exclude_dirs, spec.min_identifiers)
    extra = run_settings(spec.server_kind, spec.source, spec.project_ref, spec.settings, spec.settings_attr)
    return OracleContext(spec.run_id, spec.server_kind, spec.server_version, spec.project, root, spec.language,
                         spec.seed, targets, spec.timing, spec.settle_timeout_s, spec.request_timeout_s, extra,
                         spec.max_cases, paths.run_scratch(spec.run_id))


def counters(res: OracleResult) -> Dict[str, Any]:
    d = res.to_json()
    d.pop("candidates", None)
    return d


def signature_counts(vs: List[Violation]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for v in vs:
        out[v.signature] = out.get(v.signature, 0) + 1
    return dict(sorted(out.items()))


def write_candidates(path: str, vs: List[Violation]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for v in vs:
            f.write(v.to_json() + "\n")


def violation_row(spec: RunSpec, vid: str, v: Violation, repro: str, logs: List[str], incomplete: bool,
                  status: str = "", reason: str = "", candidates: int = 1) -> Dict[str, Any]:
    return {"vid": vid, "run_id": spec.run_id, "campaign": spec.campaign, "oracle": v.oracle,
            "server": v.server, "server_kind": spec.server_kind, "server_version": spec.server_version,
            "project": spec.project, "seed": spec.seed, "timing": spec.timing, "signature": v.signature,
            "shape": shape_of(v), "key": asdict(v.key), "reproduced": v.reproduced,
            "status": status or replay_status(v.reproduced, incomplete), "reason": reason, "candidates": candidates,
            "confirmed": not status and flake.is_confirmed(v), "incomplete": incomplete, "case": case_of(v),
            "n_ops": len(v.ops), "expected": v.expected, "actual": v.actual, "repro": repro, "logs": logs,
            "violation": violation_to_json(v)}


def skipped_rows(spec: RunSpec, skipped: List[Skipped]) -> List[Dict[str, Any]]:
    """One row per skipped signature (its first candidate), vid <run_id>-s<k>; nothing replayed."""
    return [violation_row(spec, f"{spec.run_id}-s{k:02d}", s.violations[0], "", [], False, s.status, s.reason,
                          len(s.violations)) for k, s in enumerate(skipped)]


def record_violations(spec: RunSpec, ctx: OracleContext, paths: CampaignPaths, done: List[Violation],
                      rec: ReplayRecorder) -> List[Dict[str, Any]]:
    """repro.json per replayed candidate; the last confirming replay's logs for confirmed ones."""
    rows, originals = [], rec.replayed_in_order()
    if len(originals) != len(done):
        logger.warning("replay record does not match confirm_all (%d vs %d): logs not attributed",
                       len(originals), len(done))
        originals = []
    for k, v in enumerate(done):
        vid, vdir = f"{spec.run_id}-v{k:02d}", paths.violation_dir(f"{spec.run_id}-v{k:02d}")
        orig = originals[k] if originals else None
        logs = rec.last_confirming_logs(orig) if orig is not None and flake.is_confirmed(v) else []
        names = keep_logs(logs, os.path.join(vdir, "logs"))
        incomplete = orig is not None and rec.incomplete(orig)
        doc = repro_document(ctx, v, campaign=spec.campaign, vid=vid, source=spec.source,
                             project_ref=spec.project_ref, commit=spec.commit, logs=[f"logs/{n}" for n in names],
                             extra={"incomplete": incomplete})
        write_json(os.path.join(vdir, "repro.json"), doc)
        rows.append(violation_row(spec, vid, v, rel(os.path.join(vdir, "repro.json")), names, incomplete))
    return rows


def execute(spec: RunSpec, paths: CampaignPaths, flake_cfg: flake.FlakeConfig, soft_deadline_s: float,
            cap: CapConfig = CapConfig(0), cap_path: str = "", cap_fallback: Sequence[str] = ()) -> Dict[str, Any]:
    t0 = time.monotonic()
    ctx = build_context(spec, paths)
    os.makedirs(ctx.scratch(), exist_ok=True)
    out: Dict[str, Any] = {"run_id": spec.run_id, "status": "ok", "error": "", "targets": [t.path for t in ctx.targets],
                           "positions": sum(len(t.positions) for t in ctx.targets)}
    oracle = oracles.get(spec.oracle)
    if not ctx.targets:
        return dict(out, status="no-targets", error="no eligible target file for this seed", seconds=0.0)
    if not oracle.applies_to(spec.server_kind):
        return dict(out, status="not-applicable", error=f"{spec.oracle} does not apply to {spec.server_kind}")
    logger.info("run %s: %s on %s %s, %s seed %d %s, targets %s", spec.run_id, spec.oracle, spec.server_kind,
                spec.server_version, spec.project, spec.seed, spec.timing, out["targets"])
    res = oracle.run(ctx)
    t_run = time.monotonic() - t0
    write_candidates(paths.candidates(spec.run_id), res.candidates)
    write_json(os.path.join(ctx.scratch(), "run.json"), dict(counters(res), candidates=len(res.candidates)))
    logger.info("run %s: %d candidate(s) in %.0fs; confirming", spec.run_id, len(res.candidates), t_run)
    capped = read_capped(cap_path, cap_fallback) if cap.runs > 0 else set()
    keep, skipped = split_candidates(res.candidates, capped, cap.scope, spec.project, spec.server_version)
    rec = ReplayRecorder(oracle, os.path.join(ctx.scratch(), "logs"), t0 + soft_deadline_s)
    done, stats = flake.confirm_all(rec, ctx, keep, flake_cfg)
    rows = record_violations(spec, ctx, paths, done, rec)
    incomplete = sum(r["incomplete"] for r in rows)
    rows += skipped_rows(spec, skipped)
    if incomplete:
        out.update(status="incomplete", error=f"soft deadline: {incomplete} candidate(s) not fully replayed")
    return dict(out, counters=counters(res), candidates=len(res.candidates), **skip_counts(skipped),
                candidate_signatures=signature_counts(res.candidates), flake=stats, replayed=len(done),
                confirmed=stats["confirmed"], flaky=stats["flaky"], incomplete=incomplete,
                confirmed_signatures=sorted({v.signature for v in done if flake.is_confirmed(v)}),
                violations=rows, run_seconds=round(t_run, 1), confirm_seconds=round(time.monotonic() - t0 - t_run, 1),
                seconds=round(time.monotonic() - t0, 1), sessions=res.sessions,
                replay_sessions_seconds=round(sum(c.outcome.seconds for c in rec.calls), 1))


def load_spec(path: str) -> Tuple[RunSpec, CampaignPaths, flake.FlakeConfig, float, CapConfig, str]:
    with open(path, "r", encoding="utf-8") as f:
        d: Mapping[str, Any] = json.load(f)
    fl, cap = d.get("flake") or {}, d.get("cap") or {}
    return (RunSpec.from_json(d["spec"]), CampaignPaths(d["root"], d["scratch"]),
            flake.FlakeConfig(n=int(fl.get("n", 3)), per_signature=int(fl.get("per_signature", 1))),
            float(d.get("soft_deadline_s", 1e9)), CapConfig(int(cap.get("runs", 0)), str(cap.get("scope", "campaign"))),
            str(d.get("counts_path", "")))


def main(argv: List[str]) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if len(argv) != 2:
        logger.error("usage: campaign_run.py <spec.json>")
        return 2
    spec, paths, flake_cfg, soft, cap, counts_path = load_spec(argv[1])
    result = execute(spec, paths, flake_cfg, soft, cap, counts_path)
    write_json(os.path.join(paths.run_scratch(spec.run_id), "result.json"), result)
    logger.info("run %s finished: %s, %s confirmed of %s candidate(s), %.0fs", spec.run_id, result["status"],
                result.get("confirmed", 0), result.get("candidates", 0), result.get("seconds", 0.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
