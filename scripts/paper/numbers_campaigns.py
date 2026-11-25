"""Numbers of the two current-release campaigns under the final verdicts: one section per campaign and the total.

c1 is main_v1 (the 10 most starred projects per language), c2 is main_v2 (ranks 11-20), both on the same frozen
tool and configuration. Per campaign (section c1 / c2): planned and recorded runs, run-hours and wall-clock
hours, confirmed signatures, groups by relation and by server, the final verdicts by relation, bug groups, the
five relations R1-R5, root causes (distinct bugs) by server and relation, projects and server versions. The
total (section cur): the same counts summed over both campaigns, root causes merged across the campaigns by
their identifier (C1, C2, ...: one numbering for both root_causes.csv files), the causes of the first campaign
only, of the second only and of both, per relation the causes it finds, those only it finds and its run-hours
per cause, and the baselines of RQ2 (cur.baseline): the crash check R0, the cross-implementation comparison R6
and the failing-request observer (a bug group whose signature shows a request that fails in one session and not
in the other; the regular expression of numbers_review.error_oracle), the causes each finds and the causes the
relations find that no baseline finds. The observer counts a failing request in the sessions of any check, R0
included, as numbers_review.error_oracle does on the benchmark; failing_request_five counts only the sessions of
R1-R5.

Verdicts come from numbers_final (consensus, else both raters' verdict). Reads per campaign
data/lsptest/runs/<campaign>/: config.json, results.jsonl, violations.jsonl, triage/triage.json, the three
verdict files of numbers_final, and triage/root_causes.csv, which must list exactly the final bug groups (a
missing file or a mismatch stops the computation); the corpus files named in CAMPAIGNS. Nothing is written.

Run line: not run directly; imported by scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from numbers_final import GroupVerdicts, load_group_verdicts
from numbers_io import Sources, latest, planned_runs, split_signature
from numbers_review import FAILING_REQUEST_RE

logger = logging.getLogger(__name__)

RUNS = "data/lsptest/runs"
# section key -> (run directory, corpus selection file, prepared corpus file named in the campaign's config)
CAMPAIGNS: Dict[str, Tuple[str, str, str]] = {
    "c1": ("main_v1", "data/lsptest/corpus.json", "data/lsptest/corpus_prepared.json"),
    "c2": ("main_v2", "data/lsptest/corpus_v2.json", "data/lsptest/corpus_v2_prepared.json")}
RELATIONS: Tuple[str, ...] = ("R0", "R1", "R2", "R3", "R4", "R5", "R6")
FIVE: Tuple[str, ...] = ("R1", "R2", "R3", "R4", "R5")  # the relations; R0 and R6 are baselines
VERDICTS: Tuple[str, ...] = ("bug", "legitimate", "tool-artifact")
ORACLE_RELATION = {"r0_crash": "R0", "r1_history": "R1", "r2_handles": "R2", "r3_routes": "R3", "r4_edits": "R4",
                   "r5_transforms": "R5", "r6_crossimpl": "R6"}
SERVERS: Tuple[str, ...] = ("gopls", "pyright", "rust-analyzer", "ts6", "ts7")


@dataclass(frozen=True)
class Item:
    """One finding group of one campaign with its final verdict and, for a bug group, its root cause."""

    campaign: str      # section key, c1 or c2
    gid: str
    relation: str      # R0 .. R6
    server: str        # server kind, the first field of the signature
    verdict: str
    cause: str         # "" unless verdict == "bug"
    failing: bool      # the signature shows a request failing in one session and not in the other


@dataclass(frozen=True)
class Campaign:
    """Inputs of one current-release campaign."""

    key: str
    run: str
    config: Dict[str, Any]
    results: List[Dict[str, Any]]
    violations: List[Dict[str, Any]]
    planned: List[Dict[str, Any]]
    groups: List[Dict[str, Any]]
    verdicts: GroupVerdicts
    causes: Dict[str, Dict[str, str]]   # bug group -> its root_causes.csv row
    corpus: Dict[str, Any]
    items: List[Item]


def relation_of(signature: str) -> str:
    return ORACLE_RELATION.get(split_signature(signature)[1], "?")


def check_causes(final_bugs: Iterable[str], rows: Sequence[Mapping[str, str]], rel: str) -> Dict[str, Dict[str, str]]:
    """Bug group -> its root-cause row; the rows must list each final bug group exactly once and nothing else.

    Raises:
        ValueError: naming the bug groups without a cause, the rows for groups that are not bugs and repeated groups.
    """
    bugs = set(final_bugs)
    out: Dict[str, Dict[str, str]] = {}
    repeated = sorted({r["group"] for r in rows if sum(1 for x in rows if x["group"] == r["group"]) > 1})
    for r in rows:
        out[r["group"]] = dict(r)
    missing, extra = sorted(bugs - set(out)), sorted(set(out) - bugs)
    if missing or extra or repeated:
        raise ValueError(f"{rel} does not match the final bug groups: without a cause {missing}; "
                         f"not a bug under the final verdicts {extra}; listed twice {repeated}")
    return out


def load_campaign(src: Sources, key: str) -> Campaign:
    """Read one campaign (key c1 or c2) and attach the final verdict and root cause to every group.

    Raises:
        FileNotFoundError: when triage/root_causes.csv (or another input) is missing.
        ValueError: when root_causes.csv does not list exactly the final bug groups, or the config names
            another corpus.
        numbers_final.VerdictConflict: when a group has no final verdict.
    """
    run, corpus_rel, prepared_rel = CAMPAIGNS[key]
    rdir = f"{RUNS}/{run}"
    config = src.json(f"{rdir}/config.json")
    if config["config"].get("corpus") != prepared_rel:
        raise ValueError(f"{rdir}/config.json names corpus {config['config'].get('corpus')!r}, not {prepared_rel!r}")
    groups = list(src.json(f"{rdir}/triage/triage.json")["groups"])
    verdicts = load_group_verdicts(src, run)
    bugs = [g for g, f in verdicts.final.items() if f.verdict == "bug"]
    root_rel = f"{rdir}/triage/root_causes.csv"
    causes = check_causes(bugs, src.csv_rows(root_rel), root_rel)
    items = [Item(key, str(g["gid"]), relation_of(g["signature"]), split_signature(g["signature"])[0],
                  verdicts.final[g["gid"]].verdict, causes.get(g["gid"], {}).get("cause", ""),
                  bool(FAILING_REQUEST_RE.search(split_signature(g["signature"])[2])))
             for g in groups]
    return Campaign(key=key, run=run, config=config, results=latest(src.jsonl(f"{rdir}/results.jsonl"), "run_id"),
                    violations=latest(src.jsonl(f"{rdir}/violations.jsonl"), "vid"),
                    planned=planned_runs(config, src, rdir), groups=groups, verdicts=verdicts, causes=causes,
                    corpus=src.json(corpus_rel), items=items)


# ------------------------------------------------------------------ counting helpers
def by_relation(items: Iterable[Item]) -> Dict[str, int]:
    """Items per relation, every relation listed (zeros included)."""
    sel = list(items)
    return {r: sum(1 for i in sel if i.relation == r) for r in RELATIONS}


def by_server(items: Iterable[Item]) -> Dict[str, int]:
    sel = list(items)
    return {s: sum(1 for i in sel if i.server == s) for s in SERVERS}


def pct(num: int, den: int) -> Optional[float]:
    return round(100.0 * num / den, 1) if den else None


def run_hours_by_relation(results: Iterable[Mapping[str, Any]]) -> Dict[str, float]:
    """Run-hours (wall seconds of every run, all statuses) per relation; four decimals, rounded where reported."""
    out = {r: 0.0 for r in RELATIONS}
    for r in results:
        if r.get("wall_seconds") is not None:
            out[ORACLE_RELATION[str(r["oracle"])]] += float(r["wall_seconds"]) / 3600
    return {r: round(h, 4) for r, h in out.items()}


def wall_clock_hours(config: Mapping[str, Any], results: Sequence[Mapping[str, Any]]) -> float:
    """Hours the campaign's invocations ran, as the harness measured them (config.json invocations, elapsed_s).

    The harness's clock does not advance while the machine sleeps (main_v2 slept twice, plan/main_v2_run_notes.md),
    so this is the time the laptop was busy; for main_v1, which did not sleep, it equals the span of the runs.

    Raises:
        ValueError: when the invocations' run counts do not add up to the recorded runs.
    """
    invocations = config.get("invocations") or []
    if sum(int(inv.get("runs") or 0) for inv in invocations) != len(results):
        raise ValueError(f"invocations list {sum(int(inv.get('runs') or 0) for inv in invocations)} runs, "
                         f"results.jsonl {len(results)}")
    return round(sum(float(inv["elapsed_s"]) for inv in invocations) / 3600, 2)


def cause_summary(items: Sequence[Item]) -> Dict[str, Any]:
    """Distinct causes of the bug items: total, list, per server and per relation (a cause counts for every
    relation that has one of its bug groups)."""
    bugs = [i for i in items if i.verdict == "bug"]
    causes = sorted({i.cause for i in bugs}, key=cause_order)
    server = {c: next(i.server for i in bugs if i.cause == c) for c in causes}
    return {"total": len(causes), "list": ", ".join(causes),
            "by_server": {s: sum(1 for c in causes if server[c] == s) for s in SERVERS},
            "by_relation": {r: len({i.cause for i in bugs if i.relation == r}) for r in RELATIONS}}


def cause_order(cause: str) -> Tuple[int, str]:
    """C1, C2, ..., C10 in numeric order; other labels last."""
    digits = cause[1:]
    return (int(digits), "") if cause[:1] == "C" and digits.isdigit() else (10**6, cause)


def verdict_counts(items: Sequence[Item]) -> Dict[str, Any]:
    by_rel = {r: {v: sum(1 for i in items if i.relation == r and i.verdict == v) for v in VERDICTS}
              for r in RELATIONS}
    return {"by_verdict": {v: sum(1 for i in items if i.verdict == v) for v in VERDICTS}, "by_relation": by_rel}


def group_block(items: Sequence[Item]) -> Dict[str, Any]:
    """Groups, verdicts, bug groups, the five relations and precision of a set of items."""
    bugs = [i for i in items if i.verdict == "bug"]
    five = [i for i in items if i.relation in FIVE]
    five_bugs = [i for i in five if i.verdict == "bug"]
    rel_groups, rel_bugs = by_relation(items), by_relation(bugs)
    return {"groups": {"total": len(items), "by_relation": rel_groups, "by_server": by_server(items)},
            "verdicts": verdict_counts(items),
            "bug_groups": {"total": len(bugs), "by_relation": rel_bugs, "by_server": by_server(bugs)},
            "five_relations": {"groups": len(five), "bugs": len(five_bugs),
                               "precision_pct": pct(len(five_bugs), len(five))},
            "precision_pct": pct(len(bugs), len(items)),
            "precision_by_relation_pct": {r: pct(rel_bugs[r], rel_groups[r]) for r in RELATIONS if rel_groups[r]}}


# ------------------------------------------------------------------ per campaign
def corpus_block(c: Campaign) -> Dict[str, Any]:
    by_language = {lang: len(repos) for lang, repos in sorted(c.corpus["corpus"].items())}
    tested = sorted({str(s["project"]) for s in c.planned})
    return {"projects": sum(by_language.values()), "projects_by_language": by_language,
            "projects_tested": len(tested), "pairs": len(c.config.get("eligible_pairs") or []),
            "excluded_pairs": len(c.config.get("excluded_pairs") or []),
            "selection_cutoff": c.corpus.get("cutoff"), "selected_on": c.corpus.get("selected_on")}


def campaign_section(c: Campaign) -> Dict[str, Any]:
    """Section c1 or c2 (see the module docstring)."""
    statuses: Dict[str, int] = {}
    for r in c.results:
        statuses[str(r["status"])] = statuses.get(str(r["status"]), 0) + 1
    hours = run_hours_by_relation(c.results)
    confirmed = {str(v["signature"]) for v in c.violations if v["status"] == "confirmed"}
    out: Dict[str, Any] = {
        "campaign": c.run,
        "runs": {"planned": len(c.planned), "recorded": len(c.results), "ok": statuses.get("ok", 0),
                 "by_status": dict(sorted(statuses.items())),
                 "planned_by_relation": {r: sum(1 for s in c.planned if ORACLE_RELATION[str(s["oracle"])] == r)
                                         for r in RELATIONS}},
        "run_hours": {"total": round(sum(hours.values()), 2),
                      "by_relation": {r: round(h, 2) for r, h in hours.items()}},
        "wall_clock_hours": wall_clock_hours(c.config, c.results),
        "confirmed_signatures": len(confirmed)}
    out.update(group_block(c.items))
    out["verdicts"]["from_consensus"] = sum(1 for f in c.verdicts.final.values() if f.source in ("consensus", "rejudged"))
    out["verdicts"]["rejudged"] = sum(1 for f in c.verdicts.final.values() if f.source == "rejudged")
    out["root_causes"] = cause_summary(c.items)
    out["corpus"] = corpus_block(c)
    out["servers"] = {str(b["kind"]): {"version": b.get("version", ""), "package_version": b.get("package_version", ""),
                                       "label": b.get("label", "")} for b in c.config.get("server_builds") or []}
    return out


# ------------------------------------------------------------------ both campaigns
def merge_causes(causes_by_campaign: Mapping[str, Mapping[str, Mapping[str, str]]]) -> Dict[str, Dict[str, Any]]:
    """Cause id -> server, trigger and the campaigns it occurs in, merged across the campaigns by identifier.

    Args:
        causes_by_campaign: campaign key -> (bug group -> its root_causes.csv row).

    Raises:
        ValueError: when one identifier names causes of different servers.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for key, causes in causes_by_campaign.items():
        for gid, row in causes.items():
            e = out.setdefault(row["cause"], {"server": row["server"], "trigger": row["trigger"], "campaigns": set()})
            if e["server"] != row["server"]:
                raise ValueError(f"cause {row['cause']} is {e['server']} in one campaign and {row['server']} "
                                 f"in {key} (group {gid})")
            if e["trigger"] != row["trigger"]:
                logger.warning("cause %s: trigger %r in %s differs from %r", row["cause"], row["trigger"], key,
                               e["trigger"])
            e["campaigns"].add(key)
    return dict(sorted(out.items(), key=lambda kv: cause_order(kv[0])))


