#!/usr/bin/env python3
"""Pilot data collection: closed bug-labeled issues + evidence of a fix,
across language-server repos, via the GitHub GraphQL API. Re-runnable and
idempotent (warm cache -> zero network calls).

Run: python3 run_pilot.py
"""
from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone

import clangd_pipeline
import eyeball_md
import fetch_pipeline
import gh_client
import outputs
import pyright_addressed_pipeline
import report_md
import ts_pipeline
import validate
from config import (
    ADDITIONAL_TARGETS, OPTIONAL_TARGET_MIN_REMAINING, OPTIONAL_TARGETS,
    REQUIRED_TARGETS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("run_pilot")

REQUIRED_KEYS = {t.key for t in REQUIRED_TARGETS}


def process_one(target) -> dict:
    if target.key == "microsoft-typescript":
        return ts_pipeline.process_typescript(target)
    if target.key == "clangd-clangd-repo":
        return clangd_pipeline.process_clangd_repo(target)
    return fetch_pipeline.process_target(target)


def _skip_result(target, reason: str) -> dict:
    return {
        "target": target, "notes": [], "special_stats": {}, "funnel": None,
        "fixed_rows": [], "all_rows_count": 0, "available_label_count": 0,
        "error": reason,
    }


def main() -> int:
    start = time.monotonic()

    try:
        gh_client.assert_token_present()
    except gh_client.GitHubAuthError as exc:
        logger.error(str(exc))
        return 1

    results: list[dict] = []
    for target in REQUIRED_TARGETS:
        logger.info("=== processing required target: %s ===", target.key)
        results.append(process_one(target))

    pyright_result = next((r for r in results if r["target"].key == "pyright"), None)
    for target in ADDITIONAL_TARGETS:
        logger.info("=== processing additional target: %s ===", target.key)
        if target.key == "pyright-addressed-in-next-version":
            pyright_bug_rows = pyright_result["all_rows"] if pyright_result else []
            results.append(
                pyright_addressed_pipeline.process_pyright_addressed(target, pyright_bug_rows)
            )
        else:
            results.append(process_one(target))

    remaining = gh_client.quota_stats.get("last_remaining")
    # None means no network call has happened yet (everything above was a
    # full cache hit) - proceed rather than skip: optional targets will
    # either also hit cache for free, or the first real request will
    # populate `remaining` and the pipeline's own per-request rate-limit
    # check (gh_client._sleep_for_rate_limit) still applies either way.
    if remaining is None or remaining >= OPTIONAL_TARGET_MIN_REMAINING:
        for target in OPTIONAL_TARGETS:
            logger.info("=== processing optional target: %s ===", target.key)
            results.append(process_one(target))
    else:
        logger.warning(
            "Skipping optional (tier-7) targets: remaining quota %s < threshold %s",
            remaining, OPTIONAL_TARGET_MIN_REMAINING,
        )
        reason = f"skipped: remaining quota {remaining} < {OPTIONAL_TARGET_MIN_REMAINING}"
        results.extend(_skip_result(t, reason) for t in OPTIONAL_TARGETS)

    jsonl_paths = outputs.write_all_jsonl(results)

    runtime_s = time.monotonic() - start
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    quota_report = dict(gh_client.quota_stats)

    summary_path = report_md.write_summary(results, quota_report, runtime_s, generated_at)
    eyeball_path = eyeball_md.write_eyeball_sample(results)

    idem_report = validate.rerun_idempotence_check(results)
    violations = validate.assert_all_rows_have_evidence(jsonl_paths)
    spot_sample = validate.pick_spot_check_sample(results, n=5)

    _print_final_report(
        results, jsonl_paths, summary_path, eyeball_path, runtime_s,
        quota_report, idem_report, violations, spot_sample,
    )
    return 0 if not violations else 2


def _print_final_report(
    results, jsonl_paths, summary_path, eyeball_path, runtime_s,
    quota_report, idem_report, violations, spot_sample,
):
    total_fixed_required = sum(
        (r["funnel"].fixed_bug_candidates or 0)
        for r in results
        if r.get("funnel") and r["target"].key in REQUIRED_KEYS
    )
    additional_fixed = {
        r["target"].key: (r["funnel"].fixed_bug_candidates or 0)
        for r in results
        if r.get("funnel") and r["target"] in ADDITIONAL_TARGETS
    }
    print("\n" + "=" * 70)
    print("PILOT RUN COMPLETE")
    print("=" * 70)
    for r in results:
        t = r["target"]
        f = r.get("funnel")
        if f is None:
            print(f"  {t.key}: ERROR - {r.get('error')}")
            continue
        print(
            f"  {t.key}: total={f.total_issues} closed={f.closed_issues} "
            f"bug_labeled={f.closed_bug_labeled} fixed_candidates={f.fixed_bug_candidates}"
        )
    print(f"\nTotal fixed-bug candidates (required targets 1-6): {total_fixed_required}")
    for key, count in additional_fixed.items():
        print(f"  + additional target {key}: {count} (reported separately, different evidence criterion)")
    print(
        f"Grand total (required + additional): "
        f"{total_fixed_required + sum(additional_fixed.values())}"
    )
    print(f"Runtime: {runtime_s:.1f}s")
    print(f"Quota (GraphQL): {quota_report}")
    print(f"\nIdempotence check: {idem_report}")
    print(f"Assertion violations (row must have merged PR or closer commit): {len(violations)}")
    for v in violations[:20]:
        print(f"  VIOLATION: {v}")
    print(f"\nSpot-check sample ({len(spot_sample)} rows - verify these manually):")
    for row in spot_sample:
        print(f"  {row['repo']} #{row['number']}: {row['url']}")
    print(f"\nSummary: {summary_path}")
    print(f"Eyeball sample: {eyeball_path}")
    for key, p in jsonl_paths.items():
        print(f"JSONL[{key}]: {p}")


if __name__ == "__main__":
    sys.exit(main())
