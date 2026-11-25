"""Numbers and appendix tables for the independent checks of the candidate bugs (plan/bug_evidence.md).

Reads the summary of the checks (data/lsptest/runs/main_v1/evidence/evidence_summary.csv: per cause,
whether a check outside the server exists, what it showed, and related tracker reports), the
component-isolation sweeps of the TypeScript causes (sweep/iso-ts<ts>-tsls<wrapper>/ and the year-old
sweep older-2025), the replays of the TypeScript history groups on the other TypeScript implementation (sweeps
ts6-groups-on-ts7 and ts7-groups-on-ts6, answers from evidence/cross_answers.py) and the tracker search
(evidence/dup_search.json). Returns the `evidence` section of paper_numbers.json and the tables
M2_isolation and M3_cross.

Run line: imported by scripts/paper/paper_numbers.py; not run directly.
"""

from __future__ import annotations

import collections
import os
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from numbers_io import Sources, counts, latest
from numbers_tables import Table

RUN = "data/lsptest/runs/main_v1"
SUMMARY = f"{RUN}/evidence/evidence_summary.csv"
DUP_SEARCH = f"{RUN}/evidence/dup_search.json"
YEAR_OLD = ("older-2025", "5.9.3", "5.0.0")
ISO = re.compile(r"^iso-ts(?P<ts>[\d.]+)-tsls(?P<wrapper>[\d.]+)$")
CAMPAIGN_PAIR = ("6.0.3", "6.0.0")  # TypeScript and typescript-language-server of the ts6 campaign
# The history groups of each TypeScript implementation replayed on the other one: (tested kind, sweep label,
# cross_answers.py output, name of the other build).
CROSS = (("ts6", "ts6-groups-on-ts7", "answers_ts6_on_ts7-7.0.2.json", "TS 7.0.2"),
         ("ts7", "ts7-groups-on-ts6", "answers_ts7_on_ts6-6.0.3.json", "TS 6.0.3"))


def exists(src: Sources, rel: str) -> bool:
    return os.path.exists(src.abspath(rel))


def cell(row: Optional[Mapping[str, Any]]) -> str:
    """'3/3' for a settled row, the verdict otherwise; '' when the group was not replayed."""
    if row is None:
        return ""
    if row["verdict"] in ("reproduced", "not-reproduced", "flaky"):
        return f"{row['reproduced']}/{row['replays']}"
    return row["verdict"]


def sweep_rows(src: Sources, label: str) -> Dict[str, Dict[str, Any]]:
    rel = f"{RUN}/sweep/{label}/results.jsonl"
    if not exists(src, rel):
        return {}
    return {r["gid"]: r for r in latest(src.jsonl(rel), "gid")}


def isolation_builds(src: Sources) -> List[Tuple[str, str, str]]:
    """(label, TypeScript, wrapper) of every isolation sweep, campaign pair last, then the year-old sweep."""
    builds = []
    for label in src.subdirs(f"{RUN}/sweep"):
        m = ISO.match(label)
        if m:
            builds.append((label, m["ts"], m["wrapper"]))
    builds.sort(key=lambda b: ((b[1], b[2]) == CAMPAIGN_PAIR, b[0]))
    return builds + [YEAR_OLD]


def build_name(label: str, ts: str, wrapper: str) -> str:
    """Column name of an isolation build: 'TS 6.0.3 + tsls 6.0.1', with the control and year-old ones marked."""
    name = f"TS {ts} + tsls {wrapper}"
    if (ts, wrapper) == CAMPAIGN_PAIR:
        return name + " (control)"
    return name + " (year-old)" if label == YEAR_OLD[0] else name


