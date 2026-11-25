"""Cost controls of the campaign: legitimate-difference labels and the signature cap.

Labels. Some oracles give a known class of legitimate differences a key method (and so a
signature) of its own instead of dropping it: r3_routes answers definition at a shorthand site
(`definitionConsistency.shorthand`) and at a call-like site that adds the resolved signature
(`definitionConsistency.signature`), see r3_routes.site_label. LABELS maps oracle -> labelled key
method -> reason; register_label() extends it (an oracle module, or any module imported before the
campaign runs, can call it; no oracle file has to change). A candidate whose key method is a
registered label is recorded as "labelled-legitimate" and not replayed. Only exact method names
are registered, so an unlabelled difference is never skipped this way.

Cap. Once a signature has been confirmed in K runs of a campaign (CapConfig.runs, default 3; 0
turns the cap off), later candidates of that signature are recorded as "capped" and not
replayed. Scope "campaign" counts runs campaign-wide; scope "build" counts per (signature,
project, server build), which keeps "not confirmed on the post-fix build" meaningful in a
benchmark. The scheduler keeps the counts (signature_counts.json in the campaign directory,
rewritten after every run) and each worker reads it just before confirming, so concurrent runs
can exceed K by at most the number of runs in flight.

Run line: imported by campaign.py, campaign_run.py, campaign_estimate.py and the tests (oracle modules may import register_label); not run directly.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from model import Violation  # noqa: E402

LABELS: Dict[str, Dict[str, str]] = {}
SCOPES = ("campaign", "build")
COUNTS_FILE = "signature_counts.json"


def register_label(oracle: str, method: str, reason: str) -> None:
    """Declare that candidates of `oracle` whose key method is `method` are legitimate differences."""
    LABELS.setdefault(oracle, {})[method] = reason


register_label("r3_routes", "definitionConsistency.signature",
               "TypeScript adds the declaration of the resolved call/construct/instanceof signature at a call-like "
               "site (the answers differ only in entries wider than the name); r3_routes.site_label")
register_label("r3_routes", "definitionConsistency.shorthand",
               "`{ name }` names a member and a variable (object and struct literals, binding patterns); "
               "r3_routes.site_label")


def label_of(oracle: str, method: str) -> str:
    """The reason when (oracle, key method) is a registered legitimate-difference label, else ""."""
    return LABELS.get(oracle, {}).get(method, "")


def signature_label(signature: str) -> str:
    """label_of for a signature "<kind>|<oracle>|<method>:<shape tail>"."""
    parts = signature.split("|", 2)
    return label_of(parts[1], parts[2].split(":", 1)[0]) if len(parts) == 3 else ""


# ------------------------------------------------------------------ cap
@dataclass(frozen=True)
class CapConfig:
    runs: int = 3  # 0: no cap
    scope: str = "campaign"  # campaign | build


def cap_key(signature: str, project: str, version: str, scope: str) -> str:
    return signature if scope == "campaign" else f"{signature}@{project}@{version}"


def confirmed_runs(rows: Iterable[Mapping[str, Any]], scope: str) -> Dict[str, Set[str]]:
    """cap key -> run ids with a confirmed violation of it (violations.jsonl rows)."""
    out: Dict[str, Set[str]] = {}
    for r in rows:
        if r.get("confirmed") and not r.get("incomplete") and r.get("signature"):
            k = cap_key(str(r["signature"]), str(r.get("project", "")), str(r.get("server_version", "")), scope)
            out.setdefault(k, set()).add(str(r.get("run_id", "")))
    return out


def capped_keys(counts: Mapping[str, Set[str]], cap: CapConfig) -> Set[str]:
    return {k for k, runs in counts.items() if cap.runs > 0 and len(runs) >= cap.runs}


def write_counts(path: str, counts: Mapping[str, Set[str]], cap: CapConfig) -> None:
    """Atomic write of the confirmation counts and the capped keys."""
    doc = {"runs": cap.runs, "scope": cap.scope, "capped": sorted(capped_keys(counts, cap)),
           "counts": {k: len(v) for k, v in sorted(counts.items())}}
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    os.replace(tmp, path)


def read_capped(path: str, fallback: Sequence[str] = ()) -> Set[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f).get("capped") or [])
    except (OSError, json.JSONDecodeError):
        return set(fallback)


# ------------------------------------------------------------------ splitting a run's candidates
@dataclass
class Skipped:
    status: str  # labelled-legitimate | capped
    signature: str
    reason: str
    violations: List[Violation]


def split_candidates(candidates: Sequence[Violation], capped: Set[str], scope: str, project: str,
                     version: str) -> Tuple[List[Violation], List[Skipped]]:
    """(candidates to replay, skipped signatures with their candidates, first-seen order)."""
    keep: List[Violation] = []
    skipped: Dict[str, Skipped] = {}
    for v in candidates:
        label = label_of(v.oracle, v.key.method)
        status = "labelled-legitimate" if label else \
            ("capped" if cap_key(v.signature, project, version, scope) in capped else "")
        if not status:
            keep.append(v)
            continue
        if v.signature not in skipped:
            reason = label or f"signature already confirmed in the cap number of runs ({scope} scope)"
            skipped[v.signature] = Skipped(status, v.signature, reason, [])
        skipped[v.signature].violations.append(v)
    return keep, list(skipped.values())


def skip_counts(skipped: Sequence[Skipped]) -> Dict[str, int]:
    """Per-run counters for results.jsonl."""
    out = {"labelled_legitimate": 0, "labelled_candidates": 0, "capped": 0, "capped_candidates": 0}
    for s in skipped:
        pre = "labelled" if s.status == "labelled-legitimate" else "capped"
        out["labelled_legitimate" if pre == "labelled" else "capped"] += 1
        out[f"{pre}_candidates"] += len(s.violations)
    return out


def replay_status(reproduced: str, incomplete: bool) -> str:
    """Status of a replayed candidate: confirmed (n/n), flaky (0 < k < n), not-reproduced, incomplete."""
    k, _, n = reproduced.partition("/")
    if incomplete:
        return "incomplete"
    if k.isdigit() and n.isdigit() and int(n) > 0 and k == n:
        return "confirmed"
    return "flaky" if k.isdigit() and int(k) > 0 else "not-reproduced"


def optional_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def parse_cap(raw: Optional[Mapping[str, Any]]) -> CapConfig:
    """The config's "signature_cap" object ({runs, scope}); defaults when absent."""
    raw = raw or {}
    scope = str(raw.get("scope", "campaign"))
    if scope not in SCOPES:
        raise ValueError(f"signature_cap.scope must be one of {SCOPES}")
    return CapConfig(optional_int(raw.get("runs", 3), 3), scope)


__all__ = ["COUNTS_FILE", "CapConfig", "LABELS", "SCOPES", "Skipped", "cap_key", "capped_keys", "confirmed_runs",
           "label_of", "parse_cap", "read_capped", "register_label", "replay_status", "signature_label",
           "skip_counts", "split_candidates", "write_counts"]
