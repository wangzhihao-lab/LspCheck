"""Paths, constants and target definitions for the LSP bug-pilot pipeline.

Run: python3 run_pilot.py  (from this directory)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixed paths (per task spec)
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPTS_DIR.parents[1] / "data" / "lsp_pilot"
RAW_DIR = DATA_DIR / "raw"

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# Years reported in the yearly distribution table.
YEAR_START = 2019
YEAR_END = 2026

# Sample size for the human eyeball file.
EYEBALL_SAMPLE_SIZE = 15
EYEBALL_RANDOM_SEED = 42

# Body is truncated before being written to the per-target JSONL files.
BODY_TRUNCATE_CHARS = 2000
EYEBALL_BODY_CHARS = 300

# Rate-limit safety margins (per task spec).
RATE_LIMIT_SLEEP_THRESHOLD = 100
RATE_LIMIT_DEFAULT_SLEEP_S = 60


@dataclass(frozen=True)
class Target:
    """One repo/label combination we collect closed 'bug' issues for.

    key: filesystem-safe slug used for cache subdirs and output filenames.
    owner/name: GitHub repo coordinates.
    bug_labels: labels ANDed together that define "closed bug-labeled issues"
        for this target's primary funnel (e.g. ("C-bug",) or ("gopls",)).
    monorepo_label_scope: True for golang/go and llvm/llvm-project, where
        "total issues" / "closed issues" are themselves scoped by the
        identifying label instead of the whole repo (there is no dedicated
        sub-repo to count against; the label substitutes for the repo scope,
        per the task spec's monorepo instruction).
    counts_only: optional (tier-7) targets - only compute total/closed/
        closed-bug-labeled counts, skip full node fetch, jsonl and eyeball
        sample (per task spec: "counts only").
    optional: True for tier-7 targets, only run if quota allows.
    """

    key: str
    owner: str
    name: str
    bug_labels: tuple[str, ...] = ()
    monorepo_label_scope: bool = False
    counts_only: bool = False
    optional: bool = False


# ---------------------------------------------------------------------------
# Required targets (1-6)
# ---------------------------------------------------------------------------
TARGET_RUST_ANALYZER = Target(
    key="rust-analyzer",
    owner="rust-lang",
    name="rust-analyzer",
    bug_labels=("C-bug",),
)

TARGET_PYRIGHT = Target(
    key="pyright",
    owner="microsoft",
    name="pyright",
    bug_labels=("bug",),
)

TARGET_GOPLS = Target(
    key="golang-go-gopls",
    owner="golang",
    name="go",
    bug_labels=("gopls",),
    monorepo_label_scope=True,
)

TARGET_CLANGD = Target(
    key="llvm-project-clangd",
    owner="llvm",
    name="llvm-project",
    bug_labels=("clangd",),
    monorepo_label_scope=True,
)

# Candidate "Domain: *" labels plausibly about the language service.
# Existence is confirmed against the live label list at runtime; only
# labels that actually exist are queried (missing ones are reported, not
# silently skipped).
#
# TASK_SPEC_GUESS: the literal example labels from the task spec. A live
# check found only 2 of these 13 exist verbatim on microsoft/TypeScript
# ("Domain: Formatter", "Domain: Error Messages") - the repo does NOT use
# bare "Domain: TSServer" / "Domain: Completion Lists" / etc.
TASK_SPEC_GUESS_DOMAINS = (
    "Domain: TSServer",
    "Domain: Completion Lists",
    "Domain: Quick Fixes",
    "Domain: Refactorings",
    "Domain: Rename",
    "Domain: Signature Help",
    "Domain: Go to Definition",
    "Domain: Find All References",
    "Domain: Formatter",
    "Domain: Error Messages",
    "Domain: Symbol Navigation",
    "Domain: Code Actions",
    "Domain: Organize Imports",
)

# Per coordinator direction (2026-09-20): rather than a fixed candidate
# list, enumerate EVERY "Domain:" label on the live repo (with counts) and
# keep those whose name mentions any of these keywords (case-insensitive
# substring match) as the language-service subset. Supersedes an earlier
# hardcoded "Domain: LS: *" guess.
TS_LANGUAGE_SERVICE_KEYWORDS = (
    "TSServer", "Completion", "Quick Fix", "Refactor", "Rename", "Signature",
    "Definition", "References", "Formatter", "Error Messages", "Symbol",
    "Code Action", "Organize Imports", "Navigation", "Hover", "JSDoc",
    "Import", "Inlay",
)

TARGET_TYPESCRIPT = Target(
    key="microsoft-typescript",
    owner="microsoft",
    name="TypeScript",
    bug_labels=("Bug",),
)

TARGET_JDTLS = Target(
    key="eclipse-jdtls",
    owner="eclipse-jdtls",
    name="eclipse.jdt.ls",
    bug_labels=("bug",),
)

REQUIRED_TARGETS: list[Target] = [
    TARGET_RUST_ANALYZER,
    TARGET_PYRIGHT,
    TARGET_GOPLS,
    TARGET_CLANGD,
    TARGET_TYPESCRIPT,
    TARGET_JDTLS,
]

# ---------------------------------------------------------------------------
# Coordinator-requested additions (2026-09-20, mid-run course correction).
# Always run (not gated on quota like tier-7): clangd's own repo (its
# primary issue tracker, separate from the llvm/llvm-project label:clangd
# row above, which is kept), and a pyright row for the maintainer's actual
# "fixed via label + comment" convention.
# ---------------------------------------------------------------------------
TARGET_CLANGD_REPO = Target(
    key="clangd-clangd-repo",
    owner="clangd",
    name="clangd",
    # bug_labels deliberately empty: resolved at runtime by clangd_pipeline
    # (a "bug" label if one exists, else all closed issues minus
    # enhancement/question-labeled ones).
)

TARGET_PYRIGHT_ADDRESSED = Target(
    key="pyright-addressed-in-next-version",
    owner="microsoft",
    name="pyright",
    bug_labels=("bug", "addressed in next version"),
)

# This target's rows are evidenced by the label combination itself, not a
# linked PR/commit (closing_prs may legitimately be empty for every row) -
# referenced by validate.py's assertion pass and eyeball_md.py's rendering.
LABEL_EVIDENCE_TARGET_KEY = TARGET_PYRIGHT_ADDRESSED.key

ADDITIONAL_TARGETS: list[Target] = [TARGET_CLANGD_REPO, TARGET_PYRIGHT_ADDRESSED]

# ---------------------------------------------------------------------------
# Optional targets (7) - only run if quota allows.
# ---------------------------------------------------------------------------
TARGET_LUALS = Target(
    key="lualls-lua-language-server",
    owner="LuaLS",
    name="lua-language-server",
    bug_labels=("bug",),
    counts_only=True,
    optional=True,
)

TARGET_OMNISHARP = Target(
    key="omnisharp-roslyn",
    owner="OmniSharp",
    name="omnisharp-roslyn",
    bug_labels=("bug",),
    counts_only=True,
    optional=True,
)

TARGET_DART = Target(
    key="dart-lang-sdk",
    owner="dart-lang",
    name="sdk",
    bug_labels=("area-analyzer", "type-bug"),
    counts_only=True,
    optional=True,
)

OPTIONAL_TARGETS: list[Target] = [TARGET_LUALS, TARGET_OMNISHARP, TARGET_DART]

ALL_TARGETS: list[Target] = REQUIRED_TARGETS + ADDITIONAL_TARGETS + OPTIONAL_TARGETS

# Quota (remaining GraphQL points) below which optional targets are skipped.
OPTIONAL_TARGET_MIN_REMAINING = 1000


def jsonl_path(target: Target) -> Path:
    return DATA_DIR / f"{target.key}_fixed_bugs.jsonl"


def raw_target_dir(target: Target) -> Path:
    d = RAW_DIR / target.key
    d.mkdir(parents=True, exist_ok=True)
    return d
