"""Write the second rater's exported judgements into rater2_decisions.csv.

The second rater's page (scripts/paper/triage_workbook.py --rater2) exports rater2_judgements.json:
{"page": "triage-rater2", "campaign": ..., "order_seed": int, "exported_at": ISO time,
 "items": [{"n": int, "id": group, "verdict": "bug" | "legitimate" | "tool-artifact" | "",
            "class": "L1".."L7" | "A1".."A4" | "", "note": ..., "judged_at": ISO time}]}
(only items with a verdict, a class or a note). Text around the JSON object is ignored. Exports of the
author's page ("page": "triage") are refused.

The target is data/lsptest/runs/<campaign>/triage/rater2_decisions.csv with the columns group, verdict,
class, note, judged_at, one row per group, sorted by group. By default the export is merged into the
existing file: an item replaces its group's row, groups the export does not mention keep their row (and
are listed, since the page exports everything it holds). --replace writes exactly the export. Unknown
groups and invalid verdicts are skipped; a class that does not fit the verdict (L* needs legitimate,
A* needs tool-artifact, none for bug) is dropped with a warning. Before an existing file is overwritten a
copy <name>.bak-YYYYmmdd-HHMMSS is written next to it. The script refuses to write any file named
decisions.csv; it never opens the author's decisions.csv. --dry-run prints the summary only; --csv PATH
writes that file instead (tests, copies).

Run line: python3 scripts/paper/import_rater2.py <rater2_judgements.json or -> [--dry-run] [--replace]
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
PAGE = "triage-rater2"
FIELDS: Tuple[str, ...] = ("group", "verdict", "class", "note", "judged_at")
VERDICTS: Tuple[str, ...] = ("bug", "legitimate", "tool-artifact")
CLASSES: Dict[str, Tuple[str, ...]] = {"legitimate": tuple(f"L{i}" for i in range(1, 8)),
                                       "tool-artifact": tuple(f"A{i}" for i in range(1, 5)), "bug": ()}
CAMPAIGN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
FORBIDDEN_NAME = "decisions.csv"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Item:
    n: int
    id: str
    verdict: str
    cls: str
    note: str
    judged_at: str


@dataclass(frozen=True)
class Payload:
    campaign: str
    exported_at: str
    order_seed: Optional[int]
    items: Tuple[Item, ...]


@dataclass(frozen=True)
class Summary:
    written: Tuple[str, ...]      # groups whose row is new or changed
    unchanged: Tuple[str, ...]
    skipped: Tuple[str, ...]      # items not written, with the reason
    warnings: Tuple[str, ...]     # items written with a dropped class, groups kept from the old file
    changed_verdicts: Tuple[str, ...]


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
    """The exported JSON; ValueError when it is not an export of the second rater's page."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the input")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"the input is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("the JSON is not an object")
    if data.get("page") != PAGE:
        raise ValueError(f"page must be {PAGE!r} (the second rater's page), not {data.get('page')!r}")
    campaign, raw = data.get("campaign"), data.get("items")
    if not isinstance(campaign, str) or not CAMPAIGN_RE.fullmatch(campaign) or ".." in campaign:
        raise ValueError(f"campaign {campaign!r} is not a campaign name")
    if not isinstance(raw, list):
        raise ValueError("items must be a list")
    items = tuple(Item(_int(x.get("n")), _text(x.get("id")), _text(x.get("verdict")), _text(x.get("class")),
                       _text(x.get("note")), _text(x.get("judged_at")))
                  if isinstance(x, dict) else Item(0, "", "", "", "", "") for x in raw)
    seed = data.get("order_seed")
    return Payload(campaign, _text(data.get("exported_at")), seed if isinstance(seed, int) else None, items)


def known_groups(campaign: str, repo: Optional[str] = None) -> Tuple[str, ...]:
    """The campaign's group names from its triage.json."""
    path = os.path.join(repo or REPO, "data", "lsptest", "runs", campaign, "triage", "triage.json")
    with open(path, "r", encoding="utf-8") as f:
        return tuple(g["gid"] for g in json.load(f)["groups"])


def target_csv(campaign: str, repo: Optional[str] = None) -> str:
    return os.path.join(repo or REPO, "data", "lsptest", "runs", campaign, "triage", "rater2_decisions.csv")


def guard(path: str) -> None:
    """Refuse the author's file: any path named decisions.csv."""
    if os.path.basename(os.path.realpath(path)) == FORBIDDEN_NAME or os.path.basename(path) == FORBIDDEN_NAME:
        raise ValueError(f"refusing to write {path}: this script never writes the author's {FORBIDDEN_NAME}")


