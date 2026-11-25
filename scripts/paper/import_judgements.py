"""Write the judgements copied from a judging page into the author's CSV.

The judging pages (scripts/paper/triage_workbook.py, scripts/paper/detection_workbook.py) export
{"page": "triage" | "detection", "campaign": ..., "exported_at": ISO time,
 "items": [{"n": int, "id": ..., "choice": ..., "note": ..., "minutes": int}]}
(only items with a choice or a note). Text around the JSON object (a leading sentence, code
fences) is ignored.
- triage: id = group name; target data/lsptest/runs/<campaign>/triage/decisions.csv; verdict =
  choice, maintainer_response = note, minutes_spent = minutes (only into an empty cell: the first
  measured time is kept), date = today (only when the row gets a new choice).
- detection: id = "<case>|<oracle>|<signature>"; target data/lsptest/runs/<campaign>/
  detection_author.csv (bench_v1); author_match = choice, note = note; matched by case, oracle
  and signature.
An empty choice or note never clears a cell. Unknown ids and invalid choices are reported and
skipped. The CSV keeps its columns, row order, line ends and all other values; before the first
change a timestamped copy (<name>.bak-YYYYmmdd-HHMMSS) is written next to it. --dry-run prints
the summary and writes nothing; --csv PATH writes that file instead of the campaign's CSV.

Run line: python3 scripts/paper/import_judgements.py <json file or -> [--dry-run]
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CHOICES: Dict[str, Tuple[str, ...]] = {"triage": ("bug", "legitimate", "tool-artifact"),
                                       "detection": ("yes", "no", "partial")}
CAMPAIGN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Target:
    """The CSV columns of one page kind: the row key and the cells an item writes."""
    key: Tuple[str, ...]
    choice: str
    note: str
    minutes: str = ""
    date: str = ""


TARGETS: Dict[str, Target] = {
    "triage": Target(("group",), "verdict", "maintainer_response", "minutes_spent", "date"),
    "detection": Target(("case", "oracle", "signature"), "author_match", "note")}


@dataclass(frozen=True)
class Item:
    n: int
    id: str
    choice: str
    note: str
    minutes: float


@dataclass(frozen=True)
class Payload:
    page: str
    campaign: str
    exported_at: str
    items: Tuple[Item, ...]


@dataclass(frozen=True)
class Table:
    fields: Tuple[str, ...]
    rows: Tuple[Mapping[str, str], ...]
    newline: str
    bom: bool


@dataclass(frozen=True)
class Summary:
    updated: Tuple[str, ...]
    unchanged: Tuple[str, ...]
    skipped: Tuple[str, ...]
    replaced: Tuple[str, ...]  # an earlier, different choice overwritten


def as_minutes(value: Any) -> float:
    """Minutes with one decimal (the page measures the time since the previous judgement)."""
    if isinstance(value, bool):
        return 0.0
    try:
        return round(float(value), 1)
    except (TypeError, ValueError, OverflowError):
        return 0.0


def as_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(round(float(value)))
    except (TypeError, ValueError, OverflowError):
        return 0


def parse_payload(text: str) -> Payload:
    """The exported JSON; ValueError when it is not a judging-page export."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the input")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"the input is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("the JSON is not an object")
    page, campaign, raw = data.get("page"), data.get("campaign"), data.get("items")
    if page not in CHOICES:
        raise ValueError(f"page must be one of {sorted(CHOICES)}, not {page!r}")
    if not isinstance(campaign, str) or not CAMPAIGN_RE.fullmatch(campaign) or ".." in campaign:
        raise ValueError(f"campaign {campaign!r} is not a campaign name")
    if not isinstance(raw, list):
        raise ValueError("items must be a list")
    items = tuple(Item(n=as_int(x.get("n")), id=x["id"] if isinstance(x.get("id"), str) else "",
                       choice=str(x.get("choice") or "").strip(), note=str(x.get("note") or "").strip(),
                       minutes=max(0.0, as_minutes(x.get("minutes")))) if isinstance(x, dict) else Item(0, "", "", "", 0.0)
                  for x in raw)
    return Payload(page, campaign, str(data.get("exported_at") or ""), items)


def target_csv(payload: Payload, repo: str = REPO) -> str:
    run = os.path.join(repo, "data", "lsptest", "runs", payload.campaign)
    return os.path.join(run, "triage", "decisions.csv") if payload.page == "triage" else \
        os.path.join(run, "detection_author.csv")


def read_table(path: str) -> Table:
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8-sig")
    end = text.find("\n")
    newline = "\r\n" if end > 0 and text[end - 1] == "\r" else "\n"
    reader = csv.DictReader(io.StringIO(text, newline=""))
    fields = tuple(reader.fieldnames or ())
    rows: List[Mapping[str, str]] = []
    for r in reader:
        if None in r:
            raise ValueError(f"{path}: a row has more cells than the header")
        rows.append({k: r.get(k) or "" for k in fields})
    return Table(fields, tuple(rows), newline, raw.startswith(b"\xef\xbb\xbf"))


