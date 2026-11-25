"""Unit tests for the corpus probe (scripts/lsptest/corpus/).

Push-mode publishes must be matched to the documents the probe opened by decoded,
case-folded path (settle.uri_key): typescript-language-server publishes
app/api/[provider]/[...path]/route.ts as app/api/%5Bprovider%5D/%5B...path%5D/route.ts,
and an exact string comparison made the probe wait out its whole cap on such a file.
A --skip-probe rerun must keep completed probe records instead of replacing them.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corpus.common import ProjectSpec  # noqa: E402
from corpus.probe_settle import final_diagnostics_summary, published_diagnostics, wait_push_settle  # noqa: E402
from corpus.records import ProbeOptions, probe_units, unit_key  # noqa: E402
from framing import Notification  # noqa: E402  (lsp_repro is on the path once corpus is imported)

ROOT = "/w/temp/corpus_probe/NextChat__defdcdb55d85__ts6-6.0.3"
PLAIN = f"file://{ROOT}/app/api/302ai.ts"
BRACKETED = f"file://{ROOT}/app/api/[provider]/[...path]/route.ts"
BRACKETED_AS_PUBLISHED = f"file://{ROOT}/app/api/%5Bprovider%5D/%5B...path%5D/route.ts"
DIAG = {"range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
        "severity": 1, "code": 2307, "message": "Cannot find module 'x'"}


def publish(uri: str, diagnostics: List[Dict[str, Any]]) -> Notification:
    return Notification("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": diagnostics})


class FakeClient:
    """The part of LspClient the push-mode helpers use; the server is always quiet."""

    def __init__(self, notes: List[Notification]) -> None:
        self.notifications = notes

    def wait_quiescent(self, quiet: float = 2.0, timeout: float = 90.0) -> bool:
        return True


class PublishMatchTests(unittest.TestCase):
    def test_percent_encoded_publish_matches_the_opened_uri(self) -> None:
        client = FakeClient([publish(PLAIN, []), publish(BRACKETED_AS_PUBLISHED, [DIAG])])
        self.assertEqual(published_diagnostics(client, BRACKETED), [DIAG])
        self.assertEqual(published_diagnostics(client, PLAIN), [])

    def test_case_folded_match_and_latest_publish_wins(self) -> None:
        client = FakeClient([publish(BRACKETED_AS_PUBLISHED.upper().replace("FILE:", "file:"), [DIAG]),
                             publish(BRACKETED_AS_PUBLISHED, [])])
        self.assertEqual(published_diagnostics(client, BRACKETED), [])

    def test_other_documents_do_not_match(self) -> None:
        client = FakeClient([publish(BRACKETED_AS_PUBLISHED, [DIAG])])
        self.assertIsNone(published_diagnostics(client, f"file://{ROOT}/app/api/[provider]/route.ts"))


class PushSettleTests(unittest.TestCase):
    def test_settles_when_the_only_publish_is_percent_encoded(self) -> None:
        client = FakeClient([publish(PLAIN, []), publish(BRACKETED_AS_PUBLISHED, [DIAG])])
        t0 = time.monotonic()
        self.assertTrue(wait_push_settle(client, [PLAIN, BRACKETED], cap_s=5.0))
        self.assertLess(time.monotonic() - t0, 1.0)

    def test_does_not_settle_without_a_publish_for_every_document(self) -> None:
        client = FakeClient([publish(PLAIN, [])])
        self.assertFalse(wait_push_settle(client, [PLAIN, BRACKETED], cap_s=0.6))

    def test_final_summary_reads_the_percent_encoded_publish(self) -> None:
        client = FakeClient([publish(PLAIN, []), publish(BRACKETED_AS_PUBLISHED, [DIAG])])
        summary = final_diagnostics_summary(client, "ts6", [PLAIN, BRACKETED], pull=False)
        self.assertEqual((summary["diagnostics_total"], summary["diagnostics_import_noise"]), (1, 1))


class SkipProbeTests(unittest.TestCase):
    def test_skip_probe_keeps_completed_probes_and_stubs_the_rest(self) -> None:
        p = ProjectSpec("typescript", "o", "r", "c" * 40, stars=1, size_kb=1)
        prep = {p.slug: {"clone": {"status": "already-prepared"}, "path": "/nowhere",
                         "deps": {"status": "ok", "manager": "npm-ci"}}}
        done = {"repo": "o/r", "commit": "c" * 40, "server": "ts6", "version": "6.0.3",
                "settled": True, "seconds": 4.2, "probe_complete": True}
        with tempfile.TemporaryDirectory() as tmp:
            opts = ProbeOptions(skip_probe=True, out_json=os.path.join(tmp, "out.json"))
            recs = probe_units([p], prep, {unit_key(p, "ts6", "6.0.3"): done}, set(), opts)
            self.assertFalse(os.listdir(tmp))  # nothing probed, nothing saved
        self.assertIs(recs[0], done)
        self.assertEqual((recs[1]["server"], recs[1]["probe_complete"], recs[1]["skipped_reason"]),
                         ("ts7", False, "skip-probe-flag"))


if __name__ == "__main__":
    unittest.main()
