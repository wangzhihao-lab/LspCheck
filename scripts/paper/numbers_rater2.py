"""Second-rater numbers for the triage of the first current-release campaign (section rater2).

Reads, under data/lsptest/runs/main_v1/triage/: decisions.csv (the first author's verdicts),
rater2_decisions.csv (the second rater's verdicts, written by scripts/paper/import_rater2.py),
rater2_agreement.json (written by scripts/paper/rater2_agreement.py), triage.json (relation of each
group) and root_causes.csv. Returns the "rater2" section of paper_numbers.json
(first campaign, before the discussion), or None while the second rater's file or the agreement file
is missing. The tables G4_rater2 and G5_rater2_disagreements, for both campaigns and the benchmark
signatures, are built by numbers_tables_cur.py.

Run line: not run directly; imported by scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Mapping, Optional, Tuple

from numbers_io import Sources

logger = logging.getLogger(__name__)

TRIAGE = "data/lsptest/runs/main_v1/triage"
RELATIONS = ("R0", "R1", "R2", "R3", "R4", "R5", "R6")
ORACLE_RELATION = {"r0_crash": "R0", "r1_history": "R1", "r2_handles": "R2", "r3_routes": "R3",
                   "r4_edits": "R4", "r5_transforms": "R5", "r6_crossimpl": "R6"}
SERVER_PREFIXES = ("rust-analyzer", "pyright", "gopls", "ts6", "ts7")


def _server(gid: str) -> str:
    return next((s for s in SERVER_PREFIXES if gid.startswith(s + "-")), "?")


def rater2_section(src: Sources) -> Optional[Dict[str, Any]]:
    """The "rater2" numbers; None before the second rater's verdicts exist.

    Args:
        src: the repository sources (reads are recorded in the digests).

    Returns:
        The numbers section.
    """
    paths = {k: f"{TRIAGE}/{v}" for k, v in (("r2", "rater2_decisions.csv"), ("agree", "rater2_agreement.json"),
                                              ("dec", "decisions.csv"), ("triage", "triage.json"))}
    if not all(os.path.exists(src.abspath(paths[k])) for k in ("r2", "agree")):
        return None
    agree = src.json(paths["agree"])
    author = {r["group"]: r["verdict"] for r in src.csv_rows(paths["dec"])}
    rater = {r["group"]: r for r in src.csv_rows(paths["r2"])}
    relation = {g["gid"]: ORACLE_RELATION.get(g["signature"].split("|")[1], "?")
                for g in src.json(paths["triage"])["groups"]}
    both = sorted(g for g in author if g in rater and rater[g].get("verdict"))
    differ = [g for g in both if author[g] != rater[g]["verdict"]]
    rater_bug = [g for g in differ if rater[g]["verdict"] == "bug"]
    root = {r["group"]: r["cause"] for r in src.csv_rows(f"{TRIAGE}/root_causes.csv")}
    author_bug = [g for g in differ if author[g] == "bug"]

    def count_by(groups: List[str], key: Any) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for g in groups:
            out[key(g)] = out.get(key(g), 0) + 1
        return dict(sorted(out.items()))

    def stats(block: Mapping[str, Any]) -> Dict[str, Any]:
        ci = block.get("ci95_asymptotic") or [None, None]
        return {"kappa": block["kappa"], "ci_low": ci[0], "ci_high": ci[1], "agree": block["agree"],
                "n": block["n"], "agreement_pct": block["percent_agreement"]}

    r1 = agree["by_relation"].get("R1", {})
    import rater2_agreement as ra  # noqa: E402  (same statistics as rater2_agreement.json)
    five = [g for g in both if relation.get(g) not in ("R0", "R6")]  # the five relations; R0 and R6 are baselines
    five_pairs = [(author[g], rater[g]["verdict"]) for g in five]

    def five_stats(pairs: List[Tuple[str, str]], cats: Tuple[str, ...]) -> Dict[str, Any]:
        table = ra.confusion(pairs, cats)
        ci = ra.asymptotic_ci(table) or [None, None]
        return {"kappa": ra.cohen_kappa(table), "ci_low": ci[0], "ci_high": ci[1],
                "agree": sum(1 for a, b in pairs if a == b), "n": len(pairs)}
    section: Dict[str, Any] = {
        "groups": len(both),
        "rater_bugs": sum(1 for g in both if rater[g]["verdict"] == "bug"),
        "three_class": stats(agree["three_class"]),
        "bug_or_not": stats(agree["bug_or_not"]),
        "unsure": agree["rater2_unsure"]["n"],
        "unsure_as_legitimate": {"three_class_kappa": agree["unsure_as_legitimate"]["three_class"]["kappa"],
                                 "bug_kappa": agree["unsure_as_legitimate"]["bug_or_not"]["kappa"]},
        "r1": {"groups": r1.get("n"), "agree": r1.get("agree"), "kappa_bug": r1.get("kappa_bug")},
        "by_relation": {name: {"n": r["n"], "agree": r["agree"]} for name, r in agree["by_relation"].items()},
        "five_relations": {"groups": len(five), "three_class": five_stats(five_pairs, ra.VERDICTS),
                           "bug_or_not": five_stats([(ra.to_binary(a), ra.to_binary(b)) for a, b in five_pairs],
                                                    ra.BINARY)},
        "both_bug_groups": sum(1 for g in both if author[g] == "bug" and rater[g]["verdict"] == "bug"),
        "causes_with_both_bug": len({root[g] for g in both
                                     if g in root and author[g] == "bug" and rater[g]["verdict"] == "bug"}),
        "differ": len(differ),
        "differ_on_bug": len(rater_bug) + len(author_bug),
        "rater_bug_author_not": {"total": len(rater_bug),
                                 "by_relation": count_by(rater_bug, lambda g: relation.get(g, "?")),
                                 "by_server": count_by(rater_bug, _server)},
        "author_bug_rater_not": {"total": len(author_bug),
                                 "causes": ", ".join(sorted({root.get(g, "?") for g in author_bug})),
                                 "by_rater_verdict": count_by(author_bug, lambda g: rater[g]["verdict"])},
    }
    return section


__all__ = ["rater2_section"]
