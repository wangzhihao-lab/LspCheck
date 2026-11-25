"""Agreement of the two raters, the discussion of their disagreements, and benchmark detection under the final verdicts.

agree (section of paper_numbers.json):
- c1, c2: Cohen's kappa of the first author's and the second rater's verdicts before the discussion (three verdicts,
  and bug or not), with the asymptotic 95% interval and the agreement, per campaign; computed with
  scripts/paper/rater2_agreement.py's statistics and checked against the stored triage/rater2_agreement.json;
- signatures: the same for the benchmark's pre-only signatures (yes / partial / no, and counts as a detection or
  not), over all signatures and without the cases used as practice examples in the second rater's manual
  (detection_agreement.py, without_practice_cases), plus the agreement on whether a bug counts as detected;
  checked against bench_v1/detection_rater2_agreement.json;
- discussion: the items discussed (consensus rows) per batch, whose original verdict the discussion followed,
  unresolved items, and the counts before (each rater) and after the discussion (final verdicts): bug groups per
  campaign, signatures judged yes, benchmark bugs detected.

detection.consensus (key added to the detection section): the detection counts of numbers_bench and
numbers_review recomputed with the final signature verdicts in place of the author's: detected bugs over all
cases, generic and specification-probe cases and probe families, the held-out and strict held-out counts, the
failing-request observer on the benchmark, and Wilson intervals.

Run line: not run directly; imported by scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import detection_agreement as da
import numbers_review as nr
import rater2_agreement as ra
from numbers_bench import DetectData, after_author, author_effect
from numbers_campaigns import Campaign, relation_of
from numbers_final import Final, SignatureVerdicts
from numbers_io import Sources

logger = logging.getLogger(__name__)

RUNS = "data/lsptest/runs"
BENCH = f"{RUNS}/bench_v1"
TOLERANCE = 1e-9
SigKey = Tuple[str, str, str]


def stats(block: Mapping[str, Any]) -> Dict[str, Any]:
    """kappa, interval, agreement and n of one rater2_agreement.summary block."""
    ci = block.get("ci95_asymptotic") or [None, None]
    return {"kappa": block["kappa"], "ci_low": ci[0], "ci_high": ci[1], "agree": block["agree"], "n": block["n"],
            "agreement_pct": block["percent_agreement"]}


def check_stored(src: Sources, rel: str, fresh: Mapping[str, Any], parts: Sequence[Tuple[str, ...]]) -> None:
    """Raise when a stored agreement file gives other kappas or counts than the recomputation (a stale file)."""
    if not os.path.exists(src.abspath(rel)):
        logger.warning("%s is missing; the agreement is recomputed only", rel)
        return
    stored = src.json(rel)
    for path in parts:
        a, b = stored, fresh
        for p in path:
            a, b = a[p], b[p]
        for field in ("kappa", "n", "agree"):
            x, y = a.get(field), b.get(field)
            if x is None or y is None:
                same = x is None and y is None
            else:
                same = abs(float(x) - float(y)) <= TOLERANCE
            if not same:
                raise ValueError(f"{rel}: {'.'.join(path)}.{field} is {x}, recomputed {y}; rerun the agreement script")


def campaign_agreement(src: Sources, c: Campaign) -> Dict[str, Any]:
    """kappa of one campaign's groups before the discussion (rater2_agreement.agreement, no bootstrap)."""
    tdir = f"{RUNS}/{c.run}/triage"
    rows = src.csv_rows(f"{tdir}/rater2_decisions.csv")
    rel = {str(g["gid"]): relation_of(g["signature"]) for g in c.groups}
    res = ra.agreement(c.verdicts.author, rows, rel, list(rel), None, 0)
    check_stored(src, f"{tdir}/rater2_agreement.json", res, (("three_class",), ("bug_or_not",)))
    return {"groups": res["groups"]["both"], "three_class": stats(res["three_class"]),
            "bug_or_not": stats(res["bug_or_not"]), "unsure": res["rater2_unsure"]["n"]}


def signature_agreement(src: Sources, dd: DetectData) -> Dict[str, Any]:
    """kappa of the benchmark signatures before the discussion, all and without the practice cases."""
    rows = src.csv_rows(f"{BENCH}/detection_rater2.csv")
    res = da.agreement(dd.author, rows, da.signatures(dd.stored), 0)
    check_stored(src, f"{BENCH}/detection_rater2_agreement.json", res,
                 (("three_class",), ("detected_or_not",), ("without_practice_cases", "three_class"),
                  ("without_practice_cases", "detected_or_not")))
    w = res["without_practice_cases"]
    def case_block(c: Mapping[str, Any]) -> Dict[str, Any]:
        return {"author_detected": c["author_detected"], "rater2_detected": c["rater2_detected"],
                **stats(c["summary"])}  # n: the bugs whose signatures both judged
    return {"all": {"n": res["signatures"]["both"], "three_class": stats(res["three_class"]),
                    "detected_or_not": stats(res["detected_or_not"]), "bugs": case_block(res["cases"])},
            "without_practice": {"n": w["three_class"]["n"], "excluded_signatures": w["excluded_signatures"],
                                 "excluded_cases": len(w["excluded_cases"]), "three_class": stats(w["three_class"]),
                                 "detected_or_not": stats(w["detected_or_not"]), "bugs": case_block(w["cases"])},
            "unsure": res["rater2_unsure"]["n"]}


