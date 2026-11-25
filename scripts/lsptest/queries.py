"""Query suite and per-method normalization (design section 4).

Per file: diagnostics (pull, or the last push), documentSymbol, semanticTokens/full,
inlayHint (whole file), foldingRange; per target position: hover, definition,
typeDefinition, references (includeDeclaration), documentHighlight, signatureHelp,
codeAction; per end-of-identifier position: completion; codeAction at every
distinct diagnostic range. NORMALIZERS[method] reduces each answer to canonical
JSON (lists, str, int, None) so `==` holds across sessions and JSON round trips:
URIs -> workspace-relative paths, the session's absolute paths in text -> "<ws>",
volatile fields dropped, ranges [sl, sc, el, ec], sets sorted, errors ["error", code].

Run line: imported by driver.py; not run directly.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Tuple
from urllib.parse import quote, unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from model import QueryKey, QueryResult, Snapshot  # noqa: E402
from ops import LineIndex, lsp_range  # noqa: E402
from targets import FileTargets, diagnostic_ranges  # noqa: E402
from completion_kind import is_auto_import  # noqa: E402

logger = logging.getLogger(__name__)

LSP_METHODS: Dict[str, str] = {
    "diagnostics": "textDocument/diagnostic", "hover": "textDocument/hover",
    "definition": "textDocument/definition", "typeDefinition": "textDocument/typeDefinition",
    "references": "textDocument/references", "documentHighlight": "textDocument/documentHighlight",
    "completion": "textDocument/completion", "signatureHelp": "textDocument/signatureHelp",
    "codeAction": "textDocument/codeAction", "documentSymbol": "textDocument/documentSymbol",
    "semanticTokens": "textDocument/semanticTokens/full", "inlayHint": "textDocument/inlayHint",
    "foldingRange": "textDocument/foldingRange",
}
PROVIDERS: Dict[str, str] = {m: f"{m}Provider" for m in LSP_METHODS if m not in ("diagnostics", "semanticTokens")}
PROVIDERS["semanticTokens"] = "semanticTokensProvider"
FILE_METHODS = ("diagnostics", "documentSymbol", "semanticTokens", "inlayHint", "foldingRange")
POSITION_CONTEXTS: Tuple[Tuple[str, Optional[Dict[str, Any]]], ...] = (  # method, request context
    ("hover", None), ("definition", None), ("typeDefinition", None), ("documentHighlight", None),
    ("references", {"includeDeclaration": True}), ("signatureHelp", {"triggerKind": 1, "isRetrigger": False}))
POSITION_METHODS = tuple(m for m, _ in POSITION_CONTEXTS) + ("codeAction",)
ALL_METHODS = FILE_METHODS + POSITION_METHODS + ("completion",)
Error = Tuple[str, Any]


@dataclass(frozen=True)
class QueryConfig:
    methods: Tuple[str, ...] = ALL_METHODS
    request_timeout_s: float = 30.0
    max_timeouts: int = 3  # after this many timeouts the suite stops (the snapshot is unusable)
    completion_top: int = 50
    max_diag_ranges: int = 10
    keep_raw: bool = False


class PathMapper:
    """URIs -> workspace-relative paths (on-disk case), session root -> "<ws>" in text;
    case-insensitive, as macOS volumes are and some servers lower-case paths."""

    def __init__(self, root: str, placeholder: str = "<ws>") -> None:
        self.root = os.path.abspath(root)
        self.real = os.path.realpath(self.root)
        variants = {self.root, self.real, quote(self.root, safe="/"), quote(self.real, safe="/")}
        self._pattern = re.compile("|".join(re.escape(v) for v in sorted(variants, key=len, reverse=True)), re.I)
        self._listings: Dict[str, Dict[str, str]] = {}
        self.placeholder = placeholder

    def rel(self, uri: str) -> str:
        if not uri.startswith("file:"):
            return self.scrub(uri)
        path = unquote(urlparse(uri).path)
        for base in (self.root, self.real):
            if path.casefold() == base.casefold():
                return "."
            if path.casefold().startswith(base.casefold() + "/"):
                return self._true_case(path[len(base) + 1 :])
        return path  # outside the workspace: an absolute path that is the same in every session

    def scrub(self, text: str) -> str:
        return self._pattern.sub(self.placeholder, text) if text else text

    def _true_case(self, rel: str) -> str:
        cur, out = self.root, []
        for part in rel.split("/"):
            if cur not in self._listings:
                try:
                    self._listings[cur] = {name.casefold(): name for name in os.listdir(cur)}
                except OSError:
                    self._listings[cur] = {}
            out.append(self._listings[cur].get(part.casefold(), part))
            cur = os.path.join(cur, out[-1])
        return "/".join(out)


@dataclass(frozen=True)
class NormContext:
    mapper: PathMapper
    token_types: Tuple[str, ...] = ()
    token_modifiers: Tuple[str, ...] = ()
    completion_top: int = 50


Normalizer = Callable[[Any, NormContext], Any]
NORMALIZERS: Dict[str, Normalizer] = {}


def register_normalizer(*methods: str) -> Callable[[Normalizer], Normalizer]:
    def deco(fn: Normalizer) -> Normalizer:
        for m in methods:
            NORMALIZERS[m] = fn
        return fn
    return deco


# ------------------------------------------------------------ normalizers
def _rng(r: Any) -> List[int]:
    s, e = (r or {}).get("start") or {}, (r or {}).get("end") or {}
    return [int(s.get("line", -1)), int(s.get("character", -1)), int(e.get("line", -1)), int(e.get("character", -1))]


def _collapse(s: Any) -> str:
    return " ".join(str(s).split())


def _sort(items: List[Any], unique: bool = False) -> List[Any]:
    if unique:
        items = list({json.dumps(x, sort_keys=True): x for x in items}.values())
    try:
        return sorted(items)
    except TypeError:
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True))


def _int_or(v: Any, default: int = -1) -> int:
    return int(v) if isinstance(v, (int, float)) else default


@register_normalizer("diagnostics")
def norm_diagnostics(result: Any, ctx: NormContext) -> Any:
    items = result.get("items") if isinstance(result, dict) else result
    if not isinstance(items, list):
        return None
    return _sort([_rng(d.get("range")) + [_int_or(d.get("severity"), 0), "" if d.get("code") is None else str(d["code"]),
                                          str(d.get("source") or ""), ctx.mapper.scrub(_collapse(d.get("message", "")))]
                  for d in items if isinstance(d, dict)])


def _markup_text(c: Any) -> str:
    if isinstance(c, list):
        return " ".join(t for t in (_markup_text(x) for x in c) if t)
    raw = str(c.get("value", "")) if isinstance(c, dict) else ("" if c is None else str(c))
    return _collapse("\n".join(ln for ln in raw.splitlines() if not ln.strip().startswith("```")))


@register_normalizer("hover")
def norm_hover(result: Any, ctx: NormContext) -> Any:
    if not isinstance(result, dict):
        return None
    return [ctx.mapper.scrub(_markup_text(result.get("contents"))),
            _rng(result["range"]) if isinstance(result.get("range"), dict) else None]


@register_normalizer("definition", "typeDefinition", "references")
def norm_locations(result: Any, ctx: NormContext) -> Any:
    """Location | Location[] | LocationLink[] | null -> sorted unique [path, sl, sc, el, ec]."""
    items = result if isinstance(result, list) else ([result] if isinstance(result, dict) else [])
    return _sort([[ctx.mapper.rel(str(loc.get("uri") or loc.get("targetUri") or ""))]
                  + _rng(loc.get("range") or loc.get("targetSelectionRange") or loc.get("targetRange"))
                  for loc in items if isinstance(loc, dict)], unique=True)


@register_normalizer("documentHighlight")
def norm_highlights(result: Any, ctx: NormContext) -> Any:
    items = result if isinstance(result, list) else []
    return _sort([_rng(h.get("range")) + [_int_or(h.get("kind"), 1)] for h in items if isinstance(h, dict)],
                 unique=True)


@register_normalizer("completion")
def norm_completion(result: Any, ctx: NormContext) -> Any:
    """Labels of the top `completion_top` non-auto-import items (completion_kind.py) in display order
    (sortText, else label; array order is alphabetical in TS 6 and arbitrary in TS 7), then sorted."""
    items = [i for i in (result.get("items") if isinstance(result, dict) else result) or []
             if isinstance(i, dict) and not is_auto_import(i)]
    shown = sorted(items, key=lambda i: (str(i.get("sortText") or i.get("label", "")), str(i.get("label", ""))))
    return sorted(str(i.get("label", "")) for i in shown[: ctx.completion_top])


@register_normalizer("signatureHelp")
def norm_signature(result: Any, ctx: NormContext) -> Any:
    sigs = result.get("signatures") if isinstance(result, dict) else None
    if not sigs:
        return None
    k = result.get("activeSignature") or 0
    sig = sigs[k] if isinstance(k, int) and 0 <= k < len(sigs) else sigs[0]
    return ctx.mapper.scrub(_collapse(sig.get("label", ""))) if isinstance(sig, dict) else None


@register_normalizer("codeAction")
def norm_code_actions(result: Any, ctx: NormContext) -> Any:
    """Sorted [title, kind]; a bare Command gets kind "<command>"; data and ids dropped."""
    items = result if isinstance(result, list) else []
    return _sort([[ctx.mapper.scrub(_collapse(a.get("title", ""))),
                   str(a.get("kind") or ("<command>" if isinstance(a.get("command"), str) else ""))]
                  for a in items if isinstance(a, dict)])


@register_normalizer("documentSymbol")
def norm_symbols(result: Any, ctx: NormContext) -> Any:
    """DocumentSymbol tree or SymbolInformation list -> sorted [name, kind, sl, sc, el, ec]."""
    out: List[List[Any]] = []
    stack = list(result) if isinstance(result, list) else []
    while stack:
        s = stack.pop()
        if isinstance(s, dict):
            rng = s.get("range") or (s.get("location") or {}).get("range")
            out.append([str(s.get("name", "")), _int_or(s.get("kind"), 0)] + _rng(rng))
            stack.extend(s.get("children") or [])
    return _sort(out)


@register_normalizer("semanticTokens")
def norm_semantic_tokens(result: Any, ctx: NormContext) -> Any:
    """Relative encoding decoded with the server's legend: [line, char, length, type, "mod,mod"]."""
    data = result.get("data") if isinstance(result, dict) else None
    if not isinstance(data, list):
        return None
    out, line, char, types, mods = [], 0, 0, ctx.token_types, ctx.token_modifiers
    for k in range(0, len(data) - 4, 5):
        dl, dc, length, ttype, bits = (int(x) for x in data[k : k + 5])
        line, char = line + dl, (char + dc if dl == 0 else dc)
        names = sorted(mods[b] if b < len(mods) else str(b) for b in range(bits.bit_length()) if bits >> b & 1)
        out.append([line, char, length, types[ttype] if 0 <= ttype < len(types) else str(ttype), ",".join(names)])
    return out


