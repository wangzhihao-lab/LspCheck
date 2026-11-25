"""Orchestrator: clone/reuse both repos, build fix evidence for pyright and
gopls, and render the summary markdown. This is "run 1"; use
check_idempotence.py afterwards to perform and verify "run 2".

Usage: python3 run_all.py
"""

from __future__ import annotations

import time

import run_gopls
import run_pyright
import write_summary


def main() -> None:
    t0 = time.monotonic()
    stats_pyright = run_pyright.main()
    stats_gopls = run_gopls.main()
    write_summary.build_and_write(stats_pyright, stats_gopls, idempotence=None)
    elapsed = time.monotonic() - t0
    print(f"[run_all] total runtime {elapsed:.1f}s")
    print(
        f"[run_all] pyright coverage={stats_pyright['coverage']} "
        f"validation_recall={stats_pyright['validation']['found_any_recall']}"
    )
    print(
        f"[run_all] gopls coverage={stats_gopls['coverage']} "
        f"consistency_rate={stats_gopls['consistency']['consistency_rate']}"
    )


if __name__ == "__main__":
    main()
