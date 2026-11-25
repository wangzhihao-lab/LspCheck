"""Release lists and server builds of the release sweep (scripts/paper/evidence/release_sweep.py).

plan(): applies RULES (fixed before any result) to the npm registry `time` field, proxy.golang.org and the GitHub
releases API, keeping releases published up to 2026-09-28, and writes data/lsptest/runs/main_v1/sweep/<label>/
releases.json (rules, groups, builds with release dates, status "planned"). A refresh with the environment variable
RELEASE_SWEEP_AS_OF=YYYY-MM-DD applies the same newest-release rules with that cut-off and plans, installs and runs
only the label newest-<date>; the lifecycle label keeps the 2026-09-28 cut-off.
install(): installs every planned build under temp/lsp_servers/ with the frozen installers (scripts/lsptest/bench/
install_builds.py; data/lsp_bench/builds.json is not written) or, for TypeScript 7, with npm as temp/lsp_servers/
ts7-7.0.2 was installed; launch check smoke_servers.smoke (initialize, diagnostics and hover on a one-file project),
two attempts; records ok/unavailable and, for gopls, the Go the build runs with and the groups whose project needs a
newer Go (skip).

Campaigns: set_campaign() points CAMPAIGN, RUN_ROOT and SWEEP at data/lsptest/runs/<campaign>/ (default main_v1);
labels() gives the campaign's labels; plan_doc() keeps only the lines the label's groups need and, for a later campaign,
records the campaign and the representative rule (REP_RULE); same_builds() requires a later campaign's builds to equal
main_v1's plan of the same label on shared lines; extend_plans() appends groups added to a root-cause table after the
plan. pyright: newest = newest stable on npm; lifecycle = first stable release of each quarter 2024-Q4 ... 2026-Q3,
plus the campaign's 1.1.414 and the newest (RULES).

Run line: imported by release_sweep.py (its plan and install subcommands); not run directly.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "lsptest"))
sys.dont_write_bytecode = True  # no new bytecode caches inside the frozen tree

import smoke_servers  # noqa: E402  (frozen tool, read-only)
import version_sweep as vs  # noqa: E402
import servers  # noqa: E402
import servers_extra  # noqa: E402,F401  (registers the kinds before servers_bench wraps gopls for era Go)
from bench import install_builds as ib  # noqa: E402
from campaign_store import load_repro, project_dir  # noqa: E402
from servers_bench import read_toolchain  # noqa: E402

if not hasattr(servers.SERVER_FACTORY.get("gopls"), "__wrapped__"):  # else era-Go builds would run with the local Go
    raise ImportError("the gopls launch spec is not era-Go aware (servers_bench was imported before servers_extra)")

logger = logging.getLogger("release_sweep")
FIRST_CAMPAIGN = "main_v1"
CAMPAIGNS = ("main_v1", "main_v2")
RUNS = os.path.join(REPO, "data", "lsptest", "runs")
CAMPAIGN = FIRST_CAMPAIGN  # set_campaign() rebinds CAMPAIGN, RUN_ROOT and SWEEP
RUN_ROOT = os.path.join(RUNS, CAMPAIGN)
SWEEP = os.path.join(RUN_ROOT, "sweep")
FIRST_AS_OF = "2026-09-28"  # the sweep at campaign time: labels newest-2026-09-28 and lifecycle
# A later refresh sets RELEASE_SWEEP_AS_OF=YYYY-MM-DD and gets only the label newest-<date> (same rules, later
# cut-off); the lifecycle label stays the one planned with the campaign-time cut-off.
AS_OF = os.environ.get("RELEASE_SWEEP_AS_OF", FIRST_AS_OF)
if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", AS_OF) or AS_OF < FIRST_AS_OF:
    raise SystemExit(f"RELEASE_SWEEP_AS_OF must be a date YYYY-MM-DD not before {FIRST_AS_OF}: {AS_OF!r}")
CUTOFF = f"{AS_OF}T23:59:59Z"
NEWEST, LIFECYCLE = f"newest-{AS_OF}", "lifecycle"
LABELS = (NEWEST, LIFECYCLE) if AS_OF == FIRST_AS_OF else (NEWEST,)  # of main_v1; labels() for the set campaign
LINES = ("gopls", "rust-analyzer", "ts6", "ts7", "pyright")
KIND = {"gopls": "gopls", "rust-analyzer": "rust-analyzer", "ts6": "tsserver", "ts7": "ts7", "pyright": "pyright"}
SMOKE = {"gopls": "go", "rust-analyzer": "rs", "tsserver": "ts", "ts7": "ts", "pyright": "py"}
CAMPAIGN_BUILD = {"gopls": "v0.23.0", "rust-analyzer": "2026-09-21", "ts6": "6.0.3+tsls6.0.0", "ts7": "7.0.2",
                  "pyright": "1.1.414"}  # main_v2 ran the same five builds as main_v1 (its config.json)
ERA_GO = "go1.24.4"  # the newest Go SDK under temp/lsp_servers/go-sdks before Go 1.25 changed go/token.FileSet
REPS = {"C1": "ts6-r1-references-lost-h5-d24ca6", "C2": "ts6-r1-diagnostics-extra-2304-h7-8ca52f",
        "C3": "gopls-r2-codeactionresolve-changed-codeaction-70b3e9",
        "C4": "rust-analyzer-r2-completionresolve-changed-completion-3170a1",
        "C5": "gopls-r4-diagnostics-extra-notatype-mutation-m2-477181",
        "C6": "gopls-r4-diagnostics-extra-mutation-m2-111975",
        "C7": "gopls-r4-diagnostics-extra-undeclaredname-wrongar-mutation-m3-946c39",
        "C8": "rust-analyzer-r3-definitionconsistency-extra-d-4cbc9e", "C9": "gopls-r1-references-extra-h9-0290a7",
        "C10": "ts7-r1-references-missing-h9-2dd24a", "C11": "ts6-r4-diagnostics-extra-2322-mutation-m3-1879f3"}
# Causes added after the first sweep (root-cause tables of 2026-11-21: C12-C35) get their representative by a written
# rule; REPS above stays as chosen for the first sweep.
REP_RULE = ("one representative group per cause: for C1-C11 the group chosen for the first sweep (REPS); for any later "
            "cause the cause's first group in row order of the root-cause table of the first campaign that lists the "
            "cause (main_v1 before main_v2); a campaign's lifecycle plan holds the causes whose representative comes "
            "from that campaign")
STABLE = re.compile(r"v?\d+\.\d+\.\d+")
WEEKLY = re.compile(r"\d{4}-\d{2}-\d{2}")
RULES: Dict[str, Any] = {
    NEWEST: {"gopls": "newest stable version on proxy.golang.org",
             "rust-analyzer": "newest weekly GitHub release (tag YYYY-MM-DD)",
             "ts6": "newest TypeScript 6.x with the newest typescript-language-server (npm)",
             "ts7": "newest stable TypeScript 7.x (npm)",
             "pyright": "newest stable pyright (npm)"},
    LIFECYCLE: {
        "gopls": "the first release (vX.Y.0) of every minor line v0.16 ... v0.23 (the campaign's v0.23.0), "
                 "plus the newest",
        "rust-analyzer": "the first weekly release (tag YYYY-MM-DD) of each quarter 2024-Q4 ... 2026-Q3, plus the "
                         "campaign's 2026-09-21 and the newest",
        "ts6": "the last patch of each TypeScript minor 5.5, 5.6, 5.7, 5.8, 5.9 and 6.0, each with the "
               "typescript-language-server release newest at that TypeScript release's publication time (npm `time`), "
               "plus the campaign pair 6.0.3+tsls6.0.0 and the newest pair",
        "ts7": "every TypeScript 7.x version on npm up to the newest stable one (stable and beta/rc releases; nightly "
               "-dev builds excluded)",
        "pyright": "the first stable release (npm `time`) of each quarter 2024-Q4 ... 2026-Q3, plus the campaign's "
                   "1.1.414 and the newest (as the rust-analyzer rule: both lines release about weekly); installed as "
                   "the benchmark installs pyright (npm pyright@<v>, scripts/lsptest/bench/install_builds.py)"},
    "common": [
        f"releases published up to {AS_OF}; 3 replays per group and build; verdicts of version_sweep.verdict",
        "ts6 line through the frozen sweep's kind tsserver (pinned wrapper started with the pinned tsserver.js, no ts6 "
        "session settings), as older-2025 and ts_isolation.py; the campaign pair in that kind controls for the kind",
        "gopls builds are compiled and run with the local Go (go1.27.1, the toolchain of the campaign's "
        f"v0.23.0 build); a release the local Go cannot compile is compiled and run with {ERA_GO} "
        "(install_builds --go); where the install directory already holds an era-Go benchmark build, the local-Go "
        "build goes to gopls-<v>+<go>/",
        "a gopls group is replayed on a build only if the build's Go meets every go directive of the group's project "
        "(go.mod/go.work), since the harness runs gopls with GOTOOLCHAIN=local; other pairs are listed under skip",
        "a build that cannot be installed, or fails the launch check (smoke_servers.smoke: initialize, diagnostics and "
        "hover on a one-file project), after two attempts is recorded as unavailable",
        "the C2 group (timing race) runs alone; otherwise at most 3 jobs at once (gopls, rust-analyzer, ts6+ts7)"],
    "sources": ["https://registry.npmjs.org/<package> (time)",
                "https://proxy.golang.org/golang.org/x/tools/gopls/@v/list and @v/<version>.info",
                "https://api.github.com/repos/rust-lang/rust-analyzer/releases (tag_name, published_at, asset "
                "rust-analyzer-aarch64-apple-darwin.gz)"],
}


# ------------------------------------------------------------------ release lists
def fetch(url: str, github: bool = False) -> bytes:
    """GET one registry document (the GitHub token, when set, is sent to api.github.com only)."""
    headers = {"User-Agent": "release-sweep"}
    token = os.environ.get("GITHUB_TOKEN", "") if github else ""
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=300) as resp:
        return resp.read()


def vkey(version: str) -> Tuple[int, ...]:
    """(6, 0, 3) from "6.0.3", "v0.23.0", "go1.24.4" or "7.0.1-rc" (a pre-release suffix is ignored)."""
    return tuple(int(x) for x in re.findall(r"\d+", version.split("-")[0]))


def npm_times(pkg: str) -> Dict[str, str]:
    """version -> publication time (npm `time`) of the versions published up to the cut-off."""
    times = json.loads(fetch(f"https://registry.npmjs.org/{pkg}"))["time"]
    return {v: t for v, t in times.items() if v not in ("created", "modified") and t <= CUTOFF}


def gopls_times() -> Dict[str, str]:
    """Stable gopls versions from v0.16.0 on -> publication time (module proxy)."""
    base = "https://proxy.golang.org/golang.org/x/tools/gopls/@v/"
    found = [v for v in fetch(base + "list").decode().split() if STABLE.fullmatch(v) and vkey(v) >= (0, 16, 0)]
    times = {v: json.loads(fetch(f"{base}{v}.info"))["Time"] for v in found}
    return {v: t for v, t in times.items() if t <= CUTOFF}


def ra_times() -> Dict[str, str]:
    """Weekly rust-analyzer releases with the macOS arm64 asset -> publication time, back to 2024-10."""
    asset, out = os.path.basename(ib.RA_ASSET), {}
    for page in range(1, 11):
        rels = json.loads(fetch("https://api.github.com/repos/rust-lang/rust-analyzer/releases"
                                f"?per_page=100&page={page}", github=True))
        out.update({r["tag_name"]: r["published_at"] for r in rels if WEEKLY.fullmatch(r["tag_name"])
                    and r["published_at"] <= CUTOFF and any(a["name"] == asset for a in r["assets"])})
        if len(rels) < 100 or any(WEEKLY.fullmatch(r["tag_name"]) and r["tag_name"] < "2024-10" for r in rels):
            break
    return out


def tag_of(line: str, version: str) -> str:
    """Alphanumeric build tag for run ids: g0230, r260928, t603w601, s701rc, p11414."""
    ts, _, wrapper = version.partition("+tsls")
    clean = lambda s: re.sub(r"[^0-9a-z]", "", s.lstrip("v").lower())  # noqa: E731
    if line == "rust-analyzer":
        return "r" + clean(version)[2:]
    head = {"gopls": "g", "ts6": "t", "ts7": "s", "pyright": "p"}[line]
    return head + clean(ts) + (f"w{clean(wrapper)}" if wrapper else "")


def add(builds: List[Dict[str, Any]], line: str, version: str, released: str, role: str, **extra: Any) -> None:
    """List a build, or add the role to the same build already listed."""
    same = next((b for b in builds if b["line"] == line and b["version"] == version), None)
    if same is None:
        builds.append(dict(line=line, kind=KIND[line], version=version, release=version, tag=tag_of(line, version),
                           released=released[:10], roles=[role], status="planned", **extra))
    elif role not in same["roles"]:
        same["roles"].append(role)


def plan_builds() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """(newest builds, lifecycle builds) by RULES."""
    newest: List[Dict[str, Any]] = []
    life: List[Dict[str, Any]] = []
    g = gopls_times()
    for minor in range(16, 24):
        first = min((v for v in g if vkey(v)[:2] == (0, minor)), key=vkey)
        add(life, "gopls", first, g[first], f"first of v0.{minor}")
    top = max(g, key=vkey)
    for builds in (life, newest):
        add(builds, "gopls", top, g[top], "newest")
    r = ra_times()
    for y, q in [(2024, 4)] + [(y, q) for y in (2025, 2026) for q in (1, 2, 3, 4) if (y, q) <= (2026, 3)]:
        first = min(t for t in r if int(t[:4]) == y and (int(t[5:7]) - 1) // 3 + 1 == q)
        add(life, "rust-analyzer", first, r[first], f"first of {y}-Q{q}")
    add(life, "rust-analyzer", CAMPAIGN_BUILD["rust-analyzer"], r[CAMPAIGN_BUILD["rust-analyzer"]], "campaign")
    for builds in (life, newest):
        add(builds, "rust-analyzer", max(r), r[max(r)], "newest")
    ts = npm_times("typescript")
    ts_st = {v: t for v, t in ts.items() if STABLE.fullmatch(v)}
    wr_st = {v: t for v, t in npm_times("typescript-language-server").items() if STABLE.fullmatch(v)}

    def pair(builds: List[Dict[str, Any]], v: str, w: str, role: str) -> None:
        add(builds, "ts6", f"{v}+tsls{w}", ts_st[v], role, wrapper_released=wr_st[w][:10])

    for minor in ((5, 5), (5, 6), (5, 7), (5, 8), (5, 9), (6, 0)):
        last = max((v for v in ts_st if vkey(v)[:2] == minor), key=vkey)
        wrapper = max((w for w, t in wr_st.items() if t <= ts_st[last]), key=vkey)
        pair(life, last, wrapper, f"last patch of {minor[0]}.{minor[1]}")
    pair(life, *CAMPAIGN_BUILD["ts6"].split("+tsls"), "campaign")
    top_ts, top_w = max((v for v in ts_st if vkey(v)[0] == 6), key=vkey), max(wr_st, key=vkey)
    for builds in (life, newest):
        pair(builds, top_ts, top_w, "newest")
    t7 = {v: t for v, t in ts.items() if vkey(v)[0] == 7 and re.fullmatch(r"\d+\.\d+\.\d+(-(beta|rc)(\.\d+)?)?", v)}
    top = max((v for v in t7 if STABLE.fullmatch(v)), key=vkey)
    for v in sorted((v for v in t7 if t7[v] <= t7[top]), key=lambda x: t7[x]):
        add(life, "ts7", v, t7[v], "newest" if v == top else ("pre-release" if "-" in v else "release"))
    add(newest, "ts7", top, t7[top], "newest")
    py = {v: t for v, t in npm_times("pyright").items() if STABLE.fullmatch(v)}
    for y, q in [(2024, 4)] + [(y, q) for y in (2025, 2026) for q in (1, 2, 3, 4) if (y, q) <= (2026, 3)]:
        first = min((v for v in py if int(py[v][:4]) == y and (int(py[v][5:7]) - 1) // 3 + 1 == q), key=lambda v: py[v])
        add(life, "pyright", first, py[first], f"first of {y}-Q{q}")
    add(life, "pyright", CAMPAIGN_BUILD["pyright"], py[CAMPAIGN_BUILD["pyright"]], "campaign")
    top = max(py, key=vkey)
    for builds in (life, newest):
        add(builds, "pyright", top, py[top], "newest")
    for b in newest + life:
        if b["version"] == CAMPAIGN_BUILD[b["line"]] and "campaign" not in b["roles"]:
            b["roles"].append("campaign")
    return newest, life


def plan_path(label: str) -> str:
    return os.path.join(SWEEP, label, "releases.json")


def load_plan(label: str) -> Dict[str, Any]:
    with open(plan_path(label), encoding="utf-8") as f:
        return json.load(f)


def write_text(path: str, text: str) -> None:
    """Atomic write (several processes refresh the same summary)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def set_campaign(campaign: str) -> None:
    """Point CAMPAIGN, RUN_ROOT and SWEEP at another campaign (its groups, plans and results)."""
    global CAMPAIGN, RUN_ROOT, SWEEP
    if campaign not in CAMPAIGNS:
        raise ValueError(f"campaign must be one of {', '.join(CAMPAIGNS)}: {campaign!r}")
    CAMPAIGN = campaign
    RUN_ROOT = os.path.join(RUNS, CAMPAIGN)
    SWEEP = os.path.join(RUN_ROOT, "sweep")
    _PROJECT_GO.clear()