@register_normalizer("inlayHint")
def norm_inlay_hints(result: Any, ctx: NormContext) -> Any:
    out = []
    for h in result if isinstance(result, list) else []:
        if isinstance(h, dict):
            lab, p = h.get("label"), h.get("position") or {}
            text = "".join(str(x.get("value", "")) if isinstance(x, dict) else str(x) for x in lab) \
                if isinstance(lab, list) else str(lab or "")
            out.append([_int_or(p.get("line")), _int_or(p.get("character")), ctx.mapper.scrub(text.strip())])
    return _sort(out)


@register_normalizer("foldingRange")
def norm_folding(result: Any, ctx: NormContext) -> Any:
    items = result if isinstance(result, list) else []
    return _sort([[_int_or(f.get("startLine")), _int_or(f.get("startCharacter")), _int_or(f.get("endLine")),
                   _int_or(f.get("endCharacter")), str(f.get("kind") or "")] for f in items if isinstance(f, dict)],
                 unique=True)


# ------------------------------------------------------------ running the suite
class QuerySession(Protocol):
    """What run_suite needs from a live session (driver.Driver implements it)."""
    def request(self, method: str, params: Any, timeout: float) -> Tuple[Any, Optional[Error]]: ...
    def uri(self, path: str) -> str: ...
    def text(self, path: str) -> str: ...
    def supports(self, method: str) -> bool: ...
    def diagnostics(self, path: str, timeout: float) -> Tuple[Any, Optional[Error]]: ...
    def norm_context(self, completion_top: int) -> NormContext: ...


