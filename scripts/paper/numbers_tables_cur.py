"""Appendix tables of the two current-release campaigns and the benchmark signatures, under the final verdicts.

The first corpus is main_v1 (the 10 most starred projects per language), the second main_v2 (ranks 11-20); both ran
the same frozen tool and configuration. Verdicts are the final ones of numbers_final.py: the discussion's consensus
for an item the raters judged differently, else the verdict both gave. Tables (CSV columns in brackets):

- D_corpus: the projects of both corpora [corpus = first / second], pinned commits, paired servers and the seconds
  each server took to settle in the corpus probe; a pair whose eligibility was forced or that the campaign excluded
  is noted.
- F_detection: per reproduced benchmark case, as before, with the joint verdicts on its pre-only signatures
  [joint_verdicts; discussed = yes when the discussion settled one of them].
- G_groups: the triage groups of both campaigns [corpus] with the final verdict [discussed = yes when the
  discussion settled it] and the final exception class and reason: the discussion's for a discussed group
  (consensus.csv, consensus_reasons_en.csv), else the first author's (verdict_reasons.csv), which both raters'
  verdict then equals.
- G4_rater2: agreement of the two raters before the discussion, per relation for each campaign
  (triage/rater2_agreement.json), and on the benchmark signatures, all and without the practice cases
  (bench_v1/detection_rater2_agreement.json).
- G5_rater2_disagreements: every item the discussion settled (groups of both campaigns, benchmark signatures):
  both raters' original verdicts, the joint verdict, the discussion's reason (consensus_reasons_en.csv,
  detection_consensus_reasons_en.csv) and, for a group, the second rater's reason (rater2_reasons_en.csv).
- I_sweep: every group of both campaigns replayed on the server release of about a year earlier (sweep/older-2025).
- J_cost: runs, run time and candidate outcomes per campaign (main_v1, main_v2, bench_v1), relation and server.
- M4_c1_checks: the first campaign's table of numbers_evidence.py [corpus first] and the second campaign's groups
  first counted as C1, replayed with the willRenameFiles edit applied and as a rename outside the editor
  (main_v2/evidence/c1_rename_{edit,external}.json; the waits were not replayed there).

Reads, per campaign, the inputs of numbers_main.load_main and numbers_final.load_group_verdicts and
triage/{verdict_reasons,consensus_reasons_en,rater2_reasons_en}.csv, triage/rater2_agreement.json and
triage/root_causes.csv; for the benchmark bench_v1/detection_rater2_agreement.json and
detection_consensus_reasons_en.csv. Nothing is written here; paper_numbers.py writes the tables.

Run line: not run directly; imported by scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from numbers_bench import DetectData
from numbers_campaigns import CAMPAIGNS
from numbers_evidence import rename_cell
from numbers_final import Final, GroupVerdicts, SignatureVerdicts, load_group_verdicts
from numbers_io import Sources, split_signature
from numbers_main import MainData, load_main, sweep_build
from numbers_tables import Table, cost_rows, yes_no

logger = logging.getLogger(__name__)

RUNS = "data/lsptest/runs"
BENCH = f"{RUNS}/bench_v1"
BATCHES: Tuple[Tuple[str, str], ...] = (("c1", "first"), ("c2", "second"))  # section key, corpus label
RELATIONS: Tuple[str, ...] = ("R0", "R1", "R2", "R3", "R4", "R5", "R6")
ORACLE_OF = {"R0": "r0_crash", "R1": "r1_history", "R2": "r2_handles", "R3": "r3_routes", "R4": "r4_edits",
             "R5": "r5_transforms", "R6": "r6_crossimpl"}
RELATION_OF = {v: k for k, v in ORACLE_OF.items()}


@dataclass(frozen=True)
class Batch:
    """One current-release campaign with its final verdicts, English reasons and root causes."""

    key: str            # c1 or c2
    corpus: str         # first or second
    run: str            # main_v1 or main_v2
    data: MainData
    verdicts: GroupVerdicts
    consensus_en: Dict[str, Dict[str, str]]   # discussed group -> its consensus_reasons_en.csv row
    rater2_en: Dict[str, str]                 # discussed group -> the second rater's reason, in English
    causes: Dict[str, str]                    # final bug group -> its root cause
    rejudged: Dict[str, Dict[str, str]]       # group re-judged after the discussion -> its triage/rejudged.csv row


def _optional_rows(src: Sources, rel: str) -> List[Dict[str, str]]:
    return src.csv_rows(rel) if os.path.exists(src.abspath(rel)) else []


def load_batches(src: Sources) -> List[Batch]:
    """Both campaigns, in the order of BATCHES.

    Raises:
        ValueError: when a discussed group has no English reason or the English file gives another verdict.
        numbers_final.VerdictConflict: when a group has no final verdict.
    """
    out: List[Batch] = []
    for key, corpus in BATCHES:
        run, corpus_rel, prepared_rel = CAMPAIGNS[key]
        tdir = f"{RUNS}/{run}/triage"
        data = load_main(src, f"{RUNS}/{run}", corpus_rel, prepared_rel)
        verdicts = load_group_verdicts(src, run)
        en = {r["group"]: r for r in _optional_rows(src, f"{tdir}/consensus_reasons_en.csv")}
        problems = [f"{g}: no English reason" for g in verdicts.consensus if g not in en]
        problems += [f"{g}: English row says {en[g]['verdict']!r}, consensus.csv {verdicts.consensus[g]['verdict']!r}"
                     for g in verdicts.consensus if g in en and en[g]["verdict"] != verdicts.consensus[g]["verdict"].strip()]
        if problems:
            raise ValueError(f"{tdir}/consensus_reasons_en.csv: " + "; ".join(problems))
        r2 = {r["group"]: r["reason"] for r in _optional_rows(src, f"{tdir}/rater2_reasons_en.csv")}
        causes = {r["group"]: r["cause"] for r in src.csv_rows(f"{tdir}/root_causes.csv")}
        rejudged = {r["group"]: r for r in _optional_rows(src, f"{tdir}/rejudged.csv")}
        out.append(Batch(key, corpus, run, data, verdicts, en, r2, causes, rejudged))
    return out


def cause_order(cause: str) -> Tuple[int, str]:
    m = re.fullmatch(r"C(\d+)", cause)
    return (int(m.group(1)), "") if m else (10**6, cause)


# ------------------------------------------------------------------ D, F
def corpus_table(batches: Sequence[Batch]) -> Table:
    """D_corpus: both corpora, by corpus, language and project; servers with the same note share it."""
    rows: List[List[Any]] = []
    for b in batches:
        d = b.data
        forced = {(p["server"], p["project"]): p["forced"] for p in d.config.get("eligible_pairs", []) if p.get("forced")}
        excluded = {(p["server"], p["repo"]): p["reason"] for p in d.config.get("excluded_pairs") or []}
        projects: Dict[str, List[Mapping[str, Any]]] = {}
        for r in d.prepared:
            projects.setdefault(f"{r['repo']}@{r['commit12']}", []).append(r)
        for project, recs in sorted(projects.items(), key=lambda kv: (kv[1][0]["language"], kv[0].lower())):
            recs = sorted(recs, key=lambda r: str(r["server"]))
            notes: Dict[str, List[str]] = {}  # note -> servers, in server order
            for r in recs:
                if (r["server"], project) in forced:
                    notes.setdefault(f"eligibility forced ({forced[(r['server'], project)]})", []).append(r["server"])
                if (r["server"], r["repo"]) in excluded:
                    notes.setdefault(f"excluded from the campaign: {excluded[(r['server'], r['repo'])]}", []
                                     ).append(r["server"])
            rows.append([b.corpus, recs[0]["repo"], recs[0]["language"], recs[0]["commit12"],
                         ", ".join(r["server"] for r in recs), "; ".join(f"{r['server']} {r['seconds']}" for r in recs),
                         "; ".join(f"{', '.join(servers)}: {note}" for note, servers in notes.items())])
    return Table("D_corpus", "Corpus projects of both corpora, pinned commits and probe settle seconds per server",
                 ["corpus", "project", "language", "commit", "servers", "settle_seconds", "note"], rows)


def joint_summary(finals: Sequence[Final]) -> str:
    """'no 6; yes 1' over a case's pre-only signatures; '-' when it has none."""
    tally: Dict[str, int] = {}
    for f in finals:
        tally[f.verdict] = tally.get(f.verdict, 0) + 1
    return "; ".join(f"{k} {n}" for k, n in sorted(tally.items())) or "-"