def overlap_block(merged: Mapping[str, Mapping[str, Any]], keys: Sequence[str]) -> Dict[str, Any]:
    """Causes found in the first campaign only, the second only and both (two campaigns)."""
    first, second = keys
    def pick(want: Set[str]) -> List[str]:
        return [c for c, e in merged.items() if e["campaigns"] == want]
    only1, only2, both = pick({first}), pick({second}), pick({first, second})
    return {"first_only": len(only1), "second_only": len(only2), "both": len(both),
            "first_only_list": ", ".join(only1), "second_only_list": ", ".join(only2), "both_list": ", ".join(both)}


def relation_causes(items: Sequence[Item], hours: Mapping[str, float]) -> Dict[str, Any]:
    """Per relation: causes with a bug group of the relation, causes no other relation (R0-R6) finds, and
    run-hours per cause (relations without a cause are left out of hours_per_bug)."""
    bugs = [i for i in items if i.verdict == "bug"]
    found = {r: {i.cause for i in bugs if i.relation == r} for r in RELATIONS}
    only = {r: {c for c in found[r] if all(c not in found[o] for o in RELATIONS if o != r)} for r in RELATIONS}
    return {"by_relation": {r: len(found[r]) for r in RELATIONS},
            "only_relation": {r: len(only[r]) for r in RELATIONS},
            "hours_per_bug": {r: round(hours[r] / len(found[r]), 1) for r in RELATIONS if found[r]}}


