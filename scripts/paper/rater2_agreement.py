"""Agreement between the author's verdicts and the second rater's on a campaign's finding groups.

Reads data/lsptest/runs/<campaign>/triage/decisions.csv (the author's verdict per group) and
rater2_decisions.csv (written by scripts/paper/import_rater2.py), and only for the groups both judged
(bug / legitimate / tool-artifact) computes:
- three-class Cohen's kappa, percent agreement and the confusion matrix (rows: author, columns: rater 2);
- the same for "bug or not" (legitimate and tool-artifact merged);
- for each kappa a 95% confidence interval from the large-sample variance of Fleiss, Cohen and Everitt
  (1969), kappa +- 1.96 SE (clipped to [-1, 1]), and, as a check, a percentile bootstrap interval
  (groups resampled with replacement, 10000 resamples, fixed seed; resamples with undefined kappa skipped);
- the agreement within each relation R0-R6 (relation from triage.json), with kappa where it is defined;
- descriptively, the agreement of the exception class among groups both raters gave the same non-bug
  verdict and a class (the author's class from verdict_reasons.csv, when present);
- the number of groups each rater left out, and of rater-2 notes that say the rater was unsure;
- the three-class and bug-or-not statistics again with the groups the rater's note marks as unsure recoded to
  legitimate, the default the author's judging page gave for groups that stay unclear (the second rater
  is asked for the most likely verdict plus the word 不确定, so both readings can be computed).
Writes rater2_agreement.json and rater2_agreement.md next to the inputs; reads nothing else and writes
no other file.

Run line: python3 scripts/paper/rater2_agreement.py [main_v1] [--bootstrap 10000] [--seed 20261117]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import logging
import math
import os
import random
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
VERDICTS: Tuple[str, ...] = ("bug", "legitimate", "tool-artifact")
BINARY: Tuple[str, ...] = ("bug", "not bug")
ORACLE_RELATION = {"r0_crash": "R0", "r1_history": "R1", "r2_handles": "R2", "r3_routes": "R3", "r4_edits": "R4",
                   "r5_transforms": "R5", "r6_crossimpl": "R6"}
RELATIONS: Tuple[str, ...] = ("R0", "R1", "R2", "R3", "R4", "R5", "R6")
Z95 = 1.959963984540054
BOOTSTRAP = 10000
SEED = 20261117
UNSURE_RE = re.compile(r"不确定|拿不准|unsure|not sure", re.I)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ statistics
def confusion(pairs: Sequence[Tuple[str, str]], cats: Sequence[str]) -> List[List[int]]:
    """Counts with rows = first rater's category, columns = second rater's, in the order of cats."""
    index = {c: i for i, c in enumerate(cats)}
    table = [[0] * len(cats) for _ in cats]
    for a, b in pairs:
        table[index[a]][index[b]] += 1
    return table


def _props(table: Sequence[Sequence[int]]) -> Tuple[int, List[List[float]], List[float], List[float]]:
    n = sum(sum(r) for r in table)
    k = len(table)
    p = [[x / n for x in r] for r in table] if n else [[0.0] * k for _ in range(k)]
    rows = [sum(p[i]) for i in range(k)]
    cols = [sum(p[i][j] for i in range(k)) for j in range(k)]
    return n, p, rows, cols


def kappa_parts(table: Sequence[Sequence[int]]) -> Optional[Tuple[float, float, float]]:
    """(observed agreement, chance agreement, Cohen's kappa); None when n = 0 or kappa is undefined (pe = 1)."""
    n, p, rows, cols = _props(table)
    if n == 0:
        return None
    po = sum(p[i][i] for i in range(len(table)))
    pe = sum(rows[i] * cols[i] for i in range(len(table)))
    if pe >= 1 - 1e-12:
        return None
    return po, pe, (po - pe) / (1 - pe)


def cohen_kappa(table: Sequence[Sequence[int]]) -> Optional[float]:
    parts = kappa_parts(table)
    return parts[2] if parts else None


def kappa_variance(table: Sequence[Sequence[int]]) -> Optional[float]:
    """Large-sample variance of kappa (Fleiss, Cohen and Everitt 1969, "Large sample standard errors of kappa
    and weighted kappa"); it equals the delta-method variance under multinomial sampling of the groups.

    var = [sum_i p_ii (1 - (p_i. + p_.i)(1 - k))^2 + (1 - k)^2 sum_{i != j} p_ij (p_.i + p_j.)^2
           - (k - pe (1 - k))^2] / (n (1 - pe)^2)
    """
    parts = kappa_parts(table)
    if parts is None:
        return None
    _, pe, kap = parts
    n, p, rows, cols = _props(table)
    k = len(table)
    a = sum(p[i][i] * (1 - (rows[i] + cols[i]) * (1 - kap)) ** 2 for i in range(k))
    b = (1 - kap) ** 2 * sum(p[i][j] * (cols[i] + rows[j]) ** 2 for i in range(k) for j in range(k) if i != j)
    c = (kap - pe * (1 - kap)) ** 2
    return max(0.0, (a + b - c) / (n * (1 - pe) ** 2))


def asymptotic_ci(table: Sequence[Sequence[int]], z: float = Z95) -> Optional[Tuple[float, float]]:
    """kappa +- z SE, clipped to [-1, 1]."""
    kap, var = cohen_kappa(table), kappa_variance(table)
    if kap is None or var is None:
        return None
    se = math.sqrt(var)
    return max(-1.0, kap - z * se), min(1.0, kap + z * se)


def percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear interpolation between order statistics (numpy's default)."""
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def bootstrap_ci(pairs: Sequence[Tuple[str, str]], cats: Sequence[str], resamples: int = BOOTSTRAP,
                 seed: int = SEED) -> Optional[Dict[str, Any]]:
    """Percentile bootstrap interval of kappa over the pairs; resamples with undefined kappa are skipped."""
    if not pairs or resamples <= 0:
        return None
    rng = random.Random(seed)
    n = len(pairs)
    values: List[float] = []
    for _ in range(resamples):
        kap = cohen_kappa(confusion([pairs[rng.randrange(n)] for _ in range(n)], cats))
        if kap is not None:
            values.append(kap)
    if not values:
        return None
    values.sort()
    return {"ci95": [percentile(values, 0.025), percentile(values, 0.975)], "resamples": resamples,
            "defined": len(values), "seed": seed}


def summary(pairs: Sequence[Tuple[str, str]], cats: Sequence[str], resamples: int, seed: int) -> Dict[str, Any]:
    """Kappa, agreement, intervals, confusion matrix and marginals of one categorization."""
    table = confusion(pairs, cats)
    parts = kappa_parts(table)
    var = kappa_variance(table)
    n = len(pairs)
    agree = sum(table[i][i] for i in range(len(cats)))
    ci = asymptotic_ci(table)
    return {"categories": list(cats), "n": n, "agree": agree,
            "percent_agreement": round(100 * agree / n, 2) if n else None,
            "observed_agreement": parts[0] if parts else (agree / n if n else None),
            "expected_agreement": parts[1] if parts else None,
            "kappa": parts[2] if parts else None,
            "se_asymptotic": math.sqrt(var) if var is not None else None,
            "ci95_asymptotic": list(ci) if ci else None,
            "bootstrap": bootstrap_ci(pairs, cats, resamples, seed),
            "confusion": {"rows": "author", "columns": "rater 2", "matrix": table},
            "marginals": {"author": {c: sum(table[i]) for i, c in enumerate(cats)},
                          "rater2": {c: sum(r[j] for r in table) for j, c in enumerate(cats)}}}


def to_binary(verdict: str) -> str:
    return "bug" if verdict == "bug" else "not bug"


# ------------------------------------------------------------------ inputs
def read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(f)]


def relations(triage_json: Optional[str], groups: Sequence[str]) -> Dict[str, str]:
    """group -> R0..R6, from triage.json's signatures, else from the '-rN-' part of the group name."""
    out: Dict[str, str] = {}
    if triage_json and os.path.exists(triage_json):
        with open(triage_json, "r", encoding="utf-8") as f:
            for g in json.load(f)["groups"]:
                out[g["gid"]] = ORACLE_RELATION.get(g["signature"].split("|")[1], "?")
    for g in groups:
        if g not in out:
            m = re.search(r"-r(\d)-", g)
            out[g] = f"R{m.group(1)}" if m else "?"
    return out


def shown(path: str) -> str:
    """The path relative to the repository, or absolute when it lies outside."""
    rel = os.path.relpath(os.path.abspath(path), REPO)
    return os.path.abspath(path) if rel.startswith("..") else rel


def sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def agreement(author: Mapping[str, str], rater2_rows: Sequence[Mapping[str, str]], rel: Mapping[str, str],
              universe: Sequence[str] = (), author_class: Optional[Mapping[str, str]] = None,
              resamples: int = BOOTSTRAP, seed: int = SEED) -> Dict[str, Any]:
    """All agreement statistics for the groups both raters judged (author: group -> verdict)."""
    known = set(universe) | set(author)
    rater2 = {r["group"]: r for r in rater2_rows if r.get("group")}
    a_ok = {g: v for g, v in author.items() if v in VERDICTS}
    r_ok = {g: r["verdict"] for g, r in rater2.items() if r.get("verdict") in VERDICTS and g in known}
    both = sorted(set(a_ok) & set(r_ok))
    pairs = [(a_ok[g], r_ok[g]) for g in both]
    by_relation: Dict[str, Any] = {}
    for name in RELATIONS:
        sub = [(a_ok[g], r_ok[g]) for g in both if rel.get(g) == name]
        if not sub:
            continue
        agree = sum(1 for a, b in sub if a == b)
        by_relation[name] = {"n": len(sub), "agree": agree, "percent_agreement": round(100 * agree / len(sub), 1),
                             "kappa": cohen_kappa(confusion(sub, VERDICTS)),
                             "kappa_bug": cohen_kappa(confusion([(to_binary(a), to_binary(b)) for a, b in sub], BINARY))}
    cls: Dict[str, Any] = {}
    if author_class is not None:
        same = [g for g in both if a_ok[g] == r_ok[g] != "bug" and author_class.get(g) and rater2[g].get("class")]
        cls = {"n": len(same), "agree": sum(1 for g in same if author_class[g] == rater2[g]["class"]),
               "note": "groups both raters judged legitimate (or both tool-artifact) and both gave a class"}
        cls["percent_agreement"] = round(100 * cls["agree"] / len(same), 1) if same else None
    unsure = [g for g in both if UNSURE_RE.search(rater2[g].get("note", ""))]
    # The author's page said: still unsure -> legitimate, note "unsure". The second rater picks the most
    # likely verdict and notes "不确定"; recoding those unsure groups to legitimate applies the author's rule.
    recoded = [(a_ok[g], "legitimate" if g in unsure else r_ok[g]) for g in both]
    return {
        "groups": {"universe": len(known), "author_judged": len(a_ok), "rater2_judged": len(r_ok), "both": len(both),
                   "missing_from_rater2": sorted(set(known) - set(r_ok)),
                   "missing_from_author": sorted(set(r_ok) - set(a_ok)),
                   "rater2_unknown_groups": sorted(set(rater2) - known),
                   "rater2_rows_without_verdict": sorted(g for g, r in rater2.items()
                                                         if g in known and r.get("verdict") not in VERDICTS)},
        "three_class": summary(pairs, VERDICTS, resamples, seed),
        "bug_or_not": summary([(to_binary(a), to_binary(b)) for a, b in pairs], BINARY, resamples, seed),
        "by_relation": by_relation,
        "class_agreement": cls,
        "rater2_unsure": {"n": len(unsure), "groups": unsure,
                          "agree": sum(1 for g in unsure if a_ok[g] == r_ok[g])},
        "unsure_as_legitimate": {
            "note": "rater-2 verdicts of the groups the rater's note marks as unsure recoded to legitimate, the default "
                    "the author's judging page gave for groups that stay unclear",
            "three_class": summary(recoded, VERDICTS, resamples, seed),
            "bug_or_not": summary([(to_binary(a), to_binary(b)) for a, b in recoded], BINARY, resamples, seed)},
        "method": {
            "kappa": "Cohen's kappa on the groups both raters judged",
            "ci95_asymptotic": "kappa +- 1.96 SE, SE from the large-sample variance of Fleiss, Cohen and Everitt "
                               "(1969); clipped to [-1, 1]",
            "bootstrap": f"percentile interval, groups resampled with replacement, {resamples} resamples, seed {seed}; "
                         "resamples with undefined kappa skipped",
            "by_relation": "relation from triage.json; kappa is null where it is undefined (one category only)"}}


# ------------------------------------------------------------------ outputs
def _f(x: Optional[float], digits: int = 3) -> str:
    return "–" if x is None else f"{x:.{digits}f}"


def _ci(ci: Optional[Sequence[float]]) -> str:
    return "–" if not ci else f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def markdown(res: Mapping[str, Any]) -> str:
    g = res["groups"]
    lines = [f"# Second-rater agreement, {res['campaign']}", "",
             f"Generated {res['generated']} by `scripts/paper/rater2_agreement.py` from `{res['inputs']['author']}` "
             f"and `{res['inputs']['rater2']}`.", "",
             f"Groups: {g['universe']} in the triage; the author judged {g['author_judged']}, the second rater "
             f"{g['rater2_judged']}; both {g['both']}. Missing from the second rater: {len(g['missing_from_rater2'])}; "
             f"from the author: {len(g['missing_from_author'])}; unknown groups in the rater-2 file: "
             f"{len(g['rater2_unknown_groups'])}; rater-2 rows without a verdict: {len(g['rater2_rows_without_verdict'])}.",
             "", "| | n | agreement | kappa | SE | 95% CI (asymptotic) | 95% CI (bootstrap) |", "|---|---:|---:|---:|---:|---|---|"]
    rows = [(res[k], label) for k, label in (("three_class", "three classes"), ("bug_or_not", "bug or not"))]
    rows += [(res["unsure_as_legitimate"][k], label + ", unsure as legitimate")
             for k, label in (("three_class", "three classes"), ("bug_or_not", "bug or not"))]
    for s, label in rows:
        boot = s["bootstrap"]["ci95"] if s["bootstrap"] else None
        pct = "–" if s["percent_agreement"] is None else f"{s['percent_agreement']:.1f}%"
        lines.append(f"| {label} | {s['n']} | {s['agree']} ({pct}) | {_f(s['kappa'])} | {_f(s['se_asymptotic'])} | "
                     f"{_ci(s['ci95_asymptotic'])} | {_ci(boot)} |")
    for key, label in (("three_class", "Confusion matrix, three classes"), ("bug_or_not", "Confusion matrix, bug or not")):
        s = res[key]
        cats = s["categories"]
        lines += ["", f"{label} (rows: author, columns: rater 2):", "",
                  "| author \\ rater 2 | " + " | ".join(cats) + " | total |", "|---|" + "---:|" * (len(cats) + 1)]
        for c, row in zip(cats, s["confusion"]["matrix"], strict=True):
            lines.append(f"| {c} | " + " | ".join(str(x) for x in row) + f" | {sum(row)} |")
        cols = [sum(r[j] for r in s["confusion"]["matrix"]) for j in range(len(cats))]
        lines.append("| total | " + " | ".join(str(x) for x in cols) + f" | {sum(cols)} |")
    lines += ["", "By relation:", "", "| relation | n | agree | agreement | kappa (3 classes) | kappa (bug or not) |",
              "|---|---:|---:|---:|---:|---:|"]
    for name, r in res["by_relation"].items():
        lines.append(f"| {name} | {r['n']} | {r['agree']} | {r['percent_agreement']:.1f}% | {_f(r['kappa'])} | "
                     f"{_f(r['kappa_bug'])} |")
    cls, uns = res["class_agreement"], res["rater2_unsure"]
    if cls:
        pct = "–" if cls["percent_agreement"] is None else f"{cls['percent_agreement']:.1f}%"
        lines += ["", f"Exception class (descriptive): {cls['agree']} of {cls['n']} {cls['note']} agree ({pct})."]
    lines += ["", f"Rater-2 notes marking the group as unsure: {uns['n']} (author agrees on {uns['agree']}). "
              f"The rows 'unsure as legitimate' recode those groups to legitimate: "
              f"{res['unsure_as_legitimate']['note']}.", "",
              "Method: " + "; ".join(f"{k}: {v}" for k, v in res["method"].items()) + "."]
    for key, label in (("missing_from_rater2", "Missing from the second rater"),
                       ("missing_from_author", "Missing from the author"),
                       ("rater2_unknown_groups", "Unknown groups in the rater-2 file")):
        if g[key]:
            lines += ["", f"{label}: " + ", ".join(f"`{x}`" for x in g[key])]
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="Agreement between the author's and the second rater's verdicts.")
    ap.add_argument("campaign", nargs="?", default="main_v1")
    ap.add_argument("--decisions", help="the author's CSV (default: the campaign's decisions.csv)")
    ap.add_argument("--rater2", help="the second rater's CSV (default: the campaign's rater2_decisions.csv)")
    ap.add_argument("--out", help="output path without extension (default: the campaign's triage/rater2_agreement)")
    ap.add_argument("--bootstrap", type=int, default=BOOTSTRAP, help="bootstrap resamples (0: none)")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)
    tdir = os.path.join(REPO, "data", "lsptest", "runs", args.campaign, "triage")
    dec = args.decisions or os.path.join(tdir, "decisions.csv")
    r2 = args.rater2 or os.path.join(tdir, "rater2_decisions.csv")
    out = args.out or os.path.join(tdir, "rater2_agreement")
    try:
        author = {r["group"]: r.get("verdict", "") for r in read_csv(dec) if r.get("group")}
        rater2_rows = read_csv(r2)
        triage_json = os.path.join(os.path.dirname(dec), "triage.json")
        universe = list(relations(triage_json, []).keys())
        reasons = os.path.join(os.path.dirname(dec), "verdict_reasons.csv")
        author_class = {r["group"]: r.get("class", "") for r in read_csv(reasons)} if os.path.exists(reasons) else None
    except (OSError, KeyError, ValueError) as e:
        logger.error("cannot read the inputs: %s", e)
        return 2
    rel = relations(triage_json, list(author) + [r.get("group", "") for r in rater2_rows])
    res: Dict[str, Any] = {"campaign": args.campaign, "generated": dt.datetime.now().isoformat(timespec="seconds"),
                           "inputs": {"author": shown(dec), "rater2": shown(r2),
                                      "author_sha256": sha256(dec), "rater2_sha256": sha256(r2)}}
    res.update(agreement(author, rater2_rows, rel, universe, author_class, args.bootstrap, args.seed))
    with open(out + ".json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
        f.write("\n")
    with open(out + ".md", "w", encoding="utf-8") as f:
        f.write(markdown(res))
    t, b = res["three_class"], res["bug_or_not"]
    print(f"wrote {shown(out)}.json/.md: both judged {res['groups']['both']}, "
          f"kappa {_f(t['kappa'])} {_ci(t['ci95_asymptotic'])}, bug-or-not kappa {_f(b['kappa'])} "
          f"{_ci(b['ci95_asymptotic'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
