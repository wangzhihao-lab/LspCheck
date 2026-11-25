"""One settle measurement per project x server, on a throwaway copy of the project.

- select_open_files: the first 3 source files in globally sorted relative-path order,
  skipping dependency, build-output, generated and fixture directories
  (common.SKIP_DIR_NAMES) and a few generated-file markers;
- make_probe_copy: a `cp -cR` (APFS clonefile, copy-on-write) copy under
  temp/corpus_probe/, so the server under test can never write into the shared
  temp/corpus/ cache;
- probe_server: start one server through servers.resolve / servers.start (the
  registry's launch specs, including an era Go for gopls when its install has one),
  open the files, wait for settle (probe_settle.py) bounded by the cap, record the
  diagnostics summary, peak RSS and whether the server crashed, then shut it down.
  Only the exact subprocess it spawned is ever signalled; its pid sits in `own_pids`
  while it runs;
- run_probe: probe_server for one unit on a fresh probe copy that is removed
  afterwards; the protocol log goes to data/lsptest/logs/prepare_corpus/<name>.jsonl.

Run line: imported by corpus/records.py; not run directly.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (PKG, os.path.join(os.path.dirname(PKG), "lsp_repro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import servers  # noqa: E402
from textdoc import uri_for  # noqa: E402

from .common import (  # noqa: E402
    LANG_EXT, LANGUAGE_ID_BY_EXT, LOG_DIR, PROBE_DIR, SKIP_DIR_NAMES, SKIP_FILENAME_MARKERS, ProjectSpec,
)
from .probe_settle import final_diagnostics_summary, wait_settle  # noqa: E402


# --------------------------------------------------------------- file pick
def _skip_dir(name: str) -> bool:
    return name.lower() in SKIP_DIR_NAMES or name.startswith(".")


def select_open_files(root: str, exts: Tuple[str, ...]) -> List[str]:
    """First 3 source files under `root` in globally sorted relative-path
    order, skipping generated/vendored/node_modules/target/test-fixture
    directories (see SKIP_DIR_NAMES) and a few generated-file markers."""
    hits: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _skip_dir(d)]  # prunes the walk in place
        for fn in filenames:
            if not fn.endswith(exts):
                continue
            low = fn.lower()
            if any(m in low for m in SKIP_FILENAME_MARKERS):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/")
            hits.append(rel)
    hits.sort()
    return hits[:3]


def make_probe_copy(src: str, dst: str) -> None:
    """A throwaway `cp -cR` (clonefile, copy-on-write on APFS) copy so the
    server under test can never write into the shared temp/corpus/ cache."""
    if os.path.isdir(dst):
        shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        r = subprocess.run(["cp", "-cR", src, dst], capture_output=True, text=True, timeout=600)
        if r.returncode != 0 or not os.path.isdir(dst):
            raise RuntimeError(r.stderr[-500:])
    except (subprocess.TimeoutExpired, RuntimeError, OSError):
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst, symlinks=True)


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ------------------------------------------------------------------ process
def _rss_kb(pid: int) -> int:
    """Current resident set size of `pid` in KiB (0 when ps cannot tell)."""
    try:
        r = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        return 0
    s = r.stdout.strip()
    return int(s) if r.returncode == 0 and s.isdigit() else 0


class RssSampler:
    """Cheap peak-RSS sampler: one `ps` call per second on a daemon thread until stopped."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.peak_kb = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> int:
        """Stop sampling and return the peak seen, in KiB."""
        self._stop.set()
        self._thread.join(timeout=2.0)
        return self.peak_kb

    def _run(self) -> None:
        while True:
            self.peak_kb = max(self.peak_kb, _rss_kb(self.pid))
            if self._stop.wait(1.0):
                return


def _ensure_dead(proc: "subprocess.Popen[bytes]") -> None:
    if proc.poll() is None:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass


def pid_alive(pid: int) -> bool:
    """Whether `pid` still exists (signal 0: a check, nothing is delivered)."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------- probe
def _open_files(client: Any, files_abs: Sequence[str], uris: Sequence[str]) -> None:
    for path, uri in zip(files_abs, uris):
        text = _read_text(path)
        lang = LANGUAGE_ID_BY_EXT.get(os.path.splitext(path)[1], "plaintext")
        client.notify("textDocument/didOpen",
                      {"textDocument": {"uri": uri, "languageId": lang, "version": 1, "text": text}})


def probe_server(kind: str, version: str, probe_root: str, log_path: str, files_rel: List[str],
                 own_pids: Set[int], settle_cap: float) -> Dict[str, Any]:
    """Start one server on the probe copy, open `files_rel`, wait for settle
    (bounded by settle_cap), record diagnostics/RSS/crash, and shut it down.
    Never signals anything but the exact subprocess it just spawned."""
    t_start = time.monotonic()
    try:
        spec = servers.resolve(kind, version)
        files_abs = [os.path.join(probe_root, r) for r in files_rel]
        uris = [uri_for(pth) for pth in files_abs]
        client = servers.start(spec, uri_for(probe_root), log_path, cwd=probe_root)
    except Exception as e:  # noqa: BLE001  (record and move on to the next unit)
        return {"settled": False, "init_ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}",
                "seconds": round(time.monotonic() - t_start, 1)}

    own_pids.add(client.proc.pid)
    sampler = RssSampler(client.proc.pid)
    sampler.start()
    rec: Dict[str, Any] = {"init_ok": True}
    t0 = time.monotonic()
    try:
        _open_files(client, files_abs, uris)
        pull = bool((getattr(client, "server_capabilities", None) or {}).get("diagnosticProvider"))
        rec["diag_mode"] = "pull" if pull else "push"
        rec["settled"] = wait_settle(client, kind, uris, pull, settle_cap, t0)
        rec["seconds"] = round(time.monotonic() - t0, 1)
        rec.update(final_diagnostics_summary(client, kind, uris, pull))
        rec["server_errors"] = client.server_errors()[:5]
        rec["crashed"] = client.proc.poll() is not None
    except Exception as e:  # noqa: BLE001
        rec.setdefault("settled", False)
        rec["seconds"] = round(time.monotonic() - t0, 1)
        rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    finally:
        rec["peak_rss_kb"] = sampler.stop()
        try:
            client.shutdown()
        except Exception:  # noqa: BLE001  (the process is killed just below either way)
            pass
        _ensure_dead(client.proc)
        own_pids.discard(client.proc.pid)
    return rec


def run_probe(p: ProjectSpec, prep: Mapping[str, Any], kind: str, version: str,
              own_pids: Set[int], settle_cap: float) -> Dict[str, Any]:
    """Probe one project x server on a fresh probe copy, removed afterwards."""
    project_root = prep["path"]
    files_rel = select_open_files(project_root, LANG_EXT[p.language])
    if not files_rel:
        return {"server": kind, "version": version, "files_opened": [], "settled": False,
                "skipped_reason": "no-source-files"}
    # The probe copy's name has no "@" (the clone's "@sha12" becomes "__sha12"). It dates
    # from when publishes were matched by exact URI string, which Node-based servers broke
    # by percent-encoding "@" as %40. probe_settle now compares decoded, case-folded paths
    # (settle.uri_key), so the name no longer matters for matching; it is kept so that
    # probe copies and log file names stay the same across runs.
    probe_name = f"{p.owner}__{p.repo}__{p.commit12}__{kind}-{version}"
    probe_root = os.path.join(PROBE_DIR, probe_name)
    log_path = os.path.join(LOG_DIR, probe_name + ".jsonl")
    rec: Dict[str, Any] = {"server": kind, "version": version, "files_opened": files_rel}
    try:
        make_probe_copy(project_root, probe_root)
    except Exception as e:  # noqa: BLE001
        return {**rec, "settled": False, "error": f"probe-copy failed: {type(e).__name__}: {e}"[:300]}
    try:
        return {**rec, **probe_server(kind, version, probe_root, log_path, files_rel, own_pids, settle_cap)}
    finally:
        shutil.rmtree(probe_root, ignore_errors=True)


__all__ = ["RssSampler", "make_probe_copy", "pid_alive", "probe_server", "run_probe", "select_open_files"]