def baseline_section(items: Sequence[Item]) -> Dict[str, Any]:
    """RQ2 on the current releases: what the crash check (R0), the cross-implementation comparison (R6) and the
    failing-request observer report, and the causes the relations R1-R5 find that none of them finds."""
    bugs = [i for i in items if i.verdict == "bug"]

    def block(sel_all: Sequence[Item]) -> Dict[str, Any]:
        sel_bugs = [i for i in sel_all if i.verdict == "bug"]
        causes = sorted({i.cause for i in sel_bugs}, key=cause_order)
        return {"groups": len(sel_all), "bug_groups": len(sel_bugs), "causes": len(causes),
                "cause_list": ", ".join(causes)}

    crash = block([i for i in items if i.relation == "R0"])
    cross = block([i for i in items if i.relation == "R6"])
    failing = block([i for i in items if i.failing])
    failing_five = block([i for i in items if i.failing and i.relation in FIVE])  # the observer on R1-R5 sessions only
    baseline = {c for b in (crash, cross, failing) for c in b["cause_list"].split(", ") if c}
    relations = {i.cause for i in bugs if i.relation in FIVE}
    only = sorted(relations - baseline, key=cause_order)
    shared = sorted(relations & baseline, key=cause_order)
    return {"crash": crash, "cross_impl": cross, "failing_request": failing, "failing_request_five": failing_five,
            "any": {"causes": len(baseline), "cause_list": ", ".join(sorted(baseline, key=cause_order))},
            "relations": {"causes": len(relations)},
            "relations_only": {"causes": len(only), "also_baseline": len(shared),
                               "also_baseline_list": ", ".join(shared)}}


