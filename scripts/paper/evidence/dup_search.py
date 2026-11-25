"""Read-only duplicate search for the candidate bugs C1-C10 on the upstream trackers.

For each cause, a fixed list of queries runs against the GitHub issue search API
(api.github.com/search/issues, issues only): typescript-language-server and microsoft/TypeScript
for C1/C2, golang/go restricted to label:gopls for C3, C5-C7 and C9, rust-lang/rust-analyzer for C4
and C8, microsoft/typescript-go for C10. Results are merged per cause (first-seen order, with the queries that found each issue)
and written with number, title, state, dates, comment count, labels and a body excerpt, so that
possible matches can be judged by reading. Nothing is posted anywhere.

The token is read only from os.environ["GITHUB_TOKEN"] and sent only in the Authorization header
of api.github.com requests; it is never printed, logged or written. Without it the search runs
unauthenticated (lower rate limit).

Writes data/lsptest/runs/main_v1/evidence/dup_search.json and dup_search.log.

--causes runs only the named causes and merges them into the existing dup_search.json (C9 and C10
were added after the author's second look at the verdicts, on the same day as the first search).

Run line: python3 scripts/paper/evidence/dup_search.py [--causes C9 C10] [--show owner/repo#N ...]
"""

from __future__ import annotations

import http.client
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
EVIDENCE = os.path.join(REPO, "data", "lsptest", "runs", "main_v1", "evidence")
API = "https://api.github.com/search/issues"
PER_QUERY = 6
PAUSE_S = 2.5
EXCERPT = 500
TSLS = "repo:typescript-language-server/typescript-language-server"
TS = "repo:microsoft/TypeScript"
GOPLS = "repo:golang/go label:gopls"
RA = "repo:rust-lang/rust-analyzer"
TSGO = "repo:microsoft/typescript-go"

QUERIES: Dict[str, List[str]] = {
    "C1": [f"{TSLS} rename file", f"{TSLS} didRenameFiles", f"{TSLS} willRenameFiles",
           f"{TSLS} renamed file stale", f"{TSLS} file moved definition",
           f"{TS} tsserver rename file back", f"{TS} tsserver \"renamed back\"",
           f"{TS} tsserver file renamed stale project references", f"{TS} tsserver rename file watcher missing"],
    "C2": [f"{TSLS} \"Cannot find name\"", f"{TSLS} spurious diagnostic", f"{TSLS} diagnostics didOpen race",
           f"{TS} tsserver \"Cannot find name\" spurious", f"{TS} tsserver \"Cannot find name\" quickinfo",
           f"{TS} tsserver \"Cannot find name\" after open", f"{TS} tsserver wrong diagnostics before project loaded"],
    "C3": [f"{GOPLS} codeAction resolve stale", f"{GOPLS} \"codeAction/resolve\"", f"{GOPLS} code action resolve edit",
           f"{GOPLS} stale code action", f"{GOPLS} split lines code action", f"{GOPLS} resolve version mismatch"],
    "C4": [f"{RA} completion resolve stale", f"{RA} \"completionItem/resolve\" range",
           f"{RA} completion resolve invalid range", f"{RA} completion resolve after edit",
           f"{RA} resolve completion outdated document", f"{RA} completion textEdit range inverted"],
    "C5": [f"{GOPLS} \"Create variable\"", f"{GOPLS} undeclared name quick fix nil",
           f"{GOPLS} undeclaredname untyped nil", f"{GOPLS} create variable \"not a type\"",
           f"{GOPLS} undeclared variable quick fix type"],
    "C6": [f"{GOPLS} \"Create function\"", f"{GOPLS} create function parameter name keyword",
           f"{GOPLS} undeclared function stub parameters", f"{GOPLS} \"missing parameter name\"",
           f"{GOPLS} create function quick fix syntax error"],
    "C7": [f"{GOPLS} \"Remove variable\"", f"{GOPLS} unusedvariable quick fix", f"{GOPLS} remove unused variable assignment",
           f"{GOPLS} \"declared and not used\" quick fix", f"{GOPLS} unused variable fix undefined"],
    "C8": [f"{RA} goto definition attribute macro multiple", f"{RA} go to definition rocket",
           f"{RA} goto definition proc macro duplicate", f"{RA} definition multiple results macro",
           f"{RA} goto definition attribute macro navigation"],
}
# Second, narrower round (added after reading the first round's results).
EXTRA: Dict[str, List[str]] = {
    "C1": [f"{TSLS} \"closed document\"", f"{TSLS} references lost after rename", f"{TSLS} didChangeWatchedFiles",
           f"{TS} \"go to definition\" stops working after renaming file", f"{TS} tsserver rename file undo",
           f"{TS} \"find all references\" after moving file", f"{TS} tsserver file renamed \"no project\""],
    "C2": [f"{TSLS} \"Cannot find\" diagnostic", f"{TS} \"Cannot find name\" disappears",
           f"{TS} tsserver spurious error hover", f"{TS} \"Cannot find name\" typeDefinition",
           f"{TS} tsserver \"Cannot find name\" race", f"{TS} \"Cannot find name 'div'\"",
           f"{TSLS} \"Cannot find name 'div'\"", f"{TS} tsserver JSX intrinsic elements error hover"],
    "C3": [f"{GOPLS} \"codeAction/resolve\" stale edit", f"{GOPLS} resolve document version",
           f"{GOPLS} code action wrong position after edit", f"{GOPLS} lazy code action resolve outdated"],
    "C4": [f"{RA} \"completionItem/resolve\" stale", f"{RA} resolve completion version",
           f"{RA} completion resolve wrong position after typing", f"{RA} completion resolve edit range"],
    "C5": [f"{GOPLS} \"Create variable\" nil", f"{GOPLS} undeclared quickfix \"untyped nil\"",
           f"{GOPLS} undeclared name composite literal quick fix", f"{GOPLS} undeclared type quick fix variable"],
    "C6": [f"{GOPLS} \"Create function\" parameter", f"{GOPLS} undeclared function parameter names",
           f"{GOPLS} \"Create function\" invalid", f"{GOPLS} \"Create function\" keyword"],
    "C7": [f"{GOPLS} unused variable quickfix undefined", f"{GOPLS} \"remove variable\" assignment",
           f"{GOPLS} unusedvariable undeclared"],
    "C8": [f"{RA} goto definition attribute rocket", f"{RA} \"goto definition\" multiple proc macro attribute",
           f"{RA} goto definition returns attribute", f"{RA} \"go to definition\" duplicate results",
           f"{RA} goto definition tokio main multiple"],
}
for _cause, _extra in EXTRA.items():
    QUERIES[_cause] = QUERIES[_cause] + _extra
