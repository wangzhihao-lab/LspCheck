"""Benchmark case format: data/lsp_bench/cases/<server>-<number>/{case.json, project/}.

case.json (schema 1):
  id          "<server>-<number>" (the directory name)
  meta        server (candidate list name: pyright | tsserver | rust-analyzer | gopls), kind (server
              kind in the registry, servers.SERVER_FACTORY), number, url, title, oracle_class (R1-R5),
              subtype, fix_ref, fix_shas, pre_version / post_version (upstream release names),
              pre_build / post_build (registry version strings), build_notes, effort_minutes;
              optional toolchain (era Go for gopls), wrapper, candidate_rank, notes
  language    python | typescript | javascript | rust | go | java
  settings    client settings named in the issue (merged over the session defaults); settings_note
  session     optional DriverConfig overrides: pull_diagnostics, settle_timeout_s, request_timeout_s
  files       every file under project/, each {path, provenance, source, note}; provenance is
              issue (verbatim from the issue text: non-blank lines, stripped, in order),
              issue-adapted (derived from the issue; note says how), repo (source
              "owner/repo@sha:path", byte-equal) or scaffold (at most 40 lines, note required)
  repro       attempt (1 or 2), timing (settled: settle after every op; race: ops keep their own
              delay_ms and the server is settled only at {"kind": "wait", "text": "settle"}
              markers and after the last op), steps (the issue's steps in words), ops (model.Op
              JSON), probe {type, params} (probes.PROBES)
  attempts    earlier attempts: [{attempt, timing, summary, verdict}] (at most two honest attempts)
validate_case() returns every problem found; provenance is checked against the cached issue
text (sources.py) and reported as unverified when that is not cached.

Run line: python3 scripts/lsptest/bench/case_format.py [<case dir> ...]  (validates; all cases by default)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
for _p in (PKG, os.path.join(os.path.dirname(PKG), "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from model import Op  # noqa: E402
from ops import LineIndex, OpError, apply_change, ops_from_json, read_text  # noqa: E402

REPO = os.path.abspath(os.path.join(PKG, "..", ".."))
CASES_DIR = os.path.join(REPO, "data", "lsp_bench", "cases")
SCHEMA = 1
META_KEYS = ("server", "kind", "number", "url", "title", "oracle_class", "subtype", "fix_ref", "fix_shas",
             "pre_version", "post_version", "pre_build", "post_build", "build_notes", "effort_minutes")
LANGUAGES = ("python", "typescript", "javascript", "rust", "go", "java")
PROVENANCE = ("issue", "issue-adapted", "repo", "scaffold")
TIMINGS = ("settled", "race")
SCAFFOLD_MAX_LINES = 40
SETTLE_MARK = "settle"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileEntry:
    path: str
    provenance: str
    source: str = ""
    note: str = ""


@dataclass(frozen=True)
class Repro:
    attempt: int
    timing: str
    steps: str
    ops: Tuple[Op, ...]
    probe: Dict[str, Any]


@dataclass(frozen=True)
class Case:
    case_id: str
    root: str
    meta: Dict[str, Any]
    language: str
    files: Tuple[FileEntry, ...]
    repro: Repro
    settings: Dict[str, Any] = field(default_factory=dict)
    session: Dict[str, Any] = field(default_factory=dict)
    attempts: Tuple[Dict[str, Any], ...] = ()
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def project_dir(self) -> str:
        return os.path.join(self.root, "project")

    def build(self, phase: str) -> str:
        return str(self.meta[f"{phase}_build"])


class CaseError(ValueError):
    """case.json cannot be read as a case at all (validate_case reports everything else)."""


def load_case(case_dir: str) -> Case:
    path = os.path.join(case_dir, "case.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as exc:
        raise CaseError(f"{path}: {exc}") from exc
    try:
        r = raw["repro"]
        repro = Repro(int(r.get("attempt", 1)), str(r.get("timing", "settled")), str(r.get("steps", "")),
                      tuple(ops_from_json(r.get("ops") or [])), dict(r.get("probe") or {}))
        files = tuple(FileEntry(str(f["path"]), str(f.get("provenance", "")), str(f.get("source", "")),
                                str(f.get("note", ""))) for f in raw.get("files") or [])
        return Case(str(raw.get("id", "")), os.path.abspath(case_dir), dict(raw.get("meta") or {}),
                    str(raw.get("language", "")), files, repro, dict(raw.get("settings") or {}),
                    dict(raw.get("session") or {}), tuple(raw.get("attempts") or ()), raw)
    except (KeyError, TypeError, ValueError, OpError) as exc:
        raise CaseError(f"{path}: {type(exc).__name__}: {exc}") from exc


def list_cases(root: str = CASES_DIR) -> List[str]:
    if not os.path.isdir(root):
        return []
    return sorted(os.path.join(root, d) for d in os.listdir(root) if os.path.exists(os.path.join(root, d, "case.json")))


def project_files(project_dir: str) -> List[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        out += [os.path.relpath(os.path.join(dirpath, n), project_dir).replace(os.sep, "/") for n in filenames
                if n != ".DS_Store"]
    return sorted(out)


# ------------------------------------------------------------------ validation
def _check_meta(case: Case) -> List[str]:
    errs = [f"meta.{k} missing" for k in META_KEYS if k not in case.meta]
    m = case.meta
    if case.case_id != os.path.basename(case.root):
        errs.append(f"id {case.case_id!r} differs from the directory name")
    if m.get("server") and m.get("number") and case.case_id != f"{m['server']}-{m['number']}":
        errs.append("id must be <server>-<number>")
    if m.get("oracle_class") not in ("R1", "R2", "R3", "R4", "R5"):
        errs.append(f"meta.oracle_class {m.get('oracle_class')!r}")
    if case.language not in LANGUAGES:
        errs.append(f"language {case.language!r} not in {LANGUAGES}")
    try:
        import servers  # noqa: WPS433 (registry; servers_extra registers the remaining kinds)
        import servers_extra  # noqa: F401
        if m.get("kind") not in servers.SERVER_FACTORY:
            errs.append(f"meta.kind {m.get('kind')!r} not in the server registry")
    except ImportError as exc:
        errs.append(f"server registry not importable: {exc}")
    if m.get("pre_build") == m.get("post_build"):
        errs.append("pre_build equals post_build")
    return errs


def _check_files(case: Case, offline: bool = True) -> Tuple[List[str], List[str]]:
    """(problems, notes) for the file list and each file's provenance."""
    errs: List[str] = []
    notes: List[str] = []
    listed = {f.path for f in case.files}
    on_disk = set(project_files(case.project_dir))
    errs += [f"file {p} listed but missing under project/" for p in sorted(listed - on_disk)]
    errs += [f"file {p} under project/ has no provenance entry" for p in sorted(on_disk - listed)]
    issue_text: Optional[str] = None
    for f in case.files:
        if f.provenance not in PROVENANCE:
            errs.append(f"{f.path}: provenance {f.provenance!r} not in {PROVENANCE}")
            continue
        if f.path not in on_disk:
            continue
        text = read_text(os.path.join(case.project_dir, f.path))
        if f.provenance in ("issue-adapted", "scaffold") and not f.note:
            errs.append(f"{f.path}: {f.provenance} needs a note")
        if f.provenance == "scaffold" and len(text.splitlines()) > SCAFFOLD_MAX_LINES:
            errs.append(f"{f.path}: scaffolding longer than {SCAFFOLD_MAX_LINES} lines")
        if f.provenance == "issue":
            from bench.sources import SourceError, issue_text as fetch_issue, verbatim_in
            try:
                issue_text = issue_text if issue_text is not None else fetch_issue(
                    str(case.meta.get("server")), int(case.meta.get("number", 0)), offline=offline)
            except (SourceError, KeyError, ValueError) as exc:
                notes.append(f"{f.path}: provenance unverified ({exc})")
                continue
            ok, line = verbatim_in(text, issue_text)
            if not ok:
                errs.append(f"{f.path}: not verbatim in the issue (first missing line: {line!r})")
        if f.provenance == "repo":
            errs += _check_repo_file(f, text, offline, notes)
    return errs, notes


