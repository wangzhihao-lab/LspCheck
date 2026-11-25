"""Tests of the second rater's tools: page, import and agreement.

The kappa tests use small tables whose values are worked out by hand in the comments: the 2x2 table of
the classic textbook example (kappa 0.4) with its Fleiss-Cohen-Everitt variance, a 3x3 table (kappa
203/293) and its bug-or-not collapse (kappa 10/13); the variance is also checked against a numerical
delta-method variance. The import runs on temporary files only, next to a decoy decisions.csv whose
bytes are checked to be unchanged. The page is built from a two-group synthetic campaign whose author
files carry distinctive reasons, which the page must not contain and the leak check must find once
planted.

Run line: python3 -m unittest discover -s scripts/paper/tests -p "test_rater2.py"
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from typing import Dict, List, Sequence, Tuple

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PAPER not in sys.path:
    sys.path.insert(0, PAPER)

import import_rater2 as ir  # noqa: E402
import rater2_agreement as ra  # noqa: E402
import rater2_workbook as rw  # noqa: E402

V3 = ("bug", "legitimate", "tool-artifact")


def pairs_from(table: Sequence[Sequence[int]], cats: Sequence[str]) -> List[Tuple[str, str]]:
    return [(cats[i], cats[j]) for i, row in enumerate(table) for j, n in enumerate(row) for _ in range(n)]


def delta_variance(table: Sequence[Sequence[int]], h: float = 1e-7) -> float:
    """Delta-method variance of kappa under multinomial sampling, with a numerical gradient."""
    n = sum(map(sum, table))
    k = len(table)
    p = [[x / n for x in r] for r in table]

    def kap(q: List[List[float]]) -> float:
        s = sum(map(sum, q))
        rows = [sum(q[i]) for i in range(k)]
        cols = [sum(q[i][j] for i in range(k)) for j in range(k)]
        po = sum(q[i][i] for i in range(k)) / s
        pe = sum(rows[i] * cols[i] for i in range(k)) / s ** 2
        return (po - pe) / (1 - pe)

    grad = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            up = [r[:] for r in p]
            dn = [r[:] for r in p]
            up[i][j] += h
            dn[i][j] -= h
            grad[i][j] = (kap(up) - kap(dn)) / (2 * h)
    m1 = sum(p[i][j] * grad[i][j] for i in range(k) for j in range(k))
    m2 = sum(p[i][j] * grad[i][j] ** 2 for i in range(k) for j in range(k))
    return (m2 - m1 * m1) / n


class KappaTest(unittest.TestCase):
    # 2x2, n = 50: po = 35/50 = 0.7; rows 0.5/0.5, columns 0.6/0.4; pe = 0.5*0.6 + 0.5*0.4 = 0.5; kappa = 0.4.
    # Variance (FCE 1969): sum_i p_ii (1 - (p_i. + p_.i)(0.6))^2 = 0.4*0.34^2 + 0.3*0.46^2 = 0.10972;
    # 0.36 * [0.1*(0.6+0.5)^2 + 0.2*(0.4+0.5)^2] = 0.36*0.283 = 0.10188; (0.4 - 0.5*0.6)^2 = 0.01;
    # var = (0.10972 + 0.10188 - 0.01) / (50 * 0.25) = 0.2016 / 12.5 = 0.016128.
    T2 = [[20, 5], [10, 15]]
    # 3x3, n = 30: po = 24/30; rows 10/12/8, columns 9/14/7; pe = (90 + 168 + 56)/900 = 314/900;
    # kappa = (720 - 314)/(900 - 314) = 406/586 = 203/293.
    # Bug or not: [[8, 2], [1, 19]]; po = 27/30; rows 10/20, columns 9/21; pe = (90 + 420)/900 = 510/900;
    # kappa = (810 - 510)/(900 - 510) = 300/390 = 10/13.
    T3 = [[8, 2, 0], [1, 10, 1], [0, 2, 6]]

    def test_two_by_two_by_hand(self) -> None:
        self.assertAlmostEqual(ra.cohen_kappa(self.T2), 0.4, places=12)
        self.assertAlmostEqual(ra.kappa_variance(self.T2), 0.016128, places=12)
        lo, hi = ra.asymptotic_ci(self.T2)
        se = math.sqrt(0.016128)
        self.assertAlmostEqual(lo, 0.4 - ra.Z95 * se, places=12)
        self.assertAlmostEqual(hi, 0.4 + ra.Z95 * se, places=12)
        self.assertAlmostEqual(lo, 0.15109, places=4)
        self.assertAlmostEqual(hi, 0.64891, places=4)

    def test_three_by_three_and_bug_or_not_by_hand(self) -> None:
        pairs = pairs_from(self.T3, V3)
        self.assertEqual(ra.confusion(pairs, V3), self.T3)
        s = ra.summary(pairs, V3, 0, 1)
        self.assertAlmostEqual(s["kappa"], 203 / 293, places=12)
        self.assertAlmostEqual(s["observed_agreement"], 0.8, places=12)
        self.assertAlmostEqual(s["expected_agreement"], 314 / 900, places=12)
        self.assertEqual((s["n"], s["agree"], s["percent_agreement"]), (30, 24, 80.0))
        b = ra.summary([(ra.to_binary(x), ra.to_binary(y)) for x, y in pairs], ra.BINARY, 0, 1)
        self.assertEqual(b["confusion"]["matrix"], [[8, 2], [1, 19]])
        self.assertAlmostEqual(b["kappa"], 10 / 13, places=12)

    def test_variance_matches_delta_method(self) -> None:
        for table in (self.T2, self.T3, [[30, 3, 2], [4, 40, 6], [1, 5, 9]]):
            self.assertAlmostEqual(ra.kappa_variance(table), delta_variance(table), places=8)

    def test_degenerate_tables(self) -> None:
        self.assertIsNone(ra.cohen_kappa([[5, 0], [0, 0]]))  # one category only: pe = 1
        self.assertIsNone(ra.cohen_kappa([[0, 0], [0, 0]]))
        self.assertAlmostEqual(ra.cohen_kappa([[3, 0], [0, 4]]), 1.0)
        self.assertAlmostEqual(ra.kappa_variance([[3, 0], [0, 4]]), 0.0)
        # one rater uses one category, the other two: kappa 0
        self.assertAlmostEqual(ra.cohen_kappa([[0, 0], [2, 8]]), 0.0)

    def test_bootstrap_is_reproducible_and_brackets_kappa(self) -> None:
        pairs = pairs_from(self.T3, V3)
        a = ra.bootstrap_ci(pairs, V3, 2000, 7)
        b = ra.bootstrap_ci(pairs, V3, 2000, 7)
        self.assertEqual(a, b)
        lo, hi = a["ci95"]
        self.assertLess(lo, 203 / 293)
        self.assertGreater(hi, 203 / 293)
        self.assertEqual(ra.percentile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)


class AgreementTest(unittest.TestCase):
    def test_only_groups_both_judged(self) -> None:
        author = {"g-r1-a": "bug", "g-r1-b": "legitimate", "g-r3-c": "legitimate", "g-r4-d": "tool-artifact",
                  "g-r4-e": "bug"}
        rows = [{"group": "g-r1-a", "verdict": "bug", "class": "", "note": ""},
                {"group": "g-r1-b", "verdict": "bug", "class": "", "note": "不确定"},
                {"group": "g-r3-c", "verdict": "legitimate", "class": "L4", "note": ""},
                {"group": "g-r4-d", "verdict": "", "class": "", "note": "skip"},
                {"group": "zzz", "verdict": "bug", "class": "", "note": ""}]
        rel = ra.relations(None, list(author) + ["zzz"])
        res = ra.agreement(author, rows, rel, list(author), {"g-r3-c": "L4"}, resamples=0)
        g = res["groups"]
        self.assertEqual(g["both"], 3)
        self.assertEqual(g["missing_from_rater2"], ["g-r4-d", "g-r4-e"])
        self.assertEqual(g["rater2_unknown_groups"], ["zzz"])
        self.assertEqual(g["rater2_rows_without_verdict"], ["g-r4-d"])
        t = res["three_class"]
        self.assertEqual(t["confusion"]["matrix"], [[1, 0, 0], [1, 1, 0], [0, 0, 0]])
        self.assertEqual(t["agree"], 2)
        self.assertEqual(res["by_relation"]["R1"], {"n": 2, "agree": 1, "percent_agreement": 50.0,
                                                    "kappa": 0.0, "kappa_bug": 0.0})
        self.assertEqual(res["by_relation"]["R3"]["agree"], 1)
        self.assertIsNone(res["by_relation"]["R3"]["kappa"])
        self.assertEqual((res["class_agreement"]["n"], res["class_agreement"]["agree"]), (1, 1))
        self.assertEqual(res["rater2_unsure"], {"n": 1, "groups": ["g-r1-b"], "agree": 0})
        # the author's default for unsure groups: the rater's "bug, 不确定" on g-r1-b becomes legitimate
        u = res["unsure_as_legitimate"]
        self.assertEqual(u["three_class"]["confusion"]["matrix"], [[1, 0, 0], [0, 2, 0], [0, 0, 0]])
        self.assertEqual(u["three_class"]["agree"], 3)
        self.assertEqual(u["bug_or_not"]["agree"], 3)
        self.assertEqual(res["three_class"]["agree"], 2)  # the main table keeps the rater's own pick

    def test_main_writes_json_and_md_and_leaves_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dec, r2, out = (os.path.join(tmp, n) for n in ("decisions.csv", "rater2_decisions.csv", "agree"))
            with open(dec, "w", encoding="utf-8", newline="") as f:
                f.write("group,verdict,known_issue_link,report_link,maintainer_response,date,minutes_spent\n")
                for i, row in enumerate(self_t3_author()):
                    f.write(f"g-r{i % 7}-{i},{row},,,,,\n")
            with open(r2, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(ir.FIELDS)
                for i, row in enumerate(self_t3_rater2()):
                    w.writerow([f"g-r{i % 7}-{i}", row, "", "", ""])
            before = {p: sha(p) for p in (dec, r2)}
            with redirect_stdout(io.StringIO()):
                code = ra.main(["x", "--decisions", dec, "--rater2", r2, "--out", out, "--bootstrap", "200"])
            self.assertEqual(code, 0)
            self.assertEqual(before, {p: sha(p) for p in (dec, r2)})
            with open(out + ".json", encoding="utf-8") as f:
                res = json.load(f)
            self.assertAlmostEqual(res["three_class"]["kappa"], 203 / 293, places=12)
            self.assertAlmostEqual(res["bug_or_not"]["kappa"], 10 / 13, places=12)
            self.assertEqual(sum(r["n"] for r in res["by_relation"].values()), 30)
            with open(out + ".md", encoding="utf-8") as f:
                md = f.read()
            self.assertIn("| three classes | 30 | 24 (80.0%) | 0.693 |", md)


def self_t3_author() -> List[str]:
    return [a for a, _ in pairs_from(KappaTest.T3, V3)]


def self_t3_rater2() -> List[str]:
    return [b for _, b in pairs_from(KappaTest.T3, V3)]


def sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def export(items: List[Dict[str, object]], page: str = ir.PAGE) -> str:
    return json.dumps({"page": page, "campaign": "c1", "order_seed": 5, "exported_at": "2026-11-20T10:00:00Z",
                       "items": items}, ensure_ascii=False)


class ImportTest(unittest.TestCase):
    GROUPS = ("g-r1-a", "g-r3-b", "g-r4-c")

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.csv = os.path.join(self.dir, "rater2_decisions.csv")
        self.decoy = os.path.join(self.dir, "decisions.csv")
        with open(self.decoy, "w", encoding="utf-8") as f:
            f.write("group,verdict\ng-r1-a,legitimate\n")
        self.decoy_sha = sha(self.decoy)

    def tearDown(self) -> None:
        self.assertEqual(sha(self.decoy), self.decoy_sha)
        self.tmp.cleanup()

    def rows(self) -> List[Dict[str, str]]:
        with open(self.csv, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def run_import(self, items: List[Dict[str, object]], **kw: object) -> Tuple[ir.Summary, str, bool]:
        return ir.run(ir.parse_payload(export(items)), self.csv, self.GROUPS, **kw)  # type: ignore[arg-type]

    def test_writes_columns_validates_and_sorts(self) -> None:
        summary, saved, wrote = self.run_import([
            {"n": 2, "id": "g-r3-b", "verdict": "legitimate", "class": "L4", "note": "两条路不必一致",
             "judged_at": "2026-11-20T09:00:00Z"},
            {"n": 1, "id": "g-r1-a", "verdict": "bug", "class": "L1", "note": "不确定", "judged_at": "t1"},
            {"n": 3, "id": "g-r4-c", "verdict": "tool-artifact", "class": "L2", "note": "", "judged_at": "t3"},
            {"n": 4, "id": "nope", "verdict": "bug"},
            {"n": 5, "id": "g-r4-c", "verdict": "maybe"}])
        self.assertTrue(wrote)
        self.assertEqual(saved, "")
        with open(self.csv, encoding="utf-8") as f:
            self.assertEqual(f.readline().strip(), "group,verdict,class,note,judged_at")
        self.assertEqual([(r["group"], r["verdict"], r["class"], r["note"]) for r in self.rows()],
                         [("g-r1-a", "bug", "", "不确定"), ("g-r3-b", "legitimate", "L4", "两条路不必一致"),
                          ("g-r4-c", "tool-artifact", "", "")])
        self.assertEqual(len(summary.skipped), 2)
        self.assertEqual(sum("dropped" in w for w in summary.warnings), 2)

    def test_merge_keeps_other_rows_and_backs_up(self) -> None:
        self.run_import([{"id": "g-r1-a", "verdict": "bug", "judged_at": "t1"},
                         {"id": "g-r3-b", "verdict": "legitimate", "judged_at": "t2"}])
        summary, saved, wrote = self.run_import([{"id": "g-r1-a", "verdict": "legitimate", "class": "L1",
                                                  "judged_at": "t9"}], now=dt.datetime(2026, 11, 21, 8, 0, 0))
        self.assertTrue(wrote)
        self.assertTrue(saved.endswith("rater2_decisions.csv.bak-20261121-080000"))
        with open(saved, encoding="utf-8") as f:
            self.assertIn("g-r1-a,bug,", f.read())
        self.assertEqual([(r["group"], r["verdict"], r["class"]) for r in self.rows()],
                         [("g-r1-a", "legitimate", "L1"), ("g-r3-b", "legitimate", "")])
        self.assertEqual(summary.changed_verdicts, ("#0 g-r1-a: bug -> legitimate",))
        self.assertTrue(any("keep their row" in w for w in summary.warnings))
        _, saved2, wrote2 = self.run_import([{"id": "g-r1-a", "verdict": "legitimate", "class": "L1",
                                              "judged_at": "t9"}])
        self.assertEqual((saved2, wrote2), ("", False))  # nothing changed: no rewrite, no backup

    def test_replace_writes_exactly_the_export(self) -> None:
        self.run_import([{"id": "g-r1-a", "verdict": "bug"}, {"id": "g-r3-b", "verdict": "bug"}])
        self.run_import([{"id": "g-r4-c", "verdict": "bug"}], replace=True)
        self.assertEqual([r["group"] for r in self.rows()], ["g-r4-c"])

    def test_dry_run_writes_nothing(self) -> None:
        _, saved, wrote = self.run_import([{"id": "g-r1-a", "verdict": "bug"}], dry_run=True)
        self.assertEqual((saved, wrote), ("", False))
        self.assertFalse(os.path.exists(self.csv))

    def test_refuses_decisions_csv_and_author_exports(self) -> None:
        payload = ir.parse_payload(export([{"id": "g-r1-a", "verdict": "bug"}]))
        with self.assertRaises(ValueError):
            ir.run(payload, self.decoy, self.GROUPS)
        with self.assertRaises(ValueError):
            ir.parse_payload(export([{"id": "g-r1-a", "choice": "bug"}], page="triage"))
        with self.assertRaises(ValueError):
            ir.parse_payload("no json here")
        link = os.path.join(self.dir, "other.csv")
        os.symlink(self.decoy, link)
        with self.assertRaises(ValueError):
            ir.run(payload, link, self.GROUPS)

    def test_main_on_a_file(self) -> None:
        src = os.path.join(self.dir, "rater2_judgements.json")
        with open(src, "w", encoding="utf-8") as f:
            f.write("下面是结果：\n" + export([{"id": "g-r1-a", "verdict": "bug"}]))
        triage = os.path.join(self.dir, "data", "lsptest", "runs", "c1", "triage")
        os.makedirs(triage)
        with open(os.path.join(triage, "triage.json"), "w", encoding="utf-8") as f:
            json.dump({"groups": [{"gid": g} for g in self.GROUPS]}, f)
        old = ir.REPO
        try:
            ir.REPO = self.dir
            with redirect_stdout(io.StringIO()) as out:
                code = ir.main([src, "--csv", self.csv])
        finally:
            ir.REPO = old
        self.assertEqual(code, 0, out.getvalue())
        self.assertEqual([r["group"] for r in self.rows()], ["g-r1-a"])


class PageTest(unittest.TestCase):
    """A synthetic campaign with two groups; the author files carry texts that must not reach the page."""
    REASON = "Distinctive author reason that must never appear on the rater page, number 7741."
    NOTE = "作者的备注：这一组是同一个根因，必须不出现在第二评判人的页面上。"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "c1")
        tdir = os.path.join(self.root, "triage")
        groups = []
        for gid, sig in (("srv-r1-hover-changed-h1-aaaaaa", "srv|r1_history|hover:changed"),
                         ("srv-r4-diagnostics-extra-m2-bbbbbb", "srv|r4_edits|diagnostics:extra")):
            os.makedirs(os.path.join(tdir, gid))
            groups.append({"gid": gid, "signature": sig, "family": "H1", "members": 1, "ops_before": 3, "ops_after": 1})
            with open(os.path.join(tdir, gid, "report.md"), "w", encoding="utf-8") as f:
                f.write(f"# [srv 1.0] {gid}\n\nDraft for the author (not filed). Group `{gid}`.\n\n## Server\n\n- srv 1.0\n\n"
                        "## Relation violated\n\nHistory independence (R1).\n\n## Minimal steps (LSP)\n\n1. open\n\n"
                        "## Reproduce\n\n```\npython3 scripts/lsptest/repro_violation.py x/repro.json\n```\n\n"
                        "## Evidence and reduction\n\n- confirmed 3/3\n\n"
                        "## Possibly related issues (search results, to be checked by the author)\n\n"
                        "- [org/repo#4242](https://github.com/org/repo/issues/4242) something\n\n"
                        "## Server log excerpt (last confirming replay)\n\n```\nlog line\n```\n")
            with open(os.path.join(tdir, gid, "repro.json"), "w", encoding="utf-8") as f:
                json.dump({"expected": ["a"], "actual": ["b"]}, f)
        with open(os.path.join(tdir, "triage.json"), "w", encoding="utf-8") as f:
            json.dump({"campaign": "c1", "groups": groups}, f)
        with open(os.path.join(tdir, "decisions.csv"), "w", encoding="utf-8") as f:
            f.write("group,verdict,known_issue_link,report_link,maintainer_response,date,minutes_spent\n"
                    f"{groups[0]['gid']},bug,,,{self.NOTE},2099-01-01,\n{groups[1]['gid']},tool-artifact,,,,2099-01-01,\n")
        with open(os.path.join(tdir, "verdict_reasons.csv"), "w", encoding="utf-8") as f:
            f.write(f'group,verdict,class,reason,source\n{groups[1]["gid"]},tool-artifact,A1,"{self.REASON}",x\n')
        with open(os.path.join(tdir, "decisions.csv.bak-20990101-000000"), "w", encoding="utf-8") as f:
            f.write("group,verdict\n")
        self.gids = [g["gid"] for g in groups]

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_page_has_no_author_trace_and_check_is_clean(self) -> None:
        page, order, template = rw.build_rater2("c1", self.root, seed=3)
        self.assertEqual(sorted(order), sorted(self.gids))
        self.assertEqual(order, rw.shuffled(self.gids, 3))
        for text in (self.REASON, self.NOTE, "4242", "Possibly related", "Draft for the author", "A1,"):
            self.assertNotIn(text, page)
        self.assertIn("log line", page)
        self.assertIn('"page": "triage-rater2"', page)
        self.assertIn("tse2-rater2:triage:c1", page)
        self.assertNotIn("tse2-judging", page)
        checks = rw.leak_check(page, template, self.root, order)
        self.assertEqual([c for c in checks if c["hits"]], [])

    def test_leak_check_finds_planted_traces(self) -> None:
        page, order, template = rw.build_rater2("c1", self.root, seed=3)
        planted = page.replace("</body>", f"<p>{self.REASON[:40]} C3 legitimate L4 "
                                          '<button class="choice chosen">x</button></p></body>')
        hits = {c["check"]: c["hits"] for c in rw.leak_check(planted, template, self.root, order)}
        self.assertEqual(hits["author text: verdict_reasons.csv reasons"], 1)
        self.assertEqual(hits["root-cause id C1-C11"], 1)
        self.assertEqual(hits["verdict word 'legitimate' outside the fixed page text"], 1)
        self.assertEqual(hits["class code L1-L7/A1-A4 outside the fixed page text"], 1)
        self.assertEqual(hits["pre-selected button outside the fixed page text"], 1)

    def test_shuffle_is_fixed_and_independent_of_input_order(self) -> None:
        names = [f"g{i:03d}" for i in range(50)]
        self.assertEqual(rw.shuffled(names, 11), rw.shuffled(list(reversed(names)), 11))
        self.assertNotEqual(rw.shuffled(names, 11), sorted(names))
        self.assertEqual(rw.order_overlap(names, names)["spearman"], 1.0)
        self.assertEqual(rw.order_overlap(names, list(reversed(names)))["spearman"], -1.0)

    def test_neutral_report_drops_only_the_issue_search(self) -> None:
        text = "# T\n\nDraft for the author (not filed). Group `g`.\n\n## A\n\nx\n\n## Possibly related issues (s)\n\n- y\n\n## B\n\nz\n"
        self.assertEqual(rw.neutral_report(text), "# T\n\nGroup `g`.\n\n## A\n\nx\n\n## B\n\nz\n")


if __name__ == "__main__":
    unittest.main()