def current_section(campaigns: Sequence[Campaign]) -> Dict[str, Any]:
    """Section cur: both campaigns together (see the module docstring)."""
    items = [i for c in campaigns for i in c.items]
    hours = {r: 0.0 for r in RELATIONS}
    for c in campaigns:
        for r, h in run_hours_by_relation(c.results).items():
            hours[r] += h
    repos = {str(r["repo"]) for c in campaigns for repos_ in c.corpus["corpus"].values() for r in repos_}
    out: Dict[str, Any] = {
        "campaigns": len(campaigns),
        "runs": {"planned": sum(len(c.planned) for c in campaigns), "recorded": sum(len(c.results) for c in campaigns),
                 "ok": sum(1 for c in campaigns for r in c.results if r["status"] == "ok")},
        "run_hours": {"total": round(sum(hours.values()), 2),
                      "by_relation": {r: round(h, 2) for r, h in hours.items()}},
        "wall_clock_hours": round(sum(wall_clock_hours(c.config, c.results) for c in campaigns), 2),
        "projects": sum(corpus_block(c)["projects"] for c in campaigns),
        "projects_distinct": len(repos),
        "projects_tested": sum(corpus_block(c)["projects_tested"] for c in campaigns),
        "pairs": sum(corpus_block(c)["pairs"] for c in campaigns)}
    out.update(group_block(items))
    merged = merge_causes({c.key: c.causes for c in campaigns})
    causes = cause_summary(items)
    if causes["total"] != len(merged):
        raise ValueError(f"{causes['total']} causes among the bug groups, {len(merged)} after merging by identifier")
    causes.update(overlap_block(merged, [c.key for c in campaigns]) if len(campaigns) == 2 else {})
    causes.update(relation_causes(items, hours))
    out["root_causes"] = causes
    out["baseline"] = baseline_section(items)
    return out


__all__ = ["CAMPAIGNS", "Campaign", "Item", "baseline_section", "campaign_section", "cause_summary", "check_causes",
           "current_section", "load_campaign", "merge_causes", "overlap_block", "relation_causes"]
