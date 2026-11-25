"""Unit tests for queries.py (normalizers, path mapping, the suite runner against a
fake session, snapshot JSON) and the snapshot comparison helpers in driver.py.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from driver import diff_keys, stability  # noqa: E402
from model import QueryKey, QueryResult, Snapshot  # noqa: E402
from queries import (  # noqa: E402
    NORMALIZERS, NormContext, PathMapper, QueryConfig, provider_enabled, run_suite, snapshot_from_json,
    snapshot_to_json,
)
from targets import FileTargets  # noqa: E402


def rng(sl: int, sc: int, el: int, ec: int) -> Dict[str, Any]:
    return {"start": {"line": sl, "character": sc}, "end": {"line": el, "character": ec}}


class NormTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp(prefix="norm-test-")
        os.makedirs(os.path.join(self.root, "Src"))
        open(os.path.join(self.root, "Src", "Main.ts"), "w").close()
        self.mapper = PathMapper(self.root)
        self.ctx = NormContext(self.mapper, ("variable", "function"), ("declaration", "readonly", "static"), 3)
        self.uri = "file://" + self.root + "/Src/Main.ts"

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def norm(self, method: str, result: Any) -> Any:
        out = NORMALIZERS[method](result, self.ctx)
        self.assertEqual(json.loads(json.dumps(out)), out, "normalized results must survive a JSON round trip")
        return out


class TestPathMapper(NormTestBase):
    def test_rel_restores_on_disk_case_and_decodes(self) -> None:
        lowered = "file://" + self.root.lower() + "/src/main.ts"
        self.assertEqual(self.mapper.rel(lowered), "Src/Main.ts")
        self.assertEqual(self.mapper.rel(self.uri.replace("/Src/", "/%53rc/")), "Src/Main.ts")
        self.assertEqual(self.mapper.rel("file:///opt/lib/lib.d.ts"), "/opt/lib/lib.d.ts")
        self.assertEqual(self.mapper.rel("bundled:///libs/lib.es5.d.ts"), "bundled:///libs/lib.es5.d.ts")

    def test_scrub_is_case_insensitive(self) -> None:
        text = f"Cannot find '{self.root}/a' nor '{self.root.upper()}/b'"
        self.assertEqual(self.mapper.scrub(text), "Cannot find '<ws>/a' nor '<ws>/b'")


class TestNormalizers(NormTestBase):
    def test_diagnostics_mixed_codes_sorted(self) -> None:
        diags = [{"range": rng(3, 0, 3, 4), "severity": 1, "code": 2322, "source": "ts", "message": "a\n  b"},
                 {"range": rng(1, 0, 1, 2), "severity": 2, "code": "E0061", "message": f"in {self.root}/x"},
                 {"range": rng(1, 0, 1, 2), "message": "no code", "data": {"volatile": 1}}]
        out = self.norm("diagnostics", {"kind": "full", "resultId": "7", "items": diags})
        self.assertEqual(out, [[1, 0, 1, 2, 0, "", "", "no code"], [1, 0, 1, 2, 2, "E0061", "", "in <ws>/x"],
                               [3, 0, 3, 4, 1, "2322", "ts", "a b"]])
        self.assertIsNone(self.norm("diagnostics", None))

    def test_hover_forms(self) -> None:
        md = {"contents": {"kind": "markdown", "value": "```ts\nconst  x:\n number\n```\n---\nDoc"}, "range": rng(0, 1, 0, 2)}
        self.assertEqual(self.norm("hover", md), ["const x: number --- Doc", [0, 1, 0, 2]])
        marked = {"contents": [{"language": "python", "value": "def f()"}, "text"]}
        self.assertEqual(self.norm("hover", marked), ["def f() text", None])
        self.assertIsNone(self.norm("hover", None))

    def test_locations_and_links(self) -> None:
        loc = {"uri": self.uri, "range": rng(1, 2, 1, 5)}
        link = {"targetUri": self.uri, "targetRange": rng(0, 0, 9, 0), "targetSelectionRange": rng(1, 2, 1, 5),
                "originSelectionRange": rng(7, 7, 7, 8)}
        self.assertEqual(self.norm("definition", loc), [["Src/Main.ts", 1, 2, 1, 5]])
        self.assertEqual(self.norm("definition", [link, loc]), [["Src/Main.ts", 1, 2, 1, 5]])
        self.assertEqual(self.norm("references", None), [])

    def test_highlights_default_kind(self) -> None:
        self.assertEqual(self.norm("documentHighlight", [{"range": rng(0, 0, 0, 1)}, {"range": rng(0, 0, 0, 1), "kind": 3}]),
                         [[0, 0, 0, 1, 1], [0, 0, 0, 1, 3]])

    def test_completion_top_by_sort_text(self) -> None:
        items = [{"label": "zeta", "sortText": "11", "data": 1}, {"label": "Alpha", "sortText": "15"},
                 {"label": "beta", "sortText": "11"}, {"label": "gamma"}, {"label": "delta", "sortText": "10"}]
        self.assertEqual(self.norm("completion", {"isIncomplete": False, "items": items}), ["beta", "delta", "zeta"])
        self.assertEqual(self.norm("completion", [{"label": "b"}, {"label": "a"}]), ["a", "b"])
        self.assertEqual(self.norm("completion", None), [])

    def test_signature_help(self) -> None:
        sigs = {"signatures": [{"label": "f(a)"}, {"label": "f(a,  b)"}], "activeSignature": 1}
        self.assertEqual(self.norm("signatureHelp", sigs), "f(a, b)")
        self.assertEqual(self.norm("signatureHelp", dict(sigs, activeSignature=9)), "f(a)")
        self.assertIsNone(self.norm("signatureHelp", {"signatures": []}))

    def test_code_actions_drop_data_and_ids(self) -> None:
        acts = [{"title": "Fix  it", "kind": "quickfix", "data": {"id": 99}, "command": {"arguments": [1]}},
                {"title": "Run", "command": "x.run", "arguments": [f"{self.root}/a"]}]
        self.assertEqual(self.norm("codeAction", acts), [["Fix it", "quickfix"], ["Run", "<command>"]])

    def test_document_symbols_flattened(self) -> None:
        tree = [{"name": "C", "kind": 5, "range": rng(0, 0, 9, 1), "selectionRange": rng(0, 6, 0, 7),
                 "children": [{"name": "m", "kind": 6, "range": rng(1, 2, 3, 3), "selectionRange": rng(1, 2, 1, 3)}]}]
        self.assertEqual(self.norm("documentSymbol", tree), [["C", 5, 0, 0, 9, 1], ["m", 6, 1, 2, 3, 3]])
        info = [{"name": "f", "kind": 12, "location": {"uri": self.uri, "range": rng(4, 0, 5, 0)}}]
        self.assertEqual(self.norm("documentSymbol", info), [["f", 12, 4, 0, 5, 0]])

    def test_semantic_tokens_decoded(self) -> None:
        data = [1, 4, 3, 0, 0b001, 0, 5, 2, 1, 0b110, 2, 1, 1, 7, 0b1000]
        out = self.norm("semanticTokens", {"resultId": "r1", "data": data})
        self.assertEqual(out, [[1, 4, 3, "variable", "declaration"], [1, 9, 2, "function", "readonly,static"],
                               [3, 1, 1, "7", "3"]])

    def test_inlay_hints_and_folding(self) -> None:
        hints = [{"position": {"line": 2, "character": 5}, "label": [{"value": ": "}, {"value": "number", "tooltip": "t"}]},
                 {"position": {"line": 0, "character": 1}, "label": "a:", "paddingRight": True}]
        self.assertEqual(self.norm("inlayHint", hints), [[0, 1, "a:"], [2, 5, ": number"]])
        folds = [{"startLine": 3, "endLine": 9, "kind": "imports"}, {"startLine": 0, "startCharacter": 4, "endLine": 2}]
        self.assertEqual(self.norm("foldingRange", folds), [[0, 4, 2, -1, ""], [3, -1, 9, -1, "imports"]])


class TestProviders(unittest.TestCase):
    def test_provider_enabled(self) -> None:
        none = lambda m: False  # noqa: E731
        caps = {"hoverProvider": True, "inlayHintProvider": {}, "definitionProvider": False,
                "semanticTokensProvider": {"legend": {}, "range": True}}
        self.assertTrue(provider_enabled(caps, none, "hover"))
        self.assertTrue(provider_enabled(caps, none, "inlayHint"))  # an empty options object means supported
        self.assertFalse(provider_enabled(caps, none, "definition"))
        self.assertFalse(provider_enabled(caps, none, "semanticTokens"))  # range only, no full
        self.assertTrue(provider_enabled(caps, lambda m: m == "textDocument/semanticTokens", "semanticTokens"))
        self.assertTrue(provider_enabled({}, none, "diagnostics"))


class FakeSession:
    """Answers every request from a table; unknown methods time out."""

    def __init__(self, root: str, answers: Dict[str, Any], supported: Optional[List[str]] = None) -> None:
        self.root, self.answers, self.supported = root, answers, supported
        self.calls: List[Tuple[str, Any]] = []

    def request(self, method: str, params: Any, timeout: float) -> Tuple[Any, Optional[Tuple[str, Any]]]:
        self.calls.append((method, params))
        ans = self.answers.get(method, ("error", "timeout"))
        return (None, ans) if isinstance(ans, tuple) else (ans, None)

    def uri(self, path: str) -> str:
        return "file://" + os.path.join(self.root, path)

    def text(self, path: str) -> str:
        return "let a = 1;\nlet b = a;\n"

    def supports(self, method: str) -> bool:
        return self.supported is None or method in self.supported

    def diagnostics(self, path: str, timeout: float) -> Tuple[Any, Optional[Tuple[str, Any]]]:
        return [{"range": rng(0, 4, 0, 5), "message": "unused"}], None

    def norm_context(self, completion_top: int) -> NormContext:
        return NormContext(PathMapper(self.root), completion_top=completion_top)


class TestSuite(unittest.TestCase):
    TARGETS = (FileTargets("a.ts", ((0, 4), (1, 8)), ((0, 5), (1, 9)), ("a", "a")),)

    def test_keys_errors_and_code_action_contexts(self) -> None:
        answers = {"textDocument/hover": {"contents": "x"}, "textDocument/definition": ("error", -32603),
                   "textDocument/codeAction": [], "textDocument/completion": {"items": [{"label": "a"}]}}
        sess = FakeSession("/w", answers, ["hover", "definition", "codeAction", "completion", "diagnostics"])
        results, stats = run_suite(sess, self.TARGETS, QueryConfig())
        self.assertEqual(results[QueryKey("definition", "a.ts", 0, 4)].norm, ["error", -32603])
        self.assertEqual(results[QueryKey("definition", "a.ts", 0, 4)].error, ("error", -32603))
        self.assertEqual(results[QueryKey("completion", "a.ts", 1, 9)].norm, ["a"])
        self.assertIn(QueryKey("codeAction", "a.ts", 0, 4, "diag:0:5"), results)
        pos_action = [p for m, p in sess.calls if m == "textDocument/codeAction" and p["range"]["start"]["line"] == 1]
        self.assertEqual(pos_action[0]["context"]["diagnostics"], [])  # the diagnostic is not at (1, 8)
        self.assertEqual(stats.errors, {"definition": 2})
        self.assertIn("references", stats.unsupported)
        self.assertFalse(stats.tripped)

    def test_timeouts_trip_the_suite(self) -> None:
        results, stats = run_suite(FakeSession("/w", {}), self.TARGETS, QueryConfig(max_timeouts=2))
        self.assertTrue(stats.tripped)
        self.assertEqual(stats.timeouts, 2)
        self.assertEqual(sum(1 for r in results.values() if r.error), 2)


class TestSnapshots(unittest.TestCase):
    def snap(self, label: str, hover: Any, extra: bool = False) -> Snapshot:
        results = {QueryKey("hover", "a.ts", 0, 1): QueryResult(QueryKey("hover", "a.ts", 0, 1), hover),
                   QueryKey("definition", "a.ts", 0, 1): QueryResult(QueryKey("definition", "a.ts", 0, 1), [["a.ts", 0, 0, 0, 1]])}
        if extra:
            k = QueryKey("hover", "a.ts", 2, 2)
            results[k] = QueryResult(k, ["error", "timeout"], error=("error", "timeout"))
        return Snapshot(label, "ts7-7.0.2", True, results, "sha")

    def test_json_round_trip_and_diff(self) -> None:
        a = self.snap("a", ["x", [0, 0, 0, 1]], extra=True)
        b = snapshot_from_json(json.loads(json.dumps(snapshot_to_json(a))))
        self.assertEqual(diff_keys(a, b), [])
        self.assertEqual(b.results[QueryKey("hover", "a.ts", 2, 2)].error, ("error", "timeout"))
        c = self.snap("c", ["y", [0, 0, 0, 1]])
        self.assertEqual(diff_keys(a, c), [QueryKey("hover", "a.ts", 0, 1), QueryKey("hover", "a.ts", 2, 2)])
        st = stability(a, c)
        self.assertEqual(st["hover"], {"keys": 2, "equal": 0, "share": 0.0})
        self.assertEqual(st["definition"]["share"], 1.0)


if __name__ == "__main__":
    unittest.main()
