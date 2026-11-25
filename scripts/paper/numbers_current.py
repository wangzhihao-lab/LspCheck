"""Numbers of the two current-release campaigns that the older sections (main, review, evidence) give for the first
campaign only: per campaign (keys added to the sections c1 and c2) and both together (keys added to cur).

Per campaign, with the same functions as the older sections:
- run_seconds: numbers_main.seconds_numbers (main.run_seconds); stable_filter: numbers_review.stable_filter;
  violations: numbers_main.violation_numbers (main.violations) plus filtered_pct = 100 * filtered / replayed;
  two_of_three: numbers_review.two_of_three; reduction: numbers_main.reduction_block (main.reduction);
  not_reconfirmed: reduced groups that did not reconfirm 3/3 (review.not_reconfirmed); unsettled_r1:
  numbers_review.unsettled_sessions (review.unsettled_r1);
- merge.mechanical: the mechanical merge rule of numbers_review.merge on the final bug groups;
- classes / artifact_classes: final legitimate / tool-artifact groups per exception class (L1-L7 / A1-A4), the class
  of the discussion for a discussed group, else the first author's (verdict_reasons.csv), as table G_groups does;
- evidence.c1_edit / c1_external: the replays of the groups whose root cause is C1 with the willRenameFiles edit
  applied and as a rename outside the editor (evidence/c1_rename_{edit,external}.json);
- sensitivity: bug groups per relation under the first author's, the second rater's and the final verdicts, and
  distinct bugs (root causes) per relation, all and only those with decisive independent evidence.

Both together (cur): the sums of the above (run_seconds and unstable_permille recomputed over all runs; the
mechanical merge over the union of both campaigns' bug groups, where a group id found in both counts once per
campaign; distinct bugs merged by cause identifier), root_causes.detail per cause, the independent evidence of
every cause (evidence_summary.csv of main_v1 for C1-C11, evidence_summary_v2.csv of main_v2 for C12-C35; the same
columns and rule as numbers_evidence) and the cost in hours: both campaigns' wall-clock hours, the benchmark
campaign's wall-clock hours and both campaigns' reduction compute hours; root_causes.lower_bound: the distinct bugs
left if every set of causes in data/lsptest/root_cause_possible_merges.csv (causes that could share a cause on
present evidence) is merged as well.

Reads, per campaign, the inputs of numbers_main.load_main, triage/root_causes.csv, triage/<gid>/repro.json of the
bug groups, evidence/c1_rename_{edit,external}.json and the evidence summary. Nothing is written.

Run line: not run directly; imported by scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

import numbers_final as nf
import numbers_review as nr
from numbers_campaigns import CAMPAIGNS, FIVE, RELATIONS, Campaign, cause_order
from numbers_io import Sources
from numbers_main import MainData, load_main, reduction_block, seconds_numbers, violation_numbers

logger = logging.getLogger(__name__)

RUNS = "data/lsptest/runs"
SUMMARIES: Tuple[Tuple[str, str], ...] = (("main_v1", "evidence/evidence_summary.csv"),
                                          ("main_v2", "evidence/evidence_summary_v2.csv"))
EVIDENCE: Tuple[str, ...] = ("decisive", "partial", "none")
LEGITIMATE_CLASSES: Tuple[str, ...] = ("L1", "L2", "L3", "L4", "L5", "L6", "L7")
ARTIFACT_CLASSES: Tuple[str, ...] = ("A1", "A2", "A3", "A4")
C1 = "C1"


def load_data(src: Sources, c: Campaign) -> MainData:
    """The campaign's inputs as numbers_main reads them (as numbers_tables_cur.load_batches does)."""
    run, corpus, prepared = CAMPAIGNS[c.key]
    return load_main(src, f"{RUNS}/{run}", corpus, prepared)


def load_evidence(src: Sources) -> Dict[str, Dict[str, str]]:
    """Cause -> its row of the evidence summaries (both campaigns).

    Raises:
        ValueError: when a cause is listed in both summaries.
    """
    out: Dict[str, Dict[str, str]] = {}
    gone = nf.load_withdrawn(src)
    for run, rel in SUMMARIES:
        for r in src.csv_rows(f"{RUNS}/{run}/{rel}"):
            if r["cause"] in gone:
                continue
            if r["cause"] in out:
                raise ValueError(f"cause {r['cause']} is in both evidence summaries")
            out[r["cause"]] = r
    return out