def write_table(path: str, table: Table, rows: Sequence[Mapping[str, str]]) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(table.fields), lineterminator=table.newline)
    writer.writeheader()
    writer.writerows(rows)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(("﻿" if table.bom else "") + buf.getvalue())


def backup(path: str, now: dt.datetime) -> str:
    base = f"{path}.bak-{now:%Y%m%d-%H%M%S}"
    dest, k = base, 1
    while os.path.exists(dest):
        dest, k = f"{base}-{k}", k + 1
    shutil.copy2(path, dest)
    return dest


def row_key(page: str, item_id: str) -> Tuple[str, ...]:
    if page == "triage":
        return (item_id,)
    parts = item_id.split("|", 2)
    return tuple(parts) if len(parts) == 3 else ()


def apply(payload: Payload, table: Table, today: str) -> Tuple[List[Dict[str, str]], Summary]:
    """The rows after the payload (copies; the table is not changed) and what happened to each item."""
    target = TARGETS[payload.page]
    needed = [c for c in (*target.key, target.choice, target.note, target.minutes, target.date) if c]
    missing = [c for c in needed if c not in table.fields]
    if missing:
        raise ValueError(f"the CSV has no column(s) {missing}")
    rows = [dict(r) for r in table.rows]
    index = {tuple(r[c] for c in target.key): i for i, r in enumerate(rows)}
    updated: List[str] = []
    unchanged: List[str] = []
    skipped: List[str] = []
    replaced: List[str] = []
    seen = set()
    for item in payload.items:
        label = f"#{item.n} {item.id or '(no id)'}"
        i = index.get(row_key(payload.page, item.id)) if item.id else None
        if i is None:
            skipped.append(f"{label}: unknown id")
            continue
        if item.choice and item.choice not in CHOICES[payload.page]:
            skipped.append(f"{label}: invalid choice {item.choice!r}")
            continue
        if item.id in seen:
            logger.warning("%s appears more than once; the later entry wins", label)
        seen.add(item.id)
        old, new = rows[i], dict(rows[i])
        before = old[target.choice].strip()
        if item.choice:
            new[target.choice] = item.choice
            if before != item.choice and target.date:
                new[target.date] = today
            if before and before != item.choice:
                replaced.append(f"{label}: {before} -> {item.choice}")
            if target.minutes and item.minutes > 0 and not old[target.minutes].strip():
                new[target.minutes] = f"{item.minutes:g}"
        if item.note:
            new[target.note] = item.note
        (updated if new != old else unchanged).append(label)
        rows[i] = new
    return rows, Summary(tuple(updated), tuple(unchanged), tuple(skipped), tuple(replaced))


def run(payload: Payload, path: str, dry_run: bool = False,
        now: Optional[dt.datetime] = None) -> Tuple[Summary, str]:
    """Apply the payload to the CSV at path; returns the summary and the backup path ('' if none)."""
    now = now or dt.datetime.now()
    table = read_table(path)
    rows, summary = apply(payload, table, now.date().isoformat())
    if not summary.updated or dry_run:
        return summary, ""
    saved = backup(path, now)
    write_table(path, table, rows)
    return summary, saved


def shown(path: str) -> str:
    rel = os.path.relpath(path, REPO)
    return path if rel.startswith("..") else rel


def report(payload: Payload, summary: Summary, path: str, saved: str, dry_run: bool) -> str:
    lines = [f"{payload.page} judgements of {payload.campaign} exported {payload.exported_at or '?'}: "
             f"{len(payload.items)} item(s) -> {shown(path)}",
             f"updated {len(summary.updated)}, unchanged {len(summary.unchanged)}, skipped {len(summary.skipped)}"
             + (" (dry run: nothing written)" if dry_run else "")]
    lines += [f"  skipped {s}" for s in summary.skipped]
    lines += [f"  replaced an earlier choice {s}" for s in summary.replaced]
    lines += [f"  backup {shown(saved)}"] if saved else []
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="Write the judgements copied from a judging page into the CSV.")
    ap.add_argument("source", help="the pasted JSON: a file, or - for standard input")
    ap.add_argument("--dry-run", action="store_true", help="print the summary without writing anything")
    ap.add_argument("--csv", help="write this CSV instead of the campaign's (tests, copies)")
    args = ap.parse_args(argv)
    try:
        if args.source == "-":
            text = sys.stdin.read()
        else:
            with open(args.source, "r", encoding="utf-8-sig") as f:
                text = f.read()
        payload = parse_payload(text)
        path = args.csv or target_csv(payload)
        summary, saved = run(payload, path, args.dry_run)
    except (OSError, ValueError) as e:
        logger.error("import failed: %s", e)
        return 2
    print(report(payload, summary, path, saved, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