def isolation(src: Sources, causes: Mapping[str, str]) -> Tuple[Dict[str, Any], Table]:
    builds = isolation_builds(src)
    rows_by_label = {label: sweep_rows(src, label) for label, _, _ in builds}
    ts7 = sweep_rows(src, "ts6-groups-on-ts7")
    ts_groups = sorted((c, g) for g, c in causes.items() if g.startswith("ts6-"))
    per_cause: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    rows = []
    for cause, gid in ts_groups:
        cells = [cell(rows_by_label[label].get(gid)) for label, _, _ in builds]
        for label, _, _ in builds:
            r = rows_by_label[label].get(gid)
            per_cause[cause][r["verdict"] if r else "not_run"] += 1
        rows.append([cause, gid, *cells, cell(ts7.get(gid))])
    header = ["cause", "group"] + [build_name(*b) for b in builds] + ["TS 7.0.2"]
    pairs = sorted({(ts, w) for _, ts, w in builds})
    numbers = {"pairs": len(pairs), "typescript": sorted({ts for ts, _ in pairs}),
               "wrappers": sorted({w for _, w in pairs}),
               "by_cause": {c: dict(sorted(v.items())) for c, v in sorted(per_cause.items())},
               "cells": {c: sum(v.values()) for c, v in sorted(per_cause.items())}}
    for c, v in per_cause.items():
        numbers.setdefault("not_reproduced", {})[c] = v.get("not-reproduced", 0)
        numbers.setdefault("not_run", {})[c] = v.get("not_run", 0)
    # causes whose groups were replayed on every isolation build (a cause judged a bug later may have none)
    numbers["causes_run_on_all_builds"] = sum(1 for c, v in per_cause.items() if not v.get("not_run"))
    control = next((label for label, ts, w in builds if (ts, w) == CAMPAIGN_PAIR), None)
    if control:  # later replays with the campaign's own components: how often do the groups reproduce 3/3?
        cells = [r for r in (rows_by_label[control].get(gid) for _, gid in ts_groups) if r]
        numbers["control"] = {"groups": len(cells),
                              "reproduced": sum(1 for r in cells if r and r["verdict"] == "reproduced"),
                              "not_reproduced": sum(1 for r in cells if r and r["verdict"] == "not-reproduced")}
    title = "Component isolation of the TypeScript causes: reproduced replays out of three per group and build"
    return numbers, Table("M2_isolation", title, header, rows)


MISSING = ["missing-key"]  # the norm the frozen tool records when a session lacks the key


def answer_size(norm: Any) -> Optional[int]:
    """Entries of a normalized answer (items of a list, characters of a text); None when the key is missing."""
    if norm == MISSING or norm is None:
        return None
    return len(norm) if isinstance(norm, (list, str, dict)) else 1


def canonical(method: str, norm: Any) -> Any:
    """What two implementations are compared on: diagnostics by code and start line (the range and the
    message's wording of a type differ between TypeScript 6 and 7), semantic tokens by position and length
    (the two use different token types), every other answer as it is."""
    if not isinstance(norm, list) or norm == MISSING:
        return norm
    if method == "diagnostics":
        return sorted(collections.Counter((d[5], d[0]) for d in norm).items())
    if method == "semanticTokens":
        return [tuple(t[:3]) for t in norm]
    return norm


def repro_path(src: Sources, group: Mapping[str, Any]) -> str:
    """The group's representative repro.json: the reduced one when it exists (as the version sweep does)."""
    reduced = f"{RUN}/triage/{group['gid']}/repro.json"
    return reduced if exists(src, reduced) else f"{RUN}/violations/{group['representative']}/repro.json"


def cross_match(method: str, fresh: Any, history: Any, other_history: Any) -> str:
    """Which answer of the tested server the other implementation's answer after the history agrees with."""
    if not answer_size(other_history) and answer_size(fresh):
        return "no answer"
    other = canonical(method, other_history)
    if other == canonical(method, fresh):
        return "fresh"
    return "history" if other == canonical(method, history) else "neither"


def cross_section(src: Sources, verdicts: Mapping[str, str], causes: Mapping[str, str]
                  ) -> Tuple[Dict[str, Any], Table]:
    """Both directions of the cross-implementation replay: numbers per direction and table M3."""
    groups = {g["gid"]: g for g in src.json(f"{RUN}/triage/triage.json")["groups"]}
    numbers: Dict[str, Any] = {}
    rows = []
    for kind, label, answers_file, other_name in CROSS:
        sweep = sweep_rows(src, label)
        rel = f"{RUN}/evidence/{answers_file}"
        answers = {r["gid"]: r for r in src.json(rel)["rows"]} if exists(src, rel) else {}
        by_verdict: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        bug_match: collections.Counter = collections.Counter()
        for gid in sorted(sweep):
            r, verdict, a = sweep[gid], verdicts.get(gid, ""), answers.get(gid)
            by_verdict[verdict][r["verdict"]] += 1
            cells: List[Any] = ["", "", "", ""]
            if a and not a.get("error"):
                doc = src.json(repro_path(src, groups[gid]))
                match = cross_match(doc["key"]["method"], doc["expected"], doc["actual"], a["history"])
                if verdict == "bug":
                    bug_match[match] += 1
                cells = [answer_size(doc["expected"]), answer_size(doc["actual"]), answer_size(a["history"]), match]
            rows.append([gid, causes.get(gid, ""), verdict, other_name, cell(r)]
                        + ["missing" if c is None else c for c in cells])
        bug = by_verdict.get("bug", collections.Counter())
        numbers[f"{kind}_on_other"] = {
            "groups": len(sweep), "by_verdict": {k: dict(v) for k, v in sorted(by_verdict.items())},
            "bug_groups": sum(bug.values()), "bug_not_reproduced": bug.get("not-reproduced", 0),
            "artifact_groups": sum(by_verdict.get("tool-artifact", collections.Counter()).values()),
            "artifact_reproduced": by_verdict.get("tool-artifact", collections.Counter()).get("reproduced", 0),
            # Without the recorded answers the comparisons are unknown (printed as pending), not zero.
            "answers_checked": bool(answers), "bug_match": dict(sorted(bug_match.items())) if answers else None,
            "bug_matches_fresh": bug_match.get("fresh", 0) if answers else None,
            "bug_no_answer": bug_match.get("no answer", 0) if answers else None,
            "bug_matches_history": bug_match.get("history", 0) if answers else None}
    header = ["group", "cause", "verdict", "other implementation", "replays on it", "fresh n", "history n",
              "other history n", "other history agrees with"]
    title = ("The TypeScript history groups replayed on the other TypeScript implementation: the version sweep and "
             "one replay that records the other implementation's answer after the history")
    return numbers, Table("M3_cross", title, header, rows)


