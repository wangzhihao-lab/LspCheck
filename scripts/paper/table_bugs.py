"""Main-text table of the distinct bugs of both current-release campaigns: server, relation, symptom, independent
evidence, the oldest release they reproduce on, whether they reproduce on the newest releases, and the upstream report.

The symptom lines are fixed text (below); every other column comes from the data: the server and the relations from
the cause's groups in both root-cause tables (runs/main_v1 and runs/main_v2, triage/root_causes.csv; the relation is
the -r<N>- of the group id), the evidence level from evidence/evidence_summary.csv of main_v1 (C1-C11) and
evidence/evidence_summary_v2.csv of main_v2 (C12-C35), the oldest reproducing release (Since) from the lifecycle of
the cause's representative group (data/lsptest/figure_data.json, key lifecycle_cur; numbers_release_cur.py), the
newest-release replay (Newest) from sweep/<NEWEST>/results.jsonl of both campaigns (every group of the cause; a group
without a row is not judged, and the cell is -- until every group has one), the gopls development head from
sweep/<HEAD>/results.jsonl of main_v1 (read with numbers_figures.replay_state), and the report (C1-C10: our report and
the response) from main_v1/upstream/feedback.csv.
Writes paper/tables/bugs.tex (a table* environment in scriptsize, label tab:bugs).

Run line: python3 scripts/paper/table_bugs.py
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
from typing import Dict, List, Mapping, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from numbers_figures import HEAD, NEWEST, replay_state  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RUNS = os.path.join(REPO, "data", "lsptest", "runs")
CAMPAIGNS = ("main_v1", "main_v2")
RUN = os.path.join(RUNS, "main_v1")  # the upstream reports and the gopls development head
EVIDENCE = (("main_v1", "evidence_summary.csv"), ("main_v2", "evidence_summary_v2.csv"))
FIGURE_DATA = os.path.join(REPO, "data", "lsptest", "figure_data.json")
OUT = os.path.join(REPO, "paper", "tables", "bugs.tex")
logger = logging.getLogger("table_bugs")

SERVER = {"ts6": "TS 6 + tsls", "ts7": "TS 7", "gopls": "gopls", "rust-analyzer": "r-a", "pyright": "pyright"}
SYMPTOM: Dict[str, str] = {
    "C1": "Answers on a file and its importers are lost after it is moved away and back outside the editor",
    "C2": "Wrong diagnostics after two requests sent right after opening a file",
    "C3": "A code action resolved after an edit changes the row above its target",
    "C4": "A completion item resolved after an edit gets a range that ends before it starts",
    "C5": "``Create variable'' declares an untyped literal where the use needs another type",
    "C6": "``Create function'' writes a parameter list that does not parse",
    "C7": "``Remove variable'' keeps an assignment to the removed variable",
    "C8": "Definitions in a route-handler signature point into the attribute's expansion",
    "C9": "References miss uses in a package's test files until a file of the package is edited",
    "C10": "References at an import shrink after an unsaved edit elsewhere",
    "C11": "``Add missing properties'' fills a \\lsp{Record} property with \\lsp{undefined}",
    "C12": "After a configuration change, code actions repeat a diagnostic's quick fix",
    "C13": "Changed root-module files hide or alter a nested module's import error",
    "C14": "Completion in a test file is empty after \\lsp{go.mod} is broken and restored",
    "C15": "``Delete var'' keeps the import that only the deleted initializer used",
    "C16": "Positions in comments and raw strings ignore carriage returns",
    "C17": "References on a package name in an import fail with an internal assertion",
    "C18": "Inferred types of a helper's results change after edits or requests in other files",
    "C19": "Hover loses a library docstring after a file is renamed and restored",
    "C20": "References miss uses in quoted annotations of files not yet opened",
    "C21": "Signature help shows an \\lsp{Unknown} return type after another file is opened",
    "C22": "An auto-import completion adds a private name to the \\lsp{\\_\\_future\\_\\_} import",
    "C25": "The server stops pushing its own diagnostics once the workspace has loaded",
    "C26": "Range semantic tokens drop the unsafe and macro modifiers of full tokens",
    "C27": "Completing a macro name offers \\lsp{Err(())} and keeps the macro's \\lsp{!(...)}",
    "C28": "Attribute completion inserts a second argument list",
    "C29": "``Add .to\\_owned() here'' breaks a struct-literal shorthand field",
    "C30": "The order in which files are opened changes the import fixes offered",
    "C31": "An inlay hint shows \\lsp{any} after a rename restored within a workspace change",
    "C32": "``Convert to async function'' keeps a non-global \\lsp{Promise} return type",
    "C33": "``Fix all detected spelling errors'' renames JSX component tags to \\lsp{eval}",
    "C34": "``Change spelling'' renames only the opening tag of a JSX element",
    "C35": "``Change spelling'' replaces a name with the variable being declared",
}
TRACKER = {"golang/go": "go", "rust-lang/rust-analyzer": "r-a", "microsoft/TypeScript": "TS",
           "typescript-language-server/typescript-language-server": "tsls"}
STATUS = {"fix-planned": "fix planned", "confirmed": "confirmed", "investigating": "investigating", "fixed": "fixed",
          "info-requested": "info asked", "cause-confirmed": "cause found",
          "disputed": "disputed", "no-reply": "no reply", "not-reported": "--"}
DEFINITION = {  # the two classes the main-text note explains; Appendix N3 defines all (runs/main_v1/upstream/README.md)
    "cause-confirmed": "Cause found: a maintainer reproduced the bug and traced its cause, without planning a fix.",
    "disputed": "Disputed: called expected behavior or a client error by a maintainer.",
}


# Layout: scriptsize (7 pt), a tabular* of \textwidth (516 pt) whose column gaps stretch (\extracolsep{\fill}).
# Measured in this table's fonts on 2026-11-21, the seven narrow columns are at most 203.4 pt wide (with a Newest
# cell "19 of 20", a Rel. cell "R1, R3" and the widest Report, "go#81811: investigating"); with seven gaps of
# 2 x 2.5 pt that leaves 277.6 pt, so "What goes wrong" gets 274 pt and every symptom line (the longest, C1, is
# 273.1 pt) fits on one line.
TABCOLSEP_PT = 2.5
SYMPTOM_WIDTH = "274pt"


def rows_by(path: str, key: str) -> Dict[str, Dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return {r[key]: r for r in csv.DictReader(f)}


def cause_key(cause: str) -> int:
    return int(cause[1:])


def since(cell: Mapping[str, object]) -> str:
    """Month of the oldest release the bug reproduces on (the release itself is in Appendix N, Table N1)."""
    released = str(cell["oldest_released"] or "")
    return released[:7] if cell["oldest_reproduced"] else "--"


def bug_groups() -> Tuple[Dict[str, List[Tuple[str, str]]], Dict[str, str]]:
    """Cause -> its (campaign, group) in both root-cause tables (table order), and cause -> server.

    Raises:
        ValueError: when the two tables give a cause different servers.
    """
    groups: Dict[str, List[Tuple[str, str]]] = {}
    server: Dict[str, str] = {}
    for run in CAMPAIGNS:
        with open(os.path.join(RUNS, run, "triage", "root_causes.csv"), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                groups.setdefault(r["cause"], []).append((run, r["group"]))
                if server.setdefault(r["cause"], r["server"]) != r["server"]:
                    raise ValueError(f"cause {r['cause']}: server {server[r['cause']]} and {r['server']}")
    return groups, server


def evidence_rows() -> Dict[str, Dict[str, str]]:
    """Cause -> its row of the two evidence summaries."""
    out: Dict[str, Dict[str, str]] = {}
    for run, name in EVIDENCE:
        for cause, row in rows_by(os.path.join(RUNS, run, "evidence", name), "cause").items():
            if cause in out:
                raise ValueError(f"cause {cause} is in both evidence summaries")
            out[cause] = row
    return out


def replay_states(run: str, label: str) -> Dict[str, str]:
    """Group -> replay state of the last row of each group in a campaign's replay label ({} when it has not run)."""
    path = os.path.join(RUNS, run, "sweep", label, "results.jsonl")
    if not os.path.exists(path):
        return {}
    out: Dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for r in map(json.loads, (ln for ln in f if ln.strip())):
            out[r["gid"]] = replay_state(r)
    return out


