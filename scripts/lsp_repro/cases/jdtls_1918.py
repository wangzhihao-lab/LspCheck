"""Eclipse JDT LS #1918 -- "Race condition with the shared AST provider".

Symptom, from the two fixing PRs: semantic highlighting goes wrong because
`CoreASTProvider` caches an AST that is already out of date with respect to the
buffer. PR #2709: "This fix simply compare the length of the document with the
length of the AST to check if the AST is out-of-date"; its test instructions are
"Opening a complex Java file ... Repeatedly pasting/removing multiple lines of
code ... wrong highlighting occurred approximately 1-2 times per 10 attempts in
version 1.19.0". PR #2714 describes the race: "If a thread calls `reconciled()`
with an out-of-date AST before the `clearReconciliation()` being called from
document handler, then `fReconcileLock` will be occupied by that thread, and the
out-of-date AST will be cached."

Ground-truth fixes: 63805fd0 (#2709) and c22b2299 (#2714), both 2023-07-20,
first in tag v1.26.0. Pre-fix 1.25.0 (2023-06-27), post-fix 1.26.0 (2023-07-26).

This is the one case in the set that is inherently racy, so it is run in race
mode with no waiting between edits and reported as reproduces-in-k-of-n.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from javaproj import with_sources  # noqa: E402
from scenario import Scenario, Step, edit, open_doc, quiesce, request, snapshot, undo, wait  # noqa: E402
from snapshots import norm_raw  # noqa: E402
from textdoc import rng  # noqa: E402

SERVER = "jdtls"
ISSUE = "eclipse-jdtls/eclipse.jdt.ls#1918"
TITLE = "Race condition with the shared AST provider (stale semantic tokens)"
PRE = "1.25.0"
POST = "1.26.0"
SYMPTOM = "semanticTokens computed from an AST that no longer matches the buffer"
FIX_COMMIT = "63805fd0 (#2709) + c22b2299 (#2714), 2023-07-20, released in v1.26.0"

REL = "src/app/Big.java"
VARIANTS = ["paste_race", "paste_race_fast", "paste_settled"]

_METHOD = """
    public int m{i}(int a, int b) {{
        int c = a + b;
        String s = "v" + c;
        if (c > {i}) {{
            c = c - {i};
        }}
        for (int k = 0; k < {i} + 1; k++) {{
            c += k;
        }}
        return c + s.length();
    }}
"""


def _src() -> str:
    body = "".join(_METHOD.format(i=i) for i in range(30))
    return "package app;\n\npublic class Big {\n" + body + "}\n"


SRC = _src()
BLOCK = _METHOD.format(i=999) + _METHOD.format(i=998) + _METHOD.format(i=997)


def _after_header(text: str) -> Dict[str, Dict[str, int]]:
    """Insertion point just after `public class Big {`."""
    return rng(2, len("public class Big {"), 2, len("public class Big {"))


def _tokens(sess) -> Dict[str, Any]:
    return {"textDocument": {"uri": sess.doc(REL).uri}}


def _norm_tokens(result: Any) -> Any:
    """semanticTokens/full returns a flat int array plus a resultId; the id is
    per-request and must be dropped before comparing."""
    if not isinstance(result, dict):
        return None
    data = result.get("data")
    return {"n": len(data) if isinstance(data, list) else None, "data": data}


def build(variant: str = "paste_race") -> Scenario:
    settle = variant.endswith("settled")
    gap = 0.0 if variant == "paste_race_fast" else 0.05
    steps: List[Step] = [open_doc(REL), quiesce(REL), snapshot("baseline")]
    for i in range(6):
        steps.append(edit(REL, _after_header, BLOCK, label=f"paste block {i}"))
        if settle:
            steps.append(quiesce(REL))
        elif gap:
            steps.append(wait(gap))
        # Ask for semantic tokens while the AST may still be reconciling.
        steps.append(request("textDocument/semanticTokens/full", _tokens, label=f"tokens_mid{i}", normalize=_norm_tokens))
        steps.append(undo(REL, label=f"remove block {i}"))
        if settle:
            steps.append(quiesce(REL))
        elif gap:
            steps.append(wait(gap))
        steps.append(request("textDocument/semanticTokens/full", _tokens, label=f"tokens_back{i}", normalize=_norm_tokens))
    steps += [quiesce(REL), snapshot("final_state")]
    return Scenario(
        name=f"jdtls_1918[{variant}]",
        server=SERVER,
        issue=ISSUE,
        description=f"{TITLE} ({variant})",
        files=with_sources({REL: SRC}),
        watch=[REL],
        steps=steps,
        quiet_seconds=4.0,
        quiesce_timeout=400.0,
        probes=[
            request(
                "textDocument/semanticTokens/full", _tokens, label="probe_tokens", normalize=_norm_tokens
            )
        ],
    )


def bug_present(replay: Dict[str, Any], full: Dict[str, Any]) -> Tuple[bool, str]:
    """Every `tokens_backN` is taken at the original text, so they must all agree
    with each other and with a fresh server's tokens for that text."""
    backs = [q for q in replay.get("requests", []) if q["label"].startswith("tokens_back") and q.get("ok")]
    if len(backs) < 2:
        return False, f"only {len(backs)} usable semanticTokens replies -- scenario did not arm"
    sizes = {q["label"]: (q.get("norm") or {}).get("n") for q in backs}
    payloads = {str((q.get("norm") or {}).get("data")) for q in backs}
    reasons = []
    if len(payloads) > 1:
        reasons.append(f"semanticTokens differ across identical buffer states: sizes={sizes}")
    fresh_probe = ((full.get("fresh") or {}).get("final_probes") or {}).get("probe_tokens")
    replay_probe = (replay.get("final_probes") or {}).get("probe_tokens")
    if fresh_probe is not None and replay_probe is not None and fresh_probe != replay_probe:
        reasons.append(
            f"final tokens differ from fresh server (replay n={replay_probe.get('n')} fresh n={fresh_probe.get('n')})"
        )
    diff = full.get("diff") or {}
    if diff.get("flagged"):
        reasons.append(f"replay!=fresh: files={list(diff.get('files', {}))} probes={list(diff.get('probes') or {})}")
    if reasons:
        return True, "; ".join(reasons)[:400]
    return False, f"tokens identical across {len(backs)} identical states and equal to fresh"
