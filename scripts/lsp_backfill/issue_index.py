"""Issue-number extraction and reverse-index building.

All patterns use an explicit non-digit boundary on both sides of the number
so ``#1234`` never matches inside ``#12345`` (and ``golang/go#1234`` never
matches inside ``golang/go#12345``); digits are the only characters that
must be excluded, since ``#`` itself already bounds the left side.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from git_utils import CommitRaw

# --- pyright: plain "#N" issue/PR references (single-repo convention) -----
PYRIGHT_REF_RE = re.compile(r"(?<!\d)#(\d+)(?!\d)")

# --- gopls: golang/tools commits reference golang/go issues cross-repo ----
GOLANG_GO_REF_RE = re.compile(r"golang/go#(\d+)(?!\d)")
GO_HASH_REF_RE = re.compile(r"(?<![A-Za-z0-9_/])go#(\d+)(?!\d)")
BARE_HASH_RE = re.compile(r"(?<!\d)#(\d+)(?!\d)")

PAT_GOLANG_GO = "golang/go#N"
PAT_GO_HASH = "go#N"
PAT_BARE_GOPLS = "bare#N+gopls"


def commit_text(c: CommitRaw) -> str:
    return f"{c.subject}\n{c.body}"


def extract_pyright_refs(text: str) -> set[int]:
    return {int(m.group(1)) for m in PYRIGHT_REF_RE.finditer(text)}


def extract_gopls_refs(text: str) -> dict[int, set[str]]:
    """Return {issue_number: {pattern names that matched}}."""
    refs: dict[int, set[str]] = {}

    def add(n: int, pattern: str) -> None:
        refs.setdefault(n, set()).add(pattern)

    for m in GOLANG_GO_REF_RE.finditer(text):
        add(int(m.group(1)), PAT_GOLANG_GO)
    for m in GO_HASH_REF_RE.finditer(text):
        add(int(m.group(1)), PAT_GO_HASH)

    if "gopls" in text.lower():
        for m in BARE_HASH_RE.finditer(text):
            start = m.start()
            prefix = text[max(0, start - 2) : start]
            if prefix.endswith("go"):
                continue  # already captured by golang/go#N or go#N above
            add(int(m.group(1)), PAT_BARE_GOPLS)
    return refs


@dataclass(frozen=True)
class PyrightIndex:
    # issue number -> list of commit hashes referencing it
    reverse: dict[int, list[str]]
    # commit hash -> set of issue numbers it references (for multi-issue flag)
    forward: dict[str, set[int]]


def build_pyright_index(commits: list[CommitRaw]) -> PyrightIndex:
    forward: dict[str, set[int]] = {}
    reverse: dict[int, list[str]] = {}
    for c in commits:
        refs = extract_pyright_refs(commit_text(c))
        if not refs:
            continue
        forward[c.hash] = refs
        for n in refs:
            reverse.setdefault(n, []).append(c.hash)
    return PyrightIndex(reverse=reverse, forward=forward)


@dataclass(frozen=True)
class GoplsIndex:
    # issue number -> list of (commit hash, sorted pattern names)
    reverse: dict[int, list[tuple[str, list[str]]]]
    # commit hash -> {issue number: sorted pattern names}
    forward: dict[str, dict[int, list[str]]]


def build_gopls_index(commits: list[CommitRaw]) -> GoplsIndex:
    forward: dict[str, dict[int, list[str]]] = {}
    reverse: dict[int, list[tuple[str, list[str]]]] = {}
    for c in commits:
        refs = extract_gopls_refs(commit_text(c))
        if not refs:
            continue
        forward[c.hash] = {n: sorted(pats) for n, pats in refs.items()}
        for n, pats in refs.items():
            reverse.setdefault(n, []).append((c.hash, sorted(pats)))
    return GoplsIndex(reverse=reverse, forward=forward)
