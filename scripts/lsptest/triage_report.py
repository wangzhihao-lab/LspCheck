"""Report drafts, the triage index and the decisions template (plan/tool_design_v1.md section 11.2).

render_report() writes one group's report.md: title, server and version, the relation that was
violated, minimal steps in LSP terms (from the reduced ops or the oracle's case), expected vs
actual, environment, the standalone replay command, the reduction, the group's members, the
possibly related issues found by the search (for the author to check) and a server log excerpt.
Nothing here is filed anywhere. write_decisions() keeps triage/decisions.csv: one row per group
with the author's verdict (bug / legitimate / tool-artifact), known issue link, report link,
maintainer response, date and minutes spent; existing rows are never changed, new groups are
appended. render_index() lists every group.

Run line: imported by triage.py and tests/test_triage.py; not run directly.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from campaign_store import REPO, op_text  # noqa: E402
from histories import FAMILY_DESCRIPTIONS  # noqa: E402
from model import Op, QueryKey  # noqa: E402
from queries import LSP_METHODS  # noqa: E402
from triage_group import Group  # noqa: E402

DECISION_COLUMNS = ("group", "verdict", "known_issue_link", "report_link", "maintainer_response", "date",
                    "minutes_spent")
VERDICTS = ("bug", "legitimate", "tool-artifact")
RELATIONS: Dict[str, str] = {
    "r0_crash": "A request on an unmodified project must not fail with an internal error, kill the server or time "
                "out; here it does so in two independent fresh sessions (R0 crash check).",
    "r1_history": "History independence (R1): after a sequence of edits that returns the documents to content C, "
                  "every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each "
                  "other on this query; the session that went through the history does not.",
    "r2_handles": "Handle validity (R2): a code-action or completion handle minted before an edit and resolved after "
                  "it must fail, return no edit, or return the same edit as a fresh handle for the same item.",
    "r3_routes": "Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, "
                 "semanticTokens range and full, documentHighlight and references, definition at a symbol and at its "
                 "references) must agree.",
    "r4_edits": "Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; "
                "formatting and organize imports applied twice must be no-ops; inserting a completion must not "
                "introduce a syntax error.",
    "r5_transforms": "Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF "
                     "line ends, the final newline or an inline comment do not change the program, so the answers "
                     "must agree after mapping positions.",
    "r6_crossimpl": "Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 "
                    "(typescript-language-server) answer the same query on the same project; the difference is not "
                    "among the documented intended differences.",
}


def display(text: str) -> str:
    """Local install paths shortened for a report: <servers>/ for the pinned server builds,
    repository-relative paths, ~ for the home directory."""
    for prefix, short in ((os.path.join(REPO, "temp", "lsp_servers") + os.sep, "<servers>/"), (REPO + os.sep, ""),
                          (os.path.expanduser("~") + os.sep, "~/")):
        text = text.replace(prefix, short)
    return text


def show(x: Any, limit: int = 1500) -> str:
    s = display(json.dumps(x, ensure_ascii=False, default=str, indent=1))
    return s if len(s) <= limit else s[:limit] + f"\n... ({len(s)} characters)"


def open_after(ops: Sequence[Op]) -> List[str]:
    """Documents open after the ops."""
    now: List[str] = []
    for op in ops:
        if op.kind == "open" and op.path not in now:
            now.append(op.path)
        elif op.kind == "close" and op.path in now:
            now.remove(op.path)
        elif op.kind == "fs_rename" and op.path in now:
            now[now.index(op.path)] = op.new_path
    return now


def position(line: int, ch: int) -> str:
    return f"line {line + 1}, column {ch + 1} (LSP position {{line: {line}, character: {ch}}})"


def symptom(shape: str) -> str:
    method, _, tail = shape.partition(":")
    if "->error:" in tail:
        code = tail.split("->error:")[1]
        return {"-32603": "fails with an internal error (-32603)", "timeout": "times out", "dead": "kills the server",
                "transport": "loses the connection"}.get(code, f"fails with error {code}")
    if tail.startswith("error:"):
        return f"no longer fails with {tail.split('->')[0]}"
    kind, _, codes = tail.partition(":")
    what = {"lost": "loses its answer", "gained": "gains an answer", "text": "shows a different text",
            "range": "changes its range", "changed": "changes its answer", "key-lost": "is not answered",
            "missing": f"misses {codes or 'entries'}", "extra": f"adds {codes or 'entries'}",
            "moved": f"moves {codes or 'entries'}", "message": f"rewords {codes or 'entries'}"}
    return what.get(kind, tail or "differs")


def title(g: Group, version: str) -> str:
    fam, s = g.family, symptom(g.shape)
    tails: Dict[str, Callable[[], str]] = {
        "r0_crash": lambda: f"{g.method} {s} in a fresh session",
        "r1_history": lambda: f"{g.method} {s} after {FAMILY_DESCRIPTIONS.get(fam, 'an edit history').lower()}",
        "r2_handles": lambda: f"a stale {fam} handle resolves to a different edit after an intervening edit",
        "r3_routes": lambda: f"{g.method}: two routes to the same fact disagree",
        "r4_edits": lambda: f"{fam} edit is not valid ({g.shape})",
        "r5_transforms": lambda: f"{g.method} {s} after transformation {fam}",
        "r6_crossimpl": lambda: f"{g.method} differs from TypeScript 6",
    }
    return f"[{g.server_kind} {version}] " + tails.get(g.oracle, lambda: f"{g.method} {s}")()


# ------------------------------------------------------------------ steps in LSP terms
def op_step(op: Op) -> str:
    notif = {"open": "textDocument/didOpen", "change": "textDocument/didChange", "close": "textDocument/didClose",
             "save": "textDocument/didSave (the buffer is written to disk)",
             "set_config": "workspace/didChangeConfiguration", "fs_write": "file written on disk, then "
             "workspace/didChangeWatchedFiles", "fs_rename": "workspace/willRenameFiles, didClose, rename on disk, "
             "workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path",
             "wait": "wait", "request": "request"}.get(op.kind, op.kind)
    return f"{notif}: `{op_text(op)}`"


def query_step(key: QueryKey) -> str:
    lsp = LSP_METHODS.get(key.method, key.method)
    at = position(key.line, key.character) if key.line >= 0 else "for the whole file"
    extra = f" ({key.extra})" if key.extra else ""
    return f"`{lsp}` on `{key.path}` {at}{extra}"


def _at(p: Sequence[Any]) -> str:
    return position(int(p[0]), int(p[1]))


def r2_step(case: Mapping[str, Any], key: QueryKey) -> str:
    sh = case.get("shift") or {}
    if case.get("sub") == "tokens":
        return (f"`textDocument/semanticTokens/full` on `{case.get('path')}` (keep its resultId); didChange: insert "
                f"`{json.dumps(sh.get('text', ''))}` at line {sh.get('line', 0) + 1}; `semanticTokens/full/delta` "
                "against that resultId, applied to the first answer, must equal a new `semanticTokens/full`.")
    kind = "code action" if case.get("sub") == "codeAction" else "completion item"
    return (f"didOpen `{case.get('path')}`; request {kind}s at {_at(case.get('where') or [0, 0])} and resolve them; "
            f"didChange: insert `{json.dumps(sh.get('text', ''))}` at line {sh.get('line', 0) + 1} ({sh.get('variant')}); "
            f"wait until idle; resolve the OLD {kind} `{(key.extra.split('|') + ['', '', ''])[2]}`; "
            "request and resolve a fresh one at the mapped position: the old handle must fail, give no edit, or give "
            "the fresh handle's edit.")


def r3_step(case: Mapping[str, Any], key: QueryKey) -> str:
    sub, path = case.get("sub"), case.get("path")
    if sub == "a":
        route = "pull" if case.get("want_pull") else "push"
        return (f"Two fresh sessions on the same project: the server's default diagnostics route and the {route} "
                f"route; the diagnostics of `{path}` must be equal.")
    if sub == "b":
        return (f"`textDocument/semanticTokens/full` on `{path}`, then `textDocument/semanticTokens/range` over "
                f"{case.get('range')}; the range answer must equal the full answer restricted to that range.")
    if sub == "c":
        return (f"`textDocument/documentHighlight` and `textDocument/references` (includeDeclaration) on `{path}` at "
                f"{_at(case.get('pos') or [0, 0])}; every highlight range must be a reference range in that file.")
    t = case.get("target") or ["?", 0, 0]
    return (f"`textDocument/definition` on `{t[0]}` at {_at(t[1:3])} gives the expected set; didOpen `{key.path}` and "
            f"`textDocument/definition` at the reference {_at([key.line, key.character])} must give the same set.")


def r4_step(case: Mapping[str, Any], key: QueryKey) -> str:
    kind, path = case.get("kind"), case.get("path")
    text = {"quickfix": f"request code actions for the diagnostic {case.get('diag')} in `{path}`; apply the quick fix "
                        f"'{case.get('title')}'; wait until idle: the diagnostic must be gone and no error added.",
            "format": f"`textDocument/formatting` on `{path}`, apply the edits, format again: the second answer must "
                      "be empty (and, for TypeScript, the non-whitespace text unchanged).",
            "organize": f"source.organizeImports on `{path}`, apply, run it again: the second must change nothing.",
            "completion": f"`textDocument/completion` on `{path}` at {_at([case.get('line', 0), case.get('character', 0)])}; "
                          f"insert the item: the file must not gain a syntax error."}
    return text.get(str(kind), f"check {kind}: {json.dumps(case, sort_keys=True)[:300]}")


COMPARE: Dict[str, str] = {
    "r0_crash": "it fails like this in two independent fresh sessions (expected: an answer)",
    "r1_history": "compare with the same query in a fresh session opened on the final content (expected)",
    "r4_edits": "compare with the same query in a fresh session on the same content (expected)",
    "r5_transforms": "compare with the same query on the untransformed project, positions mapped (expected)",
    "r6_crossimpl": "compare with the reference implementation's answer (expected)",
}


def steps(doc: Mapping[str, Any], ops: Sequence[Op], key: QueryKey) -> List[str]:
    oracle, case, timing = doc["oracle"], doc.get("case") or {}, doc["context"].get("timing", "settled")
    out = [f"Start {doc['server']['kind']} {doc['server']['version']} on the project root; answer "
           "workspace/configuration with the settings under Environment."]
    history = oracle == "r1_history" or (oracle == "r4_edits" and case.get("kind") in ("mutation", "r1-suspect"))
    if history and ops:
        mode = ("wait until the server is idle after every step" if timing == "settled"
                else f"send the steps {timing[4:]} ms apart without waiting, then wait until idle")
        out += [op_step(o) for o in ops] + [f"Timing: {mode}."]
        closed = [t["path"] for t in doc["context"].get("targets") or [] if t["path"] not in open_after(ops)]
        if closed:
            out.append(f"textDocument/didOpen {', '.join(f'`{p}`' for p in closed)} (the query step opens every "
                       "target file that is not open), then wait until the server is idle.")
    if oracle == "r0_crash":
        out.append("didOpen every target file, wait until the server is idle, then send the queries; the failing "
                   "request is below.")
    elif oracle == "r5_transforms":
        t = case.get("transform") or {}
        out.append(f"Two fresh sessions: one on the original project, one with transformation {t.get('kind')} "
                   f"applied to `{t.get('path')}` ({len(t.get('edits') or [])} edit(s), first "
                   f"{(t.get('edits') or [[]])[0][:4]}).")
    elif oracle == "r6_crossimpl":
        ref = case.get("reference") or {}
        out.append(f"Fresh sessions of {doc['server']['kind']} {doc['server']['version']} and of the reference "
                   f"{ref.get('kind')} {ref.get('version')} on the same project, the same query in both.")
    elif oracle == "r4_edits" and case.get("kind") == "mutation":
        out.append("The quick fix above was applied in the same session: the targeted diagnostic must be gone and "
                   "the error count must not exceed the one before the mutation.")
    step = {"r2_handles": r2_step, "r3_routes": r3_step, "r4_edits": r4_step}.get(oracle)
    if step is not None and not history:
        return out + [step(case, key)]
    return out + [f"Query {query_step(key)}; {COMPARE.get(oracle, 'compare with the expected answer')}."]


# ------------------------------------------------------------------ report
def numbered(text: str, lines: Optional[Sequence[int]] = None, context: int = 3, limit: int = 120) -> List[str]:
    """Non-blank lines with 1-based numbers (all, or around `lines`), gaps marked."""
    rows = text.split("\n")
    keep = set(range(len(rows))) if lines is None else {i for l in lines for i in range(l - context, l + context + 1)}
    out, last = [], -2
    for i, row in enumerate(rows):
        if i in keep and row.strip():
            if i != last + 1 and out:
                out.append("     ...")
            out.append(f"{i + 1:4} | {row}")
            last = i
    return out[:limit] + (["     ... (truncated)"] if len(out) > limit else [])


def render_report(g: Group, doc: Mapping[str, Any], red: Mapping[str, Any], issues: Mapping[str, Any],
                  build: Mapping[str, Any], machine: Mapping[str, Any], files: Mapping[str, str],
                  excerpt: Sequence[str], repro_cmd: str) -> str:
    key = QueryKey(**doc["key"])
    ops = [Op.from_json(o) for o in doc.get("ops") or []]
    obs = red.get("observed") or {}
    exp, act = obs.get("expected", doc.get("expected")), obs.get("actual", doc.get("actual"))
    s = g.summary()
    lines = [f"# {title(g, doc['server']['version'])}", "",
             f"Draft for the author (not filed). Group `{g.gid}`, signature `{g.signature}`, case family `{g.family}`.",
             "", "## Server", "",
             f"- {doc['server']['kind']} {doc['server']['version']}; launch `{display(' '.join(build.get('cmd') or []))}`; "
             f"entry sha256 {build.get('sha256', '?')}; package version {build.get('package_version') or '-'}"
             + (f"; node {build['node']}" if build.get("node") else ""),
             f"- project `{doc['project']['name']}` ({doc['project']['source']}"
             + (f", commit {doc['project']['commit']}" if doc['project'].get('commit') else "") + f"), "
             f"language {doc['project']['language']}", "", "## Relation violated", "", RELATIONS.get(g.oracle, g.oracle),
             "", "## Minimal steps (LSP)", ""]
    lines += [f"{i}. {st}" for i, st in enumerate(steps(doc, ops, key), 1)]
    lines += ["", "## Expected vs actual", "", "Expected (fresh session / reference):", "", "```json", show(exp), "```",
              "", "Actual:", "", "```json", show(act), "```", ""]
    for path, text in files.items():
        lines += [f"Project file `{path}`" + (" (line-reduced: other lines blanked)" if red.get("lines") else "")
                  + ":", "", "```", *numbered(text, None if red.get("lines") or len(text) < 6000 else
                                             [key.line] + [o.start[0] for o in ops if o.path == path and o.start]), "```",
                  ""]
    settings = doc["context"].get("extra_settings")
    lines += ["## Environment", "",
              f"- {machine.get('platform', '?')}, Python {machine.get('python', '?')}, {machine.get('cpus', '?')} CPUs",
              f"- client: scripts/lsp_repro (capabilities.client_capabilities); timing {doc['context'].get('timing')}; "
              f"settle timeout {doc['context'].get('settle_timeout_s')} s; request timeout "
              f"{doc['context'].get('request_timeout_s')} s",
              f"- workspace settings: {'`' + json.dumps(settings, sort_keys=True)[:600] + '`' if settings else 'the tool defaults (driver.SESSION_SETTINGS and the launch spec)'}",
              "", "## Reproduce", "", "```", repro_cmd, "```", "",
              "## Evidence and reduction", "",
              f"- representative {red.get('vid')}: confirmed {doc.get('reproduced')} (each replay: fresh baseline, fresh "
              f"control and a fresh case session)",
              f"- ops {red.get('ops_before', '?')} -> {len(ops)} ({red.get('probes', 0)} probes, "
              f"{red.get('reduce_seconds', 0)} s, reduced ops confirmed {red.get('reduced_confirmed') or '-'})"
              + ("; query targets narrowed to the key" if red.get("narrowed") else ""),
              f"- lines: {'; '.join(f'{p}: {n}' for p, n in (red.get('lines') or {}).items()) or 'not reduced'}"
              + (f" ({red.get('line_probes')} probes, confirmed {red.get('lines_confirmed')})" if red.get('lines') else "")
              + (f"; skipped: {'; '.join(red.get('line_skipped') or [])}" if red.get("line_skipped") else ""),
              f"- group: {s['members']} violation(s) in {len(s['runs'])} run(s), projects {', '.join(s['projects'])}, "
              f"timings {', '.join(s['timings'])}, seeds {', '.join(s['seeds'])}", "",
              "## Possibly related issues (search results, to be checked by the author)", ""]
    ms = issues.get("matches") or []
    lines += [f"- [{m['repo']}#{m['number']}]({m['url']}) {m['title']} ({m['state']}, {m['created']}, "
              f"{m['comments']} comments)" for m in ms] or ["- none found"]
    lines += [f"- queries: {'; '.join('`' + q + '`' for q in issues.get('queries') or [])}"]
    lines += [f"- note: {n}" for n in issues.get("notes") or []]
    if excerpt:
        lines += ["", "## Server log excerpt (last confirming replay)", "", "```", *(display(x) for x in excerpt), "```"]
    return "\n".join(lines) + "\n"


def render_index(campaign: str, rows: Sequence[Mapping[str, Any]]) -> str:
    out = [f"# Triage of campaign {campaign}", "",
           "One row per group (signature x method x case family). Verdicts go into decisions.csv "
           f"({', '.join(VERDICTS)}); nothing is filed automatically.", "",
           "| group | signature | family | members | ops (reduced) | lines | issue matches | report |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        sig = str(r["signature"]).replace("|", "\\|")  # a pipe would split the table cell
        out.append(f"| {r['gid']} | `{sig}` | {r['family']} | {r['members']} | {r['ops_before']} -> "
                   f"{r['ops_after']} | {r.get('lines') or '-'} | {r.get('matches', 0)} | [report]({r['gid']}/report.md) |")
    return "\n".join(out) + "\n"


def write_decisions(path: str, groups: Sequence[str]) -> List[str]:
    """Append a row for every group not in decisions.csv yet; returns the groups added."""
    have: List[str] = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", newline="") as f:
            have = [r.get("group", "") for r in csv.DictReader(f)]
    new = [g for g in groups if g not in have]
    fresh = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if fresh:
            w.writerow(DECISION_COLUMNS)
        for g in new:
            w.writerow([g] + [""] * (len(DECISION_COLUMNS) - 1))
    return new


__all__ = ["DECISION_COLUMNS", "RELATIONS", "VERDICTS", "numbered", "render_index", "render_report", "steps", "symptom",
           "title", "write_decisions"]
