"""Mine benchmark candidates: historical language-server bugs for pinned pre/post-fix builds.

Subcommands
  retrieve  keyword retrieval (patterns.py) over the fixed-bug issues of pyright,
            tsserver, rust-analyzer and gopls created on/after 2019-01-01; writes
            screening sheets to temp/lsp_bench/sheets for manual reading.
  build     checks that decisions/*.py decide every retrieved issue exactly once,
            maps each kept candidate's fix to the nearest released pre-fix and
            post-fix builds (versions_*.py), records build availability and
            whether the fix changed tests, ranks by scriptability (rank.py) and
            writes data/lsp_bench/candidates.jsonl and candidates.md.
  all       retrieve, then build.

The GitHub token is read from os.environ["GITHUB_TOKEN"] inside httpcache.py
only; it is never printed or written. All git access goes through gitq.py.

Optional: --check-gopls-builds compiles every gopls pre/post release not yet
checked (gopls_builds.py) and folds the result into builds_obtainable.

Run line: python3 scripts/lsp_bench/mine_candidates.py all --check-gopls-builds
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gitq  # noqa: E402
import httpcache  # noqa: E402
import versions_gopls  # noqa: E402,F401  (registers mapper)
import versions_pyright  # noqa: E402,F401
import versions_ra  # noqa: E402,F401
import versions_ts  # noqa: E402,F401
from decisions import load_all  # noqa: E402
from evidence import fix_touches_tests  # noqa: E402
from gopls_builds import annotate, both_ok, check_versions, load_results  # noqa: E402
from issues import Issue  # noqa: E402
from overrides import NO_RELEASED_BUG  # noqa: E402
from paths import (CANDIDATES_JSONL, CANDIDATES_MD, RA_REPO, SERVERS, TS_REPO,  # noqa: E402
                   ensure_dirs)
from rank import rank_rows, score  # noqa: E402
from report import write_report  # noqa: E402
from retrieve import Retrieved, retrieve, write_sheets  # noqa: E402
from versions_common import MAPPERS, VersionMapping  # noqa: E402

logger = logging.getLogger("mine_candidates")


def cmd_retrieve() -> Dict[str, Tuple[List[Issue], List[Retrieved]]]:
    """Run retrieval for every server and write the screening sheets."""
    ensure_dirs()
    for repo in (TS_REPO, RA_REPO):
        gitq.ensure_clone(repo)
    out: Dict[str, Tuple[List[Issue], List[Retrieved]]] = {}
    for server in SERVERS:
        issues, found = retrieve(server)
        write_sheets(server, issues, found)
        out[server] = (issues, found)
    return out


def _check_coverage(server: str, found: List[Retrieved], keep: Dict[int, tuple], reject: Dict[str, tuple]) -> None:
    decided = list(keep) + [n for nums in reject.values() for n in nums]
    got, want = set(decided), {r.number for r in found}
    dups = sorted({n for n in decided if decided.count(n) > 1})
    if got != want or dups:
        raise SystemExit(f"{server}: decisions do not match retrieval: missing {sorted(want - got)[:20]}, "
                         f"extra {sorted(got - want)[:20]}, duplicated {dups[:20]}")


def _row(server: str, issue: Issue, hit: Retrieved, entry: tuple) -> Dict[str, object]:
    oracle, grade, reason, hint = entry
    subtype = hint.split(":", 1)[0].strip()
    mapping: VersionMapping = MAPPERS[server](issue)
    tests = fix_touches_tests(server, issue, mapping)
    caveat = NO_RELEASED_BUG.get((server, issue.number))
    notes = f"{reason} Trigger: {hint}."
    if mapping.mapping_confidence != "high":
        notes += f" Mapping ({mapping.mapping_confidence}): {mapping.mapping_method}."
    if caveat:
        notes += f" No released pre-fix build carries the bug ({caveat})."
    if not mapping.builds_obtainable:
        notes += f" Builds: {mapping.build_notes}."
    row: Dict[str, object] = {
        "server": server, "number": issue.number, "url": issue.url, "title": issue.title,
        "oracle_class": oracle, "match_reason": hit.match_reason, "fix_ref": mapping.fix_ref,
        "fix_date": mapping.fix_date, "pre_version": mapping.pre_version, "post_version": mapping.post_version,
        "mapping_confidence": mapping.mapping_confidence, "builds_obtainable": mapping.builds_obtainable,
        "scriptability_rank": None, "notes": notes,
        "subtype": subtype, "grade": grade, "top80": False, "score": None,
        "screening_reason": reason, "trigger_hint": hint,
        "pre_date": mapping.pre_date, "post_date": mapping.post_date,
        "mapping_method": mapping.mapping_method, "build_notes": mapping.build_notes,
        "fix_touches_tests": tests, "fix_shas": list(mapping.fix_shas),
        "no_released_bug": caveat is not None, "mapping_extra": mapping.extra,
    }
    return row


def _apply_gopls_builds(rows: List[Dict[str, object]], check: bool, jobs: int) -> None:
    """Fold gopls build-check results into builds_obtainable and build_notes."""
    gopls_rows = [r for r in rows if r["server"] == "gopls"]
    versions = {v for r in gopls_rows for v in (r["pre_version"], r["post_version"]) if v}
    results = check_versions(versions, jobs) if check else load_results()
    for r in gopls_rows:
        if not r["pre_version"] or not r["post_version"]:
            continue
        note = annotate(str(r["pre_version"]), str(r["post_version"]), results)
        ok = both_ok(str(r["pre_version"]), str(r["post_version"]), results)
        if note is None or ok is None:
            r["build_notes"] = f"{r['build_notes']}; build not checked"
            continue
        r["build_notes"] = f"{r['build_notes']}; build check: {note}"
        if not ok:
            r["builds_obtainable"] = False
            r["notes"] = f"{r['notes']} Builds: {note}."


def cmd_build(workers: int, check_builds: bool = False, build_jobs: int = 2) -> None:
    """Join decisions, map versions, rank, and write the deliverables."""
    ensure_dirs()
    decisions = load_all()
    rows: List[Dict[str, object]] = []
    retrieved: Dict[str, List[dict]] = {}
    rejects: Dict[str, Dict[str, int]] = {}
    totals: Dict[str, int] = {}
    jobs = []
    for server in SERVERS:
        issues, found = retrieve(server)
        keep, reject = decisions.get(server, ({}, {}))
        _check_coverage(server, found, keep, reject)
        totals[server] = len(issues)
        retrieved[server] = [{"number": r.number, "hits": [list(h) for h in r.hits]} for r in found]
        rejects[server] = {code: len(nums) for code, nums in reject.items()}
        by_num = {i.number: i for i in issues}
        hits = {r.number: r for r in found}
        jobs += [(server, by_num[n], hits[n], keep[n]) for n in sorted(keep)]
    logger.info("mapping %d kept candidates with %d workers", len(jobs), workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_row, *job) for job in jobs]
        for k, fut in enumerate(futures, 1):
            rows.append(fut.result())
            if k % 25 == 0:
                logger.info("mapped %d/%d", k, len(jobs))
    _apply_gopls_builds(rows, check_builds, build_jobs)
    for r in rows:
        r["score"] = score(r)
    ordered = rank_rows(rows, SERVERS)
    with CANDIDATES_JSONL.open("w", encoding="utf-8") as f:
        for r in ordered:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    write_report(CANDIDATES_MD, SERVERS, ordered, retrieved, rejects, totals, dict(httpcache.STATS))
    logger.info("wrote %s (%d rows) and %s; http %s", CANDIDATES_JSONL, len(ordered), CANDIDATES_MD, httpcache.STATS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["retrieve", "build", "all"])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--check-gopls-builds", action="store_true",
                        help="compile every gopls pre/post release not yet checked (slow; results cached)")
    parser.add_argument("--build-jobs", type=int, default=2)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.command in ("retrieve", "all"):
        cmd_retrieve()
    if args.command in ("build", "all"):
        cmd_build(args.workers, args.check_gopls_builds, args.build_jobs)


if __name__ == "__main__":
    main()
