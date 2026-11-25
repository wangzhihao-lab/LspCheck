"""Report for the r4_edits / r6_crossimpl pilot.

`write_report` adds a verdict to every candidate of data/lsptest/pilot/r4_r6.json and
writes data/lsptest/pilot/r4_r6.md: the pilot table, which servers support which R4
sub-checks (quick fixes with edits, formatting, organize imports, completion resolve;
corpus projects and synthetic fixtures), the seeded quick fixes (mutation jobs: per
server and per mutation kind), the R6 intended-difference source, and each candidate
with its replays, verdict and evidence. Verdicts come from pilot_r4_r6_rules.py.

Run line: python3 scripts/lsptest/pilot_r4_r6.py --report-only
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from pilot_r4_r6_rules import LIMITS, TOOL_ARTIFACTS, classify, labels

# ------------------------------------------------------------------ support matrix
def _support(job: Dict[str, Any]) -> Dict[str, Any]:
    for note in job["result"].get("notes", []):
        if note.startswith("support "):
            return json.loads(note[len("support "):])
    return {}


def _counts(row: Dict[str, int]) -> str:
    return ", ".join(f"{k} {v}" for k, v in sorted(row.items()))


def _cell(row: Dict[str, int], good: Tuple[str, ...], empty: str) -> str:
    """yes/no by whether any outcome starts with one of `good`, followed by the outcome counts."""
    if not row:
        return empty
    return ("yes" if any(k.startswith(good) for k in row) else "no") + f" ({_counts(row)})"


def _quickfix_cell(sup: Dict[str, Any]) -> str:
    offered = sup.get("quickfix-offered", {})
    diags = sum(offered.values())
    if sup.get("quickfix"):
        return _cell(sup["quickfix"], ("edit", "resolve", "command"), "") + f"; {diags} diagnostics tried"
    return f"not exercised ({diags} diagnostics, none offered a quick fix)" if diags else "not exercised (no diagnostics)"


def support_rows(data: Dict[str, Any]) -> List[str]:
    rows = []
    for name, job in sorted(data.get("jobs", {}).items()):
        if job["oracle"] != "r4_edits":
            continue
        sup = _support(job)
        caps = sup.get("capabilities", {})
        fmt = _cell(sup.get("format", {}), ("edits", "no-op"), "not exercised") if caps.get("formatting") \
            else "no (no formatting provider)"
        resolve = ("yes" if caps.get("completionResolve") else "no") + \
            f" ({sup.get('completion', {}).get('resolved', 0)} items resolved)"
        rows.append(f"| {job['server']} | {'fixture' if job.get('fixture') else job['project']} | {_quickfix_cell(sup)} | "
                    f"{fmt} | {_cell(sup.get('organize', {}), ('action:', 'command'), 'not exercised')} | {resolve} |")
    return rows


KIND_NAMES = {"M1": "M1 remove import", "M2": "M2 misspell a use", "M3": "M3 drop argument / member",
              "M4": "M4 unused binding"}


def _seeded(job: Dict[str, Any]) -> bool:
    return "mutation" in (job.get("checks") or [])


def mutation_rows(data: Dict[str, Any], n: int) -> Tuple[List[str], List[str]]:
    """Per server: mutations, created diagnostics, quick fixes offered/applied, candidates; and
    per mutation kind: applied / creating diagnostics / targeted diagnostics with quick fixes."""
    per_server, per_kind = [], []
    for name, job in sorted(data.get("jobs", {}).items()):
        if not _seeded(job):
            continue
        c, sup = job["result"].get("compared", {}), _support(job).get("mutation", {})
        full = sum(1 for cand in job["candidates"] if n and cand["confirmed"] == f"{n}/{n}")
        verdicts: Dict[str, int] = {}
        for cand in job["candidates"]:
            verdicts[cand["verdict"]] = verdicts.get(cand["verdict"], 0) + 1
        per_server.append(f"| {job['server']} | {job['project']} | {c.get('mutations', 0)} | "
                          f"{c.get('mutationDiagnostics', 0)} | {c.get('mutationFixesOffered', 0)} | "
                          f"{c.get('mutationFixesApplied', 0)} | {len(job['candidates'])} | {full} | "
                          f"{_counts(verdicts) or '-'} |")
        per_kind.append(f"| {job['server']} | " + " | ".join(
            f"{sup.get(k + ':applied', 0)} / {sup.get(k + ':created-diagnostics', 0)} / {sup.get(k + ':fixes-offered', 0)}"
            for k in KIND_NAMES) + " |")
    return per_server, per_kind


# ------------------------------------------------------------------ report
def _fmt(x: Any, limit: int = 160) -> str:
    s = json.dumps(x, ensure_ascii=False, default=str)
    return (s if len(s) <= limit else s[:limit] + "...").replace("|", "\\|")


def write_report(data: Dict[str, Any], json_path: str, md_path: str) -> None:
    jobs = data.get("jobs", {})
    for name, job in jobs.items():
        for c in job["candidates"]:
            v = classify(name, c, job.get("project", ""))
            c["verdict"], c["evidence"] = v.label, v.evidence
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, default=str)
    n = int(data.get("replays_per_candidate") or 0)
    lines = [f"# Pilot of r4_edits and r6_crossimpl ({data.get('generated', '?')})", "",
             f"Each candidate was replayed {n} times from fresh sessions; a replay counts as reproduced when it "
             "settled, showed the same difference shape and its fresh control was stable (codes per replay: "
             "S/s settled, R/r reproduced, C/c control stable). Sessions = sessions of the run itself (R4: the "
             "running session and fresh confirmations; R6: two fresh pairs); each replay adds 2-3 (R4) or 4 (R6). "
             "Seconds = the run without replays, on a shared machine under heavy load.", "",
             f"| oracle | server | project | cases | sessions | seconds | candidates | reproduced {n}/{n} | verdicts |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, job in sorted(jobs.items()):
        r = job["result"]
        full = sum(1 for c in job["candidates"] if n and c["confirmed"] == f"{n}/{n}")
        verdicts: Dict[str, int] = {}
        for c in job["candidates"]:
            verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1
        proj = ("fixture " if job.get("fixture") else "seeded " if _seeded(job) else "") + job["project"]
        lines.append(f"| {job['oracle']} | {job['server']} | {proj} | {r['cases']} | {r['sessions']} | "
                     f"{r['seconds']} | {len(job['candidates'])} | {full} | {_counts(verdicts) or '-'} |")
    lines += ["", "## R4 sub-check support per server", "",
              "Outcome counts per sub-check. Quick fixes: edit / resolve / command = the fix's edit came with the "
              "action / from codeAction/resolve / from a followed edit-only command; no-edit:<via> = none; "
              "'not exercised' = no diagnostic of the target files offered a quick fix. Formatting: edits / no-op "
              "= the server formats (no-op: the file already is formatted); error:<code> = it does not. Organize "
              "imports: action:<via> = source.organizeImports code action, command = server command, none = not "
              "offered, no-op = offered without changes. Completion resolve: the resolveProvider capability and "
              "the items resolved.", "",
              "| server | project | quick fixes with edits | formatting | organize imports | completion resolve |",
              "|---|---|---|---|---|---|"] + support_rows(data)
    per_server, per_kind = mutation_rows(data, n)
    if per_server:
        lines += ["", "## R4 seeded quick fixes (mutation jobs)", "",
                  "Clean code has few fixable diagnostics, so each case plants one with a seeded mutation (M1 remove "
                  "an import, M2 misspell a use, M3 drop the last argument of a call or a member of a literal, M4 "
                  "insert an unused binding), applied as a change op in the running session. Only diagnostics the "
                  "mutation created are targeted (up to 2 per mutation, errors first; up to 3 quick fixes each). A "
                  "finding: the targeted diagnostic persists at the mapped range, the error count of the edited "
                  "files exceeds the count before the mutation, or the fixed text has a new parse error. The "
                  "violation's ops are open + mutation + fix; each case records both error counts and the errors "
                  "the fix itself introduced.", "",
                  f"| server | project | mutations applied | diagnostics created | quick fixes offered | quick fixes "
                  f"applied | candidates | reproduced {n}/{n} | verdicts |", "|---|---|---|---|---|---|---|---|---|"]
        lines += per_server
        lines += ["", "Per mutation kind: mutations applied / of them creating diagnostics / targeted diagnostics "
                  "that offered quick fixes.", "", "| server | " + " | ".join(KIND_NAMES.values()) + " |",
                  "|---|---|---|---|---|"] + per_kind
    src = data.get("intended_source")
    lines += ["", "## R6 intended-difference source", ""]
    lines.append(f"- {src['url']} (sha256 {src['sha256']}, fetched {src['fetched']}); re-check at pilot time: "
                 f"{src.get('check', {}).get('status', 'not run')}" if src else "- intended-difference source unavailable")
    lines += ["", "## Run notes", ""]
    for name, job in sorted(jobs.items()):
        lines += [f"- {name}: {n}" for n in job["result"].get("notes", []) if not n.startswith("support ")]
    lines += ["", "## Candidates", ""]
    for name, job in sorted(jobs.items()):
        for i, c in enumerate(job["candidates"], 1):
            v = c["violation"]
            detail = json.loads(v["detail"])
            k = v["key"]
            case = detail.get("case", {})
            codes = " ".join(("S" if r["settled"] else "s") + ("R" if r["reproduced"] else "r")
                             + ("C" if r["control_stable"] else "c") for r in c["replays"])
            lines += [f"### {name} #{i}: `{v['signature']}`", "",
                      f"- key: {k['method']} {k['path']}:{k['line'] + 1}:{k['character'] + 1} {k['extra']}".rstrip(),
                      f"- note: {detail.get('note', '')[:600]}"]
            if "only_reference" in case and isinstance(v["expected"], list) and len(json.dumps(v["expected"])) > 160:
                lines += [f"- only in the reference ({len(set(map(str, v['expected'])) - set(map(str, v['actual'])))}): "
                          f"{_fmt(labels(case.get('only_reference')), 300)}",
                          f"- only in the server under test ({len(set(map(str, v['actual'])) - set(map(str, v['expected'])))}): "
                          f"{_fmt(labels(case.get('only_test')), 300)}"]
                if case.get("sources_only_reference") is not None:
                    lines.append(f"- modules of those suggestions: reference {_fmt(case.get('sources_only_reference'), 300)}; "
                                 f"server under test {_fmt(case.get('sources_only_test'), 300)}")
            else:
                lines += [f"- expected: {_fmt(v['expected'])}", f"- actual: {_fmt(v['actual'])}"]
            lines += [f"- case kind: {case.get('kind', case.get('method', ''))}; ops: {len(v['ops'])}",
                      f"- replays: confirmed {c['confirmed']} ({codes})",
                      f"- verdict: **{c['verdict']}** — {c['evidence']}", ""]
    lines += ["## Tool artifacts found and fixed during the pilot", ""] + [f"- {n}" for n in TOOL_ARTIFACTS]
    lines += ["", "## Known limits", ""] + [f"- {n}" for n in LIMITS]
    failed = data.get("failed_jobs") or {}
    if failed:
        lines += ["", "## Failed jobs", ""] + [f"- {k}: {v}" for k, v in sorted(failed.items())]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


__all__ = ["mutation_rows", "support_rows", "write_report"]
