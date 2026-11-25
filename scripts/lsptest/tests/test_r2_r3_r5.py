"""Unit tests for the pure logic of the R2, R3 and R5 oracles: semantic-token delta
application, edit normalization and verdicts (R2); range restriction, the highlight-subset
check, shorthand labelling and route comparison (R3); insertion points, code line ends,
position/range mapping, answer mapping and case planning (R5).

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
import tempfile
import unittest
from dataclasses import asdict
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from model import Op, QueryKey, QueryResult, Snapshot  # noqa: E402
from oracles.base import MISSING, OracleContext, final_state  # noqa: E402
from oracles.r2_handles import (apply_delta, completion_edits, edit_entries, flatten, judge_edit,  # noqa: E402
                                make_shift, map_pos, resolve_produced, token_window, with_occurrence)
from oracles.r3_routes import (SessionOut, apply_text_edits, compare_routes, highlight_check,  # noqa: E402
                               key_targets, ref_position, rng4, seeded_ranges, shorthand, site_label, tokens_inside)
from oracles.r5_transforms import (INLINE, Shift, Transform, canonical, code_line_ends, comment_spots,  # noqa: E402
                                   compare_mapped, drop_inserted, insertion_line, make_transform, map_key, map_norm,
                                   plan_cases)
from ops import LineIndex, apply_change  # noqa: E402
from targets import FileTargets  # noqa: E402

PY = ('#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n"""Module doc."""\nfrom __future__ import annotations\n'
      'import os\nfrom typing import (\n    Any,\n)\n\n# comment\n@deco\ndef f():\n    s = """a\nb"""\n'
      '    return s  # c\nx = 1 + \\\n    2\n')
TS = ('#!/usr/bin/env node\n/// <reference types="node" />\n// @ts-nocheck\n"use strict";\nimport a from "a";\n'
      'import {\n  b,\n  c,\n} from "https://x.io/b";\nexport * from "./c";\nexport { d };\n/** doc */\n'
      'export function f() {\n  const t = `x\n y`;\n  return t; // e\n}\n')
GO = ('//go:build linux\n\n// Package p does.\npackage p\n\nimport (\n\t"fmt"\n\t"os"\n)\n\n// F doc.\nfunc F() {\n'
      '\ts := `raw\nx`\n\tfmt.Println(s, os.Args)\n}\n')
RS = ('#![allow(dead_code)]\n//! Crate doc.\n\nuse std::io;\nuse std::{\n    fmt,\n    collections::HashMap,\n};\n'
      'mod foo;\n\n/// Doc.\n#[derive(Debug)]\nstruct S { x: i32 }\nfn g() -> &\'static str { r#"a\nb"# }\n')


def rng(sl: int, sc: int, el: int, ec: int) -> Dict[str, Any]:
    return {"start": {"line": sl, "character": sc}, "end": {"line": el, "character": ec}}


def snap(results: Dict[QueryKey, Any], settled: bool = True) -> Snapshot:
    return Snapshot("s", "srv-1", settled, {k: QueryResult(k, v) for k, v in results.items()})


def apply_ops_text(text: str, ops: List[Op]) -> str:
    for op in ops:
        text = apply_change(text, op.start, op.end, op.text)[0] if op.kind == "change" else text
    return text


class TestR2Pure(unittest.TestCase):
    def test_apply_delta(self) -> None:
        data = list(range(15))
        self.assertEqual(apply_delta(data, [{"start": 5, "deleteCount": 5, "data": [9, 9]}]),
                         data[:5] + [9, 9] + data[10:])
        both = apply_delta(data, [{"start": 10, "deleteCount": 0, "data": [7]}, {"start": 0, "deleteCount": 5}])
        self.assertEqual(both, data[5:10] + [7] + data[10:])
        overlap = [{"start": 0, "deleteCount": 6}, {"start": 5, "deleteCount": 1}]
        for bad in ([{"start": 12, "deleteCount": 5}], overlap):
            with self.assertRaises(ValueError):
                apply_delta(data, bad)

    def test_edit_entries(self) -> None:
        rel = lambda u: u.split("/ws/")[-1]  # noqa: E731
        edit = {"changes": {"file:///ws/a.py": [{"range": rng(1, 0, 1, 2), "newText": "x"}]},
                "documentChanges": [{"textDocument": {"uri": "file:///ws/b.py", "version": 3},
                                     "edits": [{"range": rng(0, 0, 0, 0), "newText": "y"}]},
                                    {"kind": "rename", "oldUri": "file:///ws/c.py", "newUri": "file:///ws/d.py"}]}
        entries, versions = edit_entries(edit, rel)
        self.assertEqual(entries, [["<rename>", "c.py", "d.py"], ["a.py", 1, 0, 1, 2, "x"], ["b.py", 0, 0, 0, 0, "y"]])
        self.assertEqual(versions, {"b.py": 3})
        self.assertEqual(edit_entries(None, rel), ([], {}))

    def test_completion_resolve_produced(self) -> None:
        minted = {"label": "f", "textEdit": {"range": rng(3, 0, 3, 1), "newText": "f"}}
        resolved = dict(minted, additionalTextEdits=[{"range": rng(0, 0, 0, 0), "newText": "import f\n"}])
        self.assertEqual(resolve_produced(minted, resolved), {"additionalTextEdits": [[0, 0, 0, 0, "import f\n"]]})
        self.assertEqual(resolve_produced(minted, minted), {})
        ir = {"textEdit": {"insert": rng(1, 0, 1, 1), "replace": rng(1, 0, 1, 3), "newText": "g"}}
        self.assertEqual(completion_edits(ir), {"textEdit": [[1, 0, 1, 1, 1, 0, 1, 3, "g"]]})
        self.assertEqual(flatten({"textEdit": [[1, 0, 1, 1, "g"]]}), [["textEdit", 1, 0, 1, 1, "g"]])

    def test_judge_edit(self) -> None:
        k = QueryKey("codeActionResolve", "a.py", 1, 2)
        e1, e2 = [["a.py", 1, 0, 1, 0, "x"]], [["a.py", 2, 0, 2, 0, "x"]]
        self.assertEqual(judge_edit(k, [], ("error", -32801), {}, {}, [e1, e1]).allowed, "error:-32801")
        self.assertEqual(judge_edit(k, [], None, {}, {}, [e1, e1]).allowed, "no edit")
        self.assertEqual(judge_edit(k, e1, None, {"a.py": 1}, {"a.py": 2}, [e1, e1]).allowed, "stale version named")
        self.assertEqual(judge_edit(k, e1, None, {}, {}, [None, e1]).allowed, "no comparable fresh edit")
        self.assertFalse(judge_edit(k, e1, None, {}, {}, [e1, e2]).stable)
        same = judge_edit(k, e1, None, {"a.py": 2}, {"a.py": 2}, [e1, e1])
        diff = judge_edit(k, e2, None, {}, {}, [e1, e1])
        self.assertEqual((same.expected, same.actual, same.allowed), (e1, e1, ""))
        self.assertEqual((diff.expected, diff.actual, diff.stable), (e1, e2, True))

    def test_shift_and_map(self) -> None:
        text = "a\nb\nc\n"
        above, below, end = (make_shift(text, 1, v, 2) for v in ("above", "below", "end"))
        self.assertEqual([(s["line"], s["col"], s["variant"]) for s in (above, below, end)],
                         [(1, 0, "above"), (2, 0, "below"), (3, 0, "end")])
        self.assertEqual([map_pos((1, 1), s) for s in (above, below, end)], [(3, 1), (1, 1), (1, 1)])
        self.assertEqual(map_pos((0, 1), above), (0, 1))
        tail = make_shift("a\nbc", 1, "end", 1)
        self.assertEqual((tail["line"], tail["col"]), (1, 2))
        self.assertEqual((map_pos((1, 1), tail), map_pos((1, 2), tail)), ((1, 1), (2, 0)))
        self.assertEqual(make_shift("a\r\nb\r\n", 0, "above", 2)["text"], "\r\n\r\n")

    def test_token_window_and_occurrence(self) -> None:
        exp = [[0, 0, 1, "a", ""], [2, 0, 3, "b", ""], [2, 4, 1, "c", ""]]
        act = [[0, 0, 1, "a", ""], [2, 0, 3, "b", ""], [2, 4, 1, "d", ""]]
        self.assertEqual(token_window(exp, act), (exp[1:], act[1:]))
        self.assertEqual(token_window(exp, exp), ([], []))
        occ = with_occurrence([{"t": "x"}, {"t": "y"}, {"t": "x"}], lambda a: (a["t"],))
        self.assertEqual(list(occ), [("x", "0"), ("y", "0"), ("x", "1")])


class TestR3Pure(unittest.TestCase):
    TOKENS = [[1, 0, 3, "v", ""], [1, 4, 2, "f", ""], [2, 0, 5, "v", ""], [3, 2, 4, "v", ""]]

    def test_tokens_inside(self) -> None:
        self.assertEqual(tokens_inside(self.TOKENS, [1, 0, 3, 0]), self.TOKENS[:3])
        self.assertEqual(tokens_inside(self.TOKENS, [1, 1, 3, 5]), [self.TOKENS[1], self.TOKENS[2]])
        self.assertEqual(tokens_inside(self.TOKENS, [1, 4, 1, 5]), [])  # a token crossing the end is left out
        self.assertEqual(tokens_inside(None, [0, 0, 9, 0]), [])

    def test_highlight_check(self) -> None:
        refs = [["a.ts", 1, 0, 1, 3], ["a.ts", 4, 2, 4, 5], ["b.ts", 7, 0, 7, 3]]
        good = [[1, 0, 1, 3, 3], [4, 2, 4, 5, 2]]
        self.assertEqual(highlight_check(good, refs, "a.ts"), ([[1, 0, 1, 3], [4, 2, 4, 5]],) * 2)
        exp, act = highlight_check(good + [[7, 0, 7, 3, 1]], refs, "a.ts")
        self.assertEqual((exp, act), ([[1, 0, 1, 3], [4, 2, 4, 5]], [[1, 0, 1, 3], [4, 2, 4, 5], [7, 0, 7, 3]]))
        self.assertIsNone(highlight_check(["error", -32601], refs, "a.ts"))
        self.assertIsNone(highlight_check(good, ["error", "timeout"], "a.ts"))
        self.assertEqual(highlight_check(good, [], "a.ts")[0], [])

    def test_seeded_ranges(self) -> None:
        text = "\n".join(f"line {i} of the file" for i in range(60)) + "\n"
        a = seeded_ranges(text, [(10, 3), (40, 5)], 7, "x.ts")
        self.assertEqual(a, seeded_ranges(text, [(10, 3), (40, 5)], 7, "x.ts"))
        self.assertEqual(a[-1], [0, 0, 60, 0])
        self.assertTrue(all((r[0], r[1]) < (r[2], r[3]) and r[2] <= 60 for r in a))

    def test_ref_position_shorthand_site_label(self) -> None:
        self.assertEqual(ref_position(["a.ts", 3, 4, 3, 10]), ("a.ts", 3, 7))
        self.assertEqual(ref_position(["a.ts", 3, 4, 5, 1]), ("a.ts", 3, 4))
        self.assertTrue(shorthand("const o = { a, name };\n", 0, 15, 19))
        self.assertTrue(shorthand("let s = S {\n    name,\n};\n", 1, 4, 8))
        self.assertFalse(shorthand("const o = { name: name };\n", 0, 12, 16))
        self.assertFalse(shorthand("f(name, x);\n", 0, 2, 6))
        self.assertFalse(shorthand('import { a, name } from "x";\n', 0, 12, 16))
        self.assertFalse(shorthand("export {\n  name,\n};\n", 1, 2, 6))
        lib = "/lib/lib.d.ts"
        defs = [[lib, 16, 10, 16, 13], [lib, 180, 4, 180, 71]]
        at_instanceof = [[lib, 16, 10, 16, 13], [lib, 161, 4, 161, 24]]
        at = ["a.ts", 0, 13, 0, 16]
        self.assertEqual(site_label("x instanceof Map\n", at, defs, at_instanceof, "js"), "signature")
        pattern = "const { storage, setItemSpy } = make()\n"
        loc = ["t.ts", 0, 17, 0, 27]
        binding, member = [["t.ts", 5, 4, 5, 14]], [["t.ts", 30, 4, 30, 14]]
        self.assertEqual(site_label(pattern, loc, binding, member, "js"), "shorthand")
        self.assertEqual(site_label(pattern, loc, binding, member, "go"), "")
        self.assertEqual(site_label(pattern, loc, defs, defs, "js"), "")
        self.assertEqual(site_label("f(a)\n", ["a.ts", 0, 2, 0, 3], [["b.ts", 1, 0, 1, 1]], [["c.ts", 2, 0, 2, 1]],
                                    "js"), "")

    def test_apply_text_edits_and_rng4(self) -> None:
        text = "abc\ndef\n"
        self.assertEqual(apply_text_edits(text, [[0, 1, 0, 2, "X"], [1, 0, 1, 0, "Y"]]), "aXc\nYdef\n")
        self.assertEqual(apply_text_edits(text, [[0, 0, 0, 0, "1"], [0, 0, 0, 0, "2"]]), "12abc\ndef\n")
        with self.assertRaises(Exception):
            apply_text_edits(text, [[5, 0, 5, 1, "Z"]])
        with self.assertRaises(Exception):
            apply_text_edits(text, [[0, 0, 0, 2, "a"], [0, 1, 0, 3, "b"]])
        self.assertEqual(rng4(rng(1, 2, 3, 4)), [1, 2, 3, 4])

    def test_compare_routes(self) -> None:
        k = QueryKey("diagnostics", "a.py")
        d1 = [0, 0, 0, 1, 1, "E1", "src", "bad"]
        base = snap({k: [d1]})
        pulled = SessionOut(snap({k: [d1]}), pull=True)
        self.assertEqual(compare_routes(base, pulled, {k}, True, 1), ([], ""))
        diffs, why = compare_routes(base, SessionOut(snap({k: []}), pull=True), {k}, True, 1)
        self.assertEqual((diffs[0][0].extra, diffs[0][2], why), ("route:pull", [], ""))
        self.assertIn("not applicable", compare_routes(base, SessionOut(snap({k: []}), pull=True), {k}, False, 1)[1])
        pushed = SessionOut(snap({k: None}), pull=False, assumed=["a.py"])
        self.assertIn("no publishDiagnostics", compare_routes(base, pushed, {k}, False, 1)[1])
        quiet = SessionOut(snap({k: None, QueryKey("diagnostics", "b.py"): []}), pull=False, assumed=["a.py"])
        clean = snap({k: [], QueryKey("diagnostics", "b.py"): []})
        self.assertEqual(compare_routes(clean, quiet, {k}, False, 2), ([], ""))


class TestR5Insertion(unittest.TestCase):
    def line_of(self, text: str, language: str) -> str:
        line = insertion_line(text, language)
        return text.split("\n")[line - 1] if line else ""

    def test_python(self) -> None:
        self.assertEqual(self.line_of(PY, "python"), ")")
        self.assertEqual(insertion_line('#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n\n@d\ndef f():\n  pass\n',
                                        "python"), 3)
        self.assertEqual(insertion_line('"""Doc only."""\nx = 1\n', "python"), 1)
        self.assertIsNone(insertion_line("def f(:\n", "python"))
        self.assertIsNone(insertion_line("import os", "python"))  # no line after the import block

    def test_typescript(self) -> None:
        self.assertEqual(self.line_of(TS, "typescript"), 'export * from "./c";')
        no_imports = '#!/usr/bin/env node\n"use client";\n/** doc */\nexport const x = 1;\n'
        self.assertEqual(insertion_line(no_imports, "typescript"), 2)
        decorated = 'import { A } from "a"\nimport B from "b"\n@A()\nclass C {}\n'
        self.assertEqual(insertion_line(decorated, "typescript"), 2)

    def test_go_and_rust(self) -> None:
        self.assertEqual(self.line_of(GO, "go"), ")")
        self.assertEqual(insertion_line('package p\n\n// Doc.\nfunc F() {}\n', "go"), 1)
        self.assertEqual(self.line_of(RS, "rust"), "mod foo;")
        self.assertEqual(insertion_line('//! Doc.\n#![no_std]\n\n/// S.\n#[derive(Debug)]\nstruct S;\n', "rust"), 2)
        attr = 'use a::b;\n#[cfg(test)]\nmod tests {\n    use super::*;\n}\n'
        self.assertEqual(insertion_line(attr, "rust"), 1)

    def test_code_line_ends(self) -> None:
        lines = PY.split("\n")
        ends = code_line_ends(PY, "python")
        self.assertNotIn(0, ends)  # shebang
        self.assertNotIn(12, ends)  # inside the triple-quoted string
        self.assertNotIn(14, ends)  # ends in a comment
        self.assertNotIn(15, ends)  # continuation backslash
        self.assertTrue({11, 13, 16} <= ends and lines[13] == 'b"""')
        self.assertNotIn(13, code_line_ends(TS, "typescript"))  # inside a template literal
        self.assertNotIn(15, code_line_ends(TS, "typescript"))  # line comment at the end
        self.assertNotIn(12, code_line_ends(GO, "go"))  # inside a raw string
        self.assertNotIn(13, code_line_ends(RS, "rust"))  # inside a raw string


