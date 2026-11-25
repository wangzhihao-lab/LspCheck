"""Select the second lsptest corpus batch: ranks 11-20 per language under the
frozen first-batch rule.

The rule and the search are those of scripts/lsptest/select_corpus.py, imported
and called unchanged (`select` with PER_LANG raised to 20). The search result
pages must come from the on-disk cache written by the 2026-09-23 selection run,
so the ranking is the ranking of that search; an uncached search page stops the
run instead of searching again. Before anything is written, ranks 1-10 of every
language must equal the 10 repositories of data/lsptest/corpus.json (same order);
any difference stops the run and is logged.

Ranks 11-20 are pinned to the last default-branch commit at or before
2026-09-23T23:59:59Z (commits API, `until`), the day the first batch was
selected. The project-file and source-file checks of the rule are recomputed at
the pinned commit and recorded as `pin_check`; `source_files` is the count at
the pinned commit.

Output: data/lsptest/corpus_v2.json (structure of corpus.json plus `rank` per
project, `pinned_until`, `note`). GitHub reads use $GITHUB_TOKEN through the
imported `_get` (never printed or written).

Run line: python3 -I scripts/paper/corpus2/select_corpus2.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional

sys.dont_write_bytecode = True
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LSPTEST = os.path.join(REPO, "scripts", "lsptest")
if LSPTEST not in sys.path:
    sys.path.insert(0, LSPTEST)

import select_corpus as sc  # noqa: E402  (frozen first-batch selector, used unchanged)

logger = logging.getLogger(__name__)
FIRST_JSON = os.path.join(REPO, "data", "lsptest", "corpus.json")
OUT = os.path.join(REPO, "data", "lsptest", "corpus_v2.json")
RANK_FROM, RANK_TO = 11, 20
PIN_UNTIL = "2026-09-23T23:59:59Z"
NOTE = ("Second batch. Same rule and same selection code as the first batch (scripts/lsptest/select_corpus.py, "
        "imported unchanged), applied to the same GitHub search (the cached result pages of the 2026-09-23 "
        "selection run): per language the repositories ranked 11-20 among those that pass the rule; ranks 1-10 "
        "were checked to equal data/lsptest/corpus.json. Each project is pinned to the last default-branch "
        "commit at or before 2026-09-23T23:59:59Z (commits API `until`), the first batch's selection day; "
        "`source_files` is counted at that commit and `pin_check` repeats the project-file and source-file "
        "checks there.")


class UncachedSearchError(RuntimeError):
    """A search page is not in the 2026-09-23 cache (re-searching would change the ranking)."""


def _cache_path(url: str) -> str:
    return os.path.join(sc.CACHE, hashlib.sha256(url.encode()).hexdigest() + ".json")


def _guarded_get(orig: Callable[[str], Any]) -> Callable[[str], Any]:
    """Wrap the selector's `_get` so that search pages are served only from cache."""

    def get(url: str) -> Any:
        if "/search/repositories?" in url and not os.path.exists(_cache_path(url)):
            raise UncachedSearchError(url)
        return orig(url)

    return get


def _pin(full: str, branch: str) -> Optional[Dict[str, str]]:
    """Last commit of `branch` at or before PIN_UNTIL: {'sha', 'date'} or None."""
    url = (f"https://api.github.com/repos/{full}/commits?"
           + urllib.parse.urlencode({"sha": branch, "until": PIN_UNTIL, "per_page": 1}))
    res = sc._get(url) or []
    if not res:
        return None
    c = res[0]
    return {"sha": c["sha"], "date": c["commit"]["committer"]["date"]}


def _check_at(full: str, sha: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Project-file and source-file checks of the rule at commit `sha`."""
    items = sc._get(f"https://api.github.com/repos/{full}/contents/?ref={sha}") or []
    names = [i["name"] for i in items if isinstance(i, dict)]
    has_file = any(all(f in names for f in group) for group in spec["files"])
    tree = sc._get(f"https://api.github.com/repos/{full}/git/trees/{sha}?recursive=1") or {}
    n_src = sum(1 for t in tree.get("tree", []) if t.get("type") == "blob" and t["path"].endswith(spec["ext"]))
    return {"project_file": has_file, "source_files": n_src, "tree_truncated": bool(tree.get("truncated")),
            "passes": has_file and n_src >= sc.MIN_FILES}


def _compare_first(lang: str, picked: List[Dict[str, Any]], first: List[Dict[str, Any]]) -> List[str]:
    """Differences between ranks 1-10 now and the first batch (empty list = identical)."""
    diffs: List[str] = []
    now = [(p["repo"], p["commit"]) for p in picked[:10]]
    then = [(p["repo"], p["commit"]) for p in first]
    if len(now) != len(then):
        diffs.append(f"{lang}: {len(now)} picks in ranks 1-10 vs {len(then)} in corpus.json")
    for i, (a, b) in enumerate(zip(now, then), start=1):
        if a[0] != b[0]:
            diffs.append(f"{lang} rank {i}: now {a[0]} vs corpus.json {b[0]}")
        elif a[1] != b[1]:
            diffs.append(f"{lang} rank {i} {a[0]}: commit now {a[1][:12]} vs corpus.json {b[1][:12]}")
    return diffs


def main() -> int:
    """Select, verify ranks 1-10, pin ranks 11-20, write corpus_v2.json. Returns the exit code."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with open(FIRST_JSON, encoding="utf-8") as f:
        first = json.load(f)
    sc._get = _guarded_get(sc._get)
    sc.PER_LANG = RANK_TO

    corpus: Dict[str, List[Dict[str, Any]]] = {}
    diffs: List[str] = []
    for lang, spec in sc.LANGS.items():
        try:
            picked = sc.select(lang, spec)
        except UncachedSearchError as e:
            logger.error("%s: ran past the cached 2026-09-23 search pages (%s); stopping", lang, e)
            return 2
        if len(picked) < RANK_TO:
            logger.error("%s: only %d repositories pass the rule; stopping", lang, len(picked))
            return 2
        diffs += _compare_first(lang, picked, first["corpus"][lang])
        batch: List[Dict[str, Any]] = []
        for rank, p in enumerate(picked[RANK_FROM - 1:RANK_TO], start=RANK_FROM):
            pin = _pin(p["repo"], p["default_branch"])
            if pin is None:
                logger.error("%s: no commit on %s at or before %s; stopping", p["repo"], p["default_branch"], PIN_UNTIL)
                return 2
            chk = _check_at(p["repo"], pin["sha"], spec)
            rec = dict(p)
            rec.update({"rank": rank, "commit": pin["sha"], "commit_date": pin["date"],
                        "source_files": chk["source_files"], "pin_check": chk})
            if not chk["passes"]:
                logger.warning("%s rank %d %s fails the rule at the pinned commit: %s", lang, rank, p["repo"], chk)
            batch.append(rec)
            logger.info("%s rank %d %s %s stars, pinned %s (%s)", lang, rank, p["repo"], p["stars"],
                        pin["sha"][:12], pin["date"])
        corpus[lang] = batch

    if diffs:
        for d in diffs:
            logger.error("ranks 1-10 differ from corpus.json: %s", d)
        logger.error("not writing %s", OUT)
        return 1
    logger.info("ranks 1-10 of all languages equal corpus.json (repo and commit)")
    out = {"rule": first["rule"], "cutoff": first["cutoff"], "selected_on": first["selected_on"],
           "built_on": time.strftime("%Y-%m-%d"),
           "ranks": f"{RANK_FROM}-{RANK_TO}", "pinned_until": PIN_UNTIL, "note": NOTE, "corpus": corpus}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    logger.info("wrote %s", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
