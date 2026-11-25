"""Scriptability score, ranking and top-80 selection of kept candidates.

Score (higher = easier to script for a headless client on pinned builds;
the screening grade, not the issue body, carries reproduction quality):
  grade A/B/C                       +30 / +18 / +6
  both builds obtainable            +20 (candidates without both builds, or
                                     whose bug is in no released pre-fix build,
                                     are ranked after all others, never top-80)
  mapping confidence high/medium/low/none   +8 / +4 / 0 / -10
  fix commit or PR touches tests    +5
  subtype penalties: race -6, codeaction-other -4, other-route -4,
  transformation outside T1-T3 (hint says "outside") -3,
  telemetry-only report -4
  environment set-up markers in the trigger hint or note (needs/requires,
  cargo check/flycheck, third-party, install, proc macro, build script,
  vendor, module cache, large project, checkout): -2 each, at most -4
Ties: within a score, servers are interleaved, and within a server the
oracle classes are interleaved (rarer class first, each by more recent fix),
so the tie-break favours neither a server nor the most common class.
Top-80: the best 15 per server (when that many have both builds), then the
highest remaining scores across servers until 80.

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

import re
from typing import Dict, List, Sequence

GRADE_POINTS: Dict[str, int] = {"A": 30, "B": 18, "C": 6}
CONF_POINTS: Dict[str, int] = {"high": 8, "medium": 4, "low": 0, "none": -10}
SUBTYPE_PENALTY: Dict[str, int] = {"race": -6, "codeaction-other": -4, "other-route": -4}
TOP_N = 80
PER_SERVER_MIN = 15


# Environment set-up the harness cannot script as part of a history (dependencies,
# external tools, big corpora). Configuration and file operations are not
# penalised: they are ordinary R1 history steps.
_SETUP = re.compile(r"\bneeds?\b|\brequires?\b|cargo check|flycheck|third-party|\binstall|proc[- ]?macro|"
                    r"build script|vendor|module cache|large (project|workspace|repo|codebase)|monorepo|checkout", re.I)


def score(row: Dict[str, object]) -> int:
    """Return the scriptability score of one candidate row.

    The issue body is deliberately not scored: the pilot bodies are truncated at
    2,000 characters, which cuts the reproduction out of most gopls reports
    (environment dumps come first), so body-based bonuses would penalise gopls;
    the screening grade already records whether a self-contained reproduction
    exists (judged from the full text and the fix message)."""
    s = GRADE_POINTS.get(str(row.get("grade")), 0)
    s += 20 if row.get("builds_obtainable") else 0
    s += CONF_POINTS.get(str(row.get("mapping_confidence")), 0)
    s += 5 if row.get("fix_touches_tests") else 0
    s += SUBTYPE_PENALTY.get(str(row.get("subtype")), 0)
    hint = str(row.get("trigger_hint") or "").lower()
    s -= 3 if "outside" in hint else 0
    s -= 4 if "telemetry" in (str(row.get("screening_reason") or "") + hint).lower() else 0
    setup = len(_SETUP.findall(hint + " " + str(row.get("screening_reason") or "")))
    s -= min(4, 2 * setup)
    return s


def rank_rows(rows: List[Dict[str, object]], servers: Sequence[str]) -> List[Dict[str, object]]:
    """Order rows (top-80 first), set ``scriptability_rank`` (1-based) and ``top80``."""
    def recency(r: Dict[str, object]) -> int:
        return -int(str(r.get("fix_date") or "0000")[:10].replace("-", "") or 0)

    # Within one score, servers are interleaved; within a server, oracle classes are
    # interleaved (rarer class first) and each class is ordered by more recent fix.
    # Ties therefore favour neither a server nor the most common class.
    slot: Dict[tuple, int] = {}
    buckets: Dict[tuple, List[Dict[str, object]]] = {}
    for r in rows:
        buckets.setdefault((int(r["score"]), str(r["server"])), []).append(r)
    for rs in buckets.values():
        by_class: Dict[str, List[Dict[str, object]]] = {}
        for r in sorted(rs, key=lambda x: (recency(x), int(x["number"]))):
            by_class.setdefault(str(r["oracle_class"]), []).append(r)
        classes = sorted(by_class, key=lambda c: (len(by_class[c]), c))
        order: List[Dict[str, object]] = []
        for depth in range(max(len(v) for v in by_class.values())):
            order += [by_class[c][depth] for c in classes if depth < len(by_class[c])]
        for i, r in enumerate(order):
            slot[(str(r["server"]), int(r["number"]))] = i

    def key(r: Dict[str, object]) -> tuple:
        return (-int(r["score"]), slot[(str(r["server"]), int(r["number"]))], str(r["server"]), int(r["number"]))

    eligible = sorted((r for r in rows if r.get("builds_obtainable") and not r.get("no_released_bug")), key=key)
    chosen: List[Dict[str, object]] = []
    ids = set()
    for server in servers:
        for r in [x for x in eligible if x["server"] == server][:PER_SERVER_MIN]:
            chosen.append(r)
            ids.add((r["server"], r["number"]))
    for r in eligible:
        if len(chosen) >= TOP_N:
            break
        if (r["server"], r["number"]) not in ids:
            chosen.append(r)
            ids.add((r["server"], r["number"]))
    top = sorted(chosen, key=key)
    rest_ok = [r for r in eligible if (r["server"], r["number"]) not in ids]
    rest_no = sorted((r for r in rows if not r.get("builds_obtainable") or r.get("no_released_bug")), key=key)
    ordered = top + rest_ok + rest_no
    for i, r in enumerate(ordered, 1):
        r["scriptability_rank"] = i
        r["top80"] = (r["server"], r["number"]) in ids
    return ordered
