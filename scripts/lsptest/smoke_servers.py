"""Smoke-test every registered server on a tiny project with one deliberate error.

For each server: start, open the file, wait for diagnostics, ask hover and
completion, shut down. Prints one line per server and writes a JSON summary.

Run line: python3 scripts/lsptest/smoke_servers.py
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lsp_repro"))

import servers  # noqa: E402

logger = logging.getLogger(__name__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "data", "lsptest", "smoke_servers.json")

PROJECTS: Dict[str, Tuple[Dict[str, str], str, str, Tuple[int, int]]] = {
    # kind: (files, file to open, languageId, hover position (line, char))
    "ts": ({"tsconfig.json": '{"compilerOptions":{"strict":true,"target":"es2022","module":"esnext"},"include":["*.ts"]}',
            "a.ts": 'const total: number = "oops";\nfunction add(a: number, b: number) { return a + b; }\nadd(total, 1);\n'},
           "a.ts", "typescript", (1, 10)),
    "py": ({"a.py": 'total: int = "oops"\ndef add(a: int, b: int) -> int:\n    return a + b\nadd(total, 1)\n'},
           "a.py", "python", (1, 5)),
    "rs": ({"Cargo.toml": '[package]\nname = "smoke"\nversion = "0.1.0"\nedition = "2021"\n',
            "src/main.rs": 'fn add(a: i32, b: i32) -> i32 { a + b }\nfn main() {\n    let total = add(1);\n    println!("{}", total);\n}\n'},
           "src/main.rs", "rust", (0, 4)),
    "go": ({"go.mod": "module smoke\n\ngo 1.22\n",
            "main.go": 'package main\n\nfunc add(a int, b int) int { return a + b }\n\nfunc main() {\n\tvar total int = "oops"\n\t_ = add(total, 1)\n}\n'},
           "main.go", "go", (2, 6)),
}
SERVERS: List[Tuple[str, str, str]] = [
    ("pyright", "1.1.414", "py"), ("ts6", "6.0.3", "ts"), ("ts7", "7.0.2", "ts"),
    ("rust-analyzer", "2026-09-21", "rs"), ("gopls", "v0.23.0", "go"),
]


def _write_project(root: str, files: Dict[str, str]) -> None:
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def smoke(kind: str, version: str, proj: str) -> Dict[str, Any]:
    files, rel, lang, (hl, hc) = PROJECTS[proj]
    root = tempfile.mkdtemp(prefix=f"smoke-{kind}-")
    _write_project(root, files)
    uri = "file://" + os.path.join(root, rel)
    spec = servers.resolve(kind, version)
    log = os.path.join(REPO, "data", "lsptest", "logs", f"smoke-{kind}-{version}.jsonl")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    out: Dict[str, Any] = {"server": kind, "version": version}
    t0 = time.time()
    client = None
    try:
        client = servers.start(spec, "file://" + root, log, cwd=root)
        out["init_s"] = round(time.time() - t0, 1)
        text = files[rel]
        client.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": lang, "version": 1, "text": text}})
        pull = bool(getattr(client, "server_capabilities", {}).get("diagnosticProvider"))
        out["diag_mode"] = "pull" if pull else "push"
        diags: List[Dict[str, Any]] = []
        if pull:
            if kind == "rust-analyzer":  # wait until indexing is done
                client.wait_for_notification(lambda n: n.method == "experimental/serverStatus"
                                             and (n.params or {}).get("quiescent") is True, timeout=spec.ready_timeout)
            else:
                time.sleep(spec.quiet_seconds)
        else:
            note = client.wait_for_notification(
                lambda n: n.method == "textDocument/publishDiagnostics" and (n.params or {}).get("uri") == uri
                and len((n.params or {}).get("diagnostics") or []) > 0, timeout=spec.ready_timeout)
            diags = (note.params or {}).get("diagnostics", []) if note else []
        if not diags:
            try:
                rep = client.request("textDocument/diagnostic", {"textDocument": {"uri": uri}}, timeout=60)
                diags = (rep or {}).get("items", []) or []
            except Exception as e:  # noqa: BLE001  (record and continue)
                out["pull_error"] = type(e).__name__
        out["diagnostics"] = [d.get("message", "")[:70] for d in diags][:3]
        hover = client.request("textDocument/hover", {"textDocument": {"uri": uri}, "position": {"line": hl, "character": hc}}, timeout=60)
        out["hover"] = json.dumps((hover or {}).get("contents"), ensure_ascii=False)[:80]
        comp = client.request("textDocument/completion", {"textDocument": {"uri": uri}, "position": {"line": hl, "character": hc}}, timeout=60)
        items = comp.get("items", []) if isinstance(comp, dict) else (comp or [])
        out["completion_items"] = len(items)
        out["ok"] = bool(diags) and hover is not None
    except Exception as e:  # noqa: BLE001
        out["ok"] = False
        out["error"] = f"{type(e).__name__}: {str(e)[:160]}"
    finally:
        if client is not None:
            try:
                client.shutdown()
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(root, ignore_errors=True)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    results = [smoke(k, v, p) for k, v, p in SERVERS]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    for r in results:
        logger.info("%-14s %-11s ok=%-5s %5ss diag=%s hover=%s completion=%s %s", r["server"], r["version"], r.get("ok"),
                    r.get("seconds"), r.get("diagnostics"), r.get("hover", "")[:40], r.get("completion_items"), r.get("error", ""))


if __name__ == "__main__":
    main()
