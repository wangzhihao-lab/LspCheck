"""Server-independent check of the gopls finding C9 (references depend on whether the package was opened).

Group gopls-r1-references-extra-h9-0290a7 (charmbracelet/bubbletea): references of `tea.Model`
requested from examples/http/main.go (module examples/) return 80 locations in a fresh session and
87 in the history session, which had opened a file of package tea. The check decides with the Go
toolchain and the language's scoping rule whether the 7 extra locations are references of the queried
symbol, that is, whether the fresh answer is the incomplete one:
  1. the queried token is `Model` in `tea.Model`, and package tea declares Model once (non-test files);
  2. each extra location holds the identifier `Model`, unqualified, in a file whose package clause is
     `package tea` and which `go list -test` counts among the package's test files on this platform
     (so no build constraint excludes it);
  3. no extra file declares its own `Model` (type, var, const, short variable, parameter), so the
     unqualified name resolves to the package-level declaration;
  4. `go vet .` compiles the package with its test files (offline, the module cache gopls used).
The corpus clone is only read.

Writes data/lsptest/runs/main_v1/evidence/gopls_refs_check.{log,json}.

Run line: python3 scripts/paper/evidence/gopls_refs_check.py
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any, Dict, List

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
RUN = os.path.join(REPO, "data", "lsptest", "runs", "main_v1")
GID = "gopls-r1-references-extra-h9-0290a7"
GOPATH_DIR = os.path.join(REPO, "temp", "lsp_servers", "gopath")  # the module cache gopls ran with
GO_ENV = {"GOPATH": GOPATH_DIR, "GOMODCACHE": os.path.join(GOPATH_DIR, "pkg", "mod"), "GOPROXY": "off",
          "GOFLAGS": "-mod=readonly", "GOTOOLCHAIN": "local"}
NAME = "Model"
SHADOW = re.compile(rf"\b(type|var|const)\s+{NAME}\b|\b{NAME}\s*:=|[(,]\s*{NAME}\s+[\w*\[\]]")

logger = logging.getLogger("gopls_refs_check")


def go(args: List[str], cwd: str) -> Dict[str, Any]:
    p = subprocess.run(["go"] + args, cwd=cwd, env=dict(os.environ, **GO_ENV), capture_output=True, text=True,
                       timeout=600)
    return {"cmd": "go " + " ".join(args), "exit": p.returncode,
            "output": (p.stdout + p.stderr).replace(REPO, "<repo>").strip()}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with open(os.path.join(RUN, "triage", GID, "repro.json"), encoding="utf-8") as f:
        doc = json.load(f)
    root = os.path.join(REPO, doc["project"]["ref"])
    read = lambda rel: open(os.path.join(root, rel), encoding="utf-8").read()  # noqa: E731
    key = doc["key"]
    key_line = read(key["path"]).splitlines()[key["line"]]
    queried = next(m.group(0) for m in re.finditer(r"[\w.]+", key_line)
                   if m.start() <= key["character"] < m.end())
    decls = [f"{n}:{i + 1}" for n in sorted(os.listdir(root)) if n.endswith(".go") and not n.endswith("_test.go")
             for i, line in enumerate(read(n).splitlines()) if re.match(rf"type {NAME}\b", line)]
    listing = go(["list", "-test", "-f", "{{.ImportPath}} {{.TestGoFiles}}", "."], root)
    test_files = set(re.findall(r"\w+_test\.go", listing["output"]))
    extra = sorted({tuple(x) for x in doc["actual"]} - {tuple(x) for x in doc["expected"]})
    rows = []
    for path, l1, c1, _, c2 in extra:
        text = read(path)
        line = text.splitlines()[l1]
        rows.append({"location": f"{path}:{l1 + 1}:{c1 + 1}", "token": line[c1:c2],
                     "qualified": line[:c1].endswith("."),
                     "package": re.search(r"(?m)^package (\w+)", text).group(1),
                     "in_test_files": path in test_files,
                     "shadowing": sorted({m.group(0).strip() for m in SHADOW.finditer(text)}),
                     "line": line.strip()})
    vet = go(["vet", "."], root)
    ok = (queried == f"tea.{NAME}" and len(decls) == 1 and vet["exit"] == 0
          and all(r["token"] == NAME and not r["qualified"] and r["package"] == "tea" and r["in_test_files"]
                  and not r["shadowing"] for r in rows))
    result = {"group": GID, "queried": queried, "declarations": decls, "fresh_n": len(doc["expected"]),
              "history_n": len(doc["actual"]), "extra": rows, "go_list": listing, "go_vet": vet,
              "go_version": subprocess.run(["go", "version"], capture_output=True, text=True).stdout.strip(),
              "all_extra_are_references": ok}
    with open(os.path.join(RUN, "evidence", "gopls_refs_check.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    lines = [f"== C9 {GID} ({doc['project']['name']})",
             f"queried token: {queried} at {key['path']}:{key['line'] + 1}:{key['character'] + 1}",
             f"declarations of type {NAME} in non-test files of package tea: {decls}",
             f"fresh session {len(doc['expected'])} locations, history session {len(doc['actual'])}; extra in history:"]
    lines += [f"  {r['location']}  token={r['token']!r} qualified={r['qualified']} package={r['package']} "
              f"in go list TestGoFiles={r['in_test_files']} shadowing={r['shadowing']} | {r['line']}" for r in rows]
    lines += [f"$ {listing['cmd']} -> exit {listing['exit']}", "   " + listing["output"][:400],
              f"$ {vet['cmd']} -> exit {vet['exit']}", "   " + (vet["output"][:400] or "(no output)"),
              f"{result['go_version']}; all extra locations are references of {queried}: {ok}"]
    with open(os.path.join(RUN, "evidence", "gopls_refs_check.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
