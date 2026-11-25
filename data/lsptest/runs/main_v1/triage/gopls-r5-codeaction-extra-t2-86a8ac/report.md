# [gopls v0.23.0] codeAction adds entries after transformation T2

Draft for the author (not filed). Group `gopls-r5-codeaction-extra-t2-86a8ac`, signature `gopls|r5_transforms|codeAction:extra`, case family `T2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `router-for-me/CLIProxyAPI@673131f57484` (corpus, commit 673131f57484517c3a1eae7e36c4cfa7b9bb4efc), language go

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T2 applied to `internal/signature/kimi_validation_test.go` (1 edit(s), first [12, 0, 12, 0]).
3. Query `textDocument/codeAction` on `internal/signature/kimi_validation_test.go` line 26, column 20 (LSP position {line: 25, character: 19}) (pos); compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Browse arm64 assembly for kimiSignatureCorpusPath",
  "source.assembly"
 ],
 [
  "Browse documentation for func os.Stat",
  "source.doc"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Inline call to Stat",
  "refactor.inline.call"
 ],
 [
  "Show compiler optimization details for \"signature\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"signature\"",
  "source.splitPackage"
 ]
]
```

Actual:

```json
[
 [
  "Browse arm64 assembly for kimiSignatureCorpusPath",
  "source.assembly"
 ],
 [
  "Browse documentation for func os.Stat",
  "source.doc"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Inline call to Stat",
  "refactor.inline.call"
 ],
 [
  "Organize Imports",
  "source.organizeImports"
 ],
 [
  "Show compiler optimization details for \"signature\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"signature\"",
  "source.splitPackage"
 ]
]
```

Project file `internal/signature/kimi_validation_test.go`:

```
  10 | 	"strings"
  11 | 	"testing"
  12 | )
     ...
  14 | // kimiSignatureCorpusPath locates the harvested Kimi signature corpus. The
  15 | // corpus lives with the collection skill that produced it and is not tracked in
  16 | // this repository, matching how the Grok and Gemini native corpora are handled:
     ...
  23 | 	}
  24 | 	repo := filepath.Clean(filepath.Join(filepath.Dir(file), "..", ".."))
  25 | 	path := filepath.Join(repo, ".agents", "skills", "cpa-signature-catalog-and-collection", "data", "signatures", "kimi", "samples.json")
  26 | 	if _, err := os.Stat(path); err != nil {
  27 | 		return path, false
  28 | 	}
  29 | 	return path, true
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r5-codeaction-extra-t2-86a8ac/repro.json
```

## Evidence and reduction

- representative 4b8ebf18dab2-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects junegunn/fzf@b1be3a8be1b8, router-for-me/CLIProxyAPI@673131f57484, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#64936](https://github.com/golang/go/issues/64936) x/tools/gopls: support for comment rendering (open, 2024-01-02, 9 comments)
- [golang/go#43735](https://github.com/golang/go/issues/43735) x/tools/gopls: rearranging struct fields deletes comments (open, 2021-01-15, 7 comments)
- [golang/go#48200](https://github.com/golang/go/issues/48200) x/tools/gopls: show full comments for constant or variable declaration (open, 2021-09-05, 3 comments)
- [golang/go#44684](https://github.com/golang/go/issues/44684) x/tools/gopls: add an option to keep original line breaks in documentation comments (open, 2021-02-28, 5 comments)
- [golang/go#74607](https://github.com/golang/go/issues/74607) x/tools/gopls: Semantic tokens not generated for local unexported symbols referenced in comment links (open, 2025-07-14, 2 comments)
- [golang/go#70085](https://github.com/golang/go/issues/70085) x/tools/gopls: add refactor.inline.variable-all code action (open, 2024-10-29, 11 comments)
- [golang/go#39805](https://github.com/golang/go/issues/39805) x/tools/gopls: convert 'gofumpt' from formatter to code action provider (open, 2020-06-24, 5 comments)
- [golang/go#56403](https://github.com/golang/go/issues/56403) x/tools/gopls: allow enabling gofumpt extra rules (open, 2022-10-24, 5 comments)
- queries: `comment in:title repo:golang/go is:issue label:gopls`; `"code action" extra repo:golang/go is:issue label:gopls`; `"code action" comment repo:golang/go is:issue label:gopls`; `"code action" whitespace repo:golang/go is:issue label:gopls`
