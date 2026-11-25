"""Replays that decide two merges of the root-cause draft (plan/root_causes_draft_2026-11-21.md, section 6,
items 3 and 4); post-freeze evidence, the frozen tool is only imported, as in cross_answers.py.

race   C33 (main_v2: ts6-r1-codeaction-key-lost-h8-3e0e0f, ts6-r1-diagnostics-moved-2875-h8-751ff9) against
       C2 (main_v1: ts6-r1-diagnostics-extra-2304-h7-8ca52f). Each group's reduced history (open, then two
       requests with no wait) is replayed through the R1 oracle's own replay() in three variants:
         orig        the reduced history as recorded (control: does the group still reproduce today)
         first-only  the second request dropped: open, then only the first request (typeDefinition)
         settle      the reduced history with a settle (the driver waits until the server is idle, as before
                     a snapshot) between the open and the first request
       The settle is an op of kind "settle" that a patched Driver.apply turns into Driver.settle(); every
       other op goes through the frozen Driver.apply. final_state ignores the kind, so the fresh pair is the
       one of the unchanged content. Per replay: settled, control stable, reproduced (same difference shape,
       flake.counts), any difference at all, and the observed history answer when it differs.
range  C27 (main_v1) and C29 (main_v2), both rust-analyzer-r3-semantictokensrange-changed-b-b6e28b. In a fresh
       session per replay (targets opened, settled, as the R3 replay does), semanticTokens/full and
       semanticTokens/range are requested and both cut to the tokens lying entirely inside the range
       (r3_routes.tokens_inside), in two variants:
         orig        the recorded range
         moved       the range's start moved to column 0 of the first line of the enclosing function's
                     attributes and doc comment (MOVED_START), the end unchanged
       For `moved` the comparison is reported over the whole moved range and over the original span alone.

Writes data/lsptest/runs/<campaign>/evidence/root_cause_replays_<sub>.json for each campaign involved (rows of
that campaign's groups; a rerun replaces the rows of the same group and variant).

Run line: python3 scripts/paper/evidence/root_cause_replays.py race [--replays 3] [--only substr]
          python3 scripts/paper/evidence/root_cause_replays.py range [--replays 3] [--only substr]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import shutil
import sys
import time
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import REPO, entry, evidence_dir  # noqa: E402

import driver  # noqa: E402  (frozen tool, read-only)
import flake  # noqa: E402
import oracles  # noqa: E402
from campaign_store import context_from_repro, load_repro, prepare_repro_project, sweep_session_dirs  # noqa: E402
from model import Op  # noqa: E402
from ops import OpOutcome  # noqa: E402

logger = logging.getLogger("root_cause_replays")

RACE_GROUPS: Tuple[Tuple[str, str, str], ...] = (
    ("C2", "main_v1", "ts6-r1-diagnostics-extra-2304-h7-8ca52f"),
    ("C33", "main_v2", "ts6-r1-codeaction-key-lost-h8-3e0e0f"),
    ("C33", "main_v2", "ts6-r1-diagnostics-moved-2875-h8-751ff9"),
)
RANGE_GID = "rust-analyzer-r3-semantictokensrange-changed-b-b6e28b"
# 0-based first line of the enclosing function including its attributes and doc comment:
#   main_v1 alacritty_terminal/src/tty/unix.rs: '/// Create a new TTY from a PTY's file descriptors.' above
#           'pub fn from_fd(...)' (0-based lines 200-201); the unsafe block of the range starts on line 247
#   main_v2 crates/google-workspace-cli/src/auth.rs: '#[tokio::test]', '#[serial_test::serial]' above
#           'async fn test_load_credentials_adc_env_var_authorized_user()' (0-based lines 539-541)
RANGE_GROUPS: Tuple[Tuple[str, str, int], ...] = (("C27", "main_v1", 200), ("C29", "main_v2", 539))


# ------------------------------------------------------------------ race (C2, C33)
@contextlib.contextmanager
def settle_ops() -> Iterator[None]:
    """Inside the block, Driver.apply turns an op of kind "settle" into Driver.settle()."""
    original = driver.Driver.apply

    def apply(self: Any, op: Op) -> OpOutcome:
        if op.kind != "settle":
            return original(self, op)
        res = self.settle()
        out = OpOutcome(op)
        out.seconds = round(getattr(res, "seconds", 0.0) or 0.0, 3)
        self._event("op", {"op": op.to_json(), "sent": [], "settled": bool(res.settled)})
        return out

    driver.Driver.apply = apply
    try:
        yield
    finally:
        driver.Driver.apply = original


def race_variants(ops: Sequence[Op]) -> Dict[str, List[Op]]:
    """orig, first-only (second request dropped), settle (a settle before the first request)."""
    ops = list(ops)
    reqs = [i for i, o in enumerate(ops) if o.kind == "request"]
    if len(reqs) != 2:
        raise ValueError(f"expected two requests in the reduced history, got {len(reqs)}")
    return {"orig": ops,
            "first-only": [o for i, o in enumerate(ops) if i != reqs[1]],
            "settle": ops[:reqs[0]] + [Op(kind="settle")] + ops[reqs[0]:]}


def _short(x: Any, limit: int = 1500) -> Any:
    s = json.dumps(x, ensure_ascii=False, default=str)
    return x if len(s) <= limit else s[:limit] + f"... ({len(s)} chars)"


def race_group(cause: str, campaign: str, gid: str, replays: int) -> List[Dict[str, Any]]:
    doc, v = load_repro(entry(gid, campaign)["repro"])
    rows: List[Dict[str, Any]] = []
    for name, ops in race_variants(v.ops).items():
        tag = {"orig": "rco", "first-only": "rcf", "settle": "rcs"}[name]
        run_id = f"{tag}{gid[-6:]}"
        scratch = os.path.join(driver.RUNS_DIR, f"evidence-{tag}", gid)
        shutil.rmtree(scratch, ignore_errors=True)
        row: Dict[str, Any] = {"cause": cause, "campaign": campaign, "gid": gid, "variant": name,
                               "ops": [o.to_json() for o in ops], "key": doc.get("key"),
                               "recorded_expected": _short(doc.get("expected")),
                               "recorded_actual": _short(doc.get("actual")),
                               "replays": replays, "settled": 0, "control_stable": 0, "reproduced": 0,
                               "differed": 0, "runs": [], "error": ""}
        t0 = time.monotonic()
        try:
            root = prepare_repro_project(doc, scratch)
            ctx = context_from_repro(doc, root, os.path.join(scratch, "work"), run_id=run_id)
            oracle = oracles.get(v.oracle)
            with settle_ops():
                for _ in range(replays):
                    out = oracle.replay(ctx, v, ops)
                    run = {"settled": bool(out.settled), "control_stable": bool(out.control_stable),
                           "reproduced": bool(flake.counts(out)), "differed": out.observed is not None,
                           "seconds": out.seconds}
                    if out.observed is not None:
                        run["observed_expected"] = _short(out.observed.expected)
                        run["observed_actual"] = _short(out.observed.actual)
                    row["runs"].append(run)
                    for k in ("settled", "control_stable", "reproduced", "differed"):
                        row[k] += int(run[k])
        except Exception as exc:  # noqa: BLE001  (recorded per row, as the version sweep does)
            row["error"] = f"{type(exc).__name__}: {exc}"[:400]
            logger.warning("%s %s: %s", gid, name, row["error"])
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
            sweep_session_dirs(run_id)
            with contextlib.suppress(OSError):
                os.rmdir(os.path.dirname(scratch))
        row["seconds"] = round(time.monotonic() - t0, 1)
        logger.info("%s %s %s: reproduced %d/%d, differed %d, settled %d, control stable %d %s", cause, gid, name,
                    row["reproduced"], replays, row["differed"], row["settled"], row["control_stable"], row["error"])
        rows.append(row)
    return rows


# ------------------------------------------------------------------ range (C27, C29)
def _diff(full: List[Any], rng: List[Any]) -> Dict[str, Any]:
    fs, rs = {tuple(t) for t in full}, {tuple(t) for t in rng}
    return {"equal": full == rng, "n_full": len(full), "n_range": len(rng),
            "only_full": [list(t) for t in sorted(fs - rs)], "only_range": [list(t) for t in sorted(rs - fs)]}


def range_session(ctx: Any, label: str, path: str, rng: List[int], orig: List[int]) -> Dict[str, Any]:
    oracles.get("r3_routes")
    from oracles.base import session  # noqa: E402
    from oracles.r3_routes import full_tokens, range_check, tokens_inside  # noqa: E402
    out: Dict[str, Any] = {}
    with session(ctx, label) as d:
        d.open(*[t.path for t in ctx.targets])
        out["settled"] = bool(d.settle().settled)
        full = full_tokens(ctx, d, path)
        if full is None:
            out["error"] = "semanticTokens/full failed"
            return out
        chk = range_check(ctx, d, path, rng, full)
        if not isinstance(chk.actual, list) or (len(chk.actual) == 2 and chk.actual[0] == "error"):
            out["error"] = f"semanticTokens/range failed: {chk.actual}"
            return out
        out["whole_range"] = _diff(chk.expected, chk.actual)
        if rng != orig:
            out["original_span"] = _diff(tokens_inside(chk.expected, orig), tokens_inside(chk.actual, orig))
    return out


def range_group(cause: str, campaign: str, start_line: int, replays: int) -> List[Dict[str, Any]]:
    doc, v = load_repro(entry(RANGE_GID, campaign)["repro"])
    case = doc["case"]
    path, orig = case["path"], list(case["range"])
    variants = {"orig": orig, "moved": [start_line, 0, orig[2], orig[3]]}
    rows: List[Dict[str, Any]] = []
    for name, rng in variants.items():
        tag = {"orig": "rgo", "moved": "rgm"}[name]
        run_id = f"{tag}{campaign[-1]}{RANGE_GID[-6:]}"
        scratch = os.path.join(driver.RUNS_DIR, f"evidence-{tag}", f"{campaign}-{RANGE_GID}")
        shutil.rmtree(scratch, ignore_errors=True)
        row: Dict[str, Any] = {"cause": cause, "campaign": campaign, "gid": RANGE_GID, "variant": name,
                               "path": path, "range": rng, "original_range": orig, "replays": replays,
                               "settled": 0, "differs": 0, "differs_on_original_span": 0, "runs": [], "error": ""}
        t0 = time.monotonic()
        try:
            root = prepare_repro_project(doc, scratch)
            ctx = context_from_repro(doc, root, os.path.join(scratch, "work"), run_id=run_id)
            for i in range(replays):
                r = range_session(ctx, f"rc-{name}-{i}", path, rng, orig)
                row["runs"].append(r)
                row["settled"] += int(bool(r.get("settled")) and not r.get("error"))
                if "whole_range" in r:
                    row["differs"] += int(not r["whole_range"]["equal"])
                    span = r.get("original_span", r["whole_range"])
                    row["differs_on_original_span"] += int(not span["equal"])
        except Exception as exc:  # noqa: BLE001
            row["error"] = f"{type(exc).__name__}: {exc}"[:400]
            logger.warning("%s %s: %s", campaign, name, row["error"])
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
            sweep_session_dirs(run_id)
            with contextlib.suppress(OSError):
                os.rmdir(os.path.dirname(scratch))
        row["seconds"] = round(time.monotonic() - t0, 1)
        logger.info("%s %s %s: differs %d/%d (original span %d), settled %d %s", cause, campaign, name,
                    row["differs"], replays, row["differs_on_original_span"], row["settled"], row["error"])
        rows.append(row)
    return rows


# ------------------------------------------------------------------ output
def write_rows(campaign: str, sub: str, rows: List[Dict[str, Any]]) -> str:
    out_dir = evidence_dir(campaign)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"root_cause_replays_{sub}.json")
    old = json.load(open(path, encoding="utf-8"))["rows"] if os.path.exists(path) else []
    key = lambda r: (r["gid"], r["variant"])  # noqa: E731
    merged = {key(r): r for r in old}
    merged.update({key(r): r for r in rows})
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"campaign": campaign, "subcommand": sub, "written": time.strftime("%Y-%m-%d %H:%M"),
                   "rows": list(merged.values())}, f, ensure_ascii=False, indent=1)
    return os.path.relpath(path, REPO)


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sub", choices=("race", "range"))
    ap.add_argument("--replays", type=int, default=3)
    ap.add_argument("--only", default="", help="groups (race) or causes (range) containing this text")
    args = ap.parse_args(argv)
    by_campaign: Dict[str, List[Dict[str, Any]]] = {}
    if args.sub == "race":
        for cause, campaign, gid in RACE_GROUPS:
            if args.only in gid or args.only == cause:
                by_campaign.setdefault(campaign, []).extend(race_group(cause, campaign, gid, args.replays))
    else:
        for cause, campaign, start in RANGE_GROUPS:
            if not args.only or args.only == cause:
                by_campaign.setdefault(campaign, []).extend(range_group(cause, campaign, start, args.replays))
    for campaign, rows in by_campaign.items():
        print(write_rows(campaign, args.sub, rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
