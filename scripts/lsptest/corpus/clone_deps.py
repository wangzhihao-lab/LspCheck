"""Clone and dependency phases of the corpus preparation.

- prepare_clone: git init, remote add, shallow fetch of the exact pinned SHA and
  checkout into temp/corpus/<owner>__<repo>@<sha12>/. Idempotent: a directory already
  checked out at the SHA is reported as "already-prepared" and left untouched. Every
  git call goes through subprocess directly (never as literal shell text, because this
  project's interactive shell rewrites literal `git log`/`git show` output). When the
  anonymous fetch fails and GITHUB_TOKEN is set, one retry passes the token as a
  one-shot `-c http.extraheader`; it is never written to .git/config or logged, and
  it is scrubbed from every recorded output tail.
- dependencies, never running install scripts: typescript uses the package manager
  pinned in package.json `packageManager` through corepack (which never touches global
  shims), else the one the lockfile implies (npm ci, pnpm, yarn classic or berry, bun),
  with no fallback between managers; rust `cargo fetch`; go `go mod download` with
  GOTOOLCHAIN=local, a go directive newer than the local Go being recorded as
  "go-too-new" (gopls itself gets its era Go, if any, from servers.resolve); python
  installs nothing and records whether pyproject.toml / setup.py exist.
- prepare_all: both phases for every project on a thread pool; one project's crash is
  recorded as a failed clone and never sinks the batch.

Run line: imported by scripts/lsptest/prepare_corpus.py; not run directly.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .common import CARGO_HOME, CLONE_OK, CORPUS_DIR, GOPATH_DIR, RUSTUP_BIN, CmdResult, ProjectSpec, run_cmd

logger = logging.getLogger(__name__)

COREPACK_ENV = {"COREPACK_ENABLE_DOWNLOAD_PROMPT": "0", "COREPACK_ENABLE_STRICT": "0"}


# ------------------------------------------------------------------- token
def _scrub(text: str, token: Optional[str]) -> str:
    return text.replace(token, "***") if token else text


def _auth_header(token: str) -> str:
    b = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return f"AUTHORIZATION: basic {b}"


# ------------------------------------------------------------------- clone
def _clone_already_ok(dest: str, sha: str) -> bool:
    if not os.path.isdir(os.path.join(dest, ".git")):
        return False
    try:
        r = subprocess.run(["git", "-C", dest, "rev-parse", "HEAD"], capture_output=True,
                           text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return False
    return r.returncode == 0 and r.stdout.strip() == sha


def _clone_fail(dest: str, cmd_name: str, r: CmdResult, token: Optional[str]) -> Dict[str, Any]:
    return {"status": "failed", "path": dest, "failed_cmd": cmd_name,
            "tail": _scrub(r.tail, token), "elapsed_s": round(r.elapsed_s, 1)}


def prepare_clone(owner: str, repo: str, sha: str, dest: str, token: Optional[str]) -> Dict[str, Any]:
    """git init; remote add; shallow fetch of the exact pinned SHA; checkout.
    Idempotent: a dest already checked out at `sha` is left untouched. If the
    anonymous fetch fails and GITHUB_TOKEN is set, one retry is made with the
    token passed as a one-shot `-c http.extraheader`, which is never written
    to .git/config or logged."""
    if _clone_already_ok(dest, sha):
        return {"status": "already-prepared", "path": dest}
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest, exist_ok=True)
    anon_url = f"https://github.com/{owner}/{repo}.git"

    r = run_cmd(["git", "init", "-q"], cwd=dest, timeout_s=60)
    if not r.ok:
        return _clone_fail(dest, "init", r, token)
    r = run_cmd(["git", "remote", "add", "origin", anon_url], cwd=dest, timeout_s=60)
    if not r.ok:
        return _clone_fail(dest, "remote-add", r, token)
    r = run_cmd(["git", "fetch", "--depth", "1", "origin", sha], cwd=dest, timeout_s=900)
    if not r.ok and token:
        r = run_cmd(["git", "-c", f"http.extraheader={_auth_header(token)}",
                     "fetch", "--depth", "1", "origin", sha], cwd=dest, timeout_s=900)
    if not r.ok:
        return _clone_fail(dest, "fetch", r, token)
    r = run_cmd(["git", "checkout", "-q", "FETCH_HEAD"], cwd=dest, timeout_s=120)
    if not r.ok:
        return _clone_fail(dest, "checkout", r, token)
    if not _clone_already_ok(dest, sha):
        return {"status": "failed", "path": dest, "failed_cmd": "verify",
                "tail": "HEAD sha mismatch after checkout"}
    return {"status": "ok", "path": dest}


# -------------------------------------------------------------------- deps
def _dep_result(manager: str, r: CmdResult) -> Dict[str, Any]:
    status = "ok" if r.ok else ("timeout" if r.timed_out else "failed")
    out: Dict[str, Any] = {"manager": manager, "status": status, "elapsed_s": round(r.elapsed_s, 1)}
    if not r.ok:
        out["tail"] = r.tail
    return out


def _package_manager_field(root: str) -> Optional[Tuple[str, str]]:
    """(name, version) from package.json `packageManager` ("pnpm@10.3.0+sha512...")."""
    try:
        with open(os.path.join(root, "package.json"), encoding="utf-8") as f:
            pm = json.load(f).get("packageManager")
    except (OSError, ValueError):
        return None
    if not isinstance(pm, str) or "@" not in pm:
        return None
    name, version = pm.split("+", 1)[0].split("@", 1)
    return name, version


def _yarn_lock_is_berry(root: str) -> bool:
    with open(os.path.join(root, "yarn.lock"), encoding="utf-8", errors="replace") as f:
        return "__metadata" in f.read(2000)


def _ts_install_cmd(root: str) -> Optional[Tuple[str, List[str]]]:
    """The project's own package manager when package.json pins one (run via
    corepack, which never touches global shims), else chosen by lockfile.
    Install scripts are disabled in every branch."""
    pinned = _package_manager_field(root)

    def has(name: str) -> bool:
        return os.path.exists(os.path.join(root, name))

    if pinned and pinned[0] == "pnpm":
        pm = f"pnpm@{pinned[1]}"
        return pm, ["corepack", pm, "install", "--ignore-scripts", "--frozen-lockfile"]
    if pinned and pinned[0] == "yarn" and has("yarn.lock"):
        pm = f"yarn@{pinned[1]}"
        if _yarn_lock_is_berry(root):
            return pm, ["corepack", pm, "install", "--immutable", "--mode=skip-build"]
        return pm, ["corepack", pm, "install", "--ignore-scripts", "--frozen-lockfile"]
    if has("package-lock.json"):
        return "npm-ci", ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
    if has("pnpm-lock.yaml"):
        return "pnpm@10", ["corepack", "pnpm@10", "install", "--ignore-scripts", "--frozen-lockfile"]
    if has("yarn.lock"):
        if _yarn_lock_is_berry(root):
            return "yarn@4", ["corepack", "yarn@4", "install", "--immutable", "--mode=skip-build"]
        return "yarn@1", ["corepack", "yarn@1", "install", "--ignore-scripts", "--frozen-lockfile"]
    if has("bun.lock") or has("bun.lockb"):
        return "bun@1", ["npx", "--yes", "bun@1", "install", "--ignore-scripts", "--frozen-lockfile"]
    return None


def fetch_deps_typescript(root: str) -> Dict[str, Any]:
    """Install node dependencies with the project's own package manager. No
    fallback between managers: a failure is recorded and the project moves on,
    per the corpus-prep contract."""
    choice = _ts_install_cmd(root)
    if choice is None:
        return {"manager": "none", "status": "no-lockfile", "elapsed_s": 0.0}
    manager, cmd = choice
    r = run_cmd(cmd, cwd=root, env=COREPACK_ENV, timeout_s=900)
    return _dep_result(manager, r)


def fetch_deps_rust(root: str) -> Dict[str, Any]:
    """`cargo fetch` with the Homebrew rustup proxies and ~/.cargo first on PATH."""
    env = {"PATH": RUSTUP_BIN + os.pathsep + os.path.join(CARGO_HOME, "bin") + os.pathsep + os.environ.get("PATH", ""),
           "CARGO_HOME": CARGO_HOME}
    r = run_cmd(["cargo", "fetch"], cwd=root, env=env, timeout_s=900)
    return _dep_result("cargo-fetch", r)


def _go_mod_required_version(root: str) -> Optional[str]:
    try:
        with open(os.path.join(root, "go.mod"), encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2 and parts[0] == "go":
                    return parts[1]
    except OSError:
        return None
    return None


def _looks_like_toolchain_mismatch(tail: str) -> bool:
    t = tail.lower()
    return "requires go" in t or "gotoolchain=local" in t or "invalid go version" in t


def fetch_deps_go(root: str) -> Dict[str, Any]:
    """`go mod download` into the shared GOPATH with the local toolchain only; a go
    directive the local Go cannot satisfy is recorded as status "go-too-new"."""
    env = {"GOPATH": GOPATH_DIR, "GOMODCACHE": os.path.join(GOPATH_DIR, "pkg", "mod"),
           "GOFLAGS": "-modcacherw", "GOTOOLCHAIN": "local"}
    required = _go_mod_required_version(root)
    r = run_cmd(["go", "mod", "download"], cwd=root, env=env, timeout_s=900)
    out = _dep_result("go-mod-download", r)
    if required:
        out["go_directive"] = required
    if not r.ok and _looks_like_toolchain_mismatch(r.tail):
        out["status"] = "go-too-new"
    return out


def check_python_project(root: str) -> Dict[str, Any]:
    """Nothing is installed for python; only the packaging files are recorded."""
    return {
        "manager": "none", "status": "n/a", "elapsed_s": 0.0,
        "pyproject_toml": os.path.exists(os.path.join(root, "pyproject.toml")),
        "setup_py": os.path.exists(os.path.join(root, "setup.py")),
    }


DEPS_BY_LANGUAGE: Dict[str, Callable[[str], Dict[str, Any]]] = {
    "typescript": fetch_deps_typescript, "rust": fetch_deps_rust,
    "go": fetch_deps_go, "python": check_python_project,
}


# ----------------------------------------------------------------- project
def prepare_project(p: ProjectSpec, skip_deps: bool, token: Optional[str]) -> Dict[str, Any]:
    """Clone `p` (idempotent) and fetch its dependencies unless `skip_deps`."""
    dest = os.path.join(CORPUS_DIR, p.slug)
    clone = prepare_clone(p.owner, p.repo, p.commit, dest, token)
    if clone["status"] not in CLONE_OK:
        return {"clone": clone, "path": dest, "deps": {"status": "skipped-clone-failed"}}
    if skip_deps:
        return {"clone": clone, "path": dest, "deps": {"status": "skipped-by-flag"}}
    fetch = DEPS_BY_LANGUAGE.get(p.language)
    deps = fetch(dest) if fetch is not None else {"status": "unknown-language"}
    return {"clone": clone, "path": dest, "deps": deps}


def prepare_all(projects: Sequence[ProjectSpec], skip_deps: bool, token: Optional[str],
                max_workers: int) -> Dict[str, Dict[str, Any]]:
    """prepare_project for every project, `max_workers` at a time; slug -> result."""
    prep_by_slug: Dict[str, Dict[str, Any]] = {}
    workers = max(1, min(max_workers, len(projects) or 1))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(prepare_project, p, skip_deps, token): p for p in projects}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                prep_by_slug[p.slug] = fut.result()
            except Exception as e:  # noqa: BLE001  (one project's crash must not sink the batch)
                logger.exception("prepare_project crashed for %s", p.slug)
                prep_by_slug[p.slug] = {"clone": {"status": "failed", "tail": _scrub(str(e), token)[:2000]},
                                        "path": "", "deps": {"status": "skipped-clone-failed"}}
            prep = prep_by_slug[p.slug]
            logger.info("prepared %-55s clone=%s deps=%s", p.slug, prep["clone"]["status"],
                        prep.get("deps", {}).get("status"))
    return prep_by_slug


__all__ = [
    "COREPACK_ENV", "DEPS_BY_LANGUAGE", "check_python_project", "fetch_deps_go", "fetch_deps_rust",
    "fetch_deps_typescript", "prepare_all", "prepare_clone", "prepare_project",
]