def detection_table(dd: DetectData, sig: SignatureVerdicts) -> Table:
    """F_detection: per reproduced case, with the joint verdicts on its pre-only signatures."""
    rows = []
    for e in dd.entries:
        oracles = sorted({str(p["oracle"]) for p in e["pre_only"]})
        finals = [sig.final[(str(e["case"]), str(p["oracle"]), str(p["signature"]))] for p in e["pre_only"]]
        rows.append([e["case"], e["kind"], f"{e['class']} / {e['subtype']}", yes_no(e["spec_probe"]),
                     yes_no(e["detected"]), yes_no(e["complete"]), ", ".join(oracles) or "-", len(e["pre_only"]),
                     joint_summary(finals), yes_no(any(f.source == "consensus" for f in finals))])
    return Table("F_detection", "Detection of the reproduced benchmark bugs (bench_v1), with the joint verdicts",
                 ["case", "kind", "class_subtype", "spec_probe", "detected", "complete", "oracles_pre_only",
                  "pre_only_signatures", "joint_verdicts", "discussed"], rows)


# ------------------------------------------------------------------ G, I, J
def groups_table(batches: Sequence[Batch]) -> Table:
    """G_groups: every group of both campaigns with its final verdict, class and reason.

    Raises:
        ValueError: when a group not discussed has a first-author reason for another verdict than its final one.
    """
    rows: List[List[Any]] = []
    problems: List[str] = []
    for b in batches:
        d = b.data
        for g in d.groups:
            gid = str(g["gid"])
            kind, oracle, shape = split_signature(g["signature"])
            red, dec, sw = d.reductions[gid], d.decisions.get(gid, {}), d.sweep.get(gid, {})
            fin = b.verdicts.final[gid]
            discussed = fin.source in ("consensus", "rejudged")
            if fin.source == "rejudged":  # changed after the discussion: triage/rejudged.csv gives class and reason
                cls, reason = fin.cls, b.rejudged[gid]["reason_en"]
            elif discussed:
                cls, reason = fin.cls, b.consensus_en[gid]["reason"]
                if fin.verdict != "bug" and not cls:
                    logger.warning("%s %s: discussed %s group without a class", b.run, gid, fin.verdict)
            else:
                own = d.reasons.get(gid, {})
                cls, reason = own.get("class", ""), own.get("reason", "")
                if own.get("verdict", fin.verdict) != fin.verdict:
                    problems.append(f"{b.run} {gid}: verdict_reasons.csv says {own.get('verdict')!r}, final {fin.verdict!r}")
            rows.append([b.corpus, gid, kind, oracle, shape, g.get("family", ""), g.get("members", ""),
                         f"{g.get('ops_before')} -> {g.get('ops_after')}", red.get("reduced_confirmed", ""),
                         yes_no(red.get("narrowed")), fin.verdict, yes_no(discussed), dec.get("known_issue_link", ""),
                         sw.get("verdict", ""), cls, reason])
    if problems:
        raise ValueError("reasons that do not fit the final verdicts:\n  " + "\n  ".join(problems))
    return Table("G_groups", "Triage groups of both current-release campaigns, with the final verdicts",
                 ["corpus", "gid", "kind", "oracle", "shape", "family", "members", "ops", "reduced_confirmed",
                  "narrowed", "verdict", "discussed", "known_issue_link", "sweep_older_2025", "class", "reason"], rows)


