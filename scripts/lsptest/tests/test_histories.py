"""Unit tests for histories.py and history_sites.py: every family ends at the original
content (final_state(...).empty(), settings back at their effective values), every op
applies through the real OpApplier against a fake client, histories are deterministic by
seed, race delays are carried by every op, chains of histories stay round trips, and the
edit-site helpers (line classes, retyping, configuration variants, dependencies) behave.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import random
import shutil
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from histories import (  # noqa: E402
    FAMILY_ORDER, HISTORY_FAMILIES, HistoryConfig, build_workspace, generate, generate_many, interleave, prelude,
    round_trip,
)
from history_sites import (  # noqa: E402
    SETTING_TOGGLES, classify_lines, config_variant, dependency_files, fix_requests, nested, pick_line, retype_ops,
)
from model import Op  # noqa: E402
from oracles.base import final_state  # noqa: E402
from ops import DocumentStore, OpApplier, read_text  # noqa: E402

PY_MAIN = ("from pkg.util import helper, CONST\nimport sys\n\n\nclass Main:\n    def run(self) -> int:\n"
           "        return helper(CONST)\n\n\ndef entry() -> None:\n    sys.exit(Main().run())\n")
PY_CRLF = "import os\r\n\r\nNAME = 'café \U0001d518'\r\n\r\n\r\ndef f(x):\r\n    return os.path.join(NAME, x)\r\n"
PROJECTS: Dict[str, Tuple[str, Dict[str, str], Tuple[str, ...]]] = {
    "python": ("pyright", {
        "pkg/__init__.py": "", "pkg/main.py": PY_MAIN, "pkg/crlf.py": PY_CRLF,
        "pkg/util.py": "import os\n\n\ndef helper(x: int) -> int:\n    return x + 1\n\n\nCONST = 3\n",
        "pyproject.toml": '[project]\nname = "demo"\n\n[tool.pyright]\ntypeCheckingMode = "basic"\n'},
        ("pkg/crlf.py", "pkg/main.py")),
    "typescript": ("ts7", {
        "src/a.ts": ("import { b } from './b';\nimport type { T } from './types';\n\nexport function f(x: T): number {\n"
                     "  return b(x) + 1;\n}\n\nexport const k = f({ v: 1 });\n"),
        "src/b.ts": "export function b(t: { v: number }): number {\n  return t.v;\n}\n",
        "src/types.ts": "export interface T { v: number }\n",
        "tsconfig.json": '{\n  "compilerOptions": {\n    "strict": true\n  }\n}\n'}, ("src/a.ts",)),
    "go": ("gopls", {
        "go.mod": "module example.com/demo\n\ngo 1.22\n",
        "a.go": ('package demo\n\nimport (\n\t"fmt"\n\t"strings"\n)\n\nfunc A(s string) string {\n'
                 "\treturn fmt.Sprint(strings.ToUpper(s), B())\n}\n"),
        "b.go": "package demo\n\nfunc B() int { return 1 }\n"}, ("a.go",)),
    "rust": ("rust-analyzer", {
        "Cargo.toml": '[package]\nname = "demo"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n',
        "src/lib.rs": "mod util;\nuse util::helper;\n\npub fn run() -> i32 {\n    helper(2)\n}\n",
        "src/util.rs": "pub fn helper(x: i32) -> i32 {\n    x * 2\n}\n"}, ("src/lib.rs",)),
    "java": ("jdtls", {
        ".classpath": ('<?xml version="1.0" encoding="UTF-8"?>\n<classpath>\n  <classpathentry kind="src" path="src"/>\n'
                       "</classpath>\n"),
        "src/app/Main.java": ("package app;\n\nimport extra.Support;\n\npublic class Main {\n"
                              "    public static void main(String[] args) {\n        System.out.println(Support.name());\n"
                              "    }\n}\n"),
        "extra/extra/Support.java": 'package extra;\n\npublic class Support {\n    static String name() { return "s"; }\n}\n'},
        ("src/app/Main.java",)),
}


class FakeClient:
    """Accepts every notification and request the OpApplier sends."""

    def __init__(self) -> None:
        self.sent: List[Tuple[str, Any]] = []
        self.notifications: List[Any] = []
        self.server_capabilities: Dict[str, Any] = {"workspace": {"fileOperations": {"willRename": {}, "didRename": {}}}}
        self.settings: Dict[str, Any] = {}

    def notify(self, method: str, params: Any = None) -> None:
        self.sent.append((method, params))

    def request(self, method: str, params: Any = None, timeout: float = 0.0) -> Any:
        self.sent.append((method, params))
        return None

    def notification_count(self) -> int:
        return len(self.notifications)


def write_tree(root: str, files: Dict[str, str]) -> None:
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)


def toggle_defaults(kind: str) -> Dict[str, Any]:
    """Settings that hold every toggle's default, so H4 restores values that are already present."""
    return nested([(p, tg.default) for tg in SETTING_TOGGLES.get(kind, ()) for p in tg.paths])


class ProjectCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="histories-test-")
        self.roots: Dict[str, str] = {}
        for lang, (_, files, _) in PROJECTS.items():
            self.roots[lang] = os.path.join(self.tmp, lang)
            write_tree(self.roots[lang], files)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def workspace(self, lang: str, kind: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> Any:
        k, files, targets = PROJECTS[lang]
        kind = kind or k
        positions = {t: [(0, 1), (len(files[t].splitlines()) - 1, 0)] for t in targets}  # like targets.FileTargets
        return build_workspace(self.roots[lang], targets, lang, kind, toggle_defaults(kind) if settings is None else settings,
                               positions)

    def replay(self, lang: str, ops: List[Op]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Apply ops with the real OpApplier on a copy; returns (disk texts, open buffer texts)."""
        root = os.path.join(self.tmp, "replay")
        shutil.rmtree(root, ignore_errors=True)
        shutil.copytree(self.roots[lang], root)
        store = DocumentStore(root)
        applier = OpApplier(FakeClient(), store, sleep=lambda s: None)
        for op in ops:
            applier.apply(op)
        disk = {}
        for dirpath, _, names in os.walk(root):
            for n in names:
                disk[os.path.relpath(os.path.join(dirpath, n), root)] = read_text(os.path.join(dirpath, n))
        return disk, {p: store.docs[p].text for p in store.open_paths()}


class RoundTripTests(ProjectCase):
    def test_every_family_ends_at_the_original_content(self) -> None:
        for lang in PROJECTS:
            ws = self.workspace(lang)
            for family in FAMILY_ORDER:
                for seed in range(8):
                    h = generate(family, ws, HistoryConfig(), seed)
                    if h is None:
                        continue
                    with self.subTest(lang=lang, family=family, seed=seed, note=h.note):
                        st = final_state(ws.root, h.ops)
                        self.assertEqual(st.files, {})
                        self.assertTrue(round_trip(st, ws.settings))
                        if not any(op.kind == "set_config" for op in h.ops):
                            self.assertTrue(st.empty())
                        disk, bufs = self.replay(lang, h.ops)
                        self.assertEqual(disk, PROJECTS[lang][1])
                        self.assertEqual(set(bufs), set(ws.targets))
                        self.assertTrue(all(bufs[p] == PROJECTS[lang][1][p] for p in bufs))

    def test_every_family_applies_somewhere(self) -> None:
        seen = {f: 0 for f in FAMILY_ORDER}
        for lang in PROJECTS:
            ws = self.workspace(lang)
            for family in FAMILY_ORDER:
                seen[family] += sum(generate(family, ws, HistoryConfig(), s) is not None for s in range(4))
        self.assertTrue(all(n > 0 for n in seen.values()), seen)

    def test_chain_of_histories_is_a_round_trip_after_every_step(self) -> None:
        for lang in PROJECTS:
            ws = self.workspace(lang)
            hs = generate_many(ws, HistoryConfig(), 5, 10)
            ops = list(prelude(ws, HistoryConfig()))
            for h in hs:
                ops += list(h.body)
                with self.subTest(lang=lang, family=h.family):
                    self.assertTrue(round_trip(final_state(ws.root, ops), ws.settings))
            disk, _ = self.replay(lang, ops)
            self.assertEqual(disk, PROJECTS[lang][1])

    def test_toggle_restores_effective_value_even_when_absent(self) -> None:
        ws = self.workspace("go", settings={})
        for seed in range(12):
            h = generate("H4", ws, HistoryConfig(), seed)
            st = final_state(ws.root, h.ops)  # type: ignore[union-attr]
            self.assertEqual(st.files, {})
            self.assertTrue(round_trip(st, toggle_defaults("gopls")))
        ts6 = self.workspace("typescript", kind="ts6")
        ops = [op for s in range(12) for op in generate("H4", ts6, HistoryConfig(), s).body]  # type: ignore[union-attr]
        self.assertTrue(all(op.kind == "set_config" and op.settings for op in ops))


class DeterminismTests(ProjectCase):
    def test_same_seed_same_ops_and_different_seeds_differ(self) -> None:
        for lang in PROJECTS:
            a = [[o.to_json() for o in h.ops] for h in generate_many(self.workspace(lang), HistoryConfig(), 3, 9)]
            b = [[o.to_json() for o in h.ops] for h in generate_many(self.workspace(lang), HistoryConfig(), 3, 9)]
            c = [[o.to_json() for o in h.ops] for h in generate_many(self.workspace(lang), HistoryConfig(), 4, 9)]
            self.assertEqual(a, b)
            self.assertNotEqual(a, c)

    def test_round_robin_covers_families(self) -> None:
        hs = generate_many(self.workspace("python"), HistoryConfig(), 1, 14)
        self.assertEqual(len(hs), 14)
        self.assertEqual({h.family for h in hs}, set(FAMILY_ORDER))

    def test_race_delay_on_every_op(self) -> None:
        for delay in (0, 50, 200):
            for h in generate_many(self.workspace("typescript"), HistoryConfig(delay_ms=delay), 2, 14):
                self.assertTrue(all(op.delay_ms == delay for op in h.ops), (delay, h.family))


class SiteTests(ProjectCase):
    def test_line_classes_and_weights(self) -> None:
        self.assertEqual(classify_lines(PY_MAIN, "python")[:6], ["import", "import", "blank", "blank", "decl", "code"])
        go = PROJECTS["go"][1]["a.go"]
        self.assertEqual(classify_lines(go, "go")[2:7], ["import", "import", "import", "import", "blank"])
        rng, cfg = random.Random(1), HistoryConfig(import_weight=1000.0)
        picks = [pick_line(rng, PY_MAIN, "python", cfg) for _ in range(50)]
        self.assertGreater(sum(p in (0, 1) for p in picks), 45)
        self.assertNotIn(2, [pick_line(rng, PY_MAIN, "python", HistoryConfig()) for _ in range(200)])

    def test_retype_restores_the_line(self) -> None:
        for seed in range(20):
            rng = random.Random(seed)
            ops, k = retype_ops(rng, "pkg/crlf.py", PY_CRLF, 2, HistoryConfig(chunk_counts=(1, 2, 4)))
            self.assertEqual(len(ops), k + 1)
            self.assertEqual(ops[0].text, "")
            self.assertEqual("".join(o.text for o in ops[1:]), "NAME = 'café \U0001d518'\r\n")

    def test_config_variant_deletes_or_duplicates_one_line(self) -> None:
        text = PROJECTS["java"][1][".classpath"]
        kinds = set()
        for seed in range(20):
            variant, what = config_variant(random.Random(seed), text)
            kinds.add(what.split()[-1])
            self.assertIn(abs(len(variant.splitlines()) - len(text.splitlines())), (1,))  # type: ignore[union-attr]
        self.assertEqual(kinds, {"deleted", "duplicated"})

    def test_dependencies_and_configs(self) -> None:
        self.assertEqual(dependency_files(self.roots["java"], ["src/app/Main.java"], "java"), ("extra/extra/Support.java",))
        self.assertEqual(dependency_files(self.roots["rust"], ["src/lib.rs"], "rust"), ("src/util.rs",))
        self.assertIn("src/b.ts", dependency_files(self.roots["typescript"], ["src/a.ts"], "typescript"))
        self.assertEqual(self.workspace("java").configs, (".classpath",))
        self.assertEqual(self.workspace("go").deps, ("b.go",))

    def test_interleave_preserves_each_part(self) -> None:
        parts = [[Op("wait", f"a{i}") for i in range(3)], [Op("wait", f"b{i}") for i in range(2)],
                 [Op("wait", f"c{i}") for i in range(2)]]
        modes = set()
        for seed in range(30):
            ops, how = interleave(random.Random(seed), parts)
            modes.add(how.split()[0])
            self.assertEqual(sorted(o.path for o in ops), sorted(o.path for p in parts for o in p))
            for p in parts:
                self.assertEqual([o.path for o in ops if o.path[0] == p[0].path[0]], [o.path for o in p])
        self.assertEqual(modes, {"nest", "shuffle"})

    def test_registry(self) -> None:
        self.assertEqual(sorted(HISTORY_FAMILIES), sorted(FAMILY_ORDER))


class QueryOrderTests(ProjectCase):
    def test_h8_requests_are_valid_shuffled_and_content_neutral(self) -> None:
        methods, after_edit = set(), 0
        for lang in PROJECTS:
            ws = self.workspace(lang)
            for seed in range(10):
                h = generate("H8", ws, HistoryConfig(), seed)
                reqs = [o for o in h.body if o.kind == "request"]  # type: ignore[union-attr]
                self.assertGreaterEqual(len(reqs), 1)
                methods.update(o.text for o in reqs)
                after_edit += int(h.body[0].kind == "change")  # type: ignore[union-attr]
                self.assertTrue(final_state(ws.root, h.ops).empty())  # type: ignore[union-attr]
                self.replay(lang, h.ops)  # type: ignore[union-attr]  (OpApplier validates every position)
        self.assertGreater(len(methods), 4)
        self.assertTrue(0 < after_edit < 50)

    def test_requests_follow_the_code_through_edits(self) -> None:
        text = {"a.py": "x = 1\ny = x\nz = y\n"}
        ops = [Op("change", "a.py", (0, 0), (0, 0), "# c\n# d\n"), Op("request", "a.py", (1, 4), text="hover"),
               Op("change", "a.py", (0, 0), (2, 0), ""), Op("request", "a.py", (2, 4), text="hover"),
               Op("close", "a.py"), Op("request", "a.py", (1, 4), text="hover"), Op("open", "a.py"),
               Op("request", "a.py", (9, 9), text="hover"), Op("request", "a.py", (0, 0), text="definition")]
        out = fix_requests(ops, text.get, ["a.py"])
        self.assertEqual([(o.kind, o.start) for o in out if o.kind != "change"],
                         [("request", (3, 4)), ("request", (2, 4)), ("close", None), ("open", None), ("request", (0, 0))])

    def test_h9_keeps_the_workspace_change_around_the_document_changes(self) -> None:
        kinds = set()
        for lang in PROJECTS:
            ws = self.workspace(lang)
            for seed in range(12):
                h = generate("H9", ws, HistoryConfig(), seed)
                if h is None:
                    continue
                body, first = list(h.body), h.body[0]  # type: ignore[union-attr]
                kinds.add("rename" if first.kind == "fs_rename" else "dep-editor" if first.kind == "open" else
                          "config" if first.path in ws.configs else "dep-disk")
                w_files = {o.path for o in body[:1]} | {o.new_path for o in body[:1] if o.new_path}
                first_doc = next(i for i, o in enumerate(body) if o.path in ws.targets and o.path not in w_files
                                 and o.kind != "fs_rename")
                last_doc = max(i for i, o in enumerate(body) if o.path in ws.targets and o.path not in w_files)
                self.assertTrue(all(o.path in w_files or o.kind in ("open", "change", "save") for o in body[:first_doc]))
                self.assertTrue(all(o.path in w_files or o.kind in ("change", "save", "close")
                                    for o in body[last_doc + 1:]), h.note)
                touched = {o.path for o in body[first_doc:last_doc + 1] if o.path in ws.targets}
                self.assertEqual(touched, set(ws.targets) - w_files, h.note)
        self.assertEqual(kinds, {"config", "dep-disk", "dep-editor", "rename"})

    def test_h7_interleaves_requests_validly(self) -> None:
        with_requests = 0
        for lang in PROJECTS:
            ws = self.workspace(lang)
            for seed in range(20):
                h = generate("H7", ws, HistoryConfig(), seed)
                if h is None:
                    continue
                with_requests += int(any(o.kind == "request" for o in h.body))
                self.replay(lang, h.ops)
                self.assertTrue(round_trip(final_state(ws.root, h.ops), ws.settings))
        self.assertGreater(with_requests, 0)


if __name__ == "__main__":
    unittest.main()
