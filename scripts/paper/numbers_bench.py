"""Numbers of the historical-bug benchmark and of its detection campaign (bench_v1).

benchmark: the mining funnel (candidates.md counts and candidates.jsonl), attempted and reproduced
cases by server kind and oracle class (final verdict = last repro_results.jsonl row per case), and
the attempted cases that did not reproduce with their recorded reason.
detection: bench_v1 runs by status (as recorded, and as planned under the current code), the
detection table recomputed with campaign_detect.detect on the plan loaded as campaign_detect.py
does (compared with detection.json), generic and specification-probe summaries, by server kind and
oracle class, R0, per-oracle unique detections and pairwise overlap, the pre-only signatures, and
the counts after the author's match check (detection_author.csv; null while nothing is judged).

Run line: not run directly; imported by scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from numbers_io import (BENCH_DIR, BENCH_RUN, R0, SPEC_PROBE, Sources, counts, latest, planned_runs,
                        tool_module)

logger = logging.getLogger(__name__)

Keep = Callable[[str, Mapping[str, Any]], bool]
AuthorKey = Tuple[str, str, str]


@dataclass(frozen=True)
class BenchData:
    """Benchmark inputs: candidates, funnel counts, attempted cases and their last repro row."""

    candidates: List[Dict[str, Any]]
    funnel: Dict[str, Dict[str, int]]
    readme: str
    cases: List[Dict[str, Any]]
    repro_last: Dict[str, Dict[str, Any]]
    repro_rows: int


@dataclass(frozen=True)
class DetectData:
    """bench_v1 inputs and the detection table recomputed with the frozen tool."""

    config: Dict[str, Any]
    results: List[Dict[str, Any]]
    violations: List[Dict[str, Any]]
    planned: List[Dict[str, Any]]
    entries: List[Dict[str, Any]]
    stored: Dict[str, Any]
    author: List[Dict[str, str]]
    missed: List[Dict[str, str]]


DEVELOPMENT_CASES = frozenset({"jdtls-3155"})

# Probe types of the benchmark grouped by what their ground truth needs (plan/tool_design_v1.md 11.3).
PROBE_FAMILY = {"differs_from_fresh": "relation-shaped", "two_routes_differ": "relation-shaped",
                "transform_differs": "relation-shaped", "stale_code_action": "relation-shaped",
                "edit_leaves_diagnostic": "relation-shaped", "edit_breaks_syntax": "relation-shaped",
                "error_response": "relation-shaped", "diagnostic_present": "expected-diagnostic",
                "diagnostic_absent": "expected-diagnostic", "edit_text_differs": "expected-text"}


def parse_funnel(md: str) -> Dict[str, Dict[str, int]]:
    """Per-server rows (and 'all') of the 'Counts' table in candidates.md."""
    lines = md.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("| server | issues since")), None)
    if start is None:
        raise ValueError("candidates.md: counts table not found")
    header = [c.strip() for c in lines[start].strip().strip("|").split("|")]
    out: Dict[str, Dict[str, int]] = {}
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        row = dict(zip(header, (c.strip().strip("*") for c in line.strip().strip("|").split("|"))))
        out[row["server"]] = {"issues": int(row["issues since 2019"]), "retrieved": int(row["retrieved"]),
                              "kept": int(row["kept"])}
    return out


def load_bench(src: Sources) -> BenchData:
    cases = []
    for cid in src.subdirs(f"{BENCH_DIR}/cases"):
        rel = f"{BENCH_DIR}/cases/{cid}/case.json"
        if not os.path.exists(src.abspath(rel)):
            logger.warning("case directory without case.json: %s", cid)
            continue
        cases.append(src.json(rel))
    rows = src.jsonl(f"{BENCH_DIR}/repro_results.jsonl")
    return BenchData(candidates=src.jsonl(f"{BENCH_DIR}/candidates.jsonl"),
                     funnel=parse_funnel(src.text(f"{BENCH_DIR}/candidates.md")),
                     readme=src.text(f"{BENCH_DIR}/README.md"), cases=cases,
                     repro_last={str(r["case"]): r for r in latest(rows, "case")}, repro_rows=len(rows))


def final_verdict(b: BenchData, case: Mapping[str, Any]) -> str:
    row = b.repro_last.get(str(case["id"]))
    return str(row["verdict"]) if row else "not-run"


def is_spec(case: Mapping[str, Any]) -> bool:
    return str(((case.get("repro") or {}).get("probe") or {}).get("type")) == SPEC_PROBE


def failure(b: BenchData, case: Mapping[str, Any]) -> Dict[str, Any]:
    """Final verdict, harness reason and the author's note on the final attempt of a non-reproduced case."""
    row = b.repro_last.get(str(case["id"])) or {}
    attempt = row.get("attempt")
    note = next((str(a.get("verdict", "")) for a in case.get("attempts") or [] if a.get("attempt") == attempt), "")
    meta = case["meta"]
    return {"case": case["id"], "kind": meta["kind"], "class": meta["oracle_class"], "subtype": meta["subtype"],
            "probe": (case["repro"].get("probe") or {}).get("type"), "attempt": attempt,
            "verdict": final_verdict(b, case), "reason": row.get("reason", ""), "note": note}


