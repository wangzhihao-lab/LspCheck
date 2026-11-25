"""Campaign configuration (plan/tool_design_v1.md section 11.1); planning is in campaign_plan.py.

A config (data/lsptest/campaigns/<id>.json) holds: id, description, corpus (probe file,
default data/lsptest/corpus_prepared.json; "" for none), servers [{kind, version}], oracles
{name: {seeds: {timing: [seeds] | count}, max_cases, servers: [kinds]}}, targets {max_files,
max_positions_per_file, max_file_bytes, min_identifiers}, timeouts {settle_s, request_s, run_s},
concurrency, server_limits {kind: most concurrent runs}, wall_clock_budget_h (0 = none; summed
over invocations), flake {n, per_signature}, signature_cap {runs (default 3; 0 = off), scope
campaign | build} (campaign_costs.py), eligibility {force: [{server, repo, reason}], exclude:
[{server | "*", repo, reason}]}, project_overrides {repo: {exclude_dirs, settings, reason}},
case_projects [{case, language, servers, settings_attr}] (known-bug cases built from
scripts/lsp_repro/cases as validate_known_bugs.py does), bench_cases [{case, dir, kind, language,
builds {pre, post}, settings, session, ...}] (benchmark cases of data/lsp_bench, each with its own
builds; written by campaign_bench.py), dry_run {max_cases, only, projects} (only: the config always
runs as a dry run; projects: the dry run is the full plan restricted to these projects).
A RunSpec is one run; run_id = short hash of (oracle, kind, version, project, seed, timing).

Run line: imported by campaign.py, campaign_plan.py, campaign_run.py, campaign_estimate.py and the tests; not run directly.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from campaign_costs import CapConfig, parse_cap  # noqa: E402
from oracles import ORACLE_MODULES  # noqa: E402
from oracles.base import TIMINGS  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_CORPUS = "data/lsptest/corpus_prepared.json"
TOP_KEYS = frozenset({"id", "description", "corpus", "servers", "oracles", "targets", "timeouts", "concurrency",
                      "server_limits", "wall_clock_budget_h", "flake", "signature_cap", "eligibility",
                      "project_overrides", "case_projects", "bench_cases", "dry_run", "notes", "generated"})
PHASES = ("pre", "post")
_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


class ConfigError(ValueError):
    """A campaign config that cannot be used."""


@dataclass(frozen=True)
class ServerCfg:
    kind: str
    version: str


@dataclass(frozen=True)
class OracleCfg:
    name: str
    rounds: Tuple[Tuple[str, int], ...]  # (timing, seed), timings interleaved
    max_cases: int = 12
    servers: Tuple[str, ...] = ()  # empty: every configured server the oracle applies to


@dataclass(frozen=True)
class ProjectOverride:
    exclude_dirs: Tuple[str, ...] = ()
    settings: Optional[Mapping[str, Any]] = None  # merged over driver.SESSION_SETTINGS for the kind
    reason: str = ""


@dataclass(frozen=True)
class CaseProject:
    case: str
    language: str
    servers: Tuple[str, ...]
    settings_attr: str = ""


@dataclass(frozen=True)
class BenchCase:
    """A benchmark case: its project/ directory, its settings and its pre-fix and post-fix builds."""

    case: str
    dir: str  # project directory relative to the repository
    kind: str
    language: str
    builds: Tuple[Tuple[str, str], ...]  # (phase, version): pre, post
    settings: Optional[Mapping[str, Any]] = None
    settle_timeout_s: float = 0.0  # 0: the campaign's
    request_timeout_s: float = 0.0


@dataclass(frozen=True)
class CampaignConfig:
    id: str
    servers: Tuple[ServerCfg, ...]
    oracles: Tuple[OracleCfg, ...]
    description: str = ""
    corpus: str = DEFAULT_CORPUS
    max_files: int = 3
    max_positions_per_file: int = 12
    max_file_bytes: int = 256_000
    min_identifiers: int = 8
    settle_timeout_s: float = 300.0
    request_timeout_s: float = 30.0
    run_timeout_s: float = 7200.0
    concurrency: int = 4
    server_limits: Mapping[str, int] = field(default_factory=dict)  # kind -> most concurrent runs of that kind
    wall_clock_budget_s: float = 0.0
    flake_n: int = 3
    per_signature: int = 1
    cap: CapConfig = CapConfig()
    dry_run_max_cases: int = 2
    dry_run_only: bool = False  # the config describes a dry run: campaign.py always plans it as one
    dry_run_projects: Tuple[str, ...] = ()  # non-empty: the dry run is the full plan of these projects
    force: Tuple[Tuple[str, str], ...] = ()  # (server kind, repo)
    exclude: Tuple[Tuple[str, str], ...] = ()  # (server kind or "*", repo)
    overrides: Mapping[str, ProjectOverride] = field(default_factory=dict)
    case_projects: Tuple[CaseProject, ...] = ()
    bench_cases: Tuple[BenchCase, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def kinds(self) -> List[str]:
        """Server kinds in configuration order: the servers, then the benchmark cases' kinds."""
        out = [s.kind for s in self.servers]
        return out + [k for k in dict.fromkeys(b.kind for b in self.bench_cases) if k not in out]


