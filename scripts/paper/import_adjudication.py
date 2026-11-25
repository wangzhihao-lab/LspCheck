"""Write the discussion results of the adjudication page into the three consensus files.

Input: the JSON exported by data/lsptest/adjudication/adjudication.html (scripts/paper/adjudication_page.py):
{"page": "adjudication", "generated_at": ISO time, "items": [{"n", "kind": "group" | "signature", "campaign",
 "id", "verdict", "class", "followed": "author" | "rater2" | "both" | "", "unresolved": bool, "reason",
 "decided_at"}]}. Text around the JSON object is ignored.

Checks (any failure writes nothing, exit 2):
- every item is one of the disputed items, recomputed from the raw judgement files (read only): a group of
  main_v1 or main_v2 the author and the second rater judged differently, or a bench_v1 signature they
  answered differently; no item twice;
- the verdict is legal for the kind (bug / legitimate / tool-artifact; yes / no / partial); a class only for a
  legitimate (L1-L7) or tool-artifact (A1-A4) group; a reason is written;
- followed is author, rater2 or both, and agrees with the verdict (author: the author's original verdict;
  rater2: the second rater's; both: neither); it may be empty only for an unresolved item;
- an unresolved group is not a bug, an unresolved signature is no (plan/rater2_protocol.md);
- without --partial all disputed items are decided. With --partial, items without a verdict are skipped and
  the decided ones are merged into the existing consensus files (rows of the export replace rows of the same
  item; rows that are not disputed items are dropped with a warning).

Writes data/lsptest/runs/main_v1/triage/consensus.csv and main_v2/triage/consensus.csv (group, verdict, class,
followed, unresolved, reason, date) and data/lsptest/runs/bench_v1/detection_consensus.csv (case, signature,
verdict, followed, unresolved, reason, date); unresolved is yes or no, date the day of decided_at (UTC). A
file that would change is first copied to <name>.bak-YYYYmmdd-HHMMSS. The script refuses to write
decisions.csv, verdict_reasons.csv, rater2_decisions.csv, detection_author.csv and detection_rater2.csv, also
through a symbolic link. --dry-run prints the summary only.

Run line: python3 scripts/paper/import_adjudication.py <adjudication_results.json or -> [--dry-run] [--partial]
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

import adjudication_page as ap

PROTECTED: Tuple[str, ...] = ("decisions.csv", "verdict_reasons.csv", "rater2_decisions.csv", "detection_author.csv",
                              "detection_rater2.csv")
GROUP_FIELDS: Tuple[str, ...] = ("group", "verdict", "class", "followed", "unresolved", "reason", "date")
SIGNATURE_FIELDS: Tuple[str, ...] = ("case", "signature", "verdict", "followed", "unresolved", "reason", "date")
CLASSES: Dict[str, Tuple[str, ...]] = {"legitimate": tuple(f"L{i}" for i in range(1, 8)),
                                       "tool-artifact": tuple(f"A{i}" for i in range(1, 5))}
UNRESOLVED_OK: Dict[str, Tuple[str, ...]] = {"group": ("legitimate", "tool-artifact"), "signature": ("no",)}
FOLLOWED: Tuple[str, ...] = tuple(f for f, _ in ap.FOLLOWED)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Decision:
    """One exported item."""
    n: int
    kind: str
    campaign: str
    id: str
    verdict: str
    cls: str
    followed: str
    unresolved: bool
    reason: str
    decided_at: str

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.campaign}:{self.id}"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def parse_payload(text: str) -> Tuple[str, List[Decision]]:
    """(generated_at, the items) of an export of the adjudication page; ValueError otherwise."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the input")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"the input is not valid JSON: {e}") from e
    if not isinstance(data, dict) or data.get("page") != ap.PAGE:
        raise ValueError(f"page must be {ap.PAGE!r}, not {data.get('page') if isinstance(data, dict) else None!r}")
    raw = data.get("items")
    if not isinstance(raw, list):
        raise ValueError("items must be a list")
    out: List[Decision] = []
    for x in raw:
        if not isinstance(x, dict):
            raise ValueError(f"an item is not an object: {x!r}")
        n = x.get("n")
        out.append(Decision(n if isinstance(n, int) and not isinstance(n, bool) else 0, _text(x.get("kind")),
                            _text(x.get("campaign")), _text(x.get("id")), _text(x.get("verdict")),
                            _text(x.get("class")), _text(x.get("followed")), x.get("unresolved") is True,
                            _text(x.get("reason")), _text(x.get("decided_at"))))
    return _text(data.get("generated_at") or data.get("exported_at")), out