def discussion_block(rows_by_batch: Mapping[str, Sequence[Final]]) -> Dict[str, Any]:
    """Items discussed per batch, whose verdict the discussion followed, and unresolved items."""
    def followed(sel: Sequence[Final]) -> Dict[str, int]:
        return {f: sum(1 for x in sel if x.followed == f) for f in ("author", "rater2", "both")}
    every = [x for sel in rows_by_batch.values() for x in sel]
    return {"items": len(every), "by_batch": {b: len(sel) for b, sel in rows_by_batch.items()},
            "followed": followed(every), "followed_by_batch": {b: followed(sel) for b, sel in rows_by_batch.items()},
            "unresolved": sum(1 for x in every if x.unresolved),
            "unresolved_by_batch": {b: sum(1 for x in sel if x.unresolved) for b, sel in rows_by_batch.items()}}


def detected(entries: Sequence[Mapping[str, Any]], values: Mapping[SigKey, str]) -> int:
    """Benchmark bugs with at least one pre-only signature judged yes."""
    return len(nr.matched(entries, values))


def agree_section(src: Sources, campaigns: Sequence[Campaign], sig: SignatureVerdicts,
                  dd: DetectData) -> Dict[str, Any]:
    """Section agree (see the module docstring)."""
    out: Dict[str, Any] = {c.key: campaign_agreement(src, c) for c in campaigns}
    out["signatures"] = signature_agreement(src, dd)
    batches: Dict[str, List[Final]] = {c.key: [f for f in c.verdicts.final.values() if f.source in ("consensus", "rejudged")]
                                       for c in campaigns}
    batches["signatures"] = [f for f in sig.final.values() if f.source == "consensus"]
    disc = discussion_block(batches)
    changed: Dict[str, Any] = {}
    for c in campaigns:
        gids = [str(g["gid"]) for g in c.groups]
        changed[f"{c.key}_bug_groups"] = {
            "author": sum(1 for g in gids if c.verdicts.author.get(g) == "bug"),
            "rater2": sum(1 for g in gids if c.verdicts.rater2.get(g) == "bug"),
            "final": sum(1 for g in gids if c.verdicts.final[g].verdict == "bug")}
        changed[f"{c.key}_groups_changed_from_author"] = sum(
            1 for g in gids if c.verdicts.final[g].verdict != c.verdicts.author.get(g))
    changed["bug_groups"] = {who: sum(changed[f"{c.key}_bug_groups"][who] for c in campaigns)
                             for who in ("author", "rater2", "final")}
    final_values = {k: f.verdict for k, f in sig.final.items()}
    changed["signatures_yes"] = {"author": sum(1 for v in sig.author.values() if v == "yes"),
                                 "rater2": sum(1 for v in sig.rater2.values() if v == "yes"),
                                 "final": sum(1 for v in final_values.values() if v == "yes")}
    changed["signatures_changed_from_author"] = sum(1 for k, v in final_values.items() if v != sig.author.get(k))
    changed["detected"] = {"author": detected(dd.entries, sig.author), "rater2": detected(dd.entries, sig.rater2),
                           "final": detected(dd.entries, final_values)}
    disc["changed"] = changed
    out["discussion"] = disc
    return out


