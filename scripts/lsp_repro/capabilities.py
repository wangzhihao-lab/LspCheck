"""LSP client capabilities: what editor features the harness claims to support.

Kept separate from the transport so a scenario can declare a narrower or wider
client without touching the JSON-RPC plumbing.
"""

from __future__ import annotations

from typing import Any, Dict


def client_capabilities() -> Dict[str, Any]:
    """Capabilities of a reasonably modern editor: incremental sync + diagnostics."""
    return {
        "workspace": {
            "applyEdit": True,
            "workspaceEdit": {"documentChanges": True, "resourceOperations": ["create", "rename", "delete"]},
            "didChangeConfiguration": {"dynamicRegistration": True},
            "didChangeWatchedFiles": {"dynamicRegistration": True},
            "symbol": {"dynamicRegistration": True},
            "executeCommand": {"dynamicRegistration": True},
            "configuration": True,
            "workspaceFolders": True,
        },
        "textDocument": {
            "synchronization": {
                "dynamicRegistration": True,
                "willSave": True,
                "willSaveWaitUntil": True,
                "didSave": True,
            },
            "publishDiagnostics": {
                "relatedInformation": True,
                "versionSupport": True,
                "tagSupport": {"valueSet": [1, 2]},
                "codeDescriptionSupport": True,
                "dataSupport": True,
            },
            "completion": {
                "dynamicRegistration": True,
                "contextSupport": True,
                "completionItem": {
                    "snippetSupport": True,
                    "documentationFormat": ["markdown", "plaintext"],
                    "resolveSupport": {"properties": ["documentation", "detail"]},
                },
                "completionItemKind": {"valueSet": list(range(1, 26))},
            },
            "hover": {"dynamicRegistration": True, "contentFormat": ["markdown", "plaintext"]},
            "signatureHelp": {"dynamicRegistration": True},
            "definition": {"dynamicRegistration": True, "linkSupport": True},
            "typeDefinition": {"dynamicRegistration": True, "linkSupport": True},
            "references": {"dynamicRegistration": True},
            "documentSymbol": {"dynamicRegistration": True, "hierarchicalDocumentSymbolSupport": True},
            "codeAction": {
                "dynamicRegistration": True,
                "isPreferredSupport": True,
                "resolveSupport": {"properties": ["edit"]},
                "dataSupport": True,
                "codeActionLiteralSupport": {
                    "codeActionKind": {
                        "valueSet": [
                            "",
                            "quickfix",
                            "refactor",
                            "refactor.extract",
                            "refactor.inline",
                            "refactor.rewrite",
                            "source",
                            "source.organizeImports",
                        ]
                    }
                },
            },
            "rename": {"dynamicRegistration": True, "prepareSupport": True},
            "semanticTokens": {"dynamicRegistration": True, "requests": {"full": True}, "tokenTypes": [], "tokenModifiers": [], "formats": ["relative"]},
        },
        "window": {"workDoneProgress": True, "showMessage": {}, "showDocument": {"support": False}},
        "general": {"positionEncodings": ["utf-16"]},
    }


def extended_capabilities() -> Dict[str, Any]:
    """The default capabilities plus the features the functional-oracle tool queries:
    pull diagnostics, semantic-token delta/range, inlay hints, document highlight,
    formatting, code lens, linked editing and resolve support for completion items."""
    caps = client_capabilities()
    td = caps["textDocument"]
    td["diagnostic"] = {"dynamicRegistration": True, "relatedDocumentSupport": True}
    td["semanticTokens"] = {
        "dynamicRegistration": True,
        "requests": {"full": {"delta": True}, "range": True},
        "tokenTypes": [
            "namespace", "type", "class", "enum", "interface", "struct", "typeParameter", "parameter",
            "variable", "property", "enumMember", "event", "function", "method", "macro", "keyword",
            "modifier", "comment", "string", "number", "regexp", "operator", "decorator",
        ],
        "tokenModifiers": [
            "declaration", "definition", "readonly", "static", "deprecated", "abstract", "async",
            "modification", "documentation", "defaultLibrary",
        ],
        "formats": ["relative"],
        "multilineTokenSupport": False,
        "overlappingTokenSupport": False,
    }
    td["inlayHint"] = {"dynamicRegistration": True, "resolveSupport": {"properties": ["tooltip", "textEdits", "label.location"]}}
    td["documentHighlight"] = {"dynamicRegistration": True}
    td["formatting"] = {"dynamicRegistration": True}
    td["rangeFormatting"] = {"dynamicRegistration": True}
    td["codeLens"] = {"dynamicRegistration": True}
    td["linkedEditingRange"] = {"dynamicRegistration": True}
    td["completion"]["completionItem"]["resolveSupport"] = {
        "properties": ["documentation", "detail", "additionalTextEdits", "textEdit", "insertText"]
    }
    caps["workspace"]["diagnostics"] = {"refreshSupport": True}
    caps["workspace"]["semanticTokens"] = {"refreshSupport": True}
    caps["workspace"]["inlayHint"] = {"refreshSupport": True}
    return caps


__all__ = ["client_capabilities", "extended_capabilities"]
