"""Launch specs for TypeScript 6 (typescript-language-server), TypeScript 7
(native LSP), rust-analyzer and gopls. Each factory registers itself in
servers.SERVER_FACTORY; installs live under temp/lsp_servers/<kind>-<version>/.

Run line: imported by servers.resolve(); not run directly.
"""

from __future__ import annotations

import os
import shutil
from typing import Any, Dict

from capabilities import extended_capabilities
from servers import SERVERS_DIR, ServerSpec, register_server

RUSTUP_BIN = "/opt/homebrew/opt/rustup/bin"  # keg-only Homebrew rustup proxies (cargo, rustc)
CARGO_HOME = os.path.expanduser("~/.cargo")
GOPATH_DIR = os.path.join(SERVERS_DIR, "gopath")

TS_PREFERENCES: Dict[str, Any] = {
    "includeCompletionsForModuleExports": True,
    "includeCompletionsWithInsertText": True,
    "quotePreference": "auto",
}


def _need(path: str, hint: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} missing. {hint}")
    return path


def _path_with(*dirs: str) -> str:
    return os.pathsep.join([d for d in dirs if d] + [os.environ.get("PATH", "")])


@register_server("ts6")
def ts6_spec(version: str) -> ServerSpec:
    """TypeScript <=6 through typescript-language-server (wraps tsserver.js)."""
    prefix = os.path.join(SERVERS_DIR, f"ts6-{version}", "node_modules")
    cli = _need(os.path.join(prefix, "typescript-language-server", "lib", "cli.mjs"),
                f"npm install --prefix temp/lsp_servers/ts6-{version} typescript@{version} typescript-language-server")
    tsserver = _need(os.path.join(prefix, "typescript", "lib", "tsserver.js"), "typescript not installed")
    return ServerSpec(
        kind="ts6", version=version, cmd=[shutil.which("node") or "node", cli, "--stdio"],
        init_options={"tsserver": {"path": tsserver}, "preferences": TS_PREFERENCES, "hostInfo": "headless-harness"},
        capabilities=extended_capabilities(), quiet_seconds=2.0, ready_timeout=120.0,
    )


@register_server("ts7")
def ts7_spec(version: str) -> ServerSpec:
    """TypeScript 7 native language server: `tsc --lsp --stdio` from the platform package."""
    exe = _need(os.path.join(SERVERS_DIR, f"ts7-{version}", "node_modules", "@typescript",
                             "typescript-darwin-arm64", "lib", "tsc"),
                f"npm install --prefix temp/lsp_servers/ts7-{version} typescript@{version}")
    return ServerSpec(
        kind="ts7", version=version, cmd=[exe, "--lsp", "--stdio"],
        capabilities=extended_capabilities(), quiet_seconds=2.0, ready_timeout=120.0,
    )


RA_SETTINGS: Dict[str, Any] = {
    "rust-analyzer": {
        "checkOnSave": False,          # native diagnostics only; no cargo check noise
        "cargo": {"buildScripts": {"enable": True}},
        "procMacro": {"enable": True},
        "diagnostics": {"enable": True},
    }
}


@register_server("rust-analyzer")
def rust_analyzer_spec(version: str) -> ServerSpec:
    exe = _need(os.path.join(SERVERS_DIR, f"rust-analyzer-{version}", "rust-analyzer"),
                "download the release binary into temp/lsp_servers/rust-analyzer-<tag>/")
    caps = extended_capabilities()
    caps.setdefault("experimental", {})["serverStatusNotification"] = True
    return ServerSpec(
        kind="rust-analyzer", version=version, cmd=[exe],
        settings=RA_SETTINGS, init_options=RA_SETTINGS["rust-analyzer"], capabilities=caps,
        env={"PATH": _path_with(RUSTUP_BIN, os.path.join(CARGO_HOME, "bin")), "CARGO_HOME": CARGO_HOME},
        quiet_seconds=3.0, ready_timeout=300.0,
    )


@register_server("gopls")
def gopls_spec(version: str) -> ServerSpec:
    exe = _need(os.path.join(SERVERS_DIR, f"gopls-{version}", "gopls"),
                f"GOBIN=temp/lsp_servers/gopls-{version} go install golang.org/x/tools/gopls@{version}")
    env = {"GOPATH": GOPATH_DIR, "GOMODCACHE": os.path.join(GOPATH_DIR, "pkg", "mod"),
           "GOFLAGS": "-modcacherw", "GOTOOLCHAIN": "local", "PATH": _path_with("/opt/homebrew/bin")}
    return ServerSpec(
        kind="gopls", version=version, cmd=[exe, "serve"],
        settings={"gopls": {}}, capabilities=extended_capabilities(),
        env=env, quiet_seconds=2.5, ready_timeout=180.0,
    )


__all__ = ["gopls_spec", "rust_analyzer_spec", "ts6_spec", "ts7_spec"]

# Historical benchmark builds: kind "tsserver" and era Go for old gopls (additive; the
# current builds above are launched exactly as before). See servers_bench.py.
import servers_bench  # noqa: E402,F401