def evidence_numbers(src: Sources) -> Tuple[Optional[Dict[str, Any]], List[Table]]:
    """The `evidence` section and tables M2 and M3; (None, []) before the summary exists."""
    if not exists(src, SUMMARY):
        return None, []
    summary = src.csv_rows(SUMMARY)
    causes = {r["group"]: r["cause"] for r in src.csv_rows(f"{RUN}/triage/root_causes.csv")}
    verdicts = {r["group"]: r["verdict"] for r in src.csv_rows(f"{RUN}/triage/decisions.csv")}
    by_kind = counts(r["independent"] for r in summary)
    numbers: Dict[str, Any] = {
        "causes": len(summary),
        "independent": {k: by_kind.get(k, 0) for k in ("decisive", "partial", "none")},
        "independent_causes": {k: ", ".join(r["cause"] for r in summary if r["independent"] == k)
                               for k in ("decisive", "partial", "none")},
        "related_possible": sum(1 for r in summary if r["related_possible"].strip()),
        "related_possible_causes": ", ".join(r["cause"] for r in summary if r["related_possible"].strip()),
        "related_none": sum(1 for r in summary if not r["related_possible"].strip()),
    }
    if exists(src, DUP_SEARCH):
        dup = src.json(DUP_SEARCH)
        kept = {r["cause"] for r in summary}  # a cause the author later dropped keeps its search in the file
        searched = {c: v for c, v in dup["causes"].items() if c in kept}
        queries = [len(v["queries"]) for v in searched.values()]
        numbers["search"] = {"date": dup["date"], "causes": len(searched), "queries_min": min(queries),
                             "queries_max": max(queries), "hits_per_query": dup["per_query"],
                             "candidates": sum(len(v["candidates"]) for v in searched.values())}
    ck = f"{RUN}/evidence/contextual_keywords.json"
    if exists(src, ck):
        doc = src.json(ck)
        numbers["contextual_keywords"] = {"groups": len(doc["groups"]), "groups_checked": doc["groups_checked"],
                                          "tokens": ", ".join(sorted({g["token"] for g in doc["groups"]}))}
    iso_numbers, iso_table = isolation(src, causes)
    cross_numbers, cross_table = cross_section(src, verdicts, causes)
    numbers["isolation"], numbers["cross"] = iso_numbers, cross_numbers
    r2_numbers, r2_tables = round2_evidence(src, causes)
    numbers.update(r2_numbers)
    return numbers, [iso_table, cross_table] + r2_tables


__all__ = ["evidence_numbers", "rename_cell"]


def cause_order(cause: str) -> Tuple[int, str]:
    """C1, C2, ..., C10 in numeric order; unknown labels last."""
    m = re.fullmatch(r"C(\d+)", cause)
    return (int(m.group(1)), "") if m else (10**6, cause)


def rename_cell(row: Mapping[str, Any]) -> str:
    """k/n for a settled replay verdict (reproduced, not-reproduced, flaky); otherwise the verdict with the count,
    e.g. 'unsettled (2/3)' (numbers_tables_cur uses it for the second campaign's renames, too)."""
    count = f"{row['reproduced']}/{row['replays']}"
    return count if row["verdict"] in ("reproduced", "not-reproduced", "flaky") else f"{row['verdict']} ({count})"


def persistence_cell(first: Mapping[str, Any], extra: Optional[Mapping[str, Any]]) -> Tuple[int, int, str]:
    """(reproductions, replays, verdict of the first replay) of one group after one wait, retries included."""
    hits, n = int(first["reproduced"]), int(first.get("replays", 1))
    if extra:
        hits, n = hits + int(extra["reproduced"]), n + int(extra.get("replays", 1))
    return hits, n, first["verdict"]


