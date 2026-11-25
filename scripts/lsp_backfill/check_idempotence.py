"""Performs "run 2": re-runs the pyright and gopls pipelines against the
already-populated bare clones and caches, and confirms no re-clone, no
re-run of `git log`, and byte-identical output JSONL versus run 1. Writes
temp/clones/cache/idempotence.json and regenerates backfill_summary.md with
the idempotence section filled in.

Usage: python3 check_idempotence.py   (run only after run_all.py has completed once)
"""

from __future__ import annotations

import hashlib
import json
import time

import paths
import run_gopls
import run_pyright
import write_summary


def md5_of(path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> None:
    run1_pyright = json.loads((paths.CACHE_DIR / "pyright_stats.json").read_text(encoding="utf-8"))
    run1_gopls = json.loads((paths.CACHE_DIR / "gopls_stats.json").read_text(encoding="utf-8"))
    pre_pyright_md5 = md5_of(paths.PYRIGHT_OUT_JSONL)
    pre_gopls_md5 = md5_of(paths.GOPLS_OUT_JSONL)

    print("[idempotence] starting run 2 ...")
    t0 = time.monotonic()
    stats_pyright_2 = run_pyright.main()
    stats_gopls_2 = run_gopls.main()
    run2_elapsed = time.monotonic() - t0

    post_pyright_md5 = md5_of(paths.PYRIGHT_OUT_JSONL)
    post_gopls_md5 = md5_of(paths.GOPLS_OUT_JSONL)

    idem = {
        "run1_elapsed_s": round(run1_pyright["runtime_s"] + run1_gopls["runtime_s"], 1),
        "run2_elapsed_s": round(run2_elapsed, 1),
        "pyright_reclone_avoided": stats_pyright_2["clone"]["already_existed"],
        "gopls_reclone_avoided": stats_gopls_2["clone"]["already_existed"],
        "pyright_log_cached_run2": stats_pyright_2["log_cached"],
        "gopls_log_cached_run2": stats_gopls_2["log_cached"],
        "pyright_output_identical": pre_pyright_md5 == post_pyright_md5,
        "gopls_output_identical": pre_gopls_md5 == post_gopls_md5,
        "pyright_md5": post_pyright_md5,
        "gopls_md5": post_gopls_md5,
    }
    idem_path = paths.CACHE_DIR / "idempotence.json"
    idem_path.write_text(json.dumps(idem, indent=2), encoding="utf-8")
    print(f"[idempotence] {json.dumps(idem, indent=2)}")

    write_summary.build_and_write(stats_pyright_2, stats_gopls_2, idempotence=idem)


if __name__ == "__main__":
    main()
