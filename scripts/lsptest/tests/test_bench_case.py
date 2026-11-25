"""Unit tests for the benchmark: case loading and validation (bench/case_format.py), the probe
library on synthetic answers (bench/probes.py, bench/probes_derived.py), the case verdict
and report of bench/run_repro.py, and the tsserver version strings of servers_bench.py.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "lsp_repro"))

from bench.case_format import CaseError, list_cases, load_case, validate_case  # noqa: E402
from bench.probes import PROBES, decide, error_code, new_items, query_id  # noqa: E402
from bench.probes_derived import changed_lines, forward_position, line_shift, map_back  # noqa: E402
from bench.run_repro import case_verdict, render_markdown  # noqa: E402
from bench.sources import verbatim_in  # noqa: E402
from servers_bench import split_tsserver_version  # noqa: E402

HOVER = {"method": "hover", "path": "a.py", "position": [0, 4]}
DIAG = [2, 0, 2, 5, 1, "2304", "ts", "Cannot find name 'T'."]


def sess(valid: bool = True, **extra: Any) -> Dict[str, Any]:
    return dict({"valid": valid, "reason": "" if valid else "not settled", "results": {}}, **extra)


def with_results(results: Dict[str, Any], valid: bool = True) -> Dict[str, Any]:
    return sess(valid, results=results)


def case_json(**over: Any) -> Dict[str, Any]:
    d = {"schema": 1, "id": "pyright-1", "language": "python", "settings": {}, "session": {},
         "meta": {"server": "pyright", "kind": "pyright", "number": 1, "url": "u", "title": "t", "oracle_class": "R1",
                  "subtype": "edit-undo", "fix_ref": "f", "fix_shas": [], "pre_version": "1.0", "post_version": "1.1",
                  "pre_build": "1.0", "post_build": "1.1", "build_notes": "", "effort_minutes": 5},
         "files": [{"path": "main.py", "provenance": "issue-adapted", "note": "renamed a variable"}],
         "repro": {"attempt": 1, "timing": "settled", "steps": "open, edit, compare",
                   "ops": [{"kind": "open", "path": "main.py"},
                           {"kind": "change", "path": "main.py", "start": [2, 0], "end": [2, 0], "text": "x = 1\n"}],
                   "probe": {"type": "differs_from_fresh", "params": {"queries": [dict(HOVER, path="main.py")]}}},
         "attempts": []}
    for k, v in over.items():
        d[k] = v
    return d


class CaseFormatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="bench-case-")
        self.dir = os.path.join(self.tmp, "pyright-1")
        os.makedirs(os.path.join(self.dir, "project"))
        with open(os.path.join(self.dir, "project", "main.py"), "w", encoding="utf-8") as f:
            f.write("def f(x):\n    return x\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, data: Dict[str, Any]) -> List[str]:
        with open(os.path.join(self.dir, "case.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
        return validate_case(load_case(self.dir))[0]

    def test_valid_case(self) -> None:
        self.assertEqual(self.write(case_json()), [])
        case = load_case(self.dir)
        self.assertEqual(case.build("pre"), "1.0")
        self.assertEqual([o.kind for o in case.repro.ops], ["open", "change"])

    def test_files_must_match_the_project(self) -> None:
        with open(os.path.join(self.dir, "project", "extra.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        errs = self.write(case_json(files=[{"path": "main.py", "provenance": "issue-adapted", "note": "n"},
                                           {"path": "gone.py", "provenance": "scaffold", "note": "n"}]))
        self.assertTrue(any("gone.py listed but missing" in e for e in errs))
        self.assertTrue(any("extra.py under project/ has no provenance" in e for e in errs))

    def test_provenance_rules(self) -> None:
        errs = self.write(case_json(files=[{"path": "main.py", "provenance": "scaffold"}]))
        self.assertTrue(any("needs a note" in e for e in errs))
        errs = self.write(case_json(files=[{"path": "main.py", "provenance": "copied"}]))
        self.assertTrue(any("provenance 'copied'" in e for e in errs))

    def test_meta_and_id(self) -> None:
        errs = self.write(case_json(id="pyright-2"))
        self.assertTrue(any("directory name" in e for e in errs))
        bad = case_json()
        bad["meta"] = dict(bad["meta"], kind="nosuchserver", post_build="1.0")
        del bad["meta"]["fix_ref"]
        errs = self.write(bad)
        self.assertTrue(any("meta.fix_ref missing" in e for e in errs))
        self.assertTrue(any("not in the server registry" in e for e in errs))
        self.assertTrue(any("pre_build equals post_build" in e for e in errs))

    def test_ops_are_replayed(self) -> None:
        d = case_json()
        d["repro"]["ops"] = [{"kind": "change", "path": "main.py", "start": [0, 0], "end": [0, 0], "text": "x"},
                             {"kind": "open", "path": "main.py"},
                             {"kind": "request", "path": "main.py", "start": [9, 0], "text": "hover"},
                             {"kind": "wait", "text": "settle"}]
        errs = self.write(d)
        self.assertTrue(any("change main.py: document not open" in e for e in errs))
        self.assertTrue(any("request main.py" in e and "outside the document" in e for e in errs))
        self.assertTrue(any("settle markers only make sense in race timing" in e for e in errs))

    def test_probe_validation(self) -> None:
        d = case_json()
        d["repro"]["ops"] = [{"kind": "open", "path": "main.py"}]
        errs = self.write(d)  # differs_from_fresh without a history step is trivially equal
        self.assertTrue(any("trivially equal" in e for e in errs))
        d = case_json()
        d["repro"]["probe"] = {"type": "nope", "params": {}}
        self.assertTrue(any("probe.type 'nope'" in e for e in self.write(d)))
        d = case_json()
        d["repro"]["probe"]["params"]["queries"] = [dict(HOVER, path="main.py", position=[5, 0])]
        self.assertTrue(any("outside the document" in e for e in self.write(d)))
        d = case_json()
        d["repro"]["probe"] = {"type": "two_routes_differ", "params": {
            "relation": "equal", "a": dict(HOVER, path="main.py"), "b": dict(HOVER, path="main.py")}}
        self.assertTrue(any("trivially related" in e for e in self.write(d)))

    def test_attempt_and_timing(self) -> None:
        d = case_json()
        d["repro"].update(attempt=3, timing="slow", steps="")
        errs = self.write(d)
        self.assertTrue(any("at most two honest attempts" in e for e in errs))
        self.assertTrue(any("repro.timing 'slow'" in e for e in errs))
        self.assertTrue(any("repro.steps" in e for e in errs))

    def test_unreadable_case(self) -> None:
        with open(os.path.join(self.dir, "case.json"), "w", encoding="utf-8") as f:
            f.write("{not json")
        with self.assertRaises(CaseError):
            load_case(self.dir)

    def test_verbatim_in(self) -> None:
        issue = "Repro:\n```py\ndef f(x):\n    e = 0\n```\ntext\n```py\n    return e\n```"
        self.assertEqual(verbatim_in("def f(x):\n  e = 0\n\n  return e\n", issue), (True, ""))
        self.assertEqual(verbatim_in("def f(x):\n    return e\n    e = 0\n", issue), (False, "e = 0"))

    def test_pilot_cases_validate(self) -> None:
        for d in list_cases():
            errs, _ = validate_case(load_case(d))
            self.assertEqual(errs, [], os.path.basename(d))


class ProbeTests(unittest.TestCase):
    def test_registry(self) -> None:
        self.assertLessEqual({  # other probe modules may register more types (probes_spec: edit_text_differs)
            "differs_from_fresh", "error_response", "edit_breaks_syntax", "edit_leaves_diagnostic",
            "diagnostic_present", "diagnostic_absent", "two_routes_differ", "transform_differs", "stale_code_action"},
            set(PROBES))
        self.assertEqual(query_id(HOVER), "hover@a.py:0:4")
        self.assertEqual(error_code(["error", -32603]), "-32603")
        self.assertIsNone(error_code(["x", 1, 2]))

    def test_differs_from_fresh(self) -> None:
        probe = {"type": "differs_from_fresh", "params": {"queries": [HOVER]}}
        qid = query_id(HOVER)

        def run(case: Any, fresh: Any, control: Any, valid: bool = True) -> str:
            return decide(probe, {"case": with_results({qid: case}, valid), "fresh": with_results({qid: fresh}),
                                  "control": with_results({qid: control})}).verdict

        self.assertEqual(run(["f: int", None], ["f: int", None], ["f: int", None]), "absent")
        self.assertEqual(run(["f: Literal[0]", None], ["f: int", None], ["f: int", None]), "present")
        self.assertEqual(run(["error", -32603], ["f: int", None], ["f: int", None]), "present")
        self.assertEqual(run(["f: int", None], ["f: int", None], ["f: str", None]), "invalid")  # unstable key
        self.assertEqual(run(["f: int", None], ["error", "timeout"], ["error", "timeout"]), "invalid")
        self.assertEqual(run(["x", None], ["f: int", None], ["f: int", None], valid=False), "invalid")
        self.assertEqual(decide(probe, {"case": sess()}).verdict, "invalid")  # sessions missing

    def test_error_response(self) -> None:
        q = {"method": "completion", "path": "a.ts", "position": [3, 9]}
        qid = query_id(q)
        probe = {"type": "error_response", "params": {"query": q}}
        verdict = lambda ans, p=probe: decide(p, {"case": with_results({qid: ans})}).verdict  # noqa: E731
        self.assertEqual(verdict(["error", 1]), "present")
        self.assertEqual(verdict(["a", "b"]), "absent")
        self.assertEqual(verdict(["error", "timeout"]), "invalid")
        coded = {"type": "error_response", "params": {"query": q, "codes": [-32603]}}
        self.assertEqual(verdict(["error", -32603], coded), "present")
        self.assertEqual(verdict(["error", -32601], coded), "absent")

    def edit(self, **over: Any) -> Dict[str, Any]:
        return dict({"offered": True, "chosen": "Add async", "titles": ["Add async"],
                     "texts_before": {"a.ts": "x\n"}, "texts_after": {"a.ts": "y\n"},
                     "syntax_before": {"a.ts": ["3:1: TS1005 ';' expected."]},
                     "syntax_after": {"a.ts": ["4:1: TS1005 ';' expected."]}}, **over)

    def test_edit_breaks_syntax(self) -> None:
        spec = {"via": "code_action", "path": "a.ts", "title_re": "async", "diagnostic": {"code": "1308"}}
        probe = {"type": "edit_breaks_syntax", "params": {"edit": spec}}
        run = lambda e, p=probe: decide(p, {"case": sess(edit=e)})  # noqa: E731
        self.assertEqual(run(self.edit()).verdict, "absent")  # the same error, moved
        res = run(self.edit(syntax_after={"a.ts": ["4:1: TS1005 ';' expected.", "1:25: TS1005 ',' expected."]}))
        self.assertEqual(res.verdict, "present")
        self.assertEqual(res.evidence["changed"], {"a.ts": ["y"]})
        self.assertEqual(run(self.edit(offered=False)).verdict, "invalid")
        gone = {"type": "edit_breaks_syntax", "params": {"edit": dict(spec, missing="absent")}}
        self.assertEqual(run(self.edit(offered=False), gone).verdict, "absent")
        self.assertEqual(run(self.edit(texts_after={})).verdict, "absent")  # an edit that changes nothing breaks nothing
        self.assertEqual(run(self.edit(error="overlap")).verdict, "invalid")
        self.assertTrue(PROBES["edit_breaks_syntax"].validate({"edit": {"via": "code_action", "path": "a"}}, []))

    def test_formatting_routes(self) -> None:
        validate = lambda spec: PROBES["edit_breaks_syntax"].validate({"edit": spec}, [])  # noqa: E731
        self.assertEqual(validate({"via": "format", "path": "a.ts"}), [])
        self.assertEqual(validate({"via": "range_format", "path": "a.ts", "range": [0, 10, 0, 13],
                                   "options": {"tabSize": 2, "insertSpaces": True}}), [])
        self.assertTrue(any("range_format needs range" in e for e in validate({"via": "range_format", "path": "a.ts"})))
        self.assertTrue(any("edit.options" in e for e in validate({"via": "format", "path": "a.ts", "options": 4})))
        self.assertTrue(any("edit.via" in e for e in validate({"via": "rename", "path": "a.ts"})))
        spec = {"via": "range_format", "path": "a.ts", "range": [0, 20, 0, 23]}
        probe = {"type": "edit_breaks_syntax", "params": {"edit": spec}}
        broken = self.edit(chosen="textDocument/rangeFormatting", via="range_format",
                           syntax_before={"a.ts": []}, syntax_after={"a.ts": ["1:23: TS1160 Unterminated template literal."]})
        self.assertEqual(decide(probe, {"case": sess(edit=broken)}).verdict, "present")
        self.assertEqual(decide(probe, {"case": sess(edit=self.edit(texts_after={}))}).verdict, "absent")

    def test_edit_leaves_diagnostic(self) -> None:
        spec = {"via": "code_action", "path": "a.ts", "title_re": "extends", "diagnostic": {"code": "2345"}}
        probe = {"type": "edit_leaves_diagnostic", "params": {"edit": spec, "target": {"code": "2345"}}}
        target = [4, 8, 4, 9, 1, "2345", "ts", "Argument of type ..."]
        case = sess(edit=self.edit(), diagnostics_before={"a.ts": [target]})
        run = lambda after: decide(probe, {"case": case, "after": sess(diagnostics={"a.ts": after})})  # noqa: E731
        self.assertEqual(run([]).verdict, "absent")
        self.assertEqual(run([target]).verdict, "present")  # the targeted diagnostic stays
        res = run([DIAG])
        self.assertEqual((res.verdict, len(res.evidence["added"])), ("present", 1))  # a new error appears
        self.assertEqual(run([[2, 0, 2, 5, 2, "6133", "ts", "unused"]]).verdict, "absent")  # a warning is no error
        self.assertEqual(run(["error", "timeout"]).verdict, "invalid")
        self.assertEqual(decide(probe, {"case": case, "after": sess(False)}).verdict, "invalid")
        # an offered edit that changes no text: the document stays as it was, no "after" session
        empty = self.edit(texts_after={})
        unchanged = lambda before: decide(probe, {"case": sess(edit=empty, diagnostics_before=before),  # noqa: E731
                                                  "after": sess(False)})
        res = unchanged({"a.ts": [target, DIAG]})
        self.assertEqual((res.verdict, res.evidence["kept"]), ("present", [target]))
        self.assertEqual(unchanged({"a.ts": [DIAG]}).verdict, "absent")
        self.assertEqual(unchanged({}).verdict, "invalid")
        self.assertEqual(unchanged({"a.ts": ["error", "timeout"]}).verdict, "invalid")

    def test_diagnostic_present_and_absent(self) -> None:
        qid = query_id({"method": "diagnostics", "path": "a.ts"})
        params = {"path": "a.ts", "match": {"code": "2304", "message_re": "Cannot find"}}
        answers = {"case": with_results({qid: [DIAG]})}
        self.assertEqual(decide({"type": "diagnostic_present", "params": params}, answers).verdict, "present")
        self.assertEqual(decide({"type": "diagnostic_absent", "params": params}, answers).verdict, "absent")
        empty = {"case": with_results({qid: []})}
        self.assertEqual(decide({"type": "diagnostic_absent", "params": params}, empty).verdict, "present")
        broken = {"case": with_results({qid: ["error", -32603]})}
        self.assertEqual(decide({"type": "diagnostic_present", "params": params}, broken).verdict, "invalid")

    def test_two_routes_differ(self) -> None:
        a = {"method": "documentHighlight", "path": "main.go", "position": [4, 15]}
        b = {"method": "references", "path": "main.go", "position": [4, 15]}
        probe = {"type": "two_routes_differ", "params": {"relation": "highlights_in_references", "a": a, "b": b}}
        refs = [["main.go", 4, 1, 4, 20], ["main.go", 9, 1, 9, 9], ["other.go", 8, 1, 8, 5]]
        run = lambda hl, rf=refs: decide(probe, {"case": with_results({query_id(a): hl, query_id(b): rf})})  # noqa: E731
        self.assertEqual(run([[4, 1, 4, 20, 1], [9, 1, 9, 9, 1]]).verdict, "absent")
        res = run([[4, 1, 4, 20, 1], [8, 1, 8, 5, 1], [9, 1, 9, 9, 1]])
        self.assertEqual((res.verdict, res.evidence["witness"]), ("present", [[8, 1, 8, 5, 1]]))
        self.assertEqual(run([[4, 1, 4, 20, 1]], ["error", 0]).verdict, "invalid")
        subset = {"type": "two_routes_differ", "params": {"relation": "subset", "a": a, "b": b}}
        self.assertEqual(decide(subset, {"case": with_results({query_id(a): [1], query_id(b): [1, 2]})}).verdict, "absent")
        self.assertEqual(new_items([1, 2], [2, 3, 3], key=lambda x: x), [3, 3])

    def test_stale_code_action(self) -> None:
        handle = {"path": "A.java", "range": [3, 19, 3, 23], "title_re": "(?i)setter"}
        probe = {"type": "stale_code_action", "params": {"handle": handle, "mint_after": 1}}
        edit = [["A.java", 5, 5, 5, 5, "void setName() {}"]]
        moved = [["A.java", 7, 5, 7, 5, "void setName() {}"]]

        def run(stale: Any, fresh: Any = None, minted: Any = None) -> Any:
            m = dict({"offered": True, "chosen": "Generate Setter", "resolvable": True, "edit": edit}, **(minted or {}))
            f = {"offered": True, "titles": ["Generate Setter"], "edit": edit} if fresh is None else fresh
            return decide(probe, {"case": sess(handle={"minted": m, "stale": stale, "fresh": f})})

        ok = {"edit": edit, "error": None, "outdated_version": False}
        self.assertEqual(run(ok).verdict, "absent")  # the stale edit is the fresh one
        self.assertEqual(run({"edit": None, "error": None}).verdict, "absent")  # no edit
        self.assertEqual(run({"edit": None, "error": -32603}).verdict, "absent")  # refused
        self.assertEqual(run(dict(ok, edit=moved, outdated_version=True)).verdict, "absent")  # clients refuse it
        res = run(dict(ok, edit=moved))
        self.assertEqual(res.verdict, "present")
        self.assertIn("differs from the fresh edit", res.reason)
        self.assertEqual(run(ok, fresh={"offered": False, "titles": ["Generate Getter"]}).verdict, "present")
        self.assertEqual(run(ok, fresh={"offered": True, "edit": None}).verdict, "present")
        self.assertEqual(run(ok, minted={"offered": False, "titles": []}).verdict, "invalid")
        self.assertEqual(run(ok, minted={"resolvable": False}).verdict, "invalid")
        self.assertEqual(run(ok, minted={"edit": None}).verdict, "invalid")
        self.assertEqual(decide(probe, {"case": sess(handle={"minted": {"offered": True, "resolvable": True,
                                                                          "edit": edit}})}).verdict, "invalid")
        self.assertEqual(decide(probe, {"case": sess(False)}).verdict, "invalid")
        validate = PROBES["stale_code_action"].validate
        ops = [{"kind": "open", "path": "A.java"}, {"kind": "change", "path": "A.java"}]
        self.assertEqual(validate(probe["params"], ops), [])
        self.assertTrue(any("mint_after" in e for e in validate(dict(probe["params"], mint_after=3), ops)))
        self.assertTrue(any("cannot go stale" in e for e in validate(probe["params"], ops[:1])))
        self.assertTrue(any("range" in e for e in validate({"handle": {"path": "A.java", "title_re": "x"},
                                                            "mint_after": 1}, ops)))

    def test_transform_differs(self) -> None:
        t = {"kind": "insert_lines", "path": "a.py", "line": 1, "text": "\n\n"}
        q = {"method": "diagnostics", "path": "a.py"}
        probe = {"type": "transform_differs", "params": {"transform": t, "queries": [q, HOVER]}}
        plan = PROBES["transform_differs"].queries(probe["params"])
        self.assertEqual(plan["transformed"][1]["position"], [0, 4])  # above the insertion point
        self.assertEqual(forward_position(t, [3, 2]), [5, 2])
        shift = line_shift(t)
        self.assertEqual((shift(0), shift(1), shift(2), shift(3)), (0, None, None, 1))
        base = [[1, 0, 1, 3, 1, "E", "s", "m"]]
        moved = [[3, 0, 3, 3, 1, "E", "s", "m"]]
        self.assertEqual(map_back("diagnostics", moved, shift, "a.py"), base)
        hover = ["x: int", [0, 4, 0, 5]]

        def run(transformed_diag: Any) -> str:
            fresh = with_results({query_id(q): base, query_id(HOVER): hover})
            other = with_results({query_id(q): transformed_diag, query_id(HOVER): hover})
            return decide(probe, {"fresh": fresh, "control": fresh, "transformed": other}).verdict

        self.assertEqual(run(moved), "absent")
        self.assertEqual(run([[4, 0, 4, 3, 1, "E", "s", "m"]]), "present")
        self.assertEqual(changed_lines({"texts_before": {"a": "x\ny"}, "texts_after": {"a": "x\nz"}}), {"a": ["z"]})
        errs = PROBES["transform_differs"].validate(probe["params"], [{"kind": "change", "path": "a.py"}])
        self.assertTrue(any("only open/wait" in e for e in errs))


class RunnerTests(unittest.TestCase):
    @staticmethod
    def runs(pre: List[str], post: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        mk = lambda vs: [{"run": i + 1, "verdict": v, "reason": v} for i, v in enumerate(vs)]  # noqa: E731
        return {"pre": mk(pre), "post": mk(post)}

    def test_case_verdict(self) -> None:
        p, a, x = "present", "absent", "invalid"
        self.assertEqual(case_verdict(self.runs([p, p, p], [a, a, a]), 3)["verdict"], "reproduced")
        self.assertEqual(case_verdict(self.runs([a, a, a], [a, a, a]), 3)["verdict"], "not-reproduced-pre")
        self.assertEqual(case_verdict(self.runs([p, p, p], [p, p, p]), 3)["verdict"], "still-present-post")
        self.assertEqual(case_verdict(self.runs([p, a, p], [a, a, a]), 3)["verdict"], "flaky")
        self.assertEqual(case_verdict(self.runs([p, p, p], [a, p, a]), 3)["verdict"], "flaky")
        bad = case_verdict(self.runs([p, p, p], [a, x, a]), 3)
        self.assertEqual(bad["verdict"], "invalid")
        self.assertIn("post run 2", bad["reason"])
        self.assertEqual(case_verdict(self.runs([p, p], [a, a, a]), 3)["verdict"], "invalid")

    def test_render_markdown(self) -> None:
        line = {"case": "gopls-1", "verdict": "reproduced", "reason": "pre 3/3 | post 0/3", "attempt": 1,
                "timing": "settled", "builds": {"pre": "v1", "post": "v2"}, "minutes": 0.3, "effort_minutes": 9,
                "runs": self.runs(["present"] * 3, ["absent"] * 3)}
        for r in line["runs"]["pre"] + line["runs"]["post"]:
            r.update(build="v", seconds=1.0)
        md = render_markdown([line])
        self.assertIn("| gopls-1 |", md)
        self.assertIn("**reproduced**", md)
        self.assertIn("pre 3/3 \\| post 0/3", md)

    def test_tsserver_versions(self) -> None:
        self.assertEqual(split_tsserver_version("5.0.4+tsls3.3.2"), ("5.0.4", "3.3.2"))
        self.assertEqual(split_tsserver_version("5.1.0-dev.20230323+tsls3.3.2"), ("5.1.0-dev.20230323", "3.3.2"))
        with self.assertRaises(ValueError):
            split_tsserver_version("5.0.4")


if __name__ == "__main__":
    unittest.main()
