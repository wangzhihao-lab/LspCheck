"""Server-independent checks of the second-corpus root causes C12-C35: the Go, Python and Rust parts.

What it checks (one family per argument; no language server is started):
  go     C15: 'Delete var' (colima cmd/ssh.go): base/pre/post in an APFS clone, `go build -o /dev/null ./cmd`
         and `gofmt -e`; C14: the restored lux content builds (`go vet ./extractors/geekbang`); C13: what the
         go command reports for the tests module of gorm on the final content of both C13 histories.
  py     C22: `python3 -m py_compile` of the file before and after the auto-import completion; C17: py_compile
         of the queried file and its import; C20: the quoted annotations of scrapy/utils/misc.py (ast, and
         what typing makes of the strings at run time); C21: the return statements of yolov5's letterbox;
         C19: the docstring of warnings.warn in the interpreter's standard library.
  rust   C27, C28, C29: the rustc parser alone (`RUSTC_BOOTSTRAP=1 rustc -Zparse-crate-root-only`, which does
         not load out-of-line modules) on the file before and after the completion or quick fix; syntax only.

Reads: the triage groups' repro.json and case logs under data/lsptest/runs/<campaign>/triage/ (through
group_states.py), the corpus clones under temp/corpus/ (read-only), the Go module cache gopls used
(temp/lsp_servers/gopath, offline), the local rustc 1.98.1 toolchain and the interpreter's standard library.
Writes: data/lsptest/runs/main_v2/evidence/checks/<family>.json and checks_go_py_rust.log. The corpus clones
are never written: Go checks run in an APFS clone under temp/evidence_scratch_v2/, the other checks on files
written under that directory; every clone and file is removed after its check. Local absolute paths are
replaced by <repo>, <scratch> and ~ in the outputs.

Run line (through the shared core ledger, 2 cores):
python3 scripts/paper/evidence/second_corpus/checks_go_py_rust.py go py rust
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import typing
import warnings
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from group_states import OUT, REPO, SCRATCH, final_files, scrub, setup_logging, snippet, states  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))
from driver import clone_tree  # noqa: E402  (frozen tool, read-only)
from ops import write_text  # noqa: E402

GOPATH_DIR = os.path.join(REPO, "temp", "lsp_servers", "gopath")
GO_ENV = {"GOPATH": GOPATH_DIR, "GOMODCACHE": os.path.join(GOPATH_DIR, "pkg", "mod"), "GOPROXY": "off",
          "GOFLAGS": "-modcacherw -mod=readonly", "GOTOOLCHAIN": "local"}
RUST_BIN = os.path.expanduser("~/.rustup/toolchains/1.98.1-aarch64-apple-darwin/bin")
CORPUS = os.path.join(REPO, "temp", "corpus")
TIMEOUT_S = 280
logger = logging.getLogger("checks_go_py_rust")


def run(cmd: Sequence[str], cwd: str, env: Optional[Mapping[str, str]] = None, keep: int = 60) -> Dict[str, Any]:
    """Run a command and keep its exit code and scrubbed output.

    Args:
        cmd: command and arguments.
        cwd: working directory.
        env: variables added to the current environment.
        keep: number of output lines kept.

    Returns:
        {"cmd", "cwd", "exit", "output"}; exit is -1 on timeout.
    """
    try:
        p = subprocess.run(list(cmd), cwd=cwd, env=dict(os.environ, **(env or {})), capture_output=True,
                           text=True, timeout=TIMEOUT_S)
        out, code = (p.stdout + p.stderr).strip(), p.returncode
    except subprocess.TimeoutExpired:
        out, code = f"timeout after {TIMEOUT_S}s", -1
    return {"cmd": scrub(" ".join(cmd)), "cwd": scrub(cwd), "exit": code,
            "output": [scrub(x) for x in out.splitlines()][:keep]}


def fresh_clone(project: str, name: str) -> str:
    """An APFS clone of a corpus project under the scratch directory.

    Args:
        project: corpus project directory.
        name: clone directory name.

    Returns:
        Path of the new clone (any earlier one of that name is removed first).
    """
    dst = os.path.join(SCRATCH, name)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(SCRATCH, exist_ok=True)
    clone_tree(project, dst)
    return dst


def read_file(path: str) -> str:
    """UTF-8 text of a file."""
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- Go
def go_c15() -> Dict[str, Any]:
    """C15: 'Delete var' leaves the import that only the deleted initializer used."""
    gid = "gopls-r4-diagnostics-extra-unusedimport-mutation-m3-aefa9e"
    doc, project, path, texts = states("main_v2", gid)
    clone = fresh_clone(project, gid)
    res: Dict[str, Any] = {"cause": "C15", "gid": gid, "path": path, "title": doc["case"]["title"],
                           "post_snippet": snippet(texts["post"] or "", 0, 12), "states": {}}
    try:
        for st in ("base", "pre", "post"):
            write_text(os.path.join(clone, path), texts[st] or "")
            res["states"][st] = {"go": run(["go", "build", "-o", os.devnull, "./cmd"], clone, GO_ENV),
                                 "gofmt": run(["gofmt", "-e", "-l", path], clone, GO_ENV)}
    finally:
        shutil.rmtree(clone, ignore_errors=True)
    return res


def go_c14() -> Dict[str, Any]:
    """C14: the history ends on the corpus content; the test package builds and vets."""
    gid = "gopls-r1-completion-lost-h7-1a1169"
    doc, project, files = final_files("main_v2", gid)
    same = sorted(files)  # final_state lists the paths whose final content differs from the corpus
    clone = fresh_clone(project, gid)
    try:
        for p, t in files.items():
            if t is not None:
                write_text(os.path.join(clone, p), t)
        vet = run(["go", "vet", "./extractors/geekbang"], clone, GO_ENV)
    finally:
        shutil.rmtree(clone, ignore_errors=True)
    return {"cause": "C14", "gid": gid, "paths_differing_from_corpus": same, "go_vet": vet}


def go_c13() -> Dict[str, Any]:
    """C13: what the go command reports for the tests module on the final content of both histories."""
    out: Dict[str, Any] = {"cause": "C13", "runs": []}
    for gid in ("gopls-r1-diagnostics-missing-h7-10a910", "gopls-r1-diagnostics-message-h5-e59f2c"):
        doc, project, files = final_files("main_v2", gid)
        clone = fresh_clone(project, gid)
        changed = []
        try:
            for p, t in files.items():
                if t is None:
                    continue
                with open(os.path.join(project, p), encoding="utf-8", newline="") as f:
                    if t != f.read():
                        changed.append(p)
                write_text(os.path.join(clone, p), t)
            tests = os.path.join(clone, "tests")
            rec = {"gid": gid, "files_differing_from_corpus": changed,
                   "list": run(["go", "list", "-e", "-test", "-f",
                                "{{.ImportPath}} err={{.Error}} deps={{.DepsErrors}}", "."], tests, GO_ENV),
                   "build_root_from_tests": run(["go", "build", "-o", os.devnull, "gorm.io/gorm"], tests, GO_ENV)}
        finally:
            shutil.rmtree(clone, ignore_errors=True)
        out["runs"].append(rec)
    return out


def go_family() -> Dict[str, Any]:
    """The Go family: toolchain version, environment, C15, C14, C13."""
    return {"go_version": run(["go", "version"], HERE)["output"], "env": scrub(json.dumps(GO_ENV)),
            "C15": go_c15(), "C14": go_c14(), "C13": go_c13()}


# ---------------------------------------------------------------- Python
def py_compile_text(text: str, name: str) -> Dict[str, Any]:
    """`python3 -m py_compile` of `text` written to a scratch file (removed afterwards)."""
    d = os.path.join(SCRATCH, "py")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, name)
    write_text(f, text)
    try:
        return run([sys.executable, "-m", "py_compile", f], d)
    finally:
        os.remove(f)


def py_checks() -> Dict[str, Any]:
    """The Python family: C22, C17, C20, C21, C19."""
    out: Dict[str, Any] = {"python": sys.version.split()[0]}
    gid = "pyright-r4-completioninsert-gained-completion-79a584"
    doc, project, path, texts = states("main_v2", gid)
    out["C22"] = {"gid": gid, "path": path, "line6_before": texts["base"].split("\n")[5],
                  "line6_after": (texts["post"] or "").split("\n")[5],
                  "base": py_compile_text(texts["base"], "base_main.py"),
                  "post": py_compile_text(texts["post"] or "", "post_main.py")}
    hf = os.path.join(CORPUS, "virattt__ai-hedge-fund@7d897a002c26", "hedge_fund", "backtesting")
    out["C17"] = {f: py_compile_text(read_file(os.path.join(hf, f)), f"c17_{f}") for f in ("__init__.py", "engine.py")}
    out["C17"]["engine_defines_BacktestEngine"] = bool(re.search(
        r"^class BacktestEngine\b", read_file(os.path.join(hf, "engine.py")), re.M))
    out["C20"] = c20_quoted_any()
    out["C21"] = c21_letterbox()
    import _py_warnings  # the module that holds warnings.warn's source on Python 3.14
    out["C19"] = {"module_file": scrub(_py_warnings.__file__),
                  "warn_doc_first_line": (_py_warnings.warn.__doc__ or "").strip().split("\n")[0],
                  "warnings.warn_is": f"{warnings.warn.__module__}.warn"}
    return out


def c20_quoted_any() -> Dict[str, Any]:
    """The two quoted annotations in scrapy/utils/misc.py: what they parse to and where Any comes from."""
    path = os.path.join(CORPUS, "scrapy__scrapy@91d87364637c", "scrapy", "utils", "misc.py")
    tree = ast.parse(read_file(path))
    imports = [f"line {n.lineno}: from {n.module} import {', '.join(a.name for a in n.names)}"
               for n in tree.body if isinstance(n, ast.ImportFrom) and any(a.name == "Any" for a in n.names)]
    assigns_any = [n.lineno for n in ast.walk(tree)
                   if (isinstance(n, ast.Name) and n.id == "Any" and isinstance(n.ctx, ast.Store))
                   or (isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == "Any")]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "Any" in node.value \
                and node.lineno in (33, 54):
            expr = ast.parse(node.value, mode="eval")
            names = sorted({n.id for n in ast.walk(expr) if isinstance(n, ast.Name)})
            found.append({"line": node.lineno, "col": node.col_offset, "string": node.value, "names": names})
    tv = typing.TypeVar("_CallableT", bound="Callable[..., Any]")
    return {"imports_of_Any": imports, "rebindings_of_Any": assigns_any, "strings": found,
            "TypeVar_bound_runtime": repr(tv.__bound__)}


def c21_letterbox() -> Dict[str, Any]:
    """Every return statement of utils/augmentations.py:letterbox and what it returns."""
    path = os.path.join(CORPUS, "ultralytics__yolov5@402e17ddf820", "utils", "augmentations.py")
    tree = ast.parse(read_file(path))
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "letterbox")
    rets = [{"line": r.lineno, "value": ast.unparse(r.value) if r.value else None,
             "tuple_len": len(r.value.elts) if isinstance(r.value, ast.Tuple) else None}
            for r in ast.walk(fn) if isinstance(r, ast.Return)]
    yields = any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(fn))
    return {"def_line": fn.lineno, "returns": rets, "has_yield": yields,
            "annotated_return": ast.unparse(fn.returns) if fn.returns else None}


# ---------------------------------------------------------------- Rust
def edition(project: str, path: str) -> str:
    """Edition of the nearest Cargo.toml above `path` (workspace edition when inherited); 2021 if none."""
    d = os.path.dirname(os.path.join(project, path))
    while len(d) >= len(project):
        toml = os.path.join(d, "Cargo.toml")
        if os.path.exists(toml):
            m = re.search(r'^edition\s*=\s*"(\d{4})"', read_file(toml), re.M)
            if m:
                return m.group(1)
        d = os.path.dirname(d)
    return "2021"


def rust_parse(text: str, name: str, ed: str) -> Dict[str, Any]:
    """rustc's parser alone on `text` (no out-of-line modules, no name resolution, no type checking)."""
    d = os.path.join(SCRATCH, "rs")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, name)
    write_text(f, text)
    try:
        return run([os.path.join(RUST_BIN, "rustc"), "-Zparse-crate-root-only", "--edition", ed, f], d,
                   {"RUSTC_BOOTSTRAP": "1"})
    finally:
        os.remove(f)