def sweep_table(batches: Sequence[Batch]) -> Table:
    """I_sweep: the year-old replay of every group of both campaigns."""
    rows: List[List[Any]] = []
    for b in batches:
        for g in b.data.groups:
            r = b.data.sweep.get(g["gid"])
            if r is None:
                continue
            rows.append([b.corpus, r["gid"], r["from"], r["oracle"], sweep_build(r) or "-", r["verdict"],
                         f"{r.get('reproduced')}/{r.get('replays')}", r.get("settled"), r.get("control_stable"),
                         r.get("seconds"), r.get("error", "")])
    return Table("I_sweep", "Older-release sweep (older-2025) of both current-release campaigns: each triage group "
                 "replayed on a year-old build",
                 ["corpus", "gid", "from_kind", "oracle", "build", "verdict", "reproduced", "settled", "control_stable",
                  "seconds", "error"], rows)


def cost_table(batches: Sequence[Batch], dd: DetectData) -> Table:
    """J_cost: per campaign (main_v1, main_v2, bench_v1), relation and server."""
    rows = [row for b in batches for row in cost_rows(b.run, b.data.results, b.data.violations)]
    return Table("J_cost", "Cost and outcome per campaign, oracle and server kind (seconds = wall seconds per run)",
                 ["campaign", "oracle", "kind", "runs", "runs_not_ok", "mean_s", "median_s", "p90_s", "run_hours",
                  "candidates", "candidate_signatures", "confirmed", "flaky", "not_reproduced", "capped",
                  "labelled_legitimate", "incomplete"],
                 rows + cost_rows("bench_v1", dd.results, dd.violations))


