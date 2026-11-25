"""Minimal check of the TypeScript quick fix "Add missing properties" on a Record-typed property (C11).

C11 was found on pmndrs/zustand with TypeScript 6.0.3: after a seeded deletion of the member
`stores` (type Record<string, StoreInformation>), the fix inserts `stores: undefined`, which tsc
rejects with TS2322. The campaign replay could not be judged on TypeScript 7.0.2 (its fresh
sessions disagreed on the key), so this script asks both implementations directly on a seven-line
project with the same shape:

    interface StoreInformation { name: string }
    interface Options { name: string; stores: Record<string, StoreInformation> }
    const options: Options = { name: "x" }

For each build it starts the server through the harness's own launch spec (servers.resolve; the
frozen tool is only imported), opens the file, reads the TS2741 diagnostic (pushed by TypeScript 6,
pulled from TypeScript 7), asks for quick fixes at it, resolves "Add missing properties" when it
comes without an edit, records the inserted text, applies it offline and runs that build's tsc
(--noEmit) on the result.

Writes data/lsptest/runs/main_v1/evidence/ts_quickfix_minimal.{json,log}.

Run line: python3 scripts/paper/evidence/ts_quickfix_minimal.py
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsp_repro"))

import servers  # noqa: E402  (frozen tool, read-only)
from lspclient import LspClient  # noqa: E402

logger = logging.getLogger("ts_quickfix_minimal")
OUT = os.path.join(REPO, "data", "lsptest", "runs", "main_v1", "evidence")
SCRATCH = os.path.join(REPO, "temp", "evidence_scratch", "ts_quickfix_minimal")
BUILDS: Tuple[Tuple[str, str], ...] = (("ts6", "6.0.3"), ("ts7", "7.0.2"))
SOURCE = ("interface StoreInformation { name: string }\n"
          "interface Options { name: string; stores: Record<string, StoreInformation> }\n"
          "const options: Options = { name: \"x\" }\n"
          "export { options }\n")
TSCONFIG = {"compilerOptions": {"strict": True, "noEmit": True, "target": "ES2022", "module": "ESNext"}, "files": ["min.ts"]}
FIX_TITLE = "Add missing properties"


def tsc_for(kind: str, version: str) -> List[str]:
    base = os.path.join(servers.SERVERS_DIR, f"{kind}-{version}", "node_modules")
    if kind == "ts6":
        return [shutil.which("node") or "node", os.path.join(base, "typescript", "bin", "tsc")]
    return [os.path.join(base, "@typescript", "typescript-darwin-arm64", "lib", "tsc")]


def apply_edits(text: str, edits: List[Dict[str, Any]]) -> str:
    """Apply LSP text edits (0-based line/character) to `text`, last edit first."""
    lines = text.split("\n")
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln) + 1)

    def at(p: Dict[str, int]) -> int:
        return offs[p["line"]] + p["character"]
    for e in sorted(edits, key=lambda e: at(e["range"]["start"]), reverse=True):
        text = text[:at(e["range"]["start"])] + e["newText"] + text[at(e["range"]["end"]):]
    return text


def diagnostics(client: LspClient, kind: str, uri: str) -> List[Dict[str, Any]]:
    if kind == "ts7":   # pull diagnostics only
        return (client.request("textDocument/diagnostic", {"textDocument": {"uri": uri}}, timeout=60) or {}).get("items", [])
    client.wait_for_diagnostics(uri, timeout=60)
    client.wait_quiescent(quiet=2.0, timeout=60)
    return client.diagnostics_for(uri) or []


def one_build(kind: str, version: str) -> Dict[str, Any]:
    project = os.path.join(SCRATCH, f"{kind}-{version}")
    shutil.rmtree(project, ignore_errors=True)
    os.makedirs(project)
    with open(os.path.join(project, "min.ts"), "w", encoding="utf-8") as f:
        f.write(SOURCE)
    with open(os.path.join(project, "tsconfig.json"), "w", encoding="utf-8") as f:
        json.dump(TSCONFIG, f)
    spec = servers.resolve(kind, version)
    uri = "file://" + os.path.join(project, "min.ts")
    client = LspClient(spec.cmd, os.path.join(project, "session.jsonl"), cwd=project,
                       env={**os.environ, **spec.env}, settings=spec.settings)
    row: Dict[str, Any] = {"kind": kind, "version": version}
    try:
        client.initialize("file://" + project, capabilities=spec.capabilities, init_options=spec.init_options)
        client.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": "typescript", "version": 1, "text": SOURCE}})
        diags = diagnostics(client, kind, uri)
        target: Optional[Dict[str, Any]] = next((d for d in diags if str(d.get("code")) == "2741"), None)
        row["diagnostics_before"] = [f"TS{d.get('code')}: {d.get('message')}" for d in diags]
        if target is None:
            row["error"] = "no TS2741 diagnostic"
            return row
        actions = client.request("textDocument/codeAction", {"textDocument": {"uri": uri}, "range": target["range"],
                                 "context": {"diagnostics": [target], "only": ["quickfix"], "triggerKind": 1}}, timeout=60) or []
        row["quick_fixes"] = [a.get("title") for a in actions]
        fix = next((a for a in actions if a.get("title", "").startswith(FIX_TITLE)), None)
        if fix is None:
            row["error"] = f"no quick fix titled {FIX_TITLE!r}"
            return row
        if "edit" not in fix and "data" in fix:
            fix = client.request("codeAction/resolve", fix, timeout=60) or fix
        changes = (fix.get("edit") or {}).get("documentChanges") or []
        edits = [e for c in changes for e in c.get("edits", [])] or [e for es in ((fix.get("edit") or {}).get("changes") or {}).values() for e in es]
        row["inserted"] = [e["newText"] for e in edits]
        fixed = apply_edits(SOURCE, edits)
        row["fixed_source"] = fixed
        with open(os.path.join(project, "min.ts"), "w", encoding="utf-8") as f:
            f.write(fixed)
        p = subprocess.run(tsc_for(kind, version) + ["--noEmit", "-p", "tsconfig.json"], cwd=project, capture_output=True, text=True, timeout=300)
        row["tsc_after_fix"] = [ln for ln in (p.stdout + p.stderr).splitlines() if "error TS" in ln]
        row["inserts_undefined"] = any("undefined" in t for t in row["inserted"])
    finally:
        client.stop()
    return row


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rows = [one_build(k, v) for k, v in BUILDS]
    with open(os.path.join(OUT, "ts_quickfix_minimal.json"), "w", encoding="utf-8") as f:
        json.dump({"source": SOURCE, "rows": rows}, f, ensure_ascii=False, indent=1)
    lines = []
    for r in rows:
        lines.append(f"== {r['kind']} {r['version']}: " + (r.get("error") or f"inserted {r.get('inserted')}; tsc after fix: {r.get('tsc_after_fix')}"))
    with open(os.path.join(OUT, "ts_quickfix_minimal.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.info("\n%s", "\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
