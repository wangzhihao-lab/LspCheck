"""The author's match check of the benchmark detection table, as a CSV.

`export` writes data/lsptest/runs/<campaign>/detection_author.csv from detection.json: one row
per pre-only signature (case, title, url, oracle, signature, violation ids, author_match, note),
keeping the author_match values already there. `import` writes the CSV's author_match values
back into detection.json, where campaign_detect.py keeps them when it regenerates the table.
Nothing else in either file is changed.

Run line: python3 scripts/lsptest/detect_author.py bench_v1 export | import
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from campaign_store import paths_for, rel  # noqa: E402

COLUMNS = ("case", "title", "url", "oracle", "signature", "vids", "author_match", "note")
Key = Tuple[str, str, str]


def files(campaign: str) -> Tuple[str, str]:
    root = paths_for(campaign).root
    return os.path.join(root, "detection.json"), os.path.join(root, "detection_author.csv")


def read_csv(path: str) -> Dict[Key, Dict[str, str]]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        return {(r["case"], r["oracle"], r["signature"]): r for r in csv.DictReader(f)}


def export(campaign: str) -> int:
    json_path, csv_path = files(campaign)
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    earlier = read_csv(csv_path)
    rows: List[Dict[str, str]] = []
    for case in doc["cases"]:
        for p in case.get("pre_only", []):
            key = (case["case"], p["oracle"], p["signature"])
            old = earlier.get(key, {})
            rows.append({"case": case["case"], "title": case.get("title") or "", "url": case.get("url") or "",
                         "oracle": p["oracle"], "signature": p["signature"], "vids": " ".join(p.get("vids") or []),
                         "author_match": old.get("author_match") or p.get("author_match") or "",
                         "note": old.get("note", "")})
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"{rel(csv_path)}: {len(rows)} pre-only signature(s), {sum(bool(r['author_match']) for r in rows)} judged")
    return 0


def import_(campaign: str) -> int:
    json_path, csv_path = files(campaign)
    values = {k: r.get("author_match", "").strip() for k, r in read_csv(csv_path).items()}
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    n = 0
    for case in doc["cases"]:
        for p in case.get("pre_only", []):
            v = values.get((case["case"], p["oracle"], p["signature"]))
            if v is not None and v != p.get("author_match", ""):
                p["author_match"] = v
                n += 1
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False, sort_keys=True)
    print(f"{rel(json_path)}: {n} author_match value(s) updated")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("campaign")
    ap.add_argument("action", choices=("export", "import"))
    args = ap.parse_args()
    return export(args.campaign) if args.action == "export" else import_(args.campaign)


if __name__ == "__main__":
    raise SystemExit(main())