def newest_cell(states: List[str]) -> str:
    """yes / no / k of n over a cause's groups; -- when a group has no judged replay (or the cause has none)."""
    hit = sum(1 for st in states if st in ("reproduced", "partly"))
    if not states or any(st == "n/a" for st in states):
        return "--"
    return "yes" if hit == len(states) else ("no" if hit == 0 else f"{hit} of {len(states)}")


def report_cell(up: Optional[Mapping[str, str]]) -> str:
    """'go\\#81808: fixed' for a filed report (C1-C10), else --."""
    if not up or not up.get("number"):
        return "--"
    return f"{TRACKER.get(up['tracker'], up['tracker'])}\\#{up['number']}: {STATUS[up['status']]}"


def table_rows() -> List[Dict[str, str]]:
    """One row per cause (cause order) with the cells of the table, plus the newest-release and head states."""
    groups, server = bug_groups()
    missing = sorted(set(groups) ^ set(SYMPTOM), key=cause_key)
    if missing:
        raise ValueError(f"root causes and symptom lines differ: {missing}")
    evidence = evidence_rows()
    upstream = rows_by(os.path.join(RUN, "upstream", "feedback.csv"), "cause")
    with open(FIGURE_DATA, encoding="utf-8") as f:
        life = json.load(f)["lifecycle_cur"]
    newest = {run: replay_states(run, NEWEST) for run in CAMPAIGNS}
    head = replay_states("main_v1", HEAD)
    out = []
    for cause in sorted(SYMPTOM, key=cause_key):
        rels = sorted({m.group(1) for _, g in groups[cause] for m in [re.search(r"-r(\d)-", g)] if m})
        states = [newest[run].get(g, "n/a") for run, g in groups[cause]]
        # the sweep says nothing about a bug whose representative did not reproduce on the tested release there
        tested = [c for c in life[cause]["cells"] if "campaign" in c["roles"]]
        control = bool(tested) and tested[0]["state"] in ("reproduced", "partly")
        out.append({"cause": cause, "server": SERVER[server[cause]], "relations": ", ".join("R" + r for r in rels),
                    "symptom": SYMPTOM[cause], "check": evidence[cause]["independent"],
                    "since": since(life[cause]) if control else "--", "control": "yes" if control else "no",
                    "newest": newest_cell(states) if control else "--", "report": report_cell(upstream.get(cause)),
                    "head": ",".join(head[g] for run, g in groups[cause] if run == "main_v1" and g in head)})
    return out


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rows = table_rows()
    upstream = rows_by(os.path.join(RUN, "upstream", "feedback.csv"), "cause")
    as_of = max(r["as_of"] for r in upstream.values())  # = release.upstream.as_of
    no_control = [r["cause"] for r in rows if r["control"] == "no"]
    pending = [r["cause"] for r in rows if r["newest"] == "--" and r["control"] == "yes"]
    if pending:
        logger.warning("Newest is -- for %s (a group without a judged replay)", ", ".join(pending))
    lines = ["% Generated by scripts/paper/table_bugs.py; do not edit.",
             r"\begin{table*}[t]", r"\centering",
             rf"\caption{{RQ3: The {len(rows)} Distinct Bugs}}",
             r"\label{tab:bugs}", r"\scriptsize", rf"\setlength{{\tabcolsep}}{{{TABCOLSEP_PT:g}pt}}",
             rf"\begin{{tabular*}}{{\textwidth}}{{@{{\extracolsep{{\fill}}}}llc>{{\raggedright\arraybackslash}}"
             rf"p{{{SYMPTOM_WIDTH}}}llll@{{}}}}", r"\toprule",
             r"Bug & Server & Rel. & What goes wrong & Check & Since & Newest & Report \\", r"\midrule"]
    for r in rows:
        lines.append(f"{r['cause']} & {r['server']} & {r['relations']} & {r['symptom']} & {r['check']} & "
                     f"{r['since']} & {r['newest']} & {r['report']} \\\\")
    present = {u["status"] for u in upstream.values() if u["number"]}
    defined = " ".join(d for s, d in DEFINITION.items() if s in present)
    head_gone = [r["cause"] for r in rows if r["head"] and all(st == "not-reproduced" for st in r["head"].split(","))
                 and r["newest"] != "no"]
    with open(os.path.join(RUN, "sweep", NEWEST, "releases.json"), encoding="utf-8") as f:
        newest_date = json.load(f)["as_of"]
    head_note = (f" {' and '.join(head_gone)} no longer reproduce{'s' if len(head_gone) == 1 else ''} on the gopls "
                 f"development head." if head_gone else "")
    dash_note = (f" A dash in both: {', '.join(no_control)} did not reproduce in these replays even on the tested release."
                 if no_control else "")
    numbers = sorted(int(r["cause"][1:]) for r in rows)
    unused = [f"C{i}" for i in range(1, numbers[-1] + 1) if i not in numbers]
    unused_note = (f" Numbers {' and '.join(unused)} are unused (\\appx{{G}})." if unused else "")
    note = (rf"Check: independent evidence (Section~\ref{{sec:eval-rq3}}). Since: month of the oldest release tried on "
            rf"which the bug reproduces (\appx{{N}}). Newest: whether its groups reproduce on the newest release of "
            rf"{newest_date}, or how many do.{head_note}{dash_note} Report: for C1--C10, our report and the response as of "
            rf"{as_of} (classes in \appx{{N}}): go = golang/go, r-a = rust-analyzer, tsls = typescript-language-server, "
            rf"TS = TypeScript. {defined} C11 was not reported (TypeScript~6 no longer receives such fixes, and "
            rf"TypeScript~7 lacks the quick fix), and the other bugs were judged after the reports were filed.{unused_note}")
    lines += [r"\bottomrule", r"\end{tabular*}", rf"\tablenote{{{note}}}", r"\end{table*}", ""]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("wrote %s (%d bugs)", os.path.relpath(OUT, REPO), len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
