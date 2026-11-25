"""Campaign outputs and shared (de)serialization (plan/tool_design_v1.md sections 7 and 11).

Layout under data/lsptest/runs/<campaign>/: config.json, results.jsonl, violations.jsonl,
progress.log, violations/<vid>/{repro.json, logs/*.jsonl.gz}, candidates/<run_id>.jsonl.gz,
worker_logs/<run_id>.log and triage/. Scratch: temp/lsptest_runs/<campaign>/<run_id>/ (removed
after each run) and temp/lsptest_runs/<campaign>/projects/ (benchmark-case projects).
Also here: Violation from JSON, the repro.json document and the OracleContext rebuilt from it,
project directories (prepared corpus clone, or a benchmark case built from its historical
files by validate_known_bugs.build_project), server build identities and JSONL helpers.

Run line: imported by campaign.py, campaign_run.py, repro_violation.py and triage.py; not run directly.
"""

from __future__ import annotations

import dataclasses
import glob
import gzip
import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import servers  # noqa: E402  (lsp_repro)
from driver import RUNS_DIR, SESSION_SETTINGS, clone_tree  # noqa: E402
from model import QueryKey, Violation  # noqa: E402
from oracles.base import OracleContext, case_of, shape_of  # noqa: E402
from ops import deep_merge, ops_from_json, write_text  # noqa: E402
from targets import EXCLUDED_DIRS, FileTargets, TargetConfig, choose_targets, targets_from_json, targets_to_json  # noqa: E402

