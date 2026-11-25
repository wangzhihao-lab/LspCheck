"""Known-issue search for triage groups (plan/tool_design_v1.md section 11.2).

For each group, a few GitHub issue searches in the server's tracker (search API, read-only):
the server's own error message for the failing request when there is one (the most specific
symptom: crash reports quote it), the case family's words in issue titles (H1 "undo", T4 "CRLF"),
the method words with the symptom words of the shape, then with the case family's words, then
the method with the oracle's generic word (phrases quoted).
Matches are merged (first query first, duplicates
dropped) and listed in the report for the author; nothing is filed or posted. The token is read
only from os.environ["GITHUB_TOKEN"] (unauthenticated search when it is absent) and is never
printed, logged or written; responses are cached, trimmed to the fields the report shows, under
temp/triage_cache/github/ (one file per request URL), and uncached requests are spaced to stay
under the search rate limit.

Run line: imported by triage.py and tests/test_triage.py; not run directly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE_DIR = os.path.join(REPO, "temp", "triage_cache", "github")
API = "https://api.github.com/search/issues"
logger = logging.getLogger(__name__)

TRACKERS: Dict[str, Tuple[str, ...]] = {
    "pyright": ("microsoft/pyright",), "ts7": ("microsoft/typescript-go",),
    "ts6": ("typescript-language-server/typescript-language-server", "microsoft/TypeScript"),
    "rust-analyzer": ("rust-lang/rust-analyzer",), "gopls": ("golang/go",), "jdtls": ("eclipse-jdtls/eclipse.jdt.ls",),
}
QUALIFIERS: Dict[str, str] = {"golang/go": "label:gopls"}
METHOD_WORDS: Dict[str, str] = {
    "hover": "hover", "definition": "definition", "typeDefinition": "type definition", "references": "references",
    "documentHighlight": "highlight", "completion": "completion", "signatureHelp": "signature help",
    "codeAction": "code action", "documentSymbol": "document symbol", "semanticTokens": "semantic tokens",
    "inlayHint": "inlay hint", "foldingRange": "folding range", "diagnostics": "diagnostics",
    "codeActionResolve": "code action resolve", "completionResolve": "completion resolve",
    "semanticTokensDelta": "semantic tokens delta", "semanticTokensRange": "semantic tokens range",
    "highlightVsReferences": "highlight", "definitionConsistency": "definition", "formatting": "formatting",
    "organizeImports": "organize imports", "initialize": "crash", "session": "crash",
}
FAMILY_WORDS: Dict[str, str] = {
    "H1": "undo", "H2": "while typing", "H3": "reopen", "H4": "configuration change", "H5": "rename file",
    "H6": "file changed", "H7": "after edit", "H8": "order", "T1": "blank lines", "T2": "comment",
    "T3": "trailing whitespace", "T4": "CRLF", "T5": "newline end of file", "T6": "unicode",
    "tokens": "delta", "a": "pull diagnostics", "b": "range", "c": "references", "d": "go to definition",
    "quickfix": "quick fix", "format": "format", "organize": "organize imports", "r1-suspect": "stale",
    "fresh-pair": "exception",
}
ORACLE_WORDS: Dict[str, str] = {"r0_crash": "exception", "r1_history": "stale", "r2_handles": "stale",
                                "r3_routes": "inconsistent", "r4_edits": "wrong edit", "r5_transforms": "whitespace",
                                "r6_crossimpl": "TypeScript 6"}


def symptom_words(shape: str) -> str:
    """Words for the difference shape: error kind, or what happened to the answer."""
    tail = shape.split(":", 1)[1] if ":" in shape else shape
    if "error:-32603" in tail:
        return "internal error"
    if "error:timeout" in tail:
        return "hang"
    if "error:dead" in tail or "error:transport" in tail:
        return "crash"
    if "->error" in tail:
        return "error"
    first = tail.split(":")[0]
    return {"lost": "missing", "gained": "unexpected", "text": "wrong", "missing": "missing", "extra": "extra",
            "moved": "wrong range", "message": "message", "key-lost": "missing"}.get(first, "wrong")


def quoted(phrase: str) -> str:
    """A multi-word phrase in quotes (GitHub then matches it as a phrase)."""
    phrase = phrase.strip()
    return f'"{phrase}"' if " " in phrase else phrase


def error_phrase(message: str, words: int = 8) -> str:
    """The distinctive part of a server error message: the text after a "failed with message:"
    prefix, punctuation dropped (GitHub phrase search ignores it), at most `words` words."""
    text = re.split(r"failed with message:\s*", message, maxsplit=1)[-1]
    text = re.split(r"\n|\s+at\s+\S+\s+\(", text)[0]  # a stack trace starts at the first frame
    return " ".join(re.sub(r"[^\w\s.-]", " ", text).split()[:words])


def build_queries(server_kind: str, oracle: str, method: str, shape: str, family: str,
                  phrase: str = "") -> List[Tuple[str, str]]:
    """(repository, query) pairs, most specific first (the server's error message when there is
    one); empty when the server has no tracker here."""
    base = method.split(".")[0]
    mw = quoted(METHOD_WORDS.get(base, base))
    fam = FAMILY_WORDS.get(family.split(":")[0], "")
    terms = [f'"{phrase}"' if phrase else "", f"{quoted(fam)} in:title" if fam else "",
             f"{mw} {quoted(symptom_words(shape))}", f"{mw} {quoted(fam)}" if fam else "",
             f"{mw} {quoted(ORACLE_WORDS.get(oracle, ''))}"]
    out = []
    for repo in TRACKERS.get(server_kind, ()):
        for t in dict.fromkeys(x.strip() for x in terms if x.strip()):
            out.append((repo, f"{t} repo:{repo} is:issue {QUALIFIERS.get(repo, '')}".strip()))
    return out


@dataclass(frozen=True)
class Match:
    repo: str
    number: int
    title: str
    url: str
    state: str
    created: str
    comments: int
    query: str


def trim(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"number": i.get("number"), "title": i.get("title", ""), "html_url": i.get("html_url", ""),
             "state": i.get("state", ""), "created_at": str(i.get("created_at", ""))[:10],
             "comments": i.get("comments", 0), "pull_request": "pull_request" in i} for i in items]


def merge(results: Sequence[Tuple[str, str, List[Dict[str, Any]]]], limit: int = 8) -> List[Match]:
    """Matches in query order, pull requests and duplicates dropped, at most `limit`."""
    out: Dict[str, Match] = {}
    for repo, query, items in results:
        for i in items:
            if i.get("pull_request") or not i.get("html_url") or i["html_url"] in out:
                continue
            out[i["html_url"]] = Match(repo, int(i.get("number") or 0), str(i.get("title", "")), i["html_url"],
                                       str(i.get("state", "")), str(i.get("created_at", "")), int(i.get("comments") or 0),
                                       query)
    return list(out.values())[:limit]


class GitHubSearch:
    """Cached GitHub issue search; call(repo, query) -> (trimmed items, note)."""

    def __init__(self, cache_dir: str = CACHE_DIR, per_page: int = 5, min_interval_s: float = 2.2,
                 opener: Optional[Callable[[urllib.request.Request, float], Any]] = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.cache_dir, self.per_page, self.min_interval_s = cache_dir, per_page, min_interval_s
        self.opener = opener or (lambda req, timeout: urllib.request.urlopen(req, timeout=timeout))
        self.sleep, self._last, self.requests = sleep, 0.0, 0

    def url(self, query: str) -> str:
        return f"{API}?{urllib.parse.urlencode({'q': query, 'per_page': self.per_page})}"

    def cache_path(self, url: str) -> str:
        return os.path.join(self.cache_dir, hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")

    def __call__(self, repo: str, query: str) -> Tuple[List[Dict[str, Any]], str]:
        url = self.url(query)
        path = self.cache_path(url)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)["items"], ""
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "lsptest-triage",
                   "X-GitHub-Api-Version": "2022-11-28"}
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        for attempt in (1, 2):
            wait = self.min_interval_s - (time.monotonic() - self._last)
            if wait > 0:
                self.sleep(wait)
            self._last, self.requests = time.monotonic(), self.requests + 1
            try:
                with self.opener(urllib.request.Request(url, headers=headers), 30.0) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                reset = exc.headers.get("X-RateLimit-Reset") if exc.headers else None
                if exc.code in (403, 429) and attempt == 1 and reset and float(reset) - time.time() < 90:
                    self.sleep(max(1.0, float(reset) - time.time() + 1))
                    continue
                logger.warning("issue search failed with HTTP %s: %s", exc.code, query)
                return [], f"search failed ({exc.code}) for: {query}"
            except (urllib.error.URLError, OSError, ValueError) as exc:
                logger.warning("issue search failed (%s): %s", type(exc).__name__, query)
                return [], f"search failed ({type(exc).__name__}) for: {query}"
        else:
            return [], f"search rate-limited for: {query}"
        items = trim(body.get("items") or [])
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"url": url, "fetched": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "total_count": body.get("total_count"), "items": items}, f, indent=1)
        return items, ""


def search_group(server_kind: str, oracle: str, method: str, shape: str, family: str,
                 fetch: Callable[[str, str], Tuple[List[Dict[str, Any]], str]], limit: int = 8,
                 phrase: str = "") -> Dict[str, Any]:
    """Queries, merged matches and notes for one group (JSON-ready)."""
    queries = build_queries(server_kind, oracle, method, shape, family, phrase)
    results, notes = [], []
    for repo, q in queries:
        items, note = fetch(repo, q)
        results.append((repo, q, items))
        notes += [note] if note else []
    if not queries:
        notes.append(f"no issue tracker configured for {server_kind}")
    return {"queries": [q for _, q in queries], "matches": [asdict(m) for m in merge(results, limit)], "notes": notes,
            "authenticated": bool(os.environ.get("GITHUB_TOKEN"))}


__all__ = ["CACHE_DIR", "FAMILY_WORDS", "GitHubSearch", "METHOD_WORDS", "Match", "TRACKERS", "build_queries",
           "error_phrase", "merge", "quoted", "search_group", "symptom_words", "trim"]