# Candidate bugs added after the author's second look at the verdicts.
QUERIES["C9"] = [f"{GOPLS} references test files", f"{GOPLS} find references \"_test.go\"",
                 f"{GOPLS} references missing tests", f"{GOPLS} references across modules",
                 f"{GOPLS} references nested module", f"{GOPLS} \"find-references\" tests",
                 f"{GOPLS} references depend on open files", f"{GOPLS} references incomplete package not loaded",
                 f"{GOPLS} references replace directive module"]
QUERIES["C11"] = [f"{TS} \"Add missing properties\" undefined", f"{TS} \"Add missing properties\" quick fix type error",
                  f"{TS} add missing properties default value", f"{TS} \"Add missing properties\" Record",
                  f"{TS} fixMissingProperties undefined", f"{TS} missing properties quickfix wrong default"]
QUERIES["C10"] = [f"{TSGO} find all references missing", f"{TSGO} references incomplete",
                  f"{TSGO} references after edit", f"{TSGO} references unsaved file",
                  f"{TSGO} references syntax error", f"{TSGO} references lost",
                  f"{TSGO} find references project after change", f"{TSGO} \"find all references\" edit"]

logger = logging.getLogger("dup_search")


def _headers() -> Dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "lsp-evidence-dup-search",
         "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def search(q: str) -> Tuple[List[Dict[str, Any]], int, str]:
    """(items, total_count, error) for one query; waits out a rate limit and retries transient failures."""
    url = f"{API}?{urllib.parse.urlencode({'q': q + ' is:issue', 'per_page': PER_QUERY})}"
    err = ""
    for attempt in range(4):
        req = urllib.request.Request(url, headers=_headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data.get("items", []), int(data.get("total_count", 0)), ""
        except urllib.error.HTTPError as exc:
            err = f"HTTP {exc.code}"
            if exc.code not in (403, 429, 500, 502, 503):
                break
            reset = exc.headers.get("X-RateLimit-Reset") if exc.code in (403, 429) else None
            wait = min(65.0, max(5.0, float(reset) - time.time() + 1)) if reset else 10.0 * (attempt + 1)
            logger.warning("%s; waiting %.0fs", err, wait)
            time.sleep(wait)
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            err = f"{type(exc).__name__}"
            logger.warning("%s; retrying", err)
            time.sleep(5.0 * (attempt + 1))
    return [], 0, err


def slim(item: Dict[str, Any]) -> Dict[str, Any]:
    body = " ".join((item.get("body") or "").split())
    repo = item.get("repository_url", "").rsplit("/repos/", 1)[-1]
    return {"repo": repo, "number": item.get("number"), "title": item.get("title") or "", "state": item.get("state"),
            "state_reason": item.get("state_reason"), "created": (item.get("created_at") or "")[:10],
            "closed": (item.get("closed_at") or "")[:10], "comments": item.get("comments"),
            "labels": [lb.get("name") for lb in item.get("labels", [])], "url": item.get("html_url"),
            "body": body[:EXCERPT]}


def run_all(causes: Optional[List[str]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"date": time.strftime("%Y-%m-%d"), "authenticated": bool(os.environ.get("GITHUB_TOKEN")),
                           "per_query": PER_QUERY, "causes": {}}
    for cause, queries in QUERIES.items():
        if causes and cause not in causes:
            continue
        merged: Dict[str, Dict[str, Any]] = {}
        qlog = []
        for q in queries:
            items, total, err = search(q)
            qlog.append({"query": q + " is:issue", "total": total, "error": err,
                         "hits": [f"{slim(i)['repo']}#{i.get('number')}" for i in items]})
            for i in items:
                s = slim(i)
                key = f"{s['repo']}#{s['number']}"
                merged.setdefault(key, dict(s, queries=[]))["queries"].append(q)
            time.sleep(PAUSE_S)
        out["causes"][cause] = {"queries": qlog, "candidates": list(merged.values())}
        logger.info("%s: %d queries, %d distinct issues", cause, len(queries), len(merged))
    return out


def render(res: Dict[str, Any]) -> str:
    lines = [f"search date {res['date']}; authenticated {res['authenticated']}; top {res['per_query']} per query"]
    for cause, c in res["causes"].items():
        lines += ["", f"== {cause}"]
        lines += [f"  query: {q['query']}  -> total {q['total']}{' ERROR ' + q['error'] if q['error'] else ''}; "
                  f"top: {', '.join(q['hits']) or '-'}" for q in c["queries"]]
        for s in c["candidates"]:
            lines.append(f"  - {s['repo']}#{s['number']} [{s['state']}{'/' + s['state_reason'] if s['state_reason'] else ''}]"
                         f" {s['created']} ({s['comments']} comments, hits {len(s['queries'])}) {s['title']}")
            lines.append(f"      {s['body'][:300]}")
    return "\n".join(lines) + "\n"


def show(refs: List[str], chars: int = 2500) -> str:
    """Full title/state/body (first `chars` characters) of issues given as owner/repo#number."""
    out = []
    for ref in refs:
        repo, _, num = ref.partition("#")
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/{num}", headers=_headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                it = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            out.append(f"== {ref}: not fetched ({type(exc).__name__})")
            continue
        body = " ".join((it.get("body") or "").split())
        out.append(f"== {ref} [{it.get('state')}/{it.get('state_reason')}] created {(it.get('created_at') or '')[:10]} "
                   f"closed {(it.get('closed_at') or '')[:10]} comments {it.get('comments')}\n{it.get('title')}\n"
                   f"{body[:chars]}")
        time.sleep(1.0)
    return "\n\n".join(out) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Read-only duplicate search on the upstream trackers.")
    ap.add_argument("--show", nargs="*", default=None, help="owner/repo#number: write full bodies to dup_search_details.log")
    ap.add_argument("--causes", nargs="*", default=None, help="run only these causes and merge into dup_search.json")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    os.makedirs(EVIDENCE, exist_ok=True)
    if args.show:
        with open(os.path.join(EVIDENCE, "dup_search_details.log"), "w", encoding="utf-8") as f:
            f.write(show(args.show))
        print("wrote dup_search_details.log")
        return 0
    res = run_all(args.causes)
    if args.causes:
        with open(os.path.join(EVIDENCE, "dup_search.json"), encoding="utf-8") as f:
            old = json.load(f)
        if old["date"] != res["date"] or old["per_query"] != res["per_query"]:
            raise SystemExit(f"--causes merges only into a search of the same day and depth ({old['date']})")
        old["causes"].update(res["causes"])
        res = old
    with open(os.path.join(EVIDENCE, "dup_search.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    text = render(res)
    with open(os.path.join(EVIDENCE, "dup_search.log"), "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote dup_search.json/.log: " + ", ".join(
        f"{k} {len(v['candidates'])}" for k, v in res["causes"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