def benchmark_section(b: BenchData) -> Dict[str, Any]:
    for c in b.cases:
        if str(c["id"]) not in b.repro_last:
            logger.warning("case %s has no repro_results row", c["id"])
    rep = [c for c in b.cases if final_verdict(b, c) == "reproduced"]
    mined = {(str(c["server"]), int(c["number"])) for c in b.candidates}
    outside = [c["id"] for c in b.cases if (str(c["meta"]["server"]), int(c["meta"]["number"])) not in mined]
    total = b.funnel.get("all", {})
    status = re.search(r"(\d+) cases attempted, (\d+) reproduced", b.readme)
    readme = {"attempted": int(status.group(1)), "reproduced": int(status.group(2))} if status else None
    pool = [c for c in b.candidates if c.get("grade") in ("A", "B") and c.get("builds_obtainable")
            and not c.get("no_released_bug")]
    funnel = {"issues_screened": total.get("issues"), "retrieved": total.get("retrieved"),
              "candidates": len(b.candidates), "candidates_table_kept": total.get("kept"),
              "pool_grade_ab_buildable": len(pool), "attempted": len(b.cases),
              "attempted_outside_candidates": outside, "reproduced": len(rep),
              "spec_probe_attempted": sum(is_spec(c) for c in b.cases),
              "spec_probe_reproduced": sum(is_spec(c) for c in rep),
              "by_server": {k: v for k, v in sorted(b.funnel.items()) if k != "all"}}
    return {"funnel": funnel,
            "candidates_by_server": counts(c["server"] for c in b.candidates),
            "candidates_by_grade": counts(c["grade"] for c in b.candidates),
            "candidates_by_class": counts(c["oracle_class"] for c in b.candidates),
            "final_verdicts": counts(final_verdict(b, c) for c in b.cases),
            "attempted_by_kind": counts(c["meta"]["kind"] for c in b.cases),
            "reproduced_by_kind": counts(c["meta"]["kind"] for c in rep),
            "attempted_by_class": counts(c["meta"]["oracle_class"] for c in b.cases),
            "reproduced_by_class": counts(c["meta"]["oracle_class"] for c in rep),
            "reproduced_by_probe": counts(c["repro"]["probe"]["type"] for c in rep),
            "reproduced_final_attempt": counts(b.repro_last[c["id"]].get("attempt") for c in rep),
            "repro_runs_recorded": b.repro_rows, "readme_status": readme,
            "readme_status_matches": readme == {"attempted": len(b.cases), "reproduced": len(rep)},
            "not_reproduced": [failure(b, c) for c in b.cases if final_verdict(b, c) != "reproduced"]}


def author_values(rows: Sequence[Mapping[str, str]]) -> Dict[AuthorKey, str]:
    """(case, oracle, signature) -> author_match, lower-cased; empty values included."""
    return {(r["case"], r["oracle"], r["signature"]): str(r.get("author_match") or "").strip().lower() for r in rows}


def load_detection(src: Sources) -> DetectData:
    config = src.json(f"{BENCH_RUN}/config.json")
    results = src.jsonl(f"{BENCH_RUN}/results.jsonl")
    violations = src.jsonl(f"{BENCH_RUN}/violations.jsonl")
    author = src.csv_rows(f"{BENCH_RUN}/detection_author.csv")
    planned = planned_runs(config, src, BENCH_RUN)
    projects = {s["project"] for s in planned}
    cases = [c for c in config["config"].get("bench_cases") or [] if c["case"] in projects]
    filled = {k: v for k, v in author_values(author).items() if v}
    entries = tool_module("campaign_detect").detect(cases, planned, results, violations, filled)
    missed_rel = f"{BENCH_RUN}/missed_attribution.csv"
    missed = src.csv_rows(missed_rel) if os.path.exists(src.abspath(missed_rel)) else []
    return DetectData(config=config, results=latest(results, "run_id"), violations=latest(violations, "vid"),
                      planned=planned, entries=entries, stored=src.json(f"{BENCH_RUN}/detection.json"), author=author,
                      missed=missed)


