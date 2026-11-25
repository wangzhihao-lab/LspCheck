"""Server specs: how to launch each pinned server build.

pyright and Eclipse JDT LS are defined here; TypeScript 6/7, rust-analyzer and
gopls live in servers_extra.py and register themselves in SERVER_FACTORY.
Installs live under temp/lsp_servers/ and are never committed.
"""

from __future__ import annotations

import glob
import os
import shutil
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from lspclient import LspClient, Notification

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVERS_DIR = os.path.join(REPO, "temp", "lsp_servers")

PYRIGHT_SETTINGS: Dict[str, Any] = {
    "python": {
        "pythonPath": shutil.which("python3") or "python3",
        "analysis": {
            "typeCheckingMode": "basic",
            "diagnosticMode": "openFilesOnly",
            "useLibraryCodeForTypes": True,
            "autoSearchPaths": True,
            "autoImportCompletions": True,
        },
    }
}

JDTLS_SETTINGS: Dict[str, Any] = {
    "java": {
        "autobuild": {"enabled": True},
        "errors": {"incompleteClasspath": {"severity": "ignore"}},
        "configuration": {"updateBuildConfiguration": "automatic", "checkProjectSettingsExclusions": False},
        "completion": {"enabled": True},
        "maven": {"downloadSources": False},
        "import": {"maven": {"enabled": True}, "gradle": {"enabled": False}},
        "trace": {"server": "off"},
        "progressReports": {"enabled": True},
    }
}


@dataclass
class ServerSpec:
    kind: str  # "pyright" | "jdtls"
    version: str
    cmd: List[str]
    settings: Dict[str, Any] = field(default_factory=dict)
    init_options: Any = None
    ready_timeout: float = 120.0
    quiet_seconds: float = 2.5
    env: Dict[str, str] = field(default_factory=dict)
    capabilities: Optional[Dict[str, Any]] = None  # None = client_capabilities() default

    @property
    def label(self) -> str:
        return f"{self.kind}-{self.version}"


# ------------------------------------------------------------------ pyright
def pyright_spec(version: str) -> ServerSpec:
    prefix = os.path.join(SERVERS_DIR, f"pyright-{version}")
    entry = os.path.join(prefix, "node_modules", "pyright", "langserver.index.js")
    if not os.path.exists(entry):
        raise FileNotFoundError(
            f"pyright {version} not installed. Run: npm install --prefix {prefix} pyright@{version}"
        )
    node = shutil.which("node") or "node"
    return ServerSpec(
        kind="pyright",
        version=version,
        cmd=[node, entry, "--stdio"],
        settings=PYRIGHT_SETTINGS,
        quiet_seconds=2.5,
        ready_timeout=90.0,
    )


# -------------------------------------------------------------------- jdtls
def jdtls_spec(version: str, java_home: Optional[str] = None, data_dir: Optional[str] = None) -> ServerSpec:
    home = os.path.join(SERVERS_DIR, f"jdtls-{version}")
    launchers = sorted(glob.glob(os.path.join(home, "plugins", "org.eclipse.equinox.launcher_*.jar")))
    if not launchers:
        raise FileNotFoundError(f"JDT LS {version} not unpacked under {home}")
    cfg = os.path.join(home, "config_mac")
    if not os.path.isdir(cfg):
        alt = sorted(glob.glob(os.path.join(home, "config_mac*")))
        cfg = alt[0] if alt else os.path.join(home, "config_ss_mac")
    java = os.path.join(java_home, "bin", "java") if java_home else (shutil.which("java") or "/usr/bin/java")
    data = data_dir or os.path.join(SERVERS_DIR, f"jdtls-ws-{version}")
    cmd = [
        java,
        "-Declipse.application=org.eclipse.jdt.ls.core.id1",
        "-Dosgi.bundles.defaultStartLevel=4",
        "-Declipse.product=org.eclipse.jdt.ls.core.product",
        "-Dlog.level=ALL",
        "-Dfile.encoding=UTF-8",
        "-Xmx1G",
        "--add-modules=ALL-SYSTEM",
        "--add-opens", "java.base/java.util=ALL-UNNAMED",
        "--add-opens", "java.base/java.lang=ALL-UNNAMED",
        "-jar", launchers[-1],
        "-configuration", cfg,
        "-data", data,
    ]
    env = {"JAVA_HOME": java_home} if java_home else {}
    return ServerSpec(
        kind="jdtls",
        version=version,
        cmd=cmd,
        settings=JDTLS_SETTINGS,
        init_options={
            "settings": JDTLS_SETTINGS,
            "extendedClientCapabilities": {
                "progressReportProvider": True,
                "classFileContentsSupport": True,
                "overrideMethodsPromptSupport": False,
                "hashCodeEqualsPromptSupport": False,
                "advancedOrganizeImportsSupport": True,
                "generateToStringPromptSupport": False,
                "advancedGenerateAccessorsSupport": True,
                "generateConstructorsPromptSupport": False,
                "generateDelegateMethodsPromptSupport": False,
                "advancedExtractRefactoringSupport": True,
                "moveRefactoringSupport": True,
                "clientHoverProvider": True,
                "clientDocumentSymbolProvider": True,
                "resolveAdditionalTextEditsSupport": True,
                "executeClientCommandSupport": True,
            },
        },
        quiet_seconds=4.0,
        ready_timeout=420.0,
        env=env,
    )