def provider_enabled(caps: Dict[str, Any], registered: Callable[[str], bool], method: str) -> bool:
    """Whether the server offers `method`: a static provider that is not false/null
    (an empty options object counts), or a dynamic registration."""
    if method == "diagnostics":
        return True
    prov = caps.get(PROVIDERS[method])
    ok = bool(prov.get("full")) if method == "semanticTokens" and isinstance(prov, dict) else prov not in (None, False)
    return ok or registered("textDocument/semanticTokens" if method == "semanticTokens" else LSP_METHODS[method])


@dataclass
class SuiteStats:
    seconds: float = 0.0
    requests: int = 0
    timeouts: int = 0
    tripped: bool = False
    errors: Dict[str, int] = field(default_factory=dict)
    method_seconds: Dict[str, float] = field(default_factory=dict)
    method_counts: Dict[str, int] = field(default_factory=dict)
    unsupported: List[str] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        return dict(asdict(self), seconds=round(self.seconds, 3),
                    method_seconds={k: round(v, 3) for k, v in sorted(self.method_seconds.items())})


class _Suite:
    def __init__(self, session: QuerySession, cfg: QueryConfig) -> None:
        self.s, self.cfg = session, cfg
        self.ctx = session.norm_context(cfg.completion_top)
        self.enabled = {m for m in cfg.methods if session.supports(m)}
        self.stats = SuiteStats(unsupported=sorted(set(cfg.methods) - self.enabled))
        self.results: Dict[QueryKey, QueryResult] = {}

    def run_file(self, ft: FileTargets) -> None:
        doc = {"textDocument": {"uri": self.s.uri(ft.path)}}
        raw_diags: List[Dict[str, Any]] = []
        if "diagnostics" in self.enabled and not self.stats.tripped:
            t0 = time.monotonic()
            result, err = self.s.diagnostics(ft.path, self.cfg.request_timeout_s)
            self._record(QueryKey("diagnostics", ft.path), result, err, t0)
            items = result.get("items") if isinstance(result, dict) else result
            raw_diags = [d for d in items or [] if isinstance(d, dict)] if err is None else []
        whole = lsp_range((0, 0), LineIndex(self.s.text(ft.path)).end())
        for m, params in (("documentSymbol", doc), ("semanticTokens", doc), ("inlayHint", dict(doc, range=whole)),
                          ("foldingRange", doc)):
            self._ask(m, QueryKey(m, ft.path), params)
        for line, ch in ft.positions:
            at = dict(doc, position={"line": line, "character": ch})
            for m, ctx in POSITION_CONTEXTS:
                self._ask(m, QueryKey(m, ft.path, line, ch), dict(at, context=ctx) if ctx else at)
            here = [d for d in raw_diags if (r := _rng(d.get("range")))[:2] <= [line, ch] <= r[2:]]
            self._ask("codeAction", QueryKey("codeAction", ft.path, line, ch, "pos"),
                      dict(doc, range=lsp_range((line, ch), (line, ch)), context={"diagnostics": here, "triggerKind": 1}))
        for line, ch in ft.ends:
            self._ask("completion", QueryKey("completion", ft.path, line, ch),
                      dict(doc, position={"line": line, "character": ch}, context={"triggerKind": 1}))
        for sl, sc, el, ec in diagnostic_ranges(raw_diags, self.cfg.max_diag_ranges):
            group = [d for d in raw_diags if _rng(d.get("range")) == [sl, sc, el, ec]]
            self._ask("codeAction", QueryKey("codeAction", ft.path, sl, sc, f"diag:{el}:{ec}"),
                      dict(doc, range=lsp_range((sl, sc), (el, ec)), context={"diagnostics": group, "triggerKind": 1}))

    def _ask(self, method: str, key: QueryKey, params: Dict[str, Any]) -> None:
        if method not in self.enabled or self.stats.tripped:
            return
        t0 = time.monotonic()
        result, err = self.s.request(LSP_METHODS[method], params, self.cfg.request_timeout_s)
        self._record(key, result, err, t0)

    def _record(self, key: QueryKey, result: Any, err: Optional[Error], t0: float) -> None:
        secs, st = time.monotonic() - t0, self.stats
        st.requests += 1
        st.method_seconds[key.method] = st.method_seconds.get(key.method, 0.0) + secs
        st.method_counts[key.method] = st.method_counts.get(key.method, 0) + 1
        if err is not None:
            st.errors[key.method] = st.errors.get(key.method, 0) + 1
            if err[1] in ("timeout", "dead"):
                st.timeouts += 1
                st.tripped = st.tripped or err[1] == "dead" or st.timeouts >= self.cfg.max_timeouts
            self.results[key] = QueryResult(key, norm=list(err), error=err, seconds=secs)
            return
        try:
            norm = NORMALIZERS[key.method](result, self.ctx)
        except (TypeError, ValueError, KeyError, AttributeError, IndexError) as exc:
            logger.warning("cannot normalize %s: %s", key, exc)
            norm = ["unnormalizable", type(exc).__name__]
        self.results[key] = QueryResult(key, norm=norm, raw=result if self.cfg.keep_raw else None, seconds=secs)


