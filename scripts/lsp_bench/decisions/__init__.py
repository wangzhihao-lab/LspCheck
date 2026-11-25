"""Manual screening decisions for retrieved issues, merged per server.

Each module in this package covers a slice of the screening sheets written by
``mine_candidates.py retrieve`` and defines:

* ``SERVER``: the server name;
* ``KEEP``: issue number -> (oracle_class, grade, reason, trigger_hint), where
  oracle_class is one of R1..R5, grade is A/B/C (A: self-contained snippet and
  clear steps, observable by a headless client; B: reproducible but needs
  reconstruction such as a multi-file project, a config file, a dependency or a
  specific timing; C: vague, intermittent, large project or editor-specific
  trigger), reason is one factual screening sentence, trigger_hint is
  "<subtype>: <short note>" on the history / transformation / query that
  should expose it. Subtypes: R1 edit-undo, typing, open-close, file-op,
  config, dependency-edit, query-order, race; R2 resolve, semtok-delta,
  stale-edit; R3 pull-push, semtok-range, highlight-refs, def-consistency,
  other-route; R4 quickfix, codeaction-other, format, completion, organize;
  R5 blank-lines, comment, whitespace, crlf, non-ascii, file-edge;
* ``REJECT``: rejection code -> tuple of issue numbers (codes in REJECT_CODES).

Every retrieved issue must appear exactly once across KEEP and REJECT of its
server; ``mine_candidates.py`` checks this.

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Dict, List, Tuple

KeepEntry = Tuple[str, str, str, str]

REJECT_CODES: Dict[str, str] = {
    "type": "type-checking or semantic analysis bug without a state, edit, route or layout dimension",
    "refactor": "refactoring correctness (rename, extract, inline, move, convert, change signature)",
    "ui": "editor-UI-only or client-extension behaviour",
    "crash": "crash only on malformed or fuzz-like input, no oracle-visible difference",
    "perf": "performance, memory or hang without a result difference",
    "feature": "missing feature or capability, enhancement, or intended behaviour",
    "display": "content or ranking quality of hover/completion/signature/inlay text without a state, edit or route dimension",
    "cli": "command-line, build, packaging, install or project-loading issue outside an editing session",
    "semantic_edit": "code action or completion yields valid code that is merely not what the user wanted (no new error, diagnostic cleared)",
    "whitespace_only": "formatting output is wrong but whitespace-only and plausibly idempotent, so the edit-validity check cannot see it",
    "other": "none of the oracle classes applies",
}


def load_all() -> Dict[str, Tuple[Dict[int, KeepEntry], Dict[str, Tuple[int, ...]]]]:
    """Merge all decision modules into server -> (KEEP, REJECT)."""
    merged: Dict[str, Tuple[Dict[int, KeepEntry], Dict[str, List[int]]]] = {}
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        mod = importlib.import_module(f"{__name__}.{info.name}")
        server = getattr(mod, "SERVER")
        keep, reject = merged.setdefault(server, ({}, {}))
        for num, entry in getattr(mod, "KEEP").items():
            if num in keep:
                raise ValueError(f"{server} #{num} kept twice")
            keep[num] = entry
        for code, nums in getattr(mod, "REJECT").items():
            if code not in REJECT_CODES:
                raise ValueError(f"unknown reject code {code} in {info.name}")
            reject.setdefault(code, []).extend(nums)
    return {s: (k, {c: tuple(v) for c, v in r.items()}) for s, (k, r) in merged.items()}
