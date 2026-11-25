"""Select the real-world project corpus by a fixed, reproducible rule.

Rule per language: GitHub repositories with stars >= 1000, pushed after the
cutoff, size between 200 KB and 40 MB, not archived, not a fork, whose root
contains the language's project file (tsconfig.json / pyproject.toml or
setup.py / Cargo.toml / go.mod), whose name or description is not a list,
tutorial or template, where the language is at least 60% of the code bytes
and the tree holds at least 30 source files of that language. Take the first
10 by stars and pin the default-branch HEAD commit.

Run line: python3 scripts/lsptest/select_corpus.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "data", "lsptest", "corpus.json")
CUTOFF = "2026-03-23"
PER_LANG = 10
LANGS: Dict[str, Dict[str, Any]] = {
    "typescript": {"q": "language:TypeScript", "files": [["tsconfig.json"]], "gh": "TypeScript", "ext": (".ts", ".tsx")},
    "python": {"q": "language:Python", "files": [["pyproject.toml"], ["setup.py"]], "gh": "Python", "ext": (".py",)},
    "rust": {"q": "language:Rust", "files": [["Cargo.toml"]], "gh": "Rust", "ext": (".rs",)},
    "go": {"q": "language:Go", "files": [["go.mod"]], "gh": "Go", "ext": (".go",)},
}
MIN_SHARE = 0.60
MIN_FILES = 30
EXCLUDE_WORDS = ("awesome", "tutorial", "course", "interview", "leetcode", "example", "examples", "book",
                 "roadmap", "cheatsheet", "learn", "guide", "list", "template", "boilerplate", "starter",
                 "radar", "collection", "resources")


CACHE = os.path.join(REPO, "temp", "cache", "github_api")


def _get(url: str) -> Any:
    """GET a GitHub API URL with retries and an on-disk cache (reruns are idempotent)."""
    os.makedirs(CACHE, exist_ok=True)
    cpath = os.path.join(CACHE, hashlib.sha256(url.encode()).hexdigest() + ".json")
    if os.path.exists(cpath):
        with open(cpath, encoding="utf-8") as f:
            return json.load(f)
    tok = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "corpus-select"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                data = json.loads(r.read().decode())
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return data
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                time.sleep(20 * (attempt + 1))
                continue
            if e.code in (404, 409):
                return None
            raise
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionError) as e:
            logger.warning("network error (%s), retrying: %s", type(e).__name__, url)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"giving up on {url}")


def _root_names(full: str) -> List[str]:
    items = _get(f"https://api.github.com/repos/{full}/contents/") or []
    return [i["name"] for i in items if isinstance(i, dict)]


def select(lang: str, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    q = f'{spec["q"]} stars:>=1000 pushed:>={CUTOFF} size:200..40000 archived:false fork:false'
    picked: List[Dict[str, Any]] = []
    for page in range(1, 6):
        res = _get("https://api.github.com/search/repositories?" + urllib.parse.urlencode(
            {"q": q, "sort": "stars", "order": "desc", "per_page": 50, "page": page}))
        for r in res.get("items", []):
            name = r["full_name"].lower()
            desc = (r.get("description") or "").lower()
            if any(w in name or w in desc.split() for w in EXCLUDE_WORDS):
                continue
            names = _root_names(r["full_name"])
            if not any(all(f in names for f in group) for group in spec["files"]):
                continue
            langs = _get(f"https://api.github.com/repos/{r['full_name']}/languages") or {}
            share = langs.get(spec["gh"], 0) / max(1, sum(langs.values()))
            if share < MIN_SHARE:
                continue
            head = _get(f"https://api.github.com/repos/{r['full_name']}/commits/{r['default_branch']}")
            tree = _get(f"https://api.github.com/repos/{r['full_name']}/git/trees/{head['sha']}?recursive=1") or {}
            n_src = sum(1 for t in tree.get("tree", []) if t.get("type") == "blob" and t["path"].endswith(spec["ext"]))
            if n_src < MIN_FILES:
                continue
            picked.append({"language": lang, "repo": r["full_name"], "stars": r["stargazers_count"],
                           "size_kb": r["size"], "lang_share": round(share, 2), "source_files": n_src,
                           "default_branch": r["default_branch"],
                           "commit": head["sha"], "pushed_at": r["pushed_at"]})
            logger.info("%s %s (%s stars, %s KB, %.0f%% %s, %s files)", lang, r["full_name"], r["stargazers_count"],
                        r["size"], 100 * share, spec["gh"], n_src)
            if len(picked) >= PER_LANG:
                return picked
            time.sleep(0.5)
        time.sleep(3)
    return picked


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    corpus = {lang: select(lang, spec) for lang, spec in LANGS.items()}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"rule": " ".join(__doc__.strip().splitlines()[2:10]), "cutoff": CUTOFF, "selected_on": time.strftime("%Y-%m-%d"),
                   "corpus": corpus}, f, ensure_ascii=False, indent=2)
    logger.info("wrote %s", OUT)


if __name__ == "__main__":
    main()
