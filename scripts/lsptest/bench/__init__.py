"""Historical-bug benchmark (kickoff v3 contribution C3; design section 10).

One directory per bug under data/lsp_bench/cases/<server>-<number>/ (case.json + project/),
a hand-written ground-truth reproduction per case (model.Op list + one probe), pinned
pre-fix and post-fix builds, and a runner that decides `reproduced` only when the bug is
present 3/3 on the pre-fix build and 0/3 on the post-fix build.

- case_format:    case.json schema, loading, validation (provenance, ops, probe parameters)
- probes:         predicate library; pure decisions from normalized answers (PROBES registry)
- collect:        live sessions that gather the answers a probe needs (Driver-based)
- run_repro:      ground-truth runner (pre/post x 3 fresh runs) and the results files
- install_builds: historical builds under temp/lsp_servers/ (npm, release assets, era Go)
- sources:        issue text and linked-repository files (cached GitHub REST / raw)

Run line: not run directly; see run_repro.py and install_builds.py.
"""

__all__ = ["case_format", "collect", "install_builds", "probes", "run_repro", "sources"]
