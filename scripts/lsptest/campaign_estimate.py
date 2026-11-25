"""Dry-run timings per (oracle, server kind) and the projected wall time of a campaign.

Reads data/lsptest/runs/<dry-run id>/{results,violations}.jsonl and prints, per (oracle, kind): the
runs measured, mean seconds per run (oracle run + confirmation), sessions, candidates, replayed and
confirmed signatures, and what the cost controls skip (campaign_costs.py): replayed signatures
that carry a legitimate-difference label (rows recorded before the labels existed are labelled
from the registry) and capped ones. Then it projects a campaign config onto those timings with
the model in MODEL (printed with the projection). --proxy kind=other uses another kind's timings
for a kind the dry run did not measure.

Run line: python3 scripts/lsptest/campaign_estimate.py --dry-run-id dryrun --config data/lsptest/campaigns/main_v1.json [--concurrency 4,6] [--proxy pyright=gopls] [--out data/lsptest/runs/dryrun/estimate.md]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Mapping, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from campaign_config import RunSpec  # noqa: E402
from campaign_costs import CapConfig, signature_label  # noqa: E402
from campaign_store import REPO, latest_rows, paths_for, read_jsonl  # noqa: E402

logger = logging.getLogger("campaign_estimate")
CASE_SCALED = {"r1_history": 1.0, "r2_handles": 1.0, "r4_edits": 1.0, "r5_transforms": 2.0}  # fixed sessions
MODEL = ("per run, the dry-run means of its (oracle, kind) are used: the oracle run is scaled to the run's max_cases "
         "for oracles whose work grows with it (r1, r2, r4, r5: a fixed part of one fresh session, R5 two, a session "
         "costing about the dry-run R0 time; the rest linear), and, for the high estimate only, by (s0 + extra) / s0, "
         "where s0 is that session cost and extra is how much longer the project's corpus probe took to settle than "
         "the dry-run project's. Confirmation is the dry-run confirmation time without the share of replayed "
         "signatures that now carry a legitimate-difference label; the low estimate also applies the signature cap as "
         "if every signature of an (oracle, kind) queue recurred in all its runs (confirmations in min(N, K) of N "
         "runs), the high estimate as if none recurred. Wall time at concurrency c = max(total / c, longest run, "
         "run-hours of a kind with a limit L / min(c, L)). Timings come from a shared, loaded machine at the dry run's "
         "concurrency; more concurrent runs add contention.")
Key = Tuple[str, str]
FIELDS = ("wall_seconds", "run_seconds", "confirm_seconds", "sessions", "candidates", "replayed", "confirmed",
          "labelled", "labelled_replayed", "capped", "max_cases")


def dry_table(rows: Sequence[Mapping[str, Any]], violations: Sequence[Mapping[str, Any]]) -> Dict[Key, Dict[str, Any]]:
    """(oracle, kind) -> mean of FIELDS over the dry-run runs, plus runs, statuses and projects."""
    labelled_by_run: Dict[str, int] = {}
    for v in latest_rows(violations):
        if v.get("status") in (None, "", "confirmed", "flaky", "not-reproduced", "incomplete") and \
                signature_label(str(v.get("signature", ""))):
            labelled_by_run[v["run_id"]] = labelled_by_run.get(v["run_id"], 0) + 1  # replayed, now labelled
    groups: Dict[Key, List[Dict[str, Any]]] = {}
    for r in latest_rows(rows, "run_id"):
        c = r.get("counters") or {}
        vals = {"wall_seconds": r.get("wall_seconds"), "run_seconds": r.get("run_seconds", r.get("wall_seconds")),
                "confirm_seconds": r.get("confirm_seconds") or 0.0, "sessions": c.get("sessions", r.get("sessions")),
                "candidates": r.get("candidates"), "replayed": r.get("replayed"), "confirmed": r.get("confirmed"),
                "labelled": r.get("labelled_legitimate") or 0, "labelled_replayed": labelled_by_run.get(r["run_id"], 0),
                "capped": r.get("capped") or 0, "max_cases": r.get("max_cases"),
                "status": r.get("status"), "project": r.get("project"), "version": r.get("server_version")}
        groups.setdefault((r["oracle"], r["server_kind"]), []).append(vals)
    out: Dict[Key, Dict[str, Any]] = {}
    for key, vals in groups.items():
        agg: Dict[str, Any] = {f: sum(float(v[f] or 0) for v in vals) / len(vals) for f in FIELDS}
        agg.update(runs=len(vals), statuses=sorted({str(v["status"]) for v in vals}),
                   projects=sorted({str(v["project"]) for v in vals}), versions=sorted({str(v["version"]) for v in vals}))
        out[key] = agg
    return out


def table_markdown(table: Mapping[Key, Mapping[str, Any]], oracle_order: Sequence[str],
                   kind_order: Sequence[str]) -> List[str]:
    lines = ["| oracle | kind | runs | projects | max_cases | mean s per run (run + confirm) | sessions | candidates | "
             "replayed | confirmed | labelled (skipped + replayed before labels) | capped | status |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for o in oracle_order:
        for k in kind_order:
            r = table.get((o, k))
            if r is not None:
                lines.append(f"| {o} | {k} | {r['runs']} | {', '.join(r['projects'])[:60]} | {r['max_cases']:.0f} | "
                             f"{r['wall_seconds']:.1f} ({r['run_seconds']:.1f} + {r['confirm_seconds']:.1f}) | "
                             f"{r['sessions']:.1f} | {r['candidates']:.1f} | {r['replayed']:.1f} | {r['confirmed']:.1f} | "
                             f"{r['labelled']:.1f} + {r['labelled_replayed']:.1f} | {r['capped']:.1f} | "
                             f"{', '.join(r['statuses'])} |")
    return lines


def estimate_run(spec: RunSpec, table: Mapping[Key, Mapping[str, Any]], settle: Mapping[str, float],
                 cap: CapConfig, queue_runs: int, proxy: Mapping[str, str]) -> Tuple[float, float]:
    """(low, high) projected worker seconds of one planned run (see MODEL); (0, 0) when not measured."""
    kind = proxy.get(spec.server_kind, spec.server_kind)
    d, r0 = table.get((spec.oracle, kind)), table.get(("r0_crash", kind))
    if d is None or not d["wall_seconds"]:
        return 0.0, 0.0
    run, confirm = float(d["run_seconds"]), float(d["confirm_seconds"])
    overhead = max(0.0, float(d["wall_seconds"]) - run - confirm)
    if d["replayed"]:  # replays of signatures that now carry a label (rows recorded before the labels existed)
        confirm *= max(0.0, 1.0 - float(d["labelled_replayed"]) / float(d["replayed"]))
    s0 = float(r0["run_seconds"]) if r0 and r0["run_seconds"] else max(1.0, settle.get(d["projects"][0], 1.0))
    if spec.oracle in CASE_SCALED and d["max_cases"]:
        factor = spec.max_cases / float(d["max_cases"])
        fixed = min(run, CASE_SCALED[spec.oracle] * s0)
        run, confirm = fixed + (run - fixed) * factor, confirm * factor
    extra = max(0.0, settle.get(spec.project, 0.0) - settle.get(d["projects"][0], 0.0)) if len(d["projects"]) == 1 else 0.0
    share = min(queue_runs, cap.runs) / queue_runs if cap.runs > 0 and queue_runs else 1.0
    return overhead + run + confirm * share, overhead + run * (s0 + extra) / s0 + confirm


def project(runs: Sequence[RunSpec], table: Mapping[Key, Mapping[str, Any]], settle: Mapping[str, float],
            cap: CapConfig, proxy: Mapping[str, str]) -> Dict[str, Any]:
    def queue(s: RunSpec) -> Tuple[str, ...]:  # the runs a signature can recur in under the cap's scope
        return (s.oracle, s.server_kind) + ((s.project, s.server_version) if cap.scope == "build" else ())

    queues: Dict[Tuple[str, ...], int] = {}
    for s in runs:
        queues[queue(s)] = queues.get(queue(s), 0) + 1
    per: Dict[str, List[float]] = {}
    missing: Dict[str, int] = {}
    lows, highs = [], []
    for s in runs:
        lo, hi = estimate_run(s, table, settle, cap, queues[queue(s)], proxy)
        k = f"{s.oracle} {s.server_kind}"
        missing.update({k: missing.get(k, 0) + 1} if hi <= 0 else {})
        row = per.setdefault(k, [0.0, 0.0])
        row[0], row[1] = row[0] + lo, row[1] + hi
        lows.append(lo)
        highs.append(hi)
    return {"runs": len(runs), "low_hours": sum(lows) / 3600, "high_hours": sum(highs) / 3600,
            "longest_low_hours": max(lows, default=0) / 3600, "longest_high_hours": max(highs, default=0) / 3600,
            "per_oracle_server_hours": {k: (round(v[0] / 3600, 2), round(v[1] / 3600, 2)) for k, v in sorted(per.items())},
            "unmeasured": missing}


def settle_by_server(corpus_path: str) -> Dict[Tuple[str, str], float]:
    """(server kind, "<repo>@<sha12>") -> the corpus probe's settle seconds (settled probes only)."""
    if not corpus_path or not os.path.isfile(corpus_path):
        return {}
    with open(corpus_path, "r", encoding="utf-8") as f:
        recs = json.load(f)
    return {(str(r["server"]), f"{r['repo']}@{r.get('commit12', '')}"): float(r.get("seconds") or 0.0)
            for r in recs if r.get("settled")}


