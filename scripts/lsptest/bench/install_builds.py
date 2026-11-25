"""Install the historical builds of benchmark cases under temp/lsp_servers/, one at a time.

Per kind (install directory temp/lsp_servers/<kind>-<version>/, as the registry expects):
- pyright <v>: `npm install pyright@<v>` into the directory (the npm package ships the
  language server from 1.1.52 on);
- tsserver <ts>+tsls<w>: `npm install typescript@<ts> typescript-language-server@<w>`; the
  installed versions are checked, and a typescript nested inside the wrapper is reported
  (the launch spec names the pinned tsserver.js explicitly anyway);
- rust-analyzer <date>: the GitHub release asset rust-analyzer-aarch64-apple-darwin.gz of
  that weekly tag, unpacked to rust-analyzer-<date>/rust-analyzer;
- gopls <v> [--go goX.Y.Z]: with an era Go, that toolchain is installed through
  golang.org/dl into temp/lsp_servers/go-sdks/ (the wrapper's HOME points there, so the
  SDK lands in go-sdks/sdk/<go>; nothing is installed system-wide), gopls is built with
  it (`go install`, or a wrapper module for releases whose go.mod replaces x/tools), and
  toolchain.json tells servers_bench.py to run the server with that Go first on PATH.
  Without --go the local Go builds it and no toolchain.json is written;
- jdtls <v>: checks the unpacked release (unpacks temp/lsp_servers/jdt-language-server-
  <v>-*.tar.gz when only the tarball is there).
Every attempt is recorded in data/lsp_bench/builds.json (ok, path, toolchain, detail).

Run line: python3 scripts/lsptest/bench/install_builds.py --case data/lsp_bench/cases/<id> | --all | <kind> <version> [--go go1.20.4]
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
for _p in (PKG, os.path.join(os.path.dirname(PKG), "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from servers import SERVERS_DIR  # noqa: E402
from servers_bench import GO_SDKS_DIR, TOOLCHAIN_FILE, split_tsserver_version, tsserver_install_dir  # noqa: E402
from bench.filelock import locked  # noqa: E402

REPO = os.path.abspath(os.path.join(PKG, "..", ".."))
BUILDS_JSON = os.path.join(REPO, "data", "lsp_bench", "builds.json")
LOG_DIR = os.path.join(REPO, "temp", "lsp_bench", "install_logs")
GOPATH_DIR = os.path.join(SERVERS_DIR, "gopath")
RA_ASSET = "https://github.com/rust-lang/rust-analyzer/releases/download/{tag}/rust-analyzer-aarch64-apple-darwin.gz"
NPM_FLAGS = ["--no-save", "--no-audit", "--no-fund", "--no-package-lock", "--loglevel=error"]
CMD_TIMEOUT_S = 1800

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BuildResult:
    kind: str
    version: str
    ok: bool
    path: str = ""
    toolchain: str = ""
    detail: str = ""
    installed_at: str = ""


class InstallError(RuntimeError):
    """A build could not be installed; the message says why."""


def _stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _run(cmd: Sequence[str], log_name: str, env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None) -> str:
    """Run a command (bounded), append its output to the install log; InstallError on failure."""
    os.makedirs(LOG_DIR, exist_ok=True)
    full_env = dict(os.environ)
    full_env.pop("GITHUB_TOKEN", None)  # installers never need it
    full_env.update(env or {})
    try:
        proc = subprocess.run(list(cmd), capture_output=True, text=True, env=full_env, cwd=cwd, timeout=CMD_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstallError(f"{os.path.basename(cmd[0])} failed to run: {exc}") from exc
    with open(os.path.join(LOG_DIR, f"{log_name}.log"), "a", encoding="utf-8") as f:
        f.write(f"$ {' '.join(cmd)}\n{proc.stdout}{proc.stderr}\n[exit {proc.returncode}]\n")
    if proc.returncode != 0:
        lines = [ln for ln in (proc.stderr or proc.stdout).splitlines() if ln.strip()]
        raise InstallError(f"{' '.join(cmd[:3])} exited {proc.returncode}: {' | '.join(lines[-3:])[:400]}")
    return proc.stdout


def _package_version(prefix: str, name: str) -> str:
    path = os.path.join(prefix, "node_modules", name, "package.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return str(json.load(f).get("version", ""))
    except (OSError, ValueError):
        return ""


def _npm_install(prefix: str, packages: Sequence[str], log_name: str, extra: Sequence[str] = ()) -> None:
    os.makedirs(prefix, exist_ok=True)
    _run(["npm", "install", "--prefix", prefix, *NPM_FLAGS, *extra, *packages], log_name)


WRAPPER_TIMES = os.path.join(HERE, "..", "..", "..", "temp", "lsp_bench", "cache", "npm_time_typescript-language-server.json")


def wrapper_before(wrapper: str) -> Optional[str]:
    """For typescript-language-server < 0.6: one day after the wrapper's release (npm --before), so
    its open ranges (vscode-languageserver ^5.3.0-next) resolve as they did then; today they pull
    protocol 3.18 / jsonrpc 9, which crash the wrapper at start. None for newer wrappers."""
    nums = [int(x) for x in wrapper.split(".")[:2] if x.isdigit()]
    if len(nums) < 2 or (nums[0], nums[1]) >= (0, 6):
        return None
    try:
        with open(WRAPPER_TIMES, encoding="utf-8") as f:
            times = json.load(f)
    except (OSError, ValueError):
        times = json.loads(_run(["npm", "view", "typescript-language-server", "time", "--json"], "npm-time-tsls"))
    stamp = times.get(wrapper)
    if not stamp:
        raise InstallError(f"no npm release time for typescript-language-server {wrapper}")
    day = time.strptime(stamp[:10], "%Y-%m-%d")
    return time.strftime("%Y-%m-%d", time.gmtime(time.mktime(day) + 2 * 86400))


# ------------------------------------------------------------------ per kind
def install_pyright(version: str, force: bool = False, go: str = "") -> BuildResult:
    prefix = os.path.join(SERVERS_DIR, f"pyright-{version}")
    entry = os.path.join(prefix, "node_modules", "pyright", "langserver.index.js")
    if force or not os.path.exists(entry):
        _npm_install(prefix, [f"pyright@{version}"], f"pyright-{version}")
    got = _package_version(prefix, "pyright")
    if got != version or not os.path.exists(entry):
        raise InstallError(f"pyright {version}: installed {got or 'nothing'}, langserver entry "
                           f"{'present' if os.path.exists(entry) else 'missing'} (npm ships it from 1.1.52)")
    return BuildResult("pyright", version, True, prefix, detail=f"npm pyright@{got}")


def install_tsserver(version: str, force: bool = False, go: str = "") -> BuildResult:
    ts_version, wrapper = split_tsserver_version(version)
    prefix = tsserver_install_dir(version)
    if force or _package_version(prefix, "typescript") != ts_version \
            or _package_version(prefix, "typescript-language-server") != wrapper:
        before = wrapper_before(wrapper)
        if before:  # typescript as a tarball URL: the date filter would reject a newer typescript
            shutil.rmtree(prefix, ignore_errors=True)  # a lockfile from an earlier install would pin today's versions
            _npm_install(prefix, [f"https://registry.npmjs.org/typescript/-/typescript-{ts_version}.tgz",
                                  f"typescript-language-server@{wrapper}"], f"tsserver-{version}", [f"--before={before}"])
        else:
            _npm_install(prefix, [f"typescript@{ts_version}", f"typescript-language-server@{wrapper}"], f"tsserver-{version}")
    got_ts, got_ls = _package_version(prefix, "typescript"), _package_version(prefix, "typescript-language-server")
    if (got_ts, got_ls) != (ts_version, wrapper):
        raise InstallError(f"tsserver {version}: installed typescript {got_ts or '-'}, wrapper {got_ls or '-'}")
    nested = os.path.join(prefix, "node_modules", "typescript-language-server", "node_modules", "typescript")
    note = f"; wrapper carries its own typescript {nested} (not used: tsserver.js is named explicitly)" \
        if os.path.isdir(nested) else ""
    return BuildResult("tsserver", version, True, prefix, detail=f"npm typescript@{got_ts} typescript-language-server@{got_ls}{note}")


def install_rust_analyzer(version: str, force: bool = False, go: str = "") -> BuildResult:
    home = os.path.join(SERVERS_DIR, f"rust-analyzer-{version}")
    exe = os.path.join(home, "rust-analyzer")
    if force or not os.path.exists(exe):
        url = RA_ASSET.format(tag=version)
        os.makedirs(home, exist_ok=True)
        tmp = exe + ".download"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lsp-bench"}),
                                        timeout=300) as resp, open(tmp, "wb") as out:
                out.write(gzip.decompress(resp.read()))
        except (OSError, EOFError) as exc:
            raise InstallError(f"rust-analyzer {version}: cannot fetch {url}: {exc}") from exc
        os.chmod(tmp, 0o755)
        os.replace(tmp, exe)
    out = _run([exe, "--version"], f"rust-analyzer-{version}").strip()
    return BuildResult("rust-analyzer", version, True, home, detail=f"release asset; {out[:80]}")


def ensure_go(go: str) -> str:
    """GOROOT of an era Go (e.g. go1.20.4) installed through golang.org/dl under go-sdks/."""
    goroot = os.path.join(GO_SDKS_DIR, "sdk", go)
    if os.path.exists(os.path.join(goroot, "bin", "go")):
        return goroot
    gobin = os.path.join(GO_SDKS_DIR, "bin")
    env = {"GOBIN": gobin, "GOPATH": os.path.join(GO_SDKS_DIR, "gopath"), "GOTOOLCHAIN": "local",
           "GOFLAGS": "-modcacherw", "GOCACHE": os.path.join(GO_SDKS_DIR, "cache", "local")}
    _run(["go", "install", f"golang.org/dl/{go}@latest"], f"go-{go}", env)
    _run([os.path.join(gobin, go), "download"], f"go-{go}", {"HOME": GO_SDKS_DIR})
    if not os.path.exists(os.path.join(goroot, "bin", "go")):
        raise InstallError(f"{go}: golang.org/dl download finished but {goroot}/bin/go is missing")
    return goroot


def _gopls_env(goroot: str, gobin: str, go: str) -> Dict[str, str]:
    env = {"GOBIN": gobin, "GOPATH": GOPATH_DIR, "GOMODCACHE": os.path.join(GOPATH_DIR, "pkg", "mod"),
           "GOFLAGS": "-modcacherw", "GO111MODULE": "on", "GOTOOLCHAIN": "local",
           "GOCACHE": os.path.join(GO_SDKS_DIR, "cache", go or "local")}
    if goroot:
        env["GOROOT"] = goroot
        env["PATH"] = os.pathsep.join([os.path.join(goroot, "bin"), os.environ.get("PATH", "")])
    return env


def install_gopls(version: str, force: bool = False, go: str = "") -> BuildResult:
    home = os.path.join(SERVERS_DIR, f"gopls-{version}")
    exe = os.path.join(home, "gopls")
    goroot = ensure_go(go) if go else ""
    env = _gopls_env(goroot, home, go)
    method = "existing"
    if force or not os.path.exists(exe):
        os.makedirs(home, exist_ok=True)
        try:
            _run(["go", "install", f"golang.org/x/tools/gopls@{version}"], f"gopls-{version}", env)
            method = "go install"
        except InstallError as exc:
            if "replace" not in str(exc):
                raise
            work = os.path.join(GO_SDKS_DIR, "wrap", version)
            shutil.rmtree(work, ignore_errors=True)
            os.makedirs(work)
            for cmd in (["go", "mod", "init", "wrap.example/gopls"], ["go", "get", f"golang.org/x/tools/gopls@{version}"],
                        ["go", "build", "-o", exe, "golang.org/x/tools/gopls"]):
                _run(cmd, f"gopls-{version}", env, cwd=work)
            method = "wrapper module"
    marker = os.path.join(home, TOOLCHAIN_FILE)
    if go:
        with open(marker, "w", encoding="utf-8") as f:
            json.dump({"go": go, "goroot": goroot, "built_with": go, "method": method, "installed": _stamp()}, f, indent=1)
    elif os.path.exists(marker) and force:
        os.remove(marker)
    out = _run([exe, "version"], f"gopls-{version}", env).strip().splitlines()
    return BuildResult("gopls", version, True, home, toolchain=go or "local",
                       detail=f"{method}; {out[1].strip() if len(out) > 1 else (out or [''])[0]}")


def install_jdtls(version: str, force: bool = False, go: str = "") -> BuildResult:
    home = os.path.join(SERVERS_DIR, f"jdtls-{version}")
    if not glob.glob(os.path.join(home, "plugins", "org.eclipse.equinox.launcher_*.jar")):
        tarballs = sorted(glob.glob(os.path.join(SERVERS_DIR, f"jdt-language-server-{version}-*.tar.gz")))
        if not tarballs:
            raise InstallError(f"jdtls {version}: neither {home} nor a tarball in {SERVERS_DIR}")
        os.makedirs(home, exist_ok=True)
        with tarfile.open(tarballs[-1]) as tf:
            tf.extractall(home, filter="data")
    return BuildResult("jdtls", version, True, home, detail="unpacked release")


INSTALLERS: Dict[str, Callable[..., BuildResult]] = {
    "pyright": install_pyright, "tsserver": install_tsserver, "rust-analyzer": install_rust_analyzer,
    "gopls": install_gopls, "jdtls": install_jdtls,
}


# ------------------------------------------------------------------ status file and CLI
def load_status() -> Dict[str, Dict[str, object]]:
    try:
        with open(BUILDS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def record(result: BuildResult) -> None:
    os.makedirs(os.path.dirname(BUILDS_JSON), exist_ok=True)
    with locked():  # read-modify-write: other case writers may record builds at the same time
        status = load_status()
        status[f"{result.kind}-{result.version}"] = {k: v for k, v in asdict(result).items() if k not in ("kind", "version")}
        with open(BUILDS_JSON, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(status.items())), f, indent=1)


def install(kind: str, version: str, go: str = "", force: bool = False) -> BuildResult:
    """Install one build (never raises: failures come back as ok=False and are recorded)."""
    if kind not in INSTALLERS:
        result = BuildResult(kind, version, False, detail=f"no installer for kind {kind!r}")
    else:
        t0 = time.monotonic()
        try:
            result = INSTALLERS[kind](version, force=force, go=go)
        except (InstallError, OSError, ValueError) as exc:
            result = BuildResult(kind, version, False, toolchain=go, detail=str(exc)[:500])
        logger.info("%s %s: %s (%.0fs) %s", kind, version, "ok" if result.ok else "FAILED",
                    time.monotonic() - t0, result.detail[:160])
    result = BuildResult(**dict(asdict(result), installed_at=_stamp()))
    record(result)
    return result


def builds_for_case(case_dir: str) -> List[Dict[str, str]]:
    from bench.case_format import load_case  # late import: the CLI also works without a case
    case = load_case(case_dir)
    go = str(case.meta.get("toolchain") or "")
    return [{"kind": str(case.meta["kind"]), "version": str(case.meta[k]), "go": go} for k in ("pre_build", "post_build")]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Install historical language-server builds (sequentially).")
    ap.add_argument("build", nargs="*", help="<kind> <version>")
    ap.add_argument("--go", default="", help="era Go for gopls, e.g. go1.20.4")
    ap.add_argument("--case", action="append", default=[], help="a case directory (its pre and post builds)")
    ap.add_argument("--all", action="store_true", help="every case under data/lsp_bench/cases")
    ap.add_argument("--force", action="store_true", help="reinstall even when present")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    todo: List[Dict[str, str]] = []
    if len(args.build) == 2:
        todo.append({"kind": args.build[0], "version": args.build[1], "go": args.go})
    elif args.build:
        ap.error("give <kind> <version>")
    cases = list(args.case)
    if args.all:
        cases += sorted(glob.glob(os.path.join(REPO, "data", "lsp_bench", "cases", "*", "case.json")))
    for c in cases:
        todo += builds_for_case(os.path.dirname(c) if c.endswith("case.json") else c)
    seen, failed = set(), 0
    for item in todo:
        key = (item["kind"], item["version"])
        if key in seen:
            continue
        seen.add(key)
        failed += 0 if install(item["kind"], item["version"], item["go"], args.force).ok else 1
    print(f"{len(seen)} builds, {failed} failed; status in {os.path.relpath(BUILDS_JSON, REPO)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
