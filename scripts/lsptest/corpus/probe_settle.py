"""What the corpus probe reads back from a server: settle detection and the summary
of the opened files' diagnostics.

Settle rules (each bounded by the caller's cap):
- push servers (pyright, ts6, gopls): a publishDiagnostics for every opened file,
  then 3 s with no server traffic at all;
- pull servers (ts7, rust-analyzer): textDocument/diagnostic polled for every opened
  file until two consecutive rounds agree (order-insensitive, volatile fields
  stripped); rust-analyzer additionally waits for a quiescent
  experimental/serverStatus notification.

Publishes are matched to the opened documents by settle.uri_key (decoded, case-folded
file path), the comparison the engine's own settle uses. Servers percent-encode
characters such as "[", "]" and "@" in the URIs they publish (typescript-language-server
sends app/api/[provider]/[...path]/route.ts back as
app/api/%5Bprovider%5D/%5B...path%5D/route.ts), so comparing URI strings as sent never
matches such a file and a push server could never be seen to settle on it.

"Import noise" is a heuristic over the final diagnostics; its constants live in
common.py and the markdown report restates it.

Run line: imported by corpus/probe.py; not run directly.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (PKG, os.path.join(os.path.dirname(PKG), "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from framing import LspError  # noqa: E402
from settle import uri_key  # noqa: E402
from snapshots import normalize_diagnostics  # noqa: E402

from .common import IMPORT_NOISE_RE, PYRIGHT_IMPORT_CODES, SEVERITY_NAMES, TS_IMPORT_CODES  # noqa: E402


PUBLISH_METHOD = "textDocument/publishDiagnostics"
PUSH_QUIET_S = 3.0
PUSH_POLL_S = 0.25
PULL_INTERVAL_S = 1.5
PULL_TIMEOUT_S = 60.0


# ------------------------------------------------------------ publish lookup
def latest_publishes(client: Any) -> Dict[str, List[Dict[str, Any]]]:
    """uri_key -> diagnostics of the latest publishDiagnostics the server sent for
    that document (client.notifications holds them in arrival order)."""
    latest: Dict[str, List[Dict[str, Any]]] = {}
    for note in list(client.notifications):
        if note.method != PUBLISH_METHOD:
            continue
        params = note.params or {}
        latest[uri_key(str(params.get("uri", "")))] = params.get("diagnostics") or []
    return latest


def published_diagnostics(client: Any, uri: str) -> Optional[List[Dict[str, Any]]]:
    """Latest published diagnostics for the document opened as `uri`, matched by
    decoded, case-folded path; None when the server has not published for it."""
    return latest_publishes(client).get(uri_key(uri))


# --------------------------------------------------------------------- pull
def _pull_one_raw(client: Any, uri: str) -> Optional[List[Dict[str, Any]]]:
    try:
        rep = client.request("textDocument/diagnostic", {"textDocument": {"uri": uri}}, timeout=PULL_TIMEOUT_S)
    except LspError:
        return None
    if not isinstance(rep, dict):
        return None
    return rep.get("items") or []


def _pull_one_norm(client: Any, uri: str) -> Optional[List[Tuple[Any, ...]]]:
    items = _pull_one_raw(client, uri)
    return None if items is None else normalize_diagnostics(items)


# ------------------------------------------------------------------- settle
def wait_push_settle(client: Any, uris: Sequence[str], cap_s: float) -> bool:
    """publishDiagnostics received for every uri, then 3s of total quiet."""
    deadline = time.monotonic() + cap_s
    keys = [uri_key(u) for u in uris]
    while time.monotonic() < deadline:
        published = latest_publishes(client)
        if all(k in published for k in keys):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            if client.wait_quiescent(quiet=PUSH_QUIET_S, timeout=remaining):
                return True
        time.sleep(PUSH_POLL_S)
    return False


def wait_pull_settle(client: Any, uris: Sequence[str], cap_s: float) -> bool:
    """textDocument/diagnostic polled for every uri until two consecutive
    rounds agree (order-insensitive, volatile fields stripped)."""
    deadline = time.monotonic() + cap_s
    prev = {u: _pull_one_norm(client, u) for u in uris}
    while time.monotonic() < deadline:
        time.sleep(PULL_INTERVAL_S)
        cur = {u: _pull_one_norm(client, u) for u in uris}
        if all(cur[u] is not None for u in uris) and cur == prev:
            return True
        prev = cur
    return False


def wait_serverstatus_quiescent(client: Any, cap_s: float) -> bool:
    """An experimental/serverStatus notification with quiescent=true arrives within cap_s."""
    note = client.wait_for_notification(
        lambda n: n.method == "experimental/serverStatus" and (n.params or {}).get("quiescent") is True,
        timeout=cap_s,
    )
    return note is not None


def wait_settle(client: Any, kind: str, uris: Sequence[str], pull: bool, settle_cap: float, t0: float) -> bool:
    """The settle rule of the module docstring for one server kind and diagnostic
    mode; `t0` is when the files were opened (the cap counts from there)."""
    if not pull:
        return wait_push_settle(client, uris, settle_cap)
    settled = wait_pull_settle(client, uris, settle_cap)
    if settled and kind == "rust-analyzer":
        remaining = settle_cap - (time.monotonic() - t0)
        settled = remaining > 0 and wait_serverstatus_quiescent(client, remaining)
    return settled


# -------------------------------------------------------------- diagnostics
def is_import_noise(kind: str, d: Dict[str, Any]) -> bool:
    """The import-noise heuristic (common.py): structured code first, then message."""
    code = str(d.get("code", "") or "")
    msg = str(d.get("message", "") or "")
    if kind == "pyright" and code in PYRIGHT_IMPORT_CODES:
        return True
    if kind in ("ts6", "ts7") and code in TS_IMPORT_CODES:
        return True
    if kind == "rust-analyzer" and "unresolved-import" in code.lower():
        return True
    return bool(IMPORT_NOISE_RE.search(msg))


def summarize_diagnostics(kind: str, diags_by_uri: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Totals by severity, the import-noise count and up to 5 message samples."""
    counts = {"error": 0, "warning": 0, "information": 0, "hint": 0}
    total = 0
    noise = 0
    samples: List[str] = []
    for diags in diags_by_uri.values():
        for d in diags:
            total += 1
            name = SEVERITY_NAMES.get(d.get("severity"))
            if name:
                counts[name] += 1
            if is_import_noise(kind, d):
                noise += 1
            if len(samples) < 5:
                samples.append(" ".join(str(d.get("message", "")).split())[:120])
    return {"diagnostics_total": total, "diagnostics_by_severity": counts,
            "diagnostics_import_noise": noise, "diagnostics_sample": samples}


def final_diagnostics_summary(client: Any, kind: str, uris: Sequence[str], pull: bool) -> Dict[str, Any]:
    """Summary of the opened files' final diagnostics: pulled once more in pull mode
    (the latest publish when a pull fails), the latest publish in push mode."""
    diags_by_uri: Dict[str, List[Dict[str, Any]]] = {}
    for u in uris:
        items = _pull_one_raw(client, u) if pull else None
        if items is None:
            items = published_diagnostics(client, u) or []
        diags_by_uri[u] = items
    return summarize_diagnostics(kind, diags_by_uri)


__all__ = [
    "final_diagnostics_summary", "is_import_noise", "latest_publishes", "published_diagnostics",
    "summarize_diagnostics", "wait_pull_settle", "wait_push_settle", "wait_serverstatus_quiescent",
    "wait_settle",
]
