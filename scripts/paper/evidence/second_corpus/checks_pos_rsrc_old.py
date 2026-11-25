"""Server-independent checks of the second corpus, part 2: C16 positions, C26 declarations, first-batch causes.

What it checks (one family per argument; no language server is started):
  pos   C16: where the block comment of docker/compose internal/tracing/mux.go ends in the text the session
        saw (CR inserted), by the LSP 3.17 end-of-line rule, against the folding range of both sessions;
        the comment lines that carry a comment token in each semantic-tokens answer.
  rsrc  C26: the declarations behind the tokens whose modifiers the range answer drops: std's
        CommandExt::pre_exec (rust-src of the local toolchain), libc's setsid in the libc release alacritty
        locks, tokio-macros' `test` in the release googleworkspace/cli locks; rust-analyzer's own table of
        modifiers (crates/ide/src/syntax_highlighting.rs at tag 2026-09-21, kept in checks/docs/).
  old   second-corpus groups of C3, C4, C5, C7, C9 (C1, C2, C11 are covered elsewhere): C3 gofmt -e on the
        stale and the fresh edit applied to the current text; C4 the returned range against the
        CompletionItem.textEdit rule; C5/C7 go build or go vet of base/pre/post; C9 go list -test of the
        root package and the token at each extra location.

Reads: the triage groups under data/lsptest/runs/main_v2/triage/ (through group_states.py), the corpus clones
under temp/corpus/ (read-only), the local rust-src and cargo registry sources, the Go module cache gopls used
(offline), and data/lsptest/runs/main_v2/evidence/checks/docs/ra_syntax_highlighting.rs.
Writes: data/lsptest/runs/main_v2/evidence/checks/<family>.json and checks_pos_rsrc_old.log. Edited files go
only into APFS clones or files under temp/evidence_scratch_v2/, removed after each check. Local absolute
paths are replaced by <repo>, <scratch> and ~ in the outputs.

Run line (through the shared core ledger, 2 cores):
python3 scripts/paper/evidence/second_corpus/checks_pos_rsrc_old.py pos rsrc old
"""

from __future__ import annotations

import glob
import json
import logging
import os
import re
import shutil
import sys
from typing import Any, Callable, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from checks_go_py_rust import CORPUS, GO_ENV, fresh_clone, run  # noqa: E402
from group_states import (OUT, REPO, SCRATCH, apply_lsp_edits, group_dir, scrub, setup_logging,  # noqa: E402
                          snippet, states)
from campaign_store import load_repro  # noqa: E402  (frozen tool, read-only)
from oracles.base import final_state  # noqa: E402
from ops import read_text, write_text  # noqa: E402

logger = logging.getLogger("checks_pos_rsrc_old")


def lsp_lines(text: str) -> List[str]:
    """Lines by the LSP end-of-line sequences '\\r\\n', '\\n' and '\\r'."""
    return re.split(r"\r\n|\n|\r", text)


def pos_c16() -> Dict[str, Any]:
    """C16: the comment's end and comment tokens computed from the text the case session saw."""
    out: Dict[str, Any] = {}
    for gid in ("gopls-r5-foldingrange-changed-t4-b07c86", "gopls-r5-semantictokens-changed-t4-b423af",
                "gopls-r5-semantictokens-extra-t4-867006"):
        doc, v = load_repro(os.path.join(group_dir("main_v2", gid), "repro.json"))
        project = os.path.join(REPO, doc["project"]["ref"])
        path = doc["key"]["path"]
        text = final_state(project, list(v.ops)).files[path]
        lines = lsp_lines(text)
        rec: Dict[str, Any] = {"path": path, "inserted_cr": [o.start for o in v.ops if o.kind == "change"],
                               "line_count_lf": text.count("\n") + 1, "line_count_lsp": len(lines)}
        if "folding" in gid:
            end_line = next(i for i, ln in enumerate(lines) if ln.rstrip().endswith("*/"))
            rec["comment_end_from_text"] = [end_line, lines[end_line].index("*/") + 2]
            rec["end_line_text"] = lines[end_line]
            rec["fresh_comment_fold"] = [x for x in doc["expected"] if x[-1] == "comment"]
            rec["history_comment_fold"] = [x for x in doc["actual"] if x[-1] == "comment"]
        else:
            kind = "comment" if "b423af" in gid else "string"
            rec["fresh_tokens"] = sorted([x[:3] for x in doc["expected"] if x[3] == kind and x[0] < 20])
            rec["case_tokens"] = sorted([x[:3] for x in doc["actual"] if x[3] == kind and x[0] < 20])
            rec["case_tokens_outside_line"] = [x[:3] for x in doc["actual"] if x[3] == kind
                                               and (x[0] >= len(lines) or x[1] + x[2] > len(lines[x[0]]))]
            rec["zero_length_tokens"] = [x[:4] for x in doc["actual"] if x[2] == 0]
            rec["text_lines_0_19"] = [f"{i}: {ln!r}" for i, ln in enumerate(lines[:20])]
        out[gid] = rec
    return out


