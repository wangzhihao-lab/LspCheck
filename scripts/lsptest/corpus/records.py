"""Records of the corpus preparation: one per project x server, kept in
data/lsptest/corpus_prepared.json.

- build_record: the project and its clone/deps outcome (the probe result goes on top);
- probe_units: the per-unit decision, in project order, one server at a time. A failed
  clone gives a clone_failed record; a completed probe already on disk is reused
  (unless --force-probe); anything else is probed now, and the file is saved after
  every probe. With --skip-probe nothing is probed: a unit whose completed probe is on
  disk keeps that record exactly as it is (as the reuse path does), and any other unit
  gets a skip-probe-flag stub, so a clone+deps rerun never discards measurements;
- merge_and_save: this run's records overlaid on the file as it was loaded at startup,
  never a plain overwrite, so a filtered rerun (--languages/--only-repo/--limit) cannot
  discard other projects' results.

Run line: imported by scripts/lsptest/prepare_corpus.py; not run directly.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

from .common import CLONE_OK, LANGUAGE_SERVERS, OUT_JSON, SETTLE_CAP_DEFAULT, ProjectSpec
from .probe import run_probe

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProbeOptions:
    """The probe-phase switches of the command line."""

    skip_probe: bool = False
    force_probe: bool = False
    settle_cap: float = SETTLE_CAP_DEFAULT
    out_json: str = OUT_JSON  # saved after every probe


# ------------------------------------------------------------------ records
def build_record(p: ProjectSpec, prep: Mapping[str, Any]) -> Dict[str, Any]:
    """Project fields plus the clone/deps outcome of this run."""
    deps = prep.get("deps", {})
    return {
        "language": p.language, "repo": p.full_name, "commit": p.commit, "commit12": p.commit12,
        "stars": p.stars, "size_kb": p.size_kb,
        "clone_status": prep.get("clone", {}).get("status"),
        "deps_status": deps.get("status"), "deps_manager": deps.get("manager"),
    }


def record_key(r: Mapping[str, Any]) -> str:
    """Identity of a record: repo, commit, server and server version."""
    return f"{r.get('repo')}@{r.get('commit')}::{r.get('server')}-{r.get('version')}"


def unit_key(p: ProjectSpec, kind: str, version: str) -> str:
    """record_key of the record for project `p` under server `kind`-`version`."""
    return f"{p.full_name}@{p.commit}::{kind}-{version}"


def is_completed_probe(rec: Mapping[str, Any]) -> bool:
    """A record that holds a finished measurement (reused instead of probing again)."""
    return bool(rec.get("probe_complete")) and not rec.get("skipped_reason")


def load_prev_results(path: str = OUT_JSON) -> Dict[str, Dict[str, Any]]:
    """record_key -> record of the file on disk ({} when it is missing or unreadable)."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return {record_key(r): r for r in data if isinstance(r, dict) and r.get("repo") and r.get("server")}


def merge_and_save(path: str, baseline: Mapping[str, Dict[str, Any]],
                   new_records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Overlay this run's records onto whatever was already on disk (`baseline`,
    loaded once at startup) instead of overwriting it, so a filtered rerun
    (--languages/--only-repo/--limit) can never discard other projects'
    already-computed results."""
    merged = dict(baseline)
    for r in new_records:
        merged[record_key(r)] = r
    out = list(merged.values())
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return out


# -------------------------------------------------------------------- units
def _skip_probe_record(base: Mapping[str, Any], kind: str, version: str,
                       prev: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if prev is not None and is_completed_probe(prev):
        return prev
    return {**base, "server": kind, "version": version, "probe_complete": False,
            "skipped_reason": "skip-probe-flag"}


def _probe_unit(p: ProjectSpec, prep: Mapping[str, Any], base: Mapping[str, Any], kind: str, version: str,
                own_pids: Set[int], settle_cap: float) -> Dict[str, Any]:
    logger.info("probing %s with %s-%s ...", p.slug, kind, version)
    try:
        probe = run_probe(p, prep, kind, version, own_pids, settle_cap)
    except Exception as e:  # noqa: BLE001  (one unit's crash must not sink the batch)
        logger.exception("run_probe crashed for %s %s-%s", p.slug, kind, version)
        probe = {"server": kind, "version": version, "settled": False,
                 "error": f"{type(e).__name__}: {str(e)[:300]}"}
    rec = {**base, **probe, "probe_complete": True}
    logger.info("done %s %s-%s settled=%s seconds=%s diags=%s noise=%s", p.slug, kind, version,
                rec.get("settled"), rec.get("seconds"), rec.get("diagnostics_total"),
                rec.get("diagnostics_import_noise"))
    return rec


def probe_units(projects: Sequence[ProjectSpec], prep_by_slug: Mapping[str, Dict[str, Any]],
                prev_by_key: Mapping[str, Dict[str, Any]], own_pids: Set[int],
                opts: ProbeOptions) -> List[Dict[str, Any]]:
    """This run's record for every project x server, by the rules of the module
    docstring; `prev_by_key` is the file as loaded at startup (skip source and merge
    baseline), `own_pids` the registry of server processes this run spawned."""
    records: List[Dict[str, Any]] = []
    for p in projects:
        prep = prep_by_slug[p.slug]
        clone_ok = prep["clone"]["status"] in CLONE_OK
        for kind, version in LANGUAGE_SERVERS[p.language]:
            base = build_record(p, prep)
            prev = prev_by_key.get(unit_key(p, kind, version))
            if opts.skip_probe:
                records.append(_skip_probe_record(base, kind, version, prev))
                continue
            if not clone_ok:
                records.append({**base, "server": kind, "version": version, "settled": False,
                                "probe_complete": True, "skipped_reason": "clone_failed"})
                continue
            if prev is not None and not opts.force_probe and is_completed_probe(prev):
                logger.info("skip (already probed) %s %s-%s", p.slug, kind, version)
                records.append(prev)
                continue
            records.append(_probe_unit(p, prep, base, kind, version, own_pids, opts.settle_cap))
            merge_and_save(opts.out_json, prev_by_key, records)
    if opts.skip_probe:
        kept = sum(1 for r in records if r.get("probe_complete"))
        logger.info("--skip-probe: %d record(s) with a completed probe kept as on disk, %d recorded as not probed",
                    kept, len(records) - kept)
    return records


__all__ = [
    "ProbeOptions", "build_record", "is_completed_probe", "load_prev_results", "merge_and_save", "probe_units",
    "record_key", "unit_key",
]
