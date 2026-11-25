"""GitHub GraphQL client: auth from environment only, rate-limit aware,
retries with backoff on 403/429/5xx.

SECURITY: the token is read from os.environ and is never printed, logged,
written to a file, or included in any exception message. Never read shell
profile files here.

Run: imported by fetch_pipeline.py / run_pilot.py, not run directly.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

from config import GITHUB_GRAPHQL_URL, RATE_LIMIT_SLEEP_THRESHOLD, RATE_LIMIT_DEFAULT_SLEEP_S

logger = logging.getLogger(__name__)

MAX_RETRIES = 6
REQUEST_TIMEOUT_S = 30
_INTER_REQUEST_DELAY_S = 0.15


class GitHubAuthError(RuntimeError):
    """Raised when GITHUB_TOKEN is missing. Never include the token value."""


class GraphQLQueryError(RuntimeError):
    """Raised when GitHub returns a GraphQL-level error with no usable data."""


# Cumulative quota bookkeeping for the final report. No secrets in here.
quota_stats = {
    "requests_sent": 0,
    "points_used_observed": 0,
    "last_remaining": None,
    "last_limit": None,
    "rate_limit_sleeps": 0,
    "backoff_retries": 0,
}


def _get_token() -> str:
    """Read the token from the environment ONLY. Never read shell profile
    files (~/.bashrc, ~/.zshrc, etc.) or any other source."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise GitHubAuthError(
            "GITHUB_TOKEN is not set in the environment. Export it before "
            "running this pipeline, e.g.: export GITHUB_TOKEN=... "
            "(this pipeline reads os.environ only and will not look "
            "anywhere else). Stopping."
        )
    return token


def _headers() -> dict[str, str]:
    token = _get_token()
    return {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        # Kept for older Issue-timeline / closing-PR fields some tokens
        # still need a preview opt-in for; harmless if already GA.
        "Accept": "application/vnd.github.starfox-preview+json, application/json",
        "User-Agent": "lsp-pilot-data-collector",
    }


def _sleep_for_rate_limit(resp: requests.Response) -> None:
    remaining = resp.headers.get("X-RateLimit-Remaining")
    if remaining is None:
        return
    try:
        remaining_i = int(remaining)
    except ValueError:
        return
    quota_stats["last_remaining"] = remaining_i
    limit = resp.headers.get("X-RateLimit-Limit")
    if limit is not None:
        quota_stats["last_limit"] = int(limit)
    if remaining_i < RATE_LIMIT_SLEEP_THRESHOLD:
        reset = resp.headers.get("X-RateLimit-Reset")
        sleep_s = RATE_LIMIT_DEFAULT_SLEEP_S
        if reset:
            try:
                sleep_s = max(1, int(reset) - int(time.time()) + 2)
            except ValueError:
                pass
        logger.warning(
            "X-RateLimit-Remaining=%s (<%s); sleeping %ss before next request",
            remaining_i, RATE_LIMIT_SLEEP_THRESHOLD, sleep_s,
        )
        quota_stats["rate_limit_sleeps"] += 1
        time.sleep(sleep_s)


def execute(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """POST one GraphQL query. Returns the parsed 'data' dict.

    Retries with exponential backoff on 403/429/5xx. Raises GitHubAuthError
    immediately on 401 (no retry - the token is bad, retrying won't help).
    """
    backoff = 5.0
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        time.sleep(_INTER_REQUEST_DELAY_S)
        try:
            resp = requests.post(
                GITHUB_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers=_headers(),
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning("Network error (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            quota_stats["backoff_retries"] += 1
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)
            continue

        quota_stats["requests_sent"] += 1

        if resp.status_code == 401:
            raise GitHubAuthError(
                "GitHub returned 401 Unauthorized. GITHUB_TOKEN is present "
                "but was rejected (expired/invalid/insufficient scope). "
                "Stopping without retrying."
            )

        if resp.status_code == 200:
            _sleep_for_rate_limit(resp)
            try:
                payload = resp.json()
            except ValueError as exc:
                # Occasionally GitHub returns 200 with an empty/truncated
                # body (transient). Treat like a 5xx: retry with backoff
                # instead of failing the whole target.
                logger.warning(
                    "HTTP 200 but body was not valid JSON (attempt %d/%d): %s",
                    attempt, MAX_RETRIES, exc,
                )
                quota_stats["backoff_retries"] += 1
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
                continue
            errors = payload.get("errors")
            data = payload.get("data")
            rl = (data or {}).get("rateLimit")
            if rl:
                quota_stats["points_used_observed"] += rl.get("cost", 0)
                quota_stats["last_remaining"] = rl.get("remaining", quota_stats["last_remaining"])
                quota_stats["last_limit"] = rl.get("limit", quota_stats["last_limit"])
            if errors and not data:
                raise GraphQLQueryError(f"GraphQL error(s): {errors}")
            if errors:
                logger.warning("GraphQL returned partial errors: %s", errors)
            return data or {}

        if resp.status_code in (403, 429) or resp.status_code >= 500:
            retry_after = resp.headers.get("Retry-After")
            sleep_s = float(retry_after) if retry_after else backoff
            logger.warning(
                "HTTP %s from GitHub (attempt %d/%d); sleeping %.0fs",
                resp.status_code, attempt, MAX_RETRIES, sleep_s,
            )
            quota_stats["backoff_retries"] += 1
            time.sleep(sleep_s)
            backoff = min(backoff * 2, 300)
            continue

        resp.raise_for_status()

    raise RuntimeError(
        f"Exceeded {MAX_RETRIES} retries against GitHub GraphQL API"
        + (f" (last error: {last_exc})" if last_exc else "")
    )


def assert_token_present() -> None:
    """Fail fast at pipeline start, before any network calls."""
    _get_token()
