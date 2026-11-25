"""Detection table of a benchmark campaign (RQ: how many reproduced historical bugs do the generic
oracles detect?).

For each benchmark case of the campaign (config.json: config.bench_cases) and each oracle: the
signatures confirmed on the pre-fix build and on the post-fix build (violations.jsonl, the last
row per vid, status confirmed). A case is detected when its pre-fix build has at least one
confirmed signature that is not confirmed on its post-fix build ("pre-only"). Pre-only signatures
are listed per case with an empty author_match field (the author records whether each matches
the case's reported bug); values the author already entered in detection.json are kept when the
table is regenerated. A (case, oracle) whose planned runs did not all finish (status ok, or
no-targets / not-applicable: nothing to test) is marked incomplete, and so is its case. Signatures
skipped as labelled-legitimate are listed per build for reference (never counted as detections).
Cases whose ground truth used the specification probe edit_text_differs are summarized
separately. Writes data/lsptest/runs/<campaign>/detection.{json,md}.

Run line: python3 scripts/lsptest/campaign_detect.py <campaign-id>
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Mapping, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from campaign_store import latest_rows, paths_for, read_jsonl, write_json  # noqa: E402

logger = logging.getLogger("campaign_detect")
PHASES = ("pre", "post")
FINISHED = frozenset({"ok", "no-targets", "not-applicable"})


def phase_of(case: Mapping[str, Any], version: str) -> str:
    return next((p for p in PHASES if case["builds"].get(p) == version), "")


def run_status(planned: Sequence[Mapping[str, Any]], results: Mapping[str, Mapping[str, Any]]) -> Dict[str, int]:
    """Counts of planned runs by recorded status ("missing" when not recorded)."""
    out: Dict[str, int] = {}
    for spec in planned:
        st = str((results.get(spec["run_id"]) or {}).get("status", "missing"))
        out[st] = out.get(st, 0) + 1
    return out


def detect(cases: Sequence[Mapping[str, Any]], planned: Sequence[Mapping[str, Any]],
           results: Sequence[Mapping[str, Any]], violations: Sequence[Mapping[str, Any]],
           author: Mapping[Tuple[str, str, str], str]) -> List[Dict[str, Any]]:
    """One entry per case (see the module docstring); planned = RunSpec JSON of the campaign's plan."""
    by_run = {str(r["run_id"]): r for r in latest_rows(results, "run_id")}
    rows = latest_rows(violations)
    out = []
    for case in cases:
        cid = str(case["case"])
        oracles: Dict[str, Dict[str, Any]] = {}
        for spec in (s for s in planned if s["project"] == cid):
            entry = oracles.setdefault(spec["oracle"], {p: [] for p in PHASES} | {"planned": {p: [] for p in PHASES}})
            entry["planned"][phase_of(case, spec["server_version"]) or "pre"].append(spec)
        for r in (r for r in rows if r.get("project") == cid and r.get("oracle") in oracles):
            phase = phase_of(case, str(r.get("server_version")))
            if not phase:
                continue
            e = oracles[r["oracle"]]
            if r.get("confirmed") and not r.get("incomplete"):
                e[phase].append(r)
            elif r.get("status") == "labelled-legitimate":
                e.setdefault(f"labelled_{phase}", set()).add(str(r["signature"]))
        entries, pre_only = {}, []
        for name, e in sorted(oracles.items()):
            sigs = {p: sorted({str(r["signature"]) for r in e[p]}) for p in PHASES}
            only = [s for s in sigs["pre"] if s not in sigs["post"]]
            status = {p: run_status(e["planned"][p], by_run) for p in PHASES}
            complete = all(set(st) <= FINISHED for st in status.values())
            entries[name] = {"pre": sigs["pre"], "post": sigs["post"], "pre_only": only, "runs": status,
                             "complete": complete,
                             "labelled": {p: sorted(e.get(f"labelled_{p}", set())) for p in PHASES}}
            pre_only += [{"oracle": name, "signature": s, "vids": sorted(str(r["vid"]) for r in e["pre"]
                                                                          if r["signature"] == s),
                          "complete": complete, "author_match": author.get((cid, name, s), "")} for s in only]
        out.append({"case": cid, "kind": case.get("kind"), "class": case.get("oracle_class"), "subtype": case.get("subtype"),
                    "probe": case.get("probe"), "spec_probe": bool(case.get("spec_probe")), "builds": case.get("builds"),
                    "title": case.get("title"), "url": case.get("url"), "oracles": entries, "pre_only": pre_only,
                    "detected": bool(pre_only), "complete": all(e["complete"] for e in entries.values())})
    return out


