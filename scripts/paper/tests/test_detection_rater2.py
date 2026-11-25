"""Tests of the second rater's tools for the benchmark signatures: page, import and agreement.

The page is built from a synthetic campaign of three cases whose author files (detection_author.csv and the
author_match field of detection.json) carry distinctive strings that must not reach the page; the leak check
must find them once planted. The author's page is checked byte for byte against the code it had before the
evidence was shared with the rater's page (copied below as legacy_item_html and legacy_case_head). The import
runs on temporary files only, next to a decoy detection_author.csv whose bytes are checked to be unchanged. The
kappa test uses a 3x3 table worked out by hand in the comments.

Run line: python3 -m unittest discover -s scripts/paper/tests -p "test_detection_rater2.py"
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from typing import Any, Dict, List, Mapping, Sequence, Tuple

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PAPER not in sys.path:
    sys.path.insert(0, PAPER)

import detection_agreement as da  # noqa: E402
import detection_rater2 as dr  # noqa: E402
import detection_workbook as dw  # noqa: E402
import import_rater2_detection as ird  # noqa: E402
import rater2_agreement as ra  # noqa: E402

NOTE = "作者的备注 7731：这条签名对上了 issue 的复现，不能出现在第二评判人的页面上。"
MATCH = "AUTHOR-MATCH-WORD-5519"


def sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def make_campaign(base: str) -> Tuple[str, str, List[Tuple[str, str]]]:
    """(run_dir, bench_dir, [(case, signature)]) of a synthetic campaign: three detected cases, one undetected."""
    run_dir, bench_dir = os.path.join(base, "runs", "c1"), os.path.join(base, "cases")
    spec = [("srv-101", ["srv|r1_history|hover:changed", "srv|r4_edits|diagnostics:extra:X", "srv|r3_routes|a:b"]),
            ("srv-202", ["srv|r1_history|definition:lost"]),
            ("srv-303", ["srv|r4_edits|completionInsert:gained", "srv|r5_transforms|documentSymbol:changed"]),
            ("srv-404", [])]
    cases, author, keys = [], [], []
    for case, sigs in spec:
        pre_only = []
        for i, sig in enumerate(sigs):
            vid = f"{case}-v{i:02d}"
            oracle = sig.split("|")[1]
            pre_only.append({"author_match": "yes" if i % 2 == 0 else MATCH, "complete": True, "oracle": oracle,
                             "signature": sig, "vids": [vid, vid + "b"]})
            write_json(os.path.join(run_dir, "violations", vid, "repro.json"), {
                "signature": sig, "server": {"kind": "srv", "version": "1.0"}, "reproduced": "3/3",
                "note": f"tool note {vid}; flake 3/3", "context": {"timing": "settled"},
                "ops": [{"kind": "open", "path": "a.go"}, {"kind": "change", "path": "a.go", "start": [0, 0],
                                                           "end": [0, 0], "text": "x"}],
                "key": {"method": "textDocument/hover", "path": "a.go", "line": 1, "character": 2},
                "expected": {"v": [1, 2]}, "actual": {"v": [1, 3]}})
            author.append({"case": case, "title": f"title {case}", "url": f"https://example.org/{case}", "oracle": oracle,
                           "signature": sig, "vids": vid, "author_match": "partial" if i == 1 else "yes",
                           "note": NOTE if i == 0 else ""})
            keys.append((case, sig))
        cases.append({"case": case, "title": f"title {case}", "url": f"https://example.org/{case}", "kind": "srv",
                      "builds": {"pre": "1.0", "post": "1.1"}, "probe": "differs_from_fresh", "class": "R1",
                      "detected": bool(sigs), "pre_only": pre_only, "oracles": {}, "complete": True})
        write_json(os.path.join(bench_dir, case, "case.json"),
                   {"repro": {"steps": f"steps of {case}", "probe": {"type": "differs_from_fresh"}}})
    write_json(os.path.join(run_dir, "detection.json"), {"campaign": "c1", "cases": cases})
    with open(os.path.join(run_dir, "detection_author.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(author[0]))
        w.writeheader()
        w.writerows(author)
    return run_dir, bench_dir, keys


# The author's page code before evidence_html was split out (2026-11-18), kept to show the output is unchanged.
def legacy_item_html(n: int, case: Mapping[str, Any], p: Mapping[str, Any], repro: Mapping[str, Any], vid: str,
                     seed: Mapping[str, Any]) -> str:
    oracle, sig = str(p["oracle"]), str(p["signature"])
    item_id = f"{case['case']}|{oracle}|{sig}"
    server = repro.get("server") or {}
    note = str(repro.get("note") or "").split("; flake ")[0].strip()
    vids = p.get("vids") or []
    title = f'<a href="{html.escape(case["url"])}" target="_blank" rel="noopener">{html.escape(case["title"])}</a>'
    return f"""
