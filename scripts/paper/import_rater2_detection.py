"""Write the second rater's exported judgements of the benchmark signatures into detection_rater2.csv.

The second rater's page (scripts/paper/detection_workbook.py <campaign> --rater2) exports
detection_rater2_judgements.json:
{"page": "detection-rater2", "campaign": ..., "order_seed": int, "exported_at": ISO time,
 "items": [{"n": int, "id": "<case>|<oracle>|<signature>", "case": ..., "signature": ...,
            "verdict": "yes" | "partial" | "no" | "", "note": ..., "judged_at": ISO time}]}
Text around the JSON object is ignored. The import checks, and refuses on any failure:
- page is detection-rater2 (exports of the author's page, "page": "detection", are refused) and the campaign
  is a campaign name;
- order_seed is the page's seed (detection_rater2.ORDER_SEED);
- the items correspond one to one to the pre-only signatures of the detected cases in detection.json: no
  unknown or repeated item, none missing, each with a verdict yes / partial / no; the id agrees with case and
  signature, and n is the item's number on the page built with that seed.
The target is data/lsptest/runs/<campaign>/detection_rater2.csv with the columns case, signature, verdict,
note, one row per signature, in detection.json order. It is written whole from the export; before an
existing, different file is overwritten a copy <name>.bak-YYYYmmdd-HHMMSS is written next to it. The script
refuses to write the author's files (detection_author.csv, decisions.csv) or the triage rater file
(rater2_decisions.csv), also through a link, and never opens them. --dry-run prints the summary only; --csv PATH
writes that file instead (tests, copies).

Run line: python3 scripts/paper/import_rater2_detection.py <detection_rater2_judgements.json or -> [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import logging
import os
import re
import shutil
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import detection_rater2 as dr

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FIELDS: Tuple[str, ...] = ("case", "signature", "verdict", "note")
VERDICTS: Tuple[str, ...] = dr.CHOICES
CAMPAIGN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
FORBIDDEN_NAMES: Tuple[str, ...] = ("detection_author.csv", "decisions.csv", "rater2_decisions.csv")
OUT_NAME = "detection_rater2.csv"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Item:
    n: int
    id: str
    case: str
    signature: str
    verdict: str
    note: str


@dataclass(frozen=True)
class Payload:
    campaign: str
    exported_at: str
    order_seed: Optional[int]
    items: Tuple[Item, ...]


@dataclass(frozen=True)
class Signature:
    """One pre-only signature of detection.json: its page key, case and signature, in detection.json order."""
    key: str
    case: str
    signature: str


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_payload(text: str) -> Payload:
    """The exported JSON; ValueError when it is not an export of the second rater's signature page."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the input")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"the input is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("the JSON is not an object")
    if data.get("page") != dr.PAGE:
        raise ValueError(f"page must be {dr.PAGE!r} (the second rater's signature page), not {data.get('page')!r}")
    campaign, raw = data.get("campaign"), data.get("items")
    if not isinstance(campaign, str) or not CAMPAIGN_RE.fullmatch(campaign) or ".." in campaign:
        raise ValueError(f"campaign {campaign!r} is not a campaign name")
    if not isinstance(raw, list):
        raise ValueError("items must be a list")
    items = tuple(Item(_int(x.get("n")), _text(x.get("id")), _text(x.get("case")), _text(x.get("signature")),
                       _text(x.get("verdict")), _text(x.get("note")))
                  if isinstance(x, dict) else Item(0, "", "", "", "", "") for x in raw)
    seed = data.get("order_seed")
    return Payload(campaign, _text(data.get("exported_at")), seed if isinstance(seed, int) and
                   not isinstance(seed, bool) else None, items)


def universe(doc: Dict[str, Any]) -> Tuple[List[Signature], Dict[str, int]]:
    """(the pre-only signatures of the detected cases in detection.json order, key -> item number on the page)."""
    cases = dr.sanitize(doc)
    sigs = [Signature(dr.item_id(str(c["case"]), p), str(c["case"]), str(p["signature"]))
            for c in cases for p in c["pre_only"]]
    return sigs, {key: i for i, key in enumerate(dr.order_of(cases, dr.ORDER_SEED), 1)}


