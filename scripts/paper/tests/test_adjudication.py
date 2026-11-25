"""Tests of the adjudication page and of the import of its results into the consensus files.

Everything runs on a small synthetic repository in a temporary directory: two triage campaigns
(main_v1 with four groups, two of them disputed; main_v2 with three groups, one disputed) that share one
group name, and a benchmark with three signatures, one disputed. The raw judgement files are checked to be
byte for byte unchanged after every import.

Run line: python3 -m unittest discover -s scripts/paper/tests -p "test_adjudication.py"
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from typing import Any, Dict, List, Sequence

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PAPER not in sys.path:
    sys.path.insert(0, PAPER)

import adjudication_page as ap  # noqa: E402
import import_adjudication as ia  # noqa: E402

SHARED = "gopls-r4-diagnostics-extra-shared-m2-aaaaaa"
# main_v1: (gid, signature, author verdict, author class, rater2 verdict, rater2 class)
V1 = [("gopls-r1-codeaction-changed-h4-111111", "gopls|r1_history|codeAction:changed", "legitimate", "L1", "bug", ""),
      (SHARED, "gopls|r4_edits|diagnostics:extra", "bug", "", "tool-artifact", "A1"),
      ("ts6-r3-definition-lost-d-222222", "ts6|r3_routes|definitionConsistency:lost", "bug", "", "bug", ""),
      ("ts7-r0-crash-timeout-333333", "ts7|r0_crash|references:error", "tool-artifact", "A4", "tool-artifact", "A4")]
V2 = [(SHARED, "gopls|r4_edits|diagnostics:extra", "bug", "", "bug", ""),
      ("pyright-r3-highlight-gained-c-444444", "pyright|r3_routes|highlightVsReferences:gained", "legitimate", "L4",
       "bug", ""),
      ("rust-analyzer-r3-diagnostics-missing-a-555555", "rust-analyzer|r3_routes|diagnostics:missing", "bug", "",
       "bug", "")]
# bench_v1: (case, signature, author, rater2)
SIGS = [("gopls-1", "gopls|r1_history|codeAction:key-lost", "yes", "partial"),
        ("gopls-1", "gopls|r3_routes|highlightVsReferences:extra", "yes", "yes"),
        ("pyright-2", "pyright|r1_history|hover:changed", "no", "no")]
RAW = ("decisions.csv", "verdict_reasons.csv", "rater2_decisions.csv", "detection_author.csv", "detection_rater2.csv")


def write_csv(path: str, fields: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fields), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def make_repo(root: str) -> None:
    runs = os.path.join(root, "data", "lsptest", "runs")
    for campaign, groups in (("main_v1", V1), ("main_v2", V2)):
        tdir = os.path.join(runs, campaign, "triage")
        write_json(os.path.join(tdir, "triage.json"), {"campaign": campaign, "groups": [
            {"gid": g, "signature": s, "members": 1, "ops_before": 3, "ops_after": 1} for g, s, *_ in groups]})
        for g, s, *_ in groups:
            os.makedirs(os.path.join(tdir, g), exist_ok=True)
            with open(os.path.join(tdir, g, "report.md"), "w", encoding="utf-8") as f:
                f.write(f"# [{campaign}] report of {g}\n\n## Server\n\n- server x; project p@{campaign}\n\n"
                        "## Minimal steps (LSP)\n\n1. Start.\n2. Query `textDocument/definition`.\n\n"
                        "```json\n[1, 2]\n```\n")
        notes = {g: (f"{ac}：note of {g}" if campaign == "main_v2" and ac else f"note of {g}")
                 for g, _, _, ac, _, _ in groups}
        write_csv(os.path.join(tdir, "decisions.csv"),
                  ("group", "verdict", "known_issue_link", "report_link", "maintainer_response", "date", "minutes_spent"),
                  [{"group": g, "verdict": av, "maintainer_response": notes[g], "date": "2026-11-20"}
                   for g, _, av, _, _, _ in groups])
        if campaign == "main_v1":
            write_csv(os.path.join(tdir, "verdict_reasons.csv"), ("group", "verdict", "class", "reason", "source"),
                      [{"group": g, "verdict": av, "class": ac, "reason": f"AUTHOR-REASON {g}", "source": "test"}
                       for g, _, av, ac, _, _ in groups])
            write_csv(os.path.join(tdir, "root_causes.csv"), ("cause", "server", "trigger", "description", "group"),
                      [{"cause": "C5", "server": "gopls", "trigger": "t", "description": "CAUSE-DESC", "group": SHARED}])
        write_csv(os.path.join(tdir, "rater2_decisions.csv"), ("group", "verdict", "class", "note", "judged_at"),
                  [{"group": g, "verdict": rv, "class": rc, "note": f"RATER2-NOTE {g}"} for g, _, _, _, rv, rc in groups])
    write_json(os.path.join(runs, "main_v2", "evidence", "open_groups_ts-definition.json"), {"rows": [
        {"gid": V2[1][0], "build": ["ts7", "7.0.2"], "error": "", "target": ["a.ts", 1, 2], "reference": ["b.ts", 3, 4],
         "definition_at_target": [["x.d.ts", 5, 6, 5, 9]], "definition_at_reference": [],
         "diagnostics_on_reference_line": [{"code": "2503/ts", "message": "Cannot find namespace"}],
         "diagnostics_reference_file_codes": {"2503/ts": 1}, "hover_at_reference": "any"}]})
    bench = os.path.join(runs, "bench_v1")
    cases: Dict[str, Dict[str, Any]] = {}
    for i, (case, sig, _, _) in enumerate(SIGS):
        vid = f"run{i}-v00"
        c = cases.setdefault(case, {"case": case, "title": f"issue {case}", "url": f"https://example.org/{case}",
                                    "kind": case.split("-")[0], "builds": {"pre": "1", "post": "2"},
                                    "detected": True, "probe": "differs_from_fresh", "pre_only": []})
        c["pre_only"].append({"oracle": sig.split("|")[1], "signature": sig, "vids": [vid]})
        write_json(os.path.join(bench, "violations", vid, "repro.json"), {
            "signature": sig, "server": {"kind": "k", "version": "1"}, "note": "tool note", "reproduced": "2/2",
            "ops": [], "key": {"method": "m", "path": "f", "line": 0, "character": 0},
            "expected": ["a"], "actual": ["b"]})
        write_json(os.path.join(root, "data", "lsp_bench", "cases", case, "case.json"),
                   {"repro": {"steps": "steps", "probe": {"type": "differs_from_fresh"}}})
    write_json(os.path.join(bench, "detection.json"), {"cases": list(cases.values())})
    write_csv(os.path.join(bench, "detection_author.csv"),
              ("case", "title", "url", "oracle", "signature", "vids", "author_match", "note"),
              [{"case": c, "oracle": s.split("|")[1], "signature": s, "author_match": a, "note": ""} for c, s, a, _ in SIGS])
    write_csv(os.path.join(bench, "detection_rater2.csv"), ("case", "signature", "verdict", "note"),
              [{"case": c, "signature": s, "verdict": r, "note": ""} for c, s, _, r in SIGS])


def item(kind: str, campaign: str, id_: str, verdict: str, followed: str, cls: str = "", unresolved: bool = False,
         reason: str = "agreed after replay") -> Dict[str, Any]:
    return {"n": 1, "kind": kind, "campaign": campaign, "id": id_, "verdict": verdict, "class": cls,
            "followed": followed, "unresolved": unresolved, "reason": reason, "decided_at": "2026-11-21T08:00:00Z"}


def export(items: List[Dict[str, Any]]) -> str:
    return json.dumps({"page": "adjudication", "generated_at": "2026-11-21T09:00:00Z", "items": items})


def full() -> List[Dict[str, Any]]:
    return [item("group", "main_v1", V1[0][0], "bug", "rater2"),
            item("group", "main_v1", SHARED, "bug", "author"),
            item("group", "main_v2", V2[1][0], "legitimate", "author", cls="L4"),
            item("signature", "bench_v1", f"{SIGS[0][0]}|{SIGS[0][1]}", "yes", "author")]


class AdjudicationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        make_repo(self.root)
        self.runs = os.path.join(self.root, "data", "lsptest", "runs")
        self.raw = self.raw_hashes()

    def tearDown(self) -> None:
        self.assertEqual(self.raw_hashes(), self.raw, "a raw judgement file changed")
        self.tmp.cleanup()

    def raw_hashes(self) -> Dict[str, str]:
        out = {}
        for dirpath, _, files in os.walk(self.runs):
            for name in files:
                if name in RAW:
                    with open(os.path.join(dirpath, name), "rb") as f:
                        out[os.path.join(dirpath, name)] = hashlib.sha256(f.read()).hexdigest()
        return out

    def read(self, rel: str) -> List[Dict[str, str]]:
        with open(os.path.join(self.runs, rel), encoding="utf-8") as f:
            return list(csv.DictReader(f))

    # ------------------------------------------------------------ page
    def test_page_lists_only_disputed_items(self) -> None:
        page, disputes, _ = ap.build(self.root)
        keys = re.findall(r'data-key="([^"]+)"', page)
        self.assertEqual(keys, [f"group:main_v1:{V1[0][0]}", f"group:main_v1:{SHARED}", f"group:main_v2:{V2[1][0]}",
                                f"signature:bench_v1:{SIGS[0][0]}|{SIGS[0][1]}"])
        self.assertEqual([d.key for d in disputes], keys)
        for agreed in (V1[2][0], V1[3][0], V2[2][0]):
            self.assertNotIn(agreed, page)
        self.assertNotIn('data-key="signature:bench_v1:gopls-1|gopls|r3_routes', page)
        self.assertNotIn('class="choice chosen"', page)
        self.assertIn("AUTHOR-REASON", page)
        self.assertIn("RATER2-NOTE", page)
        self.assertIn("CAUSE-DESC", page)
        self.assertIn("<h3>[main_v1] report of", page)  # markdown rendered
        self.assertIn("跳定义", page)  # the main_v2 evidence summary
        self.assertIn(ap.rw.CRITERIA_EN.split(",")[0], page)

    def test_main_v2_class_from_note_prefix(self) -> None:
        d = [x for x in ap.triage_disputes("main_v2", self.root)]
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0].author.cls, "L4")

    def test_cross_batch_hint(self) -> None:
        page, _, hints = ap.build(self.root)
        self.assertEqual(list(hints), [f"group:main_v1:{SHARED}"])
        hint = hints[f"group:main_v1:{SHARED}"][0]
        self.assertEqual(hint["campaign"], "main_v2")
        self.assertEqual((hint["author"].verdict, hint["rater2"].verdict), ("bug", "bug"))
        self.assertIn("第二批（main_v2）也有同名的组", page)
        self.assertIn("那一组两人判得一样", page)

    def test_main_writes_page(self) -> None:
        with redirect_stdout(io.StringIO()):
            self.assertEqual(ap.main(["--repo", self.root]), 0)
        self.assertTrue(os.path.exists(ap.out_path(self.root)))

    # ------------------------------------------------------------ import
    def test_import_writes_three_consensus_files(self) -> None:
        _, done, keep = ia.run(export(full()), self.root)
        self.assertEqual(len(keep), 4)
        v1 = self.read("main_v1/triage/consensus.csv")
        self.assertEqual([(r["group"], r["verdict"], r["followed"], r["unresolved"], r["date"]) for r in v1],
                         [(V1[0][0], "bug", "rater2", "no", "2026-11-21"), (SHARED, "bug", "author", "no", "2026-11-21")])
        v2 = self.read("main_v2/triage/consensus.csv")
        self.assertEqual([(r["group"], r["verdict"], r["class"]) for r in v2], [(V2[1][0], "legitimate", "L4")])
        bench = self.read("bench_v1/detection_consensus.csv")
        self.assertEqual(list(bench[0]), list(ia.SIGNATURE_FIELDS))
        self.assertEqual((bench[0]["case"], bench[0]["signature"], bench[0]["verdict"]), (SIGS[0][0], SIGS[0][1], "yes"))
        # a second import that changes one row backs the file up
        items = full()
        items[0] = item("group", "main_v1", V1[0][0], "legitimate", "author", cls="L1")
        _, done, _ = ia.run(export(items), self.root)
        backups = [b for p, b, w in done if w]
        self.assertEqual(len(backups), 1)
        self.assertIn(".bak-", backups[0])

    def test_dry_run_writes_nothing(self) -> None:
        ia.run(export(full()), self.root, dry_run=True)
        self.assertFalse(os.path.exists(os.path.join(self.runs, "main_v1", "triage", "consensus.csv")))

    def test_refuses_raw_judgement_files(self) -> None:
        for name in ia.PROTECTED:
            with self.assertRaises(ValueError):
                ia.guard(os.path.join(self.runs, "main_v1", "triage", name))
        link = os.path.join(self.runs, "main_v1", "triage", "consensus.csv")
        os.symlink(os.path.join(self.runs, "main_v1", "triage", "decisions.csv"), link)
        with self.assertRaises(ValueError):
            ia.run(export(full()), self.root)
        with self.assertRaises(ValueError):
            ia.write({link: "group\n"})

    def test_refuses_item_not_in_dispute(self) -> None:
        items = full() + [item("group", "main_v1", V1[2][0], "bug", "author")]
        with self.assertRaisesRegex(ValueError, "not an item the two judged differently"):
            ia.run(export(items), self.root)
        items = full() + [item("signature", "bench_v1", f"{SIGS[1][0]}|{SIGS[1][1]}", "yes", "author")]
        with self.assertRaisesRegex(ValueError, "not an item"):
            ia.run(export(items), self.root)

    def test_unresolved_rule(self) -> None:
        items = full()
        items[0] = item("group", "main_v1", V1[0][0], "bug", "rater2", unresolved=True)
        with self.assertRaisesRegex(ValueError, "unresolved"):
            ia.run(export(items), self.root)
        items = full()
        items[3] = item("signature", "bench_v1", f"{SIGS[0][0]}|{SIGS[0][1]}", "partial", "rater2", unresolved=True)
        with self.assertRaisesRegex(ValueError, "unresolved"):
            ia.run(export(items), self.root)
        items = full()
        items[0] = item("group", "main_v1", V1[0][0], "legitimate", "", unresolved=True)
        items[3] = item("signature", "bench_v1", f"{SIGS[0][0]}|{SIGS[0][1]}", "no", "", unresolved=True)
        ia.run(export(items), self.root)
        self.assertEqual(self.read("main_v1/triage/consensus.csv")[0]["unresolved"], "yes")
        self.assertEqual(self.read("bench_v1/detection_consensus.csv")[0]["verdict"], "no")

    def test_followed_and_verdict_checks(self) -> None:
        for bad in (item("group", "main_v1", V1[0][0], "bug", "author"),      # author said legitimate
                    item("group", "main_v1", V1[0][0], "bug", "both"),
                    item("group", "main_v1", V1[0][0], "bug", ""),
                    item("group", "main_v1", V1[0][0], "bug", "rater2", cls="L1"),
                    item("group", "main_v1", V1[0][0], "maybe", "rater2"),
                    item("group", "main_v1", V1[0][0], "bug", "rater2", reason="")):
            items = full()
            items[0] = bad
            with self.assertRaises(ValueError):
                ia.run(export(items), self.root)
        items = full()
        items[0] = item("group", "main_v1", V1[0][0], "tool-artifact", "both", cls="A2")
        ia.run(export(items), self.root)

    def test_partial(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing"):
            ia.run(export(full()[:2]), self.root)
        undecided = item("group", "main_v2", V2[1][0], "", "author")
        with self.assertRaisesRegex(ValueError, "no verdict"):
            ia.run(export(full()[:2] + [undecided]), self.root)
        ia.run(export(full()[:2] + [undecided]), self.root, partial=True)
        self.assertEqual(len(self.read("main_v1/triage/consensus.csv")), 2)
        self.assertFalse(os.path.exists(os.path.join(self.runs, "main_v2", "triage", "consensus.csv")))
        ia.run(export(full()[2:3]), self.root, partial=True)  # merges, keeps the main_v1 rows
        self.assertEqual(len(self.read("main_v1/triage/consensus.csv")), 2)
        self.assertEqual(len(self.read("main_v2/triage/consensus.csv")), 1)

    def test_rejects_other_pages(self) -> None:
        with self.assertRaises(ValueError):
            ia.parse_payload(json.dumps({"page": "triage-rater2", "items": []}))
        with redirect_stdout(io.StringIO()):
            path = os.path.join(self.root, "x.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write(export(full()))
            self.assertEqual(ia.main([path, "--repo", self.root, "--dry-run"]), 0)


if __name__ == "__main__":
    unittest.main()
