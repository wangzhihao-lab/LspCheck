"""Cached HTTP GET for the GitHub REST API, the npm registry and the Go proxy.

* Responses are cached on disk (temp/lsp_bench/cache/http/<sha1>.json), so a
  rerun makes no network calls for URLs already fetched.
* GitHub requests carry the token from ``os.environ["GITHUB_TOKEN"]`` only;
  the token is never logged, printed, cached or written anywhere (the cache
  key is the URL, and only the response body and status are stored).
* Transient TLS/network errors and 5xx are retried with backoff; when the
  GitHub rate-limit budget drops below ``MIN_REMAINING`` the client sleeps
  until the reset time.

Run line: imported by versions_*.py, not run directly.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from paths import HTTP_CACHE_DIR

logger = logging.getLogger(__name__)

MIN_REMAINING = 200
MAX_TRIES = 6
_DELAY_S = 0.15
STATS: Dict[str, int] = {"github_calls": 0, "other_calls": 0, "cache_hits": 0, "rate_sleeps": 0}


def _cache_file(url: str) -> Path:
    return HTTP_CACHE_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".json")


def _github_headers() -> Dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set in the environment")
    return {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "lsp-bench-candidate-miner",
    }


def _respect_rate_limit(headers: Any) -> None:
    remaining = headers.get("X-RateLimit-Remaining")
    reset = headers.get("X-RateLimit-Reset")
    if remaining is None or reset is None:
        return
    if int(remaining) < MIN_REMAINING:
        wait = max(5, int(reset) - int(time.time()) + 5)
        logger.warning("GitHub budget %s left; sleeping %ss until reset", remaining, wait)
        STATS["rate_sleeps"] += 1
        time.sleep(wait)


def fetch(url: str, use_cache: bool = True) -> Tuple[int, Optional[str]]:
    """GET ``url``; return (status, body text). 404/422 are cached as misses."""
    path = _cache_file(url)
    if use_cache and path.exists():
        STATS["cache_hits"] += 1
        d = json.loads(path.read_text(encoding="utf-8"))
        return int(d["status"]), d.get("body")
    is_github = url.startswith("https://api.github.com/")
    headers = _github_headers() if is_github else {"User-Agent": "lsp-bench-candidate-miner"}
    backoff = 2.0
    for attempt in range(1, MAX_TRIES + 1):
        time.sleep(_DELAY_S)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                status = resp.status
                if is_github:
                    STATS["github_calls"] += 1
                    _respect_rate_limit(resp.headers)
                else:
                    STATS["other_calls"] += 1
        except urllib.error.HTTPError as exc:
            status = exc.code
            if is_github:
                STATS["github_calls"] += 1
            if status in (404, 410, 422):
                body = None
            elif status in (403, 429) and is_github:
                _respect_rate_limit(exc.headers)
                reset = exc.headers.get("Retry-After")
                time.sleep(float(reset) if reset else backoff)
                backoff = min(backoff * 2, 120)
                continue
            elif status >= 500:
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
                continue
            else:
                raise RuntimeError(f"HTTP {status} for {url}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            logger.info("network error (attempt %d) for %s: %s", attempt, url, type(exc).__name__)
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"url": url, "status": status, "body": body}), encoding="utf-8")
        return status, body
    raise RuntimeError(f"giving up on {url} after {MAX_TRIES} attempts")


def get_json(url: str, use_cache: bool = True) -> Optional[Any]:
    """GET and parse JSON; None for a cached/actual 404-like miss."""
    status, body = fetch(url, use_cache=use_cache)
    if body is None or status >= 400:
        return None
    return json.loads(body)


def get_text(url: str, use_cache: bool = True) -> Optional[str]:
    """GET a text resource; None for a miss."""
    status, body = fetch(url, use_cache=use_cache)
    return None if status >= 400 else body