def cell_text(hits: int, n: int, first_verdict: str) -> str:
    """yes/no for a single replay (or its verdict when it did not settle), k/n when retried."""
    if n > 1:
        return f"{hits}/{n}"
    return {"reproduced": "yes", "not-reproduced": "no"}.get(first_verdict, first_verdict)


def round2_evidence(src: Sources, causes: Mapping[str, str]) -> Tuple[Dict[str, Any], List[Table]]:
    """The checks added after the second internal review: C1 with the willRenameFiles edit applied and as
    a rename outside the editor (c1_rename_<mode>.json), the waits after the history (persistence.json),
    and the operations of C9's history (c9_trigger.json)."""
    numbers: Dict[str, Any] = {}
    per_group: Dict[str, Dict[str, str]] = {}
    for mode in ("edit", "external"):
        rel = f"{RUN}/evidence/c1_rename_{mode}.json"
        if not exists(src, rel):
            continue
        rows = src.json(rel)["rows"]
        numbers[f"c1_{mode}"] = {"groups": len(rows),
                                 "by_verdict": dict(sorted(counts(r["verdict"] for r in rows).items())),
                                 "reproduced_any": sum(1 for r in rows if r["reproduced"] > 0),
                                 "reproduced_all": sum(1 for r in rows if r["verdict"] == "reproduced"),
                                 "renames_with_edits": sum(1 for r in rows for x in r.get("renames", []) if x["edits"]),
                                 "renames": sum(len(r.get("renames", [])) for r in rows),
                                 "all_restored": all(all(r.get("edited_restored", {}).values()) for r in rows)}
        for r in rows:
            per_group.setdefault(r["gid"], {})[mode] = rename_cell(r)
    rel = f"{RUN}/evidence/persistence.json"
    if exists(src, rel):
        doc = src.json(rel)
        waits = [str(w) for w in doc["waits_s"]]
        rows = doc["rows"]
        retry_rel = f"{RUN}/evidence/persistence_retry.json"
        retry = {r["gid"]: r["by_wait"] for r in src.json(retry_rel)["rows"]} if exists(src, retry_rel) else {}
        cells = {r["gid"]: {w: persistence_cell(r["by_wait"][w], retry.get(r["gid"], {}).get(w)) for w in waits}
                 for r in rows}
        longest = waits[-1]
        numbers["persistence"] = {
            "groups": len(rows),
            "causes": len({causes.get(r["gid"], "") for r in rows}),
            "by_wait": {w: sum(1 for r in rows if r["by_wait"][w]["verdict"] == "reproduced") for w in waits},
            "reproduced_without_wait": sum(1 for r in rows if r["by_wait"]["0"]["verdict"] == "reproduced"),
            "still_after_longest": sum(1 for g in cells if cells[g][longest][0] > 0),
            "never_after_longest": sum(1 for g in cells if cells[g][longest][0] == 0),
            "retried_groups": len(retry),
            "retry_replays": sum(int(v.get("replays", 1)) for by_wait in retry.values() for v in by_wait.values()),
            "longest_wait_s": int(longest)}
        gone = [g for g in cells if cells[g][longest][0] == 0]
        if gone:  # the groups whose difference was not seen after the longest wait: how long did it last?
            numbers["persistence"]["gone_causes"] = ", ".join(sorted({causes.get(g, "") for g in gone}))
            numbers["persistence"]["gone_last_seen_s"] = min(
                max((int(w) for w in waits if cells[g][w][0] > 0), default=0) for g in gone)
        for gid, by_wait in cells.items():
            per_group.setdefault(gid, {}).update({f"wait {w} s": cell_text(*by_wait[w]) for w in waits})
    rel = f"{RUN}/evidence/c9_trigger.json"
    if exists(src, rel):
        rows = src.json(rel)["rows"]
        numbers["c9_trigger"] = {r["variant"]: f"{r['reproduced']}/{r['replays']}" for r in rows}
    tables: List[Table] = []
    if per_group:
        cols = ["edit", "external", "wait 0 s", "wait 5 s", "wait 30 s", "wait 60 s"]  # empty until the run exists
        rows_out = [[gid, causes.get(gid, "")] + [v.get(c, "") for c in cols]
                    for gid, v in sorted(per_group.items(), key=lambda kv: (cause_order(causes.get(kv[0], "")), kv[0]))]
        header = ["group", "cause", "rename edit applied", "rename outside the editor"] + \
                 [c.replace("wait ", "after ") for c in cols[2:]]
        tables.append(Table("M4_c1_checks", "The history bugs under a rename with the edit applied, a rename outside "
                            "the editor, and waits after the history", header, rows_out))
    return numbers, tables
