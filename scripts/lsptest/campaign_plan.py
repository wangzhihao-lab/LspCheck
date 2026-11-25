"""Campaign planning (plan/tool_design_v1.md section 11.1): eligible pairs and ordered runs.

eligible_pairs(): a corpus (server, project) pair is eligible when its probe settled, the server
initialized and did not crash, the clone and dependencies are ready, the prepared directory
exists and nothing excludes it; `force` makes a pair eligible regardless of the probe. Known-bug
case projects give one pair per listed server kind; benchmark cases give one pair per build
(pre-fix and post-fix), each with the case's own version, settings and timeouts.
plan_runs(): one RunSpec per (oracle, server kind, pair, timing, seed). Order: every (oracle,
kind) queue lists its rounds (timings interleaved) over the projects; queues are merged in
proportion to their lengths, oracles then kinds, so that a partial campaign is balanced.
dry_run_plan(): one run per (oracle, kind) on the smallest eligible project with max_cases=2,
or, when the config names dry_run.projects, the full plan restricted to those projects.

Run line: imported by campaign.py, campaign_estimate.py and the tests; not run directly.
"""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from campaign_config import CampaignConfig, OracleCfg, ProjectOverride, RunSpec  # noqa: E402

CORPUS_DIR = "temp/corpus"
READY_CLONE, READY_DEPS = frozenset({"ok", "already-prepared"}), frozenset({"ok", "n/a"})


@dataclass(frozen=True)
class Pair:
    """One eligible (server kind, project[, build])."""

    server_kind: str
    project: str  # "<owner>/<repo>@<sha12>", a known-bug case id or a benchmark case id
    source: str  # corpus | case | dir
    project_ref: str  # corpus or dir: directory relative to the repository; case: case module name
    language: str
    repo: str = ""
    commit: str = ""
    size_kb: int = 0
    probe_seconds: float = 0.0
    forced: str = ""  # reason when eligibility was forced
    version: str = ""  # a benchmark build; "" = the configured server version
    phase: str = ""  # pre | post for a benchmark build
    settings: Optional[Mapping[str, Any]] = None  # benchmark case settings
    settle_timeout_s: float = 0.0  # 0: the campaign's
    request_timeout_s: float = 0.0


def corpus_dir(repo: str, commit12: str) -> str:
    return f"{CORPUS_DIR}/{repo.replace('/', '__')}@{commit12}"


def probe_problem(rec: Mapping[str, Any]) -> str:
    """Why a probe record is not eligible ("" when it is)."""
    if rec.get("excluded") or rec.get("exclusion") or rec.get("exclude"):
        return f"excluded in the corpus file: {rec.get('exclusion') or rec.get('exclude') or 'yes'}"
    if rec.get("clone_status") not in READY_CLONE or rec.get("deps_status") not in READY_DEPS:
        return f"project not prepared (clone {rec.get('clone_status')}, deps {rec.get('deps_status')})"
    if not rec.get("init_ok", True) or rec.get("crashed"):
        return "server did not initialize or crashed in the probe"
    if not rec.get("settled"):
        return f"probe did not settle ({rec.get('seconds')} s)"
    return ""


def eligible_pairs(cfg: CampaignConfig, records: Sequence[Mapping[str, Any]],
                   exists: Callable[[str], bool]) -> Tuple[List[Pair], List[Dict[str, Any]]]:
    """(eligible pairs, excluded pairs with reasons) for the configured servers and cases."""
    kinds = {s.kind for s in cfg.servers}
    force, pairs, excluded = {(k, r) for k, r in cfg.force}, [], []
    reasons = {(str(x.get("server")), str(x.get("repo"))): str(x.get("reason", "forced"))
               for x in (cfg.raw.get("eligibility") or {}).get("force") or []}
    for rec in records:
        kind, repo = str(rec.get("server")), str(rec.get("repo"))
        if kind not in kinds:
            continue
        rel = corpus_dir(repo, str(rec.get("commit12", "")))
        why, forced = probe_problem(rec), (kind, repo) in force
        if forced:
            why = "" if rec.get("clone_status") in READY_CLONE else why
        if not why and ((kind, repo) in cfg.exclude or ("*", repo) in cfg.exclude):
            why = "excluded by the campaign config"
        if not why and not exists(rel):
            why = f"prepared directory {rel} is missing"
        if why:
            excluded.append({"server": kind, "repo": repo, "reason": why})
            continue
        pairs.append(Pair(kind, f"{repo}@{rec.get('commit12', '')}", "corpus", rel, str(rec.get("language")), repo,
                          str(rec.get("commit", "")), int(rec.get("size_kb") or 0), float(rec.get("seconds") or 0.0),
                          reasons.get((kind, repo), "") if forced else ""))
    for c in cfg.case_projects:
        pairs += [Pair(k, c.case, "case", c.case, c.language, c.case) for k in c.servers]
    for b in cfg.bench_cases:
        if not exists(b.dir):
            excluded.append({"server": b.kind, "repo": b.case, "reason": f"case project {b.dir} is missing"})
            continue
        pairs += [Pair(b.kind, b.case, "dir", b.dir, b.language, b.case, version=v, phase=phase, settings=b.settings,
                       settle_timeout_s=b.settle_timeout_s, request_timeout_s=b.request_timeout_s)
                  for phase, v in b.builds]
    return pairs, excluded


