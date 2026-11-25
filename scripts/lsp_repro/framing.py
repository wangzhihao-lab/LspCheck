"""Protocol-level odds and ends shared by the client: the error type, the
notification record, the method sets that define "the server is still busy",
and URI comparison that tolerates the file:/// slash variations servers emit.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

# Notification methods that count as "server is still thinking".
ACTIVITY_METHODS = frozenset(
    {
        "$/progress",
        "textDocument/publishDiagnostics",
        "window/logMessage",
        "window/showMessage",
        "language/status",
        "language/progressReport",
        "language/eventNotification",
        "telemetry/event",
    }
)

# Server->client requests we auto-answer so the server never blocks on us.
AUTO_REPLY_NULL = frozenset(
    {
        "client/registerCapability",
        "client/unregisterCapability",
        "workspace/codeLens/refresh",
        "workspace/semanticTokens/refresh",
        "workspace/inlayHint/refresh",
        "workspace/diagnostic/refresh",
        "window/workDoneProgress/create",
        "workspace/executeClientCommand",
    }
)


class LspError(RuntimeError):
    """A JSON-RPC error response, or a protocol-level failure.

    `code` is the JSON-RPC error code when the server answered with an error, and
    `request_id` the id of a request that timed out (so a caller can send
    `$/cancelRequest`). Both are None otherwise; the message text is unchanged.
    """

    def __init__(self, message: str = "", code: Optional[Any] = None, request_id: Optional[Any] = None) -> None:
        super().__init__(message)
        self.code = code
        self.request_id = request_id


@dataclass
class Notification:
    method: str
    params: Any
    at: float = field(default_factory=time.monotonic)


def norm_uri(u: str) -> str:
    if u.startswith("file:///"):
        return "file:///" + u[len("file:///") :].lstrip("/")
    return u


def same_uri(a: str, b: str) -> bool:
    return norm_uri(a) == norm_uri(b)


__all__ = [
    "ACTIVITY_METHODS",
    "AUTO_REPLY_NULL",
    "LspError",
    "Notification",
    "norm_uri",
    "same_uri",
]