def read_rows(path: str) -> Dict[str, Dict[str, str]]:
    """group -> row of an existing rater2_decisions.csv ({} when the file does not exist)."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in FIELDS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path} has no column(s) {missing}")
        return {r["group"]: {c: r.get(c) or "" for c in FIELDS} for r in reader if (r.get("group") or "").strip()}


def merge(payload: Payload, old: Mapping[str, Mapping[str, str]], groups: Sequence[str],
          replace: bool = False) -> Tuple[Dict[str, Dict[str, str]], Summary]:
    """The rows after the payload (old is not changed) and what happened to each item."""
    known = set(groups)
    rows: Dict[str, Dict[str, str]] = {} if replace else {g: dict(r) for g, r in old.items()}
    written: List[str] = []
    unchanged: List[str] = []
    skipped: List[str] = []
    warnings: List[str] = []
    changed: List[str] = []
    seen: set = set()
    for item in payload.items:
        label = f"#{item.n} {item.id or '(no id)'}"
        if item.id not in known:
            skipped.append(f"{label}: unknown group")
            continue
        if item.verdict and item.verdict not in VERDICTS:
            skipped.append(f"{label}: invalid verdict {item.verdict!r}")
            continue
        if item.id in seen:
            warnings.append(f"{label}: appears more than once; the later entry wins")
        seen.add(item.id)
        cls = item.cls
        if cls and cls not in CLASSES.get(item.verdict, ()):
            warnings.append(f"{label}: class {cls!r} does not fit verdict {item.verdict or '(none)'!r}; dropped")
            cls = ""
        new = {"group": item.id, "verdict": item.verdict, "class": cls, "note": item.note,
               "judged_at": item.judged_at if item.verdict else ""}
        before = old.get(item.id)
        if before and before.get("verdict") and before.get("verdict") != item.verdict:
            changed.append(f"{label}: {before.get('verdict')} -> {item.verdict or '(none)'}")
        (unchanged if before == new else written).append(label)
        rows[item.id] = new
    if not replace:
        kept = sorted(set(old) - seen)
        if kept:
            warnings.append(f"{len(kept)} group(s) in the existing file are not in this export and keep their "
                            f"row: {', '.join(kept[:5])}{' …' if len(kept) > 5 else ''}")
    elif old:
        dropped = sorted(set(old) - seen)
        if dropped:
            warnings.append(f"--replace drops {len(dropped)} row(s) the export does not have: "
                            f"{', '.join(dropped[:5])}{' …' if len(dropped) > 5 else ''}")
    return rows, Summary(tuple(written), tuple(unchanged), tuple(skipped), tuple(warnings), tuple(changed))


def render(rows: Mapping[str, Mapping[str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(FIELDS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows[g] for g in sorted(rows))
    return buf.getvalue()


def backup(path: str, now: dt.datetime) -> str:
    base = f"{path}.bak-{now:%Y%m%d-%H%M%S}"
    dest, k = base, 1
    while os.path.exists(dest):
        dest, k = f"{base}-{k}", k + 1
    shutil.copy2(path, dest)
    return dest


def run(payload: Payload, path: str, groups: Sequence[str], dry_run: bool = False, replace: bool = False,
        now: Optional[dt.datetime] = None) -> Tuple[Summary, str, bool]:
    """Merge the payload into the CSV at path: (summary, backup path or '', whether the file was written)."""
    guard(path)
    old = read_rows(path)
    rows, summary = merge(payload, old, groups, replace)
    text = render(rows)
    if dry_run:
        return summary, "", False
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            if f.read() == text:
                return summary, "", False
    saved = backup(path, now or dt.datetime.now()) if os.path.exists(path) else ""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return summary, saved, True


def report(payload: Payload, summary: Summary, path: str, saved: str, wrote: bool, dry_run: bool) -> str:
    rel = os.path.relpath(path, REPO)
    lines = [f"rater-2 judgements of {payload.campaign} exported {payload.exported_at or '?'} "
             f"(order seed {payload.order_seed}): {len(payload.items)} item(s) -> {path if rel.startswith('..') else rel}",
             f"new or changed {len(summary.written)}, unchanged {len(summary.unchanged)}, skipped {len(summary.skipped)}"
             + (" (dry run: nothing written)" if dry_run else "" if wrote else " (file already up to date)")]
    lines += [f"  skipped {s}" for s in summary.skipped]
    lines += [f"  verdict changed {s}" for s in summary.changed_verdicts]
    lines += [f"  warning {s}" for s in summary.warnings]
    lines += [f"  backup {os.path.relpath(saved, REPO)}"] if saved else []
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="Write the second rater's exported judgements into rater2_decisions.csv.")
    ap.add_argument("source", help="rater2_judgements.json, or - for standard input")
    ap.add_argument("--dry-run", action="store_true", help="print the summary without writing anything")
    ap.add_argument("--replace", action="store_true", help="write exactly the export instead of merging")
    ap.add_argument("--csv", help="write this CSV instead of the campaign's rater2_decisions.csv")
    args = ap.parse_args(argv)
    try:
        if args.source == "-":
            text = sys.stdin.read()
        else:
            with open(args.source, "r", encoding="utf-8-sig") as f:
                text = f.read()
        payload = parse_payload(text)
        path = args.csv or target_csv(payload.campaign)
        summary, saved, wrote = run(payload, path, known_groups(payload.campaign), args.dry_run, args.replace)
    except (OSError, ValueError, KeyError) as e:
        logger.error("import failed: %s", e)
        return 2
    print(report(payload, summary, path, saved, wrote, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
