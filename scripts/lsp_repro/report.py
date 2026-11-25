"""Build data/lsp_repro/results.md from the per-case result JSON files.

Run line: python3 scripts/lsp_repro/report.py
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(REPO, "data", "lsp_repro")


def load() -> List[Dict[str, Any]]:
    out = []
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "result-*.json"))):
        with open(p, "r", encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def _phase(rec: Dict[str, Any], phase: str) -> Dict[str, Any]:
    return (rec.get("phases", {}).get(phase) or {}).get("summary", {}) or {}


def _fixed(pre: Dict[str, Any], post: Dict[str, Any]) -> str:
    """"Fixed" is only meaningful when the bug was actually reproduced pre-fix."""
    if pre.get("verdict") == "no":
        return "n/a (not reproduced pre-fix)"
    v = post.get("verdict")
    return {"no": "yes", "yes": "no", "flaky": "partial", "not-run": "not-run"}.get(v, v or "-")


def _kn(s: Dict[str, Any]) -> str:
    if s.get("verdict") in (None, "not-run"):
        return "not-run"
    return f"{s.get('verdict')} ({s.get('k', '?')}/{s.get('n', '?')})"


def _orc(s: Dict[str, Any]) -> str:
    if not s:
        return "-"
    per = s.get("oracle_per_variant") or {}
    best = max(per.values(), key=lambda v: int(v.split("/")[0])) if per else "-"
    return f"{'yes' if s.get('oracle_flag_any') else 'no'} ({best})"


def table(recs: List[Dict[str, Any]]) -> str:
    head = (
        "| server | issue / commit | pre-fix | post-fix | reproduced-pre | fixed-post | "
        "oracle pre | oracle post | best pre-fix variant | repro k/n per variant (pre) | "
        "oracle k/n per variant (pre) | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for r in recs:
        pre, post = _phase(r, "pre"), _phase(r, "post")
        notes = []
        if pre.get("unstable") or post.get("unstable"):
            notes.append("snapshot unstable between two quiescent reads")
        for s, tag in ((pre, "pre"), (post, "post")):
            if s.get("errors"):
                notes.append(f"{tag} errors: {'; '.join(x[:60] for x in s['errors'][:2])}")
        rows.append(
            "| {srv} | [{iss}]({url}) | {pre_v} | {post_v} | {rep} | {fix} | {op} | {oq} | {bv} | {pv} | {ov} | {nt} |".format(
                srv=r.get("server", "?"),
                iss=r.get("issue", "?"),
                url=_issue_url(r.get("issue", "")),
                pre_v=r.get("pre") or "-",
                post_v=r.get("post") or "-",
                rep=_kn(pre),
                fix=_fixed(pre, post),
                op=_orc(pre),
                oq=_orc(post),
                bv=pre.get("best_variant", "-"),
                pv=", ".join(f"{k} {v}" for k, v in (pre.get("per_variant") or {}).items()) or "-",
                ov=", ".join(f"{k} {v}" for k, v in (pre.get("oracle_per_variant") or {}).items()) or "-",
                nt="; ".join(notes) or "-",
            )
        )
    return head + "\n".join(rows) + "\n"


def _issue_url(issue: str) -> str:
    if "#" in issue:
        repo, num = issue.split("#", 1)
        num = num.split()[0]
        return f"https://github.com/{repo}/issues/{num}"
    if "@" in issue:
        repo, sha = issue.split("@", 1)
        return f"https://github.com/{repo}/commit/{sha.split()[0]}"
    return ""


def variant_table(recs: List[Dict[str, Any]]) -> str:
    lines = ["| case | phase | version | variant | repro k/n | oracle k/n | seconds |", "|---|---|---|---|---|---|---|"]
    for r in recs:
        for phase in ("pre", "post"):
            node = r.get("phases", {}).get(phase) or {}
            entry = node.get("entry") or {}
            for vname, v in (entry.get("variants") or {}).items():
                lines.append(
                    f"| {r['case']} | {phase} | {entry.get('version', '-')} | {vname} | "
                    f"{v['k']}/{v['n']} | {v['oracle_k']}/{v['n']} | {v['seconds']} |"
                )
    return "\n".join(lines) + "\n"


def timing(recs: List[Dict[str, Any]]) -> str:
    lines = ["| case | server | total wall seconds | runs | seconds / run |", "|---|---|---|---|---|"]
    for r in recs:
        tot = 0.0
        n = 0
        for phase in ("pre", "post"):
            node = r.get("phases", {}).get(phase) or {}
            for v in ((node.get("entry") or {}).get("variants") or {}).values():
                tot += v["seconds"]
                n += v["n"]
        lines.append(
            f"| {r['case']} | {r.get('server')} | {tot:.0f} | {n} | {(tot / n if n else 0):.1f} |"
        )
    return "\n".join(lines) + "\n"


def reasons(recs: List[Dict[str, Any]]) -> str:
    out = []
    for r in recs:
        out.append(f"**{r['case']}** ({r.get('issue')})")
        for phase in ("pre", "post"):
            node = r.get("phases", {}).get(phase) or {}
            entry = node.get("entry") or {}
            if entry.get("install_error"):
                out.append(f"- {phase} {entry.get('version')}: NOT RUN -- {entry['install_error'][:200]}")
                continue
            for vname, v in (entry.get("variants") or {}).items():
                last = v["runs"][-1] if v["runs"] else {}
                out.append(
                    f"- {phase} {entry.get('version')} / {vname}: {v['k']}/{v['n']} -- "
                    f"{(last.get('bug_reason') or '')[:240]}"
                )
        out.append("")
    return "\n".join(out)


def main() -> int:
    recs = load()
    if not recs:
        print("no result-*.json under", OUT_DIR)
        return 1
    parts = [
        "<!-- generated by scripts/lsp_repro/report.py -- edit the prose sections by hand -->",
        "",
        "## Results table",
        "",
        table(recs),
        "",
        "## Per-variant detail",
        "",
        variant_table(recs),
        "",
        "## Timing",
        "",
        timing(recs),
        "",
        "## Per-run verdict reasons",
        "",
        reasons(recs),
    ]
    block = "\n".join(parts)
    path = os.path.join(OUT_DIR, "results.md")
    begin, end = "<!-- BEGIN GENERATED -->", "<!-- END GENERATED -->"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
    else:
        existing = f"# LSP state-inconsistency reproduction results\n\n{begin}\n{end}\n"
    if begin in existing and end in existing:
        pre_text = existing.split(begin)[0]
        post_text = existing.split(end, 1)[1]
        out = f"{pre_text}{begin}\n{block}\n{end}{post_text}"
    else:
        out = f"{existing}\n\n{begin}\n{block}\n{end}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote", path)
    print()
    print(table(recs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