def keep_all(case: str, p: Mapping[str, Any]) -> bool:
    return True


def detecting(e: Mapping[str, Any], keep: Keep) -> Set[str]:
    """Oracles with at least one kept pre-only signature on this case."""
    return {str(p["oracle"]) for p in e["pre_only"] if keep(str(e["case"]), p)}


def summarize(sel: Sequence[Mapping[str, Any]], keep: Keep) -> Dict[str, Any]:
    by_oracle: Dict[str, int] = {}
    for e in sel:
        for o in detecting(e, keep):
            by_oracle[o] = by_oracle.get(o, 0) + 1
    return {"cases": len(sel), "complete": sum(bool(e["complete"]) for e in sel),
            "detected": sum(bool(detecting(e, keep)) for e in sel), "detected_by_oracle": dict(sorted(by_oracle.items()))}


def by_field(sel: Sequence[Mapping[str, Any]], field: str, keep: Keep) -> Dict[str, Any]:
    values = sorted({str(e[field]) for e in sel})
    return {v: {k: s[k] for k in ("cases", "complete", "detected")}
            for v, s in ((v, summarize([e for e in sel if str(e[field]) == v], keep)) for v in values)}


def unique(sel: Sequence[Mapping[str, Any]], keep: Keep, oracles: Sequence[str]) -> Dict[str, int]:
    """Cases that only this oracle detects (what removing the oracle would lose)."""
    return {o: sum(1 for e in sel if detecting(e, keep) == {o}) for o in oracles}


def overlap(sel: Sequence[Mapping[str, Any]], keep: Keep, oracles: Sequence[str]) -> Dict[str, Dict[str, int]]:
    """[a][b] = cases detected by both a and b; the diagonal is the cases detected by a."""
    sets = [detecting(e, keep) for e in sel]
    return {a: {b: sum(1 for s in sets if a in s and b in s) for b in oracles} for a in oracles}


def views(entries: Sequence[Mapping[str, Any]], keep: Keep, oracles: Sequence[str]) -> Dict[str, Any]:
    generic = [e for e in entries if not e["spec_probe"]]
    spec = [e for e in entries if e["spec_probe"]]
    groups = {"generic": generic, "spec_probe": spec, "all": list(entries)}
    r0 = [str(e["case"]) for e in entries if R0 in detecting(e, keep)]
    return {"generic": summarize(generic, keep), "spec_probe": summarize(spec, keep), "all": summarize(list(entries), keep),
            "by_kind": {k: by_field(v, "kind", keep) for k, v in groups.items()},
            "by_class": {k: by_field(v, "class", keep) for k, v in groups.items()},
            "by_probe": by_field(entries, "probe", keep),
            "by_probe_family": {f: summarize([e for e in entries if PROBE_FAMILY.get(str(e["probe"])) == f], keep)
                                for f in sorted(set(PROBE_FAMILY.values()))},
            "by_kind_oracle": {str(k): {o: sum(1 for e in entries if e["kind"] == k and o in detecting(e, keep))
                                        for o in oracles} for k in sorted({e["kind"] for e in entries})},
            "r0_crash": {"cases_with_pre_only": r0, "cases": len(r0),
                         "detected_by_r0_alone": sum(1 for e in entries if detecting(e, keep) == {R0})},
            "unique_by_oracle": {k: unique(groups[k], keep, oracles) for k in ("generic", "all")},
            "detected_by_one_relation": sum(1 for e in entries if len(detecting(e, keep)) == 1),
            # H9 was added after the relations missed jdtls-3155 in validation (plan/kickoff_v3_tool.md decision 2)
            "excluding_development_cases": summarize([e for e in entries if e["case"] not in DEVELOPMENT_CASES], keep),
            "detected_by_several_relations": sum(1 for e in entries if len(detecting(e, keep)) > 1),
            "pairwise_overlap": {k: overlap(groups[k], keep, oracles) for k in ("generic", "all")}}


def compare_stored(entries: Sequence[Mapping[str, Any]], stored: Mapping[str, Any]) -> Dict[str, Any]:
    """Cases whose recomputed pre-only signatures, detected or complete flag differ from detection.json."""
    def key(e: Mapping[str, Any]) -> Tuple[Any, ...]:
        return (sorted((p["oracle"], p["signature"]) for p in e["pre_only"]), bool(e["detected"]), bool(e["complete"]))

    old = {str(c["case"]): key(c) for c in stored.get("cases", [])}
    new = {str(e["case"]): key(e) for e in entries}
    differ = sorted(c for c in set(old) | set(new) if old.get(c) != new.get(c))
    if differ:
        logger.warning("recomputed detection differs from detection.json for %d case(s): %s", len(differ), differ)
    return {"detection_json_generated": stored.get("generated"), "matches_detection_json": not differ,
            "cases_differing": differ}


