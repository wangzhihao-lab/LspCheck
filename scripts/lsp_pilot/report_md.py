"""Write data/lsp_pilot/pilot_summary.md: funnel table, yearly
distribution, label names actually used, anomalies, and the cross-target
total fixed-bug-candidate count. Target-specific detail sections (per-target
supplementary stats) live in report_md_extra.py to keep this file under the
300-line budget.

Run: imported by run_pilot.py, not run directly.
"""
from __future__ import annotations

from pathlib import Path

import report_md_extra as extra
from config import ADDITIONAL_TARGETS, DATA_DIR, REQUIRED_TARGETS, YEAR_END, YEAR_START

REQUIRED_KEYS = {t.key for t in REQUIRED_TARGETS}
ADDITIONAL_KEYS = {t.key for t in ADDITIONAL_TARGETS}


def _fmt(v) -> str:
    return "-" if v is None else f"{v:,}"


def _funnel_table(results: list[dict]) -> list[str]:
    lines = [
        "## Funnel table",
        "",
        "| Target | Repo | Label filter (AND) | Total issues | Closed issues | "
        "Closed bug-labeled | Fixed bug candidates |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in results:
        t = r["target"]
        f = r.get("funnel")
        if f is None:
            lines.append(f"| {t.key} | {t.owner}/{t.name} | ERROR | - | - | - | - |")
            continue
        lines.append(
            f"| {f.key} | {f.repo} | `{f.label_repr}` | {_fmt(f.total_issues)} | "
            f"{_fmt(f.closed_issues)} | {_fmt(f.closed_bug_labeled)} | "
            f"{_fmt(f.fixed_bug_candidates)} |"
        )
    return lines


def _total_fixed(results: list[dict]) -> int:
    return sum((r["funnel"].fixed_bug_candidates or 0) for r in results if r.get("funnel"))


def _yearly_table(results: list[dict]) -> list[str]:
    years = [str(y) for y in range(YEAR_START, YEAR_END + 1)]
    lines = [
        "## Yearly distribution of fixed bug candidates (by closedAt)",
        "",
        "| Target | " + " | ".join(years) + " | other |",
        "|---|" + "---:|" * (len(years) + 1),
    ]
    for r in results:
        f = r.get("funnel")
        if f is None or not f.yearly:
            continue
        vals = [str(f.yearly.get(y, 0)) for y in years]
        vals.append(str(f.yearly.get("other_out_of_range", 0)))
        lines.append(f"| {f.key} | " + " | ".join(vals) + " |")
    return lines


def _labels_used(results: list[dict]) -> list[str]:
    lines = ["## Label names actually used", ""]
    for r in results:
        t = r["target"]
        if t.key == "clangd-clangd-repo":
            continue  # bespoke conditional resolution - see its own section
        resolved = r.get("resolved_bug_labels")
        status = "OK" if resolved == list(t.bug_labels) else "DIFFERS (see anomalies)"
        lines.append(
            f"- **{t.key}** (`{t.owner}/{t.name}`): requested `{list(t.bug_labels)}` "
            f"-> used `{resolved}` [{status}]"
        )
    return lines


def _anomalies(results: list[dict]) -> list[str]:
    lines = ["## Anomalies", ""]
    any_item = False
    for r in results:
        t = r["target"]
        item_lines = []
        if r.get("error"):
            item_lines.append(f"ERROR: {r['error']}")
        item_lines.extend(r.get("notes", []))
        if r.get("funnel") and not t.counts_only:
            bot = r.get("bot_closed_count", 0)
            dup = r.get("duplicate_labeled_count", 0)
            if bot:
                item_lines.append(f"{bot} closed bug-labeled issue(s) closed by an apparent bot account")
            if dup:
                item_lines.append(f"{dup} closed bug-labeled issue(s) carry a 'duplicate'-like label")
            other = r["funnel"].yearly.get("other_out_of_range", 0) if r["funnel"].yearly else 0
            if other:
                item_lines.append(
                    f"{other} fixed-bug candidate(s) closed outside the "
                    f"{YEAR_START}-{YEAR_END} window"
                )
        if item_lines:
            any_item = True
            lines.append(f"**{t.key}**:")
            lines.extend(f"- {il}" for il in item_lines)
            lines.append("")
    if not any_item:
        lines.append("None observed.")
    return lines


def _optional_targets_section(results: list[dict]) -> list[str]:
    optional = [r for r in results if r["target"].optional]
    if not optional:
        return []
    lines = [
        "## Optional targets (tier 7, counts only)",
        "",
        "| Target | Repo | Label filter | Total issues | Closed issues | Closed bug-labeled |",
        "|---|---|---|---:|---:|---:|",
    ]
    for r in optional:
        t = r["target"]
        f = r.get("funnel")
        if f is None:
            lines.append(f"| {t.key} | {t.owner}/{t.name} | - | SKIPPED: {r.get('error')} | | |")
            continue
        lines.append(
            f"| {f.key} | {f.repo} | `{f.label_repr}` | {_fmt(f.total_issues)} | "
            f"{_fmt(f.closed_issues)} | {_fmt(f.closed_bug_labeled)} |"
        )
    return lines


def write_summary(
    results: list[dict], quota_report: dict, runtime_s: float, generated_at: str
) -> Path:
    required = [r for r in results if r["target"].key in REQUIRED_KEYS]
    additional = [r for r in results if r["target"].key in ADDITIONAL_KEYS]
    lines = [
        "# LSP bug-fix pilot data collection - summary",
        "",
        f"Generated {generated_at} by `scripts/lsp_pilot/run_pilot.py`. "
        f"Runtime: {runtime_s:.1f}s. GraphQL points used (observed): "
        f"{quota_report.get('points_used_observed', '?')}; requests sent: "
        f"{quota_report.get('requests_sent', '?')}; last remaining/limit: "
        f"{quota_report.get('last_remaining', '?')}/{quota_report.get('last_limit', '?')}; "
        f"rate-limit sleeps: {quota_report.get('rate_limit_sleeps', 0)}; "
        f"backoff retries: {quota_report.get('backoff_retries', 0)}.",
        "",
        "Column definitions: for standalone repos, 'total issues'/'closed "
        "issues' are repo-wide (no label filter). For the two monorepo "
        "targets (golang/go, llvm/llvm-project) they are scoped by the "
        "identifying label itself (gopls / clangd), since there is no "
        "dedicated sub-repo to count against - so 'closed issues' and "
        "'closed bug-labeled' are expected to be equal for those two rows.",
        "",
    ]
    lines += _funnel_table(required)
    lines.append("")
    total_required = _total_fixed(required)
    total_additional = _total_fixed(additional)
    lines.append(
        f"**Total fixed-bug candidates across required targets (1-6): {total_required:,}**"
    )
    lines.append(
        f"**Grand total including additional targets: {total_required + total_additional:,}**"
    )
    lines.append("")
    lines += _yearly_table(required + additional)
    lines.append("")
    lines += _labels_used(results)
    lines.append("")
    lines += extra.additional_targets_section(results)
    lines.append("")
    lines += extra.typescript_section(results)
    lines.append("")
    lines += extra.golang_section(results)
    lines.append("")
    lines += extra.clangd_repo_section(results)
    lines.append("")
    lines += extra.pyright_section(results)
    lines.append("")
    lines += extra.pyright_addressed_section(results)
    lines.append("")
    lines += _optional_targets_section(results)
    lines.append("")
    lines += _anomalies(results)

    path = DATA_DIR / "pilot_summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
