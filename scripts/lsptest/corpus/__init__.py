"""Corpus preparation for lsptest: the library behind scripts/lsptest/prepare_corpus.py.

Imported as the package `corpus` with scripts/lsptest on sys.path; the modules that
need scripts/lsp_repro (probe, probe_settle) put it on the path themselves.

- common:       paths, language -> server table, file-pick and noise-heuristic constants,
                ProjectSpec, load_projects, run_cmd (capped subprocess), dir_size_bytes
- clone_deps:   pinned shallow clone (token retry never persisted), dependency fetch
                without install scripts (corepack-selected package manager for typescript,
                cargo fetch, go mod download with the go-too-new check), prepare_all
- probe_settle: push / pull / serverStatus settle waits, publishDiagnostics lookup by
                decoded case-folded path (settle.uri_key), diagnostics summary
- probe:        source-file pick, throwaway probe copy, one server session per unit
- records:      per-unit decisions (reuse / probe / skip-probe), merge-on-save
- report:       data/lsptest/corpus_prepared.md

Run line: imported by scripts/lsptest/prepare_corpus.py; not run directly.
"""

from .clone_deps import prepare_all, prepare_clone, prepare_project
from .common import (
    CORPUS_DIR, LANGUAGE_SERVERS, LOG_DIR, OUT_JSON, OUT_MD, PROBE_DIR, SETTLE_CAP_DEFAULT, ProjectSpec,
    dir_size_bytes, load_projects,
)
from .probe import pid_alive, run_probe, select_open_files
from .probe_settle import latest_publishes, published_diagnostics, wait_push_settle
from .records import ProbeOptions, load_prev_results, merge_and_save, probe_units
from .report import recommend_exclusions, write_markdown_report

__all__ = [
    "CORPUS_DIR", "LANGUAGE_SERVERS", "LOG_DIR", "OUT_JSON", "OUT_MD", "PROBE_DIR", "SETTLE_CAP_DEFAULT",
    "ProbeOptions", "ProjectSpec", "dir_size_bytes", "latest_publishes", "load_prev_results", "load_projects",
    "merge_and_save", "pid_alive", "prepare_all", "prepare_clone", "prepare_project", "probe_units",
    "published_diagnostics", "recommend_exclusions", "run_probe", "select_open_files", "wait_push_settle",
    "write_markdown_report",
]
