"""Unit tests for completion_kind.is_auto_import and its use in norm_completion.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from completion_kind import is_auto_import  # noqa: E402
from queries import NormContext, PathMapper, norm_completion  # noqa: E402

PYRIGHT_AUTO = {"label": "SCHED_OTHER", "kind": 21, "detail": "Auto-import", "labelDetails": {"description": "os"},
                "data": {"autoImportText": "from os import SCHED_OTHER"}, "sortText": "12.9999.SCHED_OTHER.02.os"}
TS7_AUTO = {"label": "setAutoFreeze", "labelDetails": {"description": "immer"}, "sortText": "16",
            "data": {"source": "immer", "autoImport": {"kind": 3}}}
TSLS_AUTO = {"label": "useState", "sortText": "16", "data": {"entryNames": [{"name": "useState", "source": "react"}]}}
GOPLS_AUTO = {"label": "template", "additionalTextEdits": [{"newText": "\"text/template\""}]}
RA_AUTO = {"label": "arc(use std::sync::Arc)", "data": {"imports": [{"full_import_path": "std::sync::Arc"}]}}
TSLS6_AUTO = {"label": "isArgumentsObject", "kind": 3, "sortText": "\uffff16", "data": {"cacheId": 1040},
              "detail": "node:util/types"}
TSLS6_DEPRECATED = {"label": "setupMaster", "sortText": "\uffffz16", "data": {"cacheId": 1140}, "tags": [1]}
LOCAL = [{"label": "po", "sortText": "09"}, {"label": "map", "data": {"imports": []}},
         {"label": "__dirname", "sortText": "15", "data": {"cacheId": 9}}, {"label": "old", "sortText": "\uffffz15"},
         {"label": "x", "labelDetails": {"description": "int"}, "sortText": "11"}]


class AutoImportTests(unittest.TestCase):
    def test_markers(self) -> None:
        for item in (PYRIGHT_AUTO, TS7_AUTO, TSLS_AUTO, GOPLS_AUTO, RA_AUTO, TSLS6_AUTO, TSLS6_DEPRECATED):
            self.assertTrue(is_auto_import(item), item["label"])
        for item in LOCAL:
            self.assertFalse(is_auto_import(item), item["label"])

    def test_normalizer_keeps_only_local_items(self) -> None:
        ctx = NormContext(PathMapper("/tmp"), completion_top=50)
        items = [PYRIGHT_AUTO, TS7_AUTO, GOPLS_AUTO] + LOCAL
        self.assertEqual(norm_completion({"items": items + [TSLS6_AUTO]}, ctx), ["__dirname", "map", "old", "po", "x"])


if __name__ == "__main__":
    unittest.main()