@dataclass(frozen=True)
class RunSpec:
    campaign: str
    oracle: str
    server_kind: str
    server_version: str
    project: str
    source: str  # corpus | case | dir
    project_ref: str
    language: str
    seed: int
    timing: str = "settled"
    max_cases: int = 12
    max_files: int = 3
    max_positions_per_file: int = 12
    max_file_bytes: int = 256_000
    exclude_dirs: Tuple[str, ...] = ()
    settings: Optional[Mapping[str, Any]] = None
    settings_attr: str = ""
    settle_timeout_s: float = 300.0
    request_timeout_s: float = 30.0
    run_timeout_s: float = 7200.0
    commit: str = ""
    min_identifiers: int = 8

    @property
    def run_id(self) -> str:
        return make_run_id(self.oracle, self.server_kind, self.server_version, self.project, self.seed, self.timing)

    def to_json(self) -> Dict[str, Any]:
        d = asdict(self)
        d["exclude_dirs"] = list(self.exclude_dirs)
        d["run_id"] = self.run_id
        return d

    @staticmethod
    def from_json(d: Mapping[str, Any]) -> "RunSpec":
        known = {k: v for k, v in d.items() if k in RunSpec.__dataclass_fields__}
        known["exclude_dirs"] = tuple(known.get("exclude_dirs") or ())
        return RunSpec(**known)

    def result_affecting(self) -> Dict[str, Any]:
        """Parameters that change what a run computes (a resumed campaign must not change them)."""
        d = self.to_json()
        for k in ("campaign", "run_timeout_s"):
            d.pop(k, None)
        return d


def make_run_id(oracle: str, kind: str, version: str, project: str, seed: int, timing: str) -> str:
    return hashlib.sha1(f"{oracle}|{kind}|{version}|{project}|{seed}|{timing}".encode()).hexdigest()[:12]


# ------------------------------------------------------------------ parsing
def _seed_list(value: Any, where: str) -> List[int]:
    if isinstance(value, bool) or not isinstance(value, (int, list)):
        raise ConfigError(f"{where}: seeds must be a count or a list of integers")
    seeds = list(range(1, value + 1)) if isinstance(value, int) else value
    if any(isinstance(s, bool) or not isinstance(s, int) for s in seeds) or len(set(seeds)) != len(seeds):
        raise ConfigError(f"{where}: seeds must be distinct integers")
    return seeds


def interleave_rounds(seeds: Sequence[Tuple[str, Sequence[int]]]) -> Tuple[Tuple[str, int], ...]:
    """(timing, seed) rounds with the timings interleaved: settled 1, race0 1, settled 2, ..."""
    out: List[Tuple[str, int]] = []
    for i in range(max((len(s) for _, s in seeds), default=0)):
        out += [(t, s[i]) for t, s in seeds if i < len(s)]
    return tuple(out)


def _oracle(name: str, d: Mapping[str, Any], kinds: Sequence[str]) -> OracleCfg:
    if name not in ORACLE_MODULES:
        raise ConfigError(f"unknown oracle {name!r}; known: {list(ORACLE_MODULES)}")
    seeds = d.get("seeds", {"settled": 1})
    if not isinstance(seeds, dict) or not seeds:
        raise ConfigError(f"oracle {name}: seeds must map timing -> seeds")
    for timing in seeds:
        if timing not in TIMINGS:
            raise ConfigError(f"oracle {name}: unknown timing {timing!r}; known: {sorted(TIMINGS)}")
    servers = tuple(d.get("servers") or ())
    unknown = sorted(set(servers) - set(kinds))
    if unknown:
        raise ConfigError(f"oracle {name}: servers {unknown} are not configured")
    rounds = interleave_rounds([(t, _seed_list(v, f"oracle {name} {t}")) for t, v in seeds.items()])
    return OracleCfg(name, rounds, int(d.get("max_cases", 12)), servers)


def _bench_case(b: Mapping[str, Any]) -> BenchCase:
    builds = b.get("builds") or {}
    if set(builds) != set(PHASES) or builds["pre"] == builds["post"]:
        raise ConfigError(f"bench case {b.get('case')}: builds must name distinct pre and post versions")
    session = b.get("session") or {}
    return BenchCase(str(b["case"]), str(b["dir"]), str(b["kind"]), str(b["language"]),
                     tuple((p, str(builds[p])) for p in PHASES), b.get("settings") or None,
                     float(session.get("settle_timeout_s") or 0.0), float(session.get("request_timeout_s") or 0.0))


