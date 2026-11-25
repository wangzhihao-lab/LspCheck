"""Unit tests for the seeded mutations of the r4_edits oracle (oracles/r4_mutations.py,
oracles/r4_lexical.py, oracles/r4_seeded.py): M1-M4 on Python, TypeScript, Go and Rust
snippets (the planned mutation parses and does what its kind says), import parsing,
created-diagnostic detection and the rule that replay ops must end with the recorded fix.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import Op, QueryKey  # noqa: E402
from oracles import syntax as S  # noqa: E402
from oracles.base import OracleContext  # noqa: E402
from oracles.r4_lexical import imports  # noqa: E402
from oracles.r4_mutations import GENERATORS, Mutation, plan_mutations  # noqa: E402
from oracles.r4_seeded import created_diagnostics, mutation_case_session, new_error_sites  # noqa: E402

SNIPPETS: Dict[str, str] = {
    "python": ("import os\nfrom typing import Any, Dict\n\n\ndef helper(value: int, scale: int) -> int:\n"
               "    return value * scale\n\n\ndef main(args: Dict[str, Any]) -> None:\n"
               "    total = helper(len(args), 2)\n    print(os.sep, total, helper(total, 3))\n"),
    "typescript": ("import { readConfig, writeConfig } from './config'\nimport path from 'path'\n\n"
                   "interface Point { x: number; y: number }\n\n"
                   "export function scale(p: Point, factor: number): Point {\n"
                   "  const q: Point = { x: p.x * factor, y: p.y * factor }\n  return q\n}\n\n"
                   "export function run(file: string): number {\n  const cfg = readConfig(path.join(file, 'x'))\n"
                   "  writeConfig(cfg, file)\n  return scale({ x: 1, y: 2 }, 3).x\n}\n"),
    "go": ("package main\n\nimport (\n\t\"fmt\"\n\t\"strings\"\n)\n\nfunc greet(name string, times int) string {\n"
           "\treturn strings.Repeat(name, times)\n}\n\nfunc main() {\n\tmessage := greet(\"a\", 2)\n"
           "\tfmt.Println(message, greet(message, 1))\n}\n"),
    "rust": ("use std::collections::{HashMap, HashSet};\n\nstruct Point {\n    x: i32,\n    y: i32,\n}\n\n"
             "fn make(scale: i32, offset: i32) -> Point {\n    let p = Point { x: scale, y: offset };\n    p\n}\n\n"
             "fn main() {\n    let mut seen: HashSet<i32> = HashSet::new();\n"
             "    let counts: HashMap<i32, i32> = HashMap::new();\n    let point = make(2, 3);\n"
             "    seen.insert(point.x + point.y);\n    println!(\"{} {}\", seen.len(), counts.len());\n}\n"),
}
PATHS = {"python": "a.py", "typescript": "a.ts", "go": "a.go", "rust": "a.rs"}
TOOLS = {"python": True, "typescript": shutil.which("node") is not None, "go": shutil.which("gofmt") is not None,
         "rust": S.rustfmt_path() is not None}


def whats(language: str, kind: str) -> str:
    text = SNIPPETS[language]
    return " | ".join(m.what for m in GENERATORS[kind](text, language))


class GeneratorTests(unittest.TestCase):
    def test_m1_removes_used_imports(self) -> None:
        self.assertIn("remove 'Any' from an import", whats("python", "M1"))
        self.assertIn("remove the import of 'os'", whats("python", "M1"))
        self.assertIn("remove 'readConfig' from an import", whats("typescript", "M1"))
        self.assertIn("remove 'fmt' from an import", whats("go", "M1"))
        self.assertIn("remove 'HashSet' from an import", whats("rust", "M1"))
        unused = "import os\nimport sys\n\nprint(sys.argv)\n"
        self.assertEqual([m.what for m in GENERATORS["M1"](unused, "python")], ["remove the import of 'sys'"])

    def test_m2_misspells_a_later_use(self) -> None:
        text = SNIPPETS["typescript"]
        for m in GENERATORS["M2"](text, "typescript"):
            old, new = text[m.start:m.end], m.text
            self.assertEqual(abs(len(old) - len(new)), 1)
            self.assertLess(text.index(old), m.start)  # never the first occurrence
            self.assertNotIn(new, text)
            self.assertNotEqual(text[m.start - 1], ".")  # never a member access
        self.assertNotIn("'from'", whats("typescript", "M2"))  # `from '...'` is a keyword position
        go = "package p\n\nfunc f(m map[string]bool) []string {\n\tvar out []string\n\tfor name, ok := range m {\n" \
             "\t\tif ok {\n\t\t\tout = append(out, name)\n\t\t}\n\t}\n\tname2, err := g()\n\tname2, err = g()\n" \
             "\t_ = err\n\treturn append(out, name2)\n}\n"
        targets = {go[m.start:m.end] + "@" + str(go.count("\n", 0, m.start)) for m in GENERATORS["M2"](go, "go")}
        self.assertIn("name@6", targets)  # the use in append
        self.assertIn("name2@12", targets)  # the use in the return
        self.assertNotIn("name2@10", targets)  # `name2, err = g()` assigns: not a use

    def test_m3_drops_last_argument_or_member(self) -> None:
        self.assertIn("drop the last argument of 'helper(...)'", whats("python", "M3"))
        self.assertIn("drop member x of a literal", whats("typescript", "M3"))
        self.assertIn("drop the last argument of 'greet(...)'", whats("go", "M3"))
        self.assertIn("drop member y of a literal", whats("rust", "M3"))
        self.assertEqual(whats("typescript", "M3").count("'scale(...)'"), 1)  # the call, not the declaration
        self.assertEqual(whats("python", "M3").count("'helper(...)'"), 2)  # two calls; `def helper(` is not one
        rs = SNIPPETS["rust"]
        drop = next(m for m in GENERATORS["M3"](rs, "rust") if m.what == "drop member y of a literal")
        self.assertIn("Point { x: scale }", drop.apply(rs))

    def test_m4_inserts_unused_bindings(self) -> None:
        for language, local, imported in (
                ("python", "    r4_unused = 0\n", "import sys as r4_unused\n"),
                ("typescript", "  const r4Unused = 0;\n", "import * as r4Unused from './config'\n"),
                ("go", "\tr4Unused := 0\n", '\tr4unused "fmt"\n'),
                ("rust", "    let r4_unused = 0;\n", "use std::fmt::Write as R4Unused;\n")):
            inserted = [m.text for m in GENERATORS["M4"](SNIPPETS[language], language)]
            self.assertIn(local, inserted, language)
            self.assertIn(imported, inserted, language)
        go_imp = [m for m in GENERATORS["M4"](SNIPPETS["go"], "go") if "import" in m.what][0]
        self.assertIn('\tr4unused "fmt"\n)', go_imp.apply(SNIPPETS["go"]))


class PlanTests(unittest.TestCase):
    def test_plans_parse_and_are_seeded(self) -> None:
        for language, text in SNIPPETS.items():
            if not TOOLS[language]:
                continue
            path = PATHS[language]
            plan = plan_mutations(text, language, path, 1, path)
            self.assertEqual([m.kind for m in plan], ["M1", "M2", "M3", "M4"], language)
            for m in plan:
                self.assertEqual(S.syntax_errors(language, m.apply(text), path), [], (language, m.what))
            self.assertEqual(plan, plan_mutations(text, language, path, 1, path))  # deterministic
        self.assertNotEqual([m.what for m in plan_mutations(SNIPPETS["python"], "python", "a.py", 1, "a.py")],
                            [m.what for m in plan_mutations(SNIPPETS["python"], "python", "a.py", 7, "a.py")])

    def test_mutation_op(self) -> None:
        text = "ab\ncd\n"
        op = Mutation("M2", "x", 3, 5, "cxd").op("f.py", text)
        self.assertEqual((op.start, op.end, op.text), ((1, 0), (1, 2), "cxd"))


class BudgetTests(unittest.TestCase):
    def test_seeded_cases_round_robin_by_kind(self) -> None:
        from oracles.r4_edits import _by_kind
        cases = [{"mutation": {"id": k}, "path": p} for p, ks in (("f1", "M2 M3 M4"), ("f2", "M1 M2 M3 M4"))
                 for k in ks.split()]
        order = [(c["mutation"]["id"], c["path"]) for c in _by_kind(cases)]
        self.assertEqual(order[:4], [("M1", "f2"), ("M2", "f1"), ("M3", "f1"), ("M4", "f1")])
        self.assertEqual(len(order), 7)


class LexicalTests(unittest.TestCase):
    def test_imports(self) -> None:
        ts = "import type {\n  A,\n  B as C,\n} from './x'\nimport D, { e } from \"y\";\nimport './side'\n"
        stmts = imports(ts, "js")
        self.assertEqual([[i.bound for i in s.items] for s in stmts], [["A", "C"], ["D", "e"]])
        self.assertEqual([s.spec for s in stmts], ["./x", "y"])
        rs = "use a::{b, c::{d, e}, f as g};\nuse super::*;\n"
        self.assertEqual([[i.bound for i in s.items] for s in imports(rs, "rs")], [["b", "g"], []])


class SeededTests(unittest.TestCase):
    def test_created_diagnostics(self) -> None:
        def d(line: int, code: str, sev: int = 1) -> Dict[str, object]:
            return {"range": {"start": {"line": line, "character": 0}, "end": {"line": line, "character": 1}},
                    "severity": sev, "code": code, "message": code}
        old, new = "a\nb\nc\n", "a\nX\nb\nc\n"  # a line inserted after line 0
        created = created_diagnostics([d(1, "E1")], [d(2, "E1"), d(1, "E9", 2), d(0, "E8")], old, new, [(2, 2, "X\n")])
        self.assertEqual([x["code"] for x in created], ["E8", "E9"])  # E1 only moved; errors first

    def test_new_error_sites(self) -> None:
        def d(line: int, code: object) -> Dict[str, object]:
            return {"range": {"start": {"line": line, "character": 0}, "end": {"line": line, "character": 1}},
                    "severity": 1, "code": code, "message": str(code)}
        old, new = "decl\nuse\n", "use\n"  # the fix removes line 0
        before = [d(1, 2552)]  # "did you mean" at the use
        after = [d(0, 2304), d(0, 9999)]  # re-coded at the same place, plus a new one there
        self.assertEqual(new_error_sites(before, after[:1], old, new, [(0, 5, "")]), [])  # same place: not introduced
        self.assertEqual(new_error_sites([], after[:1], old, new, [(0, 5, "")]), after[:1])
        # at the targeted diagnostic's own place a different error is introduced by the fix; the same one persisted
        self.assertEqual(new_error_sites(before, after[:1], old, new, [(0, 5, "")], target=before[0]), after[:1])
        self.assertEqual(new_error_sites(before, [d(0, 2552)], old, new, [(0, 5, "")], target=before[0]), [])

    def test_replay_needs_the_fix_at_the_end(self) -> None:
        ctx = OracleContext("r", "ts7", "7.0.2", "p", "/nonexistent", "typescript", 1, ())
        fix = Op("change", "a.ts", (0, 0), (0, 0), "import x\n")
        case = {"path": "a.ts", "n_fix_ops": 1, "fix_ops": [fix.to_json()]}
        ops = [Op("open", "a.ts"), Op("change", "a.ts", (1, 0), (1, 3), "")]
        self.assertEqual(mutation_case_session(ctx, case, ops, QueryKey("diagnostics", "a.ts"), None, "t"), (True, []))
        stored = json.loads(json.dumps(case))  # as read back from a results file: positions become lists
        self.assertEqual([Op.from_json(o) for o in stored["fix_ops"]], [fix])


if __name__ == "__main__":
    unittest.main()