def locked_version(lock_text: str, crate: str) -> str:
    """Version of `crate` in a Cargo.lock.

    Raises:
        LookupError: the crate is not in the lock file.
    """
    m = re.search(rf'name = "{re.escape(crate)}"\nversion = "([^"]+)"', lock_text)
    if not m:
        raise LookupError(f"{crate} not in Cargo.lock")
    return m.group(1)


def rsrc_c26() -> Dict[str, Any]:
    """C26: the declarations behind the dropped modifiers, read from the sources the compiler would use."""
    out: Dict[str, Any] = {}
    std = sorted(glob.glob(os.path.expanduser(
        "~/.rustup/toolchains/*/lib/rustlib/src/rust/library/std/src/os/unix/process.rs")))
    src = read_text(std[-1])
    out["std_pre_exec"] = {"file": scrub(std[-1]), "decls": [f"{i + 1}: {ln.strip()}" for i, ln in
                           enumerate(src.split("\n")) if re.search(r"\bfn pre_exec\b", ln)]}
    ver = locked_version(read_text(os.path.join(CORPUS, "alacritty__alacritty@d692748d3f61", "Cargo.lock")), "libc")
    reg = glob.glob(os.path.expanduser(f"~/.cargo/registry/src/*/libc-{ver}/src/unix/mod.rs"))
    rec: Dict[str, Any] = {"locked_version": ver, "file": scrub(reg[0]) if reg else None}
    if reg:
        lines = read_text(reg[0]).split("\n")
        i = next(k for k, ln in enumerate(lines) if re.search(r"\bpub fn setsid\(\)", ln))
        block = next(k for k in range(i, -1, -1) if re.search(r'extern\s+"C"\s*\{', lines[k]))
        rec.update({"decl": f"{i + 1}: {lines[i].strip()}", "enclosing_block": f"{block + 1}: {lines[block].strip()}"})
    out["libc_setsid"] = rec
    unix = read_text(os.path.join(CORPUS, "alacritty__alacritty@d692748d3f61", "alacritty_terminal", "src", "tty",
                                  "unix.rs")).split("\n")
    out["alacritty_lines_248_251"] = unix[247:251]
    ver2 = locked_version(read_text(os.path.join(CORPUS, "googleworkspace__cli@a3768d0e82ad", "Cargo.lock")),
                          "tokio-macros")
    tm = glob.glob(os.path.expanduser(f"~/.cargo/registry/src/*/tokio-macros-{ver2}/src/lib.rs"))
    rec2: Dict[str, Any] = {"locked_version": ver2, "file": scrub(tm[0]) if tm else None}
    if tm:
        lines = read_text(tm[0]).split("\n")
        rec2["test_decl"] = [f"{k + 1}: {lines[k - 1].strip()} / {lines[k].strip()}" for k, ln in enumerate(lines)
                             if re.match(r"pub fn test\(", ln.strip())]
    out["tokio_macros_test"] = rec2
    auth = read_text(os.path.join(CORPUS, "googleworkspace__cli@a3768d0e82ad", "crates", "google-workspace-cli",
                                  "src", "auth.rs")).split("\n")
    out["auth_lines_540_542_564"] = auth[539:542] + [auth[563]]
    docs = read_text(os.path.join(OUT, "docs", "ra_syntax_highlighting.rs")).split("\n")
    out["ra_modifier_docs"] = [ln.strip() for ln in docs if re.match(r"//\s*\|(unsafe|macro|unresolvedReference)\|", ln)]
    return out


