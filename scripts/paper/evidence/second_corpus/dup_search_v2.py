"""Read-only search of the upstream trackers for the second-corpus root causes C12-C35.

What it does: per cause a short fixed list of queries against the GitHub issue search API (issues only) in
the server's tracker: golang/go with label:gopls, microsoft/pyright, rust-lang/rust-analyzer, and for the TS6
causes typescript-language-server and microsoft/TypeScript. Results are merged per cause with number, title,
state, state reason, dates, comment count and a body excerpt. Nothing is posted anywhere.

By default it runs offline: every query is answered from the response cache temp/triage_cache/github/v2-*
(one file per request URL, trimmed to the fields above), a query without a cache file is logged as
"not cached" and gets no results, and the recorded date is the date of the newest cache file used (the
search date). With --online an uncached query is sent to api.github.com and cached; the token is read only
from os.environ["GITHUB_TOKEN"] and sent only in the Authorization header, never printed, logged or
written; uncached requests are spaced to stay under the search rate limit. --show owner/repo#N ... (needs
--online, never cached) appends the full bodies of the named issues to dup_search_v2_details.log.

Reads: temp/triage_cache/github/v2-*.json. Writes: data/lsptest/runs/main_v2/evidence/checks/dup_search_v2.json,
dup_search_v2.log (the queries and candidates as text) and dup_search_v2_run.log (this script's log).

Run line (offline, from the cache; through the shared core ledger, 2 cores):
python3 scripts/paper/evidence/second_corpus/dup_search_v2.py
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from group_states import OUT, REPO, scrub, setup_logging  # noqa: E402

CACHE = os.path.join(REPO, "temp", "triage_cache", "github")
API = "https://api.github.com/search/issues"
PER_QUERY = 6
PAUSE_S = 2.3
EXCERPT = 500
GOPLS = "repo:golang/go label:gopls"
PYR = "repo:microsoft/pyright"
RA = "repo:rust-lang/rust-analyzer"
TSLS = "repo:typescript-language-server/typescript-language-server"
TS = "repo:microsoft/TypeScript"
logger = logging.getLogger("dup_search_v2")

QUERIES: Dict[str, List[str]] = {
    "C12": [f"{GOPLS} duplicate code actions", f"{GOPLS} duplicate quick fix", f"{GOPLS} code action twice configuration",
            f"{GOPLS} didChangeConfiguration duplicate diagnostics", f"{GOPLS} \"Replace interface{{}} by any\" duplicate"],
    "C13": [f"{GOPLS} \"missing go.sum entry\" nested module", f"{GOPLS} \"missing go.sum entry\" stale",
            f"{GOPLS} \"error while importing\" diagnostic disappears", f"{GOPLS} nested module replace directive diagnostics stale",
            f"{GOPLS} go.sum diagnostic after file rename"],
    "C14": [f"{GOPLS} completion empty after go.mod", f"{GOPLS} go.mod invalid completion broken",
            f"{GOPLS} no completions after go.mod fixed", f"{GOPLS} completion empty test file rename"],
    "C15": [f"{GOPLS} unused variable quick fix unused import", f"{GOPLS} \"imported and not used\" after quick fix",
            f"{GOPLS} unusedvariable package level var import", f"{GOPLS} delete unused var leaves import"],
    "C16": [f"{GOPLS} CRLF semantic tokens", f"{GOPLS} CRLF folding range", f"{GOPLS} carriage return comment position",
            f"{GOPLS} raw string CRLF", f"{GOPLS} \\r block comment range"],
    "C17": [f"{PYR} \"Did not find evaluation scope\"", f"{PYR} \"Debug Failure\" references",
            f"{PYR} find all references internal error", f"{PYR} \"evaluation scope\""],
    "C18": [f"{PYR} hover type depends on order", f"{PYR} inferred return type different after edit",
            f"{PYR} call-site return type inference inconsistent", f"{PYR} Unknown vs inferred type nondeterministic"],
    "C19": [f"{PYR} hover docstring missing after rename", f"{PYR} docstring missing hover stdlib",
            f"{PYR} hover documentation lost file rename", f"{PYR} rename file docstring"],
    "C20": [f"{PYR} references string annotation", f"{PYR} find references quoted type annotation",
            f"{PYR} references forward reference string", f"{PYR} references cast string type"],
    "C21": [f"{PYR} signature help return type Unknown", f"{PYR} inferred return type Unknown after opening file",
            f"{PYR} return type Unknown circular import", f"{PYR} hover return type depends on open files"],
    "C22": [f"{PYR} auto import __future__", f"{PYR} \"from __future__ import\" completion",
            f"{PYR} auto import private name typeshed", f"{PYR} _VersionInfo"],
    "C23": [f"{RA} find references hang", f"{RA} references timeout", f"{RA} find all references slow regression",
            f"{RA} references never returns"],
    "C24": [f"{RA} semantic tokens hang", f"{RA} semanticTokens full timeout", f"{RA} semantic highlighting slow regression",
            f"{RA} semantic tokens never returns"],
    "C25": [f"{RA} publishDiagnostics not sent", f"{RA} push diagnostics missing", f"{RA} diagnostics not published until edit",
            f"{RA} inactive code diagnostics not shown", f"{RA} native diagnostics not published after load"],
    "C26": [f"{RA} semantic tokens range unsafe", f"{RA} semanticTokens range different from full",
            f"{RA} range highlighting missing modifiers", f"{RA} semantic tokens range proc macro attribute",
            f"{RA} unresolvedReference semantic tokens range"],
    "C27": [f"{RA} completion macro call enum variant", f"{RA} completion before parenthesis macro",
            f"{RA} completion replaces macro name", f"{RA} completion \"!(\""],
    "C28": [f"{RA} attribute completion parentheses duplicated", f"{RA} derive completion existing arguments",
            f"{RA} attribute completion inserts parentheses", f"{RA} completion derive(Debug) twice"],
    "C29": [f"{RA} to_owned quick fix shorthand", f"{RA} \"to_owned\" struct field shorthand",
            f"{RA} add reference quick fix shorthand field", f"{RA} type mismatch fix struct shorthand"],
    "C30": [f"{TSLS} code actions file open order", f"{TS} tsserver code fix depends on open order",
            f"{TS} \"node:test\" import describe", f"{TS} inferred project test file auto import order"],
    "C31": [f"{TSLS} inlay hint any after rename", f"{TS} tsserver inlay hints any after file rename",
            f"{TS} tsserver rename file circular import any", f"{TS} type becomes any after renaming file"],
    "C32": [f"{TS} \"Convert to async function\" Bluebird", f"{TS} convert to async function return type Promise",
            f"{TS} convertToAsyncFunction TS1064", f"{TS} convert to async non-global Promise"],
    "C33": [f"{TS} spelling suggestion JSX eval", f"{TS} \"Did you mean 'eval'\" JSX",
            f"{TS} fix spelling JSX intrinsic element", f"{TS} spelling code fix lowercase JSX tag"],
    "C34": [f"{TS} \"Change spelling\" JSX closing tag", f"{TS} spelling fix JSX closing tag not renamed",
            f"{TS} code fix JSX opening tag only", f"{TS} fixSpelling JSX closing"],
    "C35": [f"{TS} spelling suggestion variable being declared", f"{TS} \"Did you mean\" used before its declaration",
            f"{TS} spelling suggestion block-scoped variable initializer", f"{TS} fixSpelling self reference initializer"],
}

# Second, narrower round for causes whose first round returned nothing close (added after reading it).
EXTRA: Dict[str, List[str]] = {
    "C12": [f"{GOPLS} code actions duplicated", f"{GOPLS} same quick fix offered twice", f"{GOPLS} staticcheck duplicate fixes"],
    "C17": [f"{PYR} \"Debug Failure\"", f"{PYR} references internal error 32603", f"{PYR} \"evaluation scope\" assert"],
    "C29": [f"{RA} to_owned", f"{RA} shorthand field quick fix", f"{RA} \"Add .to_owned()\""],
    "C33": [f"{TS} spelling JSX", f"{TS} \"Did you mean\" JSX component", f"{TS} codefix spelling JSX element"],
    "C34": [f"{TS} JSX closing tag code fix", f"{TS} rename JSX opening tag only"],
    "C35": [f"{TS} spelling suggestion own declaration", f"{TS} \"used before its declaration\" code fix"],
}
for _c, _q in EXTRA.items():
    QUERIES[_c] = QUERIES[_c] + _q


def _headers() -> Dict[str, str]:
    """Request headers; the token, when set, goes only into Authorization."""
    h = {"Accept": "application/vnd.github+json", "User-Agent": "lsp-evidence-dup-search",
         "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def slim(item: Dict[str, Any]) -> Dict[str, Any]:
    """The fields the report shows, from one search API item."""
    body = " ".join((item.get("body") or "").split())
    return {"repo": item.get("repository_url", "").rsplit("/repos/", 1)[-1], "number": item.get("number"),
            "title": item.get("title") or "", "state": item.get("state"), "state_reason": item.get("state_reason"),
            "created": (item.get("created_at") or "")[:10], "closed": (item.get("closed_at") or "")[:10],
            "comments": item.get("comments"), "url": item.get("html_url"), "body": body[:EXCERPT],
            "is_pr": "pull_request" in item}


def cache_path(q: str) -> Tuple[str, str]:
    """(request URL, cache file) of one query."""
    url = f"{API}?{urllib.parse.urlencode({'q': q + ' is:issue', 'per_page': PER_QUERY})}"
    return url, os.path.join(CACHE, "v2-" + hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")


def fetch(url: str, path: str, q: str) -> Tuple[List[Dict[str, Any]], int, str]:
    """Send one search request (online mode only) and cache the trimmed answer."""
    err = ""
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=_headers()), timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            items = [slim(i) for i in data.get("items", [])]
            os.makedirs(CACHE, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"query": q, "total": int(data.get("total_count", 0)), "items": items}, f, ensure_ascii=False)
            time.sleep(PAUSE_S)
            return items, int(data.get("total_count", 0)), ""
        except urllib.error.HTTPError as exc:
            err = f"HTTP {exc.code}"
            if exc.code not in (403, 429, 500, 502, 503):
                break
            reset = exc.headers.get("X-RateLimit-Reset") if exc.code in (403, 429) else None
            wait = min(65.0, max(5.0, float(reset) - time.time() + 1)) if reset else 10.0 * (attempt + 1)
            logger.warning("%s; waiting %.0fs", err, wait)
            time.sleep(wait)
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            err = type(exc).__name__
            time.sleep(5.0 * (attempt + 1))
    return [], 0, err


def search(q: str, online: bool, used: List[str]) -> Tuple[List[Dict[str, Any]], int, str]:
    """(items, total, error) for one query: from the cache, else fetched (online) or 'not cached' (offline).

    Args:
        q: query without the is:issue qualifier.
        online: allow a network request for an uncached query.
        used: collects the cache files read.
    """
    url, path = cache_path(q)
    if os.path.exists(path):
        used.append(path)
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
        return c["items"], c["total"], ""
    if not online:
        logger.warning("not cached: %s", q)
        return [], 0, "not cached"
    return fetch(url, path, q)


def run_all(causes: Optional[List[str]], online: bool) -> Dict[str, Any]:
    """Run the queries of the named causes (all when None) and merge the candidates per cause."""
    used: List[str] = []
    out: Dict[str, Any] = {"date": time.strftime("%Y-%m-%d"), "authenticated": bool(os.environ.get("GITHUB_TOKEN")),
                           "per_query": PER_QUERY, "causes": {}}
    for cause, queries in QUERIES.items():
        if causes and cause not in causes:
            continue
        merged: Dict[str, Dict[str, Any]] = {}
        qlog = []
        for q in queries:
            items, total, err = search(q, online, used)
            qlog.append({"query": q + " is:issue", "total": total, "error": err,
                         "hits": [f"{i['repo']}#{i['number']}" for i in items]})
            for i in items:
                if i["is_pr"]:
                    continue
                merged.setdefault(f"{i['repo']}#{i['number']}", dict(i, queries=[]))["queries"].append(q)
        out["causes"][cause] = {"queries": qlog, "candidates": list(merged.values())}
        logger.info("%s: %d queries, %d issues", cause, len(queries), len(merged))
    if not online and used:
        out["date"] = time.strftime("%Y-%m-%d", time.localtime(max(os.path.getmtime(p) for p in used)))
    logger.info("%d queries answered from the cache, mode %s", len(used), "online" if online else "offline")
    return out


def render(res: Dict[str, Any]) -> str:
    """Text report: per cause the queries with totals and the merged candidates."""
    lines = [f"search date {res['date']}; authenticated {res['authenticated']}; top {res['per_query']} per query"]
    for cause, c in res["causes"].items():
        lines += ["", f"== {cause}"]
        lines += [f"  query: {q['query']} -> total {q['total']}{' ERROR ' + q['error'] if q['error'] else ''}"
                  for q in c["queries"]]
        for s in c["candidates"]:
            lines.append(f"  - {s['repo']}#{s['number']} [{s['state']}/{s['state_reason']}] {s['created']} closed "
                         f"{s['closed'] or '-'} ({s['comments']} comments, hits {len(s['queries'])}) {s['title']}")
            lines.append(f"      {s['body'][:300]}")
    return "\n".join(lines) + "\n"


def show(refs: List[str], chars: int = 2500) -> str:
    """Full bodies of the named issues (online only; not cached)."""
    out = []
    for ref in refs:
        repo, _, num = ref.partition("#")
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/{num}",
                                                               headers=_headers()), timeout=30) as r:
                it = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            out.append(f"== {ref}: not fetched ({type(exc).__name__})")
            continue
        body = " ".join((it.get("body") or "").split())
        out.append(f"== {ref} [{it.get('state')}/{it.get('state_reason')}] created {(it.get('created_at') or '')[:10]} "
                   f"closed {(it.get('closed_at') or '')[:10]} comments {it.get('comments')}\n{it.get('title')}\n{body[:chars]}")
        time.sleep(1.0)
    return "\n\n".join(out) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    """Run the search (offline by default) and write the JSON and text reports.

    Args:
        argv: command-line arguments; defaults to sys.argv[1:].

    Returns:
        Process exit code (0; 2 when --show is given without --online).
    """
    ap = argparse.ArgumentParser(description="Read-only upstream search for C12-C35.")
    ap.add_argument("--causes", nargs="*", default=None)
    ap.add_argument("--show", nargs="*", default=None)
    ap.add_argument("--online", action="store_true", help="send uncached queries to api.github.com")
    args = ap.parse_args(argv)
    setup_logging("dup_search_v2_run")
    if args.show:
        if not args.online:
            logger.error("--show fetches issue bodies and needs --online")
            return 2
        with open(os.path.join(OUT, "dup_search_v2_details.log"), "a", encoding="utf-8") as f:
            f.write(show(args.show))
        return 0
    res = run_all(args.causes, args.online)
    path = os.path.join(OUT, "dup_search_v2.json")
    if args.causes and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
        old["causes"].update(res["causes"])
        res = old
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "dup_search_v2.log"), "w", encoding="utf-8") as f:
        f.write(render(res))
    logger.info("written to %s", scrub(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
