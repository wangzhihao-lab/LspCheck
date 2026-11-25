"""gopls fix-evidence backfill pipeline.

Usage: python3 run_gopls.py

gopls issues are filed in golang/go but fixed in golang/tools (Gerrit
mirror), so commits reference them cross-repo as "golang/go#N" (and
sometimes "go#N"). Clones (or reuses) a blob-filtered bare mirror of
golang/tools, builds a single-pass reverse index over the full commit
history, attaches per-commit file/line stats, cross-checks against the
~1,343 issues that already carry a `closer_commit` (from the GitHub API,
collected earlier in the pilot) as a consistency check, and writes
data/lsp_backfill/gopls_fix_evidence.jsonl plus a stats JSON.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Any

import paths
from build_evidence import build_issue_evidence, load_jsonl, top_referenced_commits, write_jsonl
from cache import NumstatCache, load_or_build_full_log
from git_utils import clone_bare
from issue_index import build_gopls_index
from stats import coverage_buckets, files_changed_histogram, quantiles, random_examples, touches_tests_breakdown


def log(msg: str) -> None:
    print(f"[gopls] {msg}", flush=True)


def consistency_check(issues: list[dict], evidence_by_number: dict[int, dict]) -> dict[str, Any]:
    have_closer = [i for i in issues if i.get("closer_commit")]
    lacking_closer = [i for i in issues if not i.get("closer_commit")]

    match = 0
    mismatch_examples = []
    for i in have_closer:
        oid = i["closer_commit"]["oid"]
        ev = evidence_by_number.get(i["number"])
        matched_hashes = {fc["hash"] for fc in ev["fix_commits"]} if ev else set()
        if oid in matched_hashes:
            match += 1
        elif len(mismatch_examples) < 10:
            mismatch_examples.append(
                {
                    "number": i["number"],
                    "url": i["url"],
                    "closer_oid": oid,
                    "grep_hashes": sorted(matched_hashes)[:5],
                }
            )

    gained = 0
    gained_examples = []
    for i in lacking_closer:
        ev = evidence_by_number.get(i["number"])
        if ev and ev["n_fix_commits"] > 0:
            gained += 1
            if len(gained_examples) < 10:
                gained_examples.append(
                    {
                        "number": i["number"],
                        "url": i["url"],
                        "n_fix_commits": ev["n_fix_commits"],
                        "first_commit_hash": ev["fix_commits"][0]["hash"],
                    }
                )

    return {
        "n_with_closer_commit": len(have_closer),
        "n_consistent_hash_match": match,
        "n_inconsistent": len(have_closer) - match,
        "consistency_rate": round(match / len(have_closer), 4) if have_closer else None,
        "mismatch_examples": mismatch_examples,
        "n_lacking_closer_commit": len(lacking_closer),
        "n_lacking_closer_gained_fix_commit": gained,
        "gained_examples": gained_examples,
    }


def pattern_usage(evidence: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ev in evidence:
        for fc in ev["fix_commits"]:
            for p in fc.get("matched_patterns") or []:
                counts[p] = counts.get(p, 0) + 1
    return counts


def main() -> dict:
    t_start = time.monotonic()
    paths.ensure_dirs()

    log(f"cloning/reusing {paths.TOOLS_REPO_URL} -> {paths.TOOLS_REPO_DIR}")
    clone_result = clone_bare(paths.TOOLS_REPO_URL, paths.TOOLS_REPO_DIR)
    log(
        f"clone done: already_existed={clone_result.already_existed} "
        f"elapsed={clone_result.elapsed_s:.1f}s size={clone_result.size_bytes/1e6:.1f}MB"
    )

    commits, log_cached = load_or_build_full_log(paths.TOOLS_REPO_DIR, paths.TOOLS_LOG_CACHE)
    log(f"full commit log: {len(commits)} commits (cached={log_cached})")
    commits_by_hash = {c.hash: c for c in commits}

    index = build_gopls_index(commits)
    forward_sets = {h: set(d.keys()) for h, d in index.forward.items()}
    log(f"issue-reference index: {len(index.reverse)} distinct golang/go numbers referenced")

    issues = load_jsonl(paths.GOPLS_JSONL)
    log(f"loaded {len(issues)} input issues from {paths.GOPLS_JSONL.name}")

    numstat_cache = NumstatCache(paths.TOOLS_NUMSTAT_CACHE)
    log(f"numstat cache preloaded with {len(numstat_cache)} entries")

    evidence = []
    t_loop = time.monotonic()
    for idx, issue in enumerate(issues, 1):
        hash_entries = index.reverse.get(issue["number"], [])
        ev = build_issue_evidence(
            issue, hash_entries, commits_by_hash, forward_sets, numstat_cache, paths.TOOLS_REPO_DIR
        )
        evidence.append(ev)
        if idx % 250 == 0 or idx == len(issues):
            numstat_cache.flush()
            elapsed = time.monotonic() - t_loop
            log(f"  {idx}/{len(issues)} issues processed, {len(numstat_cache)} commits stat-cached, {elapsed:.1f}s elapsed")
    numstat_cache.flush()

    write_jsonl(paths.GOPLS_OUT_JSONL, evidence)
    log(f"wrote {len(evidence)} records -> {paths.GOPLS_OUT_JSONL}")

    evidence_by_number = {ev["number"]: ev for ev in evidence}
    consistency = consistency_check(issues, evidence_by_number)
    log(
        f"consistency: {consistency['n_consistent_hash_match']}/{consistency['n_with_closer_commit']} "
        f"closer_commit matches grep; {consistency['n_lacking_closer_gained_fix_commit']}/"
        f"{consistency['n_lacking_closer_commit']} lacking closer_commit gained a fix commit"
    )

    result_stats = {
        "repo_label": "gopls",
        "repo": "golang/tools (issues tracked in golang/go)",
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
        "pattern_usage": pattern_usage(evidence),
        "consistency": consistency,
        "runtime_s": round(time.monotonic() - t_start, 1),
    }
    stats_path = paths.CACHE_DIR / "gopls_stats.json"
    stats_path.write_text(json.dumps(result_stats, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"stats -> {stats_path} (total runtime {result_stats['runtime_s']}s)")
    return result_stats


if __name__ == "__main__":
    main()
