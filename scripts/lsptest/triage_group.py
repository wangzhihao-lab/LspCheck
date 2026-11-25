"""Grouping of confirmed violations for triage (plan/tool_design_v1.md section 11.2).

Rows come from a campaign's violations.jsonl: the last row per vid (a rerun replaces a row),
confirmed (k == n) and not flagged incomplete. A group is (signature, method, case family):
the signature is "<server kind>|<oracle>|<shape>", the method is the key's method, and the
case family is what the oracle says about the kind of case (R1 history family H1..H8, R2 and
R3 sub-check, R4 check kind and mutation, R5 transformation kind, R6 compared method, R0 the
fresh pair). The representative is the member with the fewest ops (then the smallest vid).
Group ids are readable and stable across triage runs: a slug of server, oracle, shape and
family plus a short hash of the group's identity.

Run line: imported by triage.py and tests/test_triage.py; not run directly.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from campaign_store import latest_rows  # noqa: E402

FamilyFn = Callable[[Mapping[str, Any]], str]


def _r4_family(case: Mapping[str, Any]) -> str:
    kind = str(case.get("kind") or "-")
    mid = (case.get("mutation") or {}).get("id") if isinstance(case.get("mutation"), dict) else None
    return f"{kind}:{mid}" if kind == "mutation" and mid else kind


CASE_FAMILY: Dict[str, FamilyFn] = {
    "r0_crash": lambda c: "fresh-pair",
    "r1_history": lambda c: str(c.get("family") or "-"),
    "r2_handles": lambda c: str(c.get("sub") or "-"),
    "r3_routes": lambda c: str(c.get("sub") or "-"),
    "r4_edits": _r4_family,
    "r5_transforms": lambda c: str((c.get("transform") or {}).get("kind") or "-"),
    "r6_crossimpl": lambda c: str(c.get("method") or "-"),
}


def case_family(oracle: str, case: Mapping[str, Any]) -> str:
    fn = CASE_FAMILY.get(oracle)
    if fn is not None:
        return fn(case or {})
    return str((case or {}).get("family") or (case or {}).get("sub") or (case or {}).get("kind") or "-")


@dataclass
class Group:
    gid: str
    signature: str
    method: str
    family: str
    members: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def server_kind(self) -> str:
        return self.signature.split("|")[0]

    @property
    def oracle(self) -> str:
        return self.signature.split("|")[1]

    @property
    def shape(self) -> str:
        return self.signature.split("|", 2)[2]

    @property
    def representative(self) -> Dict[str, Any]:
        return representative(self.members)

    def summary(self) -> Dict[str, Any]:
        """Where the group's members come from (for the index and the report)."""
        def distinct(k: str) -> List[Any]:
            return sorted({str(m.get(k)) for m in self.members})
        return {"members": len(self.members), "runs": distinct("run_id"), "projects": distinct("project"),
                "servers": distinct("server"), "timings": distinct("timing"), "seeds": distinct("seed"),
                "vids": sorted(m["vid"] for m in self.members)}


def representative(members: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """The member with the fewest ops; ties broken by vid."""
    if not members:
        raise ValueError("empty group")
    return dict(min(members, key=lambda m: (int(m.get("n_ops") or 0), str(m.get("vid")))))


def slug(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return s[:limit].strip("-") or "x"


def group_id(signature: str, method: str, family: str) -> str:
    kind, oracle, shape = (signature.split("|", 2) + ["", ""])[:3]
    digest = hashlib.sha1(f"{signature}|{method}|{family}".encode()).hexdigest()[:6]
    return f"{slug(kind)}-{oracle.split('_')[0]}-{slug(shape, 40)}-{slug(family, 16)}-{digest}"


def confirmed_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in latest_rows(rows) if r.get("confirmed") and not r.get("incomplete")]


def group_rows(rows: Sequence[Mapping[str, Any]]) -> List[Group]:
    """Confirmed rows grouped by (signature, method, case family), groups sorted by that key."""
    groups: Dict[Tuple[str, str, str], Group] = {}
    for r in confirmed_rows(rows):
        method = str((r.get("key") or {}).get("method", ""))
        fam = case_family(str(r.get("oracle")), r.get("case") or {})
        k = (str(r.get("signature")), method, fam)
        if k not in groups:
            groups[k] = Group(group_id(*k), *k)
        groups[k].members.append(dict(r))
    return [groups[k] for k in sorted(groups)]


__all__ = ["CASE_FAMILY", "Group", "case_family", "confirmed_rows", "group_id", "group_rows", "latest_rows",
           "representative", "slug"]