def old_go_fix(camp: str, gid: str, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """go build (go vet for a test file) and gofmt -e of base/pre/post of a quick-fix group."""
    doc, project, path, texts = states(camp, gid)
    clone = fresh_clone(project, gid)
    d = os.path.dirname(os.path.join(clone, path))
    mod = d
    while not os.path.exists(os.path.join(mod, "go.mod")):
        mod = os.path.dirname(mod)
    pkg = "./" + os.path.relpath(d, mod) if d != mod else "."
    tool = ["go", "vet", pkg] if path.endswith("_test.go") else ["go", "build", "-o", os.devnull, pkg]
    rec: Dict[str, Any] = {"gid": gid, "project": doc["project"]["name"], "path": path, "title": doc["case"]["title"],
                           "tool": " ".join(tool), "states": {}}
    try:
        for st in ("base", "pre", "post"):
            write_text(os.path.join(clone, path), texts[st] or "")
            rec["states"][st] = {"go": run(tool, mod, {**GO_ENV, **(env or {})}),
                                 "gofmt": run(["gofmt", "-e", "-l", os.path.join(clone, path)], mod, GO_ENV)}
    finally:
        shutil.rmtree(clone, ignore_errors=True)
    return rec


def _as_lsp(edits: List[List[Any]]) -> List[Dict[str, Any]]:
    """Compact edits [path, l0, c0, l1, c1, text] as LSP TextEdits."""
    return [{"range": {"start": {"line": e[1], "character": e[2]}, "end": {"line": e[3], "character": e[4]}},
             "newText": e[5]} for e in edits]


def _load_json(path: str) -> Dict[str, Any]:
    """Parsed JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def old_causes() -> Dict[str, Any]:
    """Second-corpus groups of C3, C4, C5, C7 and C9."""
    out: Dict[str, Any] = {}
    gid = "gopls-r2-codeactionresolve-changed-codeaction-70b3e9"
    doc, v = load_repro(os.path.join(group_dir("main_v2", gid), "repro.json"))
    project = os.path.join(REPO, doc["project"]["ref"])
    path = doc["key"]["path"]
    cur = final_state(project, list(v.ops)).files[path]
    rec: Dict[str, Any] = {"gid": gid, "requested_line_now": cur.split("\n")[83], "line_above": cur.split("\n")[82]}
    d = os.path.join(SCRATCH, "c3v2")
    os.makedirs(d, exist_ok=True)
    try:
        for name, edits in (("stale", doc["actual"]), ("fresh", doc["expected"])):
            t = apply_lsp_edits(cur, _as_lsp(edits))
            f = os.path.join(d, f"{name}.go")
            write_text(f, t)
            rec[name] = {"lines": snippet(t, 81, 88), "gofmt": run(["gofmt", "-e", "-l", f], d)}
    finally:
        shutil.rmtree(d, ignore_errors=True)
    out["C3"] = rec
    gid = "rust-analyzer-r2-completionresolve-changed-completion-3170a1"
    doc = _load_json(os.path.join(group_dir("main_v2", gid), "repro.json"))
    out["C4"] = {"gid": gid, "returned": doc["actual"], "fresh": doc["expected"], "rules": {
        x[0] + "_" + str(i): {"start_after_end": (x[1], x[2]) > (x[3], x[4]), "single_line": x[1] == x[3]}
        for i, x in enumerate(doc["actual"] + doc["expected"])}}
    out["C5"] = [old_go_fix("main_v2", g) for g in (
        "gopls-r4-diagnostics-extra-incompatibleassign-mutation-m2-ade1f0",
        "gopls-r4-diagnostics-extra-mismatchedtypes-mutation-m2-dc6e94",
        "gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a",
        "gopls-r4-diagnostics-extra-notatype-mutation-m2-477181",
        "gopls-r4-diagnostics-extra-untypedniluse-mutation-m2-354f70")]
    out["C7"] = old_go_fix("main_v2", "gopls-r4-diagnostics-extra-undeclaredname-mutation-m2-12380c")
    gid = "gopls-r1-references-extra-h5-e2e003"
    doc = _load_json(os.path.join(group_dir("main_v2", gid), "repro.json"))
    gorm = os.path.join(CORPUS, "go-gorm__gorm@b3d3bf219f02")
    extra = [x for x in doc["actual"] if x not in doc["expected"]]
    st = read_text(os.path.join(gorm, "statement_test.go")).split("\n")
    out["C9"] = {"gid": gid, "query_line": read_text(os.path.join(gorm, doc["key"]["path"])).split("\n")[doc["key"]["line"]],
                 "extra": [{"loc": x, "text": st[x[1]][x[2]:x[4]], "line": st[x[1]].strip()} for x in extra],
                 "package_clause": st[0], "go_list": run(["go", "list", "-test", "-f",
                                                          "{{.ImportPath}} {{.TestGoFiles}}", "."], gorm, GO_ENV)}
    return out


FAMILIES: Dict[str, Callable[[], Dict[str, Any]]] = {"pos": pos_c16, "rsrc": rsrc_c26, "old": old_causes}


def main(argv: Optional[List[str]] = None) -> int:
    """Run the named families (all when none is named) and write one JSON file per family.

    Args:
        argv: family names (pos, rsrc, old); defaults to sys.argv[1:].

    Returns:
        Process exit code (0).
    """
    setup_logging("checks_pos_rsrc_old")
    names = (argv if argv is not None else sys.argv[1:]) or list(FAMILIES)
    for name in names:
        logger.info("family %s", name)
        dst = os.path.join(OUT, f"{name}.json")
        res = FAMILIES[name]()
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        logger.info("family %s written to %s", name, scrub(dst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
