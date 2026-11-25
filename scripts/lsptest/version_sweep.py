"""Replay every triage group of a campaign on other server builds and record whether the
violation still reproduces: older releases (is the finding long-standing?) and, before the
data freeze, the newest releases (has upstream fixed it independently?). Self-produced evidence;
nothing is filed or asked of anyone.

Each group's representative repro.json (the reduced one under triage/<group>/ when it exists,
else the campaign's violations/<vid>/repro.json) is replayed through the oracle's own replay()
with fresh sessions of the mapped build, `--replays` times. Verdict per group and build:
reproduced (every replay reproduced), not-reproduced (every replay settled, the controls agreed
and none reproduced), flaky (some), unsettled (a replay did not settle or its controls
disagreed), error (the replay raised). Groups whose server kind has no mapping and r6_crossimpl
groups (they need both TypeScript builds) are skipped. Resumable: groups already in
results.jsonl are not replayed again unless --redo.

Writes data/lsptest/runs/<campaign>/sweep/<label>/{results.jsonl,summary.md}.

Run line: python3 scripts/lsptest/version_sweep.py main_v1 --label older-2025 --map pyright=pyright:1.1.405 --map ts6=tsserver:5.9.3+tsls5.0.0 --map gopls=gopls:v0.20.0 --map rust-analyzer=rust-analyzer:2025-10-27 [--replays 3] [--only substr] [--redo]
"""

from __future__ import annotations

import argparse
import collections
import json
import logging
import os
import shutil
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import flake  # noqa: E402
import oracles  # noqa: E402
from campaign_store import (REPO, context_from_repro, load_repro, paths_for, prepare_repro_project, read_jsonl,  # noqa: E402
                            rel, sweep_session_dirs)
from driver import RUNS_DIR  # noqa: E402

logger = logging.getLogger("version_sweep")
SKIPPED_ORACLES = frozenset({"r6_crossimpl"})


def parse_maps(items: List[str]) -> Dict[str, Tuple[str, str]]:
    """--map ts6=tsserver:5.9.3+tsls5.0.0  ->  {"ts6": ("tsserver", "5.9.3+tsls5.0.0")}"""
    out: Dict[str, Tuple[str, str]] = {}
    for item in items:
        src, _, dst = item.partition("=")
        kind, _, version = dst.partition(":")
        if not (src and kind and version):
            raise SystemExit(f"--map expects <kind>=<kind>:<version>, got {item!r}")
        out[src] = (kind, version)
    return out


def group_repros(campaign: str) -> List[Dict[str, Any]]:
    """(gid, signature, oracle, repro path) for every group of the triage index."""
    paths = paths_for(campaign)
    with open(os.path.join(paths.triage, "triage.json"), "r", encoding="utf-8") as f:
        groups = json.load(f)["groups"]
    out = []
    for g in groups:
        reduced = os.path.join(paths.triage, g["gid"], "repro.json")
        original = os.path.join(paths.root, "violations", g["representative"], "repro.json")
        path = reduced if os.path.exists(reduced) else original
        out.append({"gid": g["gid"], "signature": g["signature"], "repro": path, "reduced": path == reduced})
    return out


