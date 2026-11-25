"""Check that gopls releases used as pre-fix / post-fix builds actually compile.

For each gopls version:
  1. local toolchain (GOTOOLCHAIN=local): ``go install golang.org/x/tools/gopls@vX``;
     releases whose go.mod carries ``replace golang.org/x/tools => ../``
     (v0.1.0-v0.5.3, v0.6.8) are refused by ``go install`` since Go 1.16, so
     they are built from a wrapper module instead
     (``go mod init``; ``go get golang.org/x/tools/gopls@vX``; ``go build``);
  2. if that fails, the same with downloaded toolchains (``GOTOOLCHAIN``):
     the release's go.mod ``go`` version, the .0 release of its Go era, and
     go1.21.0 (the oldest downloadable one), skipping any below the directive.
A failure whose log shows a network error (proxy fetch, TLS, DNS) is retried
and never cached as a build failure. Binaries are deleted after a successful
build; results are cached in
temp/lsp_bench/cache/gopls_builds.json and folded into build_notes and
builds_obtainable by ``mine_candidates.py build``. Module and build caches
live under temp/lsp_bench/gobuild (delete freely).

Run line: python3 scripts/lsp_bench/mine_candidates.py build --check-gopls-builds
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from paths import CACHE_DIR, TEMP_DIR
from versions_gopls import go_era, releases

logger = logging.getLogger(__name__)

RESULTS = CACHE_DIR / "gopls_builds.json"
WORK = TEMP_DIR / "gobuild"
_LOCK = threading.Lock()


def load_results() -> Dict[str, dict]:
    """Cached build results: version -> {ok, toolchain, method, error}."""
    if RESULTS.exists():
        return json.loads(RESULTS.read_text(encoding="utf-8"))
    return {}


_LOCAL_VERSION: Dict[str, str] = {}


def local_go_version() -> str:
    """Version string of the local go command (e.g. go1.27.1)."""
    if "v" not in _LOCAL_VERSION:
        proc = subprocess.run(["go", "env", "GOVERSION"], capture_output=True, text=True, timeout=60,
                              env={**os.environ, "GOTOOLCHAIN": "local"})
        _LOCAL_VERSION["v"] = proc.stdout.strip() or "local"
    return _LOCAL_VERSION["v"]


def _env(toolchain: str, gobin: Path) -> Dict[str, str]:
    env = dict(os.environ)
    env.pop("GITHUB_TOKEN", None)
    env.update({"GOTOOLCHAIN": toolchain, "GOPATH": str(WORK / "gopath"),
                "GOMODCACHE": str(WORK / "gopath" / "pkg" / "mod"), "GOCACHE": str(WORK / "cache"),
                "GOFLAGS": "-modcacherw", "GOBIN": str(gobin), "GO111MODULE": "on"})
    return env


def _first_error(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith(("go: downloading", "go: added", "go: finding"))]
    return " | ".join(lines[:2])[:300]


_NETWORK = re.compile(r'Get "https?://|dial tcp|TLS handshake|connection reset|unexpected EOF|i/o timeout|'
                      r'no such host|server misbehaving|net/http|EOF$', re.M)
NETWORK_TRIES = 4


def _attempt(version: str, toolchain: str, wrapper: bool) -> Dict[str, object]:
    """One build attempt, repeated while the go command fails for network reasons."""
    res: Dict[str, object] = {}
    for k in range(NETWORK_TRIES):
        res = _attempt_once(version, toolchain, wrapper)
        if res["ok"] or not res.get("network"):
            return res
        time.sleep(5 * (k + 1))
    return res


def _attempt_once(version: str, toolchain: str, wrapper: bool) -> Dict[str, object]:
    out_dir = WORK / "try" / f"{version}-{toolchain}"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = _env(toolchain, out_dir / "bin")
    if wrapper:
        cmds = [["go", "mod", "init", "wrap.example/gopls"],
                ["go", "get", f"golang.org/x/tools/gopls@{version}"],
                ["go", "build", "-o", str(out_dir / "bin" / "gopls"), "golang.org/x/tools/gopls"]]
    else:
        cmds = [["go", "install", f"golang.org/x/tools/gopls@{version}"]]
    log = ""
    ok = True
    for cmd in cmds:
        proc = subprocess.run(cmd, cwd=out_dir, env=env, capture_output=True, text=True, timeout=1800)
        log += proc.stdout + proc.stderr
        if proc.returncode != 0:
            ok = False
            break
    ok = ok and (out_dir / "bin" / "gopls").exists()
    shutil.rmtree(out_dir, ignore_errors=True)
    label = f"local {local_go_version()}" if toolchain == "local" else toolchain
    return {"ok": ok, "toolchain": label, "method": "wrapper module" if wrapper else "go install",
            "error": "" if ok else _first_error(log), "network": (not ok) and bool(_NETWORK.search(log))}


def _vkey(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def _toolchains(directive: str, era: str) -> List[str]:
    """Downloadable toolchains to try, never older than the go.mod ``go`` directive.

    Order: the directive itself (a release's minimum), the era's .0 release, then
    go1.21.0 (the oldest toolchain the go command can download)."""
    floor = directive if directive.count(".") == 2 else (directive + ".0" if directive else "")
    out: List[str] = []
    for v in (floor, f"{era}.0" if era else "", "1.21.0"):
        if not v or _vkey(v) < (1, 21, 0):
            continue
        if floor and _vkey(v) < _vkey(floor):
            continue
        if f"go{v}" not in out:
            out.append(f"go{v}")
    return out


def check_version(version: str) -> Dict[str, object]:
    """Build one gopls version, retrying with its era toolchain when needed."""
    rel = next((r for r in releases() if r.version == version), None)
    if rel is None:
        return {"ok": False, "toolchain": "", "method": "", "error": "not on proxy.golang.org"}
    first = _attempt(version, "local", rel.has_replace)
    if first["ok"] or first.get("network"):
        return first
    era = go_era(rel.date) or ""
    toolchains = _toolchains(rel.go_directive or "", era)
    last: Dict[str, object] = first
    for tc in toolchains:
        last = _attempt(version, tc, rel.has_replace)
        last["local_error"] = first["error"]
        if last["ok"] or last.get("network"):
            return last
    last["note"] = f"failed with the local toolchain and with {', '.join(toolchains)}; era go{era}"
    return last


def check_versions(versions: Iterable[str], jobs: int = 2) -> Dict[str, dict]:
    """Check every version not yet in the cache; return all cached results."""
    results = load_results()
    todo: List[str] = sorted({v for v in versions if v and v not in results})
    if not todo:
        return results
    logger.info("building %d gopls versions (%d jobs)", len(todo), jobs)
    WORK.mkdir(parents=True, exist_ok=True)

    def run(v: str) -> None:
        res = check_version(v)
        if res.get("network"):
            logger.warning("gopls %s: network failure, result not cached: %s", v, str(res.get("error", ""))[:160])
            return
        with _LOCK:
            results[v] = res
            RESULTS.parent.mkdir(parents=True, exist_ok=True)
            RESULTS.write_text(json.dumps(results, indent=1, sort_keys=True), encoding="utf-8")
        logger.info("gopls %s: %s with %s (%s) %s", v, "ok" if res["ok"] else "FAILED", res["toolchain"],
                    res["method"], res.get("error", "")[:120])

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(run, todo))
    return results


def annotate(pre: Optional[str], post: Optional[str], results: Dict[str, dict]) -> Optional[str]:
    """Build-check note for a pre/post pair, or None when either was not checked."""
    parts = []
    for label, v in (("pre", pre), ("post", post)):
        r = results.get(v or "")
        if r is None:
            return None
        state = f"builds with {r['toolchain']} via {r['method']}" if r["ok"] else f"build FAILED ({r.get('error', '')[:120]})"
        parts.append(f"{label} {v} {state}")
    return "; ".join(parts)


def both_ok(pre: Optional[str], post: Optional[str], results: Dict[str, dict]) -> Optional[bool]:
    """True/False when both versions were checked, else None."""
    a, b = results.get(pre or ""), results.get(post or "")
    if a is None or b is None:
        return None
    return bool(a["ok"] and b["ok"])
