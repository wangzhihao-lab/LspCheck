"""Unit tests for triage: grouping and case families, the representative, group ids, line
blanking and pinned lines, line-level ddmin with a fake oracle, issue queries, merging and the
cached search (no token written), report rendering and the decisions template.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Sequence
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import Op, QueryKey, Violation  # noqa: E402
from oracles.base import OracleContext, ReplayOutcome, make_violation  # noqa: E402
from ops import write_text  # noqa: E402
from triage_group import case_family, confirmed_rows, group_id, group_rows, representative  # noqa: E402
from triage_issues import GitHubSearch, build_queries, error_phrase, merge, search_group, symptom_words  # noqa: E402
from triage_reduce import LineConfig, blank_lines, line_texts, pinned_lines, reduce_lines, touched_files  # noqa: E402
from triage_report import DECISION_COLUMNS, render_index, render_report, steps, symptom, title, write_decisions  # noqa: E402


def row(vid: str, sig: str, method: str, case: Dict[str, Any], n_ops: int = 3, **kw: Any) -> Dict[str, Any]:
    oracle = sig.split("|")[1]
    return dict({"vid": vid, "run_id": vid.split("-")[0], "oracle": oracle, "signature": sig, "key": {"method": method},
                 "case": case, "n_ops": n_ops, "confirmed": True, "incomplete": False, "project": "p@1",
                 "server": "pyright-1", "timing": "settled", "seed": 1, "repro": f"x/{vid}/repro.json"}, **kw)


class GroupTests(unittest.TestCase):
    def test_families(self) -> None:
        self.assertEqual(case_family("r1_history", {"family": "H3"}), "H3")
        self.assertEqual(case_family("r4_edits", {"kind": "mutation", "mutation": {"id": "M2"}}), "mutation:M2")
        self.assertEqual(case_family("r4_edits", {"kind": "quickfix"}), "quickfix")
        self.assertEqual(case_family("r5_transforms", {"transform": {"kind": "T4"}}), "T4")
        self.assertEqual(case_family("r0_crash", {}), "fresh-pair")
        self.assertEqual(case_family("r9_new", {"sub": "z"}), "z")

    def test_grouping_representative_and_filters(self) -> None:
        sig = "pyright|r1_history|hover:text"
        rows = [row("a-v00", sig, "hover", {"family": "H1"}, 5), row("b-v00", sig, "hover", {"family": "H1"}, 2),
                row("c-v00", sig, "hover", {"family": "H2"}, 1),
                row("d-v00", sig, "hover", {"family": "H1"}, 1, confirmed=False),
                row("e-v00", sig, "hover", {"family": "H1"}, 1, incomplete=True),
                row("f-v00", sig, "hover", {"family": "H1"}, 1, confirmed=False),
                row("f-v00", sig, "hover", {"family": "H1"}, 4)]  # a rerun confirmed it: last row wins
        self.assertEqual(sorted(r["vid"] for r in confirmed_rows(rows)), ["a-v00", "b-v00", "c-v00", "f-v00"])
        groups = group_rows(rows)
        self.assertEqual([(g.family, len(g.members)) for g in groups], [("H1", 3), ("H2", 1)])
        self.assertEqual(groups[0].representative["vid"], "b-v00")
        self.assertEqual(representative([{"vid": "z", "n_ops": 1}, {"vid": "y", "n_ops": 1}])["vid"], "y")
        self.assertEqual((groups[0].server_kind, groups[0].oracle, groups[0].shape), ("pyright", "r1_history", "hover:text"))
        self.assertEqual(groups[0].summary()["members"], 3)

    def test_group_ids_stable_and_distinct(self) -> None:
        a = group_id("pyright|r1_history|typeDefinition:result->error:-32603", "typeDefinition", "H3")
        self.assertEqual(a, group_id("pyright|r1_history|typeDefinition:result->error:-32603", "typeDefinition", "H3"))
        self.assertTrue(a.startswith("pyright-r1-typedefinition-result-error-32603-h3-"))
        self.assertNotEqual(a, group_id("pyright|r1_history|typeDefinition:result->error:-32603", "typeDefinition", "H1"))
        self.assertRegex(a, r"^[a-z0-9-]+$")


TEXT = "import os\nimport sys\n\nx = 1\ny = os.sep\nprint(y)\n"


class LineTests(unittest.TestCase):
    def test_blank_keeps_line_breaks(self) -> None:
        self.assertEqual(line_texts("a\r\nb\nc"), ["a\r\n", "b\n", "c"])
        self.assertEqual(blank_lines("a\r\nb\nc", {1}), "\r\nb\n")
        self.assertEqual(blank_lines(TEXT, set()).count("\n"), TEXT.count("\n"))

    def test_pinned_lines_follow_edits(self) -> None:
        ops = [Op("open", "m.py"), Op("change", "m.py", (0, 0), (0, 0), "# a\n# b\n"),  # 2 lines inserted above
               Op("change", "m.py", (6, 0), (6, 1), "Y"), Op("change", "m.py", (0, 0), (2, 0), "")]
        pins = pinned_lines("m.py", TEXT, ops, QueryKey("hover", "m.py", 4, 1))
        self.assertEqual(pins, {0, 4})  # line 6 after the insert is original line 4; the key is on line 4 again
        self.assertIsNone(pinned_lines("m.py", TEXT, [Op("fs_write", "m.py", text="x")], None))
        self.assertEqual(pinned_lines("other.py", TEXT, ops, None), set())
        self.assertEqual(touched_files(ops + [Op("request", "n.py", (0, 0), text="hover")], QueryKey("hover", "k.py")),
                         ["m.py", "n.py", "k.py"])


class FakeOracle:
    """Reproduces when the project's m.py still contains `needle` and the key line is intact."""

    name = "r1_history"

    def __init__(self) -> None:
        self.replays = 0

    def replay(self, ctx: OracleContext, v: Violation, ops: Optional[Sequence[Op]] = None) -> ReplayOutcome:
        self.replays += 1
        with open(os.path.join(ctx.project_dir, "m.py"), encoding="utf-8") as f:
            text = f.read()
        ok = "needle" in text and text.splitlines()[4] == "y = os.sep"
        return ReplayOutcome(True, True, ok)


class LineReduceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        write_text(os.path.join(self.root, "m.py"), TEXT.replace("x = 1", "needle = 1"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reduces_to_needed_lines_and_confirms(self) -> None:
        ctx = OracleContext("lr", "pyright", "1", "p", self.root, "python", 1, (), work_dir=os.path.join(self.tmp, "w"))
        v = make_violation(ctx, "r1_history", QueryKey("hover", "m.py", 4, 1), ["a", None], ["b", None],
                           [Op("open", "m.py")], {"family": "H1"})
        oracle = FakeOracle()
        res = reduce_lines(oracle, ctx, v, LineConfig(max_probes=30))
        self.assertEqual(res.confirmed, "3/3")
        kept = [ln for ln in res.files["m.py"].split("\n") if ln.strip()]
        self.assertEqual(kept, ["needle = 1", "y = os.sep"])
        self.assertEqual(res.files["m.py"].count("\n"), TEXT.count("\n"))
        self.assertEqual(res.lines["m.py"], (2, 5))
        other = make_violation(ctx, "r2_handles", QueryKey("hover", "m.py", 4, 1), 1, 2, [], {})
        self.assertIn("r2_handles", reduce_lines(oracle, ctx, other).skipped[0])


class IssueTests(unittest.TestCase):
    def test_queries(self) -> None:
        q = build_queries("pyright", "r1_history", "typeDefinition", "typeDefinition:result->error:-32603", "H3")
        self.assertEqual([x[1] for x in q], ['reopen in:title repo:microsoft/pyright is:issue',
                                             '"type definition" "internal error" repo:microsoft/pyright is:issue',
                                             '"type definition" reopen repo:microsoft/pyright is:issue',
                                             '"type definition" stale repo:microsoft/pyright is:issue'])
        msg = "Request textDocument/typeDefinition failed with message: Cannot read properties of undefined (reading 'fileInfo')"
        self.assertEqual(error_phrase(msg), "Cannot read properties of undefined reading fileInfo")
        q = build_queries("pyright", "r1_history", "typeDefinition", "typeDefinition:result->error:-32603", "H3",
                          error_phrase(msg))
        self.assertEqual(q[0][1], '"Cannot read properties of undefined reading fileInfo" repo:microsoft/pyright is:issue')
        self.assertTrue(all(x[1].endswith("label:gopls") for x in build_queries("gopls", "r0_crash", "hover",
                                                                                 "hover:result->error:dead", "")))
        self.assertEqual(len({r for r, _ in build_queries("ts6", "r1_history", "hover", "hover:text", "H1")}), 2)
        self.assertEqual(build_queries("clangd", "r1_history", "hover", "hover:text", "H1"), [])
        self.assertEqual(symptom_words("hover:lost"), "missing")

    def test_merge_drops_prs_and_duplicates(self) -> None:
        a = {"number": 1, "title": "A", "html_url": "u1", "state": "open", "created_at": "2024", "comments": 1}
        pr = dict(a, number=2, html_url="u2", pull_request=True)
        got = merge([("r", "q1", [a, pr]), ("r", "q2", [a, dict(a, number=3, html_url="u3")])])
        self.assertEqual([(m.number, m.query) for m in got], [(1, "q1"), (3, "q2")])

    def test_cached_search_never_writes_the_token(self) -> None:
        tmp = tempfile.mkdtemp()
        seen: List[Any] = []

        class Resp(io.BytesIO):
            def __enter__(self) -> "Resp":
                return self

            def __exit__(self, *a: Any) -> None:
                self.close()

        def opener(req: Any, timeout: float) -> Resp:
            seen.append(req)
            items = [{"number": 7, "title": "Hover wrong after undo", "html_url": "https://x/7", "state": "closed",
                      "created_at": "2024-09-10T00:00:00Z", "comments": 3, "body": "long text"}]
            return Resp(json.dumps({"total_count": 1, "items": items}).encode())

        try:
            with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "tok-test-secret"}):
                gh = GitHubSearch(cache_dir=tmp, opener=opener, sleep=lambda s: None)
                res = search_group("pyright", "r1_history", "hover", "hover:text", "H1", gh)
                again = search_group("pyright", "r1_history", "hover", "hover:text", "H1", gh)
            self.assertEqual(len(seen), 4)  # four queries, the second round comes from the cache
            self.assertEqual(seen[0].get_header("Authorization"), "Bearer tok-test-secret")
            self.assertEqual(res["matches"], again["matches"])
            self.assertEqual(res["matches"][0]["number"], 7)
            for name in os.listdir(tmp):
                with open(os.path.join(tmp, name), encoding="utf-8") as f:
                    content = f.read()
                self.assertNotIn("tok-test-secret", content)
                self.assertNotIn("long text", content)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def repro_doc() -> Dict[str, Any]:
    return {"oracle": "r1_history", "vid": "abc-v00", "campaign": "c", "reproduced": "3/3",
            "server": {"kind": "pyright", "version": "1.1.380"},
            "project": {"name": "pyright_8946", "source": "case", "ref": "pyright_8946", "commit": "",
                        "language": "python"},
            "context": {"seed": 1, "timing": "settled", "settle_timeout_s": 300, "request_timeout_s": 30,
                        "extra_settings": None, "max_cases": 16, "targets": []},
            "key": {"method": "typeDefinition", "path": "repro.py", "line": 5, "character": 15, "extra": ""},
            "ops": [Op("open", "repro.py").to_json(), Op("change", "repro.py", (5, 11), (5, 19), "datetim").to_json(),
                    Op("close", "repro.py").to_json(), Op("open", "repro.py").to_json()],
            "case": {"family": "H3", "timing": "settled"}, "expected": [["x.pyi", 0, 0, 0, 0]],
            "actual": ["error", -32603]}