# ------------------------------------------------------------------ per campaign
def c1_replays(src: Sources, c: Campaign) -> Dict[str, Any]:
    """The rename replays of the campaign's C1 groups (only groups whose final cause is C1).

    Raises:
        ValueError: when a C1 group has no row in a replay file.
    """
    groups = sorted(g for g, row in c.causes.items() if row["cause"] == C1)
    out: Dict[str, Any] = {}
    for mode in ("edit", "external"):
        rel = f"{RUNS}/{c.run}/evidence/c1_rename_{mode}.json"
        by_gid = {r["gid"]: r for r in src.json(rel)["rows"]}
        missing = [g for g in groups if g not in by_gid]
        if missing:
            raise ValueError(f"{rel}: no row for the C1 group(s) {missing}")
        rows = [by_gid[g] for g in groups]
        not_restored = [r["gid"] for r in rows if not all(r.get("edited_restored", {}).values())]
        out[f"c1_{mode}"] = {"groups": len(rows),
                             "reproduced_any": sum(1 for r in rows if int(r["reproduced"]) > 0),
                             "reproduced_all": sum(1 for r in rows if r["verdict"] == "reproduced"),
                             "unsettled": sum(1 for r in rows if r["verdict"] == "unsettled"),
                             "all_restored": not not_restored, "not_restored_groups": len(not_restored),
                             "group_list": groups}
    return out


def class_counts(c: Campaign, d: MainData) -> Dict[str, Dict[str, int]]:
    """Final legitimate and tool-artifact groups per exception class (discussion's class, else the first author's).

    Raises:
        ValueError: when a non-bug group has no class.
    """
    legit = {k: 0 for k in LEGITIMATE_CLASSES}
    artifact = {k: 0 for k in ARTIFACT_CLASSES}
    missing: List[str] = []
    for gid, fin in c.verdicts.final.items():
        if fin.verdict == "bug":
            continue
        cls = fin.cls if fin.source in ("consensus", "rejudged") else d.reasons.get(gid, {}).get("class", "")
        if not cls:
            missing.append(gid)
            continue
        target = legit if fin.verdict == "legitimate" else artifact
        target[cls] = target.get(cls, 0) + 1
    if missing:
        raise ValueError(f"{c.run}: legitimate or tool-artifact group(s) without an exception class: {missing}")
    return {"classes": legit, "artifact_classes": artifact}


def relation_counts(gids: Iterable[str], relation: Mapping[str, str]) -> Dict[str, int]:
    sel = list(gids)
    out = {r: sum(1 for g in sel if relation[g] == r) for r in RELATIONS}
    out["total"] = len(sel)
    return out


def distinct_by_relation(pairs: Iterable[Tuple[str, str]], keep: Set[str]) -> Dict[str, int]:
    """(relation, cause) pairs of bug groups -> distinct causes per relation and in total, causes in keep only."""
    sel = {(r, c) for r, c in pairs if c in keep}
    out = {r: len({c for rr, c in sel if rr == r}) for r in RELATIONS}
    out["total"] = len({c for _, c in sel})
    return out


def sensitivity(campaigns: Sequence[Campaign], decisive: Set[str]) -> Dict[str, Any]:
    """Bug groups per relation under three sets of verdicts, and distinct bugs per relation (final verdicts)."""
    out: Dict[str, Any] = {"bug_groups": {}}
    for who in ("author", "rater2", "final"):
        total = {r: 0 for r in (*RELATIONS, "total")}
        for c in campaigns:
            relation = {i.gid: i.relation for i in c.items}
            if who == "final":
                bugs = [i.gid for i in c.items if i.verdict == "bug"]
            else:
                given = c.verdicts.author if who == "author" else c.verdicts.rater2
                bugs = [g for g in relation if given.get(g) == "bug"]
            for k, v in relation_counts(bugs, relation).items():
                total[k] += v
        out["bug_groups"][who] = total
    pairs = [(i.relation, i.cause) for c in campaigns for i in c.items if i.verdict == "bug"]
    every = {cause for _, cause in pairs}
    out["distinct"] = {"final": distinct_by_relation(pairs, every),
                       "decisive": distinct_by_relation(pairs, every & decisive)}
    return out


def campaign_extra(src: Sources, c: Campaign, d: MainData, decisive: Set[str]) -> Dict[str, Any]:
    """The keys this module adds to section c1 or c2."""
    viol = violation_numbers(d.violations)
    viol["filtered_pct"] = pct_int(viol["filtered"], viol["replayed"])
    red = reduction_block(d.groups, d.reductions)
    bug_rows = [dict(row, group=g) for g, row in c.causes.items()]
    notes = {g: str(src.json(f"{RUNS}/{c.run}/triage/{g}/repro.json").get("note", "")) for g in c.causes}
    out: Dict[str, Any] = {
        "run_seconds": seconds_numbers(d.results), "stable_filter": nr.stable_filter(d.results),
        "violations": viol, "two_of_three": nr.two_of_three(d.violations), "reduction": red,
        "not_reconfirmed": red["groups"] - int((red.get("reduced_confirmed") or {}).get("3/3", 0)),
        "merge": {"author": len({r["cause"] for r in bug_rows}),
                  "mechanical": len(nr.merge_keys(bug_rows, d.groups, notes))},
        "unsettled_r1": nr.unsettled_sessions(d.results),
        "evidence": c1_replays(src, c), "sensitivity": sensitivity([c], decisive)}
    out.update(class_counts(c, d))
    return out


