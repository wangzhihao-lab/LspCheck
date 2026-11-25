# [gopls v0.23.0] semanticTokens changes its answer after transformation T4

Draft for the author (not filed). Group `gopls-r5-semantictokens-changed-t4-b423af`, signature `gopls|r5_transforms|semanticTokens:changed`, case family `T4`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `docker/compose@c6dffb26bdfd` (corpus, commit c6dffb26bdfd94efb1f4e1c743f1241a150d120a), language go

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T4 applied to `internal/tracing/mux.go` (69 edit(s), first [0, 2, 0, 2]).
3. Query `textDocument/semanticTokens/full` on `internal/tracing/mux.go` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  0,
  2,
  "comment",
  ""
 ],
 [
  1,
  0,
  44,
  "comment",
  ""
 ],
 [
  10,
  0,
  68,
  "comment",
  ""
 ],
 [
  11,
  0,
  75,
  "comment",
  ""
 ],
 [
  12,
  0,
  70,
  "comment",
  ""
 ],
 [
  13,
  0,
  33,
  "comment",
  ""
 ],
 [
  14,
  0,
  2,
  "comment",
  ""
 ],
 [
  16,
  0,
  7,
  "keyword",
  ""
 ],
 [
  16,
  8,
  7,
  "namespace",
  ""
 ],
 [
  18,
  0,
  6,
  "keyword",
  ""
 ],
 [
  19,
  2,
  7,
  "namespace",
  ""
 ],
 [
  20,
  2,
  6,
  "namespace",
  ""
 ],
 [
  21,
  2,
  4,
  "namespace",
  ""
 ],
 [
  23,
  1,
  8,
  "namespace",
  ""
 ],
 [
  26,
  0,
  4,
  "keyword",
  ""
 ],
 [
  26,
  17,
  6,
  "keyword",
  ""
 ],
 [
  26,
  5,
  11,
  "type",
  "definition,struct"
 ],
 [
  27,
  1,
  9,
  "property",
  "definition,slice"
 ],
 [
  27,
  13,
  8,
  "namespace",
  ""
 ],
 [
  27,
  22,
  12,
  "type",
  "interface"
 ],
 [
  3,
  0,
  66,
  "comment",
  ""
 ],
 [
  30,
  0,
  4,
  "keyword",
  ""
 ],
 [
  30,
  21,
  11,
  "method",
  "definition,signature"
 ],
 [
  30,
  33,
  3,
  "parameter",
  "definition,interface"
 ],
 [
  30,
  37,
  7,
  "namespace",
  ""
 ],
 [
  30,
  45,
  7,
  "type",
  "interface"
 ],
 [
  30,
  54,
  5,
  "parameter",
  "definition,slice"
 ],
 [
  30,
  6,
  1,
  "parameter",
  "definition,struct"
 ],
 [
  30,
  62,
  8,
  "namespace",
  ""
 ],
 [
  30,
  71,
  12,
  "type",
  "interface"
 ],
 [
  30,
  8,
  11,
  "type",
  "struct"
 ],
 [
  30,
  85,
  5,
  "type",
  "defaultLibrary,interface"
 ],

