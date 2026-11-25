"""Data of the evaluation figures, written to one JSON that the plotting scripts read.

- benchmark_overlap: for every reproduced benchmark case detected by any oracle, the oracles that
  detected it under the joint verdicts on the signatures (numbers_final: the discussion's consensus,
  else the verdict both raters gave): the crash check and the relations (a case counts for an oracle
  when one of its pre-only signatures has the joint verdict yes), and the failing-request observer
  from detection.consensus.error_oracle; with whether the case was run before the tool was frozen.
- bugs_over_time: for every oracle, the runs of the first current-release campaign (main_v1) in the
  order they finished, then those of the second (main_v2), cumulative run-hours (wall seconds, as for
  the cost per bug), the oracle's run-hours when each campaign began (campaign_start_hours), and the
  points where a triage group, a bug group (final verdict) or a distinct bug (root cause, one
  numbering for both campaigns) was first confirmed. Groups are rebuilt from the confirmed
  violations with the frozen triage's own grouping (triage_group.group_rows), so a group's first run
  is the earliest-finishing run among its members. The numbers release.over_time, which the text
  quotes until it switches to the final verdicts, still come from the first campaign and the first
  author's verdicts (bugs_over_time_author); cur.over_time comes from bugs_over_time.
- lifecycle: for every bug, the verdicts of its representative group on the releases of its server line
  (sweep/lifecycle, sweep/newest-2026-09-28 and the refresh sweep/newest-2026-11-18, releases.json for
  dates and roles) and, for gopls, on the development head (sweep/head-2026-11-18,
  scripts/paper/evidence/head_check.py); the oldest release it reproduces on and its age relative to
  the campaign release.

Run by paper_numbers.py (figure_data); writes data/lsptest/figure_data.json.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from numbers_final import load_group_verdicts, load_signature_verdicts
from numbers_io import Sources, latest, tool_module

RUN = "data/lsptest/runs/main_v1"
CURRENT = ("main_v1", "main_v2")    # the current-release campaigns, in the order bugs_over_time joins them
BENCH = "data/lsptest/runs/bench_v1"
FIRST_NEWEST = "newest-2026-09-28"   # the newest releases when the campaign ended (part of the lifecycle plan)
NEWEST = "newest-2026-11-18"         # the refresh before submission (release_sweep.py, RELEASE_SWEEP_AS_OF)
HEAD = "head-2026-11-18"             # gopls development head (evidence/head_check.py)
SHORT = {"r0_crash": "R0", "r1_history": "R1", "r2_handles": "R2", "r3_routes": "R3", "r4_edits": "R4",
         "r5_transforms": "R5", "r6_crossimpl": "R6"}


def benchmark_overlap(src: Sources, consensus: Mapping[str, Any]) -> Dict[str, Any]:
    """The oracles that detect each benchmark case under the joint signature verdicts (consensus = the section
    detection.consensus, for the failing-request observer and the cases run before the freeze)."""
    cases = [c["case"] for c in src.json(f"{BENCH}/detection.json")["cases"]]
    found: Dict[str, set] = {c: set() for c in cases}
    for (case, oracle, _), final in load_signature_verdicts(src).final.items():
        if final.verdict == "yes" and case in found:
            found[case].add(SHORT.get(oracle, oracle))
    for c in consensus["error_oracle"]["cases"]:
        found.setdefault(c, set()).add("error")
    dev = set(consensus["held_out"]["pre_freeze_case_list"])
    rows = [{"case": c, "held_out": c not in dev, "oracles": sorted(o)} for c, o in sorted(found.items()) if o]
    return {"cases": len(cases), "held_out_cases": sum(1 for c in cases if c not in dev), "rows": rows}


def first_runs(src: Sources, run: str) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """A campaign's runs (last row per run_id) in the order they finished, and per run the groups it confirmed first."""
    tg = tool_module("triage_group")
    runs = sorted(latest(src.jsonl(f"{run}/results.jsonl"), "run_id"), key=lambda r: str(r.get("finished_at") or ""))
    finished = {r["run_id"]: str(r.get("finished_at") or "") for r in runs}
    first_run: Dict[str, str] = {}
    for g in tg.group_rows(src.jsonl(f"{run}/violations.jsonl")):
        member_runs = [m["run_id"] for m in g.members if m.get("run_id") in finished]
        if member_runs:
            first_run[g.gid] = min(member_runs, key=lambda rid: finished[rid])
    groups_in_run: Dict[str, List[str]] = {}
    for gid, rid in first_run.items():
        groups_in_run.setdefault(rid, []).append(gid)
    return runs, groups_in_run


