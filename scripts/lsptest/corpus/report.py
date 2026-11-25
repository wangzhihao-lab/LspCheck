"""data/lsptest/corpus_prepared.md: one row per project x server, the recommended
exclusions and the settle time per server, with the settle rule and both noise
heuristics restated.

A project is recommended for exclusion when any of its servers failed to prepare,
failed to settle within the cap, or produced overwhelming import noise (>= 100 noise
diagnostics, or noise making up >= 70% of >= 20 diagnostics; constants in common.py).

Run line: imported by scripts/lsptest/prepare_corpus.py; not run directly.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Mapping, Sequence

from .common import NOISE_MIN_COUNT, NOISE_MIN_RATIO, NOISE_MIN_RATIO_COUNT, OUT_MD

Record = Mapping[str, Any]


def _overwhelming(noise: int, total: int) -> bool:
    return noise >= NOISE_MIN_COUNT or bool(total and noise / total >= NOISE_MIN_RATIO
                                            and noise >= NOISE_MIN_RATIO_COUNT)


def recommend_exclusions(records: Sequence[Record]) -> Dict[str, List[str]]:
    """A project is flagged when any of its servers failed to prepare, failed
    to settle within the cap, or produced overwhelming noise (>=100 noise
    diagnostics, or noise making up >=70% of >=20 diagnostics)."""
    by_repo: Dict[str, List[str]] = {}
    for r in records:
        reasons = []
        if r.get("skipped_reason") == "clone_failed":
            reasons.append(f"failed to prepare ({r['server']})")
        elif not r.get("settled"):
            reasons.append(f"did not settle within cap ({r['server']}, {r.get('seconds', '?')}s)")
        noise = r.get("diagnostics_import_noise") or 0
        total = r.get("diagnostics_total") or 0
        if _overwhelming(noise, total):
            reasons.append(f"overwhelming import noise ({noise}/{total} diagnostics, {r['server']})")
        if reasons:
            by_repo.setdefault(r["repo"], []).extend(reasons)
    return by_repo


def _median(vals: Sequence[float]) -> float:
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _preamble(records: Sequence[Record]) -> List[str]:
    n_projects = len({(r.get("language"), r.get("repo"), r.get("commit")) for r in records})
    return [
        "# LSP test corpus preparation", "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
        f"{n_projects} projects x their language's server(s) = {len(records)} records.", "",
        "Settle rule: push servers (pyright, ts6, gopls) wait for publishDiagnostics on every "
        "opened file plus 3s with no server traffic at all; pull servers (ts7, rust-analyzer) "
        "poll textDocument/diagnostic until two consecutive polls agree; rust-analyzer additionally "
        "waits for a quiescent experimental/serverStatus notification. Hard cap: 600s per project x server.", "",
        "\"Import noise\" is a heuristic over the final diagnostics: pyright "
        "reportMissingImports/reportMissingModuleSource, TS codes 2307/2306/2792/7016, "
        "rust-analyzer unresolved-import, plus a generic message regex (cannot find "
        "module/package, could not be resolved, missing go.sum entry, ...). \"Overwhelming noise\" "
        f"below means >= {NOISE_MIN_COUNT} noise diagnostics, or noise making up >= "
        f"{int(NOISE_MIN_RATIO * 100)}% of >= {NOISE_MIN_RATIO_COUNT} diagnostics.", "",
    ]


def _results_table(records: Sequence[Record]) -> List[str]:
    lines = [
        "## Results", "",
        "| Language | Repo | Server | Deps | Settled | Seconds | Diag E/W/I/H | Noise | Peak RSS MB | Notes |",
        "|---|---|---|---|---|---:|---|---:|---:|---|",
    ]
    for r in sorted(records, key=lambda r: (r["language"], r["repo"], r["server"])):
        sev = r.get("diagnostics_by_severity") or {}
        diag = f"{sev.get('error', 0)}/{sev.get('warning', 0)}/{sev.get('information', 0)}/{sev.get('hint', 0)}"
        rss = r.get("peak_rss_kb")
        rss_mb = f"{rss / 1024:.0f}" if isinstance(rss, (int, float)) else "-"
        notes = (r.get("skipped_reason") or r.get("error") or "")[:60]
        lines.append(f"| {r['language']} | {r['repo']} | {r['server']}-{r['version']} | "
                     f"{r.get('deps_status')} | {r.get('settled')} | {r.get('seconds', '-')} | {diag} | "
                     f"{r.get('diagnostics_import_noise', '-')} | {rss_mb} | {notes} |")
    return lines


def _exclusions(records: Sequence[Record]) -> List[str]:
    lines = ["", "## Recommended exclusions", ""]
    excluded = recommend_exclusions(records)
    if not excluded:
        return lines + ["None."]
    return lines + [f"- {repo}: {'; '.join(reasons)}" for repo, reasons in sorted(excluded.items())]


def _settle_times(records: Sequence[Record]) -> List[str]:
    lines = ["", "## Settle time by server (seconds; settled runs only)", ""]
    for kind in sorted({r["server"] for r in records}):
        vals = [r["seconds"] for r in records if r["server"] == kind and r.get("settled")
                and isinstance(r.get("seconds"), (int, float))]
        if vals:
            lines.append(f"- {kind}: n={len(vals)} median={_median(vals):.1f}s max={max(vals):.1f}s")
        else:
            lines.append(f"- {kind}: no settled runs")
    return lines


def write_markdown_report(records: Sequence[Record], path: str = OUT_MD) -> None:
    """Write the report for `records` (the merged file content) to `path`."""
    lines = _preamble(records) + _results_table(records) + _exclusions(records) + _settle_times(records)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


__all__ = ["recommend_exclusions", "write_markdown_report"]
