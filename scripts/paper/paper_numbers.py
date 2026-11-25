"""Every number the paper reports, computed from the final evaluation data, plus the appendix tables.

Reads (never writes) the main campaign data/lsptest/runs/main_v1 (results, violations, triage
groups and reductions, the author's triage/decisions.csv, the older-2025 sweep), the historical-bug
benchmark data/lsp_bench, the detection campaign data/lsptest/runs/bench_v1 (with the author's
detection_author.csv), the corpus files and the tool freezes. Campaign plans and the detection
table come from the frozen tool's own functions, imported read-only; the recomputed detection
table is compared with detection.json. Writes data/lsptest/paper_numbers.json (sections setup,
main, benchmark, detection and sources = sha256 prefix of every input file read), the figure data
data/lsptest/figure_data.json and the appendix tables paper/appendix/tables/<letter>_<name>.{csv,md}.
Rerun after the author fills decisions.csv or detection_author.csv: the verdict, precision and
after_author numbers then fill in. The tables D, F, G, G4, G5, I, J and M4 cover both current-release
campaigns and the benchmark signatures under the final verdicts (numbers_tables_cur.py), as do the
figure data and cur.over_time; release.over_time keeps the first campaign and the author's verdicts.
The release replays of all distinct bugs of both campaigns (cur.newest, cur.lifecycle, cur.persistence,
figure_data lifecycle_cur) and the tables N1, N2, N3, G2 and M come from numbers_release_cur.py; the
section release keeps the first campaign.

The sections c1, c2 (main_v1, main_v2), cur (both, with the RQ2 baselines), agree and detection.consensus
count with the final verdicts of numbers_final.py (the discussion's consensus, else the verdict both raters
gave) and need each campaign's triage/root_causes.csv (numbers_campaigns.py, numbers_agree.py); numbers_current.py
adds to c1, c2 and cur what the older sections give for the first campaign only (run seconds, stability filter,
violations, reduction, merge, classes, unsettled sessions, C1 replays, sensitivity, evidence, cost). The older
sections (main, review, detection, release, evidence, rater2) keep the first author's verdicts and the
first campaign until the text switches over.

Run line: python3 scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from numbers_bench import benchmark_section, detection_section, load_bench, load_detection  # noqa: E402
from numbers_io import FREEZE_DIR, FREEZE_IDS, OUT_JSON, OUT_TABLES, REPO, Sources  # noqa: E402
from numbers_main import load_main, main_section, setup_section  # noqa: E402
from numbers_tables import Table, all_tables, write_tables  # noqa: E402

logger = logging.getLogger("paper_numbers")


def compute() -> Tuple[Dict[str, Any], List[Table]]:
    """All sections of paper_numbers.json and the appendix tables, from the repository data."""
    src = Sources(REPO)
    main = load_main(src)
    bench = load_bench(src)
    detect = load_detection(src)
    freezes = [src.json(f"{FREEZE_DIR}/{fid}.json") for fid in FREEZE_IDS]
    effort_rel = "data/lsptest/runs/main_v1/triage/effort.json"  # the author's own estimate of the judging time
    effort = src.json(effort_rel) if os.path.exists(src.abspath(effort_rel)) else None
    numbers = {"setup": setup_section(main, detect.config, detect.results, detect.planned, freezes),
               "main": main_section(main), "benchmark": benchmark_section(bench),
               "detection": detection_section(detect),
               "author_effort": None,
               "sources": src.sorted_digests()}
    numbers["main"]["root_causes"] = root_causes(src)
    numbers["example"] = example(src)
    numbers["review"] = review_numbers(src, main, detect)
    red = numbers["main"]["reduction"]
    numbers["review"]["not_reconfirmed"] = red["groups"] - int((red.get("reduced_confirmed") or {}).get("3/3", 0))
    import numbers_review as nr  # noqa: E402
    rv, aa = numbers["review"], numbers["detection"]["after_author"] or {}
    fam = aa.get("by_probe_family") or {}
    rv["intervals"] = {"all": nr.wilson(aa["all"]["detected"], aa["all"]["cases"]),
                       "held_out": nr.wilson(rv["held_out"]["held_out"]["detected"], rv["held_out"]["held_out"]["cases"]),
                       "relation_shaped": nr.wilson(fam["relation-shaped"]["detected"], fam["relation-shaped"]["cases"])}
    wc = numbers["setup"]["main_v1"]["wall_clock"]
    rv["wall_clock_hours"] = {"main": round(wc["part1_other_oracles"]["hours"] + wc["part2_r1_history"]["hours"], 1),
                              "main_part1": round(wc["part1_other_oracles"]["hours"], 1),
                              "main_part2": round(wc["part2_r1_history"]["hours"], 1)}
    if effort:  # items judged: the pre-only signatures checked plus the triage groups
        numbers["author_effort"] = {"hours_total": effort["author_hours_total"],
                                    "items": numbers["detection"]["pre_only_signatures"]["total"]
                                    + numbers["main"]["verdicts"]["rows"]}
    import numbers_evidence as ne  # noqa: E402
    numbers["evidence"], evidence_tables = ne.evidence_numbers(src)
    round2_tables = round2_numbers(numbers, src, detect)
    import numbers_review as nr  # noqa: E402
    numbers["review"]["unsettled_r1"] = nr.unsettled_sessions(main.results)
    numbers["review"]["classes"] = dict(sorted(nr.counts(r["class"] for r in main.reasons.values()
                                                           if r.get("verdict") != "bug").items()))
    campaigns = consensus_numbers(numbers, src, detect)  # before the figure data, which counts with the final verdicts
    import numbers_figures as nf  # noqa: E402
    import numbers_release_cur as nrc  # noqa: E402
    fig = nf.figure_data(src, numbers)
    fig["lifecycle_cur"] = nrc.lifecycle_cur(src, campaigns)  # every cause of both campaigns (figure, Table bugs)
    nf.write(os.path.join(REPO, "data", "lsptest", "figure_data.json"), fig)
    numbers["release"] = nf.release_numbers(src, fig)
    numbers["cur"]["over_time"] = nf.over_time_numbers(fig["bugs_over_time"])
    nrc.release_cur_numbers(numbers, src, campaigns, fig["lifecycle_cur"])  # cur.newest, cur.lifecycle, cur.persistence
    release_tables = nrc.cur_release_tables(src, campaigns, fig["lifecycle_cur"])
    import numbers_rater2 as n2  # noqa: E402
    numbers["rater2"] = n2.rater2_section(src)
    import numbers_final as nfv  # noqa: E402
    import numbers_tables_cur as ntc  # noqa: E402
    m4_first = next((t for t in evidence_tables if t.name == "M4_c1_checks"), None)  # extended with the 2nd campaign
    cur_tables = ntc.cur_tables(src, detect, nfv.load_signature_verdicts(src), m4_first)
    round2_tables = [t for t in round2_tables if t.name != "G3_sensitivity"] + [sensitivity_table(numbers["cur"])]
    numbers["sources"] = src.sorted_digests()  # every input read above, not only those read before "sources" was set
    return (numbers, all_tables(bench, freezes) + [t for t in evidence_tables if t.name != "M4_c1_checks"]
            + round2_tables + release_tables + cur_tables)


RELATION_COLUMNS = ("R0", "R1", "R2", "R3", "R4", "R5", "R6")


def sensitivity_table(cur: Mapping[str, Any]) -> Table:
    """G3_sensitivity over both corpora (cur.sensitivity): bug groups and distinct bugs per relation under each rater's
    verdicts before the discussion, the agreed verdicts, and the agreed verdicts counting only the bugs with decisive
    evidence; -- where a set of verdicts gives no merge into distinct bugs or no group count."""
    s = cur["sensitivity"]

    def row(label: str, groups: Optional[Mapping[str, int]], distinct: Optional[Mapping[str, int]]) -> List[Any]:
        g = (lambda r: str(groups.get(r, 0))) if groups else (lambda r: "--")
        d = (lambda r: str(distinct.get(r, 0))) if distinct else (lambda r: "--")
        return [label, g("total"), d("total")] + [f"{g(r)} / {d(r)}" for r in RELATION_COLUMNS]

    rows = [row("First author, before the discussion", s["bug_groups"]["author"], None),
            row("Second rater, before the discussion", s["bug_groups"]["rater2"], None),
            row("Agreed verdicts", s["bug_groups"]["final"], s["distinct"]["final"]),
            row("Agreed verdicts, decisive evidence only", None, s["distinct"]["decisive"])]
    return Table("G3_sensitivity", "Bug groups and distinct bugs of both corpora under four sets of verdicts",
                 ["verdicts", "bug groups", "distinct bugs", *RELATION_COLUMNS], rows)


def consensus_numbers(numbers: Dict[str, Any], src: Sources, detect: Any) -> List[Any]:
    """The sections that count with the final verdicts (consensus, else both raters' verdict): c1 and c2 (one per
    current-release campaign), cur (both together, with the RQ2 baselines), agree (kappas and the discussion) and
    detection.consensus. The older sections keep the first author's verdicts until the text switches over. Returns
    the campaigns (numbers_campaigns.Campaign, c1 then c2) for the release numbers of numbers_release_cur."""
    import numbers_agree as na  # noqa: E402
    import numbers_campaigns as nc  # noqa: E402
    import numbers_final as nfv  # noqa: E402
    campaigns = [nc.load_campaign(src, key) for key in nc.CAMPAIGNS]
    for c in campaigns:
        numbers[c.key] = nc.campaign_section(c)
    numbers["cur"] = nc.current_section(campaigns)
    signatures = nfv.load_signature_verdicts(src)
    numbers["agree"] = na.agree_section(src, campaigns, signatures, detect)
    numbers["detection"]["consensus"] = na.consensus_detection(detect, signatures)
    import numbers_current as ncur  # noqa: E402
    ncur.current_numbers(numbers, src, campaigns)  # the older sections' per-campaign numbers for c1, c2 and cur
    return campaigns


def author_bug_groups(src: Sources) -> Set[str]:
    """main_v1 groups the first author judged bugs (decisions.csv). The older sections count only these, so that
    root_causes.csv may also list the groups that became bugs in the discussion (counted in c1 and cur)."""
    return {r["group"] for r in src.csv_rows("data/lsptest/runs/main_v1/triage/decisions.csv") if r["verdict"] == "bug"}


def root_causes(src: Sources) -> Optional[Dict[str, Any]]:
    """The bug groups merged by minimal trigger and symptom (triage/root_causes.csv), with the year-old
    sweep: a cause is long-standing when one of its groups reproduced on the year-old release."""
    rel = "data/lsptest/runs/main_v1/triage/root_causes.csv"
    if not os.path.exists(src.abspath(rel)):
        return None
    author_bugs = author_bug_groups(src)
    rows = [r for r in src.csv_rows(rel) if r["group"] in author_bugs]
    sweep_rel = "data/lsptest/runs/main_v1/sweep/older-2025/results.jsonl"
    sweep = {r["gid"]: r["verdict"] for r in src.jsonl(sweep_rel)} if os.path.exists(src.abspath(sweep_rel)) else {}
    causes: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        c = causes.setdefault(r["cause"], {"server": r["server"], "trigger": r["trigger"], "groups": 0, "long_standing": False})
        c["groups"] += 1
        c["relation"] = next((tok.upper() for tok in r["group"].split("-") if len(tok) == 2 and tok[0] == "r" and tok[1].isdigit()), "?")
        c["long_standing"] = c["long_standing"] or sweep.get(r["group"]) == "reproduced"
    by_server: Dict[str, int] = {}
    for c in causes.values():
        by_server[c["server"]] = by_server.get(c["server"], 0) + 1
    by_relation: Dict[str, int] = {}
    for c in causes.values():
        by_relation[c["relation"]] = by_relation.get(c["relation"], 0) + 1
    servers_by_relation: Dict[str, int] = {
        rel_: len({c["server"] for c in causes.values() if c["relation"] == rel_}) for rel_ in by_relation}
    return {"causes": len(causes), "groups": len(rows), "by_server": dict(sorted(by_server.items())),
            "by_relation": dict(sorted(by_relation.items())),
            "servers_by_relation": dict(sorted(servers_by_relation.items())),
            "long_standing": sum(1 for c in causes.values() if c["long_standing"]), "detail": causes}


EXAMPLE_GROUP = "ts6-r1-references-lost-h5-d24ca6"  # the motivating example of Section 2 and Fig. 1


def example(src: Sources) -> Optional[Dict[str, Any]]:
    """Numbers of the motivating example, read from its reduced repro.json."""
    rel = f"data/lsptest/runs/main_v1/triage/{EXAMPLE_GROUP}/repro.json"
    if not os.path.exists(src.abspath(rel)):
        return None
    doc = src.json(rel)
    expected, actual = doc.get("expected") or [], doc.get("actual") or []
    return {"group": EXAMPLE_GROUP, "expected_references": len(expected),
            "expected_files": len({e[0] for e in expected}), "actual_references": len(actual),
            "ops": len(doc.get("ops") or []), "line": doc["key"]["line"] + 1, "column": doc["key"]["character"] + 1}


def review_numbers(src: Sources, main: Any, detect: Any) -> Dict[str, Any]:
    """The numbers added after the first internal review (numbers_review.py)."""
    import numbers_review as nr  # noqa: E402
    from numbers_bench import author_values  # noqa: E402
    values = {k: v for k, v in author_values(detect.author).items() if v}
    root_rel = "data/lsptest/runs/main_v1/triage/root_causes.csv"
    author_bugs = author_bug_groups(src)
    root_rows = ([r for r in src.csv_rows(root_rel) if r["group"] in author_bugs]
                 if os.path.exists(src.abspath(root_rel)) else [])
    return {"held_out": nr.held_out(detect.entries, values, detect.violations),
            "error_oracle": nr.error_oracle(detect.entries, values),
            "screening": nr.screening(src.text("data/lsp_bench/candidates.md")),
            "stable_filter": nr.stable_filter(main.results),
            "two_of_three": {"main": nr.two_of_three(main.violations), "bench": nr.two_of_three(detect.violations)},
            "merge": nr.merge(root_rows, main.groups, {r["group"]: str(src.json(
                f"data/lsptest/runs/main_v1/triage/{r['group']}/repro.json").get("note", "")) for r in root_rows}),
            "recheck": recheck_numbers(src)}


def round2_numbers(numbers: Dict[str, Any], src: Sources, detect: Any) -> List[Table]:
    """Numbers added after the second internal review (numbers_review.py): one denominator per
    comparison, the five relations without R0 and R6, verdict sensitivity and cost per distinct bug."""
    import numbers_review as nr  # noqa: E402
    from numbers_bench import author_values  # noqa: E402
    rv, main = numbers["review"], numbers["main"]
    values = {k: v for k, v in author_values(detect.author).items() if v}
    eo = rv["error_oracle"]
    rv["held_out_detail"] = nr.held_out_detail(detect.entries, values, eo["cases"], eo["internal_cases"])
    fam = (numbers["detection"]["after_author"] or {}).get("by_probe_family") or {}
    rv["intervals"].update({
        "strict": nr.wilson(rv["held_out"]["held_out_strict"]["detected"], rv["held_out"]["held_out_strict"]["cases"]),
        "expected_diagnostic": nr.wilson(fam["expected-diagnostic"]["detected"], fam["expected-diagnostic"]["cases"]),
        "expected_text": nr.wilson(fam["expected-text"]["detected"], fam["expected-text"]["cases"])})
    by_oracle_bug = {o: v.get("bug", 0) for o, v in main["verdicts"]["by_oracle_verdict"].items()}
    rv["five_relations"] = nr.five_relations(main["triage_groups"]["by_oracle"], by_oracle_bug)
    rel = "data/lsptest/runs/main_v1/triage"
    names = sorted(os.listdir(src.abspath(f"{rel}/judgements")))
    first = {i["id"]: i["choice"] for i in src.json(f"{rel}/judgements/{[n for n in names if n.startswith('triage_')][0]}")["items"]}
    final = {r["group"]: r["verdict"] for r in src.csv_rows(f"{rel}/decisions.csv")}
    cause_of = {r["group"]: r["cause"] for r in src.csv_rows(f"{rel}/root_causes.csv")}
    decisive = numbers["evidence"]["independent_causes"]["decisive"].split(", ") if numbers.get("evidence") else []
    rv["sensitivity"] = nr.sensitivity(first, final, cause_of, decisive)
    hours = {f"R{o[1]}": v["total"] / 3600.0 for o, v in main["run_seconds"]["per_oracle"].items()
             if o[1] in "12345"}
    rv["cost_per_bug"] = nr.cost_per_bug(hours, main["root_causes"]["by_relation"])
    labels = (("first_pass", "First-pass verdicts"), ("final", "Final verdicts"),
              ("decisive_only", "Final verdicts, bugs with decisive evidence only"))
    rows = []
    for key, label in labels:
        v = rv["sensitivity"][key]
        rows.append([label, v["bug_groups"], v["distinct_bugs"]]
                    + [f"{v['by_relation'].get(r, 0)} / {v['distinct_by_relation'].get(r, 0)}" for r in ("R1", "R2", "R3", "R4")])
    return [Table("G3_sensitivity", "Bug groups and distinct bugs under three sets of verdicts",
                  ["verdicts", "bug groups", "distinct bugs", "R1", "R2", "R3", "R4"], rows)]


def recheck_numbers(src: Sources) -> Optional[Dict[str, Any]]:
    """The author's second look (triage/recheck.html) against the first triage, from the exported judgements."""
    import numbers_review as nr  # noqa: E402
    from recheck_page import FLAGGED  # noqa: E402
    rel = "data/lsptest/runs/main_v1/triage/judgements"
    names = sorted(os.listdir(src.abspath(rel)))
    first = [n for n in names if n.startswith("triage_")]
    second = [n for n in names if n.startswith("recheck_")]
    if not (first and second):
        return None
    out = nr.recheck(src.json(f"{rel}/{first[0]}")["items"], src.json(f"{rel}/{second[-1]}")["items"], FLAGGED)
    # Single decisions taken after the independent checks (decision_*.json), counted against the recheck.
    rechecked = {i["id"]: i["choice"] for i in src.json(f"{rel}/{second[-1]}")["items"]}
    latest_decision: Dict[str, Dict[str, Any]] = {}
    for n in names:  # decision files sort by time; a later decision on a group replaces an earlier one
        if n.startswith("decision_"):
            for i in src.json(f"{rel}/{n}")["items"]:
                latest_decision[i["id"]] = i
    later = list(latest_decision.values())
    out["after_checks_changed"] = sum(1 for i in later if rechecked.get(i["id"], i["choice"]) != i["choice"])
    out["after_checks"] = sorted({f"{rechecked.get(i['id'])} -> {i['choice']}" for i in later
                                  if rechecked.get(i["id"], i["choice"]) != i["choice"]})
    # The consistency pass (consistency_*.json): verdicts changed when every non-bug group got its class.
    before = {i["id"]: i["choice"] for i in src.json(f"{rel}/{first[0]}")["items"]}
    before.update(rechecked)
    before.update({g: i["choice"] for g, i in latest_decision.items()})
    moves: Dict[str, int] = {}
    for n in names:
        if n.startswith("consistency_"):
            for i in src.json(f"{rel}/{n}")["items"]:
                if before.get(i["id"]) != i["choice"]:
                    key = f"{before.get(i['id'])} -> {i['choice']}"
                    moves[key] = moves.get(key, 0) + 1
    out["consistency"] = {"changed": sum(moves.values()), "moves": dict(sorted(moves.items())),
                          "to_bug": sum(v for k, v in moves.items() if k.endswith("-> bug")),
                          "between_legitimate_and_artifact": sum(v for k, v in moves.items() if "bug" not in k)}
    return out


