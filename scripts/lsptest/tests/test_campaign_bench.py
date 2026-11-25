"""Unit tests for the benchmark campaign: case selection from the latest verdicts, the generated
config (builds, oracles, targets, cap scope, dry-run cases), its plan (pre and post runs with the
case's version, settings and timeouts; oracles by kind) and the detection table (pre-only
signatures, completeness, the specification-probe split, author_match carried over, rendering).

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import collections
import os
import sys
import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from campaign_bench import build_config, latest_verdicts, select_cases  # noqa: E402
from campaign_config import parse_config  # noqa: E402
from campaign_detect import detect, render, summary  # noqa: E402
from campaign_plan import dry_run_plan, eligible_pairs, plan_runs  # noqa: E402


@dataclass
class FakeRepro:
    probe: Dict[str, Any]


@dataclass
class FakeCase:
    case_id: str
    kind: str
    probe: str = "differs_from_fresh"
    language: str = "go"
    settings: Dict[str, Any] = field(default_factory=dict)
    session: Dict[str, Any] = field(default_factory=lambda: {"settle_timeout_s": 180, "pull_diagnostics": False})

    @property
    def meta(self) -> Dict[str, Any]:
        return {"kind": self.kind, "pre_build": f"{self.case_id}-pre", "post_build": f"{self.case_id}-post",
                "oracle_class": "R1", "subtype": "edit-undo", "url": "u", "title": "t"}

    @property
    def repro(self) -> FakeRepro:
        return FakeRepro({"type": self.probe})

    @property
    def project_dir(self) -> str:
        return f"/repo/data/lsp_bench/cases/{self.case_id}/project"

    def build(self, phase: str) -> str:
        return str(self.meta[f"{phase}_build"])


CASES = {"gopls-1": FakeCase("gopls-1", "gopls"), "tsserver-2": FakeCase("tsserver-2", "tsserver", language="typescript"),
         "gopls-3": FakeCase("gopls-3", "gopls", probe="edit_text_differs"), "gopls-4": FakeCase("gopls-4", "gopls"),
         "gopls-5": FakeCase("gopls-5", "gopls")}
ROWS = [{"case": "gopls-1", "verdict": "invalid", "case_sha": "s"}, {"case": "gopls-1", "verdict": "reproduced", "case_sha": "s"},
        {"case": "tsserver-2", "verdict": "reproduced", "case_sha": "s"}, {"case": "gopls-3", "verdict": "reproduced", "case_sha": "s"},
        {"case": "gopls-4", "verdict": "reproduced", "case_sha": "old"}, {"case": "gopls-5", "verdict": "reproduced", "case_sha": "s"},
        {"case": "gopls-6", "verdict": "not-reproduced-pre", "case_sha": "s"}]
PER_KIND = {"gopls": ["r0_crash", "r1_history", "r2_handles", "r3_routes", "r4_edits", "r5_transforms"],
            "tsserver": ["r0_crash", "r1_history", "r4_edits"]}


def applies(oracle: str, kind: str) -> bool:
    return oracle in PER_KIND.get(kind, [])


def selected() -> Any:
    return select_cases(latest_verdicts(ROWS), CASES.get, lambda c: "s",
                        lambda kind, version: not version.startswith("gopls-5"))


class SelectionTests(unittest.TestCase):
    def test_latest_verdict_revision_and_builds(self) -> None:
        kept, excluded = selected()  # every case's current revision hashes to "s"; gopls-4's verdict is for "old"
        self.assertEqual([c["case"] for c in kept], ["gopls-1", "gopls-3", "tsserver-2"])
        why = {e["case"]: e["reason"] for e in excluded}
        self.assertIn("not-reproduced-pre", why["gopls-6"])
        self.assertIn("older revision", why["gopls-4"])
        self.assertIn("not installed", why["gopls-5"])
        g3 = next(c for c in kept if c["case"] == "gopls-3")
        self.assertTrue(g3["spec_probe"])
        self.assertEqual(g3["builds"], {"pre": "gopls-3-pre", "post": "gopls-3-post"})
        self.assertEqual(g3["session"], {"settle_timeout_s": 180, "pull_diagnostics": False})

    def test_config_and_plan(self) -> None:
        kept, excluded = selected()
        raw = build_config(kept, excluded, "bench_t", ["gopls-1", "tsserver-2"], "results.jsonl", PER_KIND)
        self.assertEqual(raw["servers"], [])
        self.assertNotIn("r6_crossimpl", raw["oracles"])
        self.assertEqual(raw["oracles"]["r1_history"]["seeds"], {"settled": [1, 2, 3], "race0": [1]})
        self.assertEqual(raw["signature_cap"], {"runs": 3, "scope": "build"})
        self.assertEqual((raw["targets"]["max_positions_per_file"], raw["targets"]["min_identifiers"]), (20, 1))
        self.assertEqual(raw["generated"]["spec_probe_cases"], ["gopls-3"])
        cfg = parse_config(raw)
        self.assertEqual(cfg.kinds, ["gopls", "tsserver"])
        pairs, _ = eligible_pairs(cfg, [], lambda p: True)
        self.assertEqual(len(pairs), 6)  # three cases x (pre, post)
        runs = plan_runs(cfg, pairs, applies)
        per = collections.Counter(r.project for r in runs)
        self.assertEqual(per, {"gopls-1": 28, "gopls-3": 28, "tsserver-2": 16})  # 14 or 8 runs per build
        r = next(r for r in runs if r.project == "gopls-1" and r.oracle == "r1_history" and r.timing == "race0")
        self.assertIn(r.server_version, ("gopls-1-pre", "gopls-1-post"))
        self.assertEqual((r.source, r.settle_timeout_s, r.min_identifiers), ("dir", 180.0, 1))
        self.assertEqual({x.server_version for x in runs if x.project == "tsserver-2"}, {"tsserver-2-pre", "tsserver-2-post"})
        self.assertFalse(any(x.oracle == "r3_routes" for x in runs if x.server_kind == "tsserver"))
        dry = dry_run_plan(cfg, pairs, applies)
        self.assertEqual({x.project for x in dry}, {"gopls-1", "tsserver-2"})
        self.assertEqual(len(dry), 44)


def spec(run_id: str, case: str, oracle: str, version: str) -> Dict[str, Any]:
    return {"run_id": run_id, "project": case, "oracle": oracle, "server_version": version}


def vrow(vid: str, case: str, oracle: str, version: str, sig: str, status: str = "confirmed") -> Dict[str, Any]:
    return {"vid": vid, "run_id": vid.split("-")[0], "project": case, "oracle": oracle, "server_version": version,
            "signature": sig, "status": status, "confirmed": status == "confirmed", "incomplete": False}


class DetectionTests(unittest.TestCase):
    def test_detection_table(self) -> None:
        cases = [{"case": "A", "kind": "gopls", "builds": {"pre": "a1", "post": "a2"}, "probe": "two_routes_differ"},
                 {"case": "B", "kind": "gopls", "builds": {"pre": "b1", "post": "b2"}, "probe": "differs_from_fresh"},
                 {"case": "C", "kind": "gopls", "builds": {"pre": "c1", "post": "c2"}, "probe": "edit_text_differs",
                  "spec_probe": True}]
        planned = [spec("ra", "A", "r3_routes", "a1"), spec("rb", "A", "r3_routes", "a2"),
                   spec("rc", "B", "r1_history", "b1"), spec("rd", "B", "r1_history", "b2"),
                   spec("re", "C", "r4_edits", "c1"), spec("rf", "C", "r4_edits", "c2")]
        results: List[Dict[str, Any]] = [{"run_id": r, "status": "ok"} for r in ("ra", "rb", "rc", "rd", "re")]
        sig_a, sig_b = "gopls|r3_routes|highlightVsReferences:extra", "gopls|r1_history|hover:text"
        violations = [vrow("ra-v00", "A", "r3_routes", "a1", sig_a), vrow("ra-s00", "A", "r3_routes", "a1",
                                                                          "gopls|r3_routes|definitionConsistency.shorthand:extra",
                                                                          "labelled-legitimate"),
                      vrow("rc-v00", "B", "r1_history", "b1", sig_b), vrow("rd-v00", "B", "r1_history", "b2", sig_b),
                      vrow("re-v00", "C", "r4_edits", "c1", "gopls|r4_edits|diagnostics:extra:X")]
        author = {("A", "r3_routes", sig_a): "yes"}
        entries = detect(cases, planned, results, violations, author)
        a, b, c = entries
        self.assertTrue(a["detected"] and a["complete"])
        self.assertEqual(a["pre_only"][0]["signature"], sig_a)
        self.assertEqual(a["pre_only"][0]["author_match"], "yes")
        self.assertEqual(a["oracles"]["r3_routes"]["labelled"]["pre"], ["gopls|r3_routes|definitionConsistency.shorthand:extra"])
        self.assertFalse(b["detected"])  # confirmed on both builds
        self.assertTrue(c["detected"] and not c["complete"])  # post run missing: provisional
        self.assertEqual(c["oracles"]["r4_edits"]["runs"]["post"], {"missing": 1})
        s = summary(entries)
        self.assertEqual((s["generic"]["cases"], s["generic"]["detected"]), (2, 1))
        self.assertEqual((s["spec_probe"]["cases"], s["spec_probe"]["detected"]), (1, 1))
        self.assertEqual(s["generic"]["detected_by_oracle"], {"r3_routes": 1})
        text = render("bench_t", entries, s)
        for part in ("## Cases whose ground truth used edit_text_differs", "| A | r3_routes | "
                     "`gopls\\|r3_routes\\|highlightVsReferences:extra` | ra-v00 | yes | yes |", "author_match"):
            self.assertIn(part, text)


if __name__ == "__main__":
    unittest.main()