logger = logging.getLogger(__name__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_ROOT = os.path.join(REPO, "data", "lsptest", "runs")
CASES_DIR = os.path.join(REPO, "scripts", "lsp_repro", "cases")
REPRO_FORMAT = 1


@dataclass(frozen=True)
class CampaignPaths:
    root: str
    scratch: str

    @property
    def config(self) -> str:
        return os.path.join(self.root, "config.json")

    @property
    def results(self) -> str:
        return os.path.join(self.root, "results.jsonl")

    @property
    def violations(self) -> str:
        return os.path.join(self.root, "violations.jsonl")

    @property
    def progress(self) -> str:
        return os.path.join(self.root, "progress.log")

    @property
    def triage(self) -> str:
        return os.path.join(self.root, "triage")

    def violation_dir(self, vid: str) -> str:
        return os.path.join(self.root, "violations", vid)

    def worker_log(self, run_id: str) -> str:
        return os.path.join(self.root, "worker_logs", f"{run_id}.log")

    def candidates(self, run_id: str) -> str:
        return os.path.join(self.root, "candidates", f"{run_id}.jsonl.gz")

    def run_scratch(self, run_id: str) -> str:
        return os.path.join(self.scratch, run_id)

    def projects(self) -> str:
        return os.path.join(self.scratch, "projects")


def paths_for(campaign_id: str, out_root: str = OUT_ROOT, runs_dir: str = RUNS_DIR) -> CampaignPaths:
    return CampaignPaths(os.path.join(out_root, campaign_id), os.path.join(runs_dir, campaign_id))


def rel(path: Optional[str]) -> str:
    """Repository-relative path (unchanged when outside the repository)."""
    if not path:
        return ""
    ab = os.path.abspath(path)
    return os.path.relpath(ab, REPO) if ab.startswith(REPO + os.sep) else path


# ------------------------------------------------------------------ JSONL
def append_jsonl(path: str, rows: Iterable[Mapping[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    """Rows of a JSONL file; a torn last line (interrupted write) is skipped with a warning."""
    if not os.path.exists(path):
        return []
    out = []
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:  # type: ignore[operator]
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("%s:%d: unreadable line skipped", path, n)
    return out


def write_json(path: str, obj: Any) -> None:
    """Atomic JSON write (temp file + rename)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)
    os.replace(tmp, path)


def latest_rows(rows: Iterable[Mapping[str, Any]], key: str = "vid") -> List[Dict[str, Any]]:
    """The last row per `key` (a rerun replaces a row), in first-seen order."""
    last: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        if r.get(key):
            last[str(r[key])] = dict(r)
    return list(last.values())


def completed_runs(results_path: str) -> Dict[str, Dict[str, Any]]:
    """run_id -> the last results row of that run (a rerun after --retry-failed replaces it)."""
    return {r["run_id"]: r for r in read_jsonl(results_path) if r.get("run_id")}


# ------------------------------------------------------------------ violations
def violation_from_json(d: Mapping[str, Any]) -> Violation:
    return Violation(str(d["oracle"]), str(d["server"]), str(d["project"]), QueryKey(**d["key"]), d.get("expected"),
                     d.get("actual"), ops_from_json(d.get("ops") or []), str(d.get("detail", "")),
                     str(d.get("reproduced", "0/0")), ops_from_json(d.get("reduced_ops") or []),
                     str(d.get("signature", "")), str(d.get("run_id", "")))


def violation_to_json(v: Violation) -> Dict[str, Any]:
    return json.loads(v.to_json())


def note_of(v: Violation) -> str:
    try:
        return str(json.loads(v.detail).get("note", "")) if v.detail else ""
    except json.JSONDecodeError:
        return v.detail


def op_text(op: Any) -> str:
    """One op in one line: kind, path, range and text (file contents summarized by length)."""
    d = op.to_json()
    what = f"{d['kind']} {d.get('path', '')}".strip()
    if d["kind"] == "change":
        what += f" {tuple(d.get('start') or ())}-{tuple(d.get('end') or ())} {json.dumps(d.get('text', ''))}"
    elif d["kind"] == "request":
        what += f" {d.get('text')} at {tuple(d.get('start') or ())}"
    elif d["kind"] == "set_config":
        what += f" {json.dumps(d.get('settings'), sort_keys=True)}"
    elif d["kind"] == "fs_rename":
        what += f" -> {d.get('new_path')}"
    elif d["kind"] == "fs_write":
        what += f" ({len(d.get('text', ''))} chars)"
    return what + (f" (then {d['delay_ms']} ms)" if d.get("delay_ms") else "")


# ------------------------------------------------------------------ projects
def load_case(name: str) -> Any:
    from validate_known_bugs import load_case as _load  # late import: it registers r1_history
    return _load(name)


def build_case_project(case: str, dest: str) -> str:
    from validate_known_bugs import build_project  # late import (see load_case)
    return build_project(load_case(case), dest)


def case_sha(case: str) -> str:
    with open(os.path.join(CASES_DIR, f"{case}.py"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def project_dir(source: str, project_ref: str, scratch_projects: str) -> str:
    """The prepared corpus clone, or the benchmark-case project built under scratch_projects."""
    if source in ("corpus", "dir"):  # a prepared clone, or a benchmark case's project/ directory (read-only)
        return os.path.join(REPO, project_ref)
    if source != "case":
        raise ValueError(f"unknown project source {source!r}")
    dest = os.path.join(scratch_projects, project_ref)
    if not os.path.isdir(dest):
        build_case_project(project_ref, dest)
    return dest


def run_settings(kind: str, source: str, project_ref: str, override: Optional[Mapping[str, Any]],
                 settings_attr: str = "") -> Optional[Dict[str, Any]]:
    """OracleContext.extra_settings: None (driver defaults) unless the project names settings."""
    extra = dict(override or {})
    if source == "case" and settings_attr:
        extra = deep_merge(extra, getattr(load_case(project_ref), settings_attr) or {})
    return deep_merge(dict(SESSION_SETTINGS.get(kind, {})), extra) if extra else None


def choose_run_targets(root: str, language: str, seed: int, max_files: int, max_positions: int, max_bytes: int,
                       exclude_dirs: Iterable[str] = (), min_identifiers: int = 8) -> Tuple[FileTargets, ...]:
    if language == "java":
        from validate_known_bugs import java_targets  # late import (see load_case)
        return java_targets(root, seed, max_files, max_positions)
    cfg = TargetConfig(seed=seed, max_files=max_files, max_positions_per_file=max_positions, max_file_bytes=max_bytes,
                       min_identifiers=min_identifiers, exclude_dirs=EXCLUDED_DIRS | frozenset(exclude_dirs))
    return choose_targets(root, language, cfg)


def apply_files(root: str, files: Mapping[str, Optional[str]]) -> None:
    """Overwrite (text) or delete (None) project files, e.g. the line-reduced files of a triage repro."""
    for relpath, text in files.items():
        path = os.path.join(root, relpath)
        if text is None:
            if os.path.exists(path):
                os.remove(path)
        else:
            write_text(path, text)


# ------------------------------------------------------------------ repro.json
def repro_document(ctx: OracleContext, v: Violation, *, campaign: str, vid: str, source: str, project_ref: str,
                   commit: str = "", logs: Iterable[str] = (), files: Optional[Mapping[str, Optional[str]]] = None,
                   extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    doc = {"format": REPRO_FORMAT, "campaign": campaign, "vid": vid, "run_id": v.run_id, "oracle": v.oracle,
           "server": {"kind": ctx.server_kind, "version": ctx.server_version},
           "project": {"name": ctx.project, "source": source, "ref": project_ref, "commit": commit,
                       "language": ctx.language},
           "context": {"seed": ctx.seed, "timing": ctx.timing, "settle_timeout_s": ctx.settle_timeout_s,
                       "request_timeout_s": ctx.request_timeout_s, "extra_settings": ctx.extra_settings,
                       "max_cases": ctx.max_cases, "targets": targets_to_json(ctx.targets)},
           "key": asdict(v.key), "ops": [o.to_json() for o in v.ops], "case": case_of(v), "shape": shape_of(v),
           "signature": v.signature, "expected": v.expected, "actual": v.actual, "reproduced": v.reproduced,
           "note": note_of(v), "violation": violation_to_json(v), "replay_logs": list(logs),
           "project_files": dict(files or {})}
    doc.update(extra or {})
    return doc


def load_repro(path: str) -> Tuple[Dict[str, Any], Violation]:
    """The document and its violation, with the document's ops (reduced ops in a triage repro)."""
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    if doc.get("format") != REPRO_FORMAT:
        raise ValueError(f"{path}: unsupported repro format {doc.get('format')!r}")
    return doc, dataclasses.replace(violation_from_json(doc["violation"]), ops=ops_from_json(doc.get("ops") or []))


def context_from_repro(doc: Mapping[str, Any], root: str, work_dir: str, run_id: str = "") -> OracleContext:
    c, s, p = doc["context"], doc["server"], doc["project"]
    return OracleContext(run_id or f"{doc['run_id']}-repro", s["kind"], s["version"], p["name"], root, p["language"],
                         int(c["seed"]), targets_from_json(c["targets"]), c.get("timing", "settled"),
                         float(c.get("settle_timeout_s", 300.0)), float(c.get("request_timeout_s", 30.0)),
                         c.get("extra_settings"), int(c.get("max_cases", 12)), work_dir)


def prepare_repro_project(doc: Mapping[str, Any], scratch: str) -> str:
    """Project dir for replaying a repro. A corpus clone is used in place (never modified); a
    benchmark case is built under `scratch`; project_files (line-reduced files) go into an APFS
    clone under `scratch`. The caller removes `scratch` afterwards."""
    p, files = doc["project"], doc.get("project_files") or {}
    base = project_dir(p["source"], p["ref"], os.path.join(scratch, "projects"))
    if not files:
        return base
    dst = os.path.join(scratch, "project-with-files")
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(scratch, exist_ok=True)
    clone_tree(base, dst)
    apply_files(dst, files)
    return dst


# ------------------------------------------------------------------ environment
def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _package_version(path: str) -> str:
    d = os.path.dirname(path)
    while d.startswith(servers.SERVERS_DIR) and d != servers.SERVERS_DIR:
        pj = os.path.join(d, "package.json")
        if os.path.exists(pj):
            try:
                with open(pj, "r", encoding="utf-8") as f:
                    return str(json.load(f).get("version", ""))
            except (OSError, json.JSONDecodeError):
                return ""
        d = os.path.dirname(d)
    return ""


def server_build(kind: str, version: str) -> Dict[str, Any]:
    """How a pinned build is launched and which binary it is (sha256 of its entry file)."""
    try:
        spec = servers.resolve(kind, version)
    except (FileNotFoundError, ValueError) as exc:
        return {"kind": kind, "version": version, "error": str(exc)[:300]}
    entry = next((c for c in spec.cmd if os.path.isfile(c) and os.path.abspath(c).startswith(servers.SERVERS_DIR)), "")
    out = {"kind": kind, "version": version, "label": spec.label, "cmd": [rel(c) for c in spec.cmd],
           "entry": rel(entry), "sha256": _sha256(entry) if entry else "", "package_version": _package_version(entry)}
    if os.path.basename(spec.cmd[0]).startswith("node"):
        try:
            out["node"] = subprocess.run([spec.cmd[0], "--version"], capture_output=True, text=True,
                                         timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            out["node"] = ""
    return out


def machine_info() -> Dict[str, Any]:
    return {"platform": platform.platform(), "mac_ver": platform.mac_ver()[0], "machine": platform.machine(),
            "python": platform.python_version(), "cpus": os.cpu_count()}


def sweep_session_dirs(run_id: str, runs_dir: str = RUNS_DIR) -> List[str]:
    """Remove driver session directories of a run left behind by a killed worker."""
    gone = []
    for d in glob.glob(os.path.join(runs_dir, f"*-{run_id}-*")):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
            gone.append(d)
    return gone


__all__ = ["CampaignPaths", "OUT_ROOT", "REPRO_FORMAT", "append_jsonl", "apply_files", "build_case_project",
           "case_sha", "choose_run_targets", "completed_runs", "context_from_repro", "latest_rows", "load_case",
           "load_repro",
           "machine_info", "note_of", "op_text", "paths_for", "prepare_repro_project", "project_dir", "read_jsonl",
           "rel",
           "repro_document", "run_settings", "server_build", "sweep_session_dirs", "violation_from_json",
           "violation_to_json", "write_json"]
