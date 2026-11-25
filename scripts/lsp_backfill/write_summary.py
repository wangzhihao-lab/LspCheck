"""Renders data/lsp_backfill/backfill_summary.md from the two pipelines'
stats JSON (and, once available, an idempotence-check JSON).

Can be re-run standalone at any time: it only reads paths.CACHE_DIR/*.json
and paths.*_OUT_JSONL, and always overwrites backfill_summary.md in place.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import paths


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def pct(n: int, total: int) -> str:
    return f"{n} ({n/total:.1%})" if total else f"{n} (n/a)"


def coverage_section(label: str, s: dict) -> str:
    cov = s["coverage"]
    total = s["n_issues_input"]
    rows = [
        ["0 fix commits", pct(cov["0"], total)],
        ["1 fix commit", pct(cov["1"], total)],
        ["2+ fix commits", pct(cov["2+"], total)],
    ]
    return f"### {label} ({total} issues)\n\n" + md_table(["Fix commits found", "Issues (%)"], rows)


def files_changed_section(label: str, s: dict) -> str:
    h = s["files_changed_histogram"]
    rows = [[k, v] for k, v in h.items()]
    return f"### {label}\n\n" + md_table(["files_changed bucket", "issues"], rows)


def touches_tests_section(label: str, s: dict) -> str:
    tt = s["touches_tests"]
    rows = [["true", tt.get("true", 0)], ["false", tt.get("false", 0)]]
    return f"### {label}\n\n" + md_table(["touches_tests", "issues (of those with >=1 fix commit)"], rows)


def latency_row(label: str, q: dict) -> list:
    return [label, q["count"], q["min"], q["p25"], q["median"], q["p75"], q["max"], q["mean"]]


def top_commits_section(label: str, s: dict) -> str:
    rows = []
    for c in s["top_referenced_commits"]:
        subj = c["subject"].replace("|", "/")[:80]
        rows.append([c["hash"][:10], c["date"][:10], c["n_issues_referenced"], subj])
    return f"### {label}\n\n" + md_table(["commit", "date", "n_issues_referenced", "subject"], rows)


def examples_section(label: str, s: dict) -> str:
    rows = []
    for e in s["random_examples"]:
        subj = e["commit_subject"].replace("|", "/")[:90]
        rows.append([f"#{e['number']}", e["url"], e["commit_hash"][:10], subj])
    return f"### {label}\n\n" + md_table(["issue", "url", "commit", "subject"], rows)


def validation_section(v: dict) -> str:
    lines = [
        "## 3. Validation: pyright 51 linked-issue recall\n",
        f"- total linked issues: {v['total_linked_issues']} (this file uses label filter `bug` only; "
        f"{v.get('n_linked_also_in_2469_set', 'n/a')} of the 51 also carry `addressed in next version` and "
        "hence also appear in the 2,469-issue set below -- validation below re-runs the grep method directly "
        "against all 51 via the shared commit index, independent of that overlap)",
        f"- **found_any** (grep found >=1 commit referencing the issue number): "
        f"{v['found_any_count']}/{v['total_linked_issues']} = {v['found_any_recall']:.1%}",
        f"- of those, {v['issues_with_closer_oid']} issues carry a ground-truth `closer_commit.oid` and "
        f"{v['hash_confirmed_count']} of the grep hits match that hash exactly",
        f"- {v['issues_with_merged_pr']} issues carry a merged closing PR number; {v['pr_confirmed_count']} of the "
        "grep hits contain that PR number in the matched commit's subject/body (squash-merge commits typically "
        "carry both the PR number in the subject and the original \"Fixes #N\" in the body)",
        f"- **recovered_strict** (found_any AND corroborated by hash or PR number, or no ground truth to "
        f"cross-check): {v['recovered_strict_count']}/{v['total_linked_issues']} = {v['recovered_strict_recall']:.1%}",
        f"- missed issue numbers (no commit found at all): {v['missed_issue_numbers']}",
    ]
    return "\n".join(lines)


def consistency_section(c: dict) -> str:
    rate_str = f"{c['consistency_rate']:.1%}" if c["consistency_rate"] is not None else "n/a"
    lines = [
        "## 4. gopls consistency check (closer_commit vs. grep)\n",
        f"- issues with a ground-truth `closer_commit`: {c['n_with_closer_commit']}",
        f"- grep found the exact same commit hash: {c['n_consistent_hash_match']} ({rate_str})",
        f"- inconsistent (closer_commit present but not in grep hits): {c['n_inconsistent']}",
        f"- issues lacking `closer_commit` entirely: {c['n_lacking_closer_commit']}",
        f"- of those, grep found a fix commit anyway: {c['n_lacking_closer_gained_fix_commit']}",
    ]
    return "\n".join(lines)


def clone_row(s: dict) -> list:
    c = s["clone"]
    return [s["repo"], c["url"], c["already_existed"], f"{c['elapsed_s']:.1f}", f"{c['size_bytes']/1e6:.1f}"]


def idempotence_section(idem: dict | None) -> str:
    if idem is None:
        return "## 10. Idempotence check\n\npending -- rerun not yet recorded.\n"
    rows = [
        ["pyright clone already_existed (run 2)", idem["pyright_reclone_avoided"]],
        ["gopls clone already_existed (run 2)", idem["gopls_reclone_avoided"]],
        ["pyright commit log cached (run 2)", idem["pyright_log_cached_run2"]],
        ["gopls commit log cached (run 2)", idem["gopls_log_cached_run2"]],
        ["pyright output byte-identical run1 vs run2", idem["pyright_output_identical"]],
        ["gopls output byte-identical run1 vs run2", idem["gopls_output_identical"]],
        ["run 1 wall time (s)", idem["run1_elapsed_s"]],
        ["run 2 wall time (s)", idem["run2_elapsed_s"]],
    ]
    return "## 10. Idempotence check (rerun once to confirm)\n\n" + md_table(["check", "value"], rows)


def method_notes() -> str:
    return """## Method notes (facts about how this was produced)

