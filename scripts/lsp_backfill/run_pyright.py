"""Pyright fix-evidence backfill pipeline.

Usage: python3 run_pyright.py

Clones (or reuses) a blob-filtered bare mirror of microsoft/pyright, builds
a single-pass "#N" reverse index over the full commit history, attaches
per-commit file/line stats, validates against the 51 issues that already
carry a known closing PR (data/lsp_pilot/pyright_fixed_bugs.jsonl), and
writes data/lsp_backfill/pyright_fix_evidence.jsonl plus a stats JSON for
write_summary.py to consume.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict

import paths
from build_evidence import build_issue_evidence, load_jsonl, top_referenced_commits, write_jsonl
from cache import NumstatCache, load_or_build_full_log
from git_utils import clone_bare
from issue_index import build_pyright_index
from stats import coverage_buckets, files_changed_histogram, quantiles, random_examples, touches_tests_breakdown
from validate_pyright import validate_against_linked


def log(msg: str) -> None:
    print(f"[pyright] {msg}", flush=True)


def main() -> dict:
    t_start = time.monotonic()
    paths.ensure_dirs()

    log(f"cloning/reusing {paths.PYRIGHT_REPO_URL} -> {paths.PYRIGHT_REPO_DIR}")
    clone_result = clone_bare(paths.PYRIGHT_REPO_URL, paths.PYRIGHT_REPO_DIR)
    log(
        f"clone done: already_existed={clone_result.already_existed} "
        f"elapsed={clone_result.elapsed_s:.1f}s size={clone_result.size_bytes/1e6:.1f}MB"
    )

    commits, log_cached = load_or_build_full_log(paths.PYRIGHT_REPO_DIR, paths.PYRIGHT_LOG_CACHE)
    log(f"full commit log: {len(commits)} commits (cached={log_cached})")
    commits_by_hash = {c.hash: c for c in commits}

    index = build_pyright_index(commits)
    log(f"issue-reference index: {len(index.reverse)} distinct numbers referenced across history")

    issues = load_jsonl(paths.PYRIGHT_ALL_JSONL)
    log(f"loaded {len(issues)} input issues from {paths.PYRIGHT_ALL_JSONL.name}")

    n_with_hits = sum(1 for i in issues if i["number"] in index.reverse)
    distinct_commits_needed = {h for i in issues for h in index.reverse.get(i["number"], [])}
    log(f"{n_with_hits}/{len(issues)} issues have >=1 candidate commit; {len(distinct_commits_needed)} distinct commits to stat")

    numstat_cache = NumstatCache(paths.PYRIGHT_NUMSTAT_CACHE)
    log(f"numstat cache preloaded with {len(numstat_cache)} entries")

    evidence = []
    t_loop = time.monotonic()
    for idx, issue in enumerate(issues, 1):
        hash_entries = [(h, None) for h in index.reverse.get(issue["number"], [])]
        ev = build_issue_evidence(
            issue, hash_entries, commits_by_hash, index.forward, numstat_cache, paths.PYRIGHT_REPO_DIR
        )
        evidence.append(ev)
        if idx % 250 == 0 or idx == len(issues):
            numstat_cache.flush()
            elapsed = time.monotonic() - t_loop
            log(f"  {idx}/{len(issues)} issues processed, {len(numstat_cache)} commits stat-cached, {elapsed:.1f}s elapsed")
    numstat_cache.flush()

    write_jsonl(paths.PYRIGHT_OUT_JSONL, evidence)
    log(f"wrote {len(evidence)} records -> {paths.PYRIGHT_OUT_JSONL}")

    # Validation must apply the same grep method directly to the 51 linked
    # issues via the shared history index -- NOT look them up inside the
    # 2,469-set's evidence dict. The two input files use different label
    # filters (pyright_fixed_bugs.jsonl = "bug" only; the 2,469-set also
    # requires "addressed in next version"), so only 17/51 linked issue
    # numbers actually occur in the 2,469-set; looking validation up there
    # would silently score the other 34 as "missed" regardless of whether
    # the grep method actually works on them.
    linked = load_jsonl(paths.PYRIGHT_LINKED_JSONL)
    linked_evidence = []
    for issue in linked:
        hash_entries = [(h, None) for h in index.reverse.get(issue["number"], [])]
        ev = build_issue_evidence(
            issue, hash_entries, commits_by_hash, index.forward, numstat_cache, paths.PYRIGHT_REPO_DIR
        )
        linked_evidence.append(ev)
    numstat_cache.flush()
    linked_evidence_by_number = {ev["number"]: ev for ev in linked_evidence}
    numbers_in_2469_set = {ev["number"] for ev in evidence}
    n_linked_in_2469_set = sum(1 for i in linked if i["number"] in numbers_in_2469_set)

    validation = validate_against_linked(linked, linked_evidence_by_number)
    validation["n_linked_also_in_2469_set"] = n_linked_in_2469_set
    log(
        f"validation on {validation['total_linked_issues']} linked issues "
        f"({n_linked_in_2469_set} of which also appear in the 2,469-set): "
        f"found_any={validation['found_any_count']} ({validation['found_any_recall']:.1%}), "
        f"recovered_strict={validation['recovered_strict_count']} ({validation['recovered_strict_recall']:.1%})"
    )

    result_stats = {
        "repo_label": "pyright",
        "repo": "microsoft/pyright",
        "clone": asdict(clone_result),
        "log_cached": log_cached,
        "n_commits_total_history": len(commits),
        "n_issues_input": len(issues),
        "n_numstat_fetch_failed": numstat_cache.n_failed(),
        "coverage": coverage_buckets(evidence),
        "files_changed_histogram": files_changed_histogram(evidence),
        "touches_tests": touches_tests_breakdown(evidence),
        "fix_latency_days": quantiles([ev["fix_latency_days"] for ev in evidence if ev["fix_latency_days"] is not None]),
        "top_referenced_commits": top_referenced_commits(evidence, 20),
        "random_examples": random_examples(evidence, 10),
        "validation": validation,
        "runtime_s": round(time.monotonic() - t_start, 1),
    }
    stats_path = paths.CACHE_DIR / "pyright_stats.json"
    stats_path.write_text(json.dumps(result_stats, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"stats -> {stats_path} (total runtime {result_stats['runtime_s']}s)")
    return result_stats


if __name__ == "__main__":
    main()
