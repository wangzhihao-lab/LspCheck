"""Final verdicts: the verdict the two raters settled in discussion, else the verdict both gave.

Rule (plan/rater2_protocol.md, the rules fixed on 2026-11-18, item 1): for every finding group of a current-release
campaign and every pre-only signature of the benchmark, the final verdict is the one in the consensus file
when the item was discussed, otherwise the verdict the first author and the second rater both gave. An item
the raters judged differently that has no consensus row, an item one rater left without a verdict, a
consensus row for an unknown item and an illegal verdict stop the computation (VerdictConflict). An item
the discussion left unresolved counts as not a bug (group) or as no (signature); a consensus row that says
otherwise is a conflict, too.

Inputs, per campaign data/lsptest/runs/<campaign>/triage/: triage.json (the groups), decisions.csv (the
first author), rater2_decisions.csv (the second rater), consensus.csv (the discussion); for the benchmark
data/lsptest/runs/bench_v1/: detection_author.csv, detection_rater2.csv, detection_consensus.csv. Nothing
is written.

Run line: not run directly; imported by scripts/paper/paper_numbers.py and the other numbers_*.py modules
"""

from __future__ import annotations

import dataclasses

import logging
import os
from dataclasses import dataclass
from typing import Dict, Hashable, List, Mapping, Sequence, Set, Tuple, TypeVar

from numbers_io import Sources

logger = logging.getLogger(__name__)

GROUP_VERDICTS: Tuple[str, ...] = ("bug", "legitimate", "tool-artifact")
SIGNATURE_VERDICTS: Tuple[str, ...] = ("yes", "partial", "no")
UNRESOLVED_ALLOWED: Dict[str, Tuple[str, ...]] = {"group": ("legitimate", "tool-artifact"), "signature": ("no",)}
RUNS = "data/lsptest/runs"
BENCH = "bench_v1"

K = TypeVar("K", bound=Hashable)
SigKey = Tuple[str, str, str]  # (case, oracle, signature), as in numbers_bench.author_values


class VerdictConflict(ValueError):
    """Some item has no final verdict under the rule (listed in the message)."""


@dataclass(frozen=True)
class Final:
    """The final verdict of one item and where it comes from."""

    verdict: str
    source: str        # "consensus", "agreed" or "rejudged"
    cls: str = ""      # the exception class the consensus gave (L1-L7, A1-A4), else ""
    followed: str = ""  # whose original verdict the discussion followed: author, rater2, both
    unresolved: bool = False


def merge_verdicts(universe: Sequence[K], author: Mapping[K, str], rater2: Mapping[K, str],
                   consensus: Mapping[K, Mapping[str, str]], kind: str) -> Dict[K, Final]:
    """Final verdict per item of the universe.

    Args:
        universe: every item that needs a verdict (groups of a campaign, or benchmark signatures).
        author: item -> the first author's verdict ("" or absent when not judged).
        rater2: item -> the second rater's verdict.
        consensus: item -> its consensus row (verdict, class, followed, unresolved, ...).
        kind: "group" or "signature" (selects the legal verdicts).

    Returns:
        item -> Final, in the order of the universe.

    Raises:
        VerdictConflict: listing every item without a final verdict and every illegal consensus row.
    """
    legal = GROUP_VERDICTS if kind == "group" else SIGNATURE_VERDICTS
    known = set(universe)
    problems: List[str] = [f"consensus row for an unknown {kind}: {k}" for k in consensus if k not in known]
    out: Dict[K, Final] = {}
    for k in universe:
        row = consensus.get(k)
        if row is not None:
            verdict = str(row.get("verdict", "")).strip()
            unresolved = str(row.get("unresolved", "")).strip().lower() in ("yes", "true", "1")
            if verdict not in legal:
                problems.append(f"{k}: consensus verdict {verdict!r} is not one of {legal}")
                continue
            if unresolved and verdict not in UNRESOLVED_ALLOWED[kind]:
                problems.append(f"{k}: unresolved, so it counts as {UNRESOLVED_ALLOWED[kind]}, not {verdict!r}")
                continue
            if author.get(k) and author.get(k) == rater2.get(k):
                logger.warning("%s: consensus row although both raters gave %s; the consensus is used", k, author[k])
            out[k] = Final(verdict, "consensus", str(row.get("class", "")).strip(),
                           str(row.get("followed", "")).strip(), unresolved)
            continue
        a, b = str(author.get(k, "") or "").strip(), str(rater2.get(k, "") or "").strip()
        if not a or not b:
            problems.append(f"{k}: no consensus row and the {'author' if not a else 'second rater'} gave no verdict")
        elif a != b:
            problems.append(f"{k}: the author says {a!r}, the second rater {b!r}, and there is no consensus row")
        elif a not in legal:
            problems.append(f"{k}: verdict {a!r} is not one of {legal}")
        else:
            out[k] = Final(a, "agreed")
    if problems:
        raise VerdictConflict(f"{len(problems)} {kind}(s) without a final verdict:\n  " + "\n  ".join(problems))
    return out


