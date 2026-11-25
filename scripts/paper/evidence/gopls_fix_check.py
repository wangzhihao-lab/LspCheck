"""Server-independent checks of the gopls findings C3, C5, C6 and C7 with the Go toolchain.

C5/C6/C7 (quick fixes after a seeded mutation): the file content is rebuilt offline from the
reduced ops of each triage group (oracles.base.final_state, the harness's own edit semantics)
in three states - base (corpus file), mutated (ops without the fix's edit) and fixed (all ops,
i.e. the mutation followed by the edit gopls returned). Each state is written into an APFS
clone of the corpus project under temp/evidence_scratch/ (the corpus clone is never written)
and checked with `go build -o /dev/null ./<pkg>` (or `go vet ./<pkg>` for a _test.go file) in
the nearest module, and with `gofmt -e <file>` (exit code and stderr; the formatted source on
stdout is discarded). The module cache is the one gopls ran with (GOPATH=temp/lsp_servers/gopath,
as in scripts/lsp_repro/servers_extra.py); network is off (GOPROXY=off, -mod=readonly,
GOTOOLCHAIN=local).

C3 (stale code-action resolve): the recorded stale edit (repro.json `actual`) and the fresh
session's edit (`expected`) are applied to the current text (after the inserted line); the
lines around the edit and `gofmt -e` on each result are reported.

Writes data/lsptest/runs/main_v1/evidence/gopls_checks.log (human-readable) and
gopls_checks.json. Local absolute paths are replaced by <scratch>, <repo> and ~.

Run line: python3 scripts/paper/evidence/gopls_fix_check.py
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))

from campaign_store import load_repro  # noqa: E402  (frozen tool, read-only)
from driver import clone_tree  # noqa: E402
from oracles.base import final_state  # noqa: E402
from ops import apply_change, read_text, write_text  # noqa: E402

TRIAGE = os.path.join(REPO, "data", "lsptest", "runs", "main_v1", "triage")
EVIDENCE = os.path.join(REPO, "data", "lsptest", "runs", "main_v1", "evidence")
SCRATCH = os.path.join(REPO, "temp", "evidence_scratch")
GOPATH_DIR = os.path.join(REPO, "temp", "lsp_servers", "gopath")  # the module cache gopls ran with
GO_ENV = {"GOPATH": GOPATH_DIR, "GOMODCACHE": os.path.join(GOPATH_DIR, "pkg", "mod"), "GOPROXY": "off",
          "GOFLAGS": "-modcacherw -mod=readonly", "GOTOOLCHAIN": "local"}
CONTEXT_LINES = 3
TIMEOUT_S = 600

logger = logging.getLogger("gopls_fix_check")


@dataclass(frozen=True)
class FixCheck:
    """One quick-fix group and how its package is checked."""

    cause: str
    gid: str
    env: Mapping[str, str] = field(default_factory=dict)


FIX_CHECKS: Tuple[FixCheck, ...] = (
    FixCheck("C5", "gopls-r4-diagnostics-extra-notatype-mutation-m2-477181"),
    FixCheck("C5", "gopls-r4-diagnostics-extra-untypedniluse-mutation-m2-354f70",
             {"GOOS": "windows", "GOARCH": "amd64"}),  # command_win.go is windows-only
    FixCheck("C5", "gopls-r4-diagnostics-extra-invalidifaceassign-mutation-m2-416e90"),
    FixCheck("C5", "gopls-r4-diagnostics-extra-nonindexableoperand-mutation-m2-ba152b"),  # a _test.go file
    FixCheck("C5", "gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a"),
    FixCheck("C6", "gopls-r4-diagnostics-extra-mutation-m2-111975"),
    FixCheck("C6", "gopls-r4-syntax-gained-mutation-m2-86fde3"),
    FixCheck("C7", "gopls-r4-diagnostics-extra-undeclaredname-wrongar-mutation-m3-946c39"),
)
STALE_GID = "gopls-r2-codeactionresolve-changed-codeaction-70b3e9"


def scrub(text: str, scratch: str = "") -> str:
    """Replace local absolute paths by placeholders."""
    if scratch:
        text = text.replace(scratch, "<scratch>")
    return text.replace(REPO, "<repo>").replace(os.path.expanduser("~"), "~")


def run(cmd: Sequence[str], cwd: str, env: Mapping[str, str], scratch: str, stdout: bool = True) -> Dict[str, Any]:
    """Run a command; exit code and scrubbed output lines (stderr only when `stdout` is False)."""
    full_env = dict(os.environ, **GO_ENV, **env)
    try:
        p = subprocess.run(list(cmd), cwd=cwd, env=full_env, capture_output=True, text=True, timeout=TIMEOUT_S)
        out = ((p.stdout if stdout else "") + p.stderr).strip()
        code = p.returncode
    except subprocess.TimeoutExpired:
        out, code = f"timeout after {TIMEOUT_S}s", -1
    env_txt = " ".join(f"{k}={v}" for k, v in sorted(env.items()))
    return {"cmd": scrub((env_txt + " " if env_txt else "") + " ".join(cmd), scratch), "cwd": scrub(cwd, scratch),
            "exit": code, "output": [scrub(line, scratch) for line in out.splitlines()]}


def module_root(path: str) -> str:
    """Nearest directory at or above `path` holding a go.mod."""
    d = os.path.dirname(path)
    while not os.path.exists(os.path.join(d, "go.mod")):
        parent = os.path.dirname(d)
        if parent == d:
            raise FileNotFoundError(f"no go.mod above {path}")
        d = parent
    return d


def snippet(text: str, first: int, last: int) -> List[str]:
    """Numbered lines first..last (0-based, inclusive) shown 1-based."""
    lines = text.split("\n")
    lo, hi = max(0, first), min(len(lines) - 1, last)
    return [f"{i + 1:5d} | {lines[i]}" for i in range(lo, hi + 1)]


def check_fix(fc: FixCheck) -> Dict[str, Any]:
    """Rebuild base/mutated/fixed, check each with the Go toolchain; return the record."""
    repro = os.path.join(TRIAGE, fc.gid, "repro.json")
    doc, v = load_repro(repro)
    project = os.path.join(REPO, doc["project"]["ref"])
    case = doc["case"]
    path = case["path"]
    n_fix = len(case["fix_ops"])
    ops = list(v.ops)
    mut_ops, fix_ops = ops[:len(ops) - n_fix], ops[len(ops) - n_fix:]
    tail = [o.to_json() if hasattr(o, "to_json") else o for o in fix_ops]
    texts = {"base": read_text(os.path.join(project, path)),
             "mutated": final_state(project, mut_ops).files.get(path),
             "fixed": final_state(project, ops).files.get(path)}
    scratch = os.path.join(SCRATCH, fc.gid)
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(SCRATCH, exist_ok=True)
    clone_tree(project, scratch)
    target = os.path.join(scratch, path)
    mod = module_root(target)
    pkg = "./" + os.path.relpath(os.path.dirname(target), mod) if os.path.dirname(target) != mod else "."
    tool = ["go", "vet", pkg] if path.endswith("_test.go") else ["go", "build", "-o", os.devnull, pkg]
    states: Dict[str, Any] = {}
    try:
        for state, text in texts.items():
            write_text(target, text or "")
            states[state] = {"go": run(tool, mod, fc.env, scratch),
                             "gofmt": run(["gofmt", "-e", target], mod, {}, scratch, stdout=False)}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    mline, fline = mut_ops[-1].start[0], fix_ops[0].start[0]
    added = texts["fixed"].count("\n") - texts["mutated"].count("\n")
    return {"cause": fc.cause, "gid": fc.gid, "project": doc["project"]["name"], "path": path,
            "fix_title": case.get("title"), "mutation": case["mutation"]["what"],
            "fix_ops_json": json.dumps(tail, ensure_ascii=False)[:600],
            "module": scrub(mod, scratch), "tool": " ".join(tool),
            "mutated_snippet": snippet(texts["mutated"], min(mline, fline) - CONTEXT_LINES,
                                       max(mline, fline) + CONTEXT_LINES),
            "fixed_snippet": snippet(texts["fixed"], min(mline, fline) - CONTEXT_LINES,
                                     max(mline, fline) + added + CONTEXT_LINES),
            "states": states}


def apply_edits(text: str, edits: Sequence[Sequence[Any]]) -> str:
    """Apply [path, sl, sc, el, ec, newText] edits (non-overlapping) from the last to the first."""
    out = text
    for e in sorted(edits, key=lambda e: (e[1], e[2]), reverse=True):
        out = apply_change(out, (e[1], e[2]), (e[3], e[4]), e[5])[0]
    return out


def gofmt_text(text: str, name: str) -> Dict[str, Any]:
    """gofmt -e on `text` written to a scratch file (exit code and stderr)."""
    d = os.path.join(SCRATCH, "stale")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, name)
    write_text(f, text)
    try:
        return run(["gofmt", "-e", f], d, {}, d, stdout=False)
    finally:
        os.remove(f)


def check_stale() -> Dict[str, Any]:
    """C3: apply the stale and the fresh edit to the current text; lines around; gofmt -e."""
    doc, v = load_repro(os.path.join(TRIAGE, STALE_GID, "repro.json"))
    project = os.path.join(REPO, doc["project"]["ref"])
    path = doc["key"]["path"]
    old = read_text(os.path.join(project, path))
    cur = final_state(project, v.ops).files[path]
    stale, fresh = apply_edits(cur, doc["actual"]), apply_edits(cur, doc["expected"])
    lines = sorted({e[1] for e in doc["actual"]} | {e[1] for e in doc["expected"]})
    lo, hi = lines[0] - 2, lines[-1] + 2
    rec = {"cause": "C3", "gid": STALE_GID, "project": doc["project"]["name"], "path": path,
           "key": doc["key"], "ops": [o.to_json() if hasattr(o, "to_json") else str(o) for o in v.ops],
           "old_line_34": old.split("\n")[34], "current_line_34": cur.split("\n")[34],
           "current_line_35": cur.split("\n")[35],
           "current_snippet": snippet(cur, lo, hi),
           "stale_applied_snippet": snippet(stale, lo, hi + stale.count("\n") - cur.count("\n")),
           "fresh_applied_snippet": snippet(fresh, lo, hi + fresh.count("\n") - cur.count("\n")),
           "gofmt_current": gofmt_text(cur, "current.go"), "gofmt_stale": gofmt_text(stale, "stale_applied.go"),
           "gofmt_fresh": gofmt_text(fresh, "fresh_applied.go")}
    shutil.rmtree(os.path.join(SCRATCH, "stale"), ignore_errors=True)
    return rec


def render(fixes: List[Dict[str, Any]], stale: Dict[str, Any], env: Dict[str, str]) -> str:
    """Human-readable log."""
    out = [f"go version: {env['go_version']}", f"environment: {env['go_env']}", ""]
    for r in fixes:
        out += [f"== {r['cause']} {r['gid']}", f"project {r['project']}, file {r['path']}",
                f"mutation: {r['mutation']}; fix: {r['fix_title']}", f"fix edit: {r['fix_ops_json']}",
                f"module {r['module']}; package check: {r['tool']}", "-- mutated (before the fix):",
                *r["mutated_snippet"], "-- fixed (after the fix):", *r["fixed_snippet"]]
        for state, res in r["states"].items():
            for tool in ("go", "gofmt"):
                x = res[tool]
                out.append(f"-- [{state}] $ {x['cmd']}  (in {x['cwd']}) -> exit {x['exit']}")
                out += [f"   {line}" for line in x["output"]] or ["   (no output)"]
        out.append("")
    s = stale
    out += [f"== C3 {s['gid']}", f"project {s['project']}, file {s['path']}", f"key {json.dumps(s['key'])}",
            f"ops {json.dumps(s['ops'])}", f"old line 35 (1-based): {s['old_line_34']}",
            f"current line 35 (1-based): {s['current_line_34']}", f"current line 36 (1-based): {s['current_line_35']}",
            "-- current text:", *s["current_snippet"], "-- stale edit (recorded actual) applied:",
            *s["stale_applied_snippet"], "-- fresh edit (recorded expected) applied:", *s["fresh_applied_snippet"]]
    for k in ("gofmt_current", "gofmt_stale", "gofmt_fresh"):
        x = s[k]
        out.append(f"-- {k}: $ {x['cmd']} -> exit {x['exit']}")
        out += [f"   {line}" for line in x["output"]] or ["   (no output)"]
    return "\n".join(out) + "\n"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    env = {"go_version": subprocess.run(["go", "version"], capture_output=True, text=True).stdout.strip(),
           "go_env": scrub(", ".join(f"{k}={v}" for k, v in GO_ENV.items()))}
    fixes = []
    for fc in FIX_CHECKS:
        logger.info("checking %s %s", fc.cause, fc.gid)
        fixes.append(check_fix(fc))
    stale = check_stale()
    os.makedirs(EVIDENCE, exist_ok=True)
    with open(os.path.join(EVIDENCE, "gopls_checks.json"), "w", encoding="utf-8") as f:
        json.dump({"env": env, "fixes": fixes, "stale": stale}, f, ensure_ascii=False, indent=1)
    text = render(fixes, stale, env)
    with open(os.path.join(EVIDENCE, "gopls_checks.log"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