def bugs_over_time(src: Sources) -> Dict[str, Any]:
    """Both current-release campaigns joined, first main_v1 then main_v2, with the final verdicts and root causes.

    Raises:
        ValueError: when the triage of a campaign lists a group that the grouping of its violations does not give.
    """
    campaigns = []
    for name in CURRENT:
        run = f"data/lsptest/runs/{name}"
        runs, groups_in_run = first_runs(src, run)
        final = load_group_verdicts(src, name).final
        lost = sorted(set(final) - {g for gs in groups_in_run.values() for g in gs})
        if lost:
            raise ValueError(f"{name}: triage groups without a first run in the regrouped violations: {lost}")
        cause = {r["group"]: r["cause"] for r in src.csv_rows(f"{run}/triage/root_causes.csv")}
        campaigns.append((name, runs, groups_in_run, {g: f.verdict for g, f in final.items()}, cause))
    out: Dict[str, Any] = {}
    for oracle in sorted(SHORT):
        hours, n_runs, n_groups, n_bug_groups, bugs = 0.0, 0, 0, 0, set()
        points: List[Dict[str, Any]] = [{"hours": 0.0, "groups": 0, "bug_groups": 0, "bugs": 0}]
        starts: Dict[str, float] = {}
        for name, runs, groups_in_run, verdict, cause in campaigns:
            starts[name] = round(hours, 4)
            mine = [r for r in runs if r.get("oracle") == oracle]
            n_runs += len(mine)
            for r in mine:
                hours += float(r.get("wall_seconds") or 0) / 3600
                new = groups_in_run.get(r["run_id"], [])
                if not new:
                    continue
                n_groups += len(new)
                n_bug_groups += sum(1 for g in new if verdict.get(g) == "bug")
                bugs |= {cause[g] for g in new if verdict.get(g) == "bug"}
                points.append({"hours": round(hours, 4), "groups": n_groups, "bug_groups": n_bug_groups,
                               "bugs": len(bugs)})
        points.append({"hours": round(hours, 4), "groups": n_groups, "bug_groups": n_bug_groups, "bugs": len(bugs)})
        out[SHORT[oracle]] = {"runs": n_runs, "hours": round(hours, 4), "points": points, "campaign_start_hours": starts}
    return out


