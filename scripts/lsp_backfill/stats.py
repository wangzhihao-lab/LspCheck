"""Shared summary-statistics helpers (coverage buckets, quantiles,
histograms, reproducible random sampling) used by both repo pipelines."""

from __future__ import annotations

import random
import statistics
from typing import Any


def coverage_buckets(evidence_list: list[dict]) -> dict[str, int]:
    buckets = {"0": 0, "1": 0, "2+": 0}
    for ev in evidence_list:
        n = ev["n_fix_commits"]
        if n == 0:
            buckets["0"] += 1
        elif n == 1:
            buckets["1"] += 1
        else:
            buckets["2+"] += 1
    return buckets


def quantiles(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "p25": None, "median": None, "p75": None, "max": None, "mean": None}
    if len(values) == 1:
        v = round(values[0], 3)
        return {"count": 1, "min": v, "p25": v, "median": v, "p75": v, "max": v, "mean": v}
    qs = statistics.quantiles(values, n=4, method="inclusive")
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "p25": round(qs[0], 3),
        "median": round(qs[1], 3),
        "p75": round(qs[2], 3),
        "max": round(max(values), 3),
        "mean": round(statistics.mean(values), 3),
    }


def files_changed_histogram(evidence_list: list[dict]) -> dict[str, int]:
    buckets = {"0": 0, "1": 0, "2-3": 0, "4-10": 0, "11+": 0}
    for ev in evidence_list:
        fc = ev["files_changed"]
        if fc is None:
            continue
        if fc == 0:
            buckets["0"] += 1
        elif fc == 1:
            buckets["1"] += 1
        elif fc <= 3:
            buckets["2-3"] += 1
        elif fc <= 10:
            buckets["4-10"] += 1
        else:
            buckets["11+"] += 1
    return buckets


def touches_tests_breakdown(evidence_list: list[dict]) -> dict[str, int]:
    out = {"true": 0, "false": 0}
    for ev in evidence_list:
        tt = ev["touches_tests"]
        if tt is None:
            continue
        out["true" if tt else "false"] += 1
    return out


def random_examples(evidence_list: list[dict], k: int = 10, seed: int = 42) -> list[dict]:
    matched = [ev for ev in evidence_list if ev["n_fix_commits"] > 0]
    rng = random.Random(seed)
    sample = rng.sample(matched, min(k, len(matched)))
    out = []
    for ev in sample:
        first = ev["fix_commits"][0]
        out.append(
            {
                "url": ev["url"],
                "number": ev["number"],
                "title": ev["title"],
                "commit_hash": first["hash"],
                "commit_subject": first["subject"],
                "n_fix_commits": ev["n_fix_commits"],
            }
        )
    return out
