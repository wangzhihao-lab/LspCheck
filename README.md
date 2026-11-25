# LspCheck: replication package

This package accompanies the paper *Testing Language Servers without Ground Truth: Functional
Relations over the Language Server Protocol* by Zhihao Wang, Min Ren, Xia Liang, Gaoyong Li, Ding Ding, and its supplemental material.
It contains the tool (LspCheck), the benchmark of historical language-server bugs, the data of the
two current-release campaigns on two corpora and of the benchmark campaign, the verdicts of both
raters and the verdicts they agreed on in discussion, the independent checks of the candidate bugs,
and the scripts that compute every number and appendix table of the paper from these data.

## Layout

| Path | Content |
|---|---|
| `scripts/lsptest/` | LspCheck: relations R0–R6, input generation, settling, stability filtering, replay, reduction, triage, campaigns, version sweeps. Frozen; `data/lsptest/freeze/` holds the sha256 manifests of the three freezes. |
| `scripts/lsp_repro/` | The LSP client and server launch layer the tool drives servers through (also frozen). |
| `scripts/lsp_pilot/`, `scripts/lsp_backfill/`, `scripts/lsp_bench/` | Mining of fixed-bug reports from the issue trackers and screening of benchmark candidates. |
| `scripts/paper/` | Numbers and tables of the paper (`paper_numbers.py` and the `numbers_*.py` modules it imports; `numbers_tex.py` turns the numbers into the macros the text reads), the judging pages of both raters and of the discussion and their import, the agreement, the figures, the selection and preparation of the second corpus (`corpus2/`), and `evidence/`, the checks of Appendices M and N (`evidence/second_corpus/` for the second corpus). |
| `data/lsp_bench/` | The benchmark: one directory per bug with its program, provenance and hand-written trigger (`cases/`), the screening funnel (`candidates.*`) and the reproduction results. See `data/lsp_bench/README.md`. |
| `data/lsp_pilot/`, `data/lsp_backfill/` | The fixed-bug lists and fix evidence the benchmark was mined from. |
| `data/lsptest/corpus.json`, `corpus_prepared.*` | The first corpus: 40 open-source projects (the ten most starred per language that pass the filters) with their pinned commits, and the probe of each project-server pair. |
| `data/lsptest/corpus_v2.json`, `corpus_v2_prepared.*` | The second corpus, the next ten per language from the same ranking, prepared with the same pipeline (`logs/prepare_corpus_v2/`); `corpus_v2_deps_manual.md` records the dependencies installed by hand. |
| `data/lsptest/campaigns/` | Campaign configurations: `main_v1` (first corpus) and `main_v2` (second corpus) on current releases, `bench_v1` on the benchmark, `recheck_main_v2` (a recomputation of a sample of `main_v2` runs), and the pre-freeze `dryrun` and `kb_pyright_8946`. |
| `data/lsptest/runs/main_v1/`, `runs/main_v2/` | The two current-release campaigns: run results, violations with their replay files, triage groups with reduced reproductions (`triage/<group>/repro.json`), the first author's verdicts (`triage/decisions.csv`, with a reason for every group, and `verdict_reasons.csv`), the second rater's verdicts (`triage/rater2_decisions.csv`, `rater2_reasons_en.csv`) and their agreement (`rater2_agreement.json`), the verdicts agreed in discussion (`triage/consensus.csv`, `consensus_reasons_en.csv`), the merge into distinct bugs (`triage/root_causes.csv`), the version sweeps (`sweep/`: year-old, newest and lifecycle releases) and the independent checks (`evidence/`). `main_v1/triage/rejudged.csv` records the two groups re-judged after the discussion; `main_v1/upstream/` the upstream reports. |
| `data/lsptest/runs/bench_v1/` | Benchmark campaign: runs, pre-only signatures, the detection table, the answers of both raters on the signatures (`detection_author.csv`, `detection_rater2.csv`), the agreed answers (`detection_consensus*.csv`) and the attribution of every missed bug (`missed_attribution.csv`). |
| `data/lsptest/adjudication/` | The outcome of the discussion of the items the raters judged differently, exported from the page they discussed them on: the agreed verdict of each item, whose verdict it follows and the reason (in Chinese; the reasons in English are in `triage/consensus_reasons_en.csv` and `bench_v1/detection_consensus_reasons_en.csv`). |
| `data/lsptest/root_cause_possible_merges.csv`, `root_cause_withdrawn.csv` | Bugs that could share a cause on present evidence, and the bug numbers withdrawn when their groups were re-judged (`rejudged.csv`). |
| `data/lsptest/paper_numbers.json` | Every number the paper reports, as computed by `scripts/paper/paper_numbers.py` from the files above. |
| `paper/numbers.tex` | The same numbers as LaTeX macros (`\N{key}`), written by `scripts/paper/numbers_tex.py`; the paper reads every number from this file. |
| `paper/appendix/tables/` | The appendix tables as CSV and Markdown, written by `paper_numbers.py`. |
| `MANIFEST.sha256` | sha256 of every file in the package. |

## Checks that need no language server

All scripts use only the Python 3 standard library (tested with Python 3.14.7) and are run from
the package root.

