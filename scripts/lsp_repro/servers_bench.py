"""Launch specs for historical (pinned pre-fix / post-fix) builds of the benchmark.

Registered from the last line of servers_extra.py; nothing here changes how the current
builds (pyright 1.1.414, ts6 6.0.3, ts7 7.0.2, rust-analyzer 2026-09-21, gopls v0.23.0)
are launched:

- kind "tsserver": TypeScript <= 6 through a pinned typescript-language-server, version
  string "<typescript version>+tsls<wrapper version>", installed (by
  scripts/lsptest/bench/install_builds.py) under temp/lsp_servers/tsserver-<version>/. The
  wrapper is started with the pinned tsserver.js named explicitly (CLI flag before
  wrapper 4.0, initializationOptions.tsserver.path from 2.0), so neither a global
  tsserver nor a workspace copy can be picked up. Completion preferences are the
  editor defaults the wrappers ship from 1.0 on, passed explicitly so that older
  wrappers get the same.
- kind "gopls": the registered factory is wrapped. When the install directory holds
  toolchain.json (written by install_builds.py for builds that need a Go of their own
  era), the server runs with that Go first on PATH, GOROOT set to it and a build cache
  of its own under temp/lsp_servers/go-sdks/cache/. Without the file (every current
  build) the spec is returned unchanged.

pyright and rust-analyzer factories are version-generic already (temp/lsp_servers/
pyright-<v>/, temp/lsp_servers/rust-analyzer-<date>/).

Run line: imported by servers_extra.py (registration); not run directly.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
from typing import Any, Callable, Dict, Optional, Tuple

from capabilities import extended_capabilities
from servers import SERVER_FACTORY, SERVERS_DIR, ServerSpec, register_server

TOOLCHAIN_FILE = "toolchain.json"
GO_SDKS_DIR = os.path.join(SERVERS_DIR, "go-sdks")
TSLS_SEP = "+tsls"
# Editor-default completion preferences (the DEFAULT_TSSERVER_PREFERENCES of
# typescript-language-server 1.x-6.x, completion subset), sent to every wrapper version.
TSSERVER_PREFERENCES: Dict[str, Any] = {
    "includeCompletionsForModuleExports": True,
    "includeCompletionsForImportStatements": True,
    "includeCompletionsWithInsertText": True,
    "includeCompletionsWithSnippetText": True,
    "includeCompletionsWithClassMemberSnippets": True,
    "includeCompletionsWithObjectLiteralMethodSnippets": True,
    "includeAutomaticOptionalChainCompletions": True,
    "allowIncompleteCompletions": True,
    "importModuleSpecifierPreference": "shortest",
    "importModuleSpecifierEnding": "auto",
    "quotePreference": "auto",
}


def split_tsserver_version(version: str) -> Tuple[str, str]:
    """("5.0.4", "3.3.2") from "5.0.4+tsls3.3.2"; ValueError when the wrapper is not named."""
    if TSLS_SEP not in version:
        raise ValueError(f"tsserver version must look like <typescript>{TSLS_SEP}<wrapper>, got {version!r}")
    ts_version, wrapper = version.rsplit(TSLS_SEP, 1)
    if not ts_version or not wrapper:
        raise ValueError(f"bad tsserver version {version!r}")
    return ts_version, wrapper


def _major_minor(version: str) -> Tuple[int, int]:
    parts = (version.split("-")[0].split(".") + ["0", "0"])[:2]
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return 0, 0


def tsserver_install_dir(version: str) -> str:
    return os.path.join(SERVERS_DIR, f"tsserver-{version}")


def tsserver_paths(version: str) -> Tuple[str, str]:
    """(wrapper CLI script, pinned tsserver.js) of an installed tsserver build."""
    split_tsserver_version(version)
    prefix = os.path.join(tsserver_install_dir(version), "node_modules")
    lib = os.path.join(prefix, "typescript-language-server", "lib")
    cli = next((os.path.join(lib, n) for n in ("cli.mjs", "cli.js") if os.path.exists(os.path.join(lib, n))), "")
    tsserver = os.path.join(prefix, "typescript", "lib", "tsserver.js")
    if not cli or not os.path.exists(tsserver):
        raise FileNotFoundError(f"tsserver {version} not installed under {tsserver_install_dir(version)}. "
                                f"Run: python3 scripts/lsptest/bench/install_builds.py tsserver {version}")
    return cli, tsserver


@register_server("tsserver")
def tsserver_spec(version: str) -> ServerSpec:
    """TypeScript (tsserver) behind a pinned typescript-language-server (module docstring)."""
    _, wrapper = split_tsserver_version(version)
    cli, tsserver = tsserver_paths(version)
    cmd = [shutil.which("node") or "node", cli, "--stdio"]
    major, minor = _major_minor(wrapper)
    if major < 4:
        cmd += ["--tsserver-path", tsserver]
    init: Dict[str, Any] = {"preferences": dict(TSSERVER_PREFERENCES), "hostInfo": "headless-harness"}
    if major >= 2:
        init["tsserver"] = {"path": tsserver}
    return ServerSpec(kind="tsserver", version=version, cmd=cmd, init_options=init,
                      capabilities=extended_capabilities(), quiet_seconds=2.0, ready_timeout=120.0)


# ------------------------------------------------------------------ era toolchains for gopls
def read_toolchain(kind: str, version: str) -> Optional[Dict[str, Any]]:
    """The toolchain.json of an install directory, or None when there is none."""
    path = os.path.join(SERVERS_DIR, f"{kind}-{version}", TOOLCHAIN_FILE)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else None


def with_era_go(spec: ServerSpec, info: Dict[str, Any]) -> ServerSpec:
    """The spec with the era Go of `info` ({"go": "go1.20.4", "goroot": ...}) first on PATH."""
    goroot = str(info.get("goroot") or "")
    if not os.path.exists(os.path.join(goroot, "bin", "go")):
        raise FileNotFoundError(f"era Go for {spec.label} missing at {goroot}; rerun install_builds.py")
    env = dict(spec.env)
    env["PATH"] = os.pathsep.join([os.path.join(goroot, "bin"), env.get("PATH") or os.environ.get("PATH", "")])
    env["GOROOT"] = goroot
    env["GOCACHE"] = os.path.join(GO_SDKS_DIR, "cache", str(info.get("go") or "unknown"))
    return dataclasses.replace(spec, env=env)


def _era_aware(base: Callable[[str], ServerSpec]) -> Callable[[str], ServerSpec]:
    def factory(version: str) -> ServerSpec:
        spec = base(version)
        info = read_toolchain(spec.kind, version)
        return with_era_go(spec, info) if info else spec

    factory.__wrapped__ = base  # type: ignore[attr-defined]
    factory.__doc__ = f"{base.__doc__ or ''} (era Go from {TOOLCHAIN_FILE} when present)"
    return factory


if "gopls" in SERVER_FACTORY and not hasattr(SERVER_FACTORY["gopls"], "__wrapped__"):
    SERVER_FACTORY["gopls"] = _era_aware(SERVER_FACTORY["gopls"])


__all__ = ["GO_SDKS_DIR", "TOOLCHAIN_FILE", "TSSERVER_PREFERENCES", "read_toolchain", "split_tsserver_version",
           "tsserver_install_dir", "tsserver_paths", "tsserver_spec", "with_era_go"]
