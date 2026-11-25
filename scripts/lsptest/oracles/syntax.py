"""Syntax classifier independent of the server under test (design section 10).

`syntax_errors(language, text, path)` returns the parse errors of one text as
"L:C: message" strings (1-based line and column, as the parsers report them):

- python: `ast.parse` of the running interpreter, then `compile()` of the tree, so the
  errors Python raises as SyntaxError at compile time count too (misplaced
  `from __future__` imports, `return` outside a function); first error only;
- go: `gofmt -e` on stdin (all parse errors; formatting differences are ignored);
- rust: `rustfmt --edition E` on stdin, parse errors only (the formatted output is
  discarded). The edition comes from the nearest Cargo.toml above `path` (workspace
  editions followed), default 2021. rustfmt is taken from PATH (plus the rustup and
  cargo bin dirs) when it runs, else from any rustup toolchain that ships it;
- typescript / javascript (and the React variants): the parse diagnostics of the
  installed `typescript` package (temp/lsp_servers/ts6-6.0.3) through the node helper
  ts_syntax.js, started once and kept alive; the script kind follows the extension.

Results are cached by (language family, variant, sha256 of the text); the variant is
the file extension for TypeScript and the edition for Rust. Unsupported languages
return [] (a warning is logged once). A parser that cannot be run raises
SyntaxToolError after one retry; it never reports a fake error. `new_errors(before,
after)` compares two error lists with positions ignored, so an edit that moves an
existing error is not a new error. `syntax_errors_many` checks many texts at once
(thread pool for the external tools).

Run line: imported by oracles/r4_edits.py (and other oracles); not run directly.
"""

from __future__ import annotations

import ast
import atexit
import glob
import hashlib
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TS_PACKAGE = os.path.join(REPO, "temp", "lsp_servers", "ts6-6.0.3", "node_modules", "typescript")
TS_HELPER = os.path.join(HERE, "ts_syntax.js")
RUSTUP_BIN = "/opt/homebrew/opt/rustup/bin"
CARGO_BIN = os.path.expanduser("~/.cargo/bin")
RUSTUP_TOOLCHAINS = os.path.expanduser("~/.rustup/toolchains")
TOOL_TIMEOUT_S = 30.0
DEFAULT_EDITION = "2021"

FAMILIES: Dict[str, str] = {
    "python": "py", "go": "go", "rust": "rs", "typescript": "ts", "typescriptreact": "ts",
    "javascript": "ts", "javascriptreact": "ts",
}
_POS = re.compile(r"^\d+:\d+: ")


class SyntaxToolError(RuntimeError):
    """The external parser could not be run (missing tool, crash, timeout)."""


Checker = Callable[[str, str], List[str]]
CHECKERS: Dict[str, Checker] = {}
_cache: Dict[Tuple[str, str, str], Tuple[str, ...]] = {}
_cache_lock = threading.Lock()
_warned: set = set()


def register_checker(family: str) -> Callable[[Checker], Checker]:
    def deco(fn: Checker) -> Checker:
        CHECKERS[family] = fn
        return fn
    return deco


# ------------------------------------------------------------------ public API
def supported(language: str) -> bool:
    return FAMILIES.get(language) in CHECKERS


def syntax_errors(language: str, text: str, path: str) -> List[str]:
    """Parse errors of `text` as "L:C: message" strings; [] when it parses (or when the
    language has no classifier). Raises SyntaxToolError when the parser cannot run."""
    family = FAMILIES.get(language)
    if family not in CHECKERS:
        if language not in _warned:
            _warned.add(language)
            logger.warning("no syntax classifier for language %r; reporting no errors", language)
        return []
    key = (family, _variant(family, path), hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest())
    with _cache_lock:
        hit = _cache.get(key)
    if hit is not None:
        return list(hit)
    errors = CHECKERS[family](text, path)
    with _cache_lock:
        _cache[key] = tuple(errors)
    return list(errors)


def syntax_errors_many(language: str, items: Sequence[Tuple[str, str]], workers: int = 4) -> List[List[str]]:
    """syntax_errors for many (text, path) pairs, in order; external tools run in parallel."""
    if FAMILIES.get(language) in ("go", "rs") and len(items) > 1:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            return list(pool.map(lambda it: syntax_errors(language, it[0], it[1]), items))
    return [syntax_errors(language, text, path) for text, path in items]


def error_message(error: str) -> str:
    """An error string without its "L:C: " position prefix."""
    return _POS.sub("", error, count=1)


