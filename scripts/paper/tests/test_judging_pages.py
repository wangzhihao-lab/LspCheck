"""Tests of the two judging pages and of the import of their exported results.

The import runs on temporary copies of data/lsptest/runs/main_v1/triage/decisions.csv and
data/lsptest/runs/bench_v1/detection_author.csv with the judgement cells emptied; the real files
are only read, and their bytes are checked to be unchanged after every test. The pages are built
in memory from the real campaign data with such copies: once with no judgement, once with one row
judged. The JSON format is checked through the parser and against the page script's export code.

Run line: python3 -m unittest scripts/paper/tests/test_judging_pages.py
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from typing import Any, Dict, List, Mapping, Optional, Tuple

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PAPER not in sys.path:
    sys.path.insert(0, PAPER)

import detection_workbook  # noqa: E402
import import_judgements as ij  # noqa: E402
import triage_workbook  # noqa: E402

RUNS = os.path.join(ij.REPO, "data", "lsptest", "runs")
DECISIONS = os.path.join(RUNS, "main_v1", "triage", "decisions.csv")
AUTHOR = os.path.join(RUNS, "bench_v1", "detection_author.csv")
JUDGED = {DECISIONS: ("verdict", "maintainer_response", "date", "minutes_spent"), AUTHOR: ("author_match", "note")}
NOW = dt.datetime(2026, 9, 26, 10, 30, 0)
ITEM_RE = re.compile(r'<details class="item" id="[^"]*" data-id="([^"]*)" data-n="(\d+)"><summary>'
                     r'<b class="num">(\d+)\.</b>(.*?)</details>', re.S)
BUTTON_RE = re.compile(r'<button type="button" class="choice( chosen)?" data-choice="([^"]+)" '
                       r'aria-pressed="(true|false)">')


def sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def blank_copy(src: str, dest_dir: str,
               fill: Optional[Mapping[int, Mapping[str, str]]] = None) -> Tuple[str, List[Dict[str, str]]]:
    """Copy of src in dest_dir with the judgement cells emptied, then the cells of fill (row index -> values) set."""
    with open(src, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = list(reader.fieldnames or []), list(reader)
    for i, r in enumerate(rows):
        r.update({c: "" for c in JUDGED[src]})
        r.update((fill or {}).get(i, {}))
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))
    with open(dest, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return dest, rows


def read_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def payload(page: str, campaign: str, items: List[Dict[str, Any]]) -> ij.Payload:
    return ij.parse_payload(json.dumps({"page": page, "campaign": campaign, "exported_at": "2026-09-26T02:30:00.000Z",
                                        "items": items}, ensure_ascii=False))


def page_items(page: str) -> List[Tuple[str, int, int, str]]:
    """(data-id, data-n, number at the start of the summary, rest of the item) in page order."""
    return [(html.unescape(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)) for m in ITEM_RE.finditer(page)]


def page_config(page: str) -> Dict[str, Any]:
    m = re.search(r'<script type="application/json" id="judge-config">(.*?)</script>', page, re.S)
    assert m is not None
    return json.loads(m.group(1))


def item_id(row: Mapping[str, str]) -> str:
    return f"{row['case']}|{row['oracle']}|{row['signature']}"


class RealFilesUntouched(unittest.TestCase):
    real: Dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.real = {p: sha(p) for p in JUDGED}

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="judging-test-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)
        for path, digest in self.real.items():
            self.assertEqual(sha(path), digest, f"{path} was changed by a test")


class ImportTest(RealFilesUntouched):
    def test_triage_item_fills_its_row(self) -> None:
        path, rows = blank_copy(DECISIONS, self.tmp)
        with open(path, "rb") as f:
            original = f.read()
        gid = rows[3]["group"]
        summary, saved = ij.run(payload("triage", "main_v1", [{"n": 4, "id": gid, "choice": "bug", "note": "wrong type",
                                                               "minutes": 7}]), path, now=NOW)
        self.assertEqual((summary.updated, summary.unchanged, summary.skipped), ((f"#4 {gid}",), (), ()))
        after = read_rows(path)
        self.assertEqual({k: after[3][k] for k in JUDGED[DECISIONS]},
                         {"verdict": "bug", "maintainer_response": "wrong type", "date": "2026-09-26", "minutes_spent": "7"})
        self.assertEqual(after[:3] + after[4:], rows[:3] + rows[4:])
        self.assertEqual(os.path.basename(saved), "decisions.csv.bak-20260926-103000")
        with open(saved, "rb") as f:
            self.assertEqual(f.read(), original)

    def test_detection_item_fills_its_row(self) -> None:
        path, rows = blank_copy(AUTHOR, self.tmp)
        summary, saved = ij.run(payload("detection", "bench_v1", [{"n": 11, "id": item_id(rows[10]), "choice": "partial",
                                                                   "note": "only half of it", "minutes": 3}]), path, now=NOW)
        self.assertEqual(len(summary.updated), 1)
        after = read_rows(path)
        self.assertEqual(after[10], {**rows[10], "author_match": "partial", "note": "only half of it"})
        self.assertEqual(after[:10] + after[11:], rows[:10] + rows[11:])
        self.assertTrue(saved.endswith("detection_author.csv.bak-20260926-103000"))

    def test_unknown_ids_and_invalid_choices_are_skipped(self) -> None:
        path, rows = blank_copy(DECISIONS, self.tmp)
        before = sha(path)
        summary, saved = ij.run(payload("triage", "main_v1", [
            {"n": 1, "id": "no-such-group", "choice": "bug", "note": "", "minutes": 1},
            {"n": 2, "id": rows[0]["group"], "choice": "maybe", "note": "", "minutes": 1},
            {"n": 3, "choice": "bug"}]), path, now=NOW)
        self.assertEqual((len(summary.updated), len(summary.unchanged), len(summary.skipped)), (0, 0, 3))
        self.assertIn("#1 no-such-group: unknown id", summary.skipped)
        self.assertEqual((sha(path), saved), (before, ""))
        path, rows = blank_copy(AUTHOR, self.tmp)
        partial_id = f"{rows[0]['case']}|{rows[0]['oracle']}"
        summary, _ = ij.run(payload("detection", "bench_v1", [{"n": 1, "id": partial_id, "choice": "yes"}]), path, now=NOW)
        self.assertEqual(summary.skipped, (f"#1 {partial_id}: unknown id",))

    def test_dry_run_writes_nothing(self) -> None:
        path, rows = blank_copy(DECISIONS, self.tmp)
        before = sha(path)
        summary, saved = ij.run(payload("triage", "main_v1", [{"n": 1, "id": rows[0]["group"], "choice": "legitimate"}]),
                                path, dry_run=True, now=NOW)
        self.assertEqual((len(summary.updated), saved, sha(path)), (1, "", before))
        self.assertEqual(os.listdir(self.tmp), ["decisions.csv"])

    def test_second_import_is_unchanged(self) -> None:
        path, rows = blank_copy(DECISIONS, self.tmp)
        p = payload("triage", "main_v1", [{"n": 9, "id": rows[8]["group"], "choice": "tool-artifact", "minutes": 12}])
        ij.run(p, path, now=NOW)
        summary, saved = ij.run(p, path, now=NOW + dt.timedelta(hours=1))
        self.assertEqual((summary.updated, len(summary.unchanged), saved), ((), 1, ""))
        self.assertEqual(sorted(os.listdir(self.tmp)), ["decisions.csv", "decisions.csv.bak-20260926-103000"])

    def test_date_only_on_new_choice_and_first_minutes_kept(self) -> None:
        path, rows = blank_copy(DECISIONS, self.tmp, {0: {"verdict": "bug", "date": "2026-01-02", "minutes_spent": "5"}})
        gid = rows[0]["group"]
        ij.run(payload("triage", "main_v1", [{"n": 1, "id": gid, "choice": "bug", "note": "x", "minutes": 9}]), path, now=NOW)
        self.assertEqual({k: read_rows(path)[0][k] for k in JUDGED[DECISIONS]},
                         {"verdict": "bug", "maintainer_response": "x", "date": "2026-01-02", "minutes_spent": "5"})
        summary, _ = ij.run(payload("triage", "main_v1", [{"n": 1, "id": gid, "choice": "legitimate", "minutes": 9}]),
                            path, now=NOW)
        self.assertEqual({k: read_rows(path)[0][k] for k in JUDGED[DECISIONS]},
                         {"verdict": "legitimate", "maintainer_response": "x", "date": "2026-09-26", "minutes_spent": "5"})
        self.assertEqual(summary.replaced, (f"#1 {gid}: bug -> legitimate",))

    def test_empty_choice_or_note_keeps_cells(self) -> None:
        path, rows = blank_copy(DECISIONS, self.tmp, {0: {"verdict": "bug", "maintainer_response": "keep me"}})
        summary, _ = ij.run(payload("triage", "main_v1", [{"n": 1, "id": rows[0]["group"], "choice": "bug", "note": ""},
                                                          {"n": 2, "id": rows[1]["group"], "note": "just a note"}]),
                            path, now=NOW)
        after = read_rows(path)
        self.assertEqual((after[0]["verdict"], after[0]["maintainer_response"]), ("bug", "keep me"))
        self.assertEqual({k: after[1][k] for k in JUDGED[DECISIONS]},
                         {"verdict": "", "maintainer_response": "just a note", "date": "", "minutes_spent": ""})
        self.assertEqual((len(summary.updated), len(summary.unchanged)), (1, 1))

    def test_csv_layout_is_kept(self) -> None:
        for name, newline in (("crlf", "\r\n"), ("lf", "\n")):
            path, rows = blank_copy(AUTHOR, os.path.join(self.tmp, name))
            with open(path, "r", encoding="utf-8", newline="") as f:
                text = f.read()
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text.replace("\r\n", newline))
            ij.run(payload("detection", "bench_v1", [{"n": 5, "id": item_id(rows[4]), "choice": "no"}]), path, now=NOW)
            with open(path, "r", encoding="utf-8", newline="") as f:
                new_text = f.read()
            self.assertEqual(new_text.splitlines()[0], text.splitlines()[0])
            self.assertEqual(new_text.count(newline), len(rows) + 1)
            if newline == "\n":
                self.assertNotIn("\r", new_text)
            after = read_rows(path)
            self.assertEqual([item_id(r) for r in after], [item_id(r) for r in rows])
            self.assertEqual([r["vids"] for r in after], [r["vids"] for r in rows])

    def test_command_line(self) -> None:
        path, rows = blank_copy(DECISIONS, self.tmp)
        source = os.path.join(self.tmp, "pasted.txt")
        export = {"page": "triage", "campaign": "main_v1", "exported_at": "2026-09-26T02:30:00.000Z",
                  "items": [{"n": 1, "id": rows[0]["group"], "choice": "bug", "note": "", "minutes": 2}]}
        with open(source, "w", encoding="utf-8") as f:
            f.write("结果如下：\n```json\n" + json.dumps(export) + "\n```\n")
        for extra, updated in ((["--dry-run"], ""), ([], "bug")):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(ij.main([source, "--csv", path, *extra]), 0)
            self.assertIn("updated 1, unchanged 0, skipped 0", out.getvalue())
            self.assertEqual(read_rows(path)[0]["verdict"], updated)
        with open(source, "w", encoding="utf-8") as f:
            f.write('{"page": "triage", "items": [')
        with self.assertLogs(ij.logger, "ERROR"):
            self.assertEqual(ij.main([source, "--csv", path]), 2)


class FormatTest(unittest.TestCase):
    def test_parse_a_pasted_export(self) -> None:
        text = ('这是结果：\n```json\n{"page":"detection","campaign":"bench_v1","exported_at":"2026-09-26T01:02:03.000Z",'
                '"items":[\n  {"n":3,"id":"gopls-36824|r4_edits|gopls|r4_edits|organizeImports:gained","choice":"yes",'
                '"note":" same bug ","minutes":2}\n]}\n```')
        p = ij.parse_payload(text)
        self.assertEqual((p.page, p.campaign, p.exported_at), ("detection", "bench_v1", "2026-09-26T01:02:03.000Z"))
        self.assertEqual(p.items, (ij.Item(3, "gopls-36824|r4_edits|gopls|r4_edits|organizeImports:gained", "yes",
                                           "same bug", 2),))
        self.assertEqual(ij.row_key("detection", p.items[0].id),
                         ("gopls-36824", "r4_edits", "gopls|r4_edits|organizeImports:gained"))
        self.assertEqual(ij.target_csv(p), AUTHOR)

    def test_parse_rejects_what_is_not_an_export(self) -> None:
        for bad in ("", "no json here", "[1, 2]", '{"page": "other", "campaign": "x", "items": []}',
                    '{"page": "triage", "campaign": "../main_v1", "items": []}',
                    '{"page": "triage", "campaign": "main_v1", "items": {}}', '{"page": "triage", "items": [}'):
            with self.assertRaises(ValueError, msg=bad):
                ij.parse_payload(bad)

    def test_labels_match_choices(self) -> None:
        for page, choices in ij.CHOICES.items():
            self.assertEqual(tuple(triage_workbook.LABELS[page]), choices)

    def test_script_exports_the_documented_format(self) -> None:
        script = triage_workbook.SCRIPT
        for piece in ("page: cfg.page", "campaign: cfg.campaign", "exported_at: new Date().toISOString()",
                      ',"items":[', 'n: Number(item.getAttribute("data-n"))', "id: idOf(item)", "choice: s.choice",
                      "note: note", "minutes: s.minutes", "if (s.choice || note)", "navigator.clipboard.writeText",
                      'document.execCommand("copy")', "window.localStorage.getItem(cfg.key)",
                      "Math.min(1800, (now - lastMark) / 1000)", "if (!s.minutes)", "lastMark = now"):
            self.assertIn(piece, script)
        head = json.dumps({"page": "triage", "campaign": "main_v1", "exported_at": "2026-09-26T02:30:00.000Z"})
        for body in ("", '  {"n": 1, "id": "g", "choice": "bug", "note": "", "minutes": 1}'):
            self.assertIsInstance(ij.parse_payload(head[:-1] + ',"items":[\n' + body + "\n]}\n"), ij.Payload)


class PagesTest(unittest.TestCase):
    pages: Dict[str, Tuple[str, int, int]]
    judged: Dict[str, Tuple[str, str]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.real = {p: sha(p) for p in JUDGED}
        cls.tmp = tempfile.mkdtemp(prefix="judging-pages-")
        decisions, rows = blank_copy(DECISIONS, os.path.join(cls.tmp, "blank"))
        author, arows = blank_copy(AUTHOR, os.path.join(cls.tmp, "blank"))
        decisions_one, _ = blank_copy(DECISIONS, os.path.join(cls.tmp, "one"), {
            5: {"verdict": "legitimate", "maintainer_response": "both fine", "minutes_spent": "4"}})
        author_one, _ = blank_copy(AUTHOR, os.path.join(cls.tmp, "one"), {20: {"author_match": "no", "note": "other bug"}})
        cls.judged = {"triage": (rows[5]["group"], "legitimate"), "detection": (item_id(arows[20]), "no")}
        cls.pages = {"triage": triage_workbook.build("main_v1", decisions=decisions),
                     "detection": detection_workbook.build("bench_v1", author_csv=author),
                     "triage_one": triage_workbook.build("main_v1", decisions=decisions_one),
                     "detection_one": detection_workbook.build("bench_v1", author_csv=author_one)}
        cls.detection_ids = [item_id(r) for r in arows]

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_real_files_untouched(self) -> None:
        self.assertEqual({p: sha(p) for p in JUDGED}, self.real)

    def test_items_are_numbered_and_have_buttons(self) -> None:
        for kind, expect in (("triage", 106), ("detection", 77)):
            page, n, judged = self.pages[kind]
            items = page_items(page)
            self.assertEqual((n, judged, len(items)), (expect, 0, expect))
            self.assertEqual([x[1] for x in items], list(range(1, expect + 1)))
            self.assertEqual([x[2] for x in items], list(range(1, expect + 1)))
            self.assertEqual(len({x[0] for x in items}), expect)
            for _, _, _, rest in items:
                self.assertEqual([b[1] for b in BUTTON_RE.findall(rest)], list(ij.CHOICES[kind]))
                self.assertIn('<button type="button" class="clear">清除</button>', rest)
                self.assertIn('<textarea class="note"', rest)
            for piece in ('id="copy">复制结果', 'id="download">下载结果文件', f"已判断 0 / {expect}", "做完一批就点「复制结果」"):
                self.assertIn(piece, page)

    def test_nothing_preselected_when_csv_empty(self) -> None:
        for kind in ("triage", "detection"):
            page = self.pages[kind][0]
            self.assertNotIn('aria-pressed="true"', page)
            self.assertNotIn("choice chosen", page)
            self.assertNotIn('class="state judged"', page)
            self.assertEqual(page_config(page)["seed"], {})

    def test_item_with_a_csv_value_is_prejudged(self) -> None:
        notes = {"triage": ("both fine", 4), "detection": ("other bug", 0)}
        for kind in ("triage", "detection"):
            page, n, judged = self.pages[f"{kind}_one"]
            key, choice = self.judged[kind]
            self.assertEqual((judged, page.count('aria-pressed="true"'), page.count("choice chosen")), (1, 1, 1))
            [rest] = [x[3] for x in page_items(page) if x[0] == key]
            self.assertIn(f'class="state judged">已判断：{choice}</span>', rest)
            self.assertEqual([b[1] for b in BUTTON_RE.findall(rest) if b[2] == "true"], [choice])
            self.assertIn(f">{notes[kind][0]}</textarea>", rest)
            self.assertEqual(page_config(page)["seed"], {key: {"choice": choice, "note": notes[kind][0],
                                                               "minutes": notes[kind][1], "file": choice}})
            self.assertIn(f"已判断 1 / {n}", page)

    def test_config(self) -> None:
        for kind, campaign in (("triage", "main_v1"), ("detection", "bench_v1")):
            cfg = page_config(self.pages[kind][0])
            self.assertEqual((cfg["page"], cfg["campaign"], cfg["choices"], cfg["key"]),
                             (kind, campaign, list(ij.CHOICES[kind]), f"tse2-judging:{kind}:{campaign}"))

    def test_triage_order(self) -> None:
        groups = {g["gid"]: g for g in triage_workbook.load(os.path.join(RUNS, "main_v1", "triage", "triage.json"))["groups"]}
        oracles = [groups[x[0]]["signature"].split("|")[1] for x in page_items(self.pages["triage"][0])]
        ranks = [triage_workbook.ORDER.index(o) for o in oracles]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(sorted(set(oracles), key=triage_workbook.ORDER.index)[0], "r0_crash")

    def test_detection_items_follow_the_csv(self) -> None:
        page = self.pages["detection"][0]
        self.assertEqual([x[0] for x in page_items(page)], self.detection_ids)
        self.assertEqual(page.count('<section class="case"'), 39)

    def test_pages_work_offline(self) -> None:
        self.assertIsNone(re.search(r"@import|url\(|https?:", triage_workbook.CSS + triage_workbook.SCRIPT))
        for kind in ("triage", "detection"):
            self.assertIsNone(re.search(r"<script[^>]*\bsrc=|<link\b|<iframe\b|<img\b", self.pages[kind][0]))


if __name__ == "__main__":
    unittest.main()
