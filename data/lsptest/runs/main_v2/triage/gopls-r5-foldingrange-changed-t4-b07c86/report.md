# [gopls v0.23.0] foldingRange changes its answer after transformation T4

Draft for the author (not filed). Group `gopls-r5-foldingrange-changed-t4-b07c86`, signature `gopls|r5_transforms|foldingRange:changed`, case family `T4`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `docker/compose@c6dffb26bdfd` (corpus, commit c6dffb26bdfd94efb1f4e1c743f1241a150d120a), language go

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T4 applied to `internal/tracing/mux.go` (69 edit(s), first [0, 2, 0, 2]).
3. Query `textDocument/foldingRange` on `internal/tracing/mux.go` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  2,
  14,
  2,
  "comment"
 ],
 [
  18,
  8,
  24,
  0,
  "imports"
 ],
 [
  26,
  25,
  28,
  0,
  ""
 ],
 [
  30,
  33,
  30,
  83,
  ""
 ],
 [
  30,
  6,
  30,
  19,
  ""
 ],
 [
  30,
  92,
  48,
  0,
  ""
 ],
 [
  31,
  6,
  35,
  1,
  ""
 ],
 [
  34,
  15,
  34,
  43,
  ""
 ],
 [
  34,
  31,
  34,
  42,
  ""
 ],
 [
  37,
  39,
  45,
  1,
  ""
 ],
 [
  38,
  16,
  44,
  2,
  ""
 ],
 [
  38,
  8,
  44,
  3,
  ""
 ],
 [
  39,
  34,
  39,
  44,
  ""
 ],
 [
  39,
  59,
  43,
  3,
  ""
 ],
 [
  41,
  18,
  41,
  27,
  ""
 ],
 [
  47,
  20,
  47,
  27,
  ""
 ],
 [
  50,
  30,
  50,
  49,
  ""
 ],
 [
  50,
  58,
  68,
  0,
  ""
 ],
 [
  50,
  6,
  50,
  19,
  ""
 ],
 [
  51,
  6,
  55,
  1,
  ""
 ],
 [
  54,
  15,
  54,
  43,
  ""
 ],
 [
  54,
  31,
  54,
  42,
  ""
 ],
 [
  57,
  39,
  65,
  1,
  ""
 ],
 [
  58,
  16,
  64,
  2,
  ""
 ],
 [
  58,
  8,
  64,
  3,
  ""
 ],
 [
  59,
  31,
  59,
  34,
  ""
 ],
 [
  59,
  49,
  63,
  3,
  ""
 ],
 [
  61,
  18,
  61,
  27,
  ""
 ],
 [
  67,
  20,
  67,
  27,
  ""
 ]
]
```

Actual:

```json
[
 [
  0,
  2,
  14,
  1,
  "comment"
 ],
 [
  18,
  8,
  24,
  0,
  "imports"
 ],
 [
  26,
  25,
  28,
  0,
  ""
 ],
 [
  30,
  33,
  30,
  83,
  ""
 ],
 [
  30,
  6,
  30,
  19,
  ""
 ],
 [
  30,
  92,
  48,
  0,
  ""
 ],
 [
  31,
  6,
  35,
  1,
  ""
 ],
 [
  34,
  15,
  34,
  43,
  ""
 ],
 [
  34,
  31,
  34,
  42,
  ""
 ],
 [
  37,
  39,
  45,
  1,
  ""
 ],
 [
  38,
  16,
  44,
  2,
  ""
 ],
 [
  38,
  8,
  44,
  3,
  ""
 ],
 [
  39,
  34,
  39,
  44,
  ""
 ],
 [
  39,
  59,
  43,
  3,
  ""
 ],
 [
  41,
  18,
  41,
  27,
  ""
 ],
 [
  47,
  20,
  47,
  27,
  ""
 ],
 [
  50,
  30,
  50,
  49,
  ""
 ],
 [
  50,
  58,
  68,
  0,
  ""
 ],
 [
  50,
  6,
  50,
  19,
  ""
 ],
 [
  51,
  6,
  55,
  1,
  ""
 ],
 [
  54,
  15,
  54,
  43,
  ""
 ],
 [
  54,
  31,
  54,
  42,
  ""
 ],
 [
  57,
  39,
  65,
  1,
  ""
 ],
 [
  58,
  16,
  64,
  2,
  ""
 ],
 [
  58,
  8,
  64,
  3,
  ""
 ],
 [
  59,
  31,
  59,
  34,
  ""
 ],
 [
  59,
  49,
  63,
  3,
  ""
 ],
 [
  61,
  18,
  61,
  27,
  ""
 ],
 [
  67,
  20,
  67,
  27,
  ""
 ]
]
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r5-foldingrange-changed-t4-b07c86/repro.json
```

## Evidence and reduction

- representative 11bbeaaa308c-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 70 -> 2 (6 probes, 129.441 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects docker/compose@c6dffb26bdfd, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [golang/go#80666](https://github.com/golang/go/issues/80666) x/tools/gopls: assembly identifier positions drift in CRLF files (closed, 2026-07-31, 3 comments)
- [golang/go#47200](https://github.com/golang/go/issues/47200) x/tools/gopls: autoimport doesn't work properly in VS Code when using CRLF line endings (closed, 2021-07-14, 4 comments)
- [golang/go#46791](https://github.com/golang/go/issues/46791) x/tools/gopls: unimported completions produces invalid edits with windows line endings when CRLF is used (closed, 2021-05-09, 32 comments)
- [golang/go#42923](https://github.com/golang/go/issues/42923) x/tools/gopls: comments duplicated with CRLF files (closed, 2020-12-01, 8 comments)
- [golang/go#41057](https://github.com/golang/go/issues/41057) x/tools/gopls: bad formatting with CRLF line ending (closed, 2020-08-27, 2 comments)
- [golang/go#71489](https://github.com/golang/go/issues/71489) x/tools/gopls: FoldingRange omitempty causes EndCharacter=0 to be omitted, changing its semantics in clients that distinguish 0 from missing (closed, 2025-01-30, 15 comments)
- [golang/go#79524](https://github.com/golang/go/issues/79524) x/tools/gopls: semantic tokens no longer returned (regression in v0.22.0) (closed, 2026-05-19, 11 comments)
- queries: `CRLF in:title repo:golang/go is:issue label:gopls`; `"folding range" wrong repo:golang/go is:issue label:gopls`; `"folding range" CRLF repo:golang/go is:issue label:gopls`; `"folding range" whitespace repo:golang/go is:issue label:gopls`
