"""Unit tests for the r4_edits and r6_crossimpl oracles: the syntax classifier (all four
languages), WorkspaceEdit application, snippet stripping, formatting no-op detection,
change ops and range mapping, completion item edits, quick-fix evaluation, R6
canonical forms (paths, hover, diagnostics, completion) and intended-difference tags.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import shutil
import sys
import unittest
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import Op, QueryKey, QueryResult, Snapshot  # noqa: E402
from ops import OpError, apply_change, inverse_change  # noqa: E402
from oracles import r6_intended as R6I  # noqa: E402
from oracles import syntax as S  # noqa: E402
from oracles.base import OracleContext, case_of  # noqa: E402
from oracles.r4_checks import Obs, change_norm, evaluate_quickfix  # noqa: E402
from oracles.r4_edits import EditValidity  # noqa: E402
from oracles.r4_textedits import (apply_text_edits, display_order, effective_edits, first_difference,  # noqa: E402
                                  format_options, fuzzy_match, is_noop, item_edits, map_range, minimal_change, nonws,
                                  strip_snippet, word_range, workspace_edit_texts)
from oracles.r6_crossimpl import canon_path, canonical, canonical_stable, is_auto_import, tslib_name  # noqa: E402


def E(sl: int, sc: int, el: int, ec: int, text: str) -> Dict[str, Any]:
    return {"range": {"start": {"line": sl, "character": sc}, "end": {"line": el, "character": ec}}, "newText": text}


def D(sl: int, sc: int, el: int, ec: int, code: Any, sev: int = 1, msg: str = "m") -> Dict[str, Any]:
    return dict(E(sl, sc, el, ec, ""), severity=sev, code=code, message=msg)


HAS_RUSTFMT = S.rustfmt_path() is not None


class AppliesTo(unittest.TestCase):
    def test_only_languages_with_lexical_rules(self) -> None:
        r4 = EditValidity()
        for kind in ("pyright", "ts6", "ts7", "tsserver", "rust-analyzer", "gopls"):
            self.assertTrue(r4.applies_to(kind), kind)
        self.assertFalse(r4.applies_to("jdtls"))  # no Java lexical rules: not applicable, not a failed run
        self.assertFalse(r4.applies_to(""))
HAS_GOFMT = shutil.which("gofmt") is not None
HAS_NODE = shutil.which("node") is not None and os.path.isdir(S.TS_PACKAGE)


class SyntaxTests(unittest.TestCase):
    def test_python(self) -> None:
        self.assertEqual(S.syntax_errors("python", "def f(a):\n    return a\n", "a.py"), [])
        self.assertTrue(S.syntax_errors("python", "def f(:\n", "a.py"))
        errs = S.syntax_errors("python", "import os\nfrom __future__ import annotations\n", "a.py")
        self.assertIn("__future__", errs[0])  # compile-time SyntaxError counts

    @unittest.skipUnless(HAS_GOFMT, "gofmt not installed")
    def test_go(self) -> None:
        self.assertEqual(S.syntax_errors("go", "package p\n\nfunc f() int { return 1 }\n", "a.go"), [])
        errs = S.syntax_errors("go", "package p\n\nfunc f() {\n\tx := \n}\n", "a.go")
        self.assertTrue(errs and errs[0].startswith("5:1: "))

    @unittest.skipUnless(HAS_RUSTFMT, "no working rustfmt")
    def test_rust(self) -> None:
        self.assertEqual(S.syntax_errors("rust", "fn main() {\n    let x = 1;\n}\n", "a.rs"), [])
        self.assertEqual(S.syntax_errors("rust", "fn main(){let   x=1;}\n", "a.rs"), [])  # formatting is not an error
        errs = S.syntax_errors("rust", "fn main() {\n    let x = ;\n}\n", "a.rs")
        self.assertTrue(errs and errs[0].startswith("2:"))

    @unittest.skipUnless(HAS_NODE, "node or the typescript package missing")
    def test_typescript_and_javascript(self) -> None:
        self.assertEqual(S.syntax_errors("typescript", "const x: number = 1;\n", "a.ts"), [])
        self.assertTrue(S.syntax_errors("typescript", "const x = ;\n", "a.ts")[0].startswith("1:11: TS1109"))
        jsx = "const a = <div>{x}</div>;\n"
        self.assertEqual(S.syntax_errors("typescript", jsx, "a.tsx"), [])
        self.assertTrue(S.syntax_errors("typescript", jsx, "a.ts"))  # the extension decides the script kind
        self.assertEqual(S.syntax_errors("javascript", "export default function f() {}\n", "a.js"), [])

    def test_unsupported_and_new_errors(self) -> None:
        self.assertEqual(S.syntax_errors("java", "class A {", "A.java"), [])
        self.assertFalse(S.supported("java"))
        self.assertEqual(S.new_errors(["3:1: expected x"], ["9:4: expected x", "9:9: other"]), ["9:9: other"])
        self.assertEqual(S.new_errors([], ["1:1: a", "1:1: a"]), ["1:1: a", "1:1: a"])


class WorkspaceEditTests(unittest.TestCase):
    TEXT = "abc\ndef\nghi\n"

    def test_simultaneous_edits_on_one_document(self) -> None:
        edits = [E(0, 0, 0, 1, "X"), E(1, 0, 1, 3, "YY"), E(0, 3, 0, 3, "1"), E(0, 3, 0, 3, "2"), E(2, 99, 2, 99, "!")]
        self.assertEqual(apply_text_edits(self.TEXT, edits), "Xbc12\nYY\nghi!\n")  # equal inserts keep array order
        self.assertEqual(apply_text_edits(self.TEXT, [E(9, 0, 9, 0, "END")]), self.TEXT + "END")  # clamped line
        with self.assertRaises(OpError):
            apply_text_edits(self.TEXT, [E(0, 0, 0, 2, "X"), E(0, 1, 0, 3, "Y")])

    def test_changes_document_changes_and_skips(self) -> None:
        docs = {"a.ts": self.TEXT, "b.ts": "x\n"}
        rel = lambda uri: uri.split("/ws/")[1] if "/ws/" in uri else None  # noqa: E731
        we = {"documentChanges": [
            {"textDocument": {"uri": "file:///ws/a.ts", "version": 3}, "edits": [E(0, 0, 0, 3, "ABC"), E(2, 0, 2, 3, "G")]},
            {"kind": "create", "uri": "file:///ws/new.ts"},
            {"textDocument": {"uri": "file:///ws/a.ts", "version": 4}, "edits": [E(0, 0, 0, 1, "Z")]},
            {"textDocument": {"uri": "file:///elsewhere/lib.d.ts", "version": 1}, "edits": [E(0, 0, 0, 0, "q")]}],
            "changes": {"file:///ws/b.ts": [E(0, 0, 0, 1, "ignored")]}}
        res = workspace_edit_texts([we], docs.get, rel)
        self.assertEqual(res.texts, {"a.ts": "ZBC\ndef\nG\n"})  # groups in order; documentChanges preferred
        self.assertEqual(res.skipped, ["create:file:///ws/new.ts", "outside:file:///elsewhere/lib.d.ts"])
        self.assertEqual(len(res.spans["a.ts"]), 1)  # two groups on one document: minimal-change span
        res2 = workspace_edit_texts([{"changes": {"file:///ws/b.ts": [E(0, 0, 0, 1, "y")]}},
                                     {"changes": {"file:///ws/b.ts": [E(0, 1, 0, 1, "!")]}}], docs.get, rel)
        self.assertEqual(res2.texts, {"b.ts": "y!\n"})  # several WorkspaceEdits apply in order
        self.assertEqual(workspace_edit_texts([{"changes": {"file:///ws/b.ts": [E(0, 0, 0, 1, "x")]}}],
                                              docs.get, rel).texts, {})  # no-op edit changes nothing

    def test_snippet_text_edit(self) -> None:
        edit = {"range": E(0, 0, 0, 0, "")["range"], "snippet": {"kind": "snippet", "value": "f(${1:a})$0"}}
        self.assertEqual(apply_text_edits("x", [edit]), "f(a)x")


class SnippetTests(unittest.TestCase):
    def test_strip(self) -> None:
        cases = {"foo(${1:a}, ${2:b})$0": "foo(a, b)", "${1:outer ${2:inner}}": "outer inner", "${1|one,two|}": "one",
                 "\\$x \\} $TM_FILENAME ${VAR:def} ${1}": "$x }  def ", "a${1/(.*)/$1/}b": "ab", "$": "$",
                 "x$1y": "xy", "plain": "plain"}
        for snippet, text in cases.items():
            self.assertEqual(strip_snippet(snippet), text, snippet)


class FormattingTests(unittest.TestCase):
    def test_noop_detection(self) -> None:
        text = "a  b\nc\n"
        self.assertTrue(is_noop(text, None) and is_noop(text, []))
        self.assertTrue(is_noop(text, [E(0, 0, 0, 1, "a"), E(1, 1, 1, 1, "")]))  # edits that rewrite the same text
        self.assertFalse(is_noop(text, [E(0, 1, 0, 3, " ")]))
        self.assertEqual(effective_edits(text, [E(0, 0, 0, 1, "a"), E(0, 1, 0, 3, " ")]), [[0, 1, 0, 3, " "]])

    def test_nonws_and_options(self) -> None:
        self.assertEqual(nonws("a  b\n\tc;"), "abc;")
        self.assertEqual(first_difference("abcdef", "abXdef", 2), ("abcd", "abXd"))
        self.assertEqual(format_options("function f() {\n  return 1\n}\n", "typescript"), {"tabSize": 2, "insertSpaces": True})
        self.assertEqual(format_options("def f():\n    return 1\n", "python"), {"tabSize": 4, "insertSpaces": True})
        self.assertEqual(format_options("func f() {\n\treturn\n}\n", "go"), {"tabSize": 4, "insertSpaces": False})


class ChangeOpTests(unittest.TestCase):
    def test_minimal_change_round_trip(self) -> None:
        for old, new in [("a\nb\nc\n", "a\nB\nc\n"), ("a\r\nb", "a\r\n\r\nb"), ("abc", "abXc"), ("a\rb", "a\r\nb"),
                         ("x = 1\n", ""), ("", "new\n")]:
            op = minimal_change("f", old, new)
            got = apply_change(old, op.start, op.end, op.text)[0]
            self.assertEqual(got, new)
            inv = inverse_change(op, old)
            self.assertEqual(apply_change(got, inv.start, inv.end, inv.text)[0], old)
        self.assertIsNone(minimal_change("f", "same", "same"))
        self.assertEqual(change_norm("f", "ab\n", "aXb\n"), ["f", 0, 1, 0, 1, "X", 1])

    def test_map_range(self) -> None:
        old = "line0\nline1 foo bar\nline2\n"
        res = workspace_edit_texts([{"changes": {"file:///w/a.py": [E(1, 6, 1, 9, "fooo"), E(0, 0, 0, 0, "import x\n")]}}],
                                   lambda p: old, lambda u: "a.py")
        new, spans = res.texts["a.py"], res.spans["a.py"]
        self.assertEqual(map_range(old, new, spans, (1, 6), (1, 9)), ((2, 6), (2, 10), True))  # touched: union
        self.assertEqual(map_range(old, new, spans, (2, 0), (2, 5)), ((3, 0), (3, 5), False))  # shifted
        self.assertEqual(map_range(old, new, spans, (0, 0), (0, 5)), ((1, 0), (1, 5), False))  # insert at start moves it
        self.assertEqual(map_range(old, new, spans, (1, 0), (1, 5)), ((2, 0), (2, 5), False))


class CompletionItemTests(unittest.TestCase):
    def test_display_order_and_edits(self) -> None:
        items = [{"label": "fooBar", "sortText": "2"}, {"label": "xfoo", "sortText": "1"}, {"label": "zzz", "sortText": "0"},
                 {"label": "FOO", "filterText": "foo", "sortText": "1"}]
        self.assertEqual([i["label"] for i in display_order(items, "foo")], ["FOO", "fooBar"])  # xfoo: no word start
        self.assertTrue(fuzzy_match("ss", "setState") and fuzzy_match("rea", "React"))
        self.assertFalse(fuzzy_match("from", "CSSTransformComponent") or fuzzy_match("React", "createRef"))
        gopls = {"label": "abcdef", "filterText": "untyped float(abcdef)"}  # gopls v0.13.2: a word starts after '('
        self.assertEqual(display_order([gopls], "abcd"), [gopls])
        self.assertTrue(fuzzy_match("x", "f(x)") and fuzzy_match("b", "a b") and fuzzy_match("v", "k:v"))
        word = word_range((3, 10), "foo")
        snippet = {"label": "foo", "insertText": "foo(${1:x})", "insertTextFormat": 2,
                   "additionalTextEdits": [E(0, 0, 0, 0, "import foo\n")]}
        self.assertEqual(item_edits(snippet, {}, word), [dict(E(3, 7, 3, 10, "foo(x)")), E(0, 0, 0, 0, "import foo\n")])
        replace = {"label": "f", "textEdit": {"insert": E(3, 7, 3, 10, "")["range"], "replace": E(3, 7, 3, 12, "")["range"],
                                              "newText": "fooz"}}
        self.assertEqual(item_edits(replace, {}, word), [E(3, 7, 3, 12, "fooz")])
        defaults = {"editRange": E(3, 8, 3, 10, "")["range"], "insertTextFormat": 2}
        self.assertEqual(item_edits({"label": "g", "textEditText": "g($1)"}, defaults, word), [E(3, 8, 3, 10, "g()")])


class QuickfixEvaluationTests(unittest.TestCase):
    def test_persisting_and_error_count(self) -> None:
        old = "x = foo\ny = 1\n"
        res = workspace_edit_texts([{"changes": {"file:///w/a.py": [E(0, 4, 0, 7, "food")]}}], lambda p: old, lambda u: "a.py")
        diag = D(0, 4, 0, 7, "undefined")
        base = {"a.py": [diag]}
        fixed = evaluate_quickfix(diag, "a.py", res, base, {"a.py": []})
        self.assertEqual((fixed["persist"], fixed["post_errors"]), ([], 0))
        still = evaluate_quickfix(diag, "a.py", res, base, {"a.py": [D(0, 4, 0, 8, "undefined")]})
        self.assertEqual(len(still["persist"]), 1)  # same code inside the mapped (touched) range
        worse = evaluate_quickfix(diag, "a.py", res, base, {"a.py": [D(1, 0, 1, 1, "other"), D(1, 2, 1, 3, "x")]})
        self.assertEqual((worse["persist"], worse["base_errors"], worse["post_errors"]), ([], 1, 2))
        hint = D(1, 0, 1, 1, None, sev=4, msg="not accessed")
        moved = evaluate_quickfix(hint, "a.py", res, {"a.py": [hint]}, {"a.py": [D(1, 0, 1, 1, None, sev=4, msg="not accessed")]})
        self.assertEqual(len(moved["persist"]), 1)  # no code: identified by message at the shifted range


class R1SuspectTests(unittest.TestCase):
    def test_filing(self) -> None:
        ctx = OracleContext("run1", "ts7", "7.0.2", "o/r@abc", "/nonexistent", "typescript", 1, ())
        hist = [Op("open", "a.ts"), Op("change", "a.ts", (0, 0), (0, 0), "x")]
        o = Obs("format", QueryKey("formatting", "a.ts"), [], ["a.ts", 0, 0, 0, 1, " ", 1], {"kind": "format", "path": "a.ts"},
                "second formatting edits", edited={"a.ts": "x"}, history=hist, open_paths=["a.ts"],
                running={"a.ts": ["a.ts", 0, 0, 0, 1, " ", 1]})
        v = EditValidity()._r1_suspects(ctx, o, {"a.ts": []})[0]
        self.assertEqual(case_of(v)["kind"], "r1-suspect")
        self.assertEqual((v.key, v.expected, len(v.ops)), (QueryKey("formatting", "a.ts"), [], 2))
        self.assertEqual(v.signature, "ts7|r4_edits|formatting:gained")
        self.assertEqual(EditValidity()._r1_suspects(ctx, o, {"a.ts": o.running["a.ts"]}), [])


class R6CanonicalTests(unittest.TestCase):
    def test_paths(self) -> None:
        ts6 = "/r/temp/lsp_servers/ts6-6.0.3/node_modules/typescript/lib/lib.es5.d.ts"
        ts7 = "/r/temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.es5.d.ts"
        self.assertEqual({canon_path(ts6), canon_path(ts7), canon_path("bundled:///libs/lib.es5.d.ts")},
                         {"<tslib>/lib.es5.d.ts"})
        self.assertEqual(canon_path("node_modules/typescript/lib/lib.dom.iterable.d.ts"), "<tslib>/lib.dom.iterable.d.ts")
        self.assertIsNone(tslib_name("src/lib.ts"))
        self.assertEqual(canon_path("node_modules/@types/react/index.d.ts"), "node_modules/@types/react/index.d.ts")

    def test_hover_and_diagnostics(self) -> None:
        k = QueryKey("hover", "a.ts", 1, 2)
        ts6 = {"contents": {"kind": "markdown", "value": "\n```typescript\n(alias) const c: C\nimport c\n```\nDocs."}}
        ts7 = {"contents": {"kind": "markdown", "value": "```typescript\n(alias) const c: C\n```\n"}}
        a = canonical(k, QueryResult(k, ["x", None], raw=ts6), "ts6")
        self.assertEqual(a, canonical(k, QueryResult(k, ["y", None], raw=ts7), "ts7"))
        self.assertEqual(a, "(alias) const c: C")
        fenced_default = {"contents": {"kind": "markdown", "value": "```ts\n(property) r?: boolean\n```\n*@default*\n```ts\nfalse\n```"}}
        self.assertEqual(canonical(k, QueryResult(k, ["z", None], raw=fenced_default), "ts6"), "(property) r?: boolean")
        dk = QueryKey("diagnostics", "a.ts")
        n1 = [[1, 2, 1, 5, 1, "2304", "typescript", "Cannot find name 'x'."]]
        n2 = [[1, 2, 1, 5, 2, "2304", "ts", "other words"]]
        self.assertEqual(canonical(dk, QueryResult(dk, n1), "ts6"), canonical(dk, QueryResult(dk, n2), "ts7"))
        err = QueryResult(dk, ["error", -32601], error=("error", -32601))
        self.assertEqual(canonical(dk, err, "ts7"), ["error", -32601])

    def test_completion_excludes_auto_imports(self) -> None:
        k = QueryKey("completion", "a.ts", 3, 4)
        raw = {"items": [{"label": "a", "sortText": "11"}, {"label": "b", "sortText": "\uffff16", "data": {"cacheId": 1}},
                         {"label": "c", "sortText": "\uffffz16", "data": {"cacheId": 2}}, {"label": "d", "sortText": "15"},
                         {"label": "e", "sortText": "16", "data": {"autoImport": {"name": "e"}}}]}
        self.assertEqual(canonical(k, QueryResult(k, ["a", "b", "c", "d", "e"], raw=raw), "ts6"), ["a", "d"])
        self.assertTrue(is_auto_import({"sortText": "\uffff16", "data": {"cacheId": 3}}))  # unresolved ts6 item
        self.assertFalse(is_auto_import({"sortText": "15"}) or is_auto_import({"sortText": "02.9999.x"}))

    def test_canonical_stability(self) -> None:
        k = QueryKey("hover", "a.ts", 1, 2)
        doc = lambda d: {"contents": {"kind": "markdown", "value": f"```ts\nconst c: C\n```\n{d}"}}  # noqa: E731
        b = Snapshot("b", "ts6-6.0.3", True, {k: QueryResult(k, ["c1", None], raw=doc("one"))})
        c = Snapshot("c", "ts6-6.0.3", True, {k: QueryResult(k, ["c2", None], raw=doc("two"))})
        self.assertEqual(canonical_stable(b, c, "ts6"), {k})  # documentation differs, the type text does not
        lost = Snapshot("c", "ts6-6.0.3", True, {k: QueryResult(k, ["error", "timeout"], error=("error", "timeout"))})
        self.assertEqual(canonical_stable(b, lost, "ts6"), set())
        self.assertEqual(canonical_stable(b, Snapshot("c", "x", False, dict(c.results)), "ts6"), set())

    def test_intended_difference_tags(self) -> None:
        js = "/** @param {number} x */\nfunction f(x) { return x; }\nf();\n"
        tags = R6I.tag(R6I.Candidate("diagnostics", "a.js", js, [2], ["2554"], None))
        self.assertIn("js-jsdoc", [t["rule"] for t in tags])
        conflict = R6I.tag(R6I.Candidate("diagnostics", "a.ts", "let a = 1;\nlet a = 2;\n", [1], ["2451"], True))
        self.assertEqual([t["rule"] for t in conflict], ["conflicts-under-skiplibcheck"])
        loose = R6I.tag(R6I.Candidate("diagnostics", "a.ts", "f();\n", [0], ["2554"], False))
        self.assertEqual([t["rule"] for t in loose], ["nonstrict-omitted-arguments"])
        self.assertEqual(R6I.tag(R6I.Candidate("hover", "a.ts", "const x = 1;\n", [0], [], True)), [])
        self.assertEqual(R6I.SOURCE["sha256"][:12], "4519ec0a9360")


if __name__ == "__main__":
    unittest.main()