<details class="item" id="item-{n}" data-id="{html.escape(item_id)}" data-n="{n}"><summary>{dw.summary_head(n, seed)} {html.escape(case['case'])} · {html.escape(dw.RELATION.get(oracle, oracle))} · <code>{html.escape(sig.split('|', 2)[-1])}</code></summary>
<div class="body">
<p class="muted">对照的 issue：{title}</p>
<p><b>规则</b>：{html.escape(dw.RELATION.get(oracle, oracle))}——{html.escape(dw.RULE.get(oracle, ''))}</p>
<p><b>签名</b>：<code>{html.escape(sig)}</code>（复现 {html.escape(str(repro.get('reproduced', '?')))}；这个签名共 {len(vids)} 个实例，下面是第一个）</p>
{f'<p><b>工具的说明</b>：{html.escape(note)}</p>' if note else ''}
<h4>工具在修复前版本（{html.escape(str(server.get('kind', '')))} {html.escape(str(server.get('version', '')))}）上做的操作</h4>
{dw.ops_html(repro)}
<p><b>然后查询</b>：{dw.key_text(repro.get('key') or {})}</p>
<h4>预期与实际的差别（红 = 预期，参照答案；绿 = 实际，被测答案）</h4>
<p class="muted">{html.escape(dw.EXPECTED.get(oracle, ''))}</p>
{dw.diff_html(dw.answer_diff(repro.get('expected'), repro.get('actual'), '原始记录 repro.json'))}
<p class="muted">原始记录：<a href="violations/{html.escape(vid)}/repro.json" target="_blank" rel="noopener">violations/{html.escape(vid)}/repro.json</a></p>
{dw.judge_block("detection", dw.QUESTION, seed, "备注（可选）：一句理由，或 unsure……")}
</div></details>"""


def legacy_case_head(case: Mapping[str, Any], spec: Mapping[str, Any]) -> str:
    repro = spec.get("repro") or {}
    probe = str((repro.get("probe") or {}).get("type") or case.get("probe") or "")
    builds = case.get("builds") or {}
    return (f'<section class="case" id="case-{html.escape(case["case"])}"><h2>{html.escape(case["case"])}</h2>\n'
            f'<p><a href="{html.escape(case["url"])}" target="_blank" rel="noopener">{html.escape(case["title"])}</a> '
            f'<span class="muted">（{html.escape(str(case.get("kind", "")))}，修复前 {html.escape(str(builds.get("pre", "?")))}'
            f'，修复后 {html.escape(str(builds.get("post", "?")))}；{len(case["pre_only"])} 条待核对）</span></p>\n'
            f'<p><b>基准里这个 bug 的复现步骤</b>：{html.escape(str(repro.get("steps") or "（case.json 里没有）"))}</p>\n'
            f'<p><b>基准的探针</b>：<code>{html.escape(probe)}</code>'
            + (f"（{html.escape(dw.PROBE[probe])}）" if probe in dw.PROBE else "") + "</p>\n")


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.run_dir, self.bench_dir, self.keys = make_campaign(self.tmp.name)
        with open(os.path.join(self.run_dir, "detection.json"), encoding="utf-8") as f:
            self.doc = json.load(f)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def build(self, seed: int = dr.ORDER_SEED) -> Tuple[str, List[str], str]:
        return dr.build_rater2("c1", self.run_dir, self.bench_dir, seed)


class PageTest(Base):
    def test_page_has_no_author_trace_and_check_is_clean(self) -> None:
        page, order, template = self.build()
        self.assertEqual(sorted(order), sorted(f"{c}|{s.split('|')[1]}|{s}" for c, s in self.keys))
        for text in (NOTE, NOTE[:20], MATCH, "author_match", "已判断", "待核对", "tse2-judging", "srv-404"):
            self.assertNotIn(text, page)
        self.assertNotIn("partial", dr.visible(page).replace(dr.visible(template), ""))
        self.assertNotIn('aria-pressed="true"', page)
        self.assertNotIn("chosen", page.replace(dr.SCRIPT, "").replace(dr.tw.CSS, ""))
        self.assertIn('"page": "detection-rater2"', page)
        self.assertIn(f'"seed": {dr.ORDER_SEED}', page)
        self.assertIn(str(dr.ORDER_SEED), dr.visible(page))
        self.assertIn("tool note srv-101-v00", page)
        self.assertIn("steps of srv-202", page)
        checks = dr.leak_check(page, template, self.run_dir, order, "c1", self.bench_dir, self.doc,
                               os.path.join(self.tmp.name, "none.json"))
        self.assertEqual([c for c in checks if c["hits"]], [])

    def test_leak_check_finds_planted_traces(self) -> None:
        page, order, template = self.build()
        bad = page.replace("</body>", f"<p>{NOTE} C3 已判断：yes <button class=\"choice chosen\">x</button></p></body>")
        hits = {c["check"]: c["hits"] for c in dr.leak_check(bad, template, self.run_dir, order, "c1",
                                                              self.bench_dir, self.doc)}
        self.assertEqual(hits["author text: detection_author.csv notes"], 1)
        self.assertEqual(hits["root-cause id C1-C11"], 1)
        self.assertGreaterEqual(hits["author page strings"], 1)
        self.assertEqual(hits["pre-selected button outside the fixed page text"], 1)
        self.assertEqual(hits["page changes when author_match is planted in detection.json"], 1)

    def test_page_does_not_depend_on_author_match(self) -> None:
        other, marks = dr.planted(self.doc)
        page = dr.build_rater2("c1", self.run_dir, self.bench_dir, dr.ORDER_SEED, other)[0]
        self.assertEqual(page, self.build()[0])
        self.assertFalse(any(m in page for m in marks))

    def test_order_is_fixed_by_the_seed_and_independent_of_input_order(self) -> None:
        a, b = self.build()[1], self.build()[1]
        self.assertEqual(a, b)
        cases = dr.sanitize(self.doc)
        flipped = [dict(c, pre_only=list(reversed(c["pre_only"]))) for c in reversed(cases)]
        self.assertEqual(dr.order_of(flipped), a)
        self.assertEqual(dr.order_of(cases), a)
        names = [f"case-{i:02d}" for i in range(30)]
        many = [{"case": n, "pre_only": [{"oracle": "r1_history", "signature": f"s|r1_history|{j}"} for j in range(4)]}
                for n in names]
        self.assertNotEqual([c["case"] for c, _ in dr.shuffled(many, 1)], names)
        self.assertNotEqual(dr.order_of(many, 1), dr.order_of(many, 2))
        page = self.build()[0]
        for n, key in enumerate(a, 1):
            self.assertIn(f'id="item-{n}" data-id="{html.escape(key)}" data-n="{n}"', page)
        # items of a case stay together
        runs = [k.split("|")[0] for k in a]
        self.assertEqual(len([i for i in range(len(runs)) if i == 0 or runs[i] != runs[i - 1]]), 3)

    def test_author_page_is_unchanged(self) -> None:
        new = dw.build("c1", self.run_dir, self.bench_dir)
        old_item, old_head = dw.item_html, dw.case_head
        try:
            dw.item_html, dw.case_head = legacy_item_html, legacy_case_head  # type: ignore[assignment]
            old = dw.build("c1", self.run_dir, self.bench_dir)
        finally:
            dw.item_html, dw.case_head = old_item, old_head  # type: ignore[assignment]
        self.assertEqual(new, old)
        self.assertIn(NOTE, new[0])  # the author's own page does show the author's note

    def test_overlap_report_separates_fixed_text_and_evidence(self) -> None:
        page = self.build()[0]
        author = dw.build("c1", self.run_dir, self.bench_dir)[0]
        ov = dr.overlap_report(page, author)
        self.assertEqual(ov["elsewhere"], [])
        self.assertEqual((ov["author_items_missing"], ov["rater_items_missing"]), ([], []))
        self.assertTrue(any(dw.QUESTION in f for f in ov["fixed_text"]))
        self.assertEqual(dr.common_fragments("abcdefghij" * 4, "xx" + "abcdefghij" * 3, 30), ["abcdefghij" * 4])
        self.assertEqual(dr.common_fragments("short text", "short text", 30), [])


def export(items: List[Dict[str, Any]], page: str = dr.PAGE, seed: Any = dr.ORDER_SEED) -> str:
    return json.dumps({"page": page, "campaign": "c1", "order_seed": seed, "exported_at": "2026-11-20T10:00:00Z",
                       "items": items}, ensure_ascii=False)


class ImportTest(Base):
    def setUp(self) -> None:
        super().setUp()
        self.csv = os.path.join(self.run_dir, "detection_rater2.csv")
        self.decoy = os.path.join(self.run_dir, "detection_author.csv")
        self.decoy_sha = sha(self.decoy)
        self.order = dr.order_of(dr.sanitize(self.doc))

    def tearDown(self) -> None:
        self.assertEqual(sha(self.decoy), self.decoy_sha)
        super().tearDown()

    def items(self, verdicts: Sequence[str] = ()) -> List[Dict[str, Any]]:
        out = []
        for n, key in enumerate(self.order, 1):
            case, _, sig = key.split("|", 2)
            v = verdicts[n - 1] if verdicts else ("yes", "partial", "no")[n % 3]
            out.append({"n": n, "id": key, "case": case, "signature": sig, "verdict": v, "note": f"r{n}"})
        return out

    def run_import(self, items: List[Dict[str, Any]], path: str = "", **kw: Any) -> Tuple[Dict[str, int], str, bool]:
        return ird.run(ird.parse_payload(export(items)), path or self.csv, self.doc, **kw)

    def test_writes_rows_in_detection_order(self) -> None:
        counts, saved, wrote = self.run_import(self.items())
        self.assertTrue(wrote)
        self.assertEqual(saved, "")
        with open(self.csv, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(list(rows[0]), ["case", "signature", "verdict", "note"])
        self.assertEqual([(r["case"], r["signature"]) for r in rows], self.keys)
        self.assertEqual(sum(counts.values()), len(self.keys))
        _, saved2, wrote2 = self.run_import(self.items())
        self.assertEqual((saved2, wrote2), ("", False))
        _, saved3, wrote3 = self.run_import(self.items(["no"] * len(self.keys)))
        self.assertTrue(wrote3 and saved3.startswith(self.csv + ".bak-"))

    def test_refuses_author_file_and_links(self) -> None:
        with self.assertRaises(ValueError):
            self.run_import(self.items(), self.decoy)
        link = os.path.join(self.run_dir, "other.csv")
        os.symlink(self.decoy, link)
        with self.assertRaises(ValueError):
            self.run_import(self.items(), link)
        with self.assertRaises(ValueError):
            self.run_import(self.items(), os.path.join(self.run_dir, "rater2_decisions.csv"))

    def test_refuses_missing_unknown_duplicate_and_wrong_items(self) -> None:
        items = self.items()
        for bad in (items[:-1],                                                      # one missing
                    items + [dict(items[0])],                                        # repeated
                    items + [dict(items[0], id="srv-999|r1_history|x", case="srv-999")],  # unknown
                    [dict(items[0], verdict="")] + items[1:],                        # no verdict
                    [dict(items[0], verdict="maybe")] + items[1:],
                    [dict(items[0], n=99)] + items[1:],                              # wrong number
                    [dict(items[0], signature="srv|r1_history|other")] + items[1:]):  # id and signature disagree
            with self.assertRaises(ValueError):
                self.run_import(bad)
        self.assertFalse(os.path.exists(self.csv))

    def test_refuses_other_pages_and_seeds(self) -> None:
        with self.assertRaises(ValueError):
            ird.parse_payload(export(self.items(), page="detection"))
        with self.assertRaises(ValueError):
            ird.parse_payload("no json here")
        with self.assertRaises(ValueError):
            ird.run(ird.parse_payload(export(self.items(), seed=20261117)), self.csv, self.doc)

    def test_dry_run_and_main(self) -> None:
        _, saved, wrote = self.run_import(self.items(), dry_run=True)
        self.assertEqual((saved, wrote), ("", False))
        self.assertFalse(os.path.exists(self.csv))
        src = os.path.join(self.tmp.name, "export.json")
        with open(src, "w", encoding="utf-8") as f:
            f.write("结果如下：\n" + export(self.items()))
        with redirect_stdout(io.StringIO()) as out:
            code = ird.main([src, "--csv", self.csv, "--detection", os.path.join(self.run_dir, "detection.json")])
        self.assertEqual(code, 0, out.getvalue())
        self.assertTrue(os.path.exists(self.csv))


class AgreementTest(unittest.TestCase):
    # 3x3 (rows author, columns rater 2; order yes, partial, no), n = 15:
    # po = (6 + 1 + 4)/15 = 11/15; rows 8/2/5, columns 7/2/6; pe = (56 + 4 + 30)/225 = 90/225;
    # kappa = (165 - 90)/(225 - 90) = 75/135 = 5/9.
    # Detected or not (yes vs partial + no): [[6, 2], [1, 6]]; po = 12/15; rows 8/7, columns 7/8;
    # pe = (56 + 56)/225 = 112/225; kappa = (180 - 112)/(225 - 112) = 68/113.
    T = [[6, 1, 1], [0, 1, 1], [1, 0, 4]]

    def rows(self) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Dict[Tuple[str, str], Dict[str, str]]]:
        pairs = [(da.VERDICTS[i], da.VERDICTS[j]) for i, r in enumerate(self.T) for j, n in enumerate(r) for _ in range(n)]
        author, rater2, sigs = [], [], {}
        for k, (a, b) in enumerate(pairs):
            case, sig = f"c{k // 3}", f"s|r{k % 2 + 1}_x|{k}"
            sigs[(case, sig)] = {"relation": f"R{k % 2 + 1}", "server": "srv"}
            author.append({"case": case, "signature": sig, "author_match": a, "note": ""})
            rater2.append({"case": case, "signature": sig, "verdict": b, "note": "不确定" if (a, b) == ("no", "yes") else ""})
        return author, rater2, sigs

    def test_kappa_by_hand(self) -> None:
        author, rater2, sigs = self.rows()
        res = da.agreement(author, rater2, sigs, resamples=0)
        self.assertEqual(res["three_class"]["confusion"]["matrix"], self.T)
        self.assertAlmostEqual(res["three_class"]["kappa"], 5 / 9, places=12)
        self.assertAlmostEqual(res["three_class"]["expected_agreement"], 0.4, places=12)
        self.assertEqual(res["detected_or_not"]["confusion"]["matrix"], [[6, 2], [1, 6]])
        self.assertAlmostEqual(res["detected_or_not"]["kappa"], 68 / 113, places=12)
        self.assertEqual(res["signatures"]["both"], 15)
        self.assertEqual(len(res["disagreements"]), 4)
        self.assertEqual(sum(r["n"] for r in res["by_relation"].values()), 15)
        # the one unsure signature (author no, rater yes) recoded to no: the 3x3 table becomes [[6,1,1],[0,1,1],[0,0,5]]
        self.assertEqual(res["rater2_unsure"]["n"], 1)
        self.assertEqual(res["unsure_as_no"]["three_class"]["confusion"]["matrix"], [[6, 1, 1], [0, 1, 1], [0, 0, 5]])
        self.assertEqual(res["three_class"]["agree"], 11)  # the main table keeps the rater's own pick

    def test_case_level_and_missing(self) -> None:
        sigs = {("a", "1"): {"relation": "R1", "server": "s"}, ("a", "2"): {"relation": "R1", "server": "s"},
                ("b", "3"): {"relation": "R4", "server": "s"}, ("c", "4"): {"relation": "R4", "server": "s"}}
        author = [{"case": c, "signature": s, "author_match": v} for (c, s), v in zip(sigs, ("no", "yes", "no", "yes"))]
        rater2 = [{"case": c, "signature": s, "verdict": v, "note": ""} for (c, s), v in
                  zip(list(sigs)[:3], ("yes", "partial", "no"))]
        res = da.agreement(author, rater2, sigs, resamples=0)
        self.assertEqual(res["signatures"]["missing_from_rater2"], ["c 4"])
        cases = res["cases"]
        self.assertEqual((cases["cases"], cases["judged_in_full"], cases["author_detected"], cases["rater2_detected"]),
                         (3, 2, 1, 1))
        self.assertEqual(cases["differ"], [])

    def test_without_practice_cases(self) -> None:
        sigs = {("pyright-8946", "1"): {"relation": "R1", "server": "s"}, ("pyright-8946", "2"): {"relation": "R1", "server": "s"},
                ("x", "3"): {"relation": "R4", "server": "s"}, ("y", "4"): {"relation": "R4", "server": "s"}}
        author = [{"case": c, "signature": s, "author_match": v} for (c, s), v in zip(sigs, ("yes", "yes", "no", "yes"))]
        rater2 = [{"case": c, "signature": s, "verdict": v, "note": ""} for (c, s), v in zip(sigs, ("no", "no", "no", "yes"))]
        res = da.agreement(author, rater2, sigs, resamples=0)
        w = res["without_practice_cases"]
        self.assertEqual((w["excluded_cases"], w["excluded_signatures"]), (["pyright-8946"], 2))
        self.assertEqual(w["three_class"]["n"], 2)
        self.assertEqual(w["three_class"]["agree"], 2)
        self.assertEqual(res["three_class"]["agree"], 2)  # the full table keeps all four
        self.assertEqual(w["cases"]["cases"], 2)
        self.assertIn("without practice cases", da.markdown({**res, "campaign": "c", "generated": "g",
                                                              "inputs": {"author": "a", "rater2": "r"}}))

    def test_main_writes_json_and_md_and_leaves_inputs(self) -> None:
        author, rater2, sigs = self.rows()
        with tempfile.TemporaryDirectory() as tmp:
            a, r, d, out = (os.path.join(tmp, n) for n in ("detection_author.csv", "detection_rater2.csv",
                                                           "detection.json", "agree"))
            for path, rows in ((a, author), (r, rater2)):
                with open(path, "w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
            cases: Dict[str, List[Dict[str, Any]]] = {}
            for (case, sig) in sigs:
                cases.setdefault(case, []).append({"oracle": sig.split("|")[1].replace("_x", "_history"), "signature": sig})
            write_json(d, {"cases": [{"case": c, "kind": "srv", "detected": True, "pre_only": p} for c, p in cases.items()]})
            before = {p: sha(p) for p in (a, r, d)}
            with redirect_stdout(io.StringIO()):
                code = da.main(["c1", "--author", a, "--rater2", r, "--detection", d, "--out", out, "--bootstrap", "200"])
            self.assertEqual(code, 0)
            self.assertEqual(before, {p: sha(p) for p in (a, r, d)})
            with open(out + ".json", encoding="utf-8") as f:
                res = json.load(f)
            self.assertAlmostEqual(res["three_class"]["kappa"], 5 / 9, places=12)
            self.assertIsNotNone(res["three_class"]["bootstrap"])
            with open(out + ".md", encoding="utf-8") as f:
                self.assertIn("| three classes | 15 | 11 (73.3%) | 0.556 |", f.read())
        self.assertIs(da.ra, ra)  # the statistics are rater2_agreement's


if __name__ == "__main__":
    unittest.main()
