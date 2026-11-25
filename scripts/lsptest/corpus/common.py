"""Shared configuration of the corpus preparation: paths, the language -> server
table, the constants of the file-pick and noise heuristics, the project spec, and the
capped subprocess runner every phase uses.

"Import noise" and "overwhelming noise" are heuristics documented next to their
constants below and restated in the generated markdown report (report.py).

Only temp/corpus/, temp/corpus_probe/, data/lsptest/corpus_prepared.* and
data/lsptest/logs/prepare_corpus/ are ever written by the package.

Run line: imported by the corpus package and scripts/lsptest/prepare_corpus.py; not run directly.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------- paths
PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/lsptest
REPO = os.path.abspath(os.path.join(PKG, "..", ".."))
CORPUS_JSON = os.path.join(REPO, "data", "lsptest", "corpus.json")
CORPUS_DIR = os.path.join(REPO, "temp", "corpus")
PROBE_DIR = os.path.join(REPO, "temp", "corpus_probe")
LOG_DIR = os.path.join(REPO, "data", "lsptest", "logs", "prepare_corpus")
OUT_JSON = os.path.join(REPO, "data", "lsptest", "corpus_prepared.json")
OUT_MD = os.path.join(REPO, "data", "lsptest", "corpus_prepared.md")

GOPATH_DIR = os.path.join(REPO, "temp", "lsp_servers", "gopath")
RUSTUP_BIN = "/opt/homebrew/opt/rustup/bin"
CARGO_HOME = os.path.expanduser("~/.cargo")

# ----------------------------------------------------------------- languages
LANGUAGE_SERVERS: Dict[str, List[Tuple[str, str]]] = {
    "python": [("pyright", "1.1.414")],
    "typescript": [("ts6", "6.0.3"), ("ts7", "7.0.2")],
    "rust": [("rust-analyzer", "2026-09-21")],
    "go": [("gopls", "v0.23.0")],
}
LANG_EXT: Dict[str, Tuple[str, ...]] = {
    "python": (".py",), "typescript": (".ts", ".tsx"), "rust": (".rs",), "go": (".go",),
}
LANGUAGE_ID_BY_EXT: Dict[str, str] = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescriptreact", ".rs": "rust", ".go": "go",
}
SEVERITY_NAMES: Dict[int, str] = {1: "error", 2: "warning", 3: "information", 4: "hint"}
CLONE_OK = ("ok", "already-prepared")  # clone statuses a project can be probed from

# Directories never opened as source, regardless of language: dependency
# trees, build/output artifacts and generated or fixture-only content.
SKIP_DIR_NAMES = {
    "node_modules", "vendor", "vendored", "target", "dist", "build", "out",
    "generated", "__generated__", "testdata", "fixtures", "__fixtures__",
    "test-fixtures", "test_fixtures", "coverage", "__pycache__", "venv",
    ".mypy_cache", ".pytest_cache", "htmlcov",
}
SKIP_FILENAME_MARKERS = (".min.", ".pb.go", "_pb2.py", ".generated.", "_generated.")

# "Import noise" heuristic: diagnostics that are almost certainly a side
# effect of not having installed dependencies (unresolved import/package),
# not a real bug in the workspace. Matched on structured `code` when the
# server gives one, else on the message text.
IMPORT_NOISE_RE = re.compile(
    r"cannot find module|could not be resolved|unresolved import|cannot find package|"
    r"no required module provides package|could not import|missing go\.sum entry|"
    r"has no exported member|is not a module|unable to import|import cycle not allowed",
    re.I,
)
TS_IMPORT_CODES = {"2307", "2306", "2792", "7016"}
PYRIGHT_IMPORT_CODES = {"reportMissingImports", "reportMissingModuleSource"}

# "Overwhelming noise" exclusion heuristic (see report.write_markdown_report).
NOISE_MIN_COUNT = 100
NOISE_MIN_RATIO = 0.7
NOISE_MIN_RATIO_COUNT = 20

SETTLE_CAP_DEFAULT = 600.0


@dataclass(frozen=True)
class ProjectSpec:
    """One pinned project of data/lsptest/corpus.json."""

    language: str
    owner: str
    repo: str
    commit: str
    stars: int
    size_kb: int

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def commit12(self) -> str:
        return self.commit[:12]

    @property
    def slug(self) -> str:
        return f"{self.owner}__{self.repo}@{self.commit12}"


@dataclass(frozen=True)
class CmdResult:
    """Outcome of one run_cmd call; `tail` is kept only when the command failed."""

    ok: bool
    returncode: Optional[int]
    timed_out: bool
    elapsed_s: float
    tail: str


# ------------------------------------------------------------------ corpus
def load_projects(languages: Sequence[str], only_repo: Optional[str], limit: Optional[int],
                  corpus_json: str = CORPUS_JSON) -> List[ProjectSpec]:
    """Projects of `corpus_json` in file order, filtered by language, by an
    owner/repo substring (case-insensitive) and capped at `limit` per language."""
    with open(corpus_json, encoding="utf-8") as f:
        data = json.load(f)
    out: List[ProjectSpec] = []
    for lang, items in data["corpus"].items():
        if languages and lang not in languages:
            continue
        count = 0
        for it in items:
            if only_repo and only_repo.lower() not in it["repo"].lower():
                continue
            owner, repo = it["repo"].split("/", 1)
            out.append(ProjectSpec(language=lang, owner=owner, repo=repo, commit=it["commit"],
                                   stars=it["stars"], size_kb=it["size_kb"]))
            count += 1
            if limit and count >= limit:
                break
    return out


# --------------------------------------------------------------- subprocess
def run_cmd(cmd: List[str], cwd: str, env: Optional[Dict[str, str]] = None,
            timeout_s: float = 900.0, tail_chars: int = 4000) -> CmdResult:
    """Run `cmd`, capped at `timeout_s` (<= 900s / 15 min per the corpus-prep
    contract). Output is only kept (tail_chars from the end) when the command
    fails, so successful runs stay cheap to store."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=full_env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout_s)
        ok = proc.returncode == 0
        tail = "" if ok else _tail(proc.stdout, proc.stderr, tail_chars)
        return CmdResult(ok=ok, returncode=proc.returncode, timed_out=False,
                         elapsed_s=time.monotonic() - t0, tail=tail)
    except subprocess.TimeoutExpired as e:
        out = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "replace")
        err = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode("utf-8", "replace")
        return CmdResult(ok=False, returncode=None, timed_out=True,
                         elapsed_s=time.monotonic() - t0, tail=_tail(out, err, tail_chars))
    except OSError as e:
        return CmdResult(ok=False, returncode=None, timed_out=False,
                         elapsed_s=time.monotonic() - t0, tail=str(e)[:tail_chars])


