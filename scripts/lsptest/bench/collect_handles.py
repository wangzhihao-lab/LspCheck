"""The session of the stale_code_action probe (R2 handle validity, see probes_derived.py):
the first `mint_after` ops, a settle, the handle minted (codeAction, the action matching the
spec, codeAction/resolve), the remaining ops, a final settle, the old action resolved again
and the action minted and resolved afresh.

Run line: imported by collect.py; not run directly.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from driver import Driver  # noqa: E402
from model import Op  # noqa: E402
from ops import lsp_range  # noqa: E402
from oracles.r4_session import resolves_actions  # noqa: E402
from oracles.r4_textedits import workspace_edit_groups  # noqa: E402
from queries import NORMALIZERS  # noqa: E402

from .collect import SESSION_ERRORS, RunEnv, _check_build, _pick, apply_ops, raw_diagnostics
from .probes import diag_matches


def edit_entries(d: Driver, edit: Mapping[str, Any]) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """A WorkspaceEdit as sorted [path, sl, sc, el, ec, newText] entries (resource operations as
    ["<kind:uri>"]) and the document version each TextDocumentEdit names."""
    groups, skipped = workspace_edit_groups(edit)
    out: List[List[Any]] = [[f"<{x}>"] for x in skipped]
    versions: Dict[str, Any] = {}
    for dc in edit.get("documentChanges") or []:
        if isinstance(dc, dict) and isinstance(dc.get("textDocument"), dict):
            versions[d.mapper.rel(str(dc["textDocument"].get("uri", "")))] = dc["textDocument"].get("version")
    for uri, tedits in groups:
        for e in tedits:
            if isinstance(e, dict):
                r = e.get("range") or {}
                a, b = r.get("start") or {}, r.get("end") or {}
                out.append([d.mapper.rel(uri), a.get("line"), a.get("character"), b.get("line"), b.get("character"),
                            str(e.get("newText", ""))])
    return sorted(out, key=lambda x: json.dumps(x, sort_keys=True)), versions


def resolve_action(d: Driver, action: Mapping[str, Any]) -> Dict[str, Any]:
    """codeAction/resolve of an action object: {edit (entries or None), error, outdated_version}."""
    res, err = d.request("codeAction/resolve", dict(action), d.cfg.request_timeout_s)
    if err is not None:
        return {"edit": None, "error": err[1], "outdated_version": False}
    edit = res.get("edit") if isinstance(res, dict) else None
    if not isinstance(edit, dict) or not ("changes" in edit or "documentChanges" in edit):
        return {"edit": None, "error": None, "outdated_version": False}
    entries, versions = edit_entries(d, edit)
    docs = d.store.docs
    outdated = any(v is not None and p in docs and v != docs[p].version for p, v in versions.items())
    return {"edit": entries, "error": None, "outdated_version": outdated}


def mint_action(d: Driver, spec: Mapping[str, Any], range_key: str = "range") -> Dict[str, Any]:
    """A code action at the handle's range (spec[range_key], else spec["range"]) or at its
    diagnostic, the one matching title_re (and kind), resolved once as an editor does while
    browsing: {offered, titles, chosen, resolvable, action, edit, error, outdated_version}."""
    path, timeout = str(spec["path"]), d.cfg.request_timeout_s
    out: Dict[str, Any] = {"offered": False, "titles": []}
    diags = raw_diagnostics(d, path)
    if spec.get("diagnostic"):
        norm = [NORMALIZERS["diagnostics"]([x], d.norm_context(50))[0] for x in diags]
        hit = next((raw for raw, n in zip(diags, norm) if diag_matches(n, spec["diagnostic"])), None)
        if hit is None:
            out["titles"] = [f"<no diagnostic matching {spec['diagnostic']}; have {[n[5] for n in norm]}>"]
            return out
        rng, context_diags = hit["range"], [hit]
    else:
        r = spec.get(range_key) or spec["range"]
        rng, context_diags = lsp_range((r[0], r[1]), (r[2], r[3])), diags
    ctx: Dict[str, Any] = {"diagnostics": context_diags, "triggerKind": 1}
    if spec.get("kind"):
        ctx["only"] = [spec["kind"]]
    res, err = d.request("textDocument/codeAction", {"textDocument": {"uri": d.uri(path)}, "range": rng,
                                                     "context": ctx}, timeout)
    actions = [a for a in res or [] if isinstance(a, dict)] if err is None else []
    out["titles"] = [str(a.get("title", "")) for a in actions] or ([f"<error {err[1]}>"] if err else [])
    chosen = _pick([a for a in actions if str(a.get("kind") or "").startswith(spec.get("kind", ""))],
                   "title", str(spec["title_re"]))
    if chosen is None:
        return out
    out.update(offered=True, chosen=str(chosen.get("title", "")), action=dict(chosen),
               resolvable="data" in chosen and resolves_actions(d))
    if out["resolvable"]:
        out.update(resolve_action(d, chosen))
    return out


def handle_session(env: RunEnv, project_dir: str, ops: Sequence[Op], timing: str,
                   params: Mapping[str, Any]) -> Dict[str, Any]:
    """The one session of stale_code_action (module docstring); returns {valid, reason, results,
    handle: {minted, stale, fresh}}."""
    t0 = time.monotonic()
    out: Dict[str, Any] = {"valid": False, "reason": "", "results": {}}
    spec, k = params["handle"], int(params["mint_after"])
    try:
        with Driver(env.config("case", project_dir)) as d:
            out["log"] = os.path.relpath(d.log_path, env.work_dir)
            for part, label in ((ops[:k], "before minting"), (ops[k:], "after minting")):
                errors = apply_ops(d, part, timing)
                res = d.settle() if not errors else None
                if errors or res is None or not res.settled:
                    out["reason"] = errors[0] if errors else f"not settled {label}: {res.reason if res else '?'}"
                    return out
                if label == "before minting":
                    minted = mint_action(d, spec)
                    out["handle"] = {"minted": {x: v for x, v in minted.items() if x != "action"}}
                    if not minted.get("resolvable") or minted.get("edit") is None:
                        break  # no handle to go stale: the probe is invalid, the rest is not needed
            else:
                out["handle"]["stale"] = resolve_action(d, minted["action"])
                fresh = mint_action(d, spec, "fresh_range")
                out["handle"]["fresh"] = {x: v for x, v in fresh.items() if x != "action"}
            out["reason"] = _check_build(env, d)
            out["valid"] = not out["reason"] and d.alive()
            if not d.alive():
                out["reason"] = out["reason"] or "server exited during the session"
    except SESSION_ERRORS as exc:
        out["reason"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    out["seconds"] = round(time.monotonic() - t0, 2)
    return out


__all__ = ["edit_entries", "handle_session", "mint_action", "resolve_action"]