# ------------------------------------------------------------------ planning
def _rank(project: str) -> str:
    return hashlib.sha1(f"order:{project}".encode()).hexdigest()


def run_spec(cfg: CampaignConfig, o: OracleCfg, kind: str, p: Pair, timing: str, seed: int,
             max_cases: Optional[int] = None) -> RunSpec:
    ov = cfg.overrides.get(p.repo) or ProjectOverride()
    attr = next((c.settings_attr for c in cfg.case_projects if c.case == p.project_ref), "") if p.source == "case" else ""
    version = p.version or next(s.version for s in cfg.servers if s.kind == kind)
    settings = p.settings if p.settings is not None else ov.settings
    return RunSpec(cfg.id, o.name, kind, version, p.project, p.source, p.project_ref, p.language, seed, timing,
                   o.max_cases if max_cases is None else max_cases, cfg.max_files, cfg.max_positions_per_file,
                   cfg.max_file_bytes, tuple(ov.exclude_dirs), dict(settings) if settings else None, attr,
                   p.settle_timeout_s or cfg.settle_timeout_s, p.request_timeout_s or cfg.request_timeout_s,
                   cfg.run_timeout_s, p.commit, cfg.min_identifiers)


def _kinds_for(cfg: CampaignConfig, o: OracleCfg, applies: Callable[[str, str], bool]) -> List[str]:
    return [k for k in cfg.kinds if (not o.servers or k in o.servers) and applies(o.name, k)]


def round_robin(queues: Mapping[Tuple[str, str], Sequence[RunSpec]], oracle_order: Sequence[str],
                server_order: Sequence[str]) -> List[RunSpec]:
    """Merge (oracle, server) queues in proportion to their lengths (stride order)."""
    keyed = []
    for (o, s), q in queues.items():
        for i, spec in enumerate(q):
            keyed.append(((i + 0.5) / len(q), oracle_order.index(o), server_order.index(s), i, spec))
    return [k[-1] for k in sorted(keyed, key=lambda k: k[:4])]


def plan_runs(cfg: CampaignConfig, pairs: Sequence[Pair], applies: Callable[[str, str], bool]) -> List[RunSpec]:
    queues: Dict[Tuple[str, str], List[RunSpec]] = {}
    for o in cfg.oracles:
        for kind in _kinds_for(cfg, o, applies):
            ps = sorted((p for p in pairs if p.server_kind == kind), key=lambda p: (_rank(p.project), p.phase != "pre"))
            q = [run_spec(cfg, o, kind, p, t, seed) for t, seed in o.rounds for p in ps]
            if q:
                queues[(o.name, kind)] = q
    return round_robin(queues, [o.name for o in cfg.oracles], cfg.kinds)


def dry_run_plan(cfg: CampaignConfig, pairs: Sequence[Pair], applies: Callable[[str, str], bool]) -> List[RunSpec]:
    """One run per (oracle, kind): smallest eligible project, the oracle's first round, few cases;
    or the full plan of cfg.dry_run_projects when the config names them."""
    if cfg.dry_run_projects:
        return [s for s in plan_runs(cfg, pairs, applies) if s.project in cfg.dry_run_projects]
    queues: Dict[Tuple[str, str], List[RunSpec]] = {}
    for o in cfg.oracles:
        for kind in _kinds_for(cfg, o, applies):
            ps = [p for p in pairs if p.server_kind == kind]
            if ps and o.rounds:
                p = min(ps, key=lambda x: (x.size_kb, x.project, x.phase))
                t, seed = o.rounds[0]
                queues[(o.name, kind)] = [run_spec(cfg, o, kind, p, t, seed, cfg.dry_run_max_cases)]
    return round_robin(queues, [o.name for o in cfg.oracles], cfg.kinds)


__all__ = ["CORPUS_DIR", "Pair", "corpus_dir", "dry_run_plan", "eligible_pairs", "plan_runs", "probe_problem",
           "round_robin", "run_spec"]