def detection_counts(entries: Sequence[Mapping[str, Any]], values: Mapping[SigKey, str],
                     violations: Sequence[Mapping[str, Any]], oracles: Sequence[str]) -> Dict[str, Any]:
    """Detection counts and intervals with the given signature verdicts (case, oracle, signature) -> yes/partial/no.

    Args:
        entries: the detection table (campaign_detect.detect).
        values: a verdict for every pre-only signature.
        violations: the bench_v1 violation rows (last row per vid), for the strict held-out count.
        oracles: the campaign's oracles.

    Returns:
        The counts of numbers_bench.after_author and numbers_review.held_out / error_oracle / held_out_detail.
    """
    views = after_author(entries, values, oracles)
    if views is None:
        raise ValueError("no signature has a verdict")
    keep = ("cases", "complete", "detected", "detected_by_oracle")
    held = pre_freeze(nr.held_out(entries, values, violations), entries, values)
    eo = nr.error_oracle(entries, values)
    fam = views["by_probe_family"]

    def block(name: str) -> Dict[str, Any]:  # every oracle listed in detected_by_oracle, zeros included
        out = {k: views[name][k] for k in keep}
        out["detected_by_oracle"] = {o: int(out["detected_by_oracle"].get(o, 0)) for o in oracles}
        return out

    kinds = sorted({str(e["kind"]) for e in entries})
    zero = {"cases": 0, "complete": 0, "detected": 0}
    return {"values": views["values"], "judged": views["judged"], "pending": views["pending"],
            "all": block("all"), "generic": block("generic"), "spec_probe": block("spec_probe"),
            "by_kind": {sel: {k: dict(views["by_kind"][sel].get(k, zero)) for k in kinds}
                        for sel in ("generic", "spec_probe", "all")},
            "by_kind_oracle": {k: {o: int(views["by_kind_oracle"].get(k, {}).get(o, 0)) for o in oracles}
                               for k in kinds},
            "by_probe_family": {f: {k: v[k] for k in ("cases", "detected")} for f, v in fam.items()},
            "detected_by_one_relation": views["detected_by_one_relation"],
            "detected_by_several_relations": views["detected_by_several_relations"],
            "held_out": held, "error_oracle": eo,
            "held_out_detail": nr.held_out_detail(entries, values, eo["cases"], eo["internal_cases"]),
            "intervals": {
                "all": nr.wilson(held["all"]["detected"], held["all"]["cases"]),
                "held_out": nr.wilson(held["held_out"]["detected"], held["held_out"]["cases"]),
                "strict": nr.wilson(held["held_out_strict"]["detected"], held["held_out_strict"]["cases"]),
                **{name.replace("-", "_"): nr.wilson(fam[name]["detected"], fam[name]["cases"])
                   for name in ("relation-shaped", "expected-diagnostic", "expected-text") if name in fam}}}


def consensus_detection(dd: DetectData, sig: SignatureVerdicts) -> Dict[str, Any]:
    """detection.consensus: detection_counts with the final signature verdicts.

    Raises:
        ValueError: when the final verdicts do not cover exactly the pre-only signatures of the detection table.
    """
    values = {k: f.verdict for k, f in sig.final.items()}
    table = {(str(e["case"]), str(p["oracle"]), str(p["signature"])) for e in dd.entries for p in e["pre_only"]}
    if set(values) != table:
        raise ValueError(f"final signature verdicts and the detection table differ: without a verdict "
                         f"{sorted(table - set(values))}, not in the table {sorted(set(values) - table)}")
    oracles = sorted(dd.config["config"]["oracles"])
    out = detection_counts(dd.entries, values, dd.violations, oracles)
    out["from_consensus"] = sum(1 for f in sig.final.values() if f.source == "consensus")
    out["check_effect"] = check_effect(dd.entries, values, oracles)
    out["check_removed"] = out["check_effect"]["removed"]
    return out


def pre_freeze(held: Dict[str, Any], entries: Sequence[Mapping[str, Any]],
               values: Mapping[SigKey, str]) -> Dict[str, Any]:
    """numbers_review.held_out with the cases run before the freeze counted: pre_freeze_cases becomes their number
    (the list moves to pre_freeze_case_list) and pre_freeze_detected the number of them detected."""
    cases = list(held["pre_freeze_cases"])
    hits = sorted(c for c in nr.matched(entries, values) if c in set(cases))
    out = dict(held)
    out.update({"pre_freeze_cases": len(cases), "pre_freeze_case_list": cases,
                "pre_freeze_detected": len(hits), "pre_freeze_detected_list": hits})
    return out


def check_effect(entries: Sequence[Mapping[str, Any]], values: Mapping[SigKey, str],
                 oracles: Sequence[str]) -> Dict[str, Any]:
    """numbers_bench.author_effect with the given signature verdicts: cases detected by the pre-only rule, cases with
    a signature judged yes, and the difference, with the names of the removed cases.

    Raises:
        ValueError: when no signature has a verdict.
    """
    effect = author_effect(entries, values, oracles)
    if effect is None:
        raise ValueError("no signature has a verdict")
    hits = set(nr.matched(entries, values))
    removed = sorted(str(e["case"]) for e in entries if e["pre_only"] and str(e["case"]) not in hits)
    if len(removed) != effect["removed"]:
        raise ValueError(f"check effect: {effect['removed']} removed, but {len(removed)} cases listed: {removed}")
    return {**effect, "removed_cases": removed}


__all__ = ["agree_section", "check_effect", "consensus_detection", "detection_counts", "discussion_block",
           "pre_freeze"]
