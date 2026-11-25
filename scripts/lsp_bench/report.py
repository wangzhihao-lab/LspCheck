"""Write data/lsp_bench/candidates.md from the ranked candidate rows.

Sections: counts (retrieved vs kept per server and oracle class, reject codes,
builds, mapping confidence), the top-80 table, and method notes (exact keyword
patterns, label rules, screening protocol, version mapping, ranking,
uncertainties).

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

import collections
from datetime import date
from pathlib import Path
from typing import Dict, List, Sequence

from decisions import REJECT_CODES
from patterns import LABEL_RULES, PAIR_WINDOW, PAIRS, ROUND2_CHANGES, SINGLE
from recall_audit import AUDITS, INCLUDE, PER_SERVER, summary as audit_summary
from gopls_builds import load_results as load_build_results
from rank import CONF_POINTS, GRADE_POINTS, PER_SERVER_MIN, SUBTYPE_PENALTY, TOP_N

CLASSES = ["R1", "R2", "R3", "R4", "R5"]


def _counts_table(servers: Sequence[str], retrieved: Dict[str, List[dict]], rows: List[dict],
                  totals: Dict[str, int]) -> List[str]:
    out = ["| server | issues since 2019 | retrieved | kept | " + " | ".join(f"{c} retrieved / kept" for c in CLASSES) + " |",
           "|---|---:|---:|---:|" + "---:|" * len(CLASSES)]
    for s in servers:
        ret = retrieved[s]
        kept = [r for r in rows if r["server"] == s]
        cells = []
        for c in CLASSES:
            nr = sum(1 for r in ret if c in {h[0] for h in r["hits"]})
            nk = sum(1 for r in kept if r["oracle_class"] == c)
            cells.append(f"{nr} / {nk}")
        out.append(f"| {s} | {totals[s]} | {len(ret)} | {len(kept)} | " + " | ".join(cells) + " |")
    all_ret = sum(len(retrieved[s]) for s in servers)
    cells = [f"{sum(1 for s in servers for r in retrieved[s] if c in {h[0] for h in r['hits']})} / "
             f"{sum(1 for r in rows if r['oracle_class'] == c)}" for c in CLASSES]
    out.append(f"| **all** | {sum(totals.values())} | {all_ret} | {len(rows)} | " + " | ".join(cells) + " |")
    return out


def _cross(rows: List[dict], servers: Sequence[str], field: str, values: Sequence[str]) -> List[str]:
    out = [f"| server | " + " | ".join(values) + " |", "|---|" + "---:|" * len(values)]
    for s in servers:
        c = collections.Counter(str(r[field]) for r in rows if r["server"] == s)
        out.append(f"| {s} | " + " | ".join(str(c.get(v, 0)) for v in values) + " |")
    return out


def _top_table(rows: List[dict]) -> List[str]:
    out = ["| rank | server | issue | title | class | trigger | grade | pre -> post | conf | tests | score | screening note |",
           "|---:|---|---|---|---|---|---|---|---|---|---:|---|"]
    for r in rows:
        if not r["top80"]:
            continue
        title = str(r["title"]).replace("|", "\\|")[:70]
        num = r["number"]
        link = f"[#{num}]({r['url']})"
        tests = {True: "yes", False: "no"}.get(r.get("fix_touches_tests"), "?")
        out.append(f"| {r['scriptability_rank']} | {r['server']} | {link} | {title} | {r['oracle_class']} | "
                   f"{r['subtype']} | {r['grade']} | {r['pre_version']} -> {r['post_version']} | "
                   f"{r['mapping_confidence']} | {tests} | {r['score']} | {_short(str(r['screening_reason']))} |")
    return out


def _short(text: str, limit: int = 140) -> str:
    """One-line, pipe-safe excerpt for a table cell."""
    t = " ".join(text.split()).replace("|", "\\|")
    return t if len(t) <= limit else t[: limit - 3].rstrip() + "..."


def _residual_estimate(servers: Sequence[str], retrieved: Dict[str, List[dict]], totals: Dict[str, int]) -> str:
    """Stratified estimate of candidates still missed, from the latest audit."""
    seed = max(AUDITS)
    rnd, misses = AUDITS[seed]
    parts = []
    total = 0.0
    for s in servers:
        pool = totals[s] - len(retrieved[s])
        est = pool * len(misses.get(s, {})) / PER_SERVER
        total += est
        parts.append(f"{s} {len(misses.get(s, {}))}/{PER_SERVER} of {pool} non-retrieved, about {est:.0f}")
    return (f"Residual estimate from the latest audit (seed {seed}, {rnd} patterns), stratified by server: "
            + "; ".join(parts) + f"; about {total:.0f} kept-worthy issues in total remain unretrieved, with wide "
            "intervals at 40 samples per server.")


def _cached_calls() -> str:
    """Count cached responses by host."""
    import json as _json
    from paths import HTTP_CACHE_DIR
    counts: Dict[str, int] = collections.Counter()
    for p in HTTP_CACHE_DIR.glob("*.json"):
        try:
            url = _json.loads(p.read_text(encoding="utf-8")).get("url", "")
        except (OSError, ValueError):
            continue
        host = url.split("/")[2] if url.count("/") >= 2 else "?"
        counts[host] += 1
    return ", ".join(f"{n} responses from {h}" for h, n in sorted(counts.items())) or "no cached responses"


def _build_check_summary() -> str:
    """One sentence on the cached gopls build-check results."""
    res = load_build_results()
    if not res:
        return "No build-check results were available for this run."
    local = sum(1 for v in res.values() if v["ok"] and str(v["toolchain"]).startswith("local"))
    older = sum(1 for v in res.values() if v["ok"] and not str(v["toolchain"]).startswith("local"))
    failed = sorted((k for k, v in res.items() if not v["ok"]), key=lambda k: [int(x) for x in k[1:].split(".")])
    return (f"Of {len(res)} gopls versions checked, {local} built with the local toolchain, {older} only with an older "
            f"downloaded toolchain, and {len(failed)} did not build" + (f" ({', '.join(failed)})." if failed else "."))


def _patterns_block() -> List[str]:
    out = ["Single patterns (a match anywhere in title, cleaned body or fix-commit subject):", "", "```"]
    for oracle, pid, rx in SINGLE:
        out.append(f"{oracle} {pid}: {rx}")
    out += ["```", "", f"Pair patterns (feature and symptom within {PAIR_WINDOW} characters of each other):", "", "```"]
    for oracle, pid, feat, symp in PAIRS:
        out.append(f"{oracle} {pid}:\n  feature: {feat}\n  symptom: {symp}")
    out += ["```", "", "Label rules (retrieve on the label alone):", ""]
    for server, rules in LABEL_RULES.items():
        if rules:
            out.append(f"- {server}: " + "; ".join(f"`{lab}` -> {o}" for lab, o in rules))
    return out


def write_report(path: Path, servers: Sequence[str], rows: List[dict], retrieved: Dict[str, List[dict]],
                 rejects: Dict[str, Dict[str, int]], totals: Dict[str, int], api: Dict[str, int]) -> None:
    """Render the markdown summary."""
    top = [r for r in rows if r["top80"]]
    n_other_route = sum(1 for r in rows if r["subtype"] == "other-route")
    n_outside = sum(1 for r in rows if "outside" in str(r["trigger_hint"]).lower())
    n_ca_other = sum(1 for r in rows if r["subtype"] == "codeaction-other")
    lines: List[str] = [
        "# LSP history-bug benchmark: candidate list",
        "",
        f"Generated {date.today().isoformat()} by `scripts/lsp_bench/mine_candidates.py`. "
        "Scope: pyright, tsserver (TypeScript up to 6.x), rust-analyzer, gopls; fixed-bug issues created on or after "
        "2019-01-01 from `data/lsp_pilot/*_fixed_bugs.jsonl`; oracle classes R1-R5 of `plan/tool_design_v1.md` section 5 "
        "(refactoring correctness out of scope). One JSON object per kept candidate is in `candidates.jsonl`.",
        "",
        "Regenerate: `python3 scripts/lsp_bench/mine_candidates.py all` (retrieval, then build). Network is used only "
        "for uncached GitHub REST, npm registry and Go proxy lookups; caches and clones live under `temp/lsp_bench/`.",
        "",
        "## Counts",
        "",
        "Retrieved = at least one keyword or label pattern of that class matched (an issue can match several classes). "
        "Kept = read and judged to plausibly fit that class (primary class only).",
        "",
    ]
    lines += _counts_table(servers, retrieved, rows, totals)
    lines += ["", "Kept candidates by screening grade (A: self-contained snippet and steps; B: needs reconstruction; "
              "C: vague, intermittent or editor-specific):", ""]
    lines += _cross(rows, servers, "grade", ["A", "B", "C"])
    codes = list(REJECT_CODES)
    lines += ["", "Retrieved but rejected, by reason code:", "",
              "| server | " + " | ".join(codes) + " |", "|---|" + "---:|" * len(codes)]
    for s in servers:
        lines.append(f"| {s} | " + " | ".join(str(rejects[s].get(c, 0)) for c in codes) + " |")
    lines += ["", "Codes: " + "; ".join(f"`{k}` {v}" for k, v in REJECT_CODES.items()) + ".", ""]
    lines += ["Version mapping and builds (kept candidates):", ""]
    b_rows = ["| server | kept | both builds obtainable | confidence high | medium | low | none | regression not in any release |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s in servers:
        k = [r for r in rows if r["server"] == s]
        conf = collections.Counter(r["mapping_confidence"] for r in k)
        b_rows.append(f"| {s} | {len(k)} | {sum(1 for r in k if r['builds_obtainable'])} | {conf['high']} | "
                      f"{conf['medium']} | {conf['low']} | {conf['none']} | {sum(1 for r in k if r.get('no_released_bug'))} |")
    lines += b_rows
    comp = collections.Counter((r["server"], r["oracle_class"]) for r in top)
    lines += ["", f"## Top {TOP_N} by scriptability", "",
              "Composition (server x class): " + "; ".join(
                  f"{s} {sum(v for (ss, _), v in comp.items() if ss == s)} ("
                  + ", ".join(f"{c} {comp[(s, c)]}" for c in CLASSES if comp[(s, c)]) + ")" for s in servers) + ".",
              "", "`trigger` is the screening subtype of the class (see method notes); `tests` says whether the fix "
              "changed test files; the full note for each row is in `candidates.jsonl` (`notes`, `trigger_hint`).", ""]
    lines += _top_table(rows)
    lines += ["", "## Method notes", "", "### Retrieval", ""]
    lines += ["Searched text per issue: title, body excerpt cleaned of template headings, HTML comments, `go env`/build-info "
              "dumps and tsserver log lines, and the subjects of the fix commits (backfill for pyright and gopls; merge or "
              "squash commits of the closing PRs, located in the local clones, for tsserver and rust-analyzer). Bodies in the "
              "pilot files are truncated at 2,000 characters; for gopls the truncation often leaves only the environment dump, "
              "so the fix commit subject and message carried most of the signal during screening.", ""]
    lines += _patterns_block()
    lines += ["", "### Recall audits and pattern revision", "",
              f"Two audits each read a seeded random sample of {PER_SERVER} non-retrieved issues per server "
              "(`scripts/lsp_bench/recall_audit.py`). Audit 1 ran against the first pattern set; its misses were all "
              "edit-validity (R4) reports whose wording the first set lacked, so the patterns were revised (round 2, below) "
              "and the newly retrieved issues were screened like the rest. Audit 2 ran against the revised patterns. Misses "
              "that no pattern retrieves are added to the retrieved set with pattern id `audit` ("
              + ", ".join(f"{s} " + ", ".join(f"#{n}" for n in sorted(v)) for s, v in INCLUDE.items()) + ").", ""]
    lines += audit_summary()
    lines += ["", "Round-2 pattern revisions:", ""]
    lines += [f"- `{pid}`: {what}" for pid, what in ROUND2_CHANGES.items()]
    lines += ["", _residual_estimate(servers, retrieved, totals),
              "", "### Screening", "",
              "Every retrieved issue was read (title, labels, cleaned body excerpt, fix subject; for gopls also the fix commit "
              "message; full bodies and commit messages when the excerpt was not enough) and decided once: kept with a primary "
              "class, a grade, one factual sentence and a trigger hint, or rejected with one reason code. Decisions are in "
              "`scripts/lsp_bench/decisions/*.py`; the build step fails unless every retrieved issue is decided exactly once. "
              "Trigger subtypes: R1 edit-undo, typing, open-close, file-op, config, dependency-edit, query-order, race; "
              "R2 resolve, semtok-delta, stale-edit; R3 pull-push, semtok-range, highlight-refs, def-consistency, other-route; "
              "R4 quickfix, codeaction-other, format, completion, organize; R5 blank-lines, comment, whitespace, crlf, "
              "non-ascii, file-edge.", ""]
    lines += ["### Version mapping", "",
              "`mapping_confidence`: high = the release window comes from git ancestry of the located fix commit (or, for "
              "pyright without a commit, the maintainer's release comment) and the cross-checks agree (compare API for "
              "tsserver and gopls, npm publish date after the merge); medium = window from the pyright label event, a "
              "cross-check disagrees, a fix spans releases, or no earlier release exists; low = close-date heuristic or the fix "
              "is in no release yet; none = no fix commit or PR could be located.", "",
              "- **pyright**: fix commits = squash commit of a merged closing PR, `closer_commit`, backfilled commits (merges "
              "excluded). post = lowest `1.0.x`/`1.1.x` tag containing every fix commit (`git tag --contains`), pre = highest release below "
              "it containing none. Without a fix commit: the maintainer's comment naming the release (issue comments API, high), "
              "else the first npm release after the `addressed in next version` label event (issue events API, medium), else the "
              "latest release before the issue closed (low). Versions checked against `npm view pyright time --json`; the npm package "
              "ships `pyright-langserver` only from 1.1.52, so windows starting earlier are marked not obtainable from npm "
              "(the same-version VS Code extension or a build of the git tag would be needed). A 1.1.80 language server was "
              "started on the local Node 24 as a smoke test.",
              "- **tsserver**: squash commit of the merged closing PR on main plus release-branch picks (`Pick PR #N`, "
              "`Cherry-pick PR #N`) in a treeless clone; post = lowest stable `vX.Y.Z` tag (X < 7) containing one of them, pre = "
              "highest stable release below post containing none; both nearest tags confirmed with the GitHub compare API "
              "(base=tag, head=squash commit; `behind`/`identical` = contained; a pick makes the post tag `diverged`). Merge date "
              "checked against `npm view typescript time --json`. A tighter nightly window (`X.Y.Z-dev.YYYYMMDD` whose published "
              "`gitHead` does / does not contain the fix) is recorded in `mapping_extra`. tsserver is not an LSP server; `build_notes` "
              "names the typescript-language-server release contemporary with the post-fix build as the wrapper (pairing untested).",
              "- **rust-analyzer**: merge commit of the closing PR (`Merge pull request #N`, bors `Merge #N`, homu `Auto merge of "
              "#N`) in a treeless clone, else `closer_commit`; post = earliest weekly date tag containing it, pre = latest date tag "
              "before post not containing it; the date rule (last release on or before the merge day, first after it) is "
              "recorded and differs in the rows flagged `date_rule_differs`. Builds: the release must carry "
              "`rust-analyzer-aarch64-apple-darwin.gz` (GitHub releases API); that asset exists from 2020-12-28 on, and when the exact "
              "pre or post release lacks it (e.g. 2024-09-23) the window is widened to the nearest release that has it (`mapping_extra`).",
              "- **gopls**: fix = `closer_commit` (golang/tools), else the backfilled commit saying `Fixes golang/go#N`; "
              "cherry-picks found by `[gopls-release-branch.0.X]` subject. A release contains the fix when the fix (or a pick) is "
              "an ancestor of its `gopls/vX.Y.Z` tag and, for fixes outside `gopls/`, of the x/tools commit pinned in that "
              "release's `go.mod` (proxy.golang.org); v0.1.x have no tag and use the pinned commit. The two nearest tags are "
              "confirmed with the compare API. Builds: module versions on proxy.golang.org (`go install "
              "golang.org/x/tools/gopls@vX.Y.Z`); `build_notes` gives each release's `go` directive and the newest Go release "
              "at its date. Every pre/post version was compiled (`gopls_builds.py`): first with the local Go, using a wrapper "
              "module for v0.1.0-v0.5.3 and v0.6.8 (their go.mod has `replace golang.org/x/tools => ../`, which `go install` "
              "refuses since Go 1.16), then with downloaded toolchains (`GOTOOLCHAIN` = the release's go.mod version, the .0 release "
              "of its Go era, go1.21.0; never below the go.mod version); the toolchain that worked is in "
              "`build_notes`. " + _build_check_summary(),
              ""]
    lines += ["### Ranking", "",
              f"score = grade ({', '.join(f'{k} {v:+d}' for k, v in GRADE_POINTS.items())}) + 20 if both builds are obtainable "
              f"+ mapping confidence ({', '.join(f'{k} {v:+d}' for k, v in CONF_POINTS.items())}) + 5 if the fix changed tests; "
              "the issue body itself is not scored (pilot bodies are truncated at 2,000 characters, which removes the "
              "reproduction from most gopls reports), the screening grade carries reproduction quality; penalties "
              f"{', '.join(f'{k} {v:+d}' for k, v in SUBTYPE_PENALTY.items())}, -3 if the needed transformation is outside "
              "T1-T3, -4 for telemetry-only reports, -2 per set-up "
              "marker for environment set-up in the trigger hint or note (needs/requires, cargo check/flycheck, third-party, install, "
              "proc macro, build script, vendor, module cache, large project, checkout; at most -4; configuration and file "
              "operations are not penalised because they are ordinary R1 history steps). Many candidates tie at the top score, so the "
              "tie-break matters: within a score, servers are interleaved and, within a server, oracle classes are interleaved "
              "(rarer class first, each ordered by more recent fix). "
              "Top 80: the best "
              f"{PER_SERVER_MIN} per server among candidates with both builds and a bug present in a released pre-fix build, "
              "then the best remaining scores; `scriptability_rank` orders the top 80 first, then the rest.", ""]
    lines += ["### Uncertainties", "",
              f"- Screening is a single reading per slice; borderline keeps are graded C and described in `notes`. Several "
              "R4 keeps need the edit-validity check to count type errors (unresolved imports) rather than syntax errors only, "
              f"and the {n_ca_other} `codeaction-other` keeps are not diagnostic-attached quick fixes, so R4(a) as designed would not apply them.",
              f"- {n_outside} keeps (mostly R5) need a transformation outside T1-T3 (LF to CRLF, same-line non-ASCII text, "
              f"trailing newline at EOF, same-line trailing comment); their hints say so. {n_other_route} R3 keeps use a route "
              "pair outside the four designed checks (`other-route`).",
              "- pyright: most `addressed in next version` issues have no commit that names them; those windows rest on the "
              "maintainer's release comment or on the label event (medium confidence). The label is sometimes added before the "
              "fix is committed, so `post` can be one release early when the fix lands after the next release is cut.",
              "- Regressions introduced and fixed between two consecutive releases have no released pre-fix build with the bug "
              "(`no_released_bug`); a build of the fix's parent commit would be needed.",
              "- gopls releases before v0.2.0 have no tag in golang/tools; issues fixed before v0.1.0 have no released pre-fix "
              "build. The build check compiles each release but does not run it: old gopls drives the `go` command found on "
              "PATH, so a benchmark run should put a Go of the release's era on PATH (see `build_notes`).",
              "- tsserver fixes merged after the 6.0 branch cut that only ship in 7.x (native) are out of scope and have no build.",
              f"- Network use: {_cached_calls()} (each fetched once and cached under `temp/lsp_bench/cache/http`); this run "
              f"made {api.get('github_calls', 0)} uncached GitHub calls and {api.get('other_calls', 0)} other uncached calls.",
              ""]
    path.write_text("\n".join(lines), encoding="utf-8")
