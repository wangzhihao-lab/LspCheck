"""Replay the gopls bug groups on the gopls development head (post-freeze evidence; the frozen tool is only imported).

Why: the maintainers fixed C6 and C7 after gopls v0.24.0 was cut (golang/go#81810, #81809; the fixes are on the
development head only, see plan/upstream/README.md 2026-11-18). Replaying every gopls bug group on a build of the head
shows, with our own replays, whether those fixes remove the groups, and whether anything else changed on the head.

Rule (fixed before any result): the build is golang.org/x/tools/gopls at the pseudo-version that `go list -m` resolves
for @master on the given date, compiled and run with the local Go as the newest-release builds are; every gopls group
of triage/root_causes.csv, 3 replays each, through release_sweep.replay (the frozen sweep's replay path) under the
same job lock (release_sweep.slot), so the solo C2 job of a concurrent sweep is respected.

Output: data/lsptest/runs/main_v1/sweep/head-<date>/releases.json (one build, role "development head"), results.jsonl
(release_sweep row schema) and summary.md (release_sweep.summarize).

Run line: python3 scripts/paper/evidence/head_check.py --date 2026-11-18
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True  # no new bytecode caches inside the frozen tree

import release_sweep as rs  # noqa: E402
from release_builds import REPO, RUN_ROOT, SWEEP, go_of, go_skips, smoke_servers, write_text  # noqa: E402
import servers  # noqa: E402  (frozen tool, read-only; on sys.path through release_builds)
from bench import install_builds as ib  # noqa: E402

logger = logging.getLogger("head_check")
MODULE = "golang.org/x/tools/gopls"


def head_version() -> Dict[str, str]:
    """{"version": pseudo-version, "time": commit time} of the gopls module at @master (module proxy)."""
    out = subprocess.run(["go", "list", "-m", "-json", f"{MODULE}@master"], capture_output=True, text=True,
                         timeout=600, check=True, env=dict(os.environ, GOFLAGS="-mod=mod", GO111MODULE="on"))
    doc = json.loads(out.stdout)
    return {"version": doc["Version"], "time": doc.get("Time", "")}


def install(version: str) -> Dict[str, Any]:
    """Build gopls at the pseudo-version under temp/lsp_servers/gopls-<version>/ and run the launch check.

    On the development head, gopls/go.mod replaces golang.org/x/tools with the enclosing checkout (`=> ../`), so
    `go install ...@<pseudo-version>` refuses it; the build is made the way gopls contributors make it: a checkout of
    golang/tools at the commit, then `go build` in its gopls module (the replace then applies, as on the head)."""
    home = os.path.join(servers.SERVERS_DIR, f"gopls-{version}")
    exe = os.path.join(home, "gopls")
    if not os.path.exists(exe):
        commit = version.rsplit("-", 1)[-1]
        src = os.path.join(REPO, "temp", "gopls_head_src", commit)
        log = f"gopls-{version}"
        if not os.path.isdir(os.path.join(src, "gopls")):
            shutil.rmtree(src, ignore_errors=True)
            os.makedirs(os.path.dirname(src), exist_ok=True)
            ib._run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                     "https://github.com/golang/tools", src], log)
            ib._run(["git", "-C", src, "checkout", "--quiet", "--detach", commit], log)
        os.makedirs(home, exist_ok=True)
        ib._run(["go", "build", "-o", exe, "."], log, ib._gopls_env("", home, ""), cwd=os.path.join(src, "gopls"))
    smoke = smoke_servers.smoke("gopls", version, "go")
    if not smoke.get("ok"):
        raise RuntimeError(f"launch check failed for gopls {version}: {smoke.get('error')}")
    return {"launch": {k: smoke[k] for k in ("init_s", "ok", "diagnostics", "error") if k in smoke},
            "built_with": go_of(["go", "version", servers.resolve("gopls", version).cmd[0]])}


def gopls_groups() -> List[Dict[str, str]]:
    with open(os.path.join(RUN_ROOT, "triage", "root_causes.csv"), newline="", encoding="utf-8") as f:
        return [{"cause": r["cause"], "line": r["server"], "gid": r["group"]} for r in csv.DictReader(f)
                if r["server"] == "gopls"]


def plan(date: str) -> Dict[str, Any]:
    """Write sweep/head-<date>/releases.json with the installed head build (or load it when it exists)."""
    label = f"head-{date}"
    path = os.path.join(SWEEP, label, "releases.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    head = head_version()
    version = head["version"]
    build: Dict[str, Any] = {"line": "gopls", "kind": "gopls", "version": version, "release": version,
                             "tag": "h" + version.rsplit("-", 1)[-1][:7], "released": head["time"][:10],
                             "roles": ["development head"], "status": "planned"}
    try:
        build.update(install(version), status="ok",
                     detail=f"go build in the gopls module of a golang/tools checkout at {version.rsplit('-', 1)[-1]} "
                            "with the local Go")
        groups = gopls_groups()
        build["go"], build["skip"] = go_skips(version, [g["gid"] for g in groups])
    except (ib.InstallError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        build.update(status="unavailable", reason=f"{type(exc).__name__}: {exc}"[:400])
        groups = gopls_groups()
    doc = {"label": label, "as_of": date, "planned": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "rule": {"gopls": f"the development head: {MODULE} at the pseudo-version of @master on {date}"},
           "common": ["3 replays per group; verdicts of version_sweep.verdict; compiled and run with the local Go",
                      "every gopls bug group of triage/root_causes.csv"],
           "sources": ["go list -m -json golang.org/x/tools/gopls@master (module proxy)"],
           "groups": groups, "builds": [build]}
    write_text(path, json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    return doc


def run(date: str, replays: int) -> int:
    label = f"head-{date}"
    doc = plan(date)
    b = doc["builds"][0]
    if b["status"] != "ok":
        logger.error("head build unavailable: %s", b.get("reason"))
        return 1
    done = {r["gid"] for r in rs.read_rows(label)}
    for g in doc["groups"]:
        if g["gid"] in done or g["gid"] in b.get("skip", {}):
            continue
        logger.info("%s: %s on gopls %s", label, g["gid"], b["version"])
        with rs.slot(False):
            row = rs.replay(label, b, g["gid"], replays)
        with open(os.path.join(SWEEP, label, "results.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        rs.summarize(label)
        logger.info("  -> %s (%d/%d, %.0fs) %s", row["verdict"], row["reproduced"], replays, row["seconds"], row["error"])
    rs.summarize(label)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Replay the gopls bug groups on the gopls development head.")
    ap.add_argument("--date", required=True, help="as-of date YYYY-MM-DD (label head-<date>)")
    ap.add_argument("--replays", type=int, default=3)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    return run(args.date, args.replays)


if __name__ == "__main__":
    raise SystemExit(main())