def check(decisions: Sequence[Decision], disputes: Sequence[ap.Dispute],
          partial: bool = False) -> Tuple[List[Decision], List[str], List[str]]:
    """(the decided items to write, errors, notes). Any error means nothing may be written."""
    by_key = {d.key: d for d in disputes}
    errors: List[str] = []
    notes: List[str] = []
    keep: List[Decision] = []
    seen: Dict[str, int] = {}
    for x in decisions:
        label = f"#{x.n} {x.kind} {x.campaign} {x.id or '(no id)'}"
        d = by_key.get(x.key)
        if d is None:
            errors.append(f"{label}: not an item the two judged differently")
            continue
        if x.key in seen:
            errors.append(f"{label}: appears more than once")
            continue
        seen[x.key] = x.n
        if not x.verdict:
            (notes if partial else errors).append(f"{label}: no verdict yet" + ("; skipped" if partial else ""))
            continue
        if x.verdict not in ap.CHOICES[x.kind]:
            errors.append(f"{label}: invalid verdict {x.verdict!r}")
            continue
        if x.cls and (x.kind != "group" or x.cls not in CLASSES.get(x.verdict, ())):
            errors.append(f"{label}: class {x.cls!r} does not fit verdict {x.verdict!r}")
        if not x.reason:
            errors.append(f"{label}: no reason")
        if x.followed and x.followed not in FOLLOWED:
            errors.append(f"{label}: followed must be one of {FOLLOWED}, not {x.followed!r}")
        elif not x.followed and not x.unresolved:
            errors.append(f"{label}: followed is empty (allowed only for an unresolved item)")
        elif x.followed == "author" and x.verdict != d.author.verdict:
            errors.append(f"{label}: followed author, but {x.verdict} is not the author's {d.author.verdict}")
        elif x.followed == "rater2" and x.verdict != d.rater2.verdict:
            errors.append(f"{label}: followed rater2, but {x.verdict} is not the second rater's {d.rater2.verdict}")
        elif x.followed == "both" and x.verdict in (d.author.verdict, d.rater2.verdict):
            errors.append(f"{label}: followed both, but {x.verdict} is one side's original verdict")
        if x.unresolved and x.verdict not in UNRESOLVED_OK[x.kind]:
            errors.append(f"{label}: unresolved, so the verdict must be one of {UNRESOLVED_OK[x.kind]}, not "
                          f"{x.verdict!r}")
        keep.append(x)
    if not partial:
        missing = [d.key for d in disputes if d.key not in {x.key for x in keep}]
        undecided = [d for d in missing if d not in seen]
        if undecided:
            errors.append(f"{len(undecided)} disputed item(s) missing from the export (use --partial for an "
                          f"unfinished discussion): {', '.join(undecided[:5])}{' …' if len(undecided) > 5 else ''}")
    return keep, errors, notes


def day(x: Decision, generated_at: str) -> str:
    for stamp in (x.decided_at, generated_at):
        if DATE_RE.match(stamp):
            return stamp[:10]
    return dt.date.today().isoformat()


def row_of(x: Decision, generated_at: str) -> Dict[str, str]:
    common = {"verdict": x.verdict, "followed": x.followed, "unresolved": "yes" if x.unresolved else "no",
              "reason": x.reason, "date": day(x, generated_at)}
    if x.kind == "group":
        return {"group": x.id, "class": x.cls, **common}
    case, signature = x.id.split("|", 1)
    return {"case": case, "signature": signature, **common}


def targets(repo: Optional[str] = None) -> Dict[str, str]:
    """campaign -> its consensus file."""
    runs = ap.runs_dir(repo)
    out = {c: os.path.join(runs, c, "triage", "consensus.csv") for c in ap.TRIAGE_CAMPAIGNS}
    out[ap.BENCH_CAMPAIGN] = os.path.join(runs, ap.BENCH_CAMPAIGN, "detection_consensus.csv")
    return out


def guard(path: str) -> None:
    """Refuse the raw judgement files, by name or through a symbolic link."""
    names = {os.path.basename(path), os.path.basename(os.path.realpath(path))}
    hit = sorted(names & set(PROTECTED))
    if hit:
        raise ValueError(f"refusing to write {path}: {hit[0]} holds original judgements and is never written here")


def row_key(campaign: str, row: Mapping[str, str]) -> str:
    if campaign == ap.BENCH_CAMPAIGN:
        return f"signature:{campaign}:{row.get('case', '')}|{row.get('signature', '')}"
    return f"group:{campaign}:{row.get('group', '')}"


def render(campaign: str, rows: Sequence[Mapping[str, str]]) -> str:
    fields = SIGNATURE_FIELDS if campaign == ap.BENCH_CAMPAIGN else GROUP_FIELDS
    order = sorted(rows, key=lambda r: tuple(r.get(f, "") for f in fields[:2]))
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    writer.writerows({f: r.get(f, "") for f in fields} for r in order)
    return buf.getvalue()


