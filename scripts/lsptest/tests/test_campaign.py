"""Unit tests for the campaign: config parsing, eligibility, run ids and ordering, the dry-run
plan, resumability (results rows, parameter conflicts, the scheduler with fake workers,
including a hard timeout) and the pure logic of the R0 crash oracle.

Run line: python3 -m unittest discover -s scripts/lsptest/tests
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Dict
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import campaign  # noqa: E402
from campaign_config import ConfigError, RunSpec, dry_run_config, interleave_rounds, make_run_id, parse_config  # noqa: E402
from campaign_plan import Pair, dry_run_plan, eligible_pairs, plan_runs  # noqa: E402
from campaign_store import CampaignPaths, append_jsonl, completed_runs, read_jsonl  # noqa: E402
from model import QueryKey, QueryResult, Snapshot  # noqa: E402
from oracles import r0_crash  # noqa: E402
from oracles.base import OracleContext  # noqa: E402

RAW: Dict[str, Any] = {
    "id": "t1", "corpus": "",
    "servers": [{"kind": "pyright", "version": "1.1.414"}, {"kind": "ts7", "version": "7.0.2"}],
    "oracles": {"r0_crash": {"seeds": {"settled": 1}},
                "r1_history": {"seeds": {"settled": [1, 2, 3], "race0": [1]}, "max_cases": 5},
                "r6_crossimpl": {"seeds": {"settled": [1]}, "servers": ["ts7"]}},
    "concurrency": 3, "timeouts": {"run_s": 60},
}


def pair(kind: str, name: str, size: int = 10) -> Pair:
    return Pair(kind, f"{name}@abc", "corpus", f"temp/corpus/{name}", "python", name, "abc" * 5, size, 5.0)


class ConfigTests(unittest.TestCase):
    def test_parse(self) -> None:
        cfg = parse_config(RAW)
        self.assertEqual(cfg.id, "t1")
        self.assertEqual([o.name for o in cfg.oracles], ["r0_crash", "r1_history", "r6_crossimpl"])
        r1 = cfg.oracles[1]
        self.assertEqual(r1.rounds, (("settled", 1), ("race0", 1), ("settled", 2), ("settled", 3)))
        self.assertEqual(cfg.oracles[0].rounds, (("settled", 1),))
        self.assertEqual((r1.max_cases, cfg.concurrency, cfg.run_timeout_s), (5, 3, 60.0))

    def test_rejects_bad_configs(self) -> None:
        bad = [dict(RAW, colour=1), dict(RAW, id="a b"), dict(RAW, servers=[]),
               dict(RAW, oracles={"r9_magic": {}}), dict(RAW, oracles={"r1_history": {"seeds": {"race7": [1]}}}),
               dict(RAW, oracles={"r1_history": {"seeds": {"settled": [1, 1]}}}),
               dict(RAW, oracles={"r6_crossimpl": {"servers": ["gopls"]}})]
        for raw in bad:
            with self.assertRaises(ConfigError, msg=str(raw)[:80]):
                parse_config(raw)

    def test_interleave_rounds(self) -> None:
        self.assertEqual(interleave_rounds([("settled", [1, 2]), ("race0", [7]), ("race200", [8])]),
                         (("settled", 1), ("race0", 7), ("race200", 8), ("settled", 2)))

    def test_dry_run_id(self) -> None:
        cfg = parse_config(RAW)
        self.assertEqual(dry_run_config(cfg).id, "t1-dryrun")
        self.assertEqual(dry_run_config(parse_config(dict(RAW, id="dryrun"))).id, "dryrun")
        self.assertTrue(parse_config(dict(RAW, dry_run={"only": True, "max_cases": 3})).dry_run_only)


class EligibilityTests(unittest.TestCase):
    def rec(self, repo: str, **kw: Any) -> Dict[str, Any]:
        base = {"server": "pyright", "repo": repo, "commit": "f" * 40, "commit12": "f" * 12, "language": "python",
                "clone_status": "ok", "deps_status": "n/a", "init_ok": True, "settled": True, "seconds": 4.0,
                "crashed": False, "size_kb": 100}
        return dict(base, **kw)

    def test_rules(self) -> None:
        raw = dict(RAW, eligibility={"force": [{"server": "pyright", "repo": "o/slow", "reason": "probe bug"}],
                                     "exclude": [{"server": "*", "repo": "o/banned"}]},
                   case_projects=[{"case": "pyright_8946", "language": "python", "servers": ["pyright"]}])
        cfg = parse_config(raw)
        recs = [self.rec("o/good"), self.rec("o/slow", settled=False), self.rec("o/unsettled", settled=False),
                self.rec("o/banned"), self.rec("o/gone"), self.rec("o/crash", crashed=True),
                self.rec("o/other", server="gopls")]
        pairs, excluded = eligible_pairs(cfg, recs, lambda p: "gone" not in p)
        names = [(p.server_kind, p.repo) for p in pairs]
        self.assertEqual(names, [("pyright", "o/good"), ("pyright", "o/slow"), ("pyright", "pyright_8946")])
        self.assertEqual(pairs[1].forced, "probe bug")
        self.assertEqual(pairs[0].project, "o/good@" + "f" * 12)
        self.assertEqual(pairs[0].project_ref, "temp/corpus/o__good@" + "f" * 12)
        self.assertEqual(pairs[2].source, "case")
        why = {e["repo"]: e["reason"] for e in excluded}
        self.assertEqual(set(why), {"o/unsettled", "o/banned", "o/gone", "o/crash"})
        self.assertIn("did not settle", why["o/unsettled"])


class PlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = parse_config(RAW)
        self.pairs = [pair(k, n, s) for k in ("pyright", "ts7") for n, s in (("a", 30), ("b", 10), ("c", 20))]
        self.applies = lambda o, k: not (o == "r6_crossimpl" and k == "pyright")

    def test_run_id(self) -> None:
        a = make_run_id("r1_history", "ts7", "7.0.2", "p@1", 1, "settled")
        self.assertEqual(a, make_run_id("r1_history", "ts7", "7.0.2", "p@1", 1, "settled"))
        self.assertEqual(len(a), 12)
        others = [make_run_id(*args) for args in (("r2_handles", "ts7", "7.0.2", "p@1", 1, "settled"),
                                                   ("r1_history", "ts6", "7.0.2", "p@1", 1, "settled"),
                                                   ("r1_history", "ts7", "7.0.3", "p@1", 1, "settled"),
                                                   ("r1_history", "ts7", "7.0.2", "p@2", 1, "settled"),
                                                   ("r1_history", "ts7", "7.0.2", "p@1", 2, "settled"),
                                                   ("r1_history", "ts7", "7.0.2", "p@1", 1, "race0"))]
        self.assertEqual(len(set(others + [a])), 7)

    def test_plan_counts_ids_and_json(self) -> None:
        runs = plan_runs(self.cfg, self.pairs, self.applies)
        # r0: 2 servers x 3 projects; r1: 2 x 3 x 4 rounds; r6: ts7 only x 3
        self.assertEqual(len(runs), 6 + 24 + 3)
        self.assertEqual(len({r.run_id for r in runs}), len(runs))
        self.assertFalse(any(r.oracle == "r6_crossimpl" and r.server_kind == "pyright" for r in runs))
        s = runs[0]
        self.assertEqual(RunSpec.from_json(json.loads(json.dumps(s.to_json()))), s)
        self.assertEqual(s.to_json()["run_id"], s.run_id)
        self.assertNotIn("campaign", s.result_affecting())

    def test_round_robin_is_balanced(self) -> None:
        runs = plan_runs(self.cfg, self.pairs, self.applies)
        first = runs[:5]
        self.assertEqual({r.server_kind for r in first[:2]}, {"pyright", "ts7"})  # servers alternate
        half = runs[: len(runs) // 2]
        for (o, k), n in {("r1_history", "pyright"): 12, ("r0_crash", "ts7"): 3, ("r6_crossimpl", "ts7"): 3}.items():
            done = sum(1 for r in half if (r.oracle, r.server_kind) == (o, k))
            self.assertLessEqual(abs(done / n - 0.5), 0.34, (o, k, done))
        r1 = [r for r in runs if r.oracle == "r1_history" and r.server_kind == "ts7"]
        self.assertEqual([(r.timing, r.seed) for r in r1[:3]], [("settled", 1)] * 3)  # a round covers all projects
        self.assertEqual({r.project for r in r1[:3]}, {"a@abc", "b@abc", "c@abc"})
        self.assertEqual((r1[3].timing, r1[3].seed), ("race0", 1))

    def test_dry_run_plan(self) -> None:
        cfg = dry_run_config(self.cfg)
        runs = dry_run_plan(cfg, self.pairs, self.applies)
        self.assertEqual(sorted((r.oracle, r.server_kind) for r in runs),
                         sorted([("r0_crash", "pyright"), ("r0_crash", "ts7"), ("r1_history", "pyright"),
                                 ("r1_history", "ts7"), ("r6_crossimpl", "ts7")]))
        self.assertTrue(all(r.project == "b@abc" and r.max_cases == 2 and r.campaign == "t1-dryrun" for r in runs))


class ResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.paths = CampaignPaths(os.path.join(self.tmp, "out"), os.path.join(self.tmp, "scratch"))
        self.runs = plan_runs(parse_config(RAW), [pair("pyright", "a"), pair("ts7", "a")], lambda o, k: True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_completed_runs_last_row_wins_and_torn_line(self) -> None:
        append_jsonl(self.paths.results, [dict(self.runs[0].to_json(), status="failed"),
                                          dict(self.runs[0].to_json(), status="ok")])
        with open(self.paths.results, "a", encoding="utf-8") as f:
            f.write('{"run_id": "torn')
        done = completed_runs(self.paths.results)
        self.assertEqual(list(done), [self.runs[0].run_id])
        self.assertEqual(done[self.runs[0].run_id]["status"], "ok")

    def test_conflicts_and_select(self) -> None:
        s = self.runs[0]
        done = {s.run_id: dict(s.to_json(), max_cases=s.max_cases + 1)}
        self.assertEqual(campaign.resume_conflicts(self.runs, done), [s.run_id])
        done = {s.run_id: dict(s.to_json(), run_timeout_s=9999.0, campaign="renamed")}
        self.assertEqual(campaign.resume_conflicts(self.runs, done), [])
        only = campaign.select(self.runs, "oracle=r1_history,server=ts7,timing=race0")
        self.assertTrue(only and all((r.oracle, r.server_kind, r.timing) == ("r1_history", "ts7", "race0") for r in only))
        with self.assertRaises(ConfigError):
            campaign.select(self.runs, "colour=red")


FAKE_WORKER = r"""
import json, os, sys, time
d = json.load(open(sys.argv[1]))
spec = d["spec"]
if spec["seed"] == 99:
    time.sleep(60)
