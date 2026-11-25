"""Benchmark detection campaign config (RQ: how many reproduced historical bugs do the generic
oracles detect?).

Reads data/lsp_bench/repro_results.jsonl (append-only; the last line of a case is its latest
verdict) and keeps every case whose latest verdict is `reproduced`, provided the verdict belongs
to the case's current revision (case_sha as scripts/lsptest/bench/run_repro.py computes it) and
both builds resolve in the server registry; everything else is listed with its reason. Each
kept case becomes a bench_cases entry: its project/ directory (never its repro ops or probe), its
settings, its session timeouts, its pre-fix and post-fix builds (separate runs), and, for the
detection table (campaign_detect.py), its class, subtype, ground-truth probe and whether that
probe is the specification probe edit_text_differs (reported separately). A case's
session.pull_diagnostics is recorded but cannot be applied: OracleContext has no
diagnostics-route field, so runs use the server's default route.
Oracles: every oracle whose applies_to accepts the case's server kind (tsserver cases run as kind
"tsserver"), without r6_crossimpl (a historical case has no TS6-era/TS7 build pair); r1_history
seeds 1-3 settled plus race0 seed 1, the others seeds 1-2. Targets: every source file of the
case project (one identifier is enough), up to 20 positions per file. The signature cap counts
per build, so that a capped candidate on the post-fix build is one confirmed there already.

Run line: python3 scripts/lsptest/campaign_bench.py [--out data/lsptest/campaigns/bench_v1.json] [--id bench_v1] [--dry-run-cases gopls-60435,rust-analyzer-21173,tsserver-46466]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import oracles  # noqa: E402
import servers  # noqa: E402  (lsp_repro)
from campaign_store import REPO, rel, write_json  # noqa: E402

logger = logging.getLogger("campaign_bench")
RESULTS = os.path.join(REPO, "data", "lsp_bench", "repro_results.jsonl")
CASES = os.path.join(REPO, "data", "lsp_bench", "cases")
SPEC_PROBES = frozenset({"edit_text_differs"})
SKIPPED_ORACLES = frozenset({"r6_crossimpl"})
ORACLE_SEEDS: Dict[str, Dict[str, Any]] = {
    "r0_crash": {"seeds": {"settled": [1, 2]}},
    "r1_history": {"seeds": {"settled": [1, 2, 3], "race0": [1]}, "max_cases": 12},
    "r2_handles": {"seeds": {"settled": [1, 2]}, "max_cases": 12},
    "r3_routes": {"seeds": {"settled": [1, 2]}},
    "r4_edits": {"seeds": {"settled": [1, 2]}, "max_cases": 12},
    "r5_transforms": {"seeds": {"settled": [1, 2]}, "max_cases": 6},
}


def latest_verdicts(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """case -> its last line in repro_results.jsonl."""
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        if r.get("case"):
            out[str(r["case"])] = dict(r)
    return out


def case_entry(case: Any, verdict: Mapping[str, Any]) -> Dict[str, Any]:
    """The bench_cases entry of one case (campaign_config.BenchCase plus detection metadata)."""
    m = case.meta
    probe = str(case.repro.probe.get("type", ""))
    session = {k: v for k, v in case.session.items() if k in ("settle_timeout_s", "request_timeout_s", "pull_diagnostics")}
    return {"case": case.case_id, "dir": rel(case.project_dir), "kind": str(m["kind"]), "language": case.language,
            "builds": {"pre": case.build("pre"), "post": case.build("post")}, "settings": case.settings or None,
            "session": session, "oracle_class": m.get("oracle_class"), "subtype": m.get("subtype"), "probe": probe,
            "spec_probe": probe in SPEC_PROBES, "case_sha": verdict.get("case_sha"), "verdict_started": verdict.get("started"),
            "url": m.get("url"), "title": m.get("title")}


def select_cases(verdicts: Mapping[str, Mapping[str, Any]], load: Any, sha: Any,
                 resolvable: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """(bench_cases entries, excluded cases with reasons); load/sha/resolvable are injected for tests."""
    kept: List[Dict[str, Any]] = []
    excluded: List[Dict[str, str]] = []
    for cid, v in sorted(verdicts.items()):
        if v.get("verdict") != "reproduced":
            excluded.append({"case": cid, "reason": f"latest verdict {v.get('verdict')}"})
            continue
        case = load(cid)
        if case is None:
            excluded.append({"case": cid, "reason": "case directory missing or unreadable"})
            continue
        if sha(case) != v.get("case_sha"):
            excluded.append({"case": cid, "reason": "the verdict belongs to an older revision of the case"})
            continue
        missing = [case.build(p) for p in ("pre", "post") if not resolvable(str(case.meta["kind"]), case.build(p))]
        if missing:
            excluded.append({"case": cid, "reason": f"build(s) not installed: {missing}"})
            continue
        kept.append(case_entry(case, v))
    return kept, excluded


def applicable_oracles(kinds: Sequence[str]) -> Dict[str, List[str]]:
    """kind -> oracles of the benchmark plan whose applies_to accepts it."""
    reg = oracles.load_all()
    return {k: [o for o in ORACLE_SEEDS if o in reg and reg[o].applies_to(k)] for k in kinds}


def build_config(cases: List[Dict[str, Any]], excluded: List[Dict[str, str]], cid: str,
                 dry_run_cases: Sequence[str], source: str, per_kind: Mapping[str, List[str]]) -> Dict[str, Any]:
    kinds = sorted({c["kind"] for c in cases})
    notes = [f"{k}: oracles {per_kind.get(k, [])}" for k in kinds]
    notes += ["r6_crossimpl is not run: a historical case has no TS6-era/TS7 build pair.",
              "session.pull_diagnostics of a case (rust-analyzer cases: false) is recorded but not applied: the oracle "
              "contract has no diagnostics-route field, so the runs use the server's default route.",
              "Detection: python3 scripts/lsptest/campaign_detect.py <campaign id> (pre-only confirmed signatures per case)."]
    return {"id": cid, "description": "Benchmark detection campaign: every reproduced historical case of data/lsp_bench "
            "(latest verdict), its project/ directory and settings, pre-fix and post-fix builds as separate runs, all "
            "applicable oracles except r6; generated by scripts/lsptest/campaign_bench.py.",
            "generated": {"from": rel(source), "date": time.strftime("%Y-%m-%d %H:%M"), "cases": len(cases),
                          "spec_probe_cases": sorted(c["case"] for c in cases if c["spec_probe"]),
                          "excluded": excluded},
            "corpus": "", "servers": [], "oracles": {o: dict(d) for o, d in ORACLE_SEEDS.items()},
            "targets": {"max_files": 100, "max_positions_per_file": 20, "max_file_bytes": 256000, "min_identifiers": 1},
            "timeouts": {"settle_s": 300, "request_s": 30, "run_s": 3600}, "concurrency": 4,
            "server_limits": {"rust-analyzer": 2} if "rust-analyzer" in kinds else {},
            "wall_clock_budget_h": 0, "flake": {"n": 3, "per_signature": 1},
            "signature_cap": {"runs": 3, "scope": "build"},
            "dry_run": {"projects": list(dry_run_cases)} if dry_run_cases else {},
            "bench_cases": cases, "notes": notes}


def _load_case(cid: str) -> Optional[Any]:
    from bench.case_format import CaseError, load_case  # late import (read-only use of the benchmark code)
    try:
        return load_case(os.path.join(CASES, cid))
    except CaseError as exc:
        logger.warning("case %s: %s", cid, exc)
        return None


def _case_sha(case: Any) -> str:
    from bench.run_repro import case_sha  # late import (read-only use of the benchmark code)
    return case_sha(case)


def _resolvable(kind: str, version: str) -> bool:
    try:
        servers.resolve(kind, version)
    except (FileNotFoundError, ValueError):
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the benchmark detection campaign config.")
    ap.add_argument("--out", default=os.path.join(REPO, "data", "lsptest", "campaigns", "bench_v1.json"))
    ap.add_argument("--id", default="bench_v1")
    ap.add_argument("--results", default=RESULTS)
    ap.add_argument("--dry-run-cases", default="gopls-60435,rust-analyzer-21173,tsserver-46466")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    with open(args.results, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    cases, excluded = select_cases(latest_verdicts(rows), _load_case, _case_sha, _resolvable)
    dry = [c for c in args.dry_run_cases.split(",") if c]
    unknown = sorted(set(dry) - {c["case"] for c in cases})
    if unknown:
        logger.error("dry-run cases not in the benchmark: %s", unknown)
        return 2
    per_kind = applicable_oracles(sorted({c["kind"] for c in cases}))
    write_json(args.out, build_config(cases, excluded, args.id, dry, args.results, per_kind))
    counts: Dict[str, int] = {}
    for c in cases:
        counts[c["kind"]] = counts.get(c["kind"], 0) + 1
    print(f"{rel(args.out)}: {len(cases)} case(s) {counts}, {sum(c['spec_probe'] for c in cases)} with the "
          f"specification probe; {len(excluded)} excluded; oracles per kind {per_kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
