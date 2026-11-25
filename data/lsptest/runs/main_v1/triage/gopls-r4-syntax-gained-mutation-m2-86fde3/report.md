# [gopls v0.23.0] mutation:M2 edit is not valid (syntax:gained)

Draft for the author (not filed). Group `gopls-r4-syntax-gained-mutation-m2-86fde3`, signature `gopls|r4_edits|syntax:gained`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `junegunn/fzf@b1be3a8be1b8` (corpus, commit b1be3a8be1b833ce5b92fbbac11637643d60a046), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/pattern_test.go`
3. textDocument/didChange: `change src/pattern_test.go (162, 9)-(162, 21) "buildPttern"`
4. textDocument/didChange: `change src/pattern_test.go (182, 5)-(182, 5) "buildPttern(true1 bool, result, *[]int func(caseSensitive bool, normalize bool, forward bool, input *util.Chars, pattern []rune, withPos bool, slab *util.Slab) (algo.Result, *[]int), extended bool, CaseSmart Case, false1, true2, false2, true3 bool, range []Range, delimiter Delimiter, r []rune) any {\n\tpanic(\"unimplemented\")\n}\n\nfunc "`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/reader.go`, `src/util/concurrent_set.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `syntax` on `src/pattern_test.go` line 163, column 10 (LSP position {line: 162, character: 9}) (M2:quickfix-syntax:Create function buildPttern); compare with the same query in a fresh session on the same content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 "expected ')', found bool",
 "expected ';', found ','",
 "expected declaration, found 'for'",
 "expected declaration, found extended",
 "expected declaration, found runtime",
 "expected declaration, found runtime",
 "missing ',' in parameter list",
 "missing parameter name"
]
```

Project file `src/pattern_test.go`:

```
 161 | func TestCacheKey(t *testing.T) {
 162 | 	test := func(extended bool, patStr string, expected string, cacheable bool) {
 163 | 		pat := buildPattern(true, algo.FuzzyMatchV2, extended, CaseSmart, false, true, false, true, []Range{}, Delimiter{}, []rune(patStr))
 164 | 		if pat.CacheKey() != expected {
 165 | 			t.Errorf("Expected: %s, actual: %s", expected, pat.CacheKey())
 166 | 		}
     ...
 180 | 	test(true, "| | | foo", "foo", false)
 181 | }
     ...
 183 | func TestCacheable(t *testing.T) {
 184 | 	test := func(fuzzy bool, str string, expected string, cacheable bool) {
 185 | 		pat := buildPattern(fuzzy, algo.FuzzyMatchV2, true, CaseSmart, true, true, false, true, []Range{}, Delimiter{}, []rune(str))
 186 | 		if pat.CacheKey() != expected {
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r4-syntax-gained-mutation-m2-86fde3/repro.json
```

## Evidence and reduction

- representative 9bb8ccd49c7b-v02: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 4.49 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects junegunn/fzf@b1be3a8be1b8, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#79772](https://github.com/golang/go/issues/79772) go/types: SEGV in tpWalker.isParameterized, case Signature (open, 2026-06-01, 1 comments)
- [golang/go#73779](https://github.com/golang/go/issues/73779) x/tools/gopls: ChangeSignature: "cannot inline: corrupted reference" bug (open, 2025-05-19, 1 comments)
- [golang/go#73874](https://github.com/golang/go/issues/73874) x/tools/gopls: Completion: add description to suggested function literals (open, 2025-05-27, 4 comments)
- [golang/go#69626](https://github.com/golang/go/issues/69626) x/tools/gopls: usePlaceholders=false disables variable name suggestions when using the var! suffix completion  (open, 2024-09-25, 4 comments)
- [golang/go#70603](https://github.com/golang/go/issues/70603) x/tools/gopls: DidOpen (et al?) fail to reject non-absolute path from client early, triggering assertion failure (open, 2024-11-27, 20 comments)
- [golang/go#79892](https://github.com/golang/go/issues/79892) x/tools/gopls: mcp go_diagnostics misattributes diagnostics to files[0] (and drops its own) when given multiple files (closed, 2026-06-07, 2 comments)
- [golang/go#68026](https://github.com/golang/go/issues/68026) x/tools/gopls: broken hovering in the builtin file (closed, 2024-06-16, 11 comments)
- [golang/go#32209](https://github.com/golang/go/issues/32209) x/tools/gopls: doesn't work well when jumping to definitions through the module cache (closed, 2019-05-23, 22 comments)
- queries: `syntax unexpected repo:golang/go is:issue label:gopls`; `syntax "wrong edit" repo:golang/go is:issue label:gopls`
