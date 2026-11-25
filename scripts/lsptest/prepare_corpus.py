"""Prepare the lsptest project corpus: clone each pinned commit, fetch
dependencies without running install scripts, and measure how long each
paired language server takes to settle on the first few source files.

Pipeline (idempotent -- safe to interrupt and rerun):
  1. Shallow-clone each of the 40 projects in data/lsptest/corpus.json at its
     pinned commit into temp/corpus/<owner>__<repo>@<sha12>/. All git calls go
     through subprocess directly (never as literal Bash text) because this
     project's interactive shell rewrites literal `git log`/`git show` output.
     GITHUB_TOKEN, when set, is used only for one retry of a failed fetch and
     is never persisted or logged.
  2. Fetch dependencies without running install scripts: npm/pnpm/yarn/bun for
     typescript (the package manager pinned in package.json runs via corepack),
     `cargo fetch` for rust, `go mod download` for go (a go directive newer than
     the local toolchain is recorded as go-too-new), nothing for python
     (existence of pyproject.toml/setup.py is recorded).
  3. For each prepared project and each server registered for its language
     (python->pyright, typescript->ts6+ts7, rust->rust-analyzer, go->gopls),
     open the first 3 source files (sorted path order, generated/vendored/
     node_modules/target/test-fixture paths skipped) in a throwaway `cp -cR`
     copy under temp/corpus_probe/ and measure how long the server takes to
     settle, with a hard cap. Push servers settle on publishDiagnostics for
     every opened file (matched by decoded, case-folded path) plus 3s of total
     quiet; pull servers (ts7, rust-analyzer) settle when two consecutive
     textDocument/diagnostic polls agree; rust-analyzer additionally waits for
     a quiescent experimental/serverStatus notification. A completed probe on
     disk is reused unless --force-probe; --skip-probe never discards one.
  4. Write data/lsptest/corpus_prepared.json (one record per project x
     server, merged into the file on disk, never overwriting other projects'
     records) and data/lsptest/corpus_prepared.md (table + exclusion list).

The work is done by the package scripts/lsptest/corpus/ (common, clone_deps,
probe_settle, probe, records, report); this file is the command line.
"Import noise" and "overwhelming noise" are heuristics documented next to their
constants in corpus/common.py and restated in the generated markdown report.

Only touches temp/corpus/, temp/corpus_probe/, data/lsptest/corpus_prepared.*
and data/lsptest/logs/prepare_corpus/. Never touches temp/lsptest_fixtures or
temp/lsptest_runs, and only ever signals server processes this run itself
spawned (tracked by pid).

Run line: python3 scripts/lsptest/prepare_corpus.py
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Set

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from corpus import (  # noqa: E402
    CORPUS_DIR, LANGUAGE_SERVERS, LOG_DIR, OUT_JSON, OUT_MD, PROBE_DIR, SETTLE_CAP_DEFAULT, ProbeOptions,
    dir_size_bytes, load_prev_results, load_projects, merge_and_save, pid_alive, prepare_all, probe_units,
    write_markdown_report,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """The command line (options unchanged since the single-file version)."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--languages", default="typescript,python,rust,go",
                    help="comma-separated subset of typescript,python,rust,go")
    ap.add_argument("--limit", type=int, default=None, help="max projects per language")
    ap.add_argument("--only-repo", default=None, help="substring filter on owner/repo")
    ap.add_argument("--skip-deps", action="store_true", help="skip dependency fetch (clone only)")
    ap.add_argument("--skip-probe", action="store_true", help="skip the LSP settle measurement phase")
    ap.add_argument("--force-probe", action="store_true", help="re-measure even if a completed record exists")
    ap.add_argument("--settle-cap", type=float, default=SETTLE_CAP_DEFAULT,
                    help="seconds to wait for settle per project x server")
    ap.add_argument("--max-workers", type=int, default=4, help="parallel clone+deps workers")
    args = ap.parse_args()
    args.languages = [s.strip() for s in args.languages.split(",") if s.strip()]
    unknown = set(args.languages) - set(LANGUAGE_SERVERS)
    if unknown:
        ap.error(f"unknown language(s): {sorted(unknown)}")
    return args


def main() -> None:
    """Clone + deps (thread pool), then one probe at a time, then both reports."""
    args = parse_args()
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    for d in (CORPUS_DIR, PROBE_DIR, LOG_DIR, os.path.dirname(OUT_JSON)):
        os.makedirs(d, exist_ok=True)

    token = os.environ.get("GITHUB_TOKEN") or None
    projects = load_projects(args.languages, args.only_repo, args.limit)
    logger.info("loaded %d projects (%s)", len(projects), ", ".join(sorted({p.language for p in projects})))
    prep_by_slug = prepare_all(projects, args.skip_deps, token, args.max_workers)

    own_pids: Set[int] = set()
    # Loaded once, unconditionally: used both as the skip-decision source
    # (bypassed per-unit when --force-probe asks to redo work) and as the
    # merge baseline so a filtered rerun never drops other projects' results.
    prev_by_key = load_prev_results(OUT_JSON)
    opts = ProbeOptions(skip_probe=args.skip_probe, force_probe=args.force_probe,
                        settle_cap=args.settle_cap, out_json=OUT_JSON)
    records = probe_units(projects, prep_by_slug, prev_by_key, own_pids, opts)

    merged = merge_and_save(OUT_JSON, prev_by_key, records)
    write_markdown_report(merged, OUT_MD)

    leftover = [pid for pid in own_pids if pid_alive(pid)]
    if leftover:
        logger.warning("leftover tracked server pids still alive: %s", leftover)
    else:
        logger.info("no leftover tracked server processes")
    logger.info("total disk under temp/corpus: %.2f GB", dir_size_bytes(CORPUS_DIR) / (1024 ** 3))
    logger.info("wrote %s and %s", OUT_JSON, OUT_MD)


if __name__ == "__main__":
    main()


__all__ = ["main", "parse_args"]
