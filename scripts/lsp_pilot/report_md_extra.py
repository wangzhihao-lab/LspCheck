"""Per-target supplementary detail sections for pilot_summary.md, split out
of report_md.py to keep that file under the 300-line budget.

Run: imported by report_md.py, not run directly.
"""
from __future__ import annotations

from config import ADDITIONAL_TARGETS, LABEL_EVIDENCE_TARGET_KEY, TS_LANGUAGE_SERVICE_KEYWORDS

ADDITIONAL_KEYS = {t.key for t in ADDITIONAL_TARGETS}


def _fmt(v) -> str:
    return "-" if v is None else f"{v:,}"


def _mini_funnel_table(results: list[dict]) -> list[str]:
    lines = [
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


def additional_targets_section(results: list[dict]) -> list[str]:
    additional = [r for r in results if r["target"].key in ADDITIONAL_KEYS]
    if not additional:
        return []
    total = sum((r["funnel"].fixed_bug_candidates or 0) for r in additional if r.get("funnel"))
    lines = [
        "## Additional targets (coordinator addition, 2026-09-20)",
        "",
        "Reported separately from the required-targets total above (different "
        "repos / different evidence criteria - see detail sections below).",
        "",
    ]
    lines += _mini_funnel_table(additional)
    lines.append("")
    lines.append(f"**Additional-targets subtotal: {total:,}**")
    return lines


def typescript_section(results: list[dict]) -> list[str]:
    ts = next((r for r in results if r["target"].key == "microsoft-typescript"), None)
    if ts is None or ts.get("funnel") is None:
        return []
    all_counts = ts.get("all_domain_counts", {})
    lines = [
        "## microsoft/TypeScript domain-label detail",
        "",
        f"All `Domain: *` labels on the repo with their closed-issue counts "
        f"({len(all_counts)} total, sorted descending):",
        "",
        "| Domain label | Closed issues |",
        "|---|---:|",
    ]
    for d in sorted(all_counts, key=lambda k: -all_counts[k]):
        lines.append(f"| `{d}` | {all_counts[d]:,} |")
    lines.append("")
    spec_check = ts.get("spec_guess_check", [])
    n_exist = sum(1 for _d, exists in spec_check if exists)
    lines.append(
        f"**Anomaly**: only {n_exist} of the task spec's {len(spec_check)} example "
        "domain labels exist verbatim: "
        + ", ".join(f"`{d}`" + ("" if exists else " (missing)") for d, exists in spec_check)
    )
    lines.append("")
    lines.append(
        "Per coordinator direction (2026-09-20), the language-service subset "
        "is instead every `Domain:` label whose name mentions any of: "
        + ", ".join(f"`{k}`" for k in TS_LANGUAGE_SERVICE_KEYWORDS)
        + " (case-insensitive substring match)."
    )
    lines.append("")
    matched = ts.get("keyword_matched_domains", [])
    per_domain = ts.get("per_domain_counts", {})
    lines.append(f"Matched {len(matched)} domain label(s):")
    lines.append("")
    lines.append("| Domain label | Closed `Bug` AND domain issues |")
    lines.append("|---|---:|")
    for d in matched:
        lines.append(f"| `{d}` | {per_domain.get(d, '-')} |")
    lines.append("")
    f = ts["funnel"]
    lines.append(
        f"Union of Bug AND matched domains, deduped by issue number: "
        f"**{_fmt(f.closed_bug_labeled)} closed issues**, of which "
        f"**{_fmt(f.fixed_bug_candidates)} are fixed-bug candidates**."
    )
    return lines


def golang_section(results: list[dict]) -> list[str]:
    go = next((r for r in results if r["target"].key == "golang-go-gopls"), None)
    if go is None or not go.get("special_stats"):
        return []
    s = go["special_stats"]
    bug_report_note = " (BugReport label does not exist)" if s.get("BugReport_label_missing") else ""
    return [
        "## golang/go gopls detail",
        "",
        f"- closed `gopls` AND `BugReport`: {_fmt(s.get('gopls_and_BugReport_closed'))}{bug_report_note}",
        f"- closed `gopls` AND `NeedsFix`: {_fmt(s.get('gopls_and_NeedsFix_closed'))}",
        f"- closed `gopls` AND `FixPending`: {_fmt(s.get('gopls_and_FixPending_closed'))}",
        "",
        "Proxy signal comparison over all closed `gopls`-labeled issues "
        f"(population {s.get('proxy_scan_population', 0):,}), since gopls fixes "
        "land as Gerrit CLs mirrored to golang/tools and often never produce a "
        "merged PR inside golang/go itself:",
        f"- has a ClosedEvent closer commit: {s.get('closer_commit_proxy_count', 0):,}",
        "- has a go.dev/cl or golang.org/cl link in the last 3 comments: "
        f"{s.get('cl_link_comment_proxy_count', 0):,}",
        f"- has both: {s.get('both_proxies_count', 0):,}",
    ]


def clangd_repo_section(results: list[dict]) -> list[str]:
    r = next((x for x in results if x["target"].key == "clangd-clangd-repo"), None)
    if r is None or r.get("funnel") is None:
        return []
    s = r.get("special_stats", {})
    f = r["funnel"]
    return [
        "## clangd/clangd (separate repo) detail",
        "",
        f"Label filter used: `{f.label_repr}`. llvm/llvm-project's `label:clangd` "
        "row above is kept unchanged - this is an additional, separate source, "
        "since clangd/clangd is clangd's primary issue tracker.",
        "",
        "Proxy signal comparison over all closed issues in this set "
        f"(population {s.get('proxy_scan_population', 0):,}), since clangd fixes "
        "land in llvm/llvm-project (cross-repo):",
        f"- has a ClosedEvent closer commit: {s.get('closer_commit_proxy_count', 0):,}",
        "- has a github.com/llvm/llvm-project/commit or /pull link in the last "
        f"3 comments: {s.get('llvm_link_comment_proxy_count', 0):,}",
        f"- has both: {s.get('both_proxies_count', 0):,}",
    ]


def pyright_section(results: list[dict]) -> list[str]:
    pr = next((r for r in results if r["target"].key == "pyright"), None)
    if pr is None or not pr.get("special_stats"):
        return []
    s = pr["special_stats"]
    if not s.get("addressed_in_next_version_label_exists"):
        return [
            "## pyright detail",
            "",
            "- label \"addressed in next version\" does not exist on this repo.",
        ]
    return [
        "## pyright detail",
        "",
        "- closed issues labeled \"addressed in next version\": "
        f"{_fmt(s.get('addressed_in_next_version_closed_count'))} "
        "(count only; see the dedicated row/section below for the full "
        "bug AND addressed-in-next-version breakdown)",
    ]


def pyright_addressed_section(results: list[dict]) -> list[str]:
    r = next((x for x in results if x["target"].key == LABEL_EVIDENCE_TARGET_KEY), None)
    if r is None or r.get("funnel") is None:
        return []
    s = r.get("special_stats", {})
    f = r["funnel"]
    return [
        "## pyright \"addressed in next version\" detail",
        "",
        "This row's evidence is the label combination `bug` AND `addressed in "
        "next version`, not a linked PR/commit - the pyright maintainer often "
        "closes a fixed bug by comment instead of a GitHub-linked PR, which is "
        "why the primary pyright row's fixed-bug-candidate rate is so low "
        "(51/3977 = 1.3%).",
        "",
        f"- closed issues with both labels: {_fmt(f.closed_bug_labeled)}",
        f"- of which also have a ClosedEvent closer commit: "
        f"{s.get('closer_commit_count', 0):,} ({s.get('closer_commit_rate_pct', 0)}%)",
    ]