```
python3 scripts/paper/verify_manifest.py                 # every file matches MANIFEST.sha256
python3 scripts/lsptest/freeze_tool.py check v3          # the tool is the frozen version used for all results
python3 scripts/paper/paper_numbers.py                   # recompute every number and appendix table from data/
python3 scripts/paper/numbers_tex.py                     # write paper/numbers.tex from the recomputed numbers
python3 -m unittest discover -s scripts/paper/tests      # tests of the number and judging scripts
python3 -m unittest discover -s scripts/lsptest/tests    # tool tests
```

`paper_numbers.py` rewrites `data/lsptest/paper_numbers.json`; apart from the `sources` digests,
the file it writes is the one shipped here, and `numbers_tex.py` then writes a `paper/numbers.tex`
identical to the one shipped. The campaign plans depend on the corpus clones; without them the
script reads the plan exported next to each campaign (`plan_specs.jsonl`). One tool test,
`test_r4_mutations.PlanTests`, parses TypeScript with the TypeScript 6.0.3 package and fails until
that package is installed (step 1 below); the other tests need no server.

## Rerunning with language servers

Rerunning needs macOS or Linux, git, Node.js 24 with npm, Go 1.27, a Rust toolchain installed with
rustup, network access for the installs and about 30 GB of disk. Server builds and project clones
go to `temp/`, which the scripts create.

1. Install the server builds. The campaign builds:
   ```
   npm install --prefix temp/lsp_servers/pyright-1.1.414 pyright@1.1.414
   npm install --prefix temp/lsp_servers/ts6-6.0.3 typescript@6.0.3 typescript-language-server@6.0.0
   npm install --prefix temp/lsp_servers/ts7-7.0.2 typescript@7.0.2
   python3 scripts/lsptest/bench/install_builds.py gopls v0.23.0
   python3 scripts/lsptest/bench/install_builds.py rust-analyzer 2026-09-21
   ```
   The benchmark's pre-fix and post-fix builds: `python3 scripts/lsptest/bench/install_builds.py --all`
   (or `--case data/lsp_bench/cases/<id>`). When a build is missing, the launcher stops with the command
   that installs it. rust-analyzer builds are the release assets for Apple silicon macOS
   (`aarch64-apple-darwin`); on other platforms change the asset name in `install_builds.py`.
2. Clone the corpora at their pinned commits: `python3 scripts/lsptest/prepare_corpus.py` (first corpus)
   and `python3 scripts/paper/corpus2/prepare_corpus2.py` (second corpus, the same pipeline). Some
   projects of the second corpus need the dependencies recorded in `data/lsptest/corpus_v2_deps_manual.md`.
3. Replay one reduced finding in fresh sessions:
   `python3 scripts/lsptest/repro_violation.py data/lsptest/runs/<campaign>/triage/<group>/repro.json`.
   Appendix H of the supplemental material names the representative group of each distinct bug.
4. Rerun a campaign: `python3 scripts/lsptest/campaign.py data/lsptest/campaigns/<id>.json`
   (resumable), then `python3 scripts/lsptest/triage.py <id>` for grouping and reduction, and
   `python3 scripts/lsptest/campaign_detect.py bench_v1` for the detection table.
5. Replay the triage groups on other releases: `python3 scripts/lsptest/version_sweep.py`
   (see its docstring). Do not run two sweeps of the same group at the same time: a sweep names
   the session directories of a group after the group and removes them when the group ends.
6. The checks of Appendices M and N: `scripts/paper/evidence/*.py` and `scripts/paper/evidence/second_corpus/*.py`;
   each docstring gives its run line. The replays on the newest, lifecycle and older releases are
   `scripts/paper/evidence/release_sweep.py` (plan, install, run, summarize).
7. The evaluation figures and the table of candidate bugs: `python3 scripts/paper/figures/fig_rq1_overlap.py`,
   `fig_rq2_over_time.py` and `fig_rq3_lifecycle.py` read `data/lsptest/figure_data.json`, which `paper_numbers.py`
   writes; `python3 scripts/paper/table_bugs.py` writes the table. The upstream reports and the maintainers' responses
   are in `data/lsptest/runs/main_v1/upstream/` (see its README); they are additional information only.

Timing-dependent results can differ between machines and loads; the harness settles every
session, compares only answers that two fresh sessions give alike, and confirms every violation
in three fresh replays.

## What was changed for publication

Text that identifies the machine the study ran on was replaced by placeholders in the files of
`data/`: paths inside the project became relative to the package root, the home directory became
`~`, this machine's temporary directories `<tmp>` and the account name `user`, also where a path was
written lower-cased, JSON-escaped or URL-encoded. Status lines of a local job scheduler in some run
logs became `<scheduler message>`. The plan of `main_v2` (`plan_specs.jsonl`) was
exported when the package was built, with the frozen tool and the corpus clones. No other content
was changed: the code of the tested projects, the mined issue text and the files of `data/` are
otherwise the ones the paper's numbers were computed from.

## Licenses

Code: MIT License (`LICENSE`). Data: Creative Commons Attribution 4.0 (`LICENSE-DATA.md`), except
the benchmark programs and issue excerpts, which are derived from public issue reports and keep
the terms of their sources; each case records its provenance in `case.json`.