def _check_repo_file(f: FileEntry, text: str, offline: bool, notes: List[str]) -> List[str]:
    from bench.sources import SourceError, raw_file
    try:
        repo_sha, path = f.source.split(":", 1)
        repo, sha = repo_sha.split("@", 1)
    except ValueError:
        return [f"{f.path}: repo provenance needs source 'owner/repo@sha:path'"]
    try:
        upstream = raw_file(repo, sha, path, offline=offline)
    except SourceError as exc:
        notes.append(f"{f.path}: provenance unverified ({exc})")
        return []
    return [] if upstream.replace("\r\n", "\n") == text.replace("\r\n", "\n") else [f"{f.path}: differs from {f.source}"]


def _check_ops(case: Case) -> Tuple[List[str], Dict[str, str]]:
    """Replay the ops on the project texts; returns (problems, final texts of touched files)."""
    errs: List[str] = []
    texts: Dict[str, str] = {}
    open_docs: Dict[str, bool] = {}

    def text_of(p: str) -> Optional[str]:
        if p in texts:
            return texts[p]
        try:
            return read_text(os.path.join(case.project_dir, p))
        except OSError:
            return None

    for i, op in enumerate(case.repro.ops):
        where = f"repro.ops[{i}] {op.kind} {op.path}"
        if op.kind == "wait":
            if op.text == SETTLE_MARK and case.repro.timing != "race":
                errs.append(f"{where}: settle markers only make sense in race timing")
            continue
        cur = text_of(op.path)
        if op.kind != "fs_write" and cur is None:
            errs.append(f"{where}: no such file")
            continue
        try:
            if op.kind == "open":
                if open_docs.get(op.path):
                    errs.append(f"{where}: already open")
                open_docs[op.path] = True
            elif op.kind == "close":
                open_docs[op.path] = False
            elif op.kind == "change":
                if not open_docs.get(op.path):
                    errs.append(f"{where}: document not open")
                texts[op.path] = apply_change(cur or "", op.start, op.end, op.text)[0]  # type: ignore[arg-type]
            elif op.kind == "fs_write":
                texts[op.path] = op.text
            elif op.kind == "request":
                if not open_docs.get(op.path):
                    errs.append(f"{where}: document not open")
                LineIndex(cur or "").offset(op.start or (-1, -1))
        except OpError as exc:
            errs.append(f"{where}: {exc}")
    return errs, texts