def wall_hours(per_kind: Mapping[str, Mapping[str, Any]], limits: Mapping[str, int], c: int, which: str) -> float:
    total = sum(p[f"{which}_hours"] for p in per_kind.values())
    longest = max((p[f"longest_{which}_hours"] for p in per_kind.values()), default=0.0)
    capped = [p[f"{which}_hours"] / min(c, limits[k]) for k, p in per_kind.items() if k in limits]
    return max([total / c, longest] + capped)


def main() -> int:
    from campaign import load_plan  # late import: campaign imports the oracle registry
    from campaign_config import load_config

    ap = argparse.ArgumentParser(description="Dry-run table and projected campaign wall time.")
    ap.add_argument("--dry-run-id", required=True)
    ap.add_argument("--config", required=True, help="the campaign config to project")
    ap.add_argument("--concurrency", default="4,6")
    ap.add_argument("--proxy", default="", help="kind=measured_kind,... for kinds the dry run did not measure")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    dry = paths_for(args.dry_run_id)
    table = dry_table(read_jsonl(dry.results), read_jsonl(dry.violations))
    cfg, runs, _, _ = load_plan(load_config(args.config), False)
    by_server = settle_by_server(os.path.join(REPO, cfg.corpus) if cfg.corpus else "")
    proxy = dict(x.split("=", 1) for x in args.proxy.split(",") if "=" in x)
    conc = [int(x) for x in args.concurrency.split(",") if x]
    lines = [f"# Dry run {args.dry_run_id}: timings per (oracle, server kind)", ""]
    lines += table_markdown(table, [o.name for o in cfg.oracles], cfg.kinds)
    per_kind: Dict[str, Dict[str, Any]] = {}
    for kind in [k for k in cfg.kinds if any(s.server_kind == k for s in runs)]:
        settle = {p: t for (k, p), t in by_server.items() if k == kind}
        per_kind[kind] = project([s for s in runs if s.server_kind == kind], table, settle, cfg.cap, proxy)
    low = sum(p["low_hours"] for p in per_kind.values())
    high = sum(p["high_hours"] for p in per_kind.values())
    lines += ["", f"# Projection of {cfg.id}: {len(runs)} runs", "", "Model: " + MODEL, "",
              f"Cost controls: signature cap {cfg.cap.runs} runs ({cfg.cap.scope} scope); proxies {proxy or 'none'}.",
              "", "| server kind | runs | run-hours (low - high) |", "|---|---|---|"]
    lines += [f"| {k} | {p['runs']} | {p['low_hours']:.1f} - {p['high_hours']:.1f} |" for k, p in per_kind.items()]
    lines += ["", f"Total {low:.1f} - {high:.1f} run-hours; server limits {dict(cfg.server_limits)}."]
    lines += [f"- concurrency {c}: about {wall_hours(per_kind, cfg.server_limits, c, 'low'):.1f} - "
              f"{wall_hours(per_kind, cfg.server_limits, c, 'high'):.1f} h wall time" for c in conc]
    unmeasured = {k: v for p in per_kind.values() for k, v in p["unmeasured"].items()}
    if unmeasured:
        lines.append(f"- not measured in the dry run (counted as 0): {unmeasured}")
    lines += ["", "Per (oracle, kind), run-hours (low, high): " + ", ".join(
        f"{k} {v}" for p in per_kind.values() for k, v in p["per_oracle_server_hours"].items())]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