# ------------------------------------------------------------------ G4, G5
def _kappa(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.2f}"


def rater2_agreement_table(src: Sources, batches: Sequence[Batch]) -> Table:
    """G4_rater2: agreement before the discussion, per relation for each campaign, and on the benchmark signatures
    (all, and without the cases used as practice examples in the second rater's manual)."""
    rows: List[List[Any]] = []
    for b in batches:
        agree = src.json(f"{RUNS}/{b.run}/triage/rater2_agreement.json")
        for name in RELATIONS:
            r = agree["by_relation"].get(name)
            if r:
                rows.append([f"{b.corpus} corpus", ORACLE_OF[name], r["n"], r["agree"], f"{r['percent_agreement']:.1f}",
                             _kappa(r["kappa"]), _kappa(r["kappa_bug"])])
        t3, tb = agree["three_class"], agree["bug_or_not"]
        rows.append([f"{b.corpus} corpus", "all", t3["n"], t3["agree"], f"{t3['percent_agreement']:.1f}",
                     _kappa(t3["kappa"]), _kappa(tb["kappa"])])
    det = src.json(f"{BENCH}/detection_rater2_agreement.json")
    for label, block in (("all", det), ("without practice cases", det["without_practice_cases"])):
        t3, td = block["three_class"], block["detected_or_not"]
        rows.append(["benchmark signatures", label, t3["n"], t3["agree"], f"{t3['percent_agreement']:.1f}",
                     _kappa(t3["kappa"]), _kappa(td["kappa"])])
    return Table("G4_rater2", "Agreement of the two raters before the discussion: triage groups per campaign and "
                 "relation, and the benchmark's pre-only signatures (verdicts yes, partial, no; detected or not)",
                 ["batch", "oracle", "items", "same verdict", "agreement %", "kappa (three verdicts)",
                  "kappa (bug or not)"], rows)


def _with_class(verdict: str, cls: str) -> str:
    return f"{verdict} ({cls})" if cls else verdict