def _check_probe(case: Case, final_texts: Mapping[str, str]) -> List[str]:
    from bench.probes import PROBES
    probe = case.repro.probe
    p = PROBES.get(str(probe.get("type")))
    if p is None:
        return [f"probe.type {probe.get('type')!r} not in {sorted(PROBES)}"]
    params = probe.get("params") or {}
    errs = [f"probe: {e}" for e in p.validate(params, [o.to_json() for o in case.repro.ops])]
    if errs:
        return errs
    original = probe.get("type") == "transform_differs"
    plan = p.queries(params)
    unique = {json.dumps(q, sort_keys=True): q for name in ("case", "fresh") for q in plan.get(name, [])}
    for q in unique.values():
        path = str(q.get("path"))
        text = None if original else final_texts.get(path)
        if text is None:
            try:
                text = read_text(os.path.join(case.project_dir, path))
            except OSError:
                errs.append(f"probe query {q}: no such file")
                continue
        if isinstance(q.get("position"), list):
            try:
                LineIndex(text).offset(tuple(q["position"]))
            except OpError as exc:
                errs.append(f"probe query {q.get('method')} {path}: {exc}")
    return errs


def validate_case(case: Case, offline: bool = True) -> Tuple[List[str], List[str]]:
    """(problems, notes); a case with problems must not be run."""
    errs = _check_meta(case)
    if case.raw.get("schema") != SCHEMA:
        errs.append(f"schema must be {SCHEMA}")
    if case.repro.timing not in TIMINGS:
        errs.append(f"repro.timing {case.repro.timing!r} not in {TIMINGS}")
    if case.repro.attempt not in (1, 2):
        errs.append("repro.attempt must be 1 or 2 (at most two honest attempts)")
    if not case.repro.steps:
        errs.append("repro.steps (the issue's steps in words) missing")
    file_errs, notes = _check_files(case, offline)
    op_errs, final_texts = _check_ops(case)
    return errs + file_errs + op_errs + _check_probe(case, final_texts), notes


def main(argv: Sequence[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    bad = 0
    for d in list(argv) or list_cases():
        try:
            errs, notes = validate_case(load_case(d))
        except CaseError as exc:
            errs, notes = [str(exc)], []
        bad += 1 if errs else 0
        print(f"{os.path.basename(os.path.abspath(d))}: {'ok' if not errs else 'INVALID'}")
        for line in errs + [f"note: {n}" for n in notes]:
            print(f"  {line}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


__all__ = ["CASES_DIR", "Case", "CaseError", "FileEntry", "LANGUAGES", "PROVENANCE", "Repro", "SETTLE_MARK",
           "list_cases", "load_case", "project_files", "validate_case"]