def parse_config(raw: Mapping[str, Any]) -> CampaignConfig:
    """Validate a parsed config; raises ConfigError with the first problem found."""
    unknown = sorted(set(raw) - TOP_KEYS)
    if unknown:
        raise ConfigError(f"unknown config keys {unknown}")
    cid = str(raw.get("id") or "")
    if not _ID.match(cid):
        raise ConfigError(f"config id {cid!r} must match {_ID.pattern}")
    servers = tuple(ServerCfg(str(s["kind"]), str(s["version"])) for s in raw.get("servers") or [])
    bench = tuple(_bench_case(b) for b in raw.get("bench_cases") or [])
    kinds = [s.kind for s in servers]
    if (not servers and not bench) or len(set(kinds)) != len(kinds):
        raise ConfigError("servers must be a list with one version per kind (non-empty unless bench_cases are given)")
    kinds += [b.kind for b in bench]
    oracles = tuple(_oracle(n, d or {}, kinds) for n, d in (raw.get("oracles") or {}).items())
    if not oracles:
        raise ConfigError("no oracles configured")
    tg, to, fl, dr = (raw.get(k) or {} for k in ("targets", "timeouts", "flake", "dry_run"))
    el = raw.get("eligibility") or {}
    overrides = {repo: ProjectOverride(tuple(o.get("exclude_dirs") or ()), o.get("settings"), str(o.get("reason", "")))
                 for repo, o in (raw.get("project_overrides") or {}).items()}
    cases = tuple(CaseProject(str(c["case"]), str(c["language"]), tuple(c.get("servers") or [s.kind for s in servers]),
                              str(c.get("settings_attr") or "")) for c in raw.get("case_projects") or [])
    for c in cases:
        if set(c.servers) - set(kinds):
            raise ConfigError(f"case project {c.case}: servers {sorted(set(c.servers) - set(kinds))} not configured")
    try:
        cap = parse_cap(raw.get("signature_cap"))
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    cfg = CampaignConfig(
        id=cid, servers=servers, oracles=oracles, description=str(raw.get("description", "")),
        corpus=str(raw.get("corpus", DEFAULT_CORPUS) or ""), max_files=int(tg.get("max_files", 3)),
        max_positions_per_file=int(tg.get("max_positions_per_file", 12)),
        max_file_bytes=int(tg.get("max_file_bytes", 256_000)), min_identifiers=int(tg.get("min_identifiers", 8)),
        settle_timeout_s=float(to.get("settle_s", 300)), request_timeout_s=float(to.get("request_s", 30)),
        run_timeout_s=float(to.get("run_s", 7200)), concurrency=int(raw.get("concurrency", 4)),
        server_limits={str(k): int(v) for k, v in (raw.get("server_limits") or {}).items()},
        wall_clock_budget_s=float(raw.get("wall_clock_budget_h", 0)) * 3600,
        flake_n=int(fl.get("n", 3)), per_signature=int(fl.get("per_signature", 1)), cap=cap,
        dry_run_max_cases=int(dr.get("max_cases", 2)), dry_run_only=bool(dr.get("only", False)),
        dry_run_projects=tuple(str(p) for p in dr.get("projects") or ()),
        force=tuple((str(x["server"]), str(x["repo"])) for x in el.get("force") or []),
        exclude=tuple((str(x.get("server", "*")), str(x["repo"])) for x in el.get("exclude") or []),
        overrides=overrides, case_projects=cases, bench_cases=bench, raw=dict(raw))
    if cfg.concurrency < 1 or cfg.flake_n < 1 or cfg.per_signature < 1 or cfg.cap.runs < 0:
        raise ConfigError("concurrency, flake.n and flake.per_signature must be at least 1, signature_cap.runs >= 0")
    if any(v < 1 or k not in kinds for k, v in cfg.server_limits.items()):
        raise ConfigError("server_limits: configured server kinds with a limit of at least 1")
    return cfg


def load_config(path: str) -> CampaignConfig:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: a config is a JSON object")
    return parse_config(raw)


def dry_run_config(cfg: CampaignConfig) -> CampaignConfig:
    """The campaign id of a dry run: `<id>-dryrun` (unchanged when the id already names a dry run)."""
    return cfg if cfg.id.endswith("dryrun") else replace(cfg, id=f"{cfg.id}-dryrun")


__all__ = ["BenchCase", "CampaignConfig", "CaseProject", "ConfigError", "OracleCfg", "PHASES", "ProjectOverride",
           "RunSpec", "ServerCfg", "dry_run_config", "interleave_rounds", "load_config", "make_run_id", "parse_config"]