def labels() -> Tuple[str, ...]:
    """Labels of the set campaign: main_v1 as before (LABELS); a later campaign gets only the lifecycle label at the
    campaign-time cut-off (its new causes) and only newest-<date> with RELEASE_SWEEP_AS_OF."""
    if CAMPAIGN == FIRST_CAMPAIGN:
        return LABELS
    return (LIFECYCLE,) if AS_OF == FIRST_AS_OF else (NEWEST,)


def cause_rows(campaign: str) -> List[Dict[str, str]]:
    """(cause, line, gid) of every row of the campaign's triage/root_causes.csv, in row order."""
    path = os.path.join(RUNS, campaign, "triage", "root_causes.csv")
    with open(path, newline="", encoding="utf-8") as f:
        return [{"cause": r["cause"], "line": r["server"], "gid": r["group"]} for r in csv.DictReader(f)]


def representatives(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    """The rows of the set campaign that represent a cause in its lifecycle plan, by REP_RULE (table order)."""
    fixed = dict(REPS) if CAMPAIGN == FIRST_CAMPAIGN else {}
    if any(not any(r["gid"] == gid and r["cause"] == c for r in rows) for c, gid in fixed.items()):
        raise SystemExit("a representative group is missing from triage/root_causes.csv")
    earlier = {r["cause"] for c in CAMPAIGNS[:CAMPAIGNS.index(CAMPAIGN)] for r in cause_rows(c)}
    chosen = dict(fixed)
    for r in rows:
        if r["cause"] not in chosen and r["cause"] not in earlier:
            chosen[r["cause"]] = r["gid"]
    return [r for r in rows if chosen.get(r["cause"]) == r["gid"]]


def plan_doc(label: str, builds: List[Dict[str, Any]], groups: List[Dict[str, str]]) -> Dict[str, Any]:
    """releases.json of one label; only the lines with a group are planned (for main_v1: all four, as before)."""
    lines = [x for x in LINES if any(g["line"] == x for g in groups)]
    doc = {"label": label, "as_of": AS_OF, "planned": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "rule": {k: v for k, v in RULES[label].items() if k in lines}, "common": RULES["common"],
           "sources": RULES["sources"], "groups": groups, "builds": [b for b in builds if b["line"] in lines]}
    if CAMPAIGN != FIRST_CAMPAIGN:
        doc = dict(doc, campaign=CAMPAIGN, representatives=REP_RULE if label == LIFECYCLE else "every group of "
                   "triage/root_causes.csv")
    return doc


def same_builds(label: str, doc: Dict[str, Any]) -> None:
    """A later campaign's plan must list main_v1's builds of the same label on the lines both plan (same rules,
    same cut-off); SystemExit when they differ."""
    with open(os.path.join(RUNS, FIRST_CAMPAIGN, "sweep", label, "releases.json"), encoding="utf-8") as f:
        first = json.load(f)["builds"]
    shared = {b["line"] for b in first} & {b["line"] for b in doc["builds"]}
    a = sorted((b["line"], b["release"]) for b in first if b["line"] in shared)
    b = sorted((x["line"], x["release"]) for x in doc["builds"] if x["line"] in shared)
    if a != b:
        raise SystemExit(f"{label}: the builds differ from {FIRST_CAMPAIGN}'s plan: {sorted(set(a) ^ set(b))}")


def plan(force: bool, only: Sequence[str] = (), extend: bool = False) -> int:
    """Write sweep/<label>/releases.json for the campaign's labels (`only`: these labels); 1 when one exists already
    (without --force). With extend, add to existing plans the groups the rules now select (extend_plans)."""
    todo = [label for label in labels() if not only or label in only]
    if extend:
        return extend_plans(todo)
    if not force and any(os.path.exists(plan_path(label)) for label in todo):
        logger.error("releases.json exists already; --force overwrites it (and resets the install status)")
        return 1
    newest, life = plan_builds()
    rows = cause_rows(CAMPAIGN)
    reps = representatives(rows)
    for label, builds, groups in ((NEWEST, newest, rows), (LIFECYCLE, life, reps)):
        if label not in todo:  # a refresh plans only its newest-<date> label
            continue
        doc = plan_doc(label, builds, groups)
        if CAMPAIGN != FIRST_CAMPAIGN:
            same_builds(label, doc)
        write_text(plan_path(label), json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        logger.info("%s: %d group(s), %d build(s): %s", label, len(doc["groups"]), len(doc["builds"]),
                    ", ".join(f"{b['line']} {b['version']}" for b in doc["builds"]))
    return 0


def extend_plans(todo: Sequence[str]) -> int:
    """Append to existing plans the groups the rules select from the current root-cause table but the plan lacks
    (newest: every group; lifecycle: the representative of every cause without one). Existing groups, builds and
    install records are kept; gopls builds get the skip entries of the added groups; the addition is recorded under
    "extended". 1 when a plan is missing or a group needs a line the plan has no build for."""
    rows = cause_rows(CAMPAIGN)
    for label in todo:
        if not os.path.exists(plan_path(label)):
            logger.error("%s: no releases.json to extend", label)
            return 1
        doc = load_plan(label)
        have_gid, have_cause = {g["gid"] for g in doc["groups"]}, {g["cause"] for g in doc["groups"]}
        pool = rows if label != LIFECYCLE else representatives(rows)
        new = [r for r in pool if r["gid"] not in have_gid and (label != LIFECYCLE or r["cause"] not in have_cause)]
        if not new:
            logger.info("%s: nothing to add", label)
            continue
        missing = {r["line"] for r in new} - {b["line"] for b in doc["builds"]}
        if missing:
            logger.error("%s: the plan has no build for %s", label, ", ".join(sorted(missing)))
            return 1
        gids = [r["gid"] for r in new if r["line"] == "gopls"]
        for b in doc["builds"]:
            if b["kind"] == "gopls" and b["status"] == "ok" and gids:
                go, skip = go_skips(b["version"], gids)
                if go != b["go"]:
                    raise SystemExit(f"{label}: gopls {b['version']} now runs {go}, planned with {b['go']}")
                b["skip"] = dict(b.get("skip") or {}, **skip)
        doc["groups"] += new
        doc.setdefault("extended", []).append(
            {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "groups": [r["gid"] for r in new],
             "rule": REP_RULE if label == LIFECYCLE else "every group of triage/root_causes.csv",
             "why": "groups and causes added to the root-cause table after the plan (2026-11-21); the planned "
                    "builds and their install records are unchanged"})
        write_text(plan_path(label), json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        logger.info("%s: added %d group(s): %s", label, len(new), ", ".join(f"{r['cause']} {r['gid']}" for r in new))
    return 0


# ------------------------------------------------------------------ builds
def go_of(cmd: Sequence[str], env: Optional[Dict[str, str]] = None) -> str:
    """Last word of a `go version`/`go env GOVERSION` output (the Go version)."""
    out = subprocess.run(list(cmd), capture_output=True, text=True, timeout=120, env=env).stdout.split()
    return out[-1] if out else ""


def install_gopls(release: str) -> Tuple[str, str]:
    """(version, detail) of a gopls release by the toolchain rule in RULES["common"]."""
    era = read_toolchain("gopls", release) is not None
    if os.path.exists(os.path.join(servers.SERVERS_DIR, f"gopls-{release}", "gopls")) and not era:
        return release, "existing local-Go build"
    version = f"{release}+{go_of(['go', 'env', 'GOVERSION'])}" if era else release
    home = os.path.join(servers.SERVERS_DIR, f"gopls-{version}")
    try:
        if not os.path.exists(os.path.join(home, "gopls")):
            os.makedirs(home, exist_ok=True)
            ib._run(["go", "install", f"golang.org/x/tools/gopls@{release}"], f"gopls-{version}",
                    ib._gopls_env("", home, ""))
        return version, "local-Go build" + (" (beside the benchmark's era-Go build)" if era else "")
    except ib.InstallError as exc:
        if era:
            shutil.rmtree(home, ignore_errors=True)
            return release, f"existing era-Go build; the local Go cannot compile the release: {str(exc)[:240]}"
        detail = ib.install_gopls(release, go=ERA_GO).detail
        return release, f"the local Go cannot compile the release ({str(exc)[:240]}); {detail}"


def install_kind(b: Dict[str, Any]) -> Tuple[str, str]:
    """Install one build; (version, detail). InstallError when it cannot be installed."""
    kind, version = b["kind"], b["version"]
    if kind == "gopls":
        return install_gopls(b["release"])
    if kind == "ts7":  # npm typescript@7.x; servers_extra launches its native binary (tsc --lsp --stdio)
        prefix = os.path.join(servers.SERVERS_DIR, f"ts7-{version}")
        if ib._package_version(prefix, "typescript") != version:
            ib._npm_install(prefix, [f"typescript@{version}"], f"ts7-{version}")
        got = tuple(ib._package_version(prefix, p) for p in ("typescript", "@typescript/typescript-darwin-arm64"))
        if got != (version, version):
            raise ib.InstallError(f"ts7 {version}: installed typescript {got[0] or '-'}, "
                                  f"platform package {got[1] or '-'}")
        return version, f"npm typescript@{version} (@typescript/typescript-darwin-arm64@{version})"
    installer = {"rust-analyzer": ib.install_rust_analyzer, "tsserver": ib.install_tsserver,
                 "pyright": ib.install_pyright}[kind]
    return version, installer(version).detail


def smoke_error(kind: str, version: str) -> str:
    """Tail of the server's last error line in its smoke session log (why a launch check failed)."""
    log = os.path.join(REPO, "data", "lsptest", "logs", f"smoke-{kind}-{version}.jsonl")  # smoke_servers' session log
    try:
        with open(log, encoding="utf-8") as f:
            errs = [str(r.get("msg")) for r in map(json.loads, f)
                    if r.get("dir") == "stderr" and "error" in str(r.get("msg")).lower()]
    except (OSError, ValueError):
        return ""
    last = errs[-1].replace(tempfile.gettempdir(), "<tmp>").replace(os.path.expanduser("~"), "~") if errs else ""
    return last[-220:]


def install_build(b: Dict[str, Any]) -> Dict[str, Any]:
    """Install a build and run the launch check (initialize, diagnostics and hover); two attempts."""
    why = ""
    for attempt in (1, 2):
        try:
            version, detail = install_kind(b)
            smoke = smoke_servers.smoke(b["kind"], version, SMOKE[b["kind"]])
            if not smoke.get("ok"):
                raise RuntimeError("launch check failed (no diagnostics or hover on the smoke project): "
                                   f"{smoke.get('error') or smoke_error(b['kind'], version)}")
            out = dict(b, version=version, status="ok", detail=detail, attempts=attempt,
                       launch={k: smoke[k] for k in ("init_s", "ok", "diagnostics", "error") if k in smoke})
            if b["kind"] == "gopls":
                out["built_with"] = go_of(["go", "version", servers.resolve("gopls", version).cmd[0]])
            logger.info("%s %s: ok (%s)", b["kind"], version, detail[:160])
            return out
        except (ib.InstallError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            why = f"{type(exc).__name__}: {exc}"[:400]
            logger.warning("%s %s, attempt %d: %s", b["kind"], b["version"], attempt, why)
    return dict(b, status="unavailable", reason=why, attempts=2)


_PROJECT_GO: Dict[str, str] = {}


def project_go(gid: str) -> str:
    """Highest go directive among the go.mod/go.work files of a group's project."""
    if gid not in _PROJECT_GO:  # cleared by set_campaign
        doc, _ = load_repro(next(e for e in vs.group_repros(CAMPAIGN) if e["gid"] == gid)["repro"])
        root = project_dir(doc["project"]["source"], doc["project"]["ref"], os.path.join(REPO, "temp", "release_sweep"))
        found = ["0"]
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "vendor", "testdata")]
            for name in {"go.mod", "go.work"} & set(filenames):
                with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as f:
                    found += re.findall(r"(?m)^go\s+(\d+(?:\.\d+)*)\s*$", f.read())
        _PROJECT_GO[gid] = max(found, key=vkey)
    return _PROJECT_GO[gid]


def go_skips(version: str, gids: Sequence[str]) -> Tuple[str, Dict[str, str]]:
    """(Go the harness runs the gopls build with, {gid: reason} for the groups it cannot load)."""
    env = dict(os.environ, **servers.resolve("gopls", version).env)
    go = go_of([shutil.which("go", path=env.get("PATH")) or "go", "env", "GOVERSION"], env)
    return go, {gid: f"the project needs go {project_go(gid)}; the build runs {go} with GOTOOLCHAIN=local"
                for gid in gids if vkey(project_go(gid)) > vkey(go)}


def install(lines: Sequence[str]) -> int:
    """Install the planned builds of `lines`; record the outcome in both releases.json files."""
    done: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for label in labels():
        doc = load_plan(label)
        for i, b in enumerate(doc["builds"]):
            if b["line"] not in lines:
                continue
            if (b["kind"], b["release"]) not in done:
                done[(b["kind"], b["release"])] = install_build(b)
            nb = dict(done[(b["kind"], b["release"])], roles=b["roles"])
            if nb["kind"] == "gopls" and nb["status"] == "ok":
                gids = [g["gid"] for g in doc["groups"] if g["line"] == "gopls"]
                nb["go"], nb["skip"] = go_skips(nb["version"], gids)
            doc["builds"][i] = nb
        doc["installed"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        write_text(plan_path(label), json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    bad = [f"{k} {v}" for (k, v), d in done.items() if d["status"] != "ok"]
    logger.info("%d build(s) checked; unavailable: %s", len(done), ", ".join(bad) or "none")
    return 1 if bad else 0


__all__ = ["CAMPAIGN", "CAMPAIGNS", "FIRST_CAMPAIGN", "LABELS", "LIFECYCLE", "LINES", "NEWEST", "REPO", "RULES",
           "SWEEP", "install", "labels", "load_plan", "plan", "set_campaign", "write_text"]
