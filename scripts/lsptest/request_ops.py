"""The `request` op: one position query sent as part of a history, so that histories can
vary the order in which the server is asked things (query-order dependence, design
section 10). Op(kind="request", path=<open document>, start=(line, character),
text=<method>), method one of REQUEST_METHODS. The answer is kept in OpOutcome.result
and never compared; only its effect on later answers matters. An error answer is a
normal outcome of a query, so it is stored in the result, not reported as an op error.

Run line: imported by ops.py (OpApplier.op_request); not run directly.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from framing import LspError

REQUEST_METHODS: Dict[str, Tuple[str, Optional[Dict[str, Any]]]] = {  # method -> (LSP method, context)
    "hover": ("textDocument/hover", None),
    "definition": ("textDocument/definition", None),
    "typeDefinition": ("textDocument/typeDefinition", None),
    "documentHighlight": ("textDocument/documentHighlight", None),
    "references": ("textDocument/references", {"includeDeclaration": True}),
    "signatureHelp": ("textDocument/signatureHelp", {"triggerKind": 1, "isRetrigger": False}),
    "completion": ("textDocument/completion", {"triggerKind": 1}),
}


def apply_request(applier: Any, op: Any, out: Any) -> None:
    """OpApplier handler for kind "request" (bound as OpApplier.op_request)."""
    from ops import LineIndex, OpError  # late import: ops imports this module

    if op.text not in REQUEST_METHODS or op.start is None:
        raise OpError(f"request needs a method in {sorted(REQUEST_METHODS)} and a start position")
    doc = applier.store.require_open(op.path)
    LineIndex(doc.text).offset(op.start)  # raises OpError on an invalid position
    method, context = REQUEST_METHODS[op.text]
    params: Dict[str, Any] = {"textDocument": {"uri": doc.uri},
                              "position": {"line": op.start[0], "character": op.start[1]}}
    if context:
        params["context"] = dict(context)
    try:
        out.result = applier.client.request(method, params, timeout=applier.request_timeout_s)
    except LspError as exc:
        out.result = {"error": str(exc)[:300]}
        if getattr(exc, "request_id", None) is not None:  # timed out: cancel it, as an editor would
            try:
                applier.client.notify("$/cancelRequest", {"id": exc.request_id})
            except LspError:
                pass
    out.sent.append(method)


__all__ = ["REQUEST_METHODS", "apply_request"]