def export_plans() -> int:
    """The plans of main_v1, main_v2 and bench_v1 as computed now, for readers without the corpus clones."""
    from numbers_io import PLAN_FILE, planned_runs  # noqa: E402
    for run in ("data/lsptest/runs/main_v1", "data/lsptest/runs/main_v2", "data/lsptest/runs/bench_v1"):
        with open(os.path.join(REPO, run, "config.json"), encoding="utf-8") as f:
            specs = planned_runs(json.load(f))
        if not specs:
            raise SystemExit(f"{run}: the plan is empty here (are the corpus clones under temp/ present?)")
        with open(os.path.join(REPO, run, PLAN_FILE), "w", encoding="utf-8") as f:
            f.writelines(json.dumps(s, ensure_ascii=False) + "\n" for s in specs)
        logger.info("%s/%s: %d runs", run, PLAN_FILE, len(specs))
    return 0


def write_numbers(numbers: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(numbers, f, indent=1, ensure_ascii=False)
        f.write("\n")


def summary_lines(n: Dict[str, Any]) -> List[str]:
    m, b, d = n["main"], n["benchmark"]["funnel"], n["detection"]
    red, ver, g, s = m["reduction"], m["verdicts"], d["generic"], d["spec_probe"]
    after = d["after_author"]
    return [f"main_v1: {m['runs']['total']} runs {m['runs']['by_status']}; "
            f"{m['confirmed_signatures']['total']} confirmed signatures; {m['triage_groups']['total']} triage groups",
            f"reduction: {red['groups_with_ops']} groups with ops, {red['ops_before']} -> {red['ops_after']} ops; "
            f"narrowed {red['narrowed']}; reduced_confirmed {red['reduced_confirmed']}",
            f"verdicts: {ver['judged']}/{ver['rows']} judged, precision {ver['precision']}",
            f"sweep older-2025: {m['sweep_older_2025']['by_verdict']}",
            f"benchmark: {b['attempted']} attempted, {b['reproduced']} reproduced "
            f"({b['spec_probe_reproduced']} with the specification probe)",
            f"detection: {d['runs']['recorded']['total']} runs recorded; generic {g['detected']}/{g['cases']} "
            f"({g['complete']} complete), spec-probe {s['detected']}/{s['cases']} ({s['complete']} complete); "
            f"{d['pre_only_signatures']['total']} pre-only signatures, "
            f"{d['pre_only_signatures']['author_match_filled']} judged; after_author "
            f"{'pending' if after is None else after['generic']['detected']}; "
            f"matches detection.json: {d['consistency']['matches_detection_json']}"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT_JSON, help="numbers JSON (repository-relative)")
    ap.add_argument("--tables", default=OUT_TABLES, help="appendix table directory (repository-relative)")
    ap.add_argument("--export-plans", action="store_true",
                    help="write each campaign's plan to data/lsptest/runs/<id>/plan_specs.jsonl (needs the corpus clones)")
    args = ap.parse_args()
    if args.export_plans:
        return export_plans()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    numbers, tables = compute()
    write_numbers(numbers, os.path.join(REPO, args.out))
    write_tables(tables, os.path.join(REPO, args.tables))
    logger.info("wrote %s and %d tables under %s", args.out, len(tables), args.tables)
    for line in summary_lines(numbers):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