class ReportTests(unittest.TestCase):
    def group(self) -> Any:
        rows = [row("abc-v00", "pyright|r1_history|typeDefinition:result->error:-32603", "typeDefinition",
                    {"family": "H3"}, 4)]
        return group_rows(rows)[0]

    def test_symptom_title_steps(self) -> None:
        self.assertEqual(symptom("typeDefinition:result->error:-32603"), "fails with an internal error (-32603)")
        self.assertEqual(symptom("diagnostics:missing:E1"), "misses E1")
        g = self.group()
        self.assertEqual(title(g, "1.1.380"),
                         "[pyright 1.1.380] typeDefinition fails with an internal error (-32603) after close and reopen")
        doc = repro_doc()
        st = steps(doc, [Op.from_json(o) for o in doc["ops"]], QueryKey(**doc["key"]))
        self.assertIn("textDocument/didChange", st[2])
        self.assertIn("wait until the server is idle after every step", st[5])
        self.assertIn("textDocument/typeDefinition", st[-1])
        self.assertIn("line 6, column 16", st[-1])
        doc["context"]["targets"] = [{"path": "repro.py", "positions": [], "ends": [], "names": []}]
        st = steps(doc, [Op.from_json(o) for o in doc["ops"][:3]], QueryKey(**doc["key"]))
        self.assertIn("textDocument/didOpen `repro.py` (the query step opens", st[5])

    def test_steps_of_other_oracles(self) -> None:
        doc = dict(repro_doc(), oracle="r3_routes", ops=[],
                   case={"sub": "d", "target": ["t.ts", 467, 20], "loc": ["s.ts", 70, 28, 70, 35]})
        st = steps(doc, [], QueryKey("definitionConsistency", "s.ts", 70, 31, "from:t.ts:467:20"))
        self.assertIn("`textDocument/definition` on `t.ts` at line 468, column 21", st[-1])
        self.assertIn("didOpen `s.ts`", st[-1])
        doc = dict(repro_doc(), oracle="r6_crossimpl", ops=[], case={"reference": {"kind": "ts6", "version": "6"}})
        st = steps(doc, [], QueryKey("hover", "a.ts", 5, 8))
        self.assertIn("reference ts6 6", st[1])
        self.assertIn("compare with the reference implementation's answer", st[-1])
        doc = dict(repro_doc(), oracle="r2_handles", ops=[],
                   case={"sub": "codeAction", "path": "a.go", "where": [3, 4, 3, 4], "extra": "pos",
                         "shift": {"variant": "top", "line": 0, "col": 0, "text": "\n"}})
        st = steps(doc, [], QueryKey("codeActionResolve", "a.go", 3, 4, "pos:3:4|top1|Fill struct|refactor|0"))
        self.assertIn("resolve the OLD code action `Fill struct`", st[-1])

    def test_render_report_and_index(self) -> None:
        g = self.group()
        red = {"vid": "abc-v00", "ops_before": 4, "ops_after": 3, "probes": 6, "reduced_confirmed": "3/3",
               "observed": {"expected": [["x.pyi", 0, 0, 0, 0]], "actual": ["error", -32603]}}
        issues = {"queries": ["type definition internal error repo:microsoft/pyright is:issue"],
                  "matches": [{"repo": "microsoft/pyright", "number": 8946, "url": "https://github.com/x/8946",
                               "title": "Type error after undo", "state": "closed", "created": "2024-09-10",
                               "comments": 2}], "notes": []}
        text = render_report(g, repro_doc(), red, issues, {"cmd": ["node", "x.js"], "sha256": "ab"}, {"python": "3"},
                             {"repro.py": "import os\n\nx = 1\n"}, ["[s] stderr: boom"],
                             "python3 scripts/lsptest/repro_violation.py t/repro.json")
        for part in ("# [pyright 1.1.380] typeDefinition fails", "## Relation violated", "History independence",
                     "## Minimal steps (LSP)", '"error"', "python3 scripts/lsptest/repro_violation.py t/repro.json",
                     "[microsoft/pyright#8946](https://github.com/x/8946)", "stderr: boom", "   3 | x = 1",
                     "ops 4 -> 4"):
            self.assertIn(part, text)
        index = render_index("c", [{"gid": g.gid, "signature": g.signature, "family": "H3", "members": 1,
                                    "ops_before": 4, "ops_after": 3, "matches": 1}])
        self.assertIn(f"[report]({g.gid}/report.md)", index)

    def test_decisions_template_keeps_author_rows(self) -> None:
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "decisions.csv")
        try:
            self.assertEqual(write_decisions(path, ["g1", "g2"]), ["g1", "g2"])
            with open(path, encoding="utf-8") as f:
                text = f.read().replace("g1,,,,,,", "g1,bug,https://x/1,,,2026-09-23,15")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self.assertEqual(write_decisions(path, ["g1", "g2", "g3"]), ["g3"])
            with open(path, encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(tuple(rows[0]), DECISION_COLUMNS)
            self.assertEqual([r["group"] for r in rows], ["g1", "g2", "g3"])
            self.assertEqual((rows[0]["verdict"], rows[0]["minutes_spent"]), ("bug", "15"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