def check(payload: Payload, sigs: Sequence[Signature], numbers: Dict[str, int]) -> List[str]:
    """Every reason to refuse the export (empty when it is complete and consistent)."""
    problems: List[str] = []
    if payload.order_seed != dr.ORDER_SEED:
        problems.append(f"order_seed is {payload.order_seed!r}, the page's seed is {dr.ORDER_SEED}")
    known = {s.key: s for s in sigs}
    seen: Dict[str, int] = {}
    for item in payload.items:
        label = f"#{item.n} {item.id or '(no id)'}"
        sig = known.get(item.id)
        if sig is None:
            problems.append(f"{label}: not a pre-only signature of detection.json")
            continue
        seen[item.id] = seen.get(item.id, 0) + 1
        if (item.case, item.signature) != (sig.case, sig.signature):
            problems.append(f"{label}: case/signature {item.case!r}/{item.signature!r} do not match the id")
        if item.n != numbers.get(item.id):
            problems.append(f"{label}: number {item.n} differs from the page's {numbers.get(item.id)}")
        if item.verdict not in VERDICTS:
            problems.append(f"{label}: verdict {item.verdict or '(none)'!r} is not one of {', '.join(VERDICTS)}")
    problems += [f"{key}: appears {k} times" for key, k in seen.items() if k > 1]
    missing = [s.key for s in sigs if s.key not in seen]
    if missing:
        problems.append(f"{len(missing)} of {len(sigs)} signature(s) missing: {', '.join(missing[:5])}"
                        f"{' …' if len(missing) > 5 else ''}")
    return problems


def render(payload: Payload, sigs: Sequence[Signature]) -> str:
    """The CSV text: one row per signature in detection.json order."""
    by_key = {item.id: item for item in payload.items}
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(FIELDS), lineterminator="\n")
    writer.writeheader()
    for s in sigs:
        item = by_key[s.key]
        writer.writerow({"case": s.case, "signature": s.signature, "verdict": item.verdict, "note": item.note})
    return buf.getvalue()


def guard(path: str) -> None:
    """Refuse the author's files and the triage rater file, also when path is a link to one of them."""
    names = {os.path.basename(path), os.path.basename(os.path.realpath(path))}
    hit = names & set(FORBIDDEN_NAMES)
    if hit:
        raise ValueError(f"refusing to write {path}: this script never writes {sorted(hit)[0]}")


def target_csv(campaign: str, repo: Optional[str] = None) -> str:
    return os.path.join(repo or REPO, "data", "lsptest", "runs", campaign, OUT_NAME)


def backup(path: str, now: dt.datetime) -> str:
    base = f"{path}.bak-{now:%Y%m%d-%H%M%S}"
    dest, k = base, 1
    while os.path.exists(dest):
        dest, k = f"{base}-{k}", k + 1
    shutil.copy2(path, dest)
    return dest


def run(payload: Payload, path: str, doc: Dict[str, Any], dry_run: bool = False,
        now: Optional[dt.datetime] = None) -> Tuple[Dict[str, int], str, bool]:
    """Check the payload against detection.json and write the CSV: (verdict counts, backup path or '', written).
    ValueError, with every problem listed, when the export is refused."""
    guard(path)
    sigs, numbers = universe(doc)
    problems = check(payload, sigs, numbers)
    if problems:
        raise ValueError("export refused:\n  " + "\n  ".join(problems))
    counts = {v: sum(1 for i in payload.items if i.verdict == v) for v in VERDICTS}
    text = render(payload, sigs)
    if dry_run:
        return counts, "", False
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            if f.read() == text:
                return counts, "", False
    saved = backup(path, now or dt.datetime.now()) if os.path.exists(path) else ""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return counts, saved, True


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="Write the second rater's signature judgements into detection_rater2.csv.")
    ap.add_argument("source", help="detection_rater2_judgements.json, or - for standard input")
    ap.add_argument("--dry-run", action="store_true", help="check and print the summary without writing anything")
    ap.add_argument("--csv", help="write this CSV instead of the campaign's detection_rater2.csv")
    ap.add_argument("--detection", help="detection.json to check against (default: the campaign's)")
    args = ap.parse_args(argv)
    try:
        if args.source == "-":
            text = sys.stdin.read()
        else:
            with open(args.source, "r", encoding="utf-8-sig") as f:
                text = f.read()
        payload = parse_payload(text)
        path = args.csv or target_csv(payload.campaign)
        detection = args.detection or os.path.join(REPO, "data", "lsptest", "runs", payload.campaign, "detection.json")
        with open(detection, "r", encoding="utf-8") as f:
            doc = json.load(f)
        counts, saved, wrote = run(payload, path, doc, args.dry_run)
    except (OSError, ValueError, KeyError) as e:
        logger.error("import failed: %s", e)
        return 2
    rel = os.path.relpath(path, REPO)
    print(f"second-rater signature judgements of {payload.campaign} exported {payload.exported_at or '?'} "
          f"(order seed {payload.order_seed}): {len(payload.items)} item(s) -> {path if rel.startswith('..') else rel}")
    print("verdicts: " + ", ".join(f"{v} {k}" for v, k in counts.items()) +
          (" (dry run: nothing written)" if args.dry_run else "" if wrote else " (file already up to date)"))
    if saved:
        rel_saved = os.path.relpath(saved, REPO)
        print(f"backup {saved if rel_saved.startswith('..') else rel_saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
