"""Server-independent checks of the second-corpus TypeScript causes (C11 group, C31-C35) with the TypeScript compiler.

What it checks (no language server is started):
  C11, C32, C33, C34, C35  the file before and after the quick fix or seeded mutation (group_states.py) is
      written into an APFS clone of the project and `tsc --noEmit --pretty false -p <tsconfig>` runs; the
      error lines naming the file are kept. C32: hexo 'Convert to async function'; C33: 'Fix all detected
      spelling errors' on a JSX tag; C34: 'Change spelling' on a JSX tag (also TypeScript's parser alone,
      ts_api.js parse); C35: 'Change spelling' to the variable being declared; C11: the pear-desktop group
      of the first-corpus cause C11. Compilers: TypeScript 6.0.3 (the build the campaign used,
      temp/lsp_servers/ts6-6.0.3) and, where the project pins another release, the project's own tsc.
  C31  inlay hint `: any` vs `: string`: the type of the variable in a fresh program on the final content of
      the history (ts_api.js vartype, TypeScript 6.0.3 and the project's own), and the narrowing rule on an
      `any` operand (ts_api.js narrowany).

Reads: the triage groups under data/lsptest/runs/main_v2/triage/ (through group_states.py), the corpus clones
under temp/corpus/ (read-only) and temp/lsp_servers/ts6-6.0.3/.
Writes: data/lsptest/runs/main_v2/evidence/checks/ts.json (updated per cause, so a subset of causes can be
rerun) and checks_ts.log. Clones live under temp/evidence_scratch_v2/ and are removed after each check. Local
absolute paths are replaced by <repo>, <scratch> and ~.

Run line (through the shared core ledger, 2 cores):
python3 scripts/paper/evidence/second_corpus/checks_ts.py C31 C11 C32 C33 C34 C35
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from checks_go_py_rust import fresh_clone, run  # noqa: E402
from group_states import OUT, REPO, final_files, scrub, setup_logging, states  # noqa: E402
from ops import write_text  # noqa: E402  (frozen tool, read-only)

TS6 = os.path.join(REPO, "temp", "lsp_servers", "ts6-6.0.3", "node_modules", "typescript")
API = os.path.join(HERE, "ts_api.js")
logger = logging.getLogger("checks_ts")

# cause -> (campaign, gid, tsconfig relative to the project)
FIXES: Dict[str, Tuple[str, str, str]] = {
    "C11": ("main_v2", "ts6-r4-diagnostics-extra-2322-mutation-m3-1879f3", "tsconfig.json"),
    "C32": ("main_v2", "ts6-r4-diagnostics-changed-1064-2322-quickfix-d597f5", "tsconfig.json"),
    "C33": ("main_v2", "ts6-r4-diagnostics-changed-mutation-m1-34f06f", "examples/rendering/tsconfig.json"),
    "C34": ("main_v2", "ts6-r4-diagnostics-extra-17002-2552-mutation-m1-727795",
            "examples/rendering/tsconfig.json"),
    "C35": ("main_v2", "ts6-r4-diagnostics-extra-2448-7022-mutation-m1-e5d199", "tsconfig.json"),
}


def compilers(clone: str) -> List[Tuple[str, List[str]]]:
    """The campaign's TypeScript 6.0.3, plus the project's own tsc when it is another version.

    Args:
        clone: project clone directory.

    Returns:
        (label, command prefix) per compiler.
    """
    out = [("tsc 6.0.3 (campaign build)", ["node", os.path.join(TS6, "bin", "tsc")])]
    pkg = os.path.join(clone, "node_modules", "typescript", "package.json")
    if os.path.exists(pkg):
        with open(pkg, encoding="utf-8") as f:
            ver = json.load(f)["version"]
        if ver != "6.0.3":
            out.append((f"tsc {ver} (project's own)", [os.path.join(clone, "node_modules", ".bin", "tsc")]))
    return out


def tsc_errors(cmd: Sequence[str], clone: str, tsconfig: str, rel: str) -> Dict[str, Any]:
    """`tsc --noEmit --pretty false -p tsconfig`; error lines that name `rel` (path relative to the clone).

    Args:
        cmd: compiler command prefix.
        clone: working directory (the tsconfig's directory).
        tsconfig: tsconfig file name.
        rel: path of the checked file relative to the working directory.

    Returns:
        {"cmd", "exit", "errors_in_file", "codes", "head"}.
    """
    r = run([*cmd, "--noEmit", "--pretty", "false", "-p", tsconfig], clone, keep=1_000_000)
    full = r["output"]
    lines = [ln for ln in full if rel in ln]
    return {"cmd": r["cmd"], "exit": r["exit"], "errors_in_file": lines,
            "codes": sorted({m.group(1) for ln in lines for m in [re.search(r"error TS(\d+)", ln)] if m}),
            "head": full[:3]}


def _api_json(r: Dict[str, Any], last: bool) -> Any:
    """Parsed JSON line of a ts_api.js run, or the run record when it failed."""
    if r["exit"] == 0 and r["output"]:
        return json.loads(r["output"][-1] if last else r["output"][0])
    return r


def check_fix(cause: str) -> Dict[str, Any]:
    """Base/pre/post of a quick-fix or mutation group through each compiler.

    Args:
        cause: key of FIXES.

    Returns:
        The per-compiler, per-state error records (and the parser-only result for C34).
    """
    camp, gid, tsconfig = FIXES[cause]
    doc, project, path, texts = states(camp, gid)
    clone = fresh_clone(project, gid)
    res: Dict[str, Any] = {"cause": cause, "gid": gid, "path": path, "title": doc["case"]["title"],
                           "tsconfig": tsconfig, "compilers": {}}
    rel_in_cfg = os.path.relpath(os.path.join(clone, path), os.path.dirname(os.path.join(clone, tsconfig)))
    try:
        for label, cmd in compilers(clone):
            per: Dict[str, Any] = {}
            for st in ("base", "pre", "post"):
                if st == "pre" and texts["pre"] == texts["base"]:
                    continue
                write_text(os.path.join(clone, path), texts[st] or "")
                cwd = os.path.dirname(os.path.join(clone, tsconfig))
                per[st] = tsc_errors(cmd, cwd, os.path.basename(tsconfig), rel_in_cfg)
            res["compilers"][label] = per
        if cause == "C34":
            res["parser_only"] = {}
            for st in ("base", "pre", "post"):
                f = os.path.join(clone, path)
                write_text(f, texts[st] or "")
                res["parser_only"][st] = _api_json(run(["node", API, TS6, "parse", f], clone), last=False)
    finally:
        shutil.rmtree(clone, ignore_errors=True)
    return res


def check_c31() -> Dict[str, Any]:
    """Type of modelValue (openclaude modelOptions.ts line 790) in a fresh program on the history's final content."""
    gid = "ts6-r1-inlayhint-changed-h9-b9d052"
    doc, project, files = final_files("main_v2", gid)
    clone = fresh_clone(project, gid)
    out: Dict[str, Any] = {"cause": "C31", "gid": gid, "paths_differing_from_corpus": sorted(files), "programs": {}}
    try:
        for p, t in files.items():
            if t is None:
                os.remove(os.path.join(clone, p))
            else:
                write_text(os.path.join(clone, p), t)
        f = os.path.join(clone, "src", "utils", "model", "modelOptions.ts")
        for label, tsdir in (("TypeScript 6.0.3 (campaign build)", TS6),
                             ("project's own TypeScript", os.path.join(clone, "node_modules", "typescript"))):
            r = run(["node", API, tsdir, "vartype", os.path.join(clone, "tsconfig.json"), f, "790", "modelValue"],
                    clone)
            out["programs"][label] = _api_json(r, last=True)
        out["narrow_any"] = _api_json(run(["node", API, TS6, "narrowany"], clone), last=True)
    finally:
        shutil.rmtree(clone, ignore_errors=True)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    """Run the named causes (all when none is named) and update ts.json after each.

    Args:
        argv: cause ids (C31 and the keys of FIXES); defaults to sys.argv[1:].

    Returns:
        Process exit code (0).
    """
    setup_logging("checks_ts")
    causes = (argv if argv is not None else sys.argv[1:]) or ["C31", *FIXES]
    path = os.path.join(OUT, "ts.json")
    res: Dict[str, Any] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            res = json.load(f)
    for c in causes:
        logger.info("checking %s", c)
        res[c] = check_c31() if c == "C31" else check_fix(c)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    logger.info("written to %s", scrub(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
