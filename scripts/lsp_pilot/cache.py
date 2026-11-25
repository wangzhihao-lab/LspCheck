"""Raw-response disk cache. Makes the pipeline idempotent and re-runnable:
identical inputs replay from disk with zero network calls.

Run: imported by fetch_pipeline.py / run_pilot.py, not run directly.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Simple counters so the final report can state how much of a rerun came
# from cache vs. network.
stats = {"hits": 0, "misses": 0}


def reset_stats() -> None:
    stats["hits"] = 0
    stats["misses"] = 0


def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache file %s is unreadable (%s); treating as miss", path, exc)
        return None


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=None)
    tmp_path.replace(path)


def cached_call(
    cache_path: Path,
    fetch_fn: Callable[[], Any],
    cache_only: bool = False,
) -> tuple[Any, bool]:
    """Return (data, from_cache). Loads cache_path if present; otherwise
    calls fetch_fn(), persists the result, and returns it.

    If cache_only is True and the cache is missing, raises RuntimeError
    instead of hitting the network (used by the idempotence validation
    pass, which must prove a rerun touches no network).
    """
    cached = load_json(cache_path)
    if cached is not None:
        stats["hits"] += 1
        return cached, True

    if cache_only:
        raise RuntimeError(
            f"cache_only=True but no cache at {cache_path}; "
            "pipeline is not idempotent for this call"
        )

    stats["misses"] += 1
    data = fetch_fn()
    save_json(cache_path, data)
    return data, False
