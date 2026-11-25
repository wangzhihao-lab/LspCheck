"""Write data/lsp_pilot/eyeball_sample.md: 15 randomly sampled fixed-bug
candidates per target (random.seed(42)) so a reader can judge whether
these are genuine bug reports with fixes.

Run: imported by run_pilot.py, not run directly.
"""
from __future__ import annotations

from pathlib import Path

from config import DATA_DIR, EYEBALL_BODY_CHARS, LABEL_EVIDENCE_TARGET_KEY
from outputs import sample_for_eyeball


def _closing_evidence_repr(row: dict, target_key: str) -> str:
    merged_prs = [p for p in row["closing_prs"] if p["merged"]]
    if merged_prs:
        return ", ".join(p["url"] for p in merged_prs)
    if row["closer_commit"]:
        return f"commit {row['closer_commit']['url']}"
    if row["closing_prs"]:
        return "unmerged PR ref only: " + ", ".join(p["url"] for p in row["closing_prs"])
    if target_key == LABEL_EVIDENCE_TARGET_KEY:
        return "NONE - evidence for this row is the label combination, not a link (see summary)"
    return "NONE (should not happen for a fixed-bug candidate)"


def write_eyeball_sample(results: list[dict]) -> Path:
    path = DATA_DIR / "eyeball_sample.md"
    lines = [
        "# Eyeball sample - fixed bug candidates",
        "",
        "15 per target (fewer if the target has fewer candidates), drawn "
        "with `random.Random(42).sample()` over candidates sorted by issue "
        "number. Use this to judge whether these are genuine bug reports "
        "with a real fix, not e.g. duplicates, feature requests, or "
        "bot/administrative closes.",
    ]
    for r in results:
        target = r["target"]
        if target.counts_only or r.get("funnel") is None:
            continue
        fixed_rows = r["fixed_rows"]
        sample = sample_for_eyeball(fixed_rows)
        lines.append("")
        lines.append(
            f"## {target.key} ({target.owner}/{target.name}) - "
            f"{len(sample)} of {len(fixed_rows)} fixed-bug candidates sampled"
        )
        if not sample:
            lines.append("")
            lines.append("_No fixed-bug candidates for this target._")
            continue
        for row in sample:
            body_snip = row["body_truncated"][:EYEBALL_BODY_CHARS].replace("\n", " ").strip()
            lines.append("")
            lines.append(f"### #{row['number']}: {row['title']}")
            lines.append(f"- URL: {row['url']}")
            lines.append(f"- closedAt: {row['closedAt']}")
            lines.append(f"- Closing evidence: {_closing_evidence_repr(row, target.key)}")
            lines.append(f"- Body (first {EYEBALL_BODY_CHARS} chars): {body_snip}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