class TestR5Mapping(unittest.TestCase):
    S = Shift("a.py", 5, n=2)

    def test_shift(self) -> None:
        s = self.S
        self.assertEqual((s.pos(4, 9), s.pos(5, 0), s.pos(9, 3)), ((4, 9), (7, 0), (11, 3)))
        self.assertEqual(s.rng([3, 1, 5, 0]), [3, 1, 5, 0])  # an end at the insertion point stays
        self.assertEqual(s.rng([5, 0, 5, 0]), [7, 0, 7, 0])
        self.assertEqual(s.rng([3, 1, 7, 2]), [3, 1, 9, 2])
        self.assertTrue(s.inserted(5, 0, 6, 9) and not s.inserted(4, 0, 5, 0) and not s.inserted(7, 0, 7, 0))
        self.assertFalse(Shift("a.py", 5).inserted(5, 0, 5, 1))

    def test_map_norm(self) -> None:
        s = self.S
        self.assertEqual(map_norm("references", [["a.py", 6, 1, 6, 4], ["b.py", 6, 1, 6, 4]], "b.py", s),
                         [["a.py", 8, 1, 8, 4], ["b.py", 6, 1, 6, 4]])
        diag = [[6, 0, 6, 1, 1, "c", "s", "m"]]
        self.assertEqual(map_norm("diagnostics", diag, "b.py", s), diag)
        self.assertEqual(map_norm("hover", ["t", [6, 0, 6, 2]], "a.py", s), ["t", [8, 0, 8, 2]])
        self.assertEqual(map_norm("documentSymbol", [["f", 12, 4, 0, 9, 1]], "a.py", s), [["f", 12, 4, 0, 11, 1]])
        self.assertEqual(map_norm("foldingRange", [[2, -1, 6, -1, ""]], "a.py", s), [[2, -1, 8, -1, ""]])
        inline = Shift("a.ts", 21, 9, 0, 11)  # T6: characters after the comment move, absent ones (-1) stay
        self.assertEqual(map_norm("foldingRange", [[21, 59, 23, 5, ""], [2, -1, 21, -1, ""]], "a.ts", inline),
                         [[21, 70, 23, 5, ""], [2, -1, 21, -1, ""]])
        self.assertEqual(map_norm("semanticTokens", [[5, 3, 2, "v", ""]], "a.py", s), [[7, 3, 2, "v", ""]])
        self.assertEqual(map_norm("completion", ["x", "y"], "a.py", s), ["x", "y"])
        self.assertEqual(map_norm("hover", ["error", -32801], "a.py", s), ["error", -32801])

    def test_drop_canonical_key(self) -> None:
        s = self.S
        toks = [[4, 0, 1, "x", ""], [5, 0, 3, "comment", ""], [7, 0, 2, "y", ""]]
        self.assertEqual(drop_inserted("semanticTokens", toks, "a.py", s), [toks[0], toks[2]])
        self.assertEqual(drop_inserted("semanticTokens", toks, "b.py", s), toks)
        self.assertEqual(canonical("diagnostics", [[1, 2, 3, 4, 1, "E", "src", "line 12 col 3"]]),
                         [[1, 2, 3, 4, 1, "E", "src", "line # col #"]])
        self.assertEqual(map_key(QueryKey("codeAction", "a.py", 6, 2, "diag:8:3"), s),
                         QueryKey("codeAction", "a.py", 8, 2, "diag:10:3"))
        self.assertEqual(map_key(QueryKey("hover", "b.py", 6, 2), s), QueryKey("hover", "b.py", 6, 2))
        self.assertEqual(map_key(QueryKey("diagnostics", "a.py"), s), QueryKey("diagnostics", "a.py"))

    def test_compare_mapped(self) -> None:
        s, hk, dk = self.S, QueryKey("hover", "a.py", 6, 1), QueryKey("diagnostics", "a.py")
        base = snap({hk: ["int", [6, 0, 6, 3]], dk: [[9, 0, 9, 1, 1, "E", "x", "see line 9"]]})
        same = snap({QueryKey("hover", "a.py", 8, 1): ["int", [8, 0, 8, 3]],
                     dk: [[11, 0, 11, 1, 1, "E", "x", "see line 11"], [5, 0, 5, 3, 3, "", "x", "on the new line"]]})
        self.assertEqual(compare_mapped(base, same, [hk, dk], s), [])
        other = snap({QueryKey("hover", "a.py", 8, 1): ["str", [8, 0, 8, 3]], dk: []})
        diffs = compare_mapped(base, other, [hk, dk], s)
        self.assertEqual([k.method for k, _, _ in diffs], ["diagnostics", "hover"])
        self.assertEqual(compare_mapped(base, snap({}), [hk], s)[0][2], MISSING)


