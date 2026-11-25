"""Shared data contract for the functional-oracle tool. Implementations may add
new classes but must not change or remove the fields defined here.

Run line: imported by the lsptest modules; not run directly.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

Pos = Tuple[int, int]  # (line, character), 0-based, UTF-16 code units


@dataclass(frozen=True)
class Op:
    """One serializable client action. kind: open | change | close | save | set_config |
    fs_write | fs_rename | wait | request (a position query: text = method, start = position)."""

    kind: str
    path: str = ""
    start: Optional[Pos] = None
    end: Optional[Pos] = None
    text: str = ""
    new_path: str = ""
    settings: Optional[Dict[str, Any]] = None
    delay_ms: int = 0  # wait after sending; 0 = race mode

    def to_json(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v not in (None, "", 0) or k == "kind"}

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "Op":
        d = dict(d)
        for k in ("start", "end"):
            if d.get(k) is not None:
                d[k] = tuple(d[k])
        return Op(**d)


@dataclass(frozen=True)
class QueryKey:
    method: str
    path: str
    line: int = -1
    character: int = -1
    extra: str = ""  # e.g. diagnostic index, range spec, capability variant


@dataclass
class QueryResult:
    key: QueryKey
    norm: Any  # normalized, JSON-serializable, comparable with ==
    raw: Any = None  # kept only when debugging; may be dropped to save space
    error: Optional[Tuple[str, Any]] = None  # ("error", code) when the request failed
    seconds: float = 0.0


@dataclass
class Snapshot:
    label: str
    server: str  # "<kind>-<version>"
    settled: bool
    results: Dict[QueryKey, QueryResult] = field(default_factory=dict)
    contents_sha: str = ""  # hash of all open document texts at snapshot time


@dataclass(frozen=True)
class RunConfig:
    server_kind: str
    server_version: str
    project: str  # "<owner>/<repo>@<commit12>" or a benchmark case id
    oracle: str  # r1_history | r2_handles | r3_routes | r4_edits | r5_transforms | r6_crossimpl
    seed: int
    timing: str = "settled"  # settled | race0 | race50 | race200
    max_files: int = 3
    max_positions_per_file: int = 12
    settle_timeout_s: float = 300.0


@dataclass
class Violation:
    oracle: str
    server: str
    project: str
    key: QueryKey
    expected: Any  # reference result (fresh / fresh handle / mapped / other route / other implementation)
    actual: Any
    ops: List[Op] = field(default_factory=list)
    detail: str = ""
    reproduced: str = "0/0"  # e.g. "3/3" after flake.py
    reduced_ops: List[Op] = field(default_factory=list)
    signature: str = ""
    run_id: str = ""

    def to_json(self) -> str:
        d = asdict(self)
        d["key"] = asdict(self.key)
        d["ops"] = [o.to_json() for o in self.ops]
        d["reduced_ops"] = [o.to_json() for o in self.reduced_ops]
        return json.dumps(d, ensure_ascii=False, default=str)


__all__ = ["Op", "Pos", "QueryKey", "QueryResult", "RunConfig", "Snapshot", "Violation"]
