"""Numbers of the study setup and of the main campaign (main_v1).

setup: server kinds and versions, corpus, planned runs, seeds and timings, concurrency and the
wall-clock hours of main_v1 part 1 (every oracle but r1_history), part 2 (r1_history) and bench_v1.
main: runs by status and oracle, run seconds per (oracle, server kind), violation rows by status
(last row per vid), confirmed signatures, triage groups, reduction, the author's verdicts
(triage/decisions.csv) and the older-release sweep (sweep/older-2025).

Run line: not run directly; imported by scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import os

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from numbers_io import (CORPUS, CORPUS_PREPARED, MAIN_RUN, R1, SWEEP_DIR, Sources, counts, describe, latest,
                        matrix, planned_runs, ratio, span, split_signature)

logger = logging.getLogger(__name__)

VERDICTS = ("bug", "legitimate", "tool-artifact")
SWEEP_VERDICTS = ("reproduced", "not-reproduced", "flaky", "unsettled", "error", "skipped")


@dataclass(frozen=True)
class MainData:
    """Inputs of the main campaign: last row per run_id and per vid, triage, author and sweep files."""

    config: Dict[str, Any]
    results: List[Dict[str, Any]]
    violations: List[Dict[str, Any]]
    planned: List[Dict[str, Any]]
    groups: List[Dict[str, Any]]
    reductions: Dict[str, Dict[str, Any]]
    decisions: Dict[str, Dict[str, str]]
    sweep: Dict[str, Dict[str, Any]]
    corpus: Dict[str, Any]
    prepared: List[Dict[str, Any]]
    reasons: Dict[str, Dict[str, str]] = field(default_factory=dict)  # triage/verdict_reasons.csv, when present


def load_main(src: Sources, run: str = MAIN_RUN, corpus: str = CORPUS, prepared: str = CORPUS_PREPARED) -> MainData:
    """Read every input of one current-release campaign once (hashes recorded in src).

    Args:
        src: repository sources.
        run: the campaign's run directory; main_v1 by default, the campaign of the sections setup and main.
        corpus: its corpus selection file.
        prepared: its prepared corpus file.

    Returns:
        The campaign's MainData; the year-old sweep is read from <run>/sweep/older-2025.
    """
    sweep_dir = SWEEP_DIR if run == MAIN_RUN else f"{run}/sweep/older-2025"
    config = src.json(f"{run}/config.json")
    groups = list(src.json(f"{run}/triage/triage.json")["groups"])
    reductions = {g["gid"]: src.json(f"{run}/triage/{g['gid']}/reduction.json") for g in groups}
    decisions = {r["group"]: r for r in src.csv_rows(f"{run}/triage/decisions.csv")}
    sweep = {str(r["gid"]): r for r in latest(src.jsonl(f"{sweep_dir}/results.jsonl"), "gid")}
    for gid in (g["gid"] for g in groups):
        if gid not in decisions:
            logger.warning("group %s has no row in decisions.csv", gid)
        if gid not in sweep:
            logger.warning("group %s has no row in the older-2025 sweep", gid)
    return MainData(config=config, results=latest(src.jsonl(f"{run}/results.jsonl"), "run_id"),
                    violations=latest(src.jsonl(f"{run}/violations.jsonl"), "vid"),
                    planned=planned_runs(config, src, run), groups=groups, reductions=reductions, decisions=decisions,
                    sweep=sweep, corpus=src.json(corpus), prepared=list(src.json(prepared)),
                    reasons={r["group"]: r for r in src.csv_rows(f"{run}/triage/verdict_reasons.csv")}
                    if os.path.exists(src.abspath(f"{run}/triage/verdict_reasons.csv")) else {})


def wall_seconds(rows: Sequence[Mapping[str, Any]]) -> List[float]:
    """Per-run wall seconds (worker start to end); present for every status, timeouts included."""
    return [float(r["wall_seconds"]) for r in rows if r.get("wall_seconds") is not None]


def run_hours(rows: Sequence[Mapping[str, Any]]) -> float:
    return round(sum(wall_seconds(rows)) / 3600, 2)


def oracle_settings(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """Seeds per timing, max_cases and server restriction of each oracle, as configured."""
    return {name: dict(sorted(spec.items())) for name, spec in sorted((cfg.get("oracles") or {}).items())}


def corpus_numbers(d: MainData) -> Dict[str, Any]:
    by_language = {lang: len(repos) for lang, repos in sorted(d.corpus["corpus"].items())}
    prepared_projects = {r["repo"] for r in d.prepared}
    forced = [{"server": p["server"], "project": p["project"], "reason": p["forced"]}
              for p in d.config.get("eligible_pairs", []) if p.get("forced")]
    return {"selection_cutoff": d.corpus.get("cutoff"), "selected_on": d.corpus.get("selected_on"),
            "projects": sum(by_language.values()), "projects_by_language": by_language,
            "projects_prepared": len(prepared_projects), "pairs": len(d.prepared),
            "pairs_by_server": counts(r["server"] for r in d.prepared),
            "eligible_pairs": len(d.config.get("eligible_pairs", [])), "forced_pairs": forced,
            "excluded_pairs": len(d.config.get("excluded_pairs", []))}


def setup_section(d: MainData, bench_config: Mapping[str, Any], bench_results: Sequence[Mapping[str, Any]],
                  bench_planned: Sequence[Mapping[str, Any]], freezes: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    cfg = d.config["config"]
    bcfg = bench_config["config"]
    part1 = [r for r in d.results if r["oracle"] != R1]
    part2 = [r for r in d.results if r["oracle"] == R1]
    builds = sorted({(str(r["server_kind"]), str(r["server_version"])) for r in bench_results})
    settle_by_kind = {k: sorted({float(r["settle_timeout_s"]) for r in bench_results
                                 if r["server_kind"] == k and r.get("settle_timeout_s") is not None})
                      for k in sorted({str(r["server_kind"]) for r in bench_results})}
    main = {"servers": [{"kind": b["kind"], "version": b["version"], "package_version": b.get("package_version", ""),
                         "label": b.get("label", "")} for b in d.config.get("server_builds", [])],
            "corpus": corpus_numbers(d),
            "runs_planned": len(d.planned), "runs_planned_by_oracle": counts(s["oracle"] for s in d.planned),
            "runs_planned_by_server": counts(s["server_kind"] for s in d.planned),
            "runs_recorded": len(d.results), "oracles": oracle_settings(cfg),
            "runs_by_timing": counts(r["timing"] for r in d.results),
            "runs_by_oracle_timing": matrix((r["oracle"], r["timing"]) for r in d.results),
            "targets": cfg.get("targets"), "timeouts_s": cfg.get("timeouts"), "concurrency": cfg.get("concurrency"),
            "server_limits": cfg.get("server_limits"), "flake": cfg.get("flake"),
            "signature_cap": cfg.get("signature_cap"),
            "wall_clock": {"part1_other_oracles": span(part1), "part2_r1_history": span(part2)},
            "run_hours": {"part1_other_oracles": run_hours(part1), "part2_r1_history": run_hours(part2)},
            "invocations": d.config.get("invocations"), "machine": d.config.get("machine")}
    bench = {"cases": len(bcfg.get("bench_cases") or []),
             "spec_probe_cases": sum(bool(c.get("spec_probe")) for c in bcfg.get("bench_cases") or []),
             "builds": len(builds), "builds_by_kind": counts(k for k, _ in builds),
             "oracles": oracle_settings(bcfg), "runs_planned": len(bench_planned), "runs_recorded": len(bench_results),
             "runs_by_timing": counts(r["timing"] for r in bench_results),
             "targets": bcfg.get("targets"), "timeouts_s": bcfg.get("timeouts"),
             "settle_timeout_s_by_kind": settle_by_kind,
             "concurrency": bcfg.get("concurrency"), "server_limits": bcfg.get("server_limits"),
             "flake": bcfg.get("flake"), "signature_cap": bcfg.get("signature_cap"),
             "wall_clock": span(list(bench_results)), "run_hours": run_hours(list(bench_results)),
             "invocations": bench_config.get("invocations")}
    tool = {str(f["id"]): {"created": f.get("created"), "tree_digest": f.get("tree_digest"),
                           "files": len(f.get("files") or {})} for f in freezes}
    return {"main_v1": main, "bench_v1": bench, "tool_freezes": tool}


def runs_numbers(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    not_ok = [{"run_id": r["run_id"], "oracle": r["oracle"], "server": r["server_kind"], "project": r["project"],
               "seed": r["seed"], "timing": r["timing"], "status": r["status"], "error": r.get("error", "")}
              for r in results if r["status"] != "ok"]
    return {"total": len(results), "by_status": counts(r["status"] for r in results),
            "by_oracle": counts(r["oracle"] for r in results), "by_server": counts(r["server_kind"] for r in results),
            "by_oracle_status": matrix((r["oracle"], r["status"]) for r in results), "not_ok": not_ok}


def seconds_numbers(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    per_kind: Dict[str, Dict[str, Any]] = {}
    for oracle in sorted({str(r["oracle"]) for r in results}):
        rows = [r for r in results if r["oracle"] == oracle]
        per_kind[oracle] = {kind: describe(wall_seconds([r for r in rows if r["server_kind"] == kind]))
                            for kind in sorted({str(r["server_kind"]) for r in rows})}
    total = sum(wall_seconds(results))
    return {"measure": "wall_seconds per run (all statuses); p90 by linear interpolation",
            "total_seconds": round(total, 1), "total_hours": round(total / 3600, 2),
            "per_oracle": {o: describe(wall_seconds([r for r in results if r["oracle"] == o])) for o in per_kind},
            "per_oracle_kind": per_kind}


def signature_numbers(signatures: Sequence[str]) -> Dict[str, Any]:
    parts = [split_signature(s) for s in signatures]
    return {"total": len(signatures), "by_oracle": counts(o for _, o, _ in parts),
            "by_kind": counts(k for k, _, _ in parts), "oracle_by_kind": matrix((o, k) for k, o, _ in parts)}


def group_numbers(groups: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    parts = [split_signature(g["signature"]) for g in groups]
    r1 = [(g, k) for g, (k, o, _) in zip(groups, parts) if o == R1]
    return {"total": len(groups), "signatures": len({g["signature"] for g in groups}),
            "members": sum(int(g.get("members") or 0) for g in groups),
            "by_oracle": counts(o for _, o, _ in parts), "by_kind": counts(k for k, _, _ in parts),
            "oracle_by_kind": matrix((o, k) for k, o, _ in parts),
            "r1_history": {"groups": len(r1), "by_family": counts(g["family"] for g, _ in r1),
                           "by_kind": counts(k for _, k in r1)}}


def reduction_numbers(d: MainData) -> Dict[str, Any]:
    return reduction_block(d.groups, d.reductions)


def reduction_block(groups: Sequence[Mapping[str, Any]], reductions: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """Reduction of a campaign's triage groups (triage.json rows and each group's reduction.json).

    Args:
        groups: the groups of triage/triage.json.
        reductions: group id -> its triage/<gid>/reduction.json.

    Returns:
        Groups, groups with operations, operations before and after, per oracle, narrowed, reduced_confirmed,
        budget_exhausted, probes and compute hours.
    """
    reds = [reductions[g["gid"]] for g in groups]
    with_ops = [g for g in groups if int(g.get("ops_before") or 0) > 0]
    by_oracle: Dict[str, Dict[str, int]] = {}
    for g in with_ops:
        e = by_oracle.setdefault(split_signature(g["signature"])[1], {"groups": 0, "ops_before": 0, "ops_after": 0})
        e["groups"] += 1
        e["ops_before"] += int(g["ops_before"])
        e["ops_after"] += int(g["ops_after"] or 0)
    mismatch = [g["gid"] for g in groups if (g.get("ops_before"), g.get("ops_after"))
                != (reductions[g["gid"]].get("ops_before"), reductions[g["gid"]].get("ops_after"))]
    if mismatch:
        logger.warning("ops in triage.json differ from reduction.json for %d group(s)", len(mismatch))
    return {"groups": len(groups), "groups_with_ops": len(with_ops),
            "ops_before": sum(int(g["ops_before"]) for g in with_ops),
            "ops_after": sum(int(g["ops_after"] or 0) for g in with_ops),
            "by_oracle": dict(sorted(by_oracle.items())),
            "narrowed": sum(bool(r.get("narrowed")) for r in reds),
            "reduced_confirmed": counts(r.get("reduced_confirmed") for r in reds),
            "budget_exhausted": sum(bool(r.get("budget_exhausted")) for r in reds),
            "probes": sum(int(r.get("probes") or 0) for r in reds),
            "compute_hours": round(sum(float(r.get("total_seconds") or 0) for r in reds) / 3600, 2),
            "ops_differ_from_triage_json": mismatch}


def minutes(value: str, gid: str) -> Optional[float]:
    if not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        logger.warning("decisions.csv: minutes_spent %r of %s is not a number; ignored", value, gid)
        return None


def verdict_numbers(d: MainData) -> Dict[str, Any]:
    oracle_of = {g["gid"]: split_signature(g["signature"])[1] for g in d.groups}
    rows = [(gid, d.decisions[gid]) for gid in oracle_of if gid in d.decisions]
    judged = [(gid, r["verdict"].strip()) for gid, r in rows if r.get("verdict", "").strip()]
    values = [v for _, v in judged]
    unknown = sorted(set(values) - set(VERDICTS))
    if unknown:
        logger.warning("decisions.csv: unexpected verdict value(s) %s", unknown)
    oracles = sorted(set(oracle_of.values()))
    by_oracle = {o: {v: sum(1 for g, x in judged if oracle_of[g] == o and x == v) for v in (*VERDICTS, *unknown)}
                 for o in oracles}
    spent = [m for m in (minutes(r.get("minutes_spent", ""), gid) for gid, r in rows) if m is not None]
    return {"rows": len(d.decisions), "groups_without_row": sorted(set(oracle_of) - set(d.decisions)),
            "judged": len(judged), "by_verdict": {v: values.count(v) for v in (*VERDICTS, *unknown)},
            "by_oracle_verdict": by_oracle, "precision": ratio(values.count("bug"), len(judged)),
            "precision_by_oracle": {o: ratio(by_oracle[o]["bug"], sum(by_oracle[o].values())) for o in oracles},
            "known_issue_links": sum(bool(r.get("known_issue_link", "").strip()) for _, r in rows),
            "report_links": sum(bool(r.get("report_link", "").strip()) for _, r in rows),
            "maintainer_responses": sum(bool(r.get("maintainer_response", "").strip()) for _, r in rows),
            "minutes_total": round(sum(spent), 1), "minutes_rows": len(spent)}


def sweep_build(row: Mapping[str, Any]) -> str:
    build = row.get("build") or {}
    return f"{build.get('kind', '')} {build.get('version', '')}".strip()


def sweep_numbers(d: MainData) -> Dict[str, Any]:
    rows = [d.sweep[g["gid"]] for g in d.groups if g["gid"] in d.sweep]
    extra = sorted({str(r["verdict"]) for r in rows} - set(SWEEP_VERDICTS))

    def tally(sel: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
        return {v: sum(1 for r in sel if r["verdict"] == v) for v in (*SWEEP_VERDICTS, *extra)}

    by_from: Dict[str, Any] = {}
    for kind in sorted({str(r["from"]) for r in rows}):
        sel = [r for r in rows if r["from"] == kind]
        by_from[kind] = {"builds": sorted({sweep_build(r) for r in sel if sweep_build(r)}), "groups": len(sel),
                         "by_verdict": tally(sel)}
    return {"label": "older-2025", "groups": len(rows), "replayed": sum(1 for r in rows if r["verdict"] != "skipped"),
            "by_verdict": tally(rows), "by_from_kind": by_from,
            "by_oracle": {o: tally([r for r in rows if r["oracle"] == o]) for o in sorted({str(r["oracle"]) for r in rows})},
            "replay_hours": round(sum(float(r.get("seconds") or 0) for r in rows) / 3600, 2)}


REPLAYED = frozenset({"confirmed", "flaky", "not-reproduced", "incomplete"})


def violation_numbers(violations: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Violation rows (last row per vid) by status and by oracle and status, the rows replayed by the 3/3 stability
    filter and the rows it removed (flaky or not reproduced)."""
    return {"rows": len(violations), "by_status": counts(v["status"] for v in violations),
            "by_oracle_status": matrix((v["oracle"], v["status"]) for v in violations),
            "replayed": sum(1 for v in violations if v["status"] in REPLAYED),
            "filtered": sum(1 for v in violations if v["status"] in ("flaky", "not-reproduced"))}


def main_section(d: MainData) -> Dict[str, Any]:
    confirmed = sorted({str(v["signature"]) for v in d.violations if v["status"] == "confirmed"})
    return {"runs": runs_numbers(d.results), "run_seconds": seconds_numbers(d.results),
            "violations": violation_numbers(d.violations),
            "confirmed_signatures": signature_numbers(confirmed), "triage_groups": group_numbers(d.groups),
            "reduction": reduction_numbers(d), "verdicts": verdict_numbers(d), "sweep_older_2025": sweep_numbers(d)}