def jdtls_ready(client: LspClient, timeout: float = 420.0) -> str:
    """Wait for JDT LS's own readiness signal before trusting any result."""

    def is_ready(n: Notification) -> bool:
        if n.method != "language/status":
            return False
        t = (n.params or {}).get("type")
        return t in ("ServiceReady", "Started")

    note = client.wait_for_notification(is_ready, timeout=timeout)
    if note is None:
        return "timeout"
    kind = (note.params or {}).get("type", "?")
    if kind == "ServiceReady":
        # "Started" follows ServiceReady once the project is fully built.
        started = client.wait_for_notification(
            lambda n: n.method == "language/status" and (n.params or {}).get("type") == "Started",
            timeout=min(180.0, timeout),
        )
        if started is not None:
            return "Started"
    return kind


def start(
    spec: ServerSpec,
    root_uri: str,
    log_path: str,
    cwd: Optional[str] = None,
    extra_folder_uris: Optional[List[str]] = None,
) -> LspClient:
    client = LspClient(spec.cmd, log_path=log_path, cwd=cwd, env=spec.env, settings=spec.settings)
    try:
        client.initialize(
            root_uri,
            capabilities=spec.capabilities,
            init_options=spec.init_options,
            timeout=spec.ready_timeout,
            extra_folder_uris=extra_folder_uris,
        )
    except BaseException:
        client.stop(grace=2.0)  # a failed start must not leave the server process running
        raise
    if spec.kind == "jdtls":
        status = jdtls_ready(client, timeout=spec.ready_timeout)
        client._record("meta", {"jdtls_ready": status})
    return client


SERVER_FACTORY: Dict[str, Callable[[str], ServerSpec]] = {}


def register_server(kind: str) -> Callable[[Callable[[str], ServerSpec]], Callable[[str], ServerSpec]]:
    """Register a spec factory under a server kind name."""

    def deco(fn: Callable[[str], ServerSpec]) -> Callable[[str], ServerSpec]:
        SERVER_FACTORY[kind] = fn
        return fn

    return deco


SERVER_FACTORY["pyright"] = pyright_spec
SERVER_FACTORY["jdtls"] = lambda version: jdtls_spec(version, java_home=_jdk_for(version))


def resolve(kind: str, version: str) -> ServerSpec:
    """Spec for one pinned build of one server kind."""
    if kind not in SERVER_FACTORY:
        import servers_extra  # noqa: F401  (registers the remaining kinds)
    if kind not in SERVER_FACTORY:
        raise ValueError(f"unknown server kind: {kind}")
    return SERVER_FACTORY[kind](version)


def _jdk_for(version: str) -> Optional[str]:
    """2019-era JDT LS builds are Eclipse 4.11 and do not start on Java 17+, so
    0.x releases get the bundled JDK 11 and 1.x releases the bundled JDK 17. The
    system Java 24 is used only if neither is unpacked."""
    want = "jdk11" if version.startswith("0.") else "jdk17"
    for name in (want, "jdk17", "jdk11"):
        root = os.path.join(SERVERS_DIR, name)
        if os.path.isdir(root):
            home = _jdk_home(root)
            if home:
                return home
    return None


def _jdk_home(root: str) -> Optional[str]:
    for cand in glob.glob(os.path.join(root, "**", "bin", "java"), recursive=True):
        return os.path.dirname(os.path.dirname(cand))
    return None


__all__ = ["SERVER_FACTORY", "ServerSpec", "SERVERS_DIR", "jdtls_ready", "jdtls_spec", "pyright_spec", "register_server", "resolve", "start"]
