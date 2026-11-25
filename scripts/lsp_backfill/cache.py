"""Disk caches so a rerun of the pipeline never re-clones and never re-runs
``git log`` / ``git show --numstat`` for work already done.

Two caches:
  * full commit log -> one JSONL file per repo (~one `git log --all` call)
  * per-commit numstat -> one JSON dict file per repo, keyed by commit hash
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from git_utils import CommitRaw, NumstatResult, get_full_log, get_numstat

_PRINT_FAILURE_LIMIT = 20
_failure_count = 0


def load_or_build_full_log(repo_dir: Path, cache_path: Path) -> tuple[list[CommitRaw], bool]:
    """Return (commits, was_cached)."""
    if cache_path.exists():
        commits: list[CommitRaw] = []
        with cache_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                d = json.loads(line)
                commits.append(CommitRaw(**d))
        return commits, True

    commits = get_full_log(repo_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        for c in commits:
            f.write(json.dumps(asdict(c), ensure_ascii=False))
            f.write("\n")
    tmp_path.replace(cache_path)
    return commits, False


class NumstatCache:
    """JSON-backed cache: commit hash -> numstat result.

    Flushes to disk periodically so an interrupted run loses at most a small
    batch of already-fetched entries, and a rerun resumes from disk.
    """

    def __init__(self, cache_path: Path, flush_every: int = 250) -> None:
        self.cache_path = cache_path
        self.flush_every = flush_every
        self._dirty_count = 0
        self._data: dict[str, dict] = {}
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as f:
                self._data = json.load(f)

    def __len__(self) -> int:
        return len(self._data)

    def n_failed(self) -> int:
        return sum(1 for d in self._data.values() if d.get("fetch_failed"))

    def __contains__(self, commit_hash: str) -> bool:
        return commit_hash in self._data

    def get(self, commit_hash: str) -> NumstatResult | None:
        d = self._data.get(commit_hash)
        if d is None:
            return None
        return NumstatResult(**d)

    def get_or_fetch(self, repo_dir: Path, commit_hash: str, is_merge: bool) -> NumstatResult:
        global _failure_count
        cached = self.get(commit_hash)
        if cached is not None:
            return cached
        try:
            result = get_numstat(repo_dir, commit_hash, is_merge)
        except RuntimeError as e:
            # Network/object-fetch failure after retries inside get_numstat.
            # Degrade to a zero-stat, flagged result instead of crashing a
            # multi-thousand-commit run over one bad commit; cached so a
            # rerun does not hang retrying the same failure indefinitely.
            _failure_count += 1
            if _failure_count <= _PRINT_FAILURE_LIMIT:
                print(f"[numstat WARNING] {commit_hash}: {e}", flush=True)
            result = NumstatResult(files=[], insertions=0, deletions=0, is_merge=is_merge, fetch_failed=True)
        self._data[commit_hash] = asdict(result)
        self._dirty_count += 1
        if self._dirty_count >= self.flush_every:
            self.flush()
        return result

    def flush(self) -> None:
        if self._dirty_count == 0 and self.cache_path.exists():
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f)
        tmp_path.replace(self.cache_path)
        self._dirty_count = 0
