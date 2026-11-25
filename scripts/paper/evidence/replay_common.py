"""Shared replay path of the post-freeze evidence scripts (c1_rename_edits.py, persistence.py, c9_trigger.py).

`replay_variant` replays one triage group of main_v1 (or of another campaign, given as `campaign`)
through its oracle's own replay() (the frozen tool is only imported), optionally with a different op
list and with another OpApplier class for the sessions, and returns the counts the version sweep
records. Session directories get the run id <prefix><gid6>, so they never collide with a sweep
(sw<gid6>) or another evidence script. `groups_of` reads the candidate bugs from the campaign's
triage/root_causes.csv (the final table; triage/root_causes_draft.csv only while no final table exists).

Run line: imported by the evidence scripts; not run directly.
"""

from __future__ import annotations

import contextlib
import csv
import logging
import os
import shutil
import sys
import time
from typing import Any, Dict, Iterator, List, Optional, Sequence

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))

import driver  # noqa: E402  (frozen tool, read-only)
import flake  # noqa: E402
import oracles  # noqa: E402
import version_sweep as vs  # noqa: E402
from campaign_store import context_from_repro, load_repro, prepare_repro_project, sweep_session_dirs  # noqa: E402

logger = logging.getLogger("replay_common")
CAMPAIGN = "main_v1"
RUN = os.path.join(REPO, "data", "lsptest", "runs", CAMPAIGN)
EVIDENCE = os.path.join(RUN, "evidence")


def run_dir(campaign: str = CAMPAIGN) -> str:
    return os.path.join(REPO, "data", "lsptest", "runs", campaign)


def evidence_dir(campaign: str = CAMPAIGN) -> str:
    return os.path.join(run_dir(campaign), "evidence")


def groups_of(causes: Sequence[str], campaign: str = CAMPAIGN) -> List[str]:
    """Triage groups of the given candidate bugs, in file order: the campaign's final triage/root_causes.csv,
    or triage/root_causes_draft.csv while the final table does not exist yet."""
    final = os.path.join(run_dir(campaign), "triage", "root_causes.csv")
    name = "root_causes.csv" if os.path.exists(final) else "root_causes_draft.csv"
    with open(os.path.join(run_dir(campaign), "triage", name), encoding="utf-8") as f:
        return [r["group"] for r in csv.DictReader(f) if r["cause"] in causes]


def entry(gid: str, campaign: str = CAMPAIGN) -> Dict[str, Any]:
    return next(e for e in vs.group_repros(campaign) if e["gid"] == gid)


@contextlib.contextmanager
def applier_class(cls: Optional[type]) -> Iterator[None]:
    """Sessions created inside the block apply their ops with `cls` (a subclass of ops.OpApplier)."""
    if cls is None:
        yield
        return
    original = driver.OpApplier
    driver.OpApplier = cls
    try:
        yield
    finally:
        driver.OpApplier = original


def replay_variant(gid: str, prefix: str, ops: Optional[Sequence[Any]] = None, replays: int = 3,
                   applier: Optional[type] = None, campaign: str = CAMPAIGN) -> Dict[str, Any]:
    """`replays` fresh replays of the group's case (with `ops` instead of its own when given)."""
    doc, v = load_repro(entry(gid, campaign)["repro"])
    row: Dict[str, Any] = {"gid": gid, "replays": replays, "settled": 0, "control_stable": 0, "reproduced": 0,
                           "seconds": 0.0, "error": ""}
    run_id = f"{prefix}{gid[-6:]}"
    scratch = os.path.join(driver.RUNS_DIR, f"evidence-{prefix}", gid)
    shutil.rmtree(scratch, ignore_errors=True)
    t0 = time.monotonic()
    try:
        root = prepare_repro_project(doc, scratch)
        ctx = context_from_repro(doc, root, os.path.join(scratch, "work"), run_id=run_id)
        oracle = oracles.get(v.oracle)
        with applier_class(applier):
            for _ in range(replays):
                out = oracle.replay(ctx, v, ops)
                row["settled"] += int(bool(out.settled))
                row["control_stable"] += int(bool(out.control_stable))
                row["reproduced"] += int(flake.counts(out))
    except Exception as exc:  # noqa: BLE001  (recorded per row, as the version sweep does)
        row["error"] = f"{type(exc).__name__}: {exc}"[:400]
        logger.warning("%s: %s", gid, row["error"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        sweep_session_dirs(run_id)
        with contextlib.suppress(OSError):
            os.rmdir(os.path.dirname(scratch))
    row["seconds"] = round(time.monotonic() - t0, 1)
    row["verdict"] = vs.verdict(row)
    return row


def original_ops(gid: str, campaign: str = CAMPAIGN) -> List[Any]:
    _, v = load_repro(entry(gid, campaign)["repro"])
    return list(v.ops)


__all__ = ["CAMPAIGN", "EVIDENCE", "REPO", "RUN", "entry", "evidence_dir", "groups_of", "original_ops",
           "replay_variant", "run_dir"]
