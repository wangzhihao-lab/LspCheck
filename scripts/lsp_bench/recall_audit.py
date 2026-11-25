"""Recall audit: read a seeded random sample of *non-retrieved* issues.

Each audit draws ``PER_SERVER`` issues per server from the issues that the
keyword patterns of that round did not retrieve, writes them to a sheet
(temp/lsp_bench/sheets/audit_<seed>.txt) and records, after reading, which of
them would have been kept (``AUDITS``). Audit 1 ran against the round-1
patterns; its misses led to the round-2 pattern revision (pairs for analyzer
fixes, "import organization", on-type insertion, broader completion
symptoms). Audit 2 ran against the round-2 patterns. Misses that the patterns
still do not retrieve are added to the retrieved set through ``INCLUDE`` so
that they are screened like every other candidate.

Run line: python3 scripts/lsp_bench/recall_audit.py --seed 20260924
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import SERVERS, SHEETS_DIR  # noqa: E402

logger = logging.getLogger("recall_audit")

PER_SERVER = 40

# seed -> (pattern round, server -> {issue number: "<class>: why it would be kept"})
AUDITS: Dict[int, Tuple[str, Dict[str, Dict[int, str]]]] = {
    20260923: ("round 1", {
        "pyright": {},
        "tsserver": {44374: "R4: import-path completion inserts a '.ts' extension despite importModuleSpecifierEnding, an error before TS 5.0"},
        "rust-analyzer": {11005: "R4: on-type semicolon insertion after '=' breaks a complex function signature"},
        "gopls": {36824: "R4: import organization on a single-line file drops the function",
                  44589: "R4: literal completion with a dot import inserts '&..Buffer{}'",
                  71313: "R4: slices.Contains modernizer fix does not compile",
                  73576: "R4: minmax modernizer offers an invalid fix under else-if"},
    }),
    20260924: ("round 2", {
        "pyright": {},
        "tsserver": {57498: "R4: 'Delete all unused declarations' leaves self-referencing unused functions and their diagnostics"},
        "rust-analyzer": {14841: "R3: definition of the second 'a' after an eager macro argument goes into the vec! expansion, unlike the first 'a'"},
        "gopls": {35548: "R1: changing the env (GOFLAGS) through didChangeConfiguration does not recompute diagnostics"},
    }),
}

# Audit finds that no pattern retrieves (server -> {issue: class}); retrieve.py
# adds them with pattern id "audit" so they are screened like any retrieved issue.
INCLUDE: Dict[str, Dict[int, str]] = {
    "tsserver": {44374: "R4", 57498: "R4"},
    "rust-analyzer": {14841: "R3"},
    "gopls": {35548: "R1"},
}


def write_sample(seed: int) -> Path:
    """Write the audit sheet for ``seed`` against the current patterns."""
    from retrieve import retrieve
    rng = random.Random(seed)
    lines: List[str] = []
    for server in SERVERS:
        issues, found = retrieve(server)
        got = {r.number for r in found}
        rest = [i for i in issues if i.number not in got]
        sample = sorted(rng.sample(rest, min(PER_SERVER, len(rest))), key=lambda i: i.number)
        lines.append(f"===== {server}: {len(rest)} not retrieved; sample {len(sample)}")
        for i in sample:
            fx = " | ".join(c.subject for c in i.fix_commits)[:120]
            lines.append(f"#{i.number} {i.title[:100]} || {' '.join(i.clean_body.split())[:220]} || FIX: {fx}")
    path = SHEETS_DIR / f"audit_{seed}.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def summary() -> List[str]:
    """Markdown lines summarising every recorded audit."""
    out: List[str] = []
    for seed, (rnd, misses) in sorted(AUDITS.items()):
        total = sum(len(v) for v in misses.values())
        per = ", ".join(f"{s} {len(misses.get(s, {}))}/{PER_SERVER}" for s in SERVERS)
        out.append(f"- Audit seed {seed} ({rnd} patterns): {total} of {PER_SERVER * len(SERVERS)} sampled "
                   f"non-retrieved issues would have been kept ({per}).")
        for s in SERVERS:
            for n, why in sorted(misses.get(s, {}).items()):
                out.append(f"  - {s} #{n}: {why}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="write a recall-audit sample sheet")
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logger.info("wrote %s", write_sample(args.seed))


if __name__ == "__main__":
    main()
