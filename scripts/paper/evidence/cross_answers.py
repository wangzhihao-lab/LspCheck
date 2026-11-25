"""Answers of the other TypeScript implementation on the keys of one implementation's history groups.

A version sweep (scripts/lsptest/version_sweep.py) records only whether a group's violation reproduces
on another build. A non-reproduction on the other TypeScript implementation says something only when
that implementation answers the key, and it says more when its answer after the history is the answer
of the fresh session of the tested one. For every r1_history group of one server kind (ts6 or ts7),
this script replays the group's case once on a build of the other kind through the R1 oracle's own
helpers (final_state, pair_for_state, safe_session; the frozen tool is only imported) and records the
key's answer in the fresh baseline, the fresh control and the history session.
scripts/paper/numbers_evidence.py compares them with the tested server's answers (table M3).

Run ids are xa<kind digit><gid6>, so the session directories never collide with a sweep (sw<gid6>)
or the component isolation (iso<tag><gid6>).

Writes data/lsptest/runs/main_v1/evidence/answers_<from>_on_<kind>-<version>.json.

Run line: python3 scripts/paper/evidence/cross_answers.py --from ts6 [--build ts7:7.0.2] [--only substr]
          python3 scripts/paper/evidence/cross_answers.py --from ts7 [--build ts6:6.0.3]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import shutil
import sys
import time
from typing import Any, Dict, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))

import oracles  # noqa: E402  (frozen tool, read-only)
import version_sweep as vs  # noqa: E402
from campaign_store import context_from_repro, load_repro, prepare_repro_project, sweep_session_dirs  # noqa: E402
from driver import RUNS_DIR  # noqa: E402

logger = logging.getLogger("cross_answers")
CAMPAIGN = "main_v1"
OUT = os.path.join(REPO, "data", "lsptest", "runs", CAMPAIGN, "evidence")
OTHER = {"ts6": "ts7:7.0.2", "ts7": "ts6:6.0.3"}


def out_path(source: str, build: Tuple[str, str]) -> str:
    return os.path.join(OUT, f"answers_{source}_on_{build[0]}-{build[1]}.json")


def one_group(entry: Dict[str, Any], build: Tuple[str, str]) -> Dict[str, Any]:
    """One replay of the group's case on `build` with the key's answers recorded."""
    oracles.get("r1_history")
    from oracles.base import MISSING, case_of, final_state  # noqa: E402
    from oracles.r1_history import effective_settings, guard_ops, pair_for_state, safe_session, state_key  # noqa: E402
    doc, v = load_repro(entry["repro"])
    doc = dict(doc, server={"kind": build[0], "version": build[1]})
    run_id = f"xa{build[0][-1]}{entry['gid'][-6:]}"
    scratch = os.path.join(RUNS_DIR, f"sweep-answers-{build[0]}", entry["gid"])
    shutil.rmtree(scratch, ignore_errors=True)
    row: Dict[str, Any] = {"gid": entry["gid"], "key": doc.get("key"), "error": ""}
    t0 = time.monotonic()
    try:
        root = prepare_repro_project(doc, scratch)
        ctx = context_from_repro(doc, root, os.path.join(scratch, "work"), run_id=run_id)
        rctx = dataclasses.replace(ctx, timing=case_of(v).get("timing", ctx.timing))
        ops = list(v.ops)
        st = final_state(ctx.project_dir, ops)
        pair = pair_for_state(rctx, st, state_key(st, effective_settings(ctx)), "replay")
        snap, info = safe_session(rctx, "replay-history", ops + guard_ops(rctx, ops))
        get = lambda s: s.results[v.key].norm if v.key in s.results else MISSING  # noqa: E731
        row.update(settled=bool(pair.settled and info.valid), stable=v.key in pair.stable,
                   fresh=get(pair.baseline), control=get(pair.control), history=get(snap))
    except Exception as exc:  # noqa: BLE001  (recorded per group, as the sweep does)
        row["error"] = f"{type(exc).__name__}: {exc}"[:400]
        logger.warning("group %s: %s", entry["gid"], row["error"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        sweep_session_dirs(run_id)
    row["seconds"] = round(time.monotonic() - t0, 1)
    return row


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="source", required=True, choices=sorted(OTHER), help="server kind of the groups")
    ap.add_argument("--build", default="", help="<kind>:<version> to replay on (default: the other implementation)")
    ap.add_argument("--only", default="", help="groups whose id contains this text")
    args = ap.parse_args()
    kind, _, version = (args.build or OTHER[args.source]).partition(":")
    build = (kind, version)
    entries = [e for e in vs.group_repros(CAMPAIGN)
               if e["gid"].startswith(f"{args.source}-r1-") and args.only in e["gid"]]
    rows = []
    for e in entries:
        logger.info("group %s on %s %s", e["gid"], *build)
        rows.append(one_group(e, build))
        r = rows[-1]
        logger.info("  -> settled %s stable %s history==fresh %s %s", r.get("settled"), r.get("stable"),
                    r.get("history") == r.get("fresh"), r["error"])
    os.makedirs(OUT, exist_ok=True)
    with open(out_path(args.source, build), "w", encoding="utf-8") as f:
        json.dump({"source": args.source, "build": list(build), "rows": rows}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
