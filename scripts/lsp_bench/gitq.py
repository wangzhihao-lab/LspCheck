"""Git queries against local bare clones, always through subprocess argv.

The interactive shell of this project rewrites literal ``git log`` and
``git show`` into a lossy summary, so every data-bearing git call lives here
and is executed from inside Python.

Provides: a cached full-history dump per repo, a PR-number index built from
merge/squash commit messages, tag containment (``git tag --contains``),
ancestry checks, and blob reads that never trigger a lazy fetch.

Run line: imported by mine_candidates.py and versions_*.py, not run directly.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from paths import CACHE_DIR, CLONE_URLS

logger = logging.getLogger(__name__)

_RS, _US = "\x1e", "\x1f"
_FORMAT = f"{_RS}%H{_US}%P{_US}%cI{_US}%s{_US}%b"


@dataclass(frozen=True)
class Commit:
    """A commit as read from ``git log``."""

    sha: str
    parents: tuple
    date: str
    subject: str
    body: str


# Never let a partial clone fetch missing objects on demand: queries must be
# local and must not modify the clones.
GIT_ENV: Dict[str, str] = {"GIT_NO_LAZY_FETCH": "1", "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
                           "HOME": str(Path.home())}


def run_git(repo: Path, args: List[str], timeout: int = 600, check: bool = True) -> str:
    """Run git with an argv list in ``repo`` and return stdout."""
    proc = subprocess.run(
        ["git", "-C", str(repo)] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        env=GIT_ENV,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])} failed in {repo.name}: {proc.stderr[-800:]}")
    return proc.stdout


def ensure_clone(repo: Path) -> None:
    """Create a treeless bare clone if it is missing (only for repos this miner owns)."""
    if (repo / "HEAD").exists():
        return
    url = CLONE_URLS.get(str(repo))
    if url is None:
        raise FileNotFoundError(f"missing clone {repo} and no URL registered for it")
    repo.parent.mkdir(parents=True, exist_ok=True)
    logger.info("cloning %s (treeless) into %s", url, repo)
    subprocess.run(["git", "clone", "--bare", "--filter=tree:0", url, str(repo)], check=True, timeout=3600)


def _cache_path(repo: Path) -> Path:
    return CACHE_DIR / f"gitlog_{repo.name.replace('.git', '')}.jsonl"


_LOGS: Dict[str, List[Commit]] = {}
_LOCK = threading.Lock()


def full_log(repo: Path) -> List[Commit]:
    """Return every commit reachable from any ref (memoized; cached as JSONL under temp/)."""
    with _LOCK:
        if str(repo) not in _LOGS:
            _LOGS[str(repo)] = _load_full_log(repo)
        return _LOGS[str(repo)]


def _load_full_log(repo: Path) -> List[Commit]:
    cache = _cache_path(repo)
    if cache.exists():
        out: List[Commit] = []
        with cache.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    d["parents"] = tuple(d["parents"])
                    out.append(Commit(**d))
        return out
    raw = run_git(repo, ["log", "--all", f"--format={_FORMAT}"], timeout=1200)
    commits: List[Commit] = []
    for chunk in raw.split(_RS):
        if not chunk.strip():
            continue
        parts = chunk.rstrip("\n").split(_US, 4)
        if len(parts) != 5:
            continue
        sha, par, date, subj, body = parts
        commits.append(Commit(sha=sha, parents=tuple(par.split()), date=date, subject=subj, body=body))
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("w", encoding="utf-8") as f:
        for c in commits:
            f.write(json.dumps({"sha": c.sha, "parents": list(c.parents), "date": c.date,
                                "subject": c.subject, "body": c.body}, ensure_ascii=False) + "\n")
    logger.info("%s: %d commits dumped", repo.name, len(commits))
    return commits


_PR_PATTERNS = [
    re.compile(r"^Merge pull request #(\d+) "),          # GitHub merge commit
    re.compile(r"^Merge #(\d+)"),                        # bors-ng
    re.compile(r"^Auto merge of #(\d+) "),               # homu
    re.compile(r"\(#(\d+)\)\s*$"),                       # squash merge "title (#N)"
]


_INDEX: Dict[str, Dict[str, Commit]] = {}


def commit_index(repo: Path) -> Dict[str, Commit]:
    """Map full sha -> Commit for every commit of ``full_log(repo)`` (memoized)."""
    key = str(repo)
    if key not in _INDEX:
        commits = full_log(repo)
        _INDEX[key] = {c.sha: c for c in commits}
    return _INDEX[key]


@lru_cache(maxsize=8)
def pr_index(repo: Path) -> Dict[int, List[Commit]]:
    """Map PR number -> commits whose subject records merging that PR (memoized)."""
    index: Dict[int, List[Commit]] = {}
    for c in full_log(repo):
        nums: List[int] = []
        for pat in _PR_PATTERNS:
            m = pat.search(c.subject)
            if m:
                nums.append(int(m.group(1)))
        if c.subject.startswith("Merge #"):
            nums.extend(int(n) for n in re.findall(r"#(\d+)", c.subject))
        for n in dict.fromkeys(nums):
            index.setdefault(n, []).append(c)
    return index


@lru_cache(maxsize=4096)
def tags_containing(repo: Path, sha: str) -> tuple:
    """Return the tags whose history contains ``sha`` (empty if unknown sha)."""
    try:
        out = run_git(repo, ["tag", "--contains", sha], timeout=300)
    except RuntimeError as exc:
        logger.warning("tag --contains %s in %s failed: %s", sha[:10], repo.name, str(exc)[:200])
        return tuple()
    return tuple(t for t in out.split() if t)


def is_ancestor(repo: Path, older: str, newer: str) -> Optional[bool]:
    """True if ``older`` is an ancestor of ``newer``; None if git cannot tell."""
    proc = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
                          capture_output=True, text=True, timeout=120, env=GIT_ENV)
    if proc.returncode in (0, 1):
        return proc.returncode == 0
    return None


def tag_dates(repo: Path) -> Dict[str, str]:
    """Map tag name -> committer date (ISO) of the tagged commit."""
    out = run_git(repo, ["for-each-ref", "--format=%(refname:short)\t%(*committerdate:iso-strict)\t%(committerdate:iso-strict)", "refs/tags"])
    res: Dict[str, str] = {}
    for line in out.splitlines():
        name, peeled, direct = (line.split("\t") + ["", ""])[:3]
        res[name] = peeled or direct
    return res


def commit_exists(repo: Path, sha: str) -> bool:
    """True if the commit object is present locally."""
    proc = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{sha}^{{commit}}"],
                          capture_output=True, text=True, timeout=60, env=GIT_ENV)
    return proc.returncode == 0
