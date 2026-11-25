# [gopls v0.23.0] mutation:M2 edit is not valid (diagnostics:extra:IncompatibleAssign,InvalidAppend,NotAnExpr)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-incompatibleassign-inv-mutation-m2-3cfa07`, signature `gopls|r4_edits|diagnostics:extra:IncompatibleAssign,InvalidAppend,NotAnExpr`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `docker/compose@c6dffb26bdfd` (corpus, commit c6dffb26bdfd94efb1f4e1c743f1241a150d120a), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open internal/tracing/mux.go`
3. textDocument/didChange: `change internal/tracing/mux.go (54, 10)-(54, 14) "mae"`
4. textDocument/didChange: `change internal/tracing/mux.go (69, 0)-(69, 0) "\nfunc mae(err []error, i1, i2 int) any {\n\tpanic(\"unimplemented\")\n}\n"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `pkg/compose/model.go`, `pkg/watch/temp.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `internal/tracing/mux.go` line 55, column 11 (LSP position {line: 54, character: 10}) (M2:quickfix-errors:Create function mae); compare with the same query in a fresh session on the same content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  0,
  0,
  0,
  0,
  1,
  "IncompatibleAssign",
  "compiler",
  "cannot use errs (variable of interface type any) as []error value in argument to errors.Join: need type assertion"
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "InvalidAppend",
  "compiler",
  "invalid append: argument must be a slice; have errs (variable of interface type any)"
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "NotAnExpr",
  "compiler",
  "[]error (type) is not an expression"
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r4-diagnostics-extra-incompatibleassign-inv-mutation-m2-3cfa07/repro.json
```

## Evidence and reduction

- representative 118461be1f56-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 4.182 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects docker/compose@c6dffb26bdfd, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#68075](https://github.com/golang/go/issues/68075) x/tools/gopls/internal/cmd: `gopls check` doesn't wait for didOpen finish before it makes diagnostics request (open, 2024-06-19, 4 comments)
- [golang/go#41436](https://github.com/golang/go/issues/41436) x/tools/go/analysis: a Diagnostic should indicate when it is a lint-style warning that should be ignored in generated code (open, 2020-09-16, 34 comments)
- [golang/go#70085](https://github.com/golang/go/issues/70085) x/tools/gopls: add refactor.inline.variable-all code action (open, 2024-10-29, 11 comments)
- [golang/go#50151](https://github.com/golang/go/issues/50151) x/tools/gopls: high cpu usage when make changes in package which have some cgo package dependents (open, 2021-12-14, 15 comments)
- [golang/go#54461](https://github.com/golang/go/issues/54461) x/tools/gopls: regtest flakes due to hanging go commands (open, 2022-08-15, 422 comments)
- [golang/go#69646](https://github.com/golang/go/issues/69646) x/tools/gopls: packages.Load failure with conflicting go.work and go.mod toolchain versions (open, 2024-09-16, 5 comments)
- [golang/go#79892](https://github.com/golang/go/issues/79892) x/tools/gopls: mcp go_diagnostics misattributes diagnostics to files[0] (and drops its own) when given multiple files (closed, 2026-06-07, 2 comments)
- [golang/go#68026](https://github.com/golang/go/issues/68026) x/tools/gopls: broken hovering in the builtin file (closed, 2024-06-16, 11 comments)
- queries: `diagnostics extra repo:golang/go is:issue label:gopls`; `diagnostics "wrong edit" repo:golang/go is:issue label:gopls`
