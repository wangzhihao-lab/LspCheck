"""Triage groups whose query sits on a contextual keyword (post hoc, review round 2).

The target tokenizer (scripts/lsptest/targets.py) skips reserved keywords but treats contextual
keywords that the language also accepts as identifiers as identifiers: TypeScript's from, of, get,
set, type and similar words, and Python's soft keywords. This script finds, for every triage group
of main_v1, the token under the representative's query position in the project file at its pinned
commit (the corpus clone under temp/corpus) and lists the groups whose token is such a keyword.

Writes data/lsptest/runs/main_v1/evidence/contextual_keywords.json.

Run line: python3 scripts/paper/evidence/contextual_keywords.py
"""

from __future__ import annotations

import csv
import json
import keyword
import os
import re
from typing import Any, Dict, List

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
RUN = os.path.join(REPO, "data", "lsptest", "runs", "main_v1")
JS_CONTEXTUAL = frozenset({"from", "of", "get", "set", "type", "module", "require", "global", "constructor",
                           "accessor", "override", "out", "assert", "using", "defer"})
PY_SOFT = frozenset(keyword.softkwlist)
IDENT = re.compile(r"[A-Za-z_$][\w$]*")


def token_at(line: str, character: int) -> str:
    return next((m.group(0) for m in IDENT.finditer(line) if m.start() <= character <= m.end()), "")


def main() -> int:
    with open(os.path.join(RUN, "triage", "triage.json"), encoding="utf-8") as f:
        groups = json.load(f)["groups"]
    with open(os.path.join(RUN, "triage", "decisions.csv"), encoding="utf-8") as f:
        verdicts = {r["group"]: r["verdict"] for r in csv.DictReader(f)}
    hits: List[Dict[str, Any]] = []
    checked = 0
    for g in groups:
        path = os.path.join(RUN, "triage", g["gid"], "repro.json")
        if not os.path.exists(path):
            path = os.path.join(RUN, "violations", g["representative"], "repro.json")
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        key = doc["key"]
        source = os.path.join(REPO, doc["project"]["ref"], key["path"])
        if key.get("line", -1) < 0 or not os.path.exists(source):
            continue
        with open(source, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        if key["line"] >= len(lines):
            continue
        checked += 1
        tok = token_at(lines[key["line"]], key["character"])
        lang = doc["project"].get("language", "")
        if (lang in ("typescript", "javascript") and tok in JS_CONTEXTUAL) or (lang == "python" and tok in PY_SOFT):
            hits.append({"group": g["gid"], "token": tok, "verdict": verdicts.get(g["gid"], "")})
    out = {"groups_checked": checked, "groups_total": len(groups), "groups": hits}
    with open(os.path.join(RUN, "evidence", "contextual_keywords.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
