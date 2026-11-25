"""Server-independent checks of the rust-analyzer findings C4 and C8.

C4 (stale completion item): from the triage group's repro.json, the edit range returned by
completionItem/resolve (`actual`) is checked against the LSP definitions, with no server:
start after end (a Range is start/end positions with an exclusive end, like a selection),
single-line, and containing the completion position (the CompletionItem.textEdit rule), both
in the document state the item was minted in and in the current one (after the inserted
lines). The relevant sentences of the LSP 3.17 specification are fetched from the
specification repository and quoted verbatim (skipped when offline).

C8 (definition consistency): no oracle outside the server exists for go-to-definition, so the
check is a reading of the code: the identifier at the declaration site and at the reference
site, how each file brings it into scope, the declarations of that name in the crate (regex over
src/**/*.rs), the attribute macro above each site, and the source text of every returned
location inside the project; extra and missing entries are listed per group.

Writes data/lsptest/runs/main_v1/evidence/ra_checks.log and ra_checks.json.

Run line: python3 scripts/paper/evidence/ra_checks.py
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Sequence, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))

from ops import LineIndex, apply_change, read_text  # noqa: E402  (frozen tool, read-only)

TRIAGE = os.path.join(REPO, "data", "lsptest", "runs", "main_v1", "triage")
EVIDENCE = os.path.join(REPO, "data", "lsptest", "runs", "main_v1", "evidence")
C4_GID = "rust-analyzer-r2-completionresolve-changed-completion-3170a1"
C8_GIDS = ("rust-analyzer-r3-definitionconsistency-extra-d-4cbc9e",
           "rust-analyzer-r3-definitionconsistency-missing-d-586fd8")
SPEC_BASE = "https://raw.githubusercontent.com/microsoft/language-server-protocol/gh-pages/_specifications/lsp/3.17/"
SPEC_PAGES = {"types/range.md": ("exclusive", "start position", "end position"),
              "language/completion.md": ("single line range", "contain the position")}
HOME = os.path.expanduser("~")
Pos = Tuple[int, int]


def scrub(text: str) -> str:
    """Replace local absolute paths by placeholders."""
    return text.replace(REPO, "<repo>").replace(HOME, "~")


def load(gid: str) -> Dict[str, Any]:
    with open(os.path.join(TRIAGE, gid, "repro.json"), encoding="utf-8") as f:
        return json.load(f)


def spec_quotes() -> List[str]:
    """Verbatim lines of the LSP 3.17 pages that define Range and CompletionItem.textEdit."""
    out: List[str] = []
    for page, needles in SPEC_PAGES.items():
        url = SPEC_BASE + page
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                text = r.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            out.append(f"{url}: not fetched ({exc})")
            continue
        hits = [ln.strip() for ln in text.splitlines() if any(n in ln for n in needles)]
        out += [f"{url}: {h}" for h in hits[:8]] or [f"{url}: no line matched {needles}"]
    return out


def shifted(pos: Pos, text: str, ops: Sequence[Dict[str, Any]], path: str) -> Tuple[Pos, str]:
    """Position `pos` of the minted state carried through the change ops; (new position, new text)."""
    cur = text
    off = LineIndex(cur).offset(tuple(pos))
    for op in ops:
        if op.get("kind") != "change" or op.get("path") != path:
            continue
        idx = LineIndex(cur)
        s, e = idx.offset(tuple(op["start"])), idx.offset(tuple(op["end"]))
        ins = op.get("text") or ""
        cur = apply_change(cur, tuple(op["start"]), tuple(op["end"]), ins)[0]
        if s <= off:
            off = s + len(ins) + max(0, off - e) if off >= e else s + len(ins)
    return LineIndex(cur).position(off), cur


def contains(start: Pos, end: Pos, p: Pos) -> bool:
    return start <= p <= end


def check_c4() -> Dict[str, Any]:
    """Range geometry of the resolved completion edit."""
    doc = load(C4_GID)
    key, project = doc["key"], os.path.join(REPO, doc["project"]["ref"])
    old = read_text(os.path.join(project, key["path"]))
    minted = (key["line"], key["character"])
    now, cur = shifted(minted, old, doc["ops"], key["path"])
    rows = []
    for label, edits in (("actual (resolve after the edit)", doc["actual"]), ("expected (fresh session)", doc["expected"])):
        for e in edits:
            s, t = (e[1], e[2]), (e[3], e[4])
            rows.append({"which": label, "range": [list(s), list(t)], "newText": e[5],
                         "start_after_end": s > t, "single_line": s[0] == t[0],
                         "contains_minted_position": contains(s, t, minted),
                         "contains_current_position": contains(s, t, tuple(now))})
    ol, cl = old.split("\n"), cur.split("\n")
    return {"gid": C4_GID, "project": doc["project"]["name"], "path": key["path"], "ops": doc["ops"],
            "minted_position": list(minted), "current_position": list(now),
            "old_lines": {i + 1: ol[i] for i in range(max(0, minted[0] - 1), minted[0] + 2)},
            "current_lines": {i + 1: cl[i] for i in range(max(0, minted[0] - 1), now[0] + 2)},
            "edits": rows, "spec": spec_quotes()}


def word_at(line: str, ch: int) -> str:
    for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", line):
        if m.start() <= ch <= m.end():
            return m.group(0)
    return ""


def attribute_above(lines: List[str], i: int) -> str:
    """The attribute line directly above the fn signature enclosing line i (within 3 lines)."""
    for j in range(i, max(-1, i - 4), -1):
        if lines[j].lstrip().startswith("#["):
            return f"{j + 1}: {lines[j].strip()}"
    return ""


def declarations(root: str, name: str) -> List[str]:
    pat = re.compile(rf"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:struct|enum|type|trait|fn|const|static|union|mod)\s+"
                     rf"{re.escape(name)}\b")
    out = []
    for path in sorted(glob.glob(os.path.join(root, "src", "**", "*.rs"), recursive=True)):
        for n, line in enumerate(read_text(path).split("\n")):
            if pat.search(line):
                out.append(f"{os.path.relpath(path, root)}:{n + 1}: {line.strip()}")
    return out


def imports(text: str, name: str) -> List[str]:
    """`use` statements (possibly multi-line) of a file that mention `name`."""
    out = []
    for m in re.finditer(r"(?ms)^\s*(?:pub\s+)?use\s+.*?;", text):
        if re.search(rf"\b{re.escape(name)}\b", m.group(0)):
            out.append(" ".join(m.group(0).split())[:300])
    return out


def loc_text(root: str, loc: Sequence[Any]) -> str:
    """Location as text; for a project file also the covered source line."""
    path = loc[0]
    shown = scrub(f"{path} {loc[1]}:{loc[2]}-{loc[3]}:{loc[4]}")
    if os.path.isabs(path):
        return shown
    lines = read_text(os.path.join(root, path)).split("\n")
    return f"{shown}  | line {loc[1] + 1}: {lines[loc[1]].strip()[:110]}"


def check_c8(gid: str) -> Dict[str, Any]:
    doc = load(gid)
    root = os.path.join(REPO, doc["project"]["ref"])
    case = doc["case"]
    dpath, dl, dc = case["target"]
    rpath, rl, rc = case["loc"][0], case["loc"][1], case["loc"][2]
    dlines, rlines = read_text(os.path.join(root, dpath)).split("\n"), read_text(os.path.join(root, rpath)).split("\n")
    dname, rname = word_at(dlines[dl], dc), word_at(rlines[rl], rc)
    exp = {tuple(x) for x in doc["expected"]}
    act = {tuple(x) for x in doc["actual"]}
    return {"gid": gid, "project": doc["project"]["name"],
            "declaration_site": f"{dpath}:{dl + 1}:{dc + 1} name {dname!r} | {dlines[dl].strip()}",
            "declaration_site_attribute": attribute_above(dlines, dl),
            "reference_site": f"{rpath}:{rl + 1}:{rc + 1} name {rname!r} | {rlines[rl].strip()}",
            "reference_site_attribute": attribute_above(rlines, rl),
            "same_name": dname == rname, "declarations_in_crate": declarations(root, dname),
            "imports_in_declaration_file": imports("\n".join(dlines), dname),
            "imports_in_reference_file": imports("\n".join(rlines), rname),
            "expected_at_declaration": [loc_text(root, x) for x in sorted(exp)],
            "actual_at_reference": [loc_text(root, x) for x in sorted(act)],
            "extra": [loc_text(root, x) for x in sorted(act - exp)],
            "missing": [loc_text(root, x) for x in sorted(exp - act)]}


def render(c4: Dict[str, Any], c8: List[Dict[str, Any]]) -> str:
    out = [f"== C4 {c4['gid']}", f"project {c4['project']}, file {c4['path']}", f"ops {json.dumps(c4['ops'])}",
           f"completion minted at {c4['minted_position']} (0-based) in the old text; the same place is "
           f"{c4['current_position']} after the ops", "old lines:"]
    out += [f"  {k:5d} | {v}" for k, v in c4["old_lines"].items()] + ["current lines:"]
    out += [f"  {k:5d} | {v}" for k, v in c4["current_lines"].items()]
    for r in c4["edits"]:
        out.append(f"{r['which']}: range {r['range'][0]}-{r['range'][1]} newText {r['newText']!r}; start_after_end="
                   f"{r['start_after_end']} single_line={r['single_line']} contains_minted_position="
                   f"{r['contains_minted_position']} contains_current_position={r['contains_current_position']}")
    out += ["LSP 3.17 specification (verbatim):"] + [f"  {q}" for q in c4["spec"]] + [""]
    for g in c8:
        out += [f"== C8 {g['gid']}", f"project {g['project']}",
                f"declaration site: {g['declaration_site']}", f"  attribute above: {g['declaration_site_attribute'] or '-'}",
                f"reference site:   {g['reference_site']}", f"  attribute above: {g['reference_site_attribute'] or '-'}",
                f"same identifier at both sites: {g['same_name']}", "declarations of that name in src/**/*.rs:"]
        out += [f"  {d}" for d in g["declarations_in_crate"]] or ["  none"]
        out += ["use statements naming it (declaration file):"] + [f"  {u}" for u in g["imports_in_declaration_file"]]
        out += ["use statements naming it (reference file):"] + [f"  {u}" for u in g["imports_in_reference_file"]]
        for k in ("expected_at_declaration", "actual_at_reference", "extra", "missing"):
            out += [f"{k} ({len(g[k])}):"] + [f"  {x}" for x in g[k]]
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    c4 = check_c4()
    c8 = [check_c8(g) for g in C8_GIDS]
    os.makedirs(EVIDENCE, exist_ok=True)
    with open(os.path.join(EVIDENCE, "ra_checks.json"), "w", encoding="utf-8") as f:
        json.dump(json.loads(scrub(json.dumps({"c4": c4, "c8": c8}, default=str))), f, ensure_ascii=False, indent=1)
    text = render(c4, c8)
    with open(os.path.join(EVIDENCE, "ra_checks.log"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
