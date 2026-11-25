"""Upstream sources of benchmark cases: GitHub issue text (body and comments) and raw
files of a linked repository at a pinned commit.

Responses are cached in the candidate miner's HTTP cache (temp/lsp_bench/cache/http/
<sha1 of the URL>.json holding {"url", "status", "body"}), so the mining step and the
benchmark share one cache and a rerun makes no network call. GitHub API calls carry the
token from os.environ["GITHUB_TOKEN"] only; it is never logged, printed or cached.
`dump_issue` writes the issue text to temp/lsp_bench/issues/<server>-<number>.md for
reading while a case is written. `verbatim_in` checks that a project file copied "from
the issue" really appears there (non-blank lines, stripped, in order).

Run line: python3 scripts/lsptest/bench/sources.py <server> <number> [<server> <number> ...]
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
HTTP_CACHE = os.path.join(REPO, "temp", "lsp_bench", "cache", "http")
ISSUE_DUMPS = os.path.join(REPO, "temp", "lsp_bench", "issues")
ISSUE_REPOS: Dict[str, str] = {"pyright": "microsoft/pyright", "tsserver": "microsoft/TypeScript",
                               "rust-analyzer": "rust-lang/rust-analyzer", "gopls": "golang/go",
                               "jdtls": "eclipse-jdtls/eclipse.jdt.ls"}
USER_AGENT = "lsp-bench-case-builder"
MAX_TRIES = 4

logger = logging.getLogger(__name__)


class SourceError(RuntimeError):
    """An upstream source could not be fetched."""


def cache_path(url: str) -> str:
    return os.path.join(HTTP_CACHE, hashlib.sha1(url.encode("utf-8")).hexdigest() + ".json")


def cached_get(url: str, offline: bool = False) -> Tuple[int, Optional[str]]:
    """(status, body) of a GET, from the cache when present; 404/410/422 are cached misses."""
    path = cache_path(url)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return int(d["status"]), d.get("body")
    if offline:
        raise SourceError(f"not cached (offline): {url}")
    headers = {"User-Agent": USER_AGENT}
    if url.startswith("https://api.github.com/"):
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SourceError("GITHUB_TOKEN is not set in the environment")
        headers.update({"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28"})
    status, body = 0, None
    for attempt in range(1, MAX_TRIES + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as resp:
                status, body = resp.status, resp.read().decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as exc:
            status, body = exc.code, None
            if exc.code in (404, 410, 422):
                break
            logger.info("HTTP %s for %s (attempt %d)", exc.code, url, attempt)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            logger.info("network error %s for %s (attempt %d)", type(exc).__name__, url, attempt)
        time.sleep(2.0 * attempt)
    else:
        raise SourceError(f"giving up on {url} after {MAX_TRIES} attempts (last status {status})")
    os.makedirs(HTTP_CACHE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"url": url, "status": status, "body": body}, f)
    return status, body


def get_json(url: str, offline: bool = False) -> Any:
    status, body = cached_get(url, offline)
    return None if body is None or status >= 400 else json.loads(body)


def issue(server: str, number: int, offline: bool = False) -> Dict[str, Any]:
    """The issue object (title, body, user, created_at, ...) from the REST API."""
    d = get_json(f"https://api.github.com/repos/{ISSUE_REPOS[server]}/issues/{number}", offline)
    if not isinstance(d, dict):
        raise SourceError(f"issue {server}#{number} not found")
    return d


def comments(server: str, number: int, offline: bool = False) -> List[Dict[str, Any]]:
    """All comments of an issue (pages of 100, in order)."""
    out: List[Dict[str, Any]] = []
    for page in range(1, 20):
        suffix = "?per_page=100" if page == 1 else f"?per_page=100&page={page}"
        rows = get_json(f"https://api.github.com/repos/{ISSUE_REPOS[server]}/issues/{number}/comments{suffix}", offline)
        if not isinstance(rows, list) or not rows:
            break
        out.extend(r for r in rows if isinstance(r, dict))
        if len(rows) < 100:
            break
    return out


def issue_text(server: str, number: int, offline: bool = False) -> str:
    """Title, body and every comment as one markdown text (the provenance source)."""
    d = issue(server, number, offline)
    parts = [f"# {d.get('title', '')}", f"reported by {(d.get('user') or {}).get('login', '?')} on {d.get('created_at')}",
             str(d.get("body") or "")]
    for c in comments(server, number, offline):
        parts.append(f"--- comment by {(c.get('user') or {}).get('login', '?')} on {c.get('created_at')}")
        parts.append(str(c.get("body") or ""))
    return "\n\n".join(parts).replace("\r\n", "\n")


def raw_file(repo: str, sha: str, path: str, offline: bool = False) -> str:
    """A file of a GitHub repository at a pinned commit (raw.githubusercontent.com)."""
    status, body = cached_get(f"https://raw.githubusercontent.com/{repo}/{sha}/{path}", offline)
    if body is None or status >= 400:
        raise SourceError(f"{repo}@{sha}:{path} not found (status {status})")
    return body


def _lines(text: str) -> List[str]:
    return [ln.strip() for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]


def verbatim_in(content: str, source: str) -> Tuple[bool, str]:
    """(ok, first missing line): every non-blank line of `content`, stripped, occurs in `source`
    in the same order (a file assembled from several code blocks of one issue passes)."""
    src, pos = _lines(source), 0
    for line in _lines(content):
        while pos < len(src) and src[pos] != line:
            pos += 1
        if pos >= len(src):
            return False, line
        pos += 1
    return True, ""


def dump_issue(server: str, number: int) -> str:
    os.makedirs(ISSUE_DUMPS, exist_ok=True)
    path = os.path.join(ISSUE_DUMPS, f"{server}-{number}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(issue_text(server, number))
    return path


def main(argv: Sequence[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if len(argv) < 2 or len(argv) % 2:
        logger.error("usage: sources.py <server> <number> [<server> <number> ...]")
        return 2
    for server, number in zip(argv[0::2], argv[1::2]):
        logger.info("%s", dump_issue(server, int(number)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


__all__ = ["ISSUE_REPOS", "SourceError", "cached_get", "comments", "dump_issue", "get_json", "issue", "issue_text",
           "raw_file", "verbatim_in"]