def run_suite(session: QuerySession, targets: Sequence[FileTargets],
              cfg: QueryConfig = QueryConfig()) -> Tuple[Dict[QueryKey, QueryResult], SuiteStats]:
    """Run the whole query suite over the targets; returns results and statistics."""
    t0, suite = time.monotonic(), _Suite(session, cfg)
    for ft in targets:
        suite.run_file(ft)
    suite.stats.seconds = time.monotonic() - t0
    return suite.results, suite.stats


# ------------------------------------------------------------ snapshots as data
def key_sort(k: QueryKey) -> Tuple[str, str, int, int, str]:
    return (k.method, k.path, k.line, k.character, k.extra)


def snapshot_to_json(s: Snapshot) -> Dict[str, Any]:
    rows = [{"key": list(key_sort(k)), "norm": r.norm, "error": list(r.error) if r.error else None,
             "seconds": round(r.seconds, 4)} for k, r in sorted(s.results.items(), key=lambda kv: key_sort(kv[0]))]
    return {"label": s.label, "server": s.server, "settled": s.settled, "contents_sha": s.contents_sha, "results": rows}


def snapshot_from_json(d: Dict[str, Any]) -> Snapshot:
    results = {}
    for row in d.get("results", []):
        k, err = QueryKey(*row["key"]), (tuple(row["error"]) if row.get("error") else None)
        results[k] = QueryResult(k, row.get("norm"), error=err, seconds=row.get("seconds", 0.0))
    return Snapshot(d["label"], d["server"], bool(d["settled"]), results, d.get("contents_sha", ""))


__all__ = ["ALL_METHODS", "FILE_METHODS", "LSP_METHODS", "NORMALIZERS", "NormContext", "POSITION_METHODS", "PROVIDERS",
           "PathMapper", "QueryConfig", "QuerySession", "SuiteStats", "key_sort", "provider_enabled",
           "register_normalizer", "run_suite", "snapshot_from_json", "snapshot_to_json"]