def pct_int(num: int, den: int) -> Any:
    return round(100.0 * num / den) if den else None


# ------------------------------------------------------------------ both campaigns
def add(dicts: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Key-wise sum of numeric dicts (nested dicts summed recursively; a key missing in one counts as 0)."""
    out: Dict[str, Any] = {}
    for key in dict.fromkeys(k for d in dicts for k in d):
        vals = [d[key] for d in dicts if key in d]
        if all(isinstance(v, dict) for v in vals):
            out[key] = add(vals)
        elif all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
            out[key] = round(sum(vals), 4) if any(isinstance(v, float) for v in vals) else sum(vals)
    return out


def evidence_block(evidence: Mapping[str, Mapping[str, str]], causes: Sequence[str],
                   relations_of: Mapping[str, Set[str]]) -> Dict[str, Any]:
    """Independent evidence of every cause and of the causes the relations R1-R5 find (numbers_evidence's rule).

    Raises:
        ValueError: when the summaries do not list exactly the root causes, or give an unknown evidence value.
    """
    if set(evidence) != set(causes):
        raise ValueError(f"evidence summaries and root causes differ: no evidence row "
                         f"{sorted(set(causes) - set(evidence), key=cause_order)}, not a root cause "
                         f"{sorted(set(evidence) - set(causes), key=cause_order)}")
    bad = [c for c in causes if evidence[c]["independent"] not in EVIDENCE]
    if bad:
        raise ValueError(f"unknown independent-evidence value for {bad}")
    five = [c for c in causes if relations_of[c] & set(FIVE)]

    def tally(sel: Sequence[str]) -> Dict[str, int]:
        return {k: sum(1 for c in sel if evidence[c]["independent"] == k) for k in EVIDENCE}

    def related_none(sel: Sequence[str]) -> int:
        return sum(1 for c in sel if not evidence[c]["related_possible"].strip())

    out: Dict[str, Any] = {"independent": {**tally(causes), "causes": len(causes)}, "causes": len(five)}
    out.update(tally(five))
    out.update({f"{k}_list": ", ".join(c for c in five if evidence[c]["independent"] == k) for k in EVIDENCE})
    out["excluded_list"] = ", ".join(c for c in causes if c not in five)
    out["by_relation"] = {r: tally([c for c in causes if r in relations_of[c]]) for r in RELATIONS}
    out["related_none"] = related_none(five)
    out["related_none_all"] = related_none(causes)
    return out


def root_cause_detail(campaigns: Sequence[Campaign]) -> Dict[str, Dict[str, Any]]:
    """Per cause: bug groups in both campaigns and in each, server, and the relations of its groups."""
    out: Dict[str, Dict[str, Any]] = {}
    for c in campaigns:
        for i in c.items:
            if i.verdict != "bug":
                continue
            e = out.setdefault(i.cause, {"groups": 0, **{f"groups_{k.key}": 0 for k in campaigns},
                                         "server": c.causes[i.gid]["server"], "relations": set()})
            e["groups"] += 1
            e[f"groups_{c.key}"] += 1
            e["relations"].add(i.relation)
    for e in out.values():
        e["relation"] = ", ".join(sorted(e.pop("relations")))
    return dict(sorted(out.items(), key=lambda kv: cause_order(kv[0])))


POSSIBLE_MERGES = "data/lsptest/root_cause_possible_merges.csv"


def lower_bound(causes: Sequence[str], merges: Sequence[Sequence[str]]) -> int:
    """Distinct bugs left when each set in merges (causes that could share a cause) is merged into one.

    Raises:
        ValueError: if a set names a cause that is not in causes.
    """
    parent = {c: c for c in causes}

    def find(c: str) -> str:
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    for group in merges:
        unknown = [c for c in group if c not in parent]
        if unknown:
            raise ValueError(f"possible merge names unknown causes: {unknown}")
        for a, b in zip(group, group[1:]):
            parent[find(b)] = find(a)
    return len({find(c) for c in causes})


def current_extra(src: Sources, campaigns: Sequence[Campaign], data: Sequence[MainData],
                  per: Sequence[Mapping[str, Any]], bench_hours: float, campaign_hours: float) -> Dict[str, Any]:
    """The keys this module adds to section cur (per = the campaign_extra blocks, in the order of campaigns)."""
    results = [r for d in data for r in d.results]
    stable = nr.stable_filter(results)
    viol = add([p["violations"] for p in per])
    viol.pop("by_oracle_status", None)
    viol["filtered_pct"] = pct_int(viol["filtered"], viol["replayed"])
    red = add([p["reduction"] for p in per])
    red["compute_hours"] = round(red["compute_hours"], 2)
    red.pop("by_oracle", None)
    keys: Set[Tuple[str, str, str, str]] = set()
    for c, d in zip(campaigns, data):
        bug_rows = [dict(row, group=g) for g, row in c.causes.items()]
        notes = {g: str(src.json(f"{RUNS}/{c.run}/triage/{g}/repro.json").get("note", "")) for g in c.causes}
        # a group id is a campaign's own: groups of different campaigns merge only through their key
        keys |= nr.merge_keys(bug_rows, d.groups, notes)
    detail = root_cause_detail(campaigns)
    relations_of = {cause: set(e["relation"].split(", ")) for cause, e in detail.items()}
    evidence = load_evidence(src)
    decisive = {c for c, r in evidence.items() if r["independent"] == "decisive"}
    out: Dict[str, Any] = {
        "run_seconds": seconds_numbers(results), "stable_filter": stable, "violations": viol,
        "two_of_three": add([p["two_of_three"] for p in per]), "reduction": red,
        "not_reconfirmed": sum(p["not_reconfirmed"] for p in per),
        "merge": {"author": len(detail), "mechanical": len(keys)},
        "unsettled_r1": add([p["unsettled_r1"] for p in per]),
        "classes": add([p["classes"] for p in per]), "artifact_classes": add([p["artifact_classes"] for p in per]),
        "sensitivity": sensitivity(campaigns, decisive)}
    ev = evidence_block(evidence, list(detail), relations_of)
    ev.update({m: add([{k: v for k, v in p["evidence"][m].items() if k != "group_list"} for p in per])
               for m in ("c1_edit", "c1_external")})
    for m in ("c1_edit", "c1_external"):
        ev[m]["all_restored"] = all(p["evidence"][m]["all_restored"] for p in per)
    out["evidence"] = ev
    out["root_causes_detail"] = detail
    total = campaign_hours + bench_hours + red["compute_hours"]
    out["cost"] = {"campaign_hours": campaign_hours, "bench_hours": bench_hours,
                   "reduction_hours": red["compute_hours"], "total_hours": round(total, 2),
                   "total_days": round(total / 24, 1)}
    return out


def current_numbers(numbers: Dict[str, Any], src: Sources, campaigns: Sequence[Campaign]) -> None:
    """Add this module's keys to the sections c1, c2 and cur of numbers (which consensus_numbers filled)."""
    evidence = load_evidence(src)
    decisive = {c for c, r in evidence.items() if r["independent"] == "decisive"}
    data = [load_data(src, c) for c in campaigns]
    per = [campaign_extra(src, c, d, decisive) for c, d in zip(campaigns, data)]
    for c, p in zip(campaigns, per):
        numbers[c.key].update(p)
    cur = current_extra(src, campaigns, data, per, float(numbers["setup"]["bench_v1"]["wall_clock"]["hours"]),
                        float(numbers["cur"]["wall_clock_hours"]))
    numbers["cur"]["root_causes"]["detail"] = cur.pop("root_causes_detail")
    merges = [r["causes"].split() for r in src.csv_rows(POSSIBLE_MERGES)]
    numbers["cur"]["root_causes"]["lower_bound"] = lower_bound(list(numbers["cur"]["root_causes"]["detail"]), merges)
    numbers["cur"]["root_causes"]["possible_merge_sets"] = len(merges)
    # the same hours rounded to one decimal, as the text prints them
    one = lambda x: round(float(x), 1)  # noqa: E731
    cur["cost"].update({
        "run_hours": one(numbers["cur"]["run_hours"]["total"]), "wall_hours": one(numbers["cur"]["wall_clock_hours"]),
        **{f"wall_hours_{c.key}": one(numbers[c.key]["wall_clock_hours"]) for c in campaigns},
        "bench_run_hours": one(numbers["setup"]["bench_v1"]["run_hours"]),
        "bench_wall_hours": one(numbers["setup"]["bench_v1"]["wall_clock"]["hours"])})
    numbers["cur"].update(cur)


__all__ = ["add", "c1_replays", "campaign_extra", "class_counts", "current_extra", "current_numbers",
           "evidence_block", "load_evidence", "root_cause_detail", "sensitivity"]