def summary(entries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    def count(sel: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        by_oracle: Dict[str, int] = {}
        for e in sel:
            for o in {p["oracle"] for p in e["pre_only"]}:
                by_oracle[o] = by_oracle.get(o, 0) + 1
        return {"cases": len(sel), "complete": sum(e["complete"] for e in sel), "detected": sum(e["detected"] for e in sel),
                "detected_by_oracle": dict(sorted(by_oracle.items()))}
    return {"generic": count([e for e in entries if not e["spec_probe"]]),
            "spec_probe": count([e for e in entries if e["spec_probe"]])}


def render(campaign: str, entries: Sequence[Mapping[str, Any]], summ: Mapping[str, Any]) -> str:
    g, sp = summ["generic"], summ["spec_probe"]
    lines = [f"# Detection of reproduced historical bugs: campaign {campaign}", "",
             "A case is detected when an oracle confirms (3/3) a signature on the pre-fix build that it does not confirm "
             "on the post-fix build. `author_match` is for the author: does the signature show the case's reported bug?",
             "", f"- cases with a generic ground-truth probe: {g['cases']} ({g['complete']} with every run finished), "
             f"detected {g['detected']}; by oracle {g['detected_by_oracle'] or '-'}",
             f"- cases whose ground truth used the specification probe edit_text_differs (reported separately): "
             f"{sp['cases']} ({sp['complete']} finished), detected {sp['detected']}; by oracle {sp['detected_by_oracle'] or '-'}"]
    for title, spec in (("Cases (generic ground-truth probes)", False), ("Cases whose ground truth used edit_text_differs", True)):
        sel = [e for e in entries if e["spec_probe"] == spec]
        lines += ["", f"## {title}", "", "| case | kind | class / subtype | ground-truth probe | builds | detected | "
                  "oracles with pre-only signatures | runs finished |", "|---|---|---|---|---|---|---|---|"]
        for e in sel:
            oracles = sorted({p["oracle"] for p in e["pre_only"]})
            lines.append(f"| {e['case']} | {e['kind']} | {e['class']} / {e['subtype']} | {e['probe']} | "
                         f"{e['builds']['pre']} -> {e['builds']['post']} | {'yes' if e['detected'] else 'no'} | "
                         f"{', '.join(oracles) or '-'} | {'yes' if e['complete'] else 'no'} |")
    lines += ["", "## Pre-only signatures", "", "| case | oracle | signature | pre-fix violations | runs finished | "
              "author_match |", "|---|---|---|---|---|---|"]
    for e in entries:
        for p in e["pre_only"]:
            sig = p["signature"].replace("|", "\\|")
            lines.append(f"| {e['case']} | {p['oracle']} | `{sig}` | {', '.join(p['vids'][:3])} | "
                         f"{'yes' if p['complete'] else 'no'} | {p['author_match']} |")
    lines += ["", "## Confirmed signatures per case and oracle (pre / post)", "",
              "| case | oracle | pre | post | runs pre | runs post | labelled (pre / post, not replayed) |",
              "|---|---|---|---|---|---|---|"]
    for e in entries:
        for name, o in e["oracles"].items():
            lines.append(f"| {e['case']} | {name} | {len(o['pre'])} | {len(o['post'])} | {o['runs']['pre']} | "
                         f"{o['runs']['post']} | {len(o['labelled']['pre'])} / {len(o['labelled']['post'])} |")
    return "\n".join(lines) + "\n"


def author_values(path: str) -> Dict[Tuple[str, str, str], str]:
    """author_match values already entered in an earlier detection.json."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return {(str(c["case"]), str(p["oracle"]), str(p["signature"])): str(p.get("author_match", ""))
            for c in doc.get("cases", []) for p in c.get("pre_only", []) if p.get("author_match")}


def main() -> int:
    from campaign import load_plan  # late import: campaign imports the oracle registry
    from campaign_config import parse_config

    ap = argparse.ArgumentParser(description="Detection table of a benchmark campaign.")
    ap.add_argument("campaign")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    paths = paths_for(args.campaign)
    with open(paths.config, "r", encoding="utf-8") as f:
        doc = json.load(f)
    raw = doc["config"]
    cfg, runs, _, _ = load_plan(parse_config(raw), bool(doc.get("dry_run")))
    planned = [s.to_json() for s in runs]
    cases = [c for c in raw.get("bench_cases") or [] if any(s["project"] == c["case"] for s in planned)]
    out_json = os.path.join(paths.root, "detection.json")
    entries = detect(cases, planned, read_jsonl(paths.results), read_jsonl(paths.violations), author_values(out_json))
    summ = summary(entries)
    write_json(out_json, {"campaign": args.campaign, "generated": time.strftime("%Y-%m-%d %H:%M"), "summary": summ,
                          "cases": entries})
    with open(os.path.join(paths.root, "detection.md"), "w", encoding="utf-8") as f:
        f.write(render(args.campaign, entries, summ))
    print(f"{args.campaign}: {summ['generic']['detected']}/{summ['generic']['cases']} generic-probe cases detected, "
          f"{summ['spec_probe']['detected']}/{summ['spec_probe']['cases']} specification-probe cases; "
          f"see {os.path.relpath(os.path.join(paths.root, 'detection.md'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
