"""Post-run validation:
1. Idempotence: replay every non-counts-only target's full fetch in
   cache_only mode (raises if any page is missing from cache) and diff the
   resulting fixed-bug-candidate count against the first run.
2. Assertion: every JSONL row has a merged closing PR or a closer commit -
   EXCEPT the pyright "addressed in next version" row, whose evidence is
   the label combination itself (see pyright_addressed_pipeline.py); that
   row is checked against its own criterion instead.
3. A deterministic sample of rows for manual spot-checking (issue URLs to
   open and confirm the closing PR/commit is real).

Run: imported by run_pilot.py, not run directly.
"""
from __future__ import annotations

import json
import logging
import random
from pathlib import Path

import analyze
import cache
import clangd_pipeline
import fetch_issues
import pyright_addressed_pipeline
import ts_pipeline
from config import LABEL_EVIDENCE_TARGET_KEY, Target

logger = logging.getLogger(__name__)

# Distinct from EYEBALL_RANDOM_SEED (42): this sample is an internal QA
# check, not the eyeball_sample.md deliverable.
SPOT_CHECK_SEED = 1337


def rerun_idempotence_check(results: list[dict]) -> dict:
    report = {"targets_checked": 0, "mismatches": [], "cache_hits": 0, "cache_misses": 0}
    cache.reset_stats()
    pyright_rows_rerun: list[dict] | None = None

    for r in results:
        target: Target = r["target"]
        if target.counts_only or r.get("funnel") is None:
            continue
        try:
            if target.key == "microsoft-typescript":
                fixed_count = _rerun_typescript(target, r)
            elif target.key == "clangd-clangd-repo":
                fixed_count = _rerun_clangd_repo(target, r)
            elif target.key == LABEL_EVIDENCE_TARGET_KEY:
                fixed_count = _rerun_pyright_addressed(target, r, pyright_rows_rerun)
            else:
                all_rows, fixed_rows = _rerun_simple(target, r)
                fixed_count = len(fixed_rows)
                if target.key == "pyright":
                    pyright_rows_rerun = all_rows
        except RuntimeError as exc:
            report["mismatches"].append(f"{target.key}: cache replay failed: {exc}")
            continue
        report["targets_checked"] += 1
        expected = r["funnel"].fixed_bug_candidates
        if fixed_count != expected:
            report["mismatches"].append(
                f"{target.key}: first run fixed_bug_candidates={expected} rerun={fixed_count}"
            )
    report["cache_hits"] = cache.stats["hits"]
    report["cache_misses"] = cache.stats["misses"]
    report["is_idempotent"] = not report["mismatches"] and report["cache_misses"] == 0
    return report


def _rerun_simple(target: Target, r: dict) -> tuple[list[dict], list[dict]]:
    repo_full = r["funnel"].repo
    labels = r["resolved_bug_labels"]
    nodes = fetch_issues.fetch_closed_issues_full(target, labels, subdir="issues", cache_only=True)
    rows = analyze.rows_from_nodes(repo_full, nodes)
    fixed = [x for x in rows if analyze.is_fixed_bug_candidate(x)]
    return rows, fixed


def _rerun_pyright_addressed(target: Target, r: dict, pyright_rows_rerun: list[dict] | None) -> int:
    if pyright_rows_rerun is None:
        raise RuntimeError("pyright must be rerun before pyright-addressed (ordering bug)")
    matched = [
        x for x in pyright_rows_rerun
        if pyright_addressed_pipeline.ADDRESSED_LABEL in x["labels"]
    ]
    return len(matched)


def _rerun_typescript(target: Target, r: dict) -> int:
    repo_full = r["funnel"].repo
    bug_label = r["resolved_bug_labels"][0]
    all_rows: list[dict] = []
    for domain in r.get("keyword_matched_domains", []):
        nodes = ts_pipeline.fetch_bug_domain_rows(target, bug_label, domain, cache_only=True)
        all_rows.extend(analyze.rows_from_nodes(repo_full, nodes))
    union = analyze.dedupe_by_number(all_rows)
    fixed = [x for x in union if analyze.is_fixed_bug_candidate(x)]
    return len(fixed)


def _rerun_clangd_repo(target: Target, r: dict) -> int:
    repo_full = r["funnel"].repo
    resolved = r.get("resolved_bug_labels") or []
    if resolved:
        nodes = fetch_issues.fetch_closed_issues_full(
            target, resolved, subdir="issues", cache_only=True
        )
    else:
        all_nodes = fetch_issues.fetch_closed_issues_full(
            target, None, subdir="issues_all", cache_only=True
        )
        nodes = [n for n in all_nodes if not clangd_pipeline.is_excluded(n)]
    rows = analyze.rows_from_nodes(repo_full, nodes)
    fixed = [x for x in rows if analyze.is_fixed_bug_candidate(x)]
    return len(fixed)


def assert_all_rows_have_evidence(jsonl_paths: dict[str, Path]) -> list[str]:
    """Every JSONL row must carry >=1 merged closing PR or a closer commit,
    except LABEL_EVIDENCE_TARGET_KEY's rows, whose evidence is instead
    "carries both the 'bug' and 'addressed in next version' labels"."""
    problems: list[str] = []
    total_checked = 0
    for key, path in jsonl_paths.items():
        with path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                total_checked += 1
                if key == LABEL_EVIDENCE_TARGET_KEY:
                    ok = pyright_addressed_pipeline.ADDRESSED_LABEL in row["labels"] and "bug" in row["labels"]
                    problem = "missing 'bug' + 'addressed in next version' labels"
                else:
                    has_merged_pr = any(p["merged"] for p in row["closing_prs"])
                    has_commit = row["closer_commit"] is not None
                    ok = has_merged_pr or has_commit
                    problem = "has no merged PR and no closer commit"
                if not ok:
                    problems.append(
                        f"{key}:{path.name}:{lineno} issue #{row['number']} ({row['url']}) {problem}"
                    )
    logger.info("assertion pass: %d rows checked across %d files, %d violations",
                total_checked, len(jsonl_paths), len(problems))
    return problems


def pick_spot_check_sample(results: list[dict], n: int = 5) -> list[dict]:
    candidates: list[dict] = []
    for r in results:
        if r["target"].counts_only:
            continue
        candidates.extend(r.get("fixed_rows", []))
    candidates.sort(key=lambda row: (row["repo"], row["number"]))
    rng = random.Random(SPOT_CHECK_SEED)
    k = min(n, len(candidates))
    return rng.sample(candidates, k) if k else []