... (6894 characters)
```

Actual:

```json
[
 [
  0,
  0,
  2,
  "comment",
  ""
 ],
 [
  1,
  0,
  44,
  "comment",
  ""
 ],
 [
  13,
  31,
  2,
  "comment",
  ""
 ],
 [
  16,
  0,
  7,
  "keyword",
  ""
 ],
 [
  16,
  8,
  7,
  "namespace",
  ""
 ],
 [
  18,
  0,
  6,
  "keyword",
  ""
 ],
 [
  19,
  2,
  7,
  "namespace",
  ""
 ],
 [
  20,
  2,
  6,
  "namespace",
  ""
 ],
 [
  21,
  2,
  4,
  "namespace",
  ""
 ],
 [
  23,
  1,
  8,
  "namespace",
  ""
 ],
 [
  26,
  0,
  4,
  "keyword",
  ""
 ],
 [
  26,
  17,
  6,
  "keyword",
  ""
 ],
 [
  26,
  5,
  11,
  "type",
  "definition,struct"
 ],
 [
  27,
  1,
  9,
  "property",
  "definition,slice"
 ],
 [
  27,
  13,
  8,
  "namespace",
  ""
 ],
 [
  27,
  22,
  12,
  "type",
  "interface"
 ],
 [
  30,
  0,
  4,
  "keyword",
  ""
 ],
 [
  30,
  21,
  11,
  "method",
  "definition,signature"
 ],
 [
  30,
  33,
  3,
  "parameter",
  "definition,interface"
 ],
 [
  30,
  37,
  7,
  "namespace",
  ""
 ],
 [
  30,
  45,
  7,
  "type",
  "interface"
 ],
 [
  30,
  54,
  5,
  "parameter",
  "definition,slice"
 ],
 [
  30,
  6,
  1,
  "parameter",
  "definition,struct"
 ],
 [
  30,
  62,
  8,
  "namespace",
  ""
 ],
 [
  30,
  71,
  12,
  "type",
  "interface"
 ],
 [
  30,
  8,
  11,
  "type",
  "struct"
 ],
 [
  30,
  85,
  5,
  "type",
  "defaultLibrary,interface"
 ],
 [
  31,
  1,
  3,
  "keyword",
  ""
 ],
 [
  32,
  13,
  9,
  "type",
  "struct"
 ],
 [
  32,
  2,
  2,
  "variable",
  "definition,struct"
 ],
 [
  32,
  8,
  4,
  "namespace",
  ""
 ],
 [
  33,
  13,
  5,

... (6522 characters)
```

Project file `internal/tracing/mux.go`:

```
   1 | /*
   2 |    Copyright 2023 Docker Compose CLI authors
     ...
   4 |    Licensed under the Apache License, Version 2.0 (the "License");
   5 |    you may not use this file except in compliance with the License.
   6 |    You may obtain a copy of the License at
     ...
   8 |        http://www.apache.org/licenses/LICENSE-2.0
     ...
  10 |    Unless required by applicable law or agreed to in writing, software
  11 |    distributed under the License is distributed on an "AS IS" BASIS,
  12 |    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  13 |    See the License for the specific language governing permissions and
  14 |    limitations under the License.
  15 | */
     ...
  17 | package tracing
     ...
  19 | import (
  20 | 	"context"
  21 | 	"errors"
  22 | 	"sync"
     ...
  24 | 	sdktrace "go.opentelemetry.io/otel/sdk/trace"
  25 | )
     ...
  27 | type MuxExporter struct {
  28 | 	exporters []sdktrace.SpanExporter
  29 | }
     ...
  31 | func (m MuxExporter) ExportSpans(ctx context.Context, spans []sdktrace.ReadOnlySpan) error {
  32 | 	var (
  33 | 		wg    sync.WaitGroup
  34 | 		errMu sync.Mutex
  35 | 		errs  = make([]error, 0, len(m.exporters))
  36 | 	)
     ...
  38 | 	for _, exporter := range m.exporters {
  39 | 		wg.Go(func() {
  40 | 			if err := exporter.ExportSpans(ctx, spans); err != nil {
  41 | 				errMu.Lock()
  42 | 				errs = append(errs, err)
  43 | 				errMu.Unlock()
  44 | 			}
  45 | 		})
  46 | 	}
  47 | 	wg.Wait()
  48 | 	return errors.Join(errs...)
  49 | }
     ...
  51 | func (m MuxExporter) Shutdown(ctx context.Context) error {
  52 | 	var (
  53 | 		wg    sync.WaitGroup
  54 | 		errMu sync.Mutex
  55 | 		errs  = make([]error, 0, len(m.exporters))
  56 | 	)
     ...
  58 | 	for _, exporter := range m.exporters {
  59 | 		wg.Go(func() {
  60 | 			if err := exporter.Shutdown(ctx); err != nil {
  61 | 				errMu.Lock()
  62 | 				errs = append(errs, err)
  63 | 				errMu.Unlock()
  64 | 			}
  65 | 		})
  66 | 	}
  67 | 	wg.Wait()
  68 | 	return errors.Join(errs...)
  69 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r5-semantictokens-changed-t4-b423af/repro.json
```

## Evidence and reduction

- representative 11bbeaaa308c-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 70 -> 4 (13 probes, 262.917 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects docker/compose@c6dffb26bdfd, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [golang/go#80666](https://github.com/golang/go/issues/80666) x/tools/gopls: assembly identifier positions drift in CRLF files (closed, 2026-07-31, 3 comments)
- [golang/go#47200](https://github.com/golang/go/issues/47200) x/tools/gopls: autoimport doesn't work properly in VS Code when using CRLF line endings (closed, 2021-07-14, 4 comments)
- [golang/go#46791](https://github.com/golang/go/issues/46791) x/tools/gopls: unimported completions produces invalid edits with windows line endings when CRLF is used (closed, 2021-05-09, 32 comments)
- [golang/go#42923](https://github.com/golang/go/issues/42923) x/tools/gopls: comments duplicated with CRLF files (closed, 2020-12-01, 8 comments)
- [golang/go#41057](https://github.com/golang/go/issues/41057) x/tools/gopls: bad formatting with CRLF line ending (closed, 2020-08-27, 2 comments)
- [golang/go#73426](https://github.com/golang/go/issues/73426) x/tools/gopls: no autocompletion when missing closing parenthesis (open, 2025-04-17, 6 comments)
- [golang/go#70554](https://github.com/golang/go/issues/70554) x/tools/gopls: refactor.rewrite.removeUnusedParam: avoid literalization for recursive spread call  (open, 2024-11-25, 3 comments)
- [golang/go#71227](https://github.com/golang/go/issues/71227) x/tools/gopls: gopls does not reset workspace/configuration if missing from the client (open, 2025-01-10, 8 comments)
- queries: `CRLF in:title repo:golang/go is:issue label:gopls`; `"semantic tokens" wrong repo:golang/go is:issue label:gopls`; `"semantic tokens" CRLF repo:golang/go is:issue label:gopls`; `"semantic tokens" whitespace repo:golang/go is:issue label:gopls`