def discussion_table(src: Sources, batches: Sequence[Batch], sig: SignatureVerdicts) -> Table:
    """G5_rater2_disagreements: every item the discussion settled, with both original verdicts and the joint one.

    Raises:
        ValueError: when a discussed signature has no English reason.
    """
    rows: List[List[Any]] = []
    for b in batches:
        relation = {str(g["gid"]): RELATION_OF.get(split_signature(g["signature"])[1], "?") for g in b.data.groups}
        rater2 = {r["group"]: r for r in src.csv_rows(f"{RUNS}/{b.run}/triage/rater2_decisions.csv")}
        items = sorted(b.verdicts.consensus, key=lambda g: (RELATIONS.index(relation[g]), g))
        missing = [g for g in items if g not in b.rater2_en]
        if missing:
            logger.warning("%s: rater2_reasons_en.csv lacks discussed group(s) %s", b.run, missing)
        for g in items:
            fin = b.verdicts.final[g]
            joint, discussion = _with_class(fin.verdict, fin.cls), b.consensus_en[g]["reason"]
            if g in b.rejudged:  # the discussion's verdict, then the change after it (triage/rejudged.csv)
                disc = b.verdicts.consensus[g]
                joint = f"{_with_class(disc['verdict'].strip(), disc.get('class', '').strip())}; later {joint}"
                discussion = f"{discussion} {b.rejudged[g]['reason_en']}"
            rows.append([f"{b.corpus} corpus", g, ORACLE_OF[relation[g]],
                         _with_class(b.verdicts.author[g], b.data.reasons.get(g, {}).get("class", "")),
                         _with_class(rater2[g]["verdict"], rater2[g].get("class", "")), joint,
                         discussion, b.rater2_en.get(g, "")])
    en = {(r["case"], r["signature"]): r for r in _optional_rows(src, f"{BENCH}/detection_consensus_reasons_en.csv")}
    keys = sorted(sig.consensus, key=lambda k: (k[1], k[0], k[2]))
    missing_sig = [k for k in keys if (k[0], k[2]) not in en]
    if missing_sig:
        raise ValueError(f"detection_consensus_reasons_en.csv lacks {missing_sig}")
    for case, oracle, signature in keys:
        row = en[(case, signature)]
        fin = sig.final[(case, oracle, signature)]
        if row["verdict"] != fin.verdict:
            raise ValueError(f"{case} {signature}: English row says {row['verdict']!r}, consensus {fin.verdict!r}")
        rows.append(["benchmark signatures", f"{case}, {signature}", oracle, sig.author[(case, oracle, signature)],
                     sig.rater2[(case, oracle, signature)], fin.verdict, row["reason"], ""])
    return Table("G5_rater2_disagreements", "Items the two raters judged differently and settled in discussion",
                 ["batch", "item", "oracle", "first author", "second rater", "joint verdict", "discussion",
                  "second rater's reason"], rows)


# ------------------------------------------------------------------ M4
def c1_checks_table(src: Sources, first: Optional[Table], second: Batch) -> Optional[Table]:
    """M4_c1_checks: the first campaign's table (numbers_evidence.round2_evidence) and the second campaign's groups
    first counted as C1, with the renames only ('-' under the waits, which were not replayed there)."""
    cells: Dict[str, Dict[str, str]] = {}
    for mode in ("edit", "external"):
        rel = f"{RUNS}/{second.run}/evidence/c1_rename_{mode}.json"
        if os.path.exists(src.abspath(rel)):
            for r in src.json(rel)["rows"]:
                cells.setdefault(r["gid"], {})[mode] = rename_cell(r)
    if first is None and not cells:
        return None
    header = ["corpus"] + (first.columns if first else ["group", "cause", "rename edit applied",
                                                        "rename outside the editor", "after 0 s", "after 5 s",
                                                        "after 30 s", "after 60 s"])
    rows = [["first"] + list(r) for r in (first.rows if first else [])]
    waits = len(header) - 5  # the columns after group, cause and the two renames
    for gid in sorted(cells, key=lambda g: (cause_order(second.causes.get(g, "")), g)):
        if gid not in second.causes:
            logger.warning("%s %s: renamed group without a root cause", second.run, gid)
        rows.append([second.corpus, gid, second.causes.get(gid, ""), cells[gid].get("edit", ""),
                     cells[gid].get("external", "")] + ["-"] * waits)
    return Table("M4_c1_checks", "The history bugs under a rename with the edit applied, a rename outside the editor, "
                 "and waits after the history (second corpus: the groups first counted as C1, renames only)",
                 header, rows)


# ------------------------------------------------------------------ all
def cur_tables(src: Sources, dd: DetectData, sig: SignatureVerdicts, m4_first: Optional[Table]) -> List[Table]:
    """The tables of this module (see the module docstring), in appendix order."""
    batches = load_batches(src)
    m4 = c1_checks_table(src, m4_first, batches[1])
    return [corpus_table(batches), detection_table(dd, sig), groups_table(batches),
            rater2_agreement_table(src, batches), discussion_table(src, batches, sig), sweep_table(batches),
            cost_table(batches, dd)] + ([m4] if m4 else [])


__all__ = ["Batch", "c1_checks_table", "corpus_table", "cost_table", "cur_tables", "detection_table",
           "discussion_table", "groups_table", "load_batches", "rater2_agreement_table", "sweep_table"]
