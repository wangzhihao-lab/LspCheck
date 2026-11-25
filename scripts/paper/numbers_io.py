"""Shared input handling for the paper numbers.

Repository paths of the evaluation data, a reader that records the sha256 (first 16 hex digits)
of every input file it reads, last-row-per-key selection, counting helpers, summary statistics and
a read-only import of the frozen tool (scripts/lsptest) for the campaign plan and the detection
table. Nothing here writes into the data or the tool tree.

Run line: not run directly; imported by scripts/paper/paper_numbers.py
"""

from __future__ import annotations

import csv
import hashlib
import importlib
import io
import json
import logging
import os
import statistics
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TOOL_DIR = os.path.join(REPO, "scripts", "lsptest")

MAIN_RUN = "data/lsptest/runs/main_v1"
BENCH_RUN = "data/lsptest/runs/bench_v1"
SWEEP_DIR = f"{MAIN_RUN}/sweep/older-2025"
BENCH_DIR = "data/lsp_bench"
CORPUS = "data/lsptest/corpus.json"
CORPUS_PREPARED = "data/lsptest/corpus_prepared.json"
FREEZE_DIR = "data/lsptest/freeze"
FREEZE_IDS = ("v1", "v2", "v3")
OUT_JSON = "data/lsptest/paper_numbers.json"
OUT_TABLES = "paper/appendix/tables"

SPEC_PROBE = "edit_text_differs"  # ground-truth probe reported separately (specification probe)
R1 = "r1_history"
R0 = "r0_crash"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class Sources:
    """Reads repository files and records the first 16 hex digits of each file's sha256."""

    def __init__(self, repo: str = REPO) -> None:
        self.repo = repo
        self.digests: Dict[str, str] = {}

    def abspath(self, rel: str) -> str:
        return os.path.join(self.repo, rel)

    def text(self, rel: str) -> str:
        try:
            with open(self.abspath(rel), "rb") as f:
                data = f.read()
        except FileNotFoundError:
            logger.error("input file not found: %s", rel)
            raise
        self.digests[rel] = hashlib.sha256(data).hexdigest()[:16]
        return data.decode("utf-8")

    def json(self, rel: str) -> Any:
        return json.loads(self.text(rel))

    def jsonl(self, rel: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for n, line in enumerate(self.text(rel).splitlines(), 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("%s:%d: unreadable line skipped", rel, n)
        return out

    def csv_rows(self, rel: str) -> List[Dict[str, str]]:
        return [dict(r) for r in csv.DictReader(io.StringIO(self.text(rel), newline=""))]

    def subdirs(self, rel: str) -> List[str]:
        """Sorted names of the subdirectories of a repository directory (not recorded as input)."""
        root = self.abspath(rel)
        return sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))

    def sorted_digests(self) -> Dict[str, str]:
        return dict(sorted(self.digests.items()))


def latest(rows: Iterable[Mapping[str, Any]], key: str) -> List[Dict[str, Any]]:
    """The last row per key (a rerun replaces a row), in first-seen order."""
    last: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        if r.get(key):
            last[str(r[key])] = dict(r)
    return list(last.values())


def split_signature(signature: str) -> Tuple[str, str, str]:
    """'<kind>|<oracle>|<shape>' -> (kind, oracle, shape)."""
    parts = str(signature).split("|", 2)
    if len(parts) != 3:
        raise ValueError(f"malformed signature {signature!r}")
    return parts[0], parts[1], parts[2]


def counts(values: Iterable[Any]) -> Dict[str, int]:
    """Occurrences per value, keys sorted."""
    out: Dict[str, int] = {}
    for v in values:
        out[str(v)] = out.get(str(v), 0) + 1
    return dict(sorted(out.items()))


def matrix(pairs: Iterable[Tuple[Any, Any]], cols: Optional[Sequence[str]] = None) -> Dict[str, Dict[str, int]]:
    """Row -> column -> count; every row lists every column (zeros included), keys sorted."""
    cells: Dict[Tuple[str, str], int] = {}
    for a, b in pairs:
        cells[(str(a), str(b))] = cells.get((str(a), str(b)), 0) + 1
    rows = sorted({a for a, _ in cells})
    columns = sorted(set(cols or []) | {b for _, b in cells})
    return {a: {b: cells.get((a, b), 0) for b in columns} for a in rows}


def quantile(values: Sequence[float], q: float) -> float:
    """Quantile by linear interpolation between closest ranks (numpy's default method)."""
    xs = sorted(values)
    if not xs:
        raise ValueError("quantile of an empty sequence")
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def describe(values: Sequence[float], digits: int = 1) -> Dict[str, Any]:
    """n, total, mean, median and p90 of a list of seconds (None when empty)."""
    if not values:
        return {"n": 0, "total": 0.0, "mean": None, "median": None, "p90": None}
    return {"n": len(values), "total": round(sum(values), digits), "mean": round(statistics.fmean(values), digits),
            "median": round(statistics.median(values), digits), "p90": round(quantile(values, 0.9), digits)}


def span(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Wall-clock span of runs: earliest started_at to latest finished_at, in hours."""
    if not rows:
        return {"runs": 0, "start": None, "end": None, "hours": None}
    start = min(str(r["started_at"]) for r in rows)
    end = max(str(r["finished_at"]) for r in rows)
    seconds = (datetime.strptime(end, TIME_FORMAT) - datetime.strptime(start, TIME_FORMAT)).total_seconds()
    return {"runs": len(rows), "start": start, "end": end, "hours": round(seconds / 3600, 2)}


def ratio(num: int, den: int, digits: int = 3) -> Optional[float]:
    return round(num / den, digits) if den else None


def tool_module(name: str) -> Any:
    """Import a module of the frozen tool read-only (no bytecode is written into its tree)."""
    sys.dont_write_bytecode = True
    if TOOL_DIR not in sys.path:
        sys.path.append(TOOL_DIR)
    return importlib.import_module(name)


PLAN_FILE = "plan_specs.jsonl"  # a campaign's plan as exported where the corpus clones exist


def planned_runs(config_doc: Mapping[str, Any], src: Optional["Sources"] = None, run_dir: str = "") -> List[Dict[str, Any]]:
    """RunSpec JSON of a campaign's plan under the current code, loaded as campaign_detect.py does.

    The plan depends on the corpus clones under temp/. Where they are absent (the replication package),
    the plan exported to <run_dir>/plan_specs.jsonl by `paper_numbers.py --export-plans` is used; where
    both exist they must be equal."""
    campaign = tool_module("campaign")
    campaign_config = tool_module("campaign_config")
    _, runs, _, _ = campaign.load_plan(campaign_config.parse_config(config_doc["config"]),
                                       bool(config_doc.get("dry_run")))
    specs = [s.to_json() for s in runs]
    rel = f"{run_dir}/{PLAN_FILE}"
    if src is None or not run_dir or not os.path.exists(src.abspath(rel)):
        return specs
    recorded = src.jsonl(rel)
    if specs and specs != recorded:
        raise ValueError(f"{rel} differs from the plan computed now; rerun paper_numbers.py --export-plans")
    return specs or recorded