def bugs_over_time_author(src: Sources) -> Dict[str, Any]:
    """bugs_over_time of the first campaign alone with the first author's verdicts (triage/decisions.csv), as the
    figure was drawn before the second campaign; kept for release.over_time until the text switches over."""
    tg = tool_module("triage_group")
    runs = sorted(src.jsonl(f"{RUN}/results.jsonl"), key=lambda r: str(r.get("finished_at") or ""))
    finished = {r["run_id"]: str(r.get("finished_at") or "") for r in runs}
    verdict = {r["group"]: r["verdict"] for r in src.csv_rows(f"{RUN}/triage/decisions.csv")}
    cause = {r["group"]: r["cause"] for r in src.csv_rows(f"{RUN}/triage/root_causes.csv")}
    first_run: Dict[str, str] = {}
    for g in tg.group_rows(src.jsonl(f"{RUN}/violations.jsonl")):
        member_runs = [m["run_id"] for m in g.members if m.get("run_id") in finished]
        if member_runs:
            first_run[g.gid] = min(member_runs, key=lambda rid: finished[rid])
    groups_in_run: Dict[str, List[str]] = {}
    for gid, rid in first_run.items():
        groups_in_run.setdefault(rid, []).append(gid)
    out: Dict[str, Any] = {}
    for oracle in sorted(SHORT):
        hours, n_groups, n_bug_groups, bugs = 0.0, 0, 0, set()
        points: List[Dict[str, Any]] = [{"hours": 0.0, "groups": 0, "bug_groups": 0, "bugs": 0}]
        mine = [r for r in runs if r.get("oracle") == oracle]
        for r in mine:
            hours += float(r.get("wall_seconds") or 0) / 3600
            new = groups_in_run.get(r["run_id"], [])
            if not new:
                continue
            n_groups += len(new)
            n_bug_groups += sum(1 for g in new if verdict.get(g) == "bug")
            bugs |= {cause[g] for g in new if verdict.get(g) == "bug" and g in cause}
            points.append({"hours": round(hours, 4), "groups": n_groups, "bug_groups": n_bug_groups, "bugs": len(bugs)})
        points.append({"hours": round(hours, 4), "groups": n_groups, "bug_groups": n_bug_groups, "bugs": len(bugs)})
        # four decimals, so that the one-decimal values of over_time_numbers are not rounded twice (8.649 -> 8.65 -> 8.7)
        out[SHORT[oracle]] = {"runs": len(mine), "hours": round(hours, 4), "points": points}
    return out


def replay_state(r: Optional[Mapping[str, Any]]) -> str:
    """reproduced, partly, not-reproduced or n/a for one replay row (release_sweep / version_sweep schema).

    An edit-validity replay of a seeded quick fix (oracles/r4_edits.py, _replay_r4 with r4_seeded.mutation_case_session)
    starts its fresh baseline and control only after its case session shows the violation. When the case session runs
    to the end without it (the seeded diagnostic or the same quick fix is not offered, or the fix no longer breaks the
    code), the row has settled = replays and control_stable = 0, which the frozen sweep's verdict calls unsettled. Such
    a row is read here as not reproduced: the build ran the mutation and, where offered, the same quick fix in every
    replay, and the violation never showed."""
    if r is None or r.get("error"):
        return "n/a"
    if r["reproduced"] == r["replays"]:
        return "reproduced"
    if r["reproduced"] > 0:
        return "partly"
    if r["verdict"] == "not-reproduced":
        return "not-reproduced"
    if "-mutation-" in str(r.get("gid", "")) and r.get("oracle") == "r4_edits" and r["settled"] == r["replays"]:
        return "not-reproduced"
    return "n/a"


