"""Appendix H of the supplemental material: the reduced reproduction of every distinct bug of both corpora.

For each cause in triage/root_causes.csv of data/lsptest/runs/main_v1 and main_v2, the member group (of either
campaign) with the fewest operations after reduction represents the cause (ties: the first campaign, then the group
id; the group of Fig. 1 represents C1). Its report.md gives the minimal protocol steps and its repro.json the expected
(reference) and actual (tested) answers, printed as the first differing lines of both; the replay command names the
campaign the group belongs to. Output: paper/supplement/tables/H_cases.tex (verbatim blocks, lines wrapped at 96
characters, one-column page).

Run line: python3 scripts/paper/appendix_cases.py
"""

from __future__ import annotations

import csv
import difflib
import json
import logging
import os
import re
import textwrap
from typing import Dict, List, Mapping, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RUNS = os.path.join(REPO, "data", "lsptest", "runs")
CAMPAIGNS = ("main_v1", "main_v2")
CORPUS = {"main_v1": "first", "main_v2": "second"}
OUT = os.path.join(REPO, "paper", "supplement", "tables", "H_cases.tex")
WIDTH = 96
MAX_DIFF = 16

logger = logging.getLogger(__name__)


EXAMPLE_GROUP = "ts6-r1-references-lost-h5-d24ca6"  # the motivating example of Section II and Fig. 1
QUICKFIX_ERRORS = ("the expected answer lists the errors in the edited files before the mutation, the actual answer "
                   "those after the fix, confirmed in a fresh session on the edited content; errors are counted "
                   "wherever they are, so their ranges print as 0.")


def tex(text: str) -> str:
    """Escape plain text for LaTeX (outside verbatim)."""
    repl = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(repl.get(c, c) for c in text)


HOME = re.compile(r"/(?:Users|home)/[^/\s\"']+")  # local home directories never reach the paper


def wrap(lines: List[str]) -> List[str]:
    out: List[str] = []
    for line in lines:
        line = HOME.sub("~", line)
        out += textwrap.wrap(line, WIDTH, subsequent_indent="    ", break_long_words=True,
                             break_on_hyphens=False, drop_whitespace=False) or [""]
    return out


def steps(report: str, extra: str = "") -> List[str]:
    """The report's minimal steps; for a quick fix judged by its errors (R4), the last step says what the
    two answers are, since they are not a fresh session's answer and the tested one."""
    m = re.search(r"(?ms)^## Minimal steps[^\n]*\n(.*?)(?=^## )", report)
    lines = [ln.rstrip().replace("`", "") for ln in (m.group(1) if m else "").strip().splitlines() if ln.strip()]
    if "quickfix-errors:" in extra and lines:
        lines[-1] = lines[-1].replace("compare with the same query in a fresh session on the same content (expected).",
                                      QUICKFIX_ERRORS)
    return lines


def answer_diff(expected: object, actual: object) -> List[str]:
    a = json.dumps(expected, indent=1, sort_keys=True, ensure_ascii=False).splitlines()
    b = json.dumps(actual, indent=1, sort_keys=True, ensure_ascii=False).splitlines()
    lines = [ln for ln in difflib.unified_diff(a, b, "expected (reference answer)", "actual (tested answer)",
                                               lineterm="", n=1)]
    if len(lines) > MAX_DIFF:
        lines = lines[:MAX_DIFF] + [f"... {len(lines) - MAX_DIFF} more diff lines in the group's report"]
    return lines


def triage(run: str) -> str:
    return os.path.join(RUNS, run, "triage")


def causes() -> Dict[str, Tuple[Mapping[str, str], List[Tuple[str, str]]]]:
    """Cause -> (its row in the first table that lists it, its (campaign, group) in both tables)."""
    out: Dict[str, Tuple[Mapping[str, str], List[Tuple[str, str]]]] = {}
    for run in CAMPAIGNS:
        with open(os.path.join(triage(run), "root_causes.csv"), "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                out.setdefault(row["cause"], (row, []))[1].append((run, row["group"]))
    return out


def reduced_ops() -> Dict[Tuple[str, str], int]:
    """(campaign, group) -> operations after reduction (triage.json; 0 when not recorded, as before)."""
    out: Dict[Tuple[str, str], int] = {}
    for run in CAMPAIGNS:
        with open(os.path.join(triage(run), "triage.json"), "r", encoding="utf-8") as f:
            out.update({(run, g["gid"]): g.get("ops_after") or 0 for g in json.load(f)["groups"]})
    return out


def representative(groups: List[Tuple[str, str]], ops: Mapping[Tuple[str, str], int]) -> Tuple[str, str]:
    """The group of Fig. 1 when it belongs to the cause, else the member with the fewest operations (ties: campaign
    order, then group id)."""
    if ("main_v1", EXAMPLE_GROUP) in groups:
        return "main_v1", EXAMPLE_GROUP
    return min(groups, key=lambda rg: (ops.get(rg, 0), CAMPAIGNS.index(rg[0]), rg[1]))


def merged(groups: List[Tuple[str, str]]) -> str:
    """'13 (8 in the first corpus, 5 in the second)' or '2 (second corpus)'."""
    per = {run: sum(1 for r, _ in groups if r == run) for run in CAMPAIGNS}
    if all(per.values()):
        return f"{len(groups)} ({per['main_v1']} in the first corpus, {per['main_v2']} in the second)"
    return f"{len(groups)} ({next(CORPUS[r] for r, n in per.items() if n)} corpus)"


def render() -> str:
    parts = ["% Generated by scripts/paper/appendix_cases.py; do not edit."]
    ops = reduced_ops()
    for cause, (row, groups) in sorted(causes().items(), key=lambda kv: int(kv[0].lstrip("C"))):
        run, rep = representative(groups, ops)
        with open(os.path.join(triage(run), rep, "report.md"), "r", encoding="utf-8") as f:
            report = f.read()
        with open(os.path.join(triage(run), rep, "repro.json"), "r", encoding="utf-8") as f:
            doc = json.load(f)
        block = wrap(["Minimal steps:"] + steps(report, str(doc.get("key", {}).get("extra", ""))) + ["", "Answers:"]
                     + answer_diff(doc.get("expected"), doc.get("actual"))
                     + ["", f"Replay: python3 scripts/lsptest/repro_violation.py data/lsptest/runs/{run}/triage/{rep}/repro.json"])
        parts += [f"\\subsection*{{{cause}: {tex(row['trigger'])} ({tex(row['server'])})}}",
                  f"{tex(row['description'])}. Groups merged: {merged(groups)}; representative: \\texttt{{{tex(rep)}}} "
                  f"({CORPUS[run]} corpus).",
                  "{\\footnotesize", "\\begin{verbatim}", *block, "\\end{verbatim}", "}"]
    return "\n".join(parts) + "\n"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    text = render()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
