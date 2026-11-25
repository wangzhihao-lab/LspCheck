"""Release replays of the distinct bugs of both current-release campaigns, and the appendix tables that list them.

Adds to section cur of paper_numbers.json (final bug groups and root causes of numbers_campaigns.load_campaign):
- cur.newest: every final bug group of both campaigns replayed on the newest releases of 2026-11-18 (each campaign's
  sweep/newest-2026-11-18), counted as numbers_figures.sweep_numbers counts the first campaign (release.newest):
  groups reproduced in all, some or none of their three replays, causes with a group reproduced in all three,
  by_cause, the date and releases, and upstream_fixed (the fixed reports of main_v1/upstream/feedback.csv, with the
  gopls development head of main_v1); relations.* the same over the causes found by R1-R5 (all causes but the crash
  check's). The last row of a group counts; a group without a row (its replay has not run yet) is left out and logged.
- cur.lifecycle: numbers_figures.lifecycle_numbers over lifecycle_cur (older_than_year: causes whose representative
  reproduces on a release at least 12 months older than the campaign's release), and relations.{causes,
  older_than_year} over the causes found by R1-R5.
- cur.persistence: the waits after the history, with the keys and rule of evidence.persistence
  (numbers_evidence.round2_evidence), over the final bug groups of relation R1 of both campaigns, from
  main_v1/evidence/persistence.json, main_v1/evidence/persistence_new.json and main_v2/evidence/persistence.json; a
  campaign's evidence/persistence_retry.json adds its replays to that campaign's groups. A file that does not exist
  yet is skipped with a warning; rows of groups that are not final R1 bug groups are left out.

lifecycle_cur (figure_data.json, key lifecycle_cur): per cause, numbers_figures.lifecycle of the campaign whose
sweep/lifecycle/releases.json holds the cause's representative group, with the campaign and corpus added. The
representatives are checked against release_builds.REP_RULE: C1-C11 the first sweep's groups (main_v1), a later cause
the first row that lists it in the first root-cause table that does (main_v1 before main_v2).

Tables (paper/appendix/tables): N1_lifecycle (lifecycle_cur), N2_newest (both campaigns' newest-release replays, then
the gopls development head of main_v1), N3_upstream (main_v1/upstream/feedback.csv), G2_root_causes (both root-cause
tables, one row per cause and group, the group marked with its corpus; server, trigger and description from the first
table that lists the cause) and M_evidence (evidence_summary.csv of main_v1 and evidence_summary_v2.csv of main_v2).

Run line: not run directly; imported by scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from numbers_campaigns import FIVE, Campaign, cause_order
from numbers_current import load_evidence
from numbers_evidence import persistence_cell
from numbers_final import load_withdrawn
from numbers_figures import HEAD, NEWEST, lifecycle, lifecycle_numbers, replay_state, sweep_numbers
from numbers_io import Sources
from numbers_tables import Table

logger = logging.getLogger(__name__)

RUNS = "data/lsptest/runs"
FIRST_RUN = "main_v1"
CORPUS = {"main_v1": "first", "main_v2": "second"}
FIRST_SWEEP = tuple(f"C{i}" for i in range(1, 12))  # release_builds.REPS: representatives chosen for the first sweep
FEEDBACK = f"{RUNS}/main_v1/upstream/feedback.csv"
PERSISTENCE: Tuple[Tuple[str, str], ...] = (("main_v1", "persistence.json"), ("main_v1", "persistence_new.json"),
                                            ("main_v2", "persistence.json"))
RETRY = "persistence_retry.json"
HIT = ("reproduced", "partly")
READING = {"reproduced": "reproduces", "partly": "partly", "not-reproduced": "does not reproduce",
           "n/a": "could not be judged"}


def exists(src: Sources, rel: str) -> bool:
    return os.path.exists(src.abspath(rel))


def ordered(causes: Iterable[str]) -> List[str]:
    return sorted(causes, key=cause_order)


def cause_relations(campaigns: Sequence[Campaign]) -> Dict[str, Set[str]]:
    """Cause -> the relations of its final bug groups in both campaigns."""
    out: Dict[str, Set[str]] = {}
    for c in campaigns:
        for i in c.items:
            if i.verdict == "bug":
                out.setdefault(i.cause, set()).add(i.relation)
    return out


def relation_causes(rel_of: Mapping[str, Set[str]]) -> Set[str]:
    """The causes found by the relations R1-R5 (a bug group under one of them)."""
    return {c for c, rels in rel_of.items() if rels & set(FIVE)}


# ------------------------------------------------------------------ newest releases
def replay_rows(src: Sources, campaigns: Sequence[Campaign], label: str,
                warn_missing: bool = True) -> Tuple[List[Tuple[str, str, Dict[str, Any]]], List[Dict[str, Any]]]:
    """(campaign run, cause, row) of the final bug groups in the label's results of each campaign (file order, the last
    row of a group), and the label's plans (releases.json). A campaign without the label is skipped.
    """
    out: List[Tuple[str, str, Dict[str, Any]]] = []
    plans: List[Dict[str, Any]] = []
    for c in campaigns:
        base = f"{RUNS}/{c.run}/sweep/{label}"
        if not exists(src, f"{base}/results.jsonl"):
            logger.warning("%s/results.jsonl does not exist; its groups are not counted", base)
            continue
        plans.append(src.json(f"{base}/releases.json"))
        rows = [r for r in src.jsonl(f"{base}/results.jsonl") if r["gid"] in c.causes]
        last: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            last[r["gid"]] = r
        if len(last) < len(rows):
            logger.warning("%s: %d repeated rows; the last row of each group counts", base, len(rows) - len(last))
        missing = sorted(set(c.causes) - set(last))
        if missing and warn_missing:
            logger.warning("%s: %d of %d bug groups have no row yet (first: %s)", base, len(missing), len(c.causes),
                           ", ".join(missing[:3]))
        out += [(c.run, c.causes[g]["cause"], r) for g, r in last.items()]
    return out, plans


def replay_counts(rows: Sequence[Tuple[str, Mapping[str, Any]]]) -> Dict[str, Any]:
    """numbers_figures.sweep_numbers' counts of (cause, row) pairs: groups by replay state, causes with a reproducing
    group, with a group reproduced in all three replays, with every group gone, and per cause."""
    states = [(cause, r, replay_state(r)) for cause, r in rows]
    by_cause: Dict[str, List[str]] = {}
    for cause, _, st in states:
        by_cause.setdefault(cause, []).append(st)
    gone = ordered(c for c, sts in by_cause.items() if all(st == "not-reproduced" for st in sts))
    part = ordered(c for c, sts in by_cause.items() if "not-reproduced" in sts and any(st in HIT for st in sts))
    return {"groups": len(states),
            "reproduced_all": sum(1 for _, _, st in states if st == "reproduced"),
            "reproduced_some": sum(1 for _, _, st in states if st == "partly"),
            "not_reproduced": sum(1 for _, _, st in states if st == "not-reproduced"),
            "not_judged": sum(1 for _, _, st in states if st == "n/a"),
            "errors": sum(1 for _, r, _ in states if r.get("error")),
            "causes_partly_gone": len(part), "causes_partly_gone_list": ", ".join(part) or "none",
            "causes": len(by_cause),
            "causes_reproduced": sum(1 for sts in by_cause.values() if any(st in HIT for st in sts)),
            "causes_reproduced_all": sum(1 for sts in by_cause.values() if "reproduced" in sts),
            "causes_not_reproduced": len(gone), "causes_not_reproduced_list": ", ".join(gone) or "none",
            "causes_reproduced_list": ", ".join(ordered(c for c, sts in by_cause.items()
                                                        if any(st in HIT for st in sts))) or "none",
            "by_cause": {c: {"groups": len(by_cause[c]),
                             "reproducing": sum(1 for st in by_cause[c] if st in HIT),
                             "gone": sum(1 for st in by_cause[c] if st == "not-reproduced")}
                         for c in ordered(by_cause)}}


def upstream_fixed(src: Sources, nb: Mapping[str, Mapping[str, int]]) -> Dict[str, Any]:
    """The fixed upstream reports (C1-C10, feedback.csv): fixed only on the gopls development head, fixed in part on
    the newest release, gone on it (numbers_figures.release_numbers' rule, by_cause nb of both campaigns)."""
    hb = sweep_numbers(src, HEAD)["by_cause"]
    fixed = [r["cause"] for r in src.csv_rows(FEEDBACK) if r["status"] == "fixed"]
    unreleased = [c for c in fixed if nb.get(c, {}).get("gone") == 0 and c in hb and hb[c]["reproducing"] == 0]
    in_part = [c for c in fixed if nb.get(c, {}).get("gone", 0) > 0 and nb[c]["reproducing"] > 0]
    released = [c for c in fixed if nb.get(c, {}).get("reproducing") == 0]
    return {"total": len(fixed), "only_unreleased": len(unreleased),
            "only_unreleased_list": ", ".join(unreleased) or "none",
            "in_part": len(in_part), "in_part_list": ", ".join(in_part) or "none",
            "gone_in_release": len(released), "gone_in_release_list": ", ".join(released) or "none"}


def newest_cur(src: Sources, campaigns: Sequence[Campaign], rel_of: Mapping[str, Set[str]]) -> Dict[str, Any]:
    """cur.newest: both campaigns' final bug groups on the newest releases (NEWEST).

    Raises:
        ValueError: when the campaigns' plans have different dates or different releases of a shared line.
    """
    rows, plans = replay_rows(src, campaigns, NEWEST)
    out = replay_counts([(cause, r) for _, cause, r in rows])
    dates = sorted({str(p.get("as_of", "")) for p in plans})
    if len(dates) > 1:
        raise ValueError(f"{NEWEST}: the campaigns' plans have different dates {dates}")
    releases: Dict[str, str] = {}
    for p in plans:
        for b in p["builds"]:
            if b.get("status") != "ok":
                continue
            if releases.setdefault(b["line"], b["release"]) != b["release"]:
                raise ValueError(f"{NEWEST}: line {b['line']} has releases {releases[b['line']]} and {b['release']}")
    out["date"] = dates[0] if dates else ""
    out["releases"] = dict(sorted(releases.items()))
    five = relation_causes(rel_of)
    rel = replay_counts([(cause, r) for _, cause, r in rows if cause in five])
    out["relations"] = {k: rel[k] for k in ("groups", "causes", "causes_reproduced", "causes_reproduced_all",
                                            "causes_not_reproduced", "causes_not_reproduced_list")}
    out["upstream_fixed"] = upstream_fixed(src, out["by_cause"])
    return out


# ------------------------------------------------------------------ lifecycle
def rule_representatives(src: Sources, campaigns: Sequence[Campaign]) -> Dict[str, Tuple[str, str]]:
    """Cause -> (campaign run, group) by REP_RULE for the causes after the first sweep: the first row that lists the
    cause in the first root-cause table that does (campaign order)."""
    out: Dict[str, Tuple[str, str]] = {}
    for c in campaigns:
        for row in src.csv_rows(f"{RUNS}/{c.run}/triage/root_causes.csv"):
            if row["cause"] not in FIRST_SWEEP:
                out.setdefault(row["cause"], (c.run, row["group"]))
    return out


def lifecycle_cur(src: Sources, campaigns: Sequence[Campaign]) -> Dict[str, Dict[str, Any]]:
    """Per root cause of both campaigns: numbers_figures.lifecycle of the campaign whose lifecycle plan holds its
    representative, with campaign (run) and corpus (first or second); cause order.

    Raises:
        ValueError: when a cause is in both plans or in none, a plan lists a cause that is not a root cause, or a
            representative breaks REP_RULE.
    """
    out: Dict[str, Dict[str, Any]] = {}
    gone = load_withdrawn(src)
    for c in campaigns:
        for cause, v in lifecycle(src, f"{RUNS}/{c.run}").items():
            if cause in gone:  # withdrawn after the discussion; its replays stay in the sweep
                continue
            if cause in out:
                raise ValueError(f"cause {cause} is in the lifecycle plans of {out[cause]['campaign']} and {c.run}")
            out[cause] = dict(v, campaign=c.run, corpus=CORPUS[c.run])
    causes = {row["cause"] for c in campaigns for row in c.causes.values()}
    if set(out) != causes:
        raise ValueError(f"lifecycle plans and root causes differ: no representative for "
                         f"{ordered(causes - set(out))}, not a root cause {ordered(set(out) - causes)}")
    wrong = [cause for cause, rep in rule_representatives(src, campaigns).items()
             if (out[cause]["campaign"], out[cause]["group"]) != rep]
    first = next((c for c in campaigns if c.run == FIRST_RUN), None)
    for cause in FIRST_SWEEP:
        v = out.get(cause)
        if v is not None and (first is None or v["campaign"] != FIRST_RUN
                              or first.causes.get(v["group"], {}).get("cause") != cause):
            wrong.append(cause)
    if wrong:
        raise ValueError(f"representatives not chosen by REP_RULE: {ordered(wrong)}")
    return {cause: out[cause] for cause in ordered(out)}


def lifecycle_cur_numbers(life: Mapping[str, Any], rel_of: Mapping[str, Set[str]]) -> Dict[str, Any]:
    """cur.lifecycle: release.lifecycle's numbers over every cause, and over the causes found by R1-R5."""
    out = lifecycle_numbers(life)
    five = relation_causes(rel_of)
    sub = lifecycle_numbers({c: v for c, v in life.items() if c in five})
    out["relations"] = {"causes": sub["causes"], "older_than_year": sub["older_than_year"]}
    return out


# ------------------------------------------------------------------ persistence
def persistence_cur(src: Sources, campaigns: Sequence[Campaign]) -> Optional[Dict[str, Any]]:
    """cur.persistence: evidence.persistence's numbers over the final R1 bug groups of both campaigns.

    Raises:
        ValueError: when the files use different waits or list a group twice.
    """
    r1 = {(c.run, i.gid): i.cause for c in campaigns for i in c.items if i.verdict == "bug" and i.relation == "R1"}
    runs = {c.run for c in campaigns}
    waits: Optional[List[str]] = None
    rows: Dict[Tuple[str, str], Dict[str, Any]] = {}
    left_out = 0
    for run, name in PERSISTENCE:
        rel = f"{RUNS}/{run}/evidence/{name}"
        if run not in runs:
            continue
        if not exists(src, rel):
            logger.warning("%s does not exist yet; cur.persistence leaves its groups out", rel)
            continue
        doc = src.json(rel)
        w = [str(x) for x in doc["waits_s"]]
        if waits is None:
            waits = w
        elif w != waits:
            raise ValueError(f"{rel}: waits {w} differ from {waits}")
        for r in doc["rows"]:
            key = (run, r["gid"])
            if key not in r1:
                left_out += 1
                continue
            if key in rows:
                raise ValueError(f"{rel}: group {r['gid']} of {run} is listed twice")
            rows[key] = r
    if waits is None:
        return None
    if left_out:
        logger.info("cur.persistence: %d rows of groups that are not final R1 bug groups left out", left_out)
    missing = sorted(set(r1) - set(rows))
    if missing:
        logger.warning("cur.persistence: %d of %d final R1 bug groups have no persistence row (first: %s)",
                       len(missing), len(r1), ", ".join(f"{run}/{g}" for run, g in missing[:3]))
    retry: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for run in sorted(runs):
        rel = f"{RUNS}/{run}/evidence/{RETRY}"
        if exists(src, rel):
            retry.update({(run, r["gid"]): r["by_wait"] for r in src.json(rel)["rows"] if (run, r["gid"]) in rows})
    cells = {k: {w: persistence_cell(r["by_wait"][w], retry.get(k, {}).get(w)) for w in waits} for k, r in rows.items()}
    longest = waits[-1]
    out: Dict[str, Any] = {
        "groups": len(rows),
        "causes": len({r1[k] for k in rows}),
        "by_wait": {w: sum(1 for r in rows.values() if r["by_wait"][w]["verdict"] == "reproduced") for w in waits},
        "reproduced_without_wait": sum(1 for r in rows.values() if r["by_wait"]["0"]["verdict"] == "reproduced"),
        "still_after_longest": sum(1 for k in cells if cells[k][longest][0] > 0),
        "never_after_longest": sum(1 for k in cells if cells[k][longest][0] == 0),
        "retried_groups": len(retry),
        "retry_replays": sum(int(v.get("replays", 1)) for by_wait in retry.values() for v in by_wait.values()),
        "longest_wait_s": int(longest)}
    gone = [k for k in cells if cells[k][longest][0] == 0]
    if gone:
        out["gone_causes"] = ", ".join(ordered({r1[k] for k in gone}))
        out["gone_last_seen_s"] = min(max((int(w) for w in waits if cells[k][w][0] > 0), default=0) for k in gone)
    return out


def release_cur_numbers(numbers: Dict[str, Any], src: Sources, campaigns: Sequence[Campaign],
                        life: Mapping[str, Any]) -> None:
    """Add cur.newest, cur.lifecycle and cur.persistence to numbers (section cur must exist)."""
    rel_of = cause_relations(campaigns)
    numbers["cur"]["newest"] = newest_cur(src, campaigns, rel_of)
    numbers["cur"]["lifecycle"] = lifecycle_cur_numbers(life, rel_of)
    numbers["cur"]["persistence"] = persistence_cur(src, campaigns)


# ------------------------------------------------------------------ tables
def lifecycle_table(life: Mapping[str, Any]) -> Table:
    rows = []
    for cause, v in life.items():
        for c in v["cells"]:
            result = "not run" if c["reproduced"] is None else f"{c['reproduced']}/{c['replays']}"
            roles = ", ".join(r for r in c["roles"] if r in ("campaign", "newest", "development head")
                              or r.startswith("newest on"))
            rows.append([cause, v["line"], c["build"], c["released"], result, READING[c["state"]], roles, v["corpus"],
                         v["group"]])
    return Table("N1_lifecycle", "Each bug's representative group (both corpora) replayed three times on releases of "
                 "its server line", ["cause", "line", "build", "released", "reproduced", "result", "role", "corpus",
                                     "group"], rows)


def newest_table(src: Sources, campaigns: Sequence[Campaign]) -> Table:
    first = [c for c in campaigns if c.run == FIRST_RUN]
    rows = []
    for label, sel, replay in ((NEWEST, campaigns, "newest release"), (HEAD, first, "gopls development head")):
        for c in sel:
            got, _ = replay_rows(src, [c], label, warn_missing=False)
            for run, cause, r in sorted(got, key=lambda x: (cause_order(x[1]), x[2]["gid"])):
                rows.append([CORPUS[run], replay, r["gid"], cause, f"{r['build']['kind']} {r['build']['version']}",
                             f"{r['reproduced']}/{r['replays']}", r["verdict"], READING[replay_state(r)]])
    return Table("N2_newest", f"Every bug group of both corpora replayed three times on the newest release of its "
                 f"server line ({NEWEST[len('newest-'):]}), then the gopls groups of the first corpus on the gopls "
                 f"development head",
                 ["corpus", "replay", "group", "cause", "build", "reproduced", "verdict", "result"], rows)


def upstream_table(src: Sources) -> Table:
    rows = [[r["cause"], f"{r['tracker']}#{r['number']}" if r["number"] else "not reported", r["reported"] or "-",
             r["status"], r["note"] or "-"]
            for r in sorted(src.csv_rows(FEEDBACK), key=lambda r: cause_order(r["cause"]))]
    return Table("N3_upstream", "The upstream reports and the maintainers' responses",
                 ["cause", "issue", "reported", "status", "note"], rows)


def root_cause_table(src: Sources, campaigns: Sequence[Campaign]) -> Table:
    """G2: both root-cause tables, cause order, then campaign and row order; server, trigger and description from the
    first table that lists the cause, the group marked with its corpus."""
    first: Dict[str, Dict[str, str]] = {}
    entries = []
    for k, c in enumerate(campaigns):
        for j, row in enumerate(src.csv_rows(f"{RUNS}/{c.run}/triage/root_causes.csv")):
            first.setdefault(row["cause"], row)
            entries.append((cause_order(row["cause"]), k, j, c.run, row))
    rows = [[row["cause"], first[row["cause"]]["server"], first[row["cause"]]["trigger"],
             first[row["cause"]]["description"], f"{row['group']} ({CORPUS[run]})"]
            for *_, run, row in sorted(entries, key=lambda e: e[:3])]
    return Table("G2_root_causes", "Distinct bugs of both corpora: bug groups merged by minimal trigger and kind of "
                 "symptom", ["cause", "server", "trigger", "description", "group"], rows)


def evidence_table(src: Sources) -> Table:
    cols = ["cause", "server", "independent", "check", "result", "related_possible", "related_other"]
    ev = load_evidence(src)
    return Table("M_evidence", "Checks of the distinct bugs that do not rest on the tested server, and related tracker "
                 "reports (both evidence summaries)", cols, [[ev[c][k] for k in cols] for c in ordered(ev)])


def cur_release_tables(src: Sources, campaigns: Sequence[Campaign], life: Mapping[str, Any]) -> List[Table]:
    """Appendix tables N1, N2, N3, G2 and M over both campaigns."""
    return [lifecycle_table(life), newest_table(src, campaigns), upstream_table(src), root_cause_table(src, campaigns),
            evidence_table(src)]


__all__ = ["cause_relations", "cur_release_tables", "lifecycle_cur", "lifecycle_cur_numbers", "newest_cur",
           "persistence_cur", "release_cur_numbers", "relation_causes", "replay_counts", "replay_rows"]