def replay_group(entry: Mapping[str, Any], build: Tuple[str, str], label: str, replays: int) -> Dict[str, Any]:
    doc, v = load_repro(entry["repro"])
    doc = dict(doc, server={"kind": build[0], "version": build[1]})
    row: Dict[str, Any] = {"gid": entry["gid"], "signature": entry["signature"], "oracle": v.oracle,
                           "from": entry.get("from", ""), "build": {"kind": build[0], "version": build[1]},
                           "repro": rel(entry["repro"]), "reduced": entry["reduced"], "replays": replays,
                           "settled": 0, "control_stable": 0, "reproduced": 0, "seconds": 0.0, "error": ""}
    run_id = f"sw{entry['gid'][-6:]}"
    scratch = os.path.join(RUNS_DIR, f"sweep-{label}", entry["gid"])
    shutil.rmtree(scratch, ignore_errors=True)
    t0 = time.monotonic()
    try:
        root = prepare_repro_project(doc, scratch)
        ctx = context_from_repro(doc, root, os.path.join(scratch, "work"), run_id=run_id)
        oracle = oracles.get(v.oracle)
        for _ in range(replays):
            out = oracle.replay(ctx, v)
            row["settled"] += int(bool(out.settled))
            row["control_stable"] += int(bool(out.control_stable))
            row["reproduced"] += int(flake.counts(out))
    except Exception as exc:  # noqa: BLE001  (recorded per group; the sweep goes on)
        row["error"] = f"{type(exc).__name__}: {exc}"[:400]
        logger.warning("group %s on %s %s: %s", entry["gid"], build[0], build[1], row["error"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        sweep_session_dirs(run_id)
    row["seconds"] = round(time.monotonic() - t0, 1)
    row["verdict"] = verdict(row)
    return row


def verdict(row: Mapping[str, Any]) -> str:
    n, hits = int(row["replays"]), int(row["reproduced"])
    if row.get("error"):
        return "error"
    if hits == n:
        return "reproduced"
    if row["settled"] < n or row["control_stable"] < n:
        return "unsettled"
    return "not-reproduced" if hits == 0 else "flaky"


def summary(rows: List[Dict[str, Any]], label: str, maps: Mapping[str, Tuple[str, str]]) -> str:
    by_kind: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    by_oracle: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for r in rows:
        by_kind[r["from"]][r["verdict"]] += 1
        by_oracle[r["oracle"]][r["verdict"]] += 1
    verdicts = ("reproduced", "not-reproduced", "flaky", "unsettled", "error", "skipped")
    lines = [f"# Version sweep `{label}`", "",
             "Each triage group's representative replayed on another build of its server; "
             "reproduced = every replay reproduced the violation, not-reproduced = every replay settled with agreeing "
             "controls and none reproduced.", "",
             "| from kind | build | " + " | ".join(verdicts) + " |", "|---|---|" + "---|" * len(verdicts)]
    for kind in sorted(by_kind):
        build = maps.get(kind, ("-", "-"))
        lines.append(f"| {kind} | {build[0]} {build[1]} | " + " | ".join(str(by_kind[kind][v]) for v in verdicts) + " |")
    lines += ["", "| oracle | " + " | ".join(verdicts) + " |", "|---|" + "---|" * len(verdicts)]
    for o in sorted(by_oracle):
        lines.append(f"| {o} | " + " | ".join(str(by_oracle[o][v]) for v in verdicts) + " |")
    lines += ["", "| group | from | build | verdict | reproduced | settled | seconds |", "|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: x["gid"]):
        b = r["build"]
        lines.append(f"| {r['gid']} | {r['from']} | {b['kind']} {b['version']} | {r['verdict']} | "
                     f"{r['reproduced']}/{r['replays']} | {r['settled']}/{r['replays']} | {r['seconds']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay triage groups on other server builds.")
    ap.add_argument("campaign")
    ap.add_argument("--label", required=True)
    ap.add_argument("--map", action="append", default=[], help="<kind>=<kind>:<version>")
    ap.add_argument("--replays", type=int, default=3)
    ap.add_argument("--only", default="", help="groups whose id contains this text")
    ap.add_argument("--redo", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    maps = parse_maps(args.map)
    out_dir = os.path.join(paths_for(args.campaign).root, "sweep", args.label)
    os.makedirs(out_dir, exist_ok=True)
    results = os.path.join(out_dir, "results.jsonl")
    done = {} if args.redo else {r["gid"]: r for r in read_jsonl(results)}
    rows: List[Dict[str, Any]] = list(done.values())
    for entry in group_repros(args.campaign):
        if args.only not in entry["gid"] or entry["gid"] in done:
            continue
        doc, v = load_repro(entry["repro"])
        kind = doc["server"]["kind"]
        entry = dict(entry, **{"from": kind})
        if kind not in maps or v.oracle in SKIPPED_ORACLES:
            row = {"gid": entry["gid"], "signature": entry["signature"], "oracle": v.oracle, "from": kind,
                   "build": {"kind": "", "version": ""}, "repro": rel(entry["repro"]), "reduced": entry["reduced"],
                   "replays": 0, "settled": 0, "control_stable": 0, "reproduced": 0, "seconds": 0.0, "error": "",
                   "verdict": "skipped"}
        else:
            logger.info("group %s (%s): %s %s -> %s %s", entry["gid"], v.oracle, kind, doc["server"]["version"],
                        *maps[kind])
            row = replay_group(entry, maps[kind], args.label, args.replays)
        rows.append(row)
        with open(results, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{row['gid']}: {row['verdict']} ({row['reproduced']}/{row['replays']}, {row['seconds']}s)")
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(summary(rows, args.label, maps))
    counts = collections.Counter(r["verdict"] for r in rows)
    print(f"sweep {args.label}: {len(rows)} group(s); " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items()))
          + f"; see {rel(out_dir)}/summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