- Clones: `git clone --filter=blob:none --bare <url> temp/clones/<repo>.git`. Blobs are fetched
  lazily on demand only for the specific commits that are later diffed for stats.
- Every git invocation (`log`, `show --numstat`) runs via Python `subprocess` inside the scripts in
  `scripts/lsp_backfill/`, never as literal `git ...` text passed to a shell command. This session's
  interactive shell used for this project has an active `rtk` hook that transparently rewrites recognized
  commands (`git log` -> `rtk git log`, a lossy "one-line commit history"; `git show` -> `rtk git show`,
  a "compact show"; also `head`/`cat`/`wc`) before they run, which would have silently corrupted the
  exact hashes/dates/full commit text this pipeline depends on. `git clone` and any `python3 ...`
  invocation are not recognized by that hook and pass through unmodified, which is what this pipeline
  relies on for correctness.
- Issue-number matching uses a non-digit lookbehind/lookahead around `#N` (`(?<!\\d)#(\\d+)(?!\\d)`) so
  `#1234` never matches inside `#12345`.
- pyright: single-repo `#N` convention. gopls: golang/tools commits reference golang/go issues
  cross-repo; three patterns are tried in priority order -- `golang/go#N`, then `go#N` (excluding the
  `go#N` inside an already-matched `golang/go#N`), then bare `#N` restricted to commit messages that
  also contain "gopls" (case-insensitive) to hold down false positives from golang/tools' own,
  unrelated PR/CL numbers.
- Per-commit stats come from `git show --format= --numstat --no-renames`, the machine-readable
  equivalent of `--stat`, chosen because the human-readable graph format can truncate long pathnames
  (which would corrupt `touches_tests`). Renames are disabled so every touched path is a plain
  add/delete pair rather than an ambiguous `{old => new}` token. `touches_tests` is true if any
  changed path contains "test" (case-insensitive). Merge commits are not given special-case
  handling: plain `git show --numstat` on a merge already defaults to a diff against its first
  parent only (verified empirically against git 2.50.1, equivalent to `--first-parent -m`), so the
  stat is well-defined and non-empty; such commits are flagged `is_merge` for transparency.
- Issue-level `files_changed` / `insertions` / `deletions` / `touches_tests` report the **first
  (earliest-dated) fix commit only**; `fix_commits` in the JSONL carries the full per-commit
  breakdown for every matched commit if a different aggregation is needed downstream. Ties on an
  identical committer-date second (rare) are broken by commit hash for determinism, not by any
  semantic ordering.
