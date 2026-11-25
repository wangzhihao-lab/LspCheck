"""Numbers added after the first internal review (plan/revision_round1.md), kept apart from the
original sections so that each can be traced to the concern it answers.

- held_out: detection counting only benchmark cases that played no role before the tool was frozen
  (the three known-bug validation cases and the three cases of the benchmark dry run are excluded),
  and additionally not crediting a case whose matching signatures all come from generator families
  that were added after the benchmark mining or the validation (H8, H9, T4-T6, seeded mutations).
- error_oracle: cases whose author-matched pre-only signatures include an error response of the
  server (any code, or only internal error / timeout / dead server), in any session of any relation.
- screening: issues retrieved but rejected during benchmark screening, by reason code (candidates.md).
- stable_filter: key comparisons and keys excluded as unstable, from the run counters of main_v1.
- two_of_three: replayed candidates that reproduced in exactly two of three replays.
- merge: distinct bugs under a mechanical rule (same server, relation and case family) next to the
  author's merge (root_causes.csv).

Run line: imported by scripts/paper/paper_numbers.py; not run directly.
"""

from __future__ import annotations

import collections
import csv
import io
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

PRE_FREEZE_CASES = frozenset({"pyright-8946", "jdtls-2111", "jdtls-3155",  # known-bug validation
                              "gopls-60435", "rust-analyzer-21173", "tsserver-46466"})  # benchmark dry run
POST_MINING = frozenset({"H8", "H9", "T4", "T5", "T6", "mutation"})
# A signature shape in which a request fails in one session and not in the other (the failing-request observer).
FAILING_REQUEST_RE = re.compile(r"(result->error|error:[^|]*->result|error:timeout|timeout|dead)")
AuthorKey = Tuple[str, str, str]


def violation_families(v: Mapping[str, Any]) -> Set[str]:
    """Generator families behind one violation row (R1 history family, R5 transformation, R4 check kind)."""
    case = v.get("case") if isinstance(v.get("case"), dict) else {}
    fams: Set[str] = set()
    if isinstance(case.get("family"), str):
        fams.add(case["family"])
        fams.update(str(f) for f in case.get("families") or [])
    transform = case.get("transform")
    if isinstance(transform, dict) and isinstance(transform.get("kind"), str):
        fams.add(transform["kind"])
    if isinstance(case.get("kind"), str):
        fams.add(case["kind"])
    return fams


def depends_on_post_mining(fams: Set[str]) -> bool:
    if "H7" in fams:  # an interleaving counts as post-mining only if it contains a post-mining part
        return bool(fams & POST_MINING)
    return bool(fams & POST_MINING)


def matched(entries: Sequence[Mapping[str, Any]], values: Mapping[AuthorKey, str]) -> Dict[str, List[Mapping[str, Any]]]:
    """Case -> its pre-only signatures that the author judged 'yes'."""
    out: Dict[str, List[Mapping[str, Any]]] = {}
    for e in entries:
        yes = [p for p in e["pre_only"] if values.get((str(e["case"]), str(p["oracle"]), str(p["signature"]))) == "yes"]
        if yes:
            out[str(e["case"])] = yes
    return out


def held_out(entries: Sequence[Mapping[str, Any]], values: Mapping[AuthorKey, str],
             violations: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    by_vid = {str(v["vid"]): v for v in violations}
    hits = matched(entries, values)
    cases = [str(e["case"]) for e in entries]
    held = [c for c in cases if c not in PRE_FREEZE_CASES]
    detected = [c for c in held if c in hits]
    strict = []
    only_post: List[str] = []
    for c in detected:
        fam_sets = [violation_families(by_vid[vid]) for p in hits[c] for vid in p["vids"] if vid in by_vid]
        if fam_sets and all(depends_on_post_mining(f) for f in fam_sets):
            only_post.append(c)
        else:
            strict.append(c)
    return {"all": {"cases": len(cases), "detected": len(hits)},
            "pre_freeze_cases": sorted(PRE_FREEZE_CASES & set(cases)),
            "held_out": {"cases": len(held), "detected": len(detected)},
            "held_out_strict": {"cases": len(held), "detected": len(strict), "not_credited": sorted(only_post)}}


def error_oracle(entries: Sequence[Mapping[str, Any]], values: Mapping[AuthorKey, str]) -> Dict[str, Any]:
    any_error: Set[str] = set()
    internal: Set[str] = set()
    for case, sigs in matched(entries, values).items():
        for p in sigs:
            shape = str(p["signature"]).split("|", 2)[2]
            transition = FAILING_REQUEST_RE.search(shape)
            if not transition:
                continue
            any_error.add(case)
            if "-32603" in shape or "timeout" in shape or "dead" in shape:
                internal.add(case)
    return {"any_error_response": len(any_error), "internal_error_or_timeout": len(internal),
            "cases": sorted(any_error), "internal_cases": sorted(internal)}


def screening(candidates_md: str) -> Dict[str, Any]:
    """The 'Retrieved but rejected, by reason code' table of candidates.md, summed over servers."""
    lines = candidates_md.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("Retrieved but rejected")), None)
    if start is None:
        return {}
    head = next(i for i in range(start, len(lines)) if lines[i].startswith("| server"))
    table = []
    for ln in lines[head:]:
        if not ln.startswith("|"):
            break
        table.append(ln)
    rows = list(csv.reader(io.StringIO("\n".join(ln.strip().strip("|") for ln in table)), delimiter="|"))
    header = [c.strip() for c in rows[0]]
    totals: Dict[str, int] = collections.Counter()
    for row in rows[2:]:
        cells = [c.strip() for c in row]
        for name, cell in zip(header[1:], cells[1:]):
            if cell.isdigit():
                totals[name] += int(cell)
    return {"rejected_by_reason": dict(sorted(totals.items())), "rejected_total": sum(totals.values())}