@dataclass(frozen=True)
class GroupVerdicts:
    """A campaign's verdicts per group: each rater's before the discussion, the discussion's and the final one."""

    campaign: str
    author: Dict[str, str]
    rater2: Dict[str, str]
    consensus: Dict[str, Dict[str, str]]
    final: Dict[str, Final]


@dataclass(frozen=True)
class SignatureVerdicts:
    """The benchmark's verdicts per pre-only signature, keyed (case, oracle, signature)."""

    author: Dict[SigKey, str]
    rater2: Dict[SigKey, str]
    consensus: Dict[SigKey, Dict[str, str]]
    final: Dict[SigKey, Final]
    rater2_notes: Dict[SigKey, str]


def _optional_rows(src: Sources, rel: str) -> List[Dict[str, str]]:
    """Rows of a CSV that may not exist yet (no discussion held): [] when absent."""
    return src.csv_rows(rel) if os.path.exists(src.abspath(rel)) else []


WITHDRAWN = "data/lsptest/root_cause_withdrawn.csv"


def load_withdrawn(src: Sources) -> Set[str]:
    """Root causes withdrawn after the discussion (their groups re-judged, triage/rejudged.csv): their evidence rows
    and sweep plans stay on record, and the number scripts skip them."""
    if not os.path.exists(src.abspath(WITHDRAWN)):
        return set()
    return {r["cause"] for r in src.csv_rows(WITHDRAWN)}


def load_group_verdicts(src: Sources, campaign: str) -> GroupVerdicts:
    """The final verdict of every group of one campaign (triage.json lists the groups).

    Args:
        src: repository sources (reads are recorded).
        campaign: run directory name, e.g. main_v1.

    Returns:
        GroupVerdicts of the campaign.

    Raises:
        VerdictConflict: when a group has no final verdict.
        FileNotFoundError: when triage.json, decisions.csv or rater2_decisions.csv is missing.
    """
    tdir = f"{RUNS}/{campaign}/triage"
    groups = [str(g["gid"]) for g in src.json(f"{tdir}/triage.json")["groups"]]
    author = {r["group"]: r.get("verdict", "").strip() for r in src.csv_rows(f"{tdir}/decisions.csv")}
    rater2 = {r["group"]: r.get("verdict", "").strip() for r in src.csv_rows(f"{tdir}/rater2_decisions.csv")}
    consensus = {r["group"]: r for r in _optional_rows(src, f"{tdir}/consensus.csv")}
    final = merge_verdicts(groups, author, rater2, consensus, "group")
    # triage/rejudged.csv: verdicts the raters changed after the discussion on new replay evidence; consensus.csv
    # keeps the discussion as it was (whose verdict it followed), the final verdict and class come from here
    for r in _optional_rows(src, f"{tdir}/rejudged.csv"):
        g = r["group"]
        if g not in final:
            raise VerdictConflict(f"{campaign}: rejudged group {g} is not a triage group")
        final[g] = dataclasses.replace(final[g], verdict=r["verdict"].strip(), source="rejudged", cls=r.get("class", "").strip())
    return GroupVerdicts(campaign, author, rater2, consensus, final)


def load_signature_verdicts(src: Sources) -> SignatureVerdicts:
    """The final verdict of every pre-only signature of the benchmark (the rows of detection_author.csv).

    The second rater's file and the consensus file carry no oracle column; the oracle is read from the
    author's row of the same (case, signature).

    Raises:
        VerdictConflict: when a signature has no final verdict, or a rater-2 row names an unknown signature.
    """
    run = f"{RUNS}/{BENCH}"
    author_rows = src.csv_rows(f"{run}/detection_author.csv")
    oracle_of = {(r["case"], r["signature"]): r["oracle"] for r in author_rows}

    def key(r: Mapping[str, str], name: str) -> SigKey:
        cs = (r["case"], r["signature"])
        if cs not in oracle_of:
            raise VerdictConflict(f"{name}: signature {cs} is not in detection_author.csv")
        return (cs[0], oracle_of[cs], cs[1])

    universe = [(r["case"], r["oracle"], r["signature"]) for r in author_rows]
    author = {(r["case"], r["oracle"], r["signature"]): str(r.get("author_match") or "").strip().lower()
              for r in author_rows}
    r2_rows = src.csv_rows(f"{run}/detection_rater2.csv")
    rater2 = {key(r, "detection_rater2.csv"): str(r.get("verdict") or "").strip().lower() for r in r2_rows}
    notes = {key(r, "detection_rater2.csv"): str(r.get("note") or "") for r in r2_rows}
    consensus = {key(r, "detection_consensus.csv"): r for r in _optional_rows(src, f"{run}/detection_consensus.csv")}
    final = merge_verdicts(universe, author, rater2, consensus, "signature")
    return SignatureVerdicts(author, rater2, consensus, final, notes)


__all__ = ["Final", "GroupVerdicts", "SignatureVerdicts", "VerdictConflict", "load_group_verdicts",
           "load_signature_verdicts", "merge_verdicts"]