def after_author(entries: Sequence[Mapping[str, Any]], values: Mapping[AuthorKey, str],
                 oracles: Sequence[str]) -> Optional[Dict[str, Any]]:
    """The detection views counting only pre-only signatures judged 'yes'; None while none is judged."""
    judged = {k: v for k, v in values.items() if v}
    if not judged:
        return None

    def keep(case: str, p: Mapping[str, Any]) -> bool:
        return values.get((case, str(p["oracle"]), str(p["signature"]))) == "yes"

    total = sum(len(e["pre_only"]) for e in entries)
    return {"judged": len(judged), "pending": total - len(judged), "values": counts(judged.values()),
            **views(entries, keep, oracles)}


def run_numbers(dd: DetectData) -> Dict[str, Any]:
    by_run = {str(r["run_id"]): r for r in dd.results}
    planned_ids = {str(s["run_id"]) for s in dd.planned}
    outside = [r for r in dd.results if str(r["run_id"]) not in planned_ids]
    return {"recorded": {"total": len(dd.results), "by_status": counts(r["status"] for r in dd.results)},
            "planned": {"total": len(dd.planned),
                        "by_status": counts(str((by_run.get(str(s["run_id"])) or {}).get("status", "missing"))
                                            for s in dd.planned),
                        "by_oracle": counts(s["oracle"] for s in dd.planned)},
            "recorded_outside_plan": {"total": len(outside),
                                      "by_oracle_kind_status": counts(f"{r['oracle']}|{r['server_kind']}|{r['status']}"
                                                                      for r in outside)}}


def author_effect(entries: Sequence[Mapping[str, Any]], values: Mapping[AuthorKey, str],
                  oracles: Sequence[str]) -> Optional[Dict[str, int]]:
    """Detected cases before and after the author's match check (None while nothing is judged)."""
    after = after_author(entries, values, oracles)
    if after is None:
        return None
    before = sum(1 for e in entries if e["pre_only"])
    return {"detected_before": before, "detected_after": after["all"]["detected"],
            "removed": before - after["all"]["detected"]}


def missed_numbers(rows: Sequence[Mapping[str, str]]) -> Dict[str, Any]:
    """Counts of the missed-case attribution (missed_attribution.csv), generic vs specification probe."""
    def part(sel: Sequence[Mapping[str, str]]) -> Dict[str, Any]:
        ing = [r for r in sel if r["category"] == "input-not-generated"]
        return {"cases": len(sel), "by_category": counts(r["category"] for r in sel),
                "input_not_generated_by_detail": counts(re.sub(r"^\[(?:author|consensus): \w+\] ", "", r["detail"])[:3] for r in ing),
                "author_rejected": sum(1 for r in sel if r["detail"].startswith(("[author:", "[consensus:"))),  # rejected by the signature check
                "by_confidence": counts(r["confidence"] for r in sel),
                "by_relation_that_could_see": counts(r["relation_that_could_see"] for r in sel)}
    return {"generic": part([r for r in rows if r["spec_probe"] != "True"]),
            "spec_probe": part([r for r in rows if r["spec_probe"] == "True"]), "rows": len(rows)}


def detection_section(dd: DetectData) -> Dict[str, Any]:
    oracles = sorted((dd.config["config"].get("oracles") or {}).keys())
    values = author_values(dd.author)
    pre_only = [(str(e["case"]), p) for e in dd.entries for p in e["pre_only"]]
    keys = {(c, str(p["oracle"]), str(p["signature"])) for c, p in pre_only}
    filled = [v for v in values.values() if v]
    return {"runs": run_numbers(dd), "cases": len(dd.entries), **views(dd.entries, keep_all, oracles),
            "incomplete_cases": [str(e["case"]) for e in dd.entries if not e["complete"]],
            "pre_only_signatures": {"total": len(pre_only), "by_oracle": counts(p["oracle"] for _, p in pre_only),
                                    "author_match_filled": len(filled), "author_match_values": counts(filled),
                                    "author_csv_rows": len(dd.author), "author_csv_matches_table": keys == set(values)},
            "after_author": after_author(dd.entries, values, oracles),
            "missed_attribution": missed_numbers(dd.missed),
            "author_check_effect": author_effect(dd.entries, values, oracles),
            "consistency": compare_stored(dd.entries, dd.stored)}
