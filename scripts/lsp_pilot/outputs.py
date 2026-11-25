"""JSONL writer and the deterministic eyeball-sample selector shared by
report_md.py and eyeball_md.py.

Run: imported by run_pilot.py, not run directly.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from config import EYEBALL_RANDOM_SEED, EYEBALL_SAMPLE_SIZE, Target, jsonl_path


def write_jsonl(target: Target, fixed_rows: list[dict]) -> Path:
    path = jsonl_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in fixed_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def write_all_jsonl(results: list[dict]) -> dict[str, Path]:
    paths = {}
    for r in results:
        if r.get("funnel") is None or r["target"].counts_only:
            continue
        paths[r["target"].key] = write_jsonl(r["target"], r["fixed_rows"])
    return paths


def sample_for_eyeball(fixed_rows: list[dict]) -> list[dict]:
    """Deterministic sample: sort by issue number (fixed population order,
    independent of API/dict ordering) then random.Random(42).sample()."""
    rows_sorted = sorted(fixed_rows, key=lambda r: r["number"])
    rng = random.Random(EYEBALL_RANDOM_SEED)
    k = min(EYEBALL_SAMPLE_SIZE, len(rows_sorted))
    if k == 0:
        return []
    return rng.sample(rows_sorted, k)