def new_errors(before: Sequence[str], after: Sequence[str]) -> List[str]:
    """Errors of `after` not accounted for by `before` (multiset of messages, positions ignored)."""
    budget: Dict[str, int] = {}
    for e in before:
        budget[error_message(e)] = budget.get(error_message(e), 0) + 1
    out = []
    for e in after:
        m = error_message(e)
        if budget.get(m, 0) > 0:
            budget[m] -= 1
        else:
            out.append(e)
    return out


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


# ------------------------------------------------------------------ helpers
def _variant(family: str, path: str) -> str:
    if family == "ts":
        return os.path.splitext(path or "")[1].lower() or ".ts"
    if family == "rs":
        return rust_edition(path)
    return ""


def _run(cmd: List[str], text: str, cwd: Optional[str] = None,
         env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, input=text.encode("utf-8", "surrogatepass"), capture_output=True,
                              timeout=TOOL_TIMEOUT_S, cwd=cwd, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        raise SyntaxToolError(f"{os.path.basename(cmd[0])} failed to run: {exc}") from exc


def _dedupe(errors: List[str]) -> List[str]:
    return list(dict.fromkeys(errors))


# ------------------------------------------------------------------ python
@register_checker("py")
def _python(text: str, path: str) -> List[str]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # SyntaxWarning (escape sequences) is not an error
        try:  # ast.parse, then compile(): misplaced __future__ imports, 'return' outside a function, ...
            compile(ast.parse(text, filename=path or "<text>"), path or "<text>", "exec", dont_inherit=True)
        except SyntaxError as exc:  # IndentationError and TabError included
            return [f"{exc.lineno or 0}:{exc.offset or 0}: {exc.msg}"]
        except (ValueError, RecursionError, MemoryError) as exc:  # null bytes, nesting limits
            return [f"0:0: {type(exc).__name__}: {exc}"]
    return []


# ------------------------------------------------------------------ go
@register_checker("go")
def _go(text: str, path: str) -> List[str]:
    exe = shutil.which("gofmt") or shutil.which("gofmt", path="/opt/homebrew/bin:/usr/local/go/bin")
    if not exe:
        raise SyntaxToolError("gofmt not found")
    res = _run([exe, "-e"], text)
    if res.returncode == 0:
        return []
    errors = []
    for line in res.stderr.decode("utf-8", "replace").splitlines():
        m = re.match(r"^(?:<standard input>|[^:]*):(\d+):(\d+): (.*)$", line.strip())
        if m:
            errors.append(f"{m.group(1)}:{m.group(2)}: {m.group(3)}")
    if not errors:
        raise SyntaxToolError(f"gofmt exited {res.returncode} without parse errors: {res.stderr[-300:]!r}")
    return _dedupe(errors)


# ------------------------------------------------------------------ rust
_rustfmt: Dict[str, Optional[str]] = {}
_editions: Dict[str, str] = {}
_RS_HEAD = re.compile(r"^error(?:\[\w+\])?: (.*)$")
_RS_LOC = re.compile(r"^\s*--> (?:<stdin>|.*?):(\d+):(\d+)")
_EDITION = re.compile(r'(?m)^\s*edition\s*=\s*"(\d{4})"')


def _works(exe: str) -> bool:
    try:
        return subprocess.run([exe, "--version"], capture_output=True, timeout=TOOL_TIMEOUT_S).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def rustfmt_path() -> Optional[str]:
    """A rustfmt that runs: PATH (with the rustup/cargo bin dirs) first, then any toolchain."""
    if "exe" not in _rustfmt:
        search = os.pathsep.join([RUSTUP_BIN, CARGO_BIN, os.environ.get("PATH", "")])
        cands = [shutil.which("rustfmt", path=search)] + sorted(
            glob.glob(os.path.join(RUSTUP_TOOLCHAINS, "*", "bin", "rustfmt")), reverse=True)
        _rustfmt["exe"] = next((c for c in cands if c and _works(c)), None)
    return _rustfmt["exe"]


def rust_toolchain_with_rustfmt() -> Optional[str]:
    """Name of the rustup toolchain whose rustfmt is used (None when it comes from PATH)."""
    exe = rustfmt_path()
    if exe and exe.startswith(RUSTUP_TOOLCHAINS + os.sep):
        return exe[len(RUSTUP_TOOLCHAINS) + 1 :].split(os.sep)[0]
    return None


def rust_edition(path: str) -> str:
    """Edition of the crate containing `path` (nearest Cargo.toml naming one), default 2021."""
    if not path or not os.path.isabs(path):
        return DEFAULT_EDITION
    cur = os.path.dirname(path)
    seen = []
    while True:
        if cur in _editions:
            found = _editions[cur]
            break
        seen.append(cur)
        manifest = os.path.join(cur, "Cargo.toml")
        m = None
        if os.path.isfile(manifest):
            try:
                with open(manifest, "r", encoding="utf-8", errors="replace") as f:
                    m = _EDITION.search(f.read())
            except OSError:
                m = None
        parent = os.path.dirname(cur)
        if m or parent == cur:
            found = m.group(1) if m else DEFAULT_EDITION
            break
        cur = parent
    for d in seen:
        _editions[d] = found
    return found


@register_checker("rs")
def _rust(text: str, path: str) -> List[str]:
    exe = rustfmt_path()
    if not exe:
        raise SyntaxToolError("no working rustfmt (install the rustfmt component of a toolchain)")
    res = _run([exe, "--edition", rust_edition(path)], text, cwd=tempfile.gettempdir())
    if res.returncode == 0:
        return []
    errors, head = [], None
    for line in res.stderr.decode("utf-8", "replace").splitlines():
        m = _RS_HEAD.match(line)
        if m:
            head = m.group(1).strip()
            continue
        loc = _RS_LOC.match(line)
        if loc and head is not None:
            errors.append(f"{loc.group(1)}:{loc.group(2)}: {head}")
            head = None
    if not errors:
        raise SyntaxToolError(f"rustfmt exited {res.returncode} without located errors: {res.stderr[-300:]!r}")
    return _dedupe(errors)


# ------------------------------------------------------------------ typescript
class _TsHelper:
    """The long-lived node process running ts_syntax.js (started on first use)."""

    def __init__(self) -> None:
        self.proc: Optional[subprocess.Popen] = None
        self.lines: "queue.Queue[str]" = queue.Queue()
        self.lock = threading.Lock()
        self.next_id = 0

    def _start(self) -> None:
        node = shutil.which("node")
        if not node or not os.path.isdir(TS_PACKAGE):
            raise SyntaxToolError(f"node or the typescript package is missing ({TS_PACKAGE})")
        self.lines = queue.Queue()
        self.proc = subprocess.Popen([node, TS_HELPER, TS_PACKAGE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1)
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()
        ready = self._read("ready")
        logger.debug("typescript syntax helper ready (typescript %s)", ready.get("version"))

    def _pump(self, proc: subprocess.Popen) -> None:
        for line in iter(proc.stdout.readline, ""):  # type: ignore[union-attr]
            self.lines.put(line)
        self.lines.put("")  # EOF marker

    def _read(self, want: str) -> Dict[str, object]:
        while True:
            try:
                line = self.lines.get(timeout=TOOL_TIMEOUT_S)
            except queue.Empty as exc:
                raise SyntaxToolError("typescript syntax helper timed out") from exc
            if not line:
                raise SyntaxToolError("typescript syntax helper exited")
            msg = json.loads(line)
            if str(msg.get("id")) == want:
                return msg

    def check(self, text: str, path: str) -> List[str]:
        with self.lock:
            for attempt in (0, 1):
                try:
                    if self.proc is None or self.proc.poll() is not None:
                        self._start()
                    self.next_id += 1
                    rid = str(self.next_id)
                    self.proc.stdin.write(json.dumps({"id": rid, "path": path, "text": text}) + "\n")  # type: ignore[union-attr]
                    self.proc.stdin.flush()  # type: ignore[union-attr]
                    msg = self._read(rid)
                    if "fatal" in msg:
                        raise SyntaxToolError(f"typescript parser failed: {str(msg['fatal'])[:300]}")
                    return [str(e) for e in msg.get("errors") or []]
                except (OSError, ValueError, SyntaxToolError) as exc:
                    self.stop()
                    if attempt == 1:
                        raise SyntaxToolError(str(exc)) from exc
                    logger.warning("typescript syntax helper restarted: %s", exc)
        return []

    def stop(self) -> None:
        proc, self.proc = self.proc, None
        if proc is not None and proc.poll() is None:
            try:
                proc.stdin.close()  # type: ignore[union-attr]
                proc.wait(timeout=5)
            except (OSError, subprocess.SubprocessError):
                proc.kill()


_TS = _TsHelper()
atexit.register(_TS.stop)


@register_checker("ts")
def _typescript(text: str, path: str) -> List[str]:
    return _TS.check(text, os.path.basename(path or "") or "file.ts")


__all__ = [
    "CHECKERS", "FAMILIES", "SyntaxToolError", "clear_cache", "error_message", "new_errors", "register_checker",
    "rust_edition", "rust_toolchain_with_rustfmt", "rustfmt_path", "supported", "syntax_errors", "syntax_errors_many",
]
