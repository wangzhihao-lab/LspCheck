"""Raw git access for the backfill pipeline.

IMPORTANT: every git invocation here goes through Python's ``subprocess``
module directly (never as literal shell text passed to a Bash tool). This
project's interactive shell has an `rtk` hook that
transparently rewrites recognized Bash commands -- in particular
``git log`` becomes ``rtk git log`` ("one-line commit history") and
``git show`` becomes ``rtk git show`` ("compact show"), both of which
reformat/summarize output and would silently corrupt the exact hashes,
dates, and full commit-message text this pipeline depends on. Invoking git
as a subprocess from inside a already-running ``python3`` process is not a
recognized rtk pattern and is never rewritten, so all data-bearing git
calls live here and nowhere else.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

REC_SEP = "\x1e"  # RS, marks the start of each commit record
FIELD_SEP = "\x1f"  # US, separates fields within a record
LOG_FORMAT = f"{REC_SEP}%H{FIELD_SEP}%P{FIELD_SEP}%ci{FIELD_SEP}%s{FIELD_SEP}%b"


@dataclass(frozen=True)
class CommitRaw:
    hash: str
    parents: list[str]
    date: str
    subject: str
    body: str


@dataclass(frozen=True)
class CloneResult:
    url: str
    dest: str
    already_existed: bool
    elapsed_s: float
    size_bytes: int


def run_git(repo_dir: Path, args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Run git with explicit argv (no shell) and return the completed process."""
    cmd = ["git", "-C", str(repo_dir)] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size
    return total


def clone_bare(url: str, dest: Path, filter_spec: str = "blob:none") -> CloneResult:
    """Clone a bare, blob-filtered mirror of ``url`` into ``dest`` unless it
    already exists (idempotent: reruns never re-clone)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    already = (dest / "HEAD").exists()
    t0 = time.monotonic()
    if not already:
        proc = subprocess.run(
            [
                "git",
                "clone",
                f"--filter={filter_spec}",
                "--bare",
                url,
                str(dest),
            ],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed for {url}: {proc.stderr[-4000:]}")
    elapsed = time.monotonic() - t0
    size = dir_size_bytes(dest)
    return CloneResult(url=url, dest=str(dest), already_existed=already, elapsed_s=elapsed, size_bytes=size)


def fetch_updates(repo_dir: Path) -> None:
    """Refresh an existing bare clone in place (kept separate from clone_bare
    so a rerun can pick up new commits without a fresh clone)."""
    run_git(repo_dir, ["fetch", "--filter=blob:none", "--all", "--prune"], timeout=1800)


def get_full_log(repo_dir: Path) -> list[CommitRaw]:
    """Dump the entire reachable commit history exactly once, in a single
    ``git log`` process, using control-character delimiters so multi-line
    commit bodies can never be confused with field/record boundaries."""
    proc = subprocess.run(
        ["git", "-C", str(repo_dir), "log", "--all", f"--format={LOG_FORMAT}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git log --all failed in {repo_dir}: {proc.stderr[-4000:]}")
    return parse_full_log(proc.stdout)


def parse_full_log(raw: str) -> list[CommitRaw]:
    chunks = raw.split(REC_SEP)
    commits: list[CommitRaw] = []
    for chunk in chunks:
        if not chunk:
            continue
        if chunk.endswith("\n"):
            chunk = chunk[:-1]
        parts = chunk.split(FIELD_SEP, 4)
        if len(parts) != 5:
            # Should not happen with a well-formed log; skip defensively.
            continue
        h, p, d, s, b = parts
        parents = p.split() if p else []
        commits.append(CommitRaw(hash=h, parents=parents, date=d, subject=s, body=b))
    return commits


@dataclass(frozen=True)
class NumstatResult:
    files: list[str]
    insertions: int
    deletions: int
    is_merge: bool
    fetch_failed: bool = False


def get_numstat(repo_dir: Path, commit_hash: str, is_merge: bool, retries: int = 3) -> NumstatResult:
    """Return the changed-file list and insertion/deletion counts for a
    commit via ``git show --format= --numstat`` (the machine-readable form
    of ``--stat``; chosen over the human graph format because the latter can
    truncate long pathnames, which would corrupt the test-path detection).
    Renames are disabled (--no-renames) so every touched path is reported as
    a plain add/delete pair rather than an ambiguous ``{old => new}`` token.
    Merge commits are not given special handling: empirically verified
    (2.50.1) that plain `git show --numstat <merge>` already defaults to a
    diff against the merge's *first parent only* (identical output to
    `--first-parent -m`), not an empty diff and not a combined diff against
    every parent. is_merge is still recorded so downstream analysis can
    tell "diff vs first parent of a merge" apart from a normal commit's
    diff if that distinction ever matters.
    """
    last_err = ""
    for attempt in range(retries):
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "show",
                "--format=",
                "--numstat",
                "--no-renames",
                "--no-color",
                commit_hash,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if proc.returncode == 0:
            return _parse_numstat(proc.stdout, is_merge)
        last_err = proc.stderr
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"git show --numstat failed for {commit_hash} in {repo_dir}: {last_err[-2000:]}")


def _parse_numstat(raw: str, is_merge: bool) -> NumstatResult:
    files: list[str] = []
    insertions = 0
    deletions = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        ins_s, del_s, path = parts
        files.append(path)
        if ins_s.isdigit():
            insertions += int(ins_s)
        if del_s.isdigit():
            deletions += int(del_s)
    return NumstatResult(files=files, insertions=insertions, deletions=deletions, is_merge=is_merge)