class TestR5Cases(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp(prefix="r5-test-")
        for name, text in (("a.py", PY), ("b.py", "import sys\n\nprint(sys.argv)\n")):
            with open(os.path.join(self.root, name), "w") as f:
                f.write(text)
        self.targets = (FileTargets("a.py", ((11, 5),), ((11, 5),), ("f",)),
                        FileTargets("b.py", ((2, 1),), ((2, 5),), ("p",)))

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def make(self, kind: str, text: str = PY, language: str = "python", ft: Any = None) -> Transform:
        return make_transform(kind, "a.py", text, language, random.Random(3), ft)

    def test_t1_t2_t3(self) -> None:
        t1, t2, t3 = self.make("T1"), self.make("T2"), self.make("T3")
        self.assertEqual((t1.edits[0][:4], t2.edits[0], t2.shift.n, t3.shift), ((8, 0, 8, 0),
                         (8, 0, 8, 0, "\n# inserted comment line\n\n"), 3, Shift("a.py")))
        self.assertEqual(apply_ops_text(PY, t2.ops()).split("\n")[7:11], [")", "", "# inserted comment line", ""])
        self.assertTrue(all(e[0] >= 8 for e in t3.edits))  # T3 leaves the import block alone
        self.assertEqual(final_state(self.root, t3.ops()).files["a.py"], apply_ops_text(PY, t3.ops()))
        lines = apply_ops_text(PY, t3.ops()).split("\n")
        self.assertTrue(all(lines[e[0]].endswith(e[4]) for e in t3.edits))
        self.assertEqual(Transform.from_json(json.loads(json.dumps(asdict(t3)))), t3)

    def test_t4_crlf(self) -> None:
        t4 = self.make("T4")
        out = apply_ops_text(PY, t4.ops())
        self.assertEqual(out, PY.replace("\n", "\r\n"))
        a, b = LineIndex(PY), LineIndex(out)
        self.assertEqual([a.line_text(i) for i in range(len(a.starts))], [b.line_text(i) for i in range(len(b.starts))])
        self.assertIsNone(self.make("T4", out))
        self.assertEqual(t4.shift.pos(5, 3), (5, 3))

    def test_t5_final_newline(self) -> None:
        drop = self.make("T5")
        self.assertEqual(apply_ops_text(PY, drop.ops()), PY[:-1])
        self.assertEqual((drop.shift.pos(17, 0), drop.shift.pos(16, 5)), ((16, 5), (16, 5)))
        self.assertEqual(drop.back.pos(17, 0), (17, 0))
        add = self.make("T5", PY[:-1])
        self.assertEqual(apply_ops_text(PY[:-1], add.ops()), PY)
        self.assertEqual((add.shift.pos(16, 5), add.back.pos(17, 0)), ((16, 5), (16, 5)))
        k = QueryKey("foldingRange", "a.py")
        base, trans = snap({k: [[11, -1, 16, -1, ""]]}), snap({k: [[11, -1, 17, -1, ""]]})
        self.assertEqual(compare_mapped(base, trans, [k], add.shift, add.back), [])  # the new EOF line reads as EOF
        self.assertEqual(len(compare_mapped(base, snap({k: [[11, -1, 15, -1, ""]]}), [k], add.shift, add.back)), 1)
        span, whole = QueryKey("documentSymbol", "a.py"), [["m", 2, 0, 0, 16, 5]]
        self.assertEqual(compare_mapped(snap({span: whole}), snap({span: [["m", 2, 0, 0, 17, 0]]}), [span],
                                        add.shift, add.back), [])

    def test_t6_inline_comment(self) -> None:
        text = "package p\n\nfunc F() int { return helper(x) + other }\n"
        ft = FileTargets("a.go", ((2, 25), (2, 36)), ((2, 28), (2, 39)), ("helper", "other"))
        self.assertEqual(comment_spots(text, "go", ft), [(2, 22), (2, 34)])
        self.assertEqual(comment_spots(text, "python", ft), [])
        self.assertEqual(comment_spots(text, "typescript", FileTargets("a.tsx", ft.positions, ft.ends, ft.names)), [])
        hashed = "fn f() { let r#type = 1; }\n"
        self.assertEqual(comment_spots(hashed, "rust", FileTargets("a.rs", ((0, 17),), ((0, 19),), ("type",))), [])
        t6 = make_transform("T6", "a.go", text, "go", random.Random(1), ft)
        out = apply_ops_text(text, t6.ops())
        s = t6.shift
        self.assertEqual((s.n, s.w, len(INLINE.encode("utf-16-le")) // 2), (0, 11, 11))
        line = LineIndex(out).line_text(2)
        name_at = s.pos(*t6.edits[0][:2])
        self.assertTrue(line.encode("utf-16-le")[2 * name_at[1]:].decode("utf-16-le").startswith(("helper", "other")))
        self.assertEqual((s.pos(2, 3), s.rng([2, 0, 2, t6.edits[0][1]])), ((2, 3), [2, 0, 2, t6.edits[0][1]]))
        self.assertTrue(s.inserted(2, t6.edits[0][1], 2, t6.edits[0][1] + 10))
        self.assertFalse(s.inserted(*name_at, name_at[0], name_at[1] + 5))

    def test_plan_cases_and_key_targets(self) -> None:
        ctx = OracleContext("r", "pyright", "1", "p", self.root, "python", 5, self.targets, max_cases=7)
        cases = plan_cases(ctx)
        self.assertEqual(cases, plan_cases(ctx))
        self.assertEqual([c.kind for c in cases[:5]], ["T1", "T2", "T3", "T4", "T5"])  # T6: no block comments
        self.assertEqual(len(cases), 7)
        kt = key_targets(self.targets, QueryKey("completion", "b.py", 2, 5))
        self.assertEqual([(t.positions, t.ends) for t in kt], [((), ()), ((), ((2, 5),))])
        kd = key_targets(self.targets, QueryKey("diagnostics", "a.py"))
        self.assertTrue(all(not t.positions and not t.ends for t in kd))


if __name__ == "__main__":
    unittest.main()