def months_between(a: str, b: str) -> float:
    return round((dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days / 30.44, 1)


def lifecycle(src: Sources, run: str = RUN) -> Dict[str, Any]:
    """Per bug of one campaign's lifecycle plan (run: the campaign directory): its representative group on every
    release of the plan, on the refreshed newest releases (NEWEST) and, for gopls, on the development head (HEAD).
    The lifecycle plan's builds with role "newest" are the newest of 2026-09-28; they keep that role under the name
    "newest on 2026-09-28". A label the campaign has not run (no releases.json or results.jsonl: main_v2 has no
    newest-2026-09-28 and no head label, and its lifecycle results come in while its sweep runs) is skipped; a
    build without a result is not judged (n/a). A build that only a later label (NEWEST, HEAD) adds gets a cell only for
    the groups that label planned: the gopls development head was replayed for some bugs, and the others get no cell there."""
    plan = src.json(f"{run}/sweep/lifecycle/releases.json")
    later = [src.json(f"{run}/sweep/{label}/releases.json") for label in (NEWEST, HEAD)
             if os.path.exists(src.abspath(f"{run}/sweep/{label}/releases.json"))]
    rows = [r for label in ("lifecycle", FIRST_NEWEST, NEWEST, HEAD)
            if os.path.exists(src.abspath(f"{run}/sweep/{label}/results.jsonl"))
            for r in src.jsonl(f"{run}/sweep/{label}/results.jsonl")]
    got = {(r["gid"], r["build"]["version"]): r for r in rows}
    builds_all: List[Dict[str, Any]] = []
    every = None  # the lifecycle plan's builds are planned for all of its groups
    for b in plan["builds"]:
        roles = [f"newest on {FIRST_NEWEST[len('newest-'):]}" if r == "newest" else r for r in b.get("roles", [])]
        builds_all.append(dict(b, roles=roles, planned=every))
    for doc in later:
        planned = {g["gid"] for g in doc.get("groups", [])}
        for b in doc["builds"]:
            same = next((x for x in builds_all if x["line"] == b["line"] and x["version"] == b["version"]), None)
            if same is None:
                builds_all.append(dict(b, planned=set(planned)))
            else:
                same["roles"] = sorted(set(same["roles"]) | set(b.get("roles", [])))
                if same["planned"] is not None:
                    same["planned"] |= planned
    out: Dict[str, Any] = {}
    for g in plan["groups"]:
        builds = sorted((b for b in builds_all if b["line"] == g["line"]), key=lambda b: (b["released"], b["version"]))
        cells: List[Dict[str, Any]] = []
        for b in builds:
            if b["planned"] is not None and g["gid"] not in b["planned"]:
                continue
            r = got.get((g["gid"], b["version"]))
            if b.get("status") != "ok" or g["gid"] in (b.get("skip") or {}):
                r = None
            state = replay_state(r)
            cells.append({"version": b["release"], "build": b["version"], "released": b["released"], "roles": b.get("roles", []),
                          "state": state, "reproduced": r["reproduced"] if r else None, "replays": r["replays"] if r else None})
        campaign = next(c for c in cells if "campaign" in c["roles"])
        oldest: Optional[Dict[str, Any]] = next((c for c in cells if c["state"] in ("reproduced", "partly")), None)
        out[g["cause"]] = {"line": g["line"], "group": g["gid"], "cells": cells, "campaign_release": campaign["released"],
                           "oldest_reproduced": oldest["version"] if oldest else None,
                           "oldest_released": oldest["released"] if oldest else None,
                           "age_months": months_between(oldest["released"], campaign["released"]) if oldest else None}
    return out


def figure_data(src: Sources, numbers: Mapping[str, Any]) -> Dict[str, Any]:
    """The data of the figures; needs the section detection.consensus (paper_numbers.consensus_numbers)."""
    return {"benchmark_overlap": benchmark_overlap(src, numbers["detection"]["consensus"]),
            "bugs_over_time": bugs_over_time(src),
            "lifecycle": lifecycle(src)}


def lifecycle_numbers(life: Mapping[str, Any]) -> Dict[str, Any]:
    """Numbers for the text: bugs older than a year relative to the campaign release, per-cause ages."""
    ages = {c: v["age_months"] for c, v in life.items()}
    return {"older_than_year": sum(1 for a in ages.values() if a is not None and a >= 12),
            "causes": len(ages), "age_months": ages,
            "oldest": {c: v["oldest_reproduced"] for c, v in life.items()}}


def sweep_numbers(src: Sources, label: str) -> Dict[str, Any]:
    """Counts of one replay label over the bug groups: groups reproduced in all, some or none of their replays, and
    the causes with at least one reproducing group and with none."""
    rows = src.jsonl(f"{RUN}/sweep/{label}/results.jsonl")
    cause = {r["group"]: r["cause"] for r in src.csv_rows(f"{RUN}/triage/root_causes.csv")}
    plan = src.json(f"{RUN}/sweep/{label}/releases.json")
    states = [(r, replay_state(r)) for r in rows]
    by_cause: Dict[str, List[str]] = {}
    for r, st in states:
        if r["gid"] in cause:
            by_cause.setdefault(cause[r["gid"]], []).append(st)
    order = lambda cs: sorted(cs, key=lambda c: int(c[1:]))  # noqa: E731
    gone = order(c for c, sts in by_cause.items() if all(st == "not-reproduced" for st in sts))
    part = order(c for c, sts in by_cause.items() if "not-reproduced" in sts and any(st in ("reproduced", "partly") for st in sts))
    return {"groups": len(rows),
            "reproduced_all": sum(1 for _, st in states if st == "reproduced"),
            "reproduced_some": sum(1 for _, st in states if st == "partly"),
            "not_reproduced": sum(1 for _, st in states if st == "not-reproduced"),
            "not_judged": sum(1 for _, st in states if st == "n/a"),
            "errors": sum(1 for r in rows if r.get("error")),
            "causes_partly_gone": len(part), "causes_partly_gone_list": ", ".join(part) or "none",
            "causes": len(by_cause),
            "causes_reproduced": sum(1 for sts in by_cause.values() if any(st in ("reproduced", "partly") for st in sts)),
            "causes_reproduced_all": sum(1 for sts in by_cause.values() if "reproduced" in sts),  # a group in 3 of 3
            "causes_not_reproduced": len(gone), "causes_not_reproduced_list": ", ".join(gone) or "none",
            "causes_reproduced_list": ", ".join(order(c for c, sts in by_cause.items()
                                                      if any(st in ("reproduced", "partly") for st in sts))) or "none",
            "by_cause": {c: {"groups": len(sts), "reproducing": sum(1 for st in sts if st in ("reproduced", "partly")),
                             "gone": sum(1 for st in sts if st == "not-reproduced")} for c, sts in order_items(by_cause)},
            "date": plan.get("as_of", ""),
            "releases": dict(sorted((b["line"], b["release"]) for b in plan["builds"] if b.get("status") == "ok"))}


def order_items(d: Mapping[str, Any]) -> List[Any]:
    """Items of a dict keyed by cause (C1, C2, ...) in cause order."""
    return sorted(d.items(), key=lambda kv: int(kv[0][1:]))


def release_numbers(src: Sources, fig: Mapping[str, Any]) -> Dict[str, Any]:
    """The replay of every bug group on the newest releases (the refresh NEWEST; FIRST_NEWEST as of the campaign's
    end), of the gopls groups on the gopls development head (HEAD), and the lifecycle numbers."""
    head = sweep_numbers(src, HEAD)
    head_plan = src.json(f"{RUN}/sweep/{HEAD}/releases.json")
    head_build = head_plan["builds"][0]
    head.update(version=head_build["version"], commit=head_build["version"].rsplit("-", 1)[-1][:12],
                commit_date=head_build["released"])
    newest = sweep_numbers(src, NEWEST)
    fixed = [r["cause"] for r in src.csv_rows(f"{RUN}/upstream/feedback.csv") if r["status"] == "fixed"]
    nb, hb = newest["by_cause"], head["by_cause"]
    unreleased = [c for c in fixed if nb.get(c, {}).get("gone") == 0 and c in hb and hb[c]["reproducing"] == 0]
    in_part = [c for c in fixed if nb.get(c, {}).get("gone", 0) > 0 and nb[c]["reproducing"] > 0]
    released = [c for c in fixed if nb.get(c, {}).get("reproducing") == 0]
    newest["upstream_fixed"] = {"total": len(fixed), "only_unreleased": len(unreleased),
                                "only_unreleased_list": ", ".join(unreleased) or "none",
                                "in_part": len(in_part), "in_part_list": ", ".join(in_part) or "none",
                                "gone_in_release": len(released), "gone_in_release_list": ", ".join(released) or "none"}
    return {"newest": newest,
            "first_newest": sweep_numbers(src, FIRST_NEWEST),
            "head": head,
            "lifecycle": lifecycle_numbers(fig["lifecycle"]),
            "over_time": over_time_numbers(bugs_over_time_author(src)),
            "upstream": upstream_numbers(src),
            "follow_up": follow_up_numbers(src)}


def follow_up_numbers(src: Sources) -> Dict[str, Any]:
    """The checks prompted by the maintainers' replies and by C11 (evidence/ts_wrapper_options.json, ts_quickfix_minimal.json,
    c8_vscode/result_*.json from scripts/paper/evidence/vscode_probe)."""
    rows = src.json(f"{RUN}/evidence/ts_wrapper_options.json")["rows"]
    c1 = [r for r in rows if r["case"] == "c1"]
    c2 = [r for r in rows if r["case"] == "c2"]
    mini = {r["kind"]: r for r in src.json(f"{RUN}/evidence/ts_quickfix_minimal.json")["rows"]}
    vscode = [src.json(f"{RUN}/evidence/c8_vscode/result_{v}.json") for v in ("default", "sqlite")]
    server = re.search(r"\d{4}-\d{2}-\d{2}", vscode[0]["server"])
    return {"c1_client_watcher": {"groups": len(c1), "reproduced_any": sum(1 for r in c1 if r["reproduced"] > 0),
                                  "replays": sum(r["replays"] for r in c1)},
            "c2_syntax_server_never": {"reproduced": sum(r["reproduced"] for r in c2), "replays": sum(r["replays"] for r in c2)},
            "c11_minimal": {"ts6_inserts_undefined": bool(mini.get("ts6", {}).get("inserts_undefined")),
                            "ts7_quick_fixes": len(mini.get("ts7", {}).get("quick_fixes") or [])},
            "c8_vscode": {"vscode": vscode[0]["vscode"], "extension": vscode[0]["extension"],
                          "server_date": server.group(0) if server else "", "runs": len(vscode),
                          "runs_same_answer": sum(1 for v in vscode if v["tested_route"] == vscode[0]["tested_route"]),
                          "tested_locations": len(vscode[0]["tested_route"]),
                          "reference_locations": len(vscode[0]["reference_route"])}}


def over_time_numbers(bot: Mapping[str, Any]) -> Dict[str, Any]:
    """Per oracle: run-hours, distinct bugs and bug groups, and the run-hours at which its last distinct bug came."""
    out: Dict[str, Any] = {}
    for key, v in bot.items():
        pts = v["points"]
        last = next((p["hours"] for p in pts if p["bugs"] == pts[-1]["bugs"]), 0.0) if pts[-1]["bugs"] else None
        out[key] = {"hours": round(v["hours"], 1), "bugs": pts[-1]["bugs"], "bug_groups": pts[-1]["bug_groups"],
                    "groups": pts[-1]["groups"], "last_bug_hours": round(last, 1) if last is not None else None}
        if "campaign_start_hours" in v:  # the joined campaigns: where each one began on the oracle's run-hours
            out[key]["campaign_start_hours"] = {c: round(h, 1) for c, h in v["campaign_start_hours"].items()}
    return out


UPSTREAM_STATUSES = ("fixed", "fix-planned", "confirmed", "investigating", "info-requested", "cause-confirmed", "disputed",
                     "no-reply", "not-reported")


def upstream_numbers(src: Sources) -> Dict[str, Any]:
    """The upstream reports and the maintainers' responses (runs/main_v1/upstream/feedback.csv; classes in its README).
    Every class gets a count, zero included, so that the text's macros survive a change of the responses."""
    rows = src.csv_rows(f"{RUN}/upstream/feedback.csv")
    unknown = sorted({r["status"] for r in rows} - set(UPSTREAM_STATUSES))
    if unknown:
        raise ValueError(f"feedback.csv: unknown status {unknown}")
    by = {s: sum(1 for r in rows if r["status"] == s) for s in UPSTREAM_STATUSES}
    reported = sum(1 for r in rows if r["status"] != "not-reported")
    taken = ("fixed", "fix-planned", "confirmed", "cause-confirmed", "disputed")  # a maintainer took a position
    return {"reported": reported, "responded": reported - by["no-reply"], "by_status": by,
            "position_taken": sum(by[st] for st in taken),
            "treated_as_defect": sum(by[st] for st in taken if st != "disputed"),
            "fixed_or_confirmed": by["fixed"] + by["fix-planned"] + by["confirmed"],
            "planned_or_confirmed": by["fix-planned"] + by["confirmed"],
            "as_of": max(r["as_of"] for r in rows)}


def write(path: str, data: Mapping[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


__all__ = ["bugs_over_time", "bugs_over_time_author", "figure_data", "lifecycle_numbers", "over_time_numbers",
           "release_numbers", "write"]