rid = spec["run_id"]
row = {"vid": rid + "-v00", "run_id": rid, "confirmed": True, "signature": "k|o|s"}
out = {"run_id": rid, "status": "ok", "error": "", "candidates": 2, "confirmed": 1, "flaky": 0, "replayed": 1,
       "violations": [row], "seconds": 0.1}
with open(os.path.join(d["scratch"], rid, "result.json"), "w") as f:
    json.dump(out, f)
"""


def fake_launcher(spec_path: str, log_path: str) -> subprocess.Popen:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "ab") as log:
        return subprocess.Popen([sys.executable, "-c", FAKE_WORKER, spec_path], stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.paths = CampaignPaths(os.path.join(self.tmp, "out"), os.path.join(self.tmp, "scratch"))
        os.makedirs(self.paths.root)
        cfg = parse_config(RAW)
        self.runs = plan_runs(cfg, [pair("pyright", "a"), pair("ts7", "b")], lambda o, k: o != "r6_crossimpl")[:4]

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sched(self) -> campaign.Scheduler:
        return campaign.Scheduler(self.paths, {"n": 3, "per_signature": 1}, 2, launcher=fake_launcher)

    def test_runs_record_and_resume(self) -> None:
        self.assertEqual(self.sched().execute(self.runs, poll_s=0.05), 4)
        rows = read_jsonl(self.paths.results)
        self.assertEqual(sorted(r["run_id"] for r in rows), sorted(s.run_id for s in self.runs))
        self.assertTrue(all(r["status"] == "ok" and r["confirmed"] == 1 and r["oracle"] for r in rows))
        self.assertEqual(len(read_jsonl(self.paths.violations)), 4)
        self.assertFalse(os.listdir(self.paths.scratch))  # every run scratch removed
        done = completed_runs(self.paths.results)
        self.assertEqual([s for s in self.runs if s.run_id not in done], [])
        with open(self.paths.progress, encoding="utf-8") as f:
            self.assertEqual(len(f.read().splitlines()), 4)

    def test_server_limit_skips_to_another_server(self) -> None:
        s = campaign.Scheduler(self.paths, {"n": 3}, 4, launcher=fake_launcher, server_limits={"pyright": 1})
        py = [r for r in self.runs if r.server_kind == "pyright"]
        other = [r for r in self.runs if r.server_kind != "pyright"]
        queue = py + other
        self.assertEqual(s.next_index(queue), 0)
        s.active["x"] = campaign.Active(py[0], mock.Mock(), 0.0, "")
        self.assertEqual(s.next_index(queue), len(py))  # pyright is at its limit: the first other run
        self.assertIsNone(s.next_index(py))

    def test_hard_timeout_kills_and_records(self) -> None:
        slow = RunSpec.from_json(dict(self.runs[0].to_json(), seed=99, run_timeout_s=0.5))
        self.assertEqual(self.sched().execute([slow], poll_s=0.05), 1)
        row = read_jsonl(self.paths.results)[0]
        self.assertEqual(row["status"], "timeout")
        self.assertIn("hard timeout", row["error"])
        self.assertEqual(read_jsonl(self.paths.violations), [])
        self.assertFalse(os.path.exists(self.paths.run_scratch(slow.run_id)))


class R0Tests(unittest.TestCase):
    def ctx(self) -> OracleContext:
        return OracleContext("r0test", "gopls", "v0", "p@1", "/nonexistent", "go", 1, ())

    def session(self, label: str, **norms: Any) -> r0_crash.CrashSession:
        res = {}
        for name, norm in norms.items():
            k = QueryKey(name, "a.go", 1, 2)
            err = tuple(norm) if isinstance(norm, list) and norm[:1] == ["error"] else None
            res[k] = QueryResult(k, norm, error=err)
        s = r0_crash.CrashSession(label, Snapshot(label, "gopls-v0", False, res), "done")
        s.pseudo = {r0_crash.INIT_KEY: [], r0_crash.SESSION_KEY: []}
        return s

    def test_crash_code(self) -> None:
        cc = r0_crash.crash_code
        self.assertEqual([cc(["error", -32603]), cc(["error", -32001]), cc(["error", "dead"]), cc(["error", "timeout"])],
                         ["-32603", "-32001", "dead", "timeout"])
        self.assertEqual([cc(["error", 0]), cc(["error", -32801]), cc(["error", -32602]), cc(["hover", None]), cc(None)],
                         [None] * 5)

    def test_run_candidates_need_both_sessions(self) -> None:
        b = self.session("b", hover=["error", -32603], definition=["error", 0], references=["error", "timeout"])
        c = self.session("c", hover=["error", -32603], definition=["error", 0], references=[["a.go", 1, 1, 1, 2]])
        with mock.patch.object(r0_crash, "crash_pair", return_value=(b, c)):
            res = r0_crash.CrashCheck().run(self.ctx())
        self.assertEqual([v.key.method for v in res.candidates], ["hover"])
        self.assertEqual(res.candidates[0].signature, "gopls|r0_crash|hover:result->error:-32603")
        self.assertEqual(res.unstable, {"references": 1})
        with mock.patch.object(r0_crash, "crash_pair", return_value=(b, c)):
            out = r0_crash.CrashCheck().replay(self.ctx(), res.candidates[0])
        self.assertTrue(out.settled and out.control_stable and out.reproduced)
        d = self.session("d", hover=["error", -32603])
        e = self.session("e", hover=["hover text", None])
        with mock.patch.object(r0_crash, "crash_pair", return_value=(d, e)):
            out = r0_crash.CrashCheck().replay(self.ctx(), res.candidates[0])
        self.assertTrue(out.settled)
        self.assertFalse(out.control_stable or out.reproduced)


if __name__ == "__main__":
    unittest.main()
