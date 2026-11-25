"""Agreement between the author's and the second rater's judgements of the benchmark's pre-only signatures.

Reads data/lsptest/runs/<campaign>/detection_author.csv (author_match per signature), detection_rater2.csv
(written by scripts/paper/import_rater2_detection.py) and, for the list of signatures and their relation and
server, detection.json (its author_match field is not used). Only for the signatures both judged (yes /
partial / no) it computes, with the statistics of scripts/paper/rater2_agreement.py:
- three-class Cohen's kappa, percent agreement and the confusion matrix (rows: author, columns: rater 2);
- the same for "counts as a detection or not" (yes against partial and no, the paper's rule);
- for each kappa the Fleiss-Cohen-Everitt asymptotic 95% interval and a percentile bootstrap check;
- the agreement within each relation R0-R6 and each server;
- at the case level, whether each rater makes the case a detection (at least one yes among its signatures),
  over the cases whose signatures both judged in full;
- the number of rater-2 notes that say the rater was unsure (不确定, unsure, ...), and the statistics again with
  those signatures recoded to no, the reading that does not count an unsure signature as a detection;
- the statistics again without the cases used as practice examples in the second rater's manual
  (plan/rater2_manual_zh.html; PRACTICE_CASES): the manual explains those bugs, so the rater's judgements of
  their signatures are not independent of what the manual told him;
- the list of signatures the two judged differently, with both notes.
Writes detection_rater2_agreement.json and .md next to the inputs; reads nothing else and writes no other file.

Run line: python3 scripts/paper/detection_agreement.py [bench_v1] [--bootstrap 10000] [--seed 20261118]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import rater2_agreement as ra

REPO = ra.REPO
VERDICTS: Tuple[str, ...] = ("yes", "partial", "no")
BINARY: Tuple[str, ...] = ("detected", "not detected")
SEED = 20261118
# The four practice examples of plan/rater2_manual_zh.html (written for the group page, 2026-11-17); three of them
# are benchmark cases with pre-only signatures (gopls-36824: 7, pyright-9681: 1, pyright-8946: 7).
PRACTICE_CASES: Tuple[str, ...] = ("gopls-46667", "gopls-36824", "pyright-9681", "pyright-8946")
Key = Tuple[str, str]

logger = logging.getLogger(__name__)


def to_binary(verdict: str) -> str:
    return "detected" if verdict == "yes" else "not detected"


def signatures(doc: Mapping[str, Any]) -> Dict[Key, Dict[str, str]]:
    """(case, signature) -> relation and server, for the pre-only signatures of the detected cases."""
    out: Dict[Key, Dict[str, str]] = {}
    for c in doc.get("cases", []):
        if not c.get("detected"):
            continue
        for p in c.get("pre_only", []):
            out[(str(c["case"]), str(p["signature"]))] = {
                "relation": ra.ORACLE_RELATION.get(str(p["oracle"]), "?"), "server": str(c.get("kind", "?"))}
    return out


def label(k: Key) -> str:
    return f"{k[0]} {k[1]}"


def _stats(pairs: Sequence[Tuple[str, str]], resamples: int, seed: int) -> Dict[str, Any]:
    return {"three_class": ra.summary(pairs, VERDICTS, resamples, seed),
            "detected_or_not": ra.summary([(to_binary(a), to_binary(b)) for a, b in pairs], BINARY, resamples, seed)}


def _subset(pairs: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    agree = sum(1 for a, b in pairs if a == b)
    return {"n": len(pairs), "agree": agree, "percent_agreement": round(100 * agree / len(pairs), 1),
            "kappa": ra.cohen_kappa(ra.confusion(pairs, VERDICTS)),
            "kappa_detected": ra.cohen_kappa(ra.confusion([(to_binary(a), to_binary(b)) for a, b in pairs], BINARY))}


def case_level(both: Sequence[Key], a_ok: Mapping[Key, str], r_ok: Mapping[Key, str], universe: Sequence[Key],
               resamples: int, seed: int) -> Dict[str, Any]:
    """Detection per case (some signature judged yes), over the cases whose signatures both judged in full."""
    judged = set(both)
    cases = sorted({c for c, _ in universe})
    full = [c for c in cases if all(k in judged for k in universe if k[0] == c)]
    pairs = [(to_binary("yes" if any(a_ok[k] == "yes" for k in universe if k[0] == c) else "no"),
              to_binary("yes" if any(r_ok[k] == "yes" for k in universe if k[0] == c) else "no")) for c in full]
    s = ra.summary(pairs, BINARY, resamples, seed)
    return {"cases": len(cases), "judged_in_full": len(full), "summary": s,
            "author_detected": sum(1 for a, _ in pairs if a == "detected"),
            "rater2_detected": sum(1 for _, b in pairs if b == "detected"),
            "differ": [{"case": c, "author": a, "rater2": b} for c, (a, b) in zip(full, pairs, strict=True) if a != b]}


def agreement(author_rows: Sequence[Mapping[str, str]], rater2_rows: Sequence[Mapping[str, str]],
              sigs: Mapping[Key, Mapping[str, str]], resamples: int = ra.BOOTSTRAP, seed: int = SEED) -> Dict[str, Any]:
    """All agreement statistics for the signatures both raters judged."""
    author = {(r.get("case", ""), r.get("signature", "")): r for r in author_rows}
    rater2 = {(r.get("case", ""), r.get("signature", "")): r for r in rater2_rows}
    a_ok = {k: r["author_match"] for k, r in author.items() if k in sigs and r.get("author_match") in VERDICTS}
    r_ok = {k: r["verdict"] for k, r in rater2.items() if k in sigs and r.get("verdict") in VERDICTS}
    universe = list(sigs)
    both = [k for k in universe if k in a_ok and k in r_ok]
    pairs = [(a_ok[k], r_ok[k]) for k in both]
    by: Dict[str, Dict[str, Any]] = {"relation": {}, "server": {}}
    for field in by:
        for name in sorted({sigs[k][field] for k in both}):
            by[field][name] = _subset([(a_ok[k], r_ok[k]) for k in both if sigs[k][field] == name])
    unsure = [k for k in both if ra.UNSURE_RE.search(rater2[k].get("note", ""))]
    recoded = {k: ("no" if k in unsure else r_ok[k]) for k in both}
    res: Dict[str, Any] = {
        "signatures": {"universe": len(universe), "author_judged": len(a_ok), "rater2_judged": len(r_ok),
                       "both": len(both),
                       "missing_from_rater2": [label(k) for k in universe if k not in r_ok],
                       "missing_from_author": [label(k) for k in universe if k not in a_ok],
                       "rater2_unknown": sorted(label(k) for k in rater2 if k not in sigs),
                       "author_unknown": sorted(label(k) for k in author if k not in sigs)}}
    res.update(_stats(pairs, resamples, seed))
    res["by_relation"], res["by_server"] = by["relation"], by["server"]
    res["cases"] = case_level(both, a_ok, r_ok, universe, resamples, seed)
    res["rater2_unsure"] = {"n": len(unsure), "signatures": [label(k) for k in unsure],
                            "agree": sum(1 for k in unsure if a_ok[k] == r_ok[k])}
    res["unsure_as_no"] = {"note": "rater-2 verdicts of the signatures the rater's note marks as unsure recoded to no: "
                                   "an unsure signature does not count as a detection"}
    res["unsure_as_no"].update(_stats([(a_ok[k], recoded[k]) for k in both], resamples, seed))
    res["unsure_as_no"]["cases"] = case_level(both, a_ok, recoded, universe, resamples, seed)
    indep = [k for k in both if k[0] not in PRACTICE_CASES]
    res["without_practice_cases"] = {
        "note": "signatures of the cases used as practice examples in the second rater's manual left out",
        "excluded_cases": sorted({k[0] for k in both if k[0] in PRACTICE_CASES}),
        "excluded_signatures": len(both) - len(indep)}
    res["without_practice_cases"].update(_stats([(a_ok[k], r_ok[k]) for k in indep], resamples, seed))
    res["without_practice_cases"]["cases"] = case_level(indep, a_ok, r_ok,
                                                        [k for k in universe if k[0] not in PRACTICE_CASES],
                                                        resamples, seed)
    res["disagreements"] = [{"case": k[0], "signature": k[1], "relation": sigs[k]["relation"], "author": a_ok[k],
                             "rater2": r_ok[k], "author_note": author[k].get("note", ""),
                             "rater2_note": rater2[k].get("note", "")} for k in both if a_ok[k] != r_ok[k]]
    res["method"] = {
        "kappa": "Cohen's kappa on the signatures both raters judged; detected_or_not: yes against partial and no",
        "ci95_asymptotic": "kappa +- 1.96 SE, SE from the large-sample variance of Fleiss, Cohen and Everitt (1969); "
                           "clipped to [-1, 1]",
        "bootstrap": f"percentile interval, signatures resampled with replacement, {resamples} resamples, seed {seed}; "
                     "resamples with undefined kappa skipped",
        "cases": "a case counts as detected by a rater when at least one of its signatures is judged yes; only cases "
                 "whose signatures both judged in full",
        "by_relation": "kappa is null where it is undefined (one category only)"}
    return res


def _row(s: Mapping[str, Any], label: str) -> str:
    boot = s["bootstrap"]["ci95"] if s["bootstrap"] else None
    pct = "–" if s["percent_agreement"] is None else f"{s['percent_agreement']:.1f}%"
    return (f"| {label} | {s['n']} | {s['agree']} ({pct}) | {ra._f(s['kappa'])} | {ra._f(s['se_asymptotic'])} | "
            f"{ra._ci(s['ci95_asymptotic'])} | {ra._ci(boot)} |")


def _matrix(s: Mapping[str, Any], title: str) -> List[str]:
    cats = s["categories"]
    out = ["", f"{title} (rows: author, columns: rater 2):", "",
           "| author \\ rater 2 | " + " | ".join(cats) + " | total |", "|---|" + "---:|" * (len(cats) + 1)]
    for c, row in zip(cats, s["confusion"]["matrix"], strict=True):
        out.append(f"| {c} | " + " | ".join(str(x) for x in row) + f" | {sum(row)} |")
    cols = [sum(r[j] for r in s["confusion"]["matrix"]) for j in range(len(cats))]
    return out + ["| total | " + " | ".join(str(x) for x in cols) + f" | {sum(cols)} |"]


def markdown(res: Mapping[str, Any]) -> str:
    g, c, u, w = res["signatures"], res["cases"], res["unsure_as_no"], res["without_practice_cases"]
    lines = [f"# Second-rater agreement on the benchmark signatures, {res['campaign']}", "",
             f"Generated {res['generated']} by `scripts/paper/detection_agreement.py` from `{res['inputs']['author']}` "
             f"and `{res['inputs']['rater2']}`.", "",
             f"Signatures: {g['universe']} pre-only signatures; the author judged {g['author_judged']}, the second rater "
             f"{g['rater2_judged']}; both {g['both']}. Missing from the second rater: {len(g['missing_from_rater2'])}; "
             f"from the author: {len(g['missing_from_author'])}; unknown rows: rater 2 {len(g['rater2_unknown'])}, "
             f"author {len(g['author_unknown'])}.", "",
             "| | n | agreement | kappa | SE | 95% CI (asymptotic) | 95% CI (bootstrap) |",
             "|---|---:|---:|---:|---:|---|---|",
             _row(res["three_class"], "three classes"), _row(res["detected_or_not"], "detected or not"),
             _row(c["summary"], "case detected or not"),
             _row(u["three_class"], "three classes, unsure as no"),
             _row(u["detected_or_not"], "detected or not, unsure as no"),
             _row(u["cases"]["summary"], "case detected or not, unsure as no"),
             _row(w["three_class"], "three classes, without practice cases"),
             _row(w["detected_or_not"], "detected or not, without practice cases"),
             _row(w["cases"]["summary"], "case detected or not, without practice cases")]
    lines += ["", f"Without practice cases: the manual's practice examples cover {len(w['excluded_cases'])} cases on this page ({', '.join(w['excluded_cases']) or 'none'}), {w['excluded_signatures']} signatures left out."]
    lines += _matrix(res["three_class"], "Confusion matrix, three classes")
    lines += _matrix(res["detected_or_not"], "Confusion matrix, detected or not")
    lines += ["", f"Cases: {c['cases']}, judged in full by both {c['judged_in_full']}; detected by the author "
              f"{c['author_detected']}, by the second rater {c['rater2_detected']}; differ on {len(c['differ'])}"
              + (": " + ", ".join(f"`{d['case']}` ({d['author']} / {d['rater2']})" for d in c["differ"]) if c["differ"]
                 else "") + "."]
    for key, title in (("by_relation", "relation"), ("by_server", "server")):
        lines += ["", f"By {title}:", "", f"| {title} | n | agree | agreement | kappa (3 classes) | kappa (detected) |",
                  "|---|---:|---:|---:|---:|---:|"]
        lines += [f"| {name} | {r['n']} | {r['agree']} | {r['percent_agreement']:.1f}% | {ra._f(r['kappa'])} | "
                  f"{ra._f(r['kappa_detected'])} |" for name, r in res[key].items()]
    uns = res["rater2_unsure"]
    lines += ["", f"Rater-2 notes marking the signature as unsure: {uns['n']} (author agrees on {uns['agree']}). "
              f"The rows 'unsure as no': {u['note']}."]
    if res["disagreements"]:
        lines += ["", "Signatures judged differently:", "", "| case | signature | author | rater 2 | rater-2 note |",
                  "|---|---|---|---|---|"]
        lines += [f"| {d['case']} | `{d['signature']}` | {d['author']} | {d['rater2']} | "
                  f"{d['rater2_note'].replace('|', '/').replace(chr(10), ' ')} |" for d in res["disagreements"]]
    lines += ["", "Method: " + "; ".join(f"{k}: {v}" for k, v in res["method"].items()) + "."]
    for key, label in (("missing_from_rater2", "Missing from the second rater"),
                       ("missing_from_author", "Missing from the author")):
        if g[key]:
            lines += ["", f"{label}: " + ", ".join(f"`{x}`" for x in g[key])]
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="Agreement on the benchmark signatures between the author and rater 2.")
    ap.add_argument("campaign", nargs="?", default="bench_v1")
    ap.add_argument("--author", help="the author's CSV (default: the campaign's detection_author.csv)")
    ap.add_argument("--rater2", help="the second rater's CSV (default: the campaign's detection_rater2.csv)")
    ap.add_argument("--detection", help="detection.json (default: the campaign's)")
    ap.add_argument("--out", help="output path without extension (default: the campaign's detection_rater2_agreement)")
    ap.add_argument("--bootstrap", type=int, default=ra.BOOTSTRAP, help="bootstrap resamples (0: none)")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)
    run_dir = os.path.join(REPO, "data", "lsptest", "runs", args.campaign)
    author = args.author or os.path.join(run_dir, "detection_author.csv")
    r2 = args.rater2 or os.path.join(run_dir, "detection_rater2.csv")
    det = args.detection or os.path.join(run_dir, "detection.json")
    out = args.out or os.path.join(run_dir, "detection_rater2_agreement")
    try:
        author_rows, rater2_rows = ra.read_csv(author), ra.read_csv(r2)
        with open(det, "r", encoding="utf-8") as f:
            sigs = signatures(json.load(f))
    except (OSError, KeyError, ValueError) as e:
        logger.error("cannot read the inputs: %s", e)
        return 2
    res: Dict[str, Any] = {"campaign": args.campaign, "generated": dt.datetime.now().isoformat(timespec="seconds"),
                           "inputs": {"author": ra.shown(author), "rater2": ra.shown(r2), "detection": ra.shown(det),
                                      "author_sha256": ra.sha256(author), "rater2_sha256": ra.sha256(r2),
                                      "detection_sha256": ra.sha256(det)}}
    res.update(agreement(author_rows, rater2_rows, sigs, args.bootstrap, args.seed))
    with open(out + ".json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
        f.write("\n")
    with open(out + ".md", "w", encoding="utf-8") as f:
        f.write(markdown(res))
    t, b = res["three_class"], res["detected_or_not"]
    print(f"wrote {ra.shown(out)}.json/.md: both judged {res['signatures']['both']}, "
          f"kappa {ra._f(t['kappa'])} {ra._ci(t['ci95_asymptotic'])}, detected-or-not kappa {ra._f(b['kappa'])} "
          f"{ra._ci(b['ci95_asymptotic'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