def _tail(stdout: Optional[str], stderr: Optional[str], n: int) -> str:
    combined = (stdout or "") + "\n--- stderr ---\n" + (stderr or "")
    return combined[-n:]


def dir_size_bytes(path: str) -> int:
    """Total size of the regular files under `path` (symlinks not followed)."""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
            except OSError:
                pass
    return total


__all__ = [
    "CARGO_HOME", "CLONE_OK", "CORPUS_DIR", "CORPUS_JSON", "CmdResult", "GOPATH_DIR", "IMPORT_NOISE_RE",
    "LANGUAGE_ID_BY_EXT", "LANGUAGE_SERVERS", "LANG_EXT", "LOG_DIR", "NOISE_MIN_COUNT", "NOISE_MIN_RATIO",
    "NOISE_MIN_RATIO_COUNT", "OUT_JSON", "OUT_MD", "PKG", "PROBE_DIR", "PYRIGHT_IMPORT_CODES", "ProjectSpec",
    "REPO", "RUSTUP_BIN", "SETTLE_CAP_DEFAULT", "SEVERITY_NAMES", "SKIP_DIR_NAMES", "SKIP_FILENAME_MARKERS",
    "TS_IMPORT_CODES", "dir_size_bytes", "load_projects", "run_cmd",
]