def plan(keep: Sequence[Decision], disputes: Sequence[ap.Dispute], generated_at: str, partial: bool,
         repo: Optional[str] = None) -> Tuple[Dict[str, str], List[str]]:
    """path -> new text for every consensus file to write, and warnings."""
    disputed = {d.key for d in disputes}
    warnings: List[str] = []
    out: Dict[str, str] = {}
    for campaign, path in targets(repo).items():
        guard(path)
        mine = [x for x in keep if x.campaign == campaign]
        rows: Dict[str, Dict[str, str]] = {}
        if partial:
            for r in ap.csv_rows(path):
                k = row_key(campaign, r)
                if k in disputed:
                    rows[k] = r
                else:
                    warnings.append(f"{os.path.basename(path)} ({campaign}): dropped a row that is not a disputed "
                                    f"item: {k}")
        for x in mine:
            rows[x.key] = row_of(x, generated_at)
        if partial and not rows and not os.path.exists(path):
            continue
        out[path] = render(campaign, list(rows.values()))
    return out, warnings


def backup(path: str, now: dt.datetime) -> str:
    base = f"{path}.bak-{now:%Y%m%d-%H%M%S}"
    dest, k = base, 1
    while os.path.exists(dest):
        dest, k = f"{base}-{k}", k + 1
    shutil.copy2(path, dest)
    return dest


def write(texts: Mapping[str, str], now: Optional[dt.datetime] = None) -> List[Tuple[str, str, bool]]:
    """Write each file whose text changes, after a backup: (path, backup or '', written)."""
    done: List[Tuple[str, str, bool]] = []
    for path, text in texts.items():
        guard(path)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                if f.read() == text:
                    done.append((path, "", False))
                    continue
        saved = backup(path, now or dt.datetime.now()) if os.path.exists(path) else ""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        done.append((path, saved, True))
    return done


def run(text: str, repo: Optional[str] = None, dry_run: bool = False, partial: bool = False,
        now: Optional[dt.datetime] = None) -> Tuple[List[str], List[Tuple[str, str, bool]], List[Decision]]:
    """Check the export and write the consensus files: (report lines, writes, the items written).
    ValueError when the export fails a check; nothing is written then."""
    generated_at, decisions = parse_payload(text)
    disputes = ap.all_disputes(repo)
    keep, errors, notes = check(decisions, disputes, partial)
    if errors:
        raise ValueError("the export fails the checks; nothing written:\n  " + "\n  ".join(errors))
    texts, warnings = plan(keep, disputes, generated_at, partial, repo)
    lines = [f"export generated {generated_at or '?'}: {len(decisions)} item(s), {len(keep)} decided, "
             f"{len(disputes)} disputed in all" + (" (dry run: nothing written)" if dry_run else "")]
    for campaign in ap.TRIAGE_CAMPAIGNS + (ap.BENCH_CAMPAIGN,):
        mine = [x for x in keep if x.campaign == campaign]
        verdicts: Dict[str, int] = {}
        followed: Dict[str, int] = {}
        for x in mine:
            verdicts[x.verdict] = verdicts.get(x.verdict, 0) + 1
            followed[x.followed or "-"] = followed.get(x.followed or "-", 0) + 1
        total = sum(1 for d in disputes if d.campaign == campaign)
        lines.append(f"  {campaign}: {len(mine)}/{total} decided; verdicts {verdicts}; followed {followed}; "
                     f"unresolved {sum(1 for x in mine if x.unresolved)}")
    lines += [f"  note {n}" for n in notes] + [f"  warning {w}" for w in warnings]
    done: List[Tuple[str, str, bool]] = []
    if not dry_run:
        done = write(texts, now)
        for path, saved, wrote in done:
            lines.append(f"  {'wrote' if wrote else 'unchanged'} {path}" + (f" (backup {saved})" if saved else ""))
    else:
        lines += [f"  would write {p}" for p in texts]
    return lines, done, keep


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Write the adjudication page's results into the consensus files.")
    parser.add_argument("source", help="adjudication_results.json, or - for standard input")
    parser.add_argument("--dry-run", action="store_true", help="check and print the summary, write nothing")
    parser.add_argument("--partial", action="store_true", help="accept an unfinished discussion and merge it")
    parser.add_argument("--repo", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.source == "-":
            text = sys.stdin.read()
        else:
            with open(args.source, "r", encoding="utf-8-sig") as f:
                text = f.read()
        lines, _, _ = run(text, args.repo, args.dry_run, args.partial)
    except (OSError, ValueError, KeyError) as e:
        logger.error("import failed: %s", e)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