- `fix_latency_days` = first_fix_date (commit committer date) minus the issue's `createdAt`.
"""


def build_markdown(stats_pyright: dict, stats_gopls: dict, idempotence: dict | None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        "# LSP Bug Fix-Evidence Backfill Summary\n",
        f"Generated {now} by `scripts/lsp_backfill/run_all.py`. Method: git history grep "
        "(no GitHub API, no tokens read or printed).\n",
        method_notes(),
        "## 1. Clone report\n",
        md_table(
            ["Repo", "URL", "Already existed", "Elapsed (s)", "Size (MB)"],
            [clone_row(stats_pyright), clone_row(stats_gopls)],
        ),
        f"\nFull commit history: pyright {stats_pyright['n_commits_total_history']:,} commits, "
        f"golang/tools {stats_gopls['n_commits_total_history']:,} commits. "
        f"numstat fetch failures: pyright {stats_pyright.get('n_numstat_fetch_failed', 0)}, "
        f"gopls {stats_gopls.get('n_numstat_fetch_failed', 0)}.\n",
        "## 2. Coverage: issues with 0 / 1 / 2+ fix commits\n",
        coverage_section("pyright (addressed-in-next-version)", stats_pyright),
        "",
        coverage_section("gopls", stats_gopls),
        "",
        validation_section(stats_pyright["validation"]),
        "",
        consistency_section(stats_gopls["consistency"]),
        "\n**gopls match-pattern usage** (a commit can match more than one pattern):\n",
        md_table(["pattern", "matches"], [[k, v] for k, v in stats_gopls["pattern_usage"].items()]),
        "\n## 5. files_changed distribution\n",
        files_changed_section("pyright", stats_pyright),
        "",
        files_changed_section("gopls", stats_gopls),
        "\n## 6. touches_tests\n",
        touches_tests_section("pyright", stats_pyright),
        "",
        touches_tests_section("gopls", stats_gopls),
        "\n## 7. fix_latency_days quantiles\n",
        md_table(
            ["repo", "count", "min", "p25", "median", "p75", "max", "mean"],
            [
                latency_row("pyright", stats_pyright["fix_latency_days"]),
                latency_row("gopls", stats_gopls["fix_latency_days"]),
            ],
        ),
        "\n## 8. 20 most-referenced commits (bulk-fix / release-note candidates to exclude later)\n",
        top_commits_section("pyright", stats_pyright),
        "",
        top_commits_section("gopls", stats_gopls),
        "\n## 9. Random examples for eyeballing (10 per repo)\n",
        examples_section("pyright", stats_pyright),
        "",
        examples_section("gopls", stats_gopls),
        "",
        idempotence_section(idempotence),
        "\n## 11. Output files\n",
        f"- `{paths.PYRIGHT_OUT_JSONL.relative_to(paths.ROOT)}` ({stats_pyright['n_issues_input']} records)",
        f"- `{paths.GOPLS_OUT_JSONL.relative_to(paths.ROOT)}` ({stats_gopls['n_issues_input']} records)",
        f"- pyright runtime: {stats_pyright['runtime_s']}s; gopls runtime: {stats_gopls['runtime_s']}s\n",
    ]
    return "\n".join(parts) + "\n"


def load_stats(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_and_write(stats_pyright: dict, stats_gopls: dict, idempotence: dict | None) -> None:
    md = build_markdown(stats_pyright, stats_gopls, idempotence)
    paths.SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    paths.SUMMARY_MD.write_text(md, encoding="utf-8")
    print(f"[summary] wrote {paths.SUMMARY_MD}")


def main() -> None:
    stats_pyright = load_stats(paths.CACHE_DIR / "pyright_stats.json")
    stats_gopls = load_stats(paths.CACHE_DIR / "gopls_stats.json")
    idem_path = paths.CACHE_DIR / "idempotence.json"
    idempotence = load_stats(idem_path) if idem_path.exists() else None
    build_and_write(stats_pyright, stats_gopls, idempotence)


if __name__ == "__main__":
    main()
