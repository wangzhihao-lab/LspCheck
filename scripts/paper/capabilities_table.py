"""Appendix C table of the server capabilities that decide where R2 and R3 can run.

Reads the initialize results in the smoke logs of the five current-release servers
(data/lsptest/logs/smoke-<server>-<version>.jsonl) and the settle mode each server was run with
(data/lsptest/smoke_servers.json), and writes paper/appendix/tables/C_capabilities.csv: whether
pulled diagnostics are declared (every server also pushes), resolve support for code actions and
completion items, semantic-token requests, the file operations the server registers statically, and
the settle strategy.

Run line: python3 scripts/paper/capabilities_table.py
"""

from __future__ import annotations

import csv
import json
import logging
import os
from typing import Any, Dict, List, Optional

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LOGS = os.path.join(REPO, "data", "lsptest", "logs")
OUT = os.path.join(REPO, "paper", "appendix", "tables", "C_capabilities.csv")
NAMES = {"pyright": "pyright", "ts6": "TypeScript 6 (tsls)", "ts7": "TypeScript 7", "rust-analyzer": "rust-analyzer",
         "gopls": "gopls"}

logger = logging.getLogger("capabilities_table")


def initialize_capabilities(path: str) -> Optional[Dict[str, Any]]:
    """The capabilities of the first initialize result recorded in a session log."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            if '"capabilities"' not in line:
                continue
            d = json.loads(line)
            for msg in (d.get("msg"), d.get("message"), d):
                res = msg.get("result") if isinstance(msg, dict) else None
                if isinstance(res, dict) and isinstance(res.get("capabilities"), dict):
                    return res["capabilities"]
    return None


def yes(flag: Any) -> str:
    return "yes" if flag else "no"


def row(server: str, version: str, settle: str, caps: Dict[str, Any]) -> List[str]:
    ca = caps.get("codeActionProvider")
    co = caps.get("completionProvider") or {}
    st = caps.get("semanticTokensProvider") or {}
    full = st.get("full")
    fo = ((caps.get("workspace") or {}).get("fileOperations") or {})
    tokens = [n for n, ok in (("full", bool(full)), ("delta", isinstance(full, dict) and full.get("delta")),
                              ("range", bool(st.get("range")))) if ok]
    return [NAMES.get(server, server), version, yes(caps.get("diagnosticProvider")), yes(isinstance(ca, dict) and ca.get("resolveProvider")),
            yes(co.get("resolveProvider")), ", ".join(tokens) or "none", ", ".join(sorted(fo)) or "none", settle]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with open(os.path.join(REPO, "data", "lsptest", "smoke_servers.json"), encoding="utf-8") as f:
        servers = json.load(f)
    rows = []
    for s in servers:
        path = os.path.join(LOGS, f"smoke-{s['server']}-{s['version']}.jsonl")
        caps = initialize_capabilities(path) if os.path.exists(path) else None
        if caps is None:
            raise SystemExit(f"no initialize result in {os.path.relpath(path, REPO)}")
        rows.append(row(s["server"], s["version"], s["diag_mode"], caps))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["server", "version", "pulled diagnostics", "code action resolve", "completion resolve",
                    "semantic tokens", "file operations", "settled by"])
        w.writerows(rows)
    for r in rows:
        logger.info("%s", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
