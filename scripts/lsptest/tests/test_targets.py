"""Unit tests for targets.py: the identifier tokenizer per language (comments and
strings skipped, keywords excluded), UTF-16 positions, deterministic seeded
selection, file discovery and diagnostic ranges.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from targets import (  # noqa: E402
    TargetConfig, choose_targets, diagnostic_ranges, file_targets, identifiers, source_files, targets_from_json,
    targets_to_json,
)


def names(text: str, language: str) -> List[str]:
    return [t.text for t in identifiers(text, language)]


class TestTokenizer(unittest.TestCase):
    def test_typescript(self) -> None:
        src = ('const a = "b c"; // d e\n/* f\n g */ let h = `i ${j + k({ l })} m ${n}`;\n'
               "const re = /o [/] p/g; x / y; const q = 'r\\' s';\n<T,>(u: string) => u;\n")
        self.assertEqual(names(src, "typescript"), ["a", "h", "j", "k", "l", "n", "re", "x", "y", "q", "T", "u", "u"])

    def test_typescript_unterminated_quote_stops_at_line_end(self) -> None:
        self.assertEqual(names("<p>don't</p>\nconst z = 1;\n", "typescriptreact")[-1], "z")

    def test_python(self) -> None:
        src = ('def f(a):\n    s = "x y"  # c d\n    t = """z\n  w""" + rb\'q\' + f"{v}"\n'
               "    u = r'\\'' ; match = 1\n    return a + fx\n")
        self.assertEqual(names(src, "python"), ["f", "a", "s", "t", "u", "match", "a", "fx"])

    def test_rust(self) -> None:
        src = ('fn main() { let s = r#"raw "x" y"#; let c = \'z\'; let e = \'\\n\'; let l: &\'a str = "q";\n'
               "/* outer /* inner */ still */ let r#type = b'x'; 'outer: loop { break 'outer; } v.len() }\n")
        self.assertEqual(names(src, "rust"), ["main", "s", "c", "e", "l", "str", "type", "v", "len"])

    def test_go(self) -> None:
        src = "package p\nfunc F() { s := `raw\nx`; r := 'y'; t := \"q w\" // c\n\tg.Do(s) }\n"
        self.assertEqual(names(src, "go"), ["p", "F", "s", "r", "t", "g", "Do", "s"])

    def test_unknown_language(self) -> None:
        with self.assertRaises(ValueError):
            identifiers("x", "cobol")


class TestSelection(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp(prefix="targets-test-")
        body = "\n".join(f"let v{i} = w{i} + x{i};" for i in range(20)) + "\n"
        files = {"src/a.ts": body, "src/b.ts": body, "src/c.tsx": body, "src/tiny.ts": "let q = 1;\n",
                 "src/types.d.ts": body, "node_modules/m/index.ts": body, ".hidden/h.ts": body, "README.md": body}
        for rel, text in files.items():
            os.makedirs(os.path.dirname(os.path.join(self.root, rel)), exist_ok=True)
            with open(os.path.join(self.root, rel), "w", encoding="utf-8") as f:
                f.write(text)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_source_files_skip_excluded(self) -> None:
        self.assertEqual(source_files(self.root, "typescript"), ["src/a.ts", "src/b.ts", "src/c.tsx", "src/tiny.ts"])

    def test_choice_is_deterministic_and_filtered(self) -> None:
        cfg = TargetConfig(seed=3, max_files=2, max_positions_per_file=5)
        first = choose_targets(self.root, "typescript", cfg)
        self.assertEqual(first, choose_targets(self.root, "typescript", cfg))
        self.assertEqual(len(first), 2)
        self.assertNotIn("src/tiny.ts", [f.path for f in first])  # too few identifiers
        self.assertTrue(all(len(f.positions) == 5 == len(f.ends) == len(f.names) for f in first))
        seeds = {tuple(f.path for f in choose_targets(self.root, "typescript", TargetConfig(seed=s, max_files=1)))
                 for s in range(12)}
        self.assertGreater(len(seeds), 1)

    def test_positions_depend_only_on_seed_and_path(self) -> None:
        text = "let alpha = beta + gamma;\n" * 5
        a = file_targets("x.ts", text, "typescript", 9, 4)
        self.assertEqual(a, file_targets("x.ts", text, "typescript", 9, 4))
        self.assertNotEqual(a.positions, file_targets("y.ts", text, "typescript", 9, 4).positions)

    def test_positions_are_utf16(self) -> None:
        ft = file_targets("u.ts", "const s = '\U0001F600'; let zz = 1;\n", "typescript", 0, 5)
        self.assertEqual(ft.names, ("s", "zz"))
        self.assertEqual(ft.positions[1], (0, 21))  # the emoji counts two UTF-16 units (20 code points)
        self.assertEqual(ft.ends[1], (0, 22))

    def test_json_round_trip(self) -> None:
        chosen = choose_targets(self.root, "typescript", TargetConfig(seed=1))
        self.assertEqual(targets_from_json(targets_to_json(chosen)), chosen)


class TestDiagnosticRanges(unittest.TestCase):
    def test_dedup_sort_cap(self) -> None:
        def d(sl: int, sc: int, el: int, ec: int) -> dict:
            return {"range": {"start": {"line": sl, "character": sc}, "end": {"line": el, "character": ec}}}
        diags = [d(5, 0, 5, 3), d(1, 2, 1, 4), d(5, 0, 5, 3), d(0, 0, 0, 1), "junk"]
        self.assertEqual(diagnostic_ranges(diags), [(0, 0, 0, 1), (1, 2, 1, 4), (5, 0, 5, 3)])
        self.assertEqual(diagnostic_ranges(diags, limit=2), [(0, 0, 0, 1), (1, 2, 1, 4)])
        self.assertEqual(diagnostic_ranges(None), [])


if __name__ == "__main__":
    unittest.main()
