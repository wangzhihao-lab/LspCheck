"""Shared types and helpers for mapping a fix to pre-fix / post-fix releases.

``VersionMapping`` is what every server-specific mapper returns. The mapper
registry ``MAPPERS`` (server -> callable) is filled by the ``versions_*``
modules through ``register_mapper``.

Run line: imported by versions_*.py and mine_candidates.py, not run directly.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from paths import CACHE_DIR

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VersionMapping:
    """Fix reference plus the nearest released builds without / with the fix."""

    fix_ref: str
    fix_shas: Tuple[str, ...]
    fix_date: Optional[str]
    pre_version: Optional[str]
    post_version: Optional[str]
    pre_date: Optional[str]
    post_date: Optional[str]
    mapping_confidence: str  # high | medium | low | none
    mapping_method: str
    builds_obtainable: bool
    build_notes: str
    extra: Dict[str, object] = field(default_factory=dict)


Mapper = Callable[..., VersionMapping]
MAPPERS: Dict[str, Mapper] = {}


def register_mapper(server: str) -> Callable[[Mapper], Mapper]:
    """Decorator registering a version mapper for a server."""
    def deco(fn: Mapper) -> Mapper:
        MAPPERS[server] = fn
        return fn
    return deco


def semver_key(version: str) -> Tuple[int, ...]:
    """Numeric sort key for 'v1.2.3', '1.2.3', 'gopls/v0.14.2'."""
    nums = re.findall(r"\d+", version.split("-")[0])
    return tuple(int(n) for n in nums)


def earliest(versions: Iterable[str]) -> Optional[str]:
    vs = sorted(set(versions), key=semver_key)
    return vs[0] if vs else None


def previous_release(ordered: Sequence[str], version: str, excluded: Iterable[str] = ()) -> Optional[str]:
    """Greatest release in ``ordered`` (ascending) below ``version`` and not in ``excluded``."""
    bad = set(excluded)
    key = semver_key(version)
    below = [v for v in ordered if semver_key(v) < key and v not in bad]
    return below[-1] if below else None


def npm_times(package: str) -> Dict[str, str]:
    """Return ``npm view <package> time --json`` (version -> ISO publish time), cached."""
    path = CACHE_DIR / f"npm_time_{package}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    proc = subprocess.run(["npm", "view", package, "time", "--json"], capture_output=True,
                          text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"npm view {package} time failed: {proc.stderr[-400:]}")
    data = json.loads(proc.stdout)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=0), encoding="utf-8")
    return data


def iso_date(value: Optional[str]) -> Optional[str]:
    """Normalize git/GitHub/npm timestamps to 'YYYY-MM-DDTHH:MM:SSZ'-like UTC strings."""
    if not value:
        return None
    from datetime import datetime, timezone
    v = value.strip().replace(" ", "T", 1)
    v = re.sub(r"\s+", "", v)
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    m = re.match(r"(.*T\d\d:\d\d:\d\d(?:\.\d+)?)([+-]\d\d):?(\d\d)$", v)
    if m:
        v = f"{m.group(1)}{m.group(2)}:{m.group(3)}"
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def none_mapping(fix_ref: str, reason: str, fix_date: Optional[str] = None,
                 shas: Tuple[str, ...] = ()) -> VersionMapping:
    """Mapping used when no release window can be determined."""
    return VersionMapping(fix_ref=fix_ref, fix_shas=shas, fix_date=fix_date, pre_version=None,
                          post_version=None, pre_date=None, post_date=None,
                          mapping_confidence="none", mapping_method=reason,
                          builds_obtainable=False, build_notes=reason)


def compare_status(repo_slug: str, base: str, head: str) -> Optional[str]:
    """GitHub compare API status of base...head (ahead/behind/identical/diverged)."""
    from urllib.parse import quote
    from httpcache import get_json
    url = f"https://api.github.com/repos/{repo_slug}/compare/{quote(base, safe='')}...{head}"
    data = get_json(url)
    return data.get("status") if isinstance(data, dict) else None


def contains_by_compare(status: Optional[str]) -> Optional[bool]:
    """Map a compare status (base=tag, head=fix) to 'tag contains the fix'."""
    if status in ("behind", "identical"):
        return True
    if status in ("ahead", "diverged"):
        return False
    return None


def first_line(text: str) -> str:
    return next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")


def dedupe(items: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(i for i in items if i))
