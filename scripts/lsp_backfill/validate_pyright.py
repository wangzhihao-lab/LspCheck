"""Validation: for the 51 pyright issues that already carry a known closing
PR / closer commit (ground truth from the GitHub API, collected earlier in
the pilot), check how many of those are recovered by the pure git-log-grep
method. Two corroboration signals are checked, per the task's instruction
to match "by commit hash of the merged PR's merge commit or by the PR
number appearing in the message":

  * hash_confirmed  -- closer_commit.oid (when present) is literally one of
                        the commit hashes the grep method found for that issue.
  * pr_confirmed    -- any merged closing PR's number appears (same
                        digit-bounded #N regex) in the subject/body text of
                        any commit the grep method found for that issue.

found_any (n_fix_commits > 0) is reported separately since it is the
simplest and most literal "did the method recover a fix commit" signal;
hash_confirmed/pr_confirmed are stricter corroboration that the recovered
commit is specifically the known closing one, not a coincidental reference.
"""

from __future__ import annotations

from typing import Any

from issue_index import PYRIGHT_REF_RE


def _text_refs(text: str) -> set[int]:
    return {int(m.group(1)) for m in PYRIGHT_REF_RE.finditer(text)}


def validate_against_linked(
    linked_issues: list[dict], evidence_by_number: dict[int, dict]
) -> dict[str, Any]:
    rows = []
    for issue in linked_issues:
        number = issue["number"]
        ev = evidence_by_number.get(number)
        found_any = bool(ev and ev["n_fix_commits"] > 0)

        closer_commit = issue.get("closer_commit") or {}
        closer_oid = closer_commit.get("oid")
        merged_pr_numbers = [
            pr["number"] for pr in (issue.get("closing_prs") or []) if pr.get("merged")
        ]

        matched_hashes = {fc["hash"] for fc in ev["fix_commits"]} if ev else set()
        hash_confirmed = bool(closer_oid) and closer_oid in matched_hashes

        pr_confirmed = False
        if ev and merged_pr_numbers:
            all_text_refs: set[int] = set()
            for fc in ev["fix_commits"]:
                all_text_refs |= _text_refs(fc["subject"] + "\n" + fc["body"])
            pr_confirmed = any(pr in all_text_refs for pr in merged_pr_numbers)

        has_ground_truth = bool(closer_oid) or bool(merged_pr_numbers)
        corroborated = hash_confirmed or pr_confirmed
        recovered_strict = found_any and (corroborated or not has_ground_truth)

        rows.append(
            {
                "number": number,
                "url": issue["url"],
                "found_any": found_any,
                "n_fix_commits": ev["n_fix_commits"] if ev else 0,
                "has_closer_oid": bool(closer_oid),
                "has_merged_pr": bool(merged_pr_numbers),
                "hash_confirmed": hash_confirmed,
                "pr_confirmed": pr_confirmed,
                "recovered_strict": recovered_strict,
            }
        )

    total = len(rows)
    n_found_any = sum(r["found_any"] for r in rows)
    n_with_oid = sum(r["has_closer_oid"] for r in rows)
    n_hash_confirmed = sum(r["hash_confirmed"] for r in rows)
    n_with_pr = sum(r["has_merged_pr"] for r in rows)
    n_pr_confirmed = sum(r["pr_confirmed"] for r in rows)
    n_recovered_strict = sum(r["recovered_strict"] for r in rows)
    misses = [r for r in rows if not r["found_any"]]

    return {
        "total_linked_issues": total,
        "found_any_count": n_found_any,
        "found_any_recall": round(n_found_any / total, 4) if total else None,
        "issues_with_closer_oid": n_with_oid,
        "hash_confirmed_count": n_hash_confirmed,
        "issues_with_merged_pr": n_with_pr,
        "pr_confirmed_count": n_pr_confirmed,
        "recovered_strict_count": n_recovered_strict,
        "recovered_strict_recall": round(n_recovered_strict / total, 4) if total else None,
        "missed_issue_numbers": [m["number"] for m in misses],
        "rows": rows,
    }