def rust_checks() -> Dict[str, Any]:
    """The Rust family: C27, C28 (completion) and C29 (quick fix, both groups share the edit)."""
    out: Dict[str, Any] = {"rustc": run([os.path.join(RUST_BIN, "rustc"), "--version"], HERE)["output"]}
    for cause, camp, gid in (("C27", "main_v1", "rust-analyzer-r4-completioninsert-gained-completion-e99b79"),
                             ("C28", "main_v2", "rust-analyzer-r4-completioninsert-gained-completion-e99b79"),
                             ("C29", "main_v2", "rust-analyzer-r4-diagnostics-extra-e0063-mutation-m1-aeef82"),
                             ("C29", "main_v2", "rust-analyzer-r4-syntax-gained-mutation-m1-7af5e4")):
        doc, project, path, texts = states(camp, gid)
        ed = edition(project, path)
        line = doc["key"]["line"]
        rec = {"campaign": camp, "gid": gid, "path": path, "edition": ed,
               "post_line": (texts["post"] or "").split("\n")[line]}
        for st in ("base", "pre", "post"):
            rec[st] = rust_parse(texts[st] or "", f"{cause}_{st}.rs", ed)
        out.setdefault(cause, []).append(rec)
    return out


FAMILIES: Dict[str, Callable[[], Dict[str, Any]]] = {"go": go_family, "py": py_checks, "rust": rust_checks}


def main(argv: Optional[List[str]] = None) -> int:
    """Run the named families (all when none is named) and write one JSON file per family.

    Args:
        argv: family names (go, py, rust); defaults to sys.argv[1:].

    Returns:
        Process exit code (0).
    """
    setup_logging("checks_go_py_rust")
    names = (argv if argv is not None else sys.argv[1:]) or list(FAMILIES)
    for name in names:
        logger.info("family %s", name)
        res = FAMILIES[name]()
        dst = os.path.join(OUT, f"{name}.json")
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        logger.info("family %s written to %s", name, scrub(dst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