def stable_filter(results: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    compared: Dict[str, int] = collections.Counter()
    unstable: Dict[str, int] = collections.Counter()
    for r in results:
        c = r.get("counters") or {}
        kind = str(r.get("server_kind"))
        compared[kind] += sum(int(v) for v in (c.get("compared") or {}).values())
        unstable[kind] += sum(int(v) for v in (c.get("unstable") or {}).values())
    total_c, total_u = sum(compared.values()), sum(unstable.values())
    return {"compared": total_c, "unstable": total_u,
            "unstable_permille": round(1000 * total_u / total_c, 1) if total_c else None,
            "unstable_by_kind": dict(sorted(unstable.items()))}


def two_of_three(violations: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    rows = [v for v in violations if v.get("status") in ("flaky", "not-reproduced")]
    two = sum(1 for v in rows if str(v.get("reproduced")) == "2/3")
    return {"not_confirmed": len(rows), "reproduced_2_of_3": two}


def merge(root_rows: Sequence[Mapping[str, str]], groups: Sequence[Mapping[str, Any]],
          notes: Mapping[str, str]) -> Optional[Dict[str, Any]]:
    """Distinct bugs by a mechanical rule next to the author's merge: two bug groups are one bug when
    they share the server, the relation, the case family (history family, sub-check or mutation) and,
    for quick fixes, the fix's action (its title without the identifier it names)."""
    if not root_rows:
        return None
    return {"author": len({r["cause"] for r in root_rows}), "mechanical": len(merge_keys(root_rows, groups, notes))}


def merge_keys(root_rows: Sequence[Mapping[str, str]], groups: Sequence[Mapping[str, Any]],
               notes: Mapping[str, str]) -> Set[Tuple[str, str, str, str]]:
    """The mechanical merge keys of merge(): (server, relation, case family, quick-fix action) per bug group;
    the number of distinct keys is the number of distinct bugs under the rule."""
    by_gid = {str(g["gid"]): g for g in groups}
    keys: Set[Tuple[str, str, str, str]] = set()
    for r in root_rows:
        g = by_gid.get(r["group"], {})
        kind, oracle = str(g.get("signature", "?|?|?")).split("|")[:2]
        action = re.search(r"quick fix '(\S+ \S+)", notes.get(r["group"], ""))
        keys.add((kind, oracle, str(g.get("family", "")).split(":")[0], action.group(1) if action else ""))
    return keys


def wilson(k: int, n: int, z: float = 1.96) -> Dict[str, float]:
    """Wilson score interval for k successes in n trials, in percent with one decimal."""
    if n == 0:
        return {"low": 0.0, "high": 0.0}
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return {"low": round(100 * (centre - half), 1), "high": round(100 * (centre + half), 1)}


__all__ = ["FAILING_REQUEST_RE", "PRE_FREEZE_CASES", "wilson", "error_oracle", "held_out", "merge", "merge_keys", "screening", "stable_filter", "two_of_three"]


def recheck(first: Sequence[Mapping[str, Any]], second: Sequence[Mapping[str, Any]],
            flagged: Iterable[str]) -> Dict[str, Any]:
    """The author's second look at the triage (concern M3): the groups flagged as inconsistent with similar
    groups and the bug groups, how many changed verdict and in which direction, and how many got a reason."""
    before = {i["id"]: i["choice"] for i in first}
    after = {i["id"]: i["choice"] for i in second}
    flagged = set(flagged)
    changed = {gid: f"{before.get(gid)} -> {c}" for gid, c in after.items() if before.get(gid) != c}
    return {"items": len(after), "flagged": len(flagged & set(after)),
            "flagged_changed": sum(1 for g in changed if g in flagged),
            "bug_groups_rechecked": sum(1 for g in after if g not in flagged),
            "bug_groups_changed": sum(1 for g in changed if g not in flagged),
            "bug_groups_kept": sum(1 for g in after if g not in flagged and g not in changed),
            "changes": dict(sorted(collections.Counter(changed.values()).items())),
            "with_reason": sum(1 for i in second if str(i.get("note", "")).strip())}


def held_out_detail(entries: Sequence[Mapping[str, Any]], values: Mapping[AuthorKey, str],
                    error_cases: Iterable[str], internal_cases: Iterable[str]) -> Dict[str, Any]:
    """Detection on the cases not run before the freeze: per relation, by one relation only, and the
    in-session error-response oracle on the same cases (round-2 review: one denominator per comparison)."""
    hits = {c: sigs for c, sigs in matched(entries, values).items() if c not in PRE_FREEZE_CASES}
    oracles_of = {c: {str(p["oracle"]) for p in sigs} for c, sigs in hits.items()}
    by_oracle = collections.Counter(o for os_ in oracles_of.values() for o in os_)
    unique = collections.Counter(next(iter(os_)) for os_ in oracles_of.values() if len(os_) == 1)
    return {"detected": len(hits), "detected_by_oracle": dict(sorted(by_oracle.items())),
            "unique_by_oracle": dict(sorted(unique.items())),
            "error_response": len([c for c in error_cases if c not in PRE_FREEZE_CASES]),
            "internal_error": len([c for c in internal_cases if c not in PRE_FREEZE_CASES]),
            "error_cases_pre_freeze": sorted(c for c in error_cases if c in PRE_FREEZE_CASES)}


def five_relations(groups_by_oracle: Mapping[str, int], bugs_by_oracle: Mapping[str, int]) -> Dict[str, Any]:
    """Groups and bugs of R1–R5, without the crash check R0 and the exploratory R6."""
    keep = [o for o in groups_by_oracle if o not in ("r0_crash", "r6_crossimpl")]
    groups = sum(groups_by_oracle[o] for o in keep)
    bugs = sum(bugs_by_oracle.get(o, 0) for o in keep)
    return {"groups": groups, "bugs": bugs, "precision_pct": round(100.0 * bugs / groups, 1) if groups else None}


def sensitivity(first: Mapping[str, str], final: Mapping[str, str], cause_of: Mapping[str, str],
                decisive: Iterable[str]) -> Dict[str, Any]:
    """Bug groups, distinct bugs and bug groups per relation under the first-pass verdicts, the final
    verdicts, and the final verdicts restricted to bugs with decisive evidence outside the server."""
    decisive = set(decisive)
    def rel(gid: str) -> str:
        return next((t.upper() for t in gid.split("-") if len(t) == 2 and t[0] == "r" and t[1].isdigit()), "?")
    def summary(bugs: Sequence[str]) -> Dict[str, Any]:
        return {"bug_groups": len(bugs), "distinct_bugs": len({cause_of[g] for g in bugs if g in cause_of}),
                "by_relation": dict(sorted(collections.Counter(rel(g) for g in bugs).items())),
                "distinct_by_relation": dict(sorted(collections.Counter(
                    rel(g) for g in {cause_of[b]: b for b in bugs if b in cause_of}.values()).items()))}
    first_bugs = sorted(g for g, v in first.items() if v == "bug")
    final_bugs = sorted(g for g, v in final.items() if v == "bug")
    return {"first_pass": summary(first_bugs), "final": summary(final_bugs),
            "decisive_only": summary([g for g in final_bugs if cause_of.get(g) in decisive])}


def cost_per_bug(run_hours: Mapping[str, float], distinct: Mapping[str, int]) -> Dict[str, Any]:
    """Run-hours of the current-release campaign per distinct bug, per relation (R1–R5)."""
    out: Dict[str, Any] = {}
    for rel_, hours in sorted(run_hours.items()):
        n = distinct.get(rel_, 0)
        out[rel_] = {"run_hours": round(hours, 1), "distinct_bugs": n,
                     "hours_per_bug": round(hours / n, 1) if n else None}
    return out


def unsettled_sessions(results: Iterable[Mapping[str, Any]], oracle: str = "r1_history") -> Dict[str, Any]:
    """Sessions of one relation's runs that never settled and were discarded, per server."""
    per: Dict[str, Dict[str, int]] = {}
    for r in results:
        c = r.get("counters") or {}
        if r.get("oracle") != oracle:
            continue
        a = per.setdefault(str(r.get("server_kind")), {"sessions": 0, "unsettled": 0})
        a["sessions"] += int(c.get("sessions", 0))
        a["unsettled"] += int(c.get("unsettled", 0))
    return {"by_server": dict(sorted(per.items())), "unsettled": sum(v["unsettled"] for v in per.values()),
            "sessions": sum(v["sessions"] for v in per.values())}


def counts(values: Iterable[Any]) -> Dict[str, int]:
    """Occurrences per value."""
    return dict(collections.Counter(str(v) for v in values))
