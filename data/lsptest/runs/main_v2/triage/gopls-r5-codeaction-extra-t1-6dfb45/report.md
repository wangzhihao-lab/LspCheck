# [gopls v0.23.0] codeAction adds entries after transformation T1

Draft for the author (not filed). Group `gopls-r5-codeaction-extra-t1-6dfb45`, signature `gopls|r5_transforms|codeAction:extra`, case family `T1`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `beego/beego@939cfde380bb` (corpus, commit 939cfde380bb9f15844ad633b84f037f7da21584), language go

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T1 applied to `server/web/filter/opentracing/filter.go` (1 edit(s), first [26, 0, 26, 0]).
3. Query `textDocument/codeAction` on `server/web/filter/opentracing/filter.go` line 34, column 50 (LSP position {line: 33, character: 49}) (pos); compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Add test for FilterChain",
  "source.addTest"
 ],
 [
  "Browse arm64 assembly for FilterChain",
  "source.assembly"
 ],
 [
  "Browse documentation for package opentracing",
  "source.doc"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Show compiler optimization details for \"opentracing\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"opentracing\"",
  "source.splitPackage"
 ]
]
```

Actual:

```json
[
 [
  "Add test for FilterChain",
  "source.addTest"
 ],
 [
  "Browse arm64 assembly for FilterChain",
  "source.assembly"
 ],
 [
  "Browse documentation for package opentracing",
  "source.doc"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Organize Imports",
  "source.organizeImports"
 ],
 [
  "Show compiler optimization details for \"opentracing\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"opentracing\"",
  "source.splitPackage"
 ]
]
```

Project file `server/web/filter/opentracing/filter.go`:

```
   1 | // Copyright 2020 beego
   2 | //
   3 | // Licensed under the Apache License, Version 2.0 (the "License");
   4 | // you may not use this file except in compliance with the License.
   5 | // You may obtain a copy of the License at
   6 | //
   7 | // http://www.apache.org/licenses/LICENSE-2.0
   8 | //
   9 | // Unless required by applicable law or agreed to in writing, software
  10 | // distributed under the License is distributed on an "AS IS" BASIS,
  11 | // WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  12 | // See the License for the specific language governing permissions and
  13 | // limitations under the License.
     ...
  15 | package opentracing
     ...
  17 | import (
  18 | 	"context"
     ...
  20 | 	opentracingKit "github.com/go-kit/kit/tracing/opentracing"
  21 | 	logKit "github.com/go-kit/log"
  22 | 	"github.com/opentracing/opentracing-go"
     ...
  24 | 	"github.com/beego/beego/v2/server/web"
  25 | 	beegoCtx "github.com/beego/beego/v2/server/web/context"
  26 | )
     ...
  28 | // FilterChainBuilder provides an extension point that we can support more configurations if necessary
  29 | type FilterChainBuilder struct {
  30 | 	// CustomSpanFunc makes users to custom the span.
  31 | 	CustomSpanFunc func(span opentracing.Span, ctx *beegoCtx.Context)
  32 | }
     ...
  34 | func (builder *FilterChainBuilder) FilterChain(next web.FilterFunc) web.FilterFunc {
  35 | 	return func(ctx *beegoCtx.Context) {
  36 | 		var (
  37 | 			spanCtx context.Context
  38 | 			span    opentracing.Span
  39 | 		)
  40 | 		operationName := builder.operationName(ctx)
     ...
  42 | 		if preSpan := opentracing.SpanFromContext(ctx.Request.Context()); preSpan == nil {
  43 | 			inject := opentracingKit.HTTPToContext(opentracing.GlobalTracer(), operationName, logKit.NewNopLogger())
  44 | 			spanCtx = inject(ctx.Request.Context(), ctx.Request)
  45 | 			span = opentracing.SpanFromContext(spanCtx)
  46 | 		} else {
  47 | 			span, spanCtx = opentracing.StartSpanFromContext(ctx.Request.Context(), operationName)
  48 | 		}
     ...
  50 | 		defer span.Finish()
     ...
  52 | 		newReq := ctx.Request.Clone(spanCtx)
  53 | 		ctx.Reset(ctx.ResponseWriter.ResponseWriter, newReq)
     ...
  55 | 		next(ctx)
  56 | 		// if you think we need to do more things, feel free to create an issue to tell us
  57 | 		span.SetTag("http.status_code", ctx.ResponseWriter.Status)
  58 | 		span.SetTag("http.method", ctx.Input.Method())
  59 | 		span.SetTag("peer.hostname", ctx.Request.Host)
  60 | 		span.SetTag("http.url", ctx.Request.URL.String())
  61 | 		span.SetTag("http.scheme", ctx.Request.URL.Scheme)
  62 | 		span.SetTag("span.kind", "server")
  63 | 		span.SetTag("component", "beego")
  64 | 		if ctx.Output.IsServerError() || ctx.Output.IsClientError() {
  65 | 			span.SetTag("error", true)
  66 | 		}
  67 | 		span.SetTag("peer.address", ctx.Request.RemoteAddr)
  68 | 		span.SetTag("http.proto", ctx.Request.Proto)
     ...
  70 | 		span.SetTag("beego.route", ctx.Input.GetData("RouterPattern"))
     ...
  72 | 		if builder.CustomSpanFunc != nil {
  73 | 			builder.CustomSpanFunc(span, ctx)
  74 | 		}
  75 | 	}
  76 | }
     ...
  78 | func (builder *FilterChainBuilder) operationName(ctx *beegoCtx.Context) string {
  79 | 	operationName := ctx.Input.URL()
  80 | 	// it means that there is not any span, so we create a span as the root span.
  81 | 	// TODO, if we support multiple servers, this need to be changed
  82 | 	route, found := web.BeeApp.Handlers.FindRouter(ctx)
  83 | 	if found {
  84 | 		operationName = ctx.Input.Method() + "#" + route.GetPattern()
  85 | 	}
  86 | 	return operationName
  87 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r5-codeaction-extra-t1-6dfb45/repro.json
```

## Evidence and reduction

- representative 2628b01ed446-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects abiosoft/colima@bba803d3d6fa, beego/beego@939cfde380bb, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#70085](https://github.com/golang/go/issues/70085) x/tools/gopls: add refactor.inline.variable-all code action (open, 2024-10-29, 11 comments)
- [golang/go#39805](https://github.com/golang/go/issues/39805) x/tools/gopls: convert 'gofumpt' from formatter to code action provider (open, 2020-06-24, 5 comments)
- [golang/go#56403](https://github.com/golang/go/issues/56403) x/tools/gopls: allow enabling gofumpt extra rules (open, 2022-10-24, 5 comments)
- [golang/go#65944](https://github.com/golang/go/issues/65944) x/tools/gopls: extract variable returns an extra lhs expression and no template edit support is available (open, 2024-02-22, 5 comments)
- [golang/go#81403](https://github.com/golang/go/issues/81403) x/tools/gopls: upgrade mvdan/gofumpt dependency (closed, 2026-09-09, 4 comments)
- [golang/go#50262](https://github.com/golang/go/issues/50262) x/tools/gopls: add go:embed support (closed, 2021-12-10, 26 comments)
- [golang/go#77910](https://github.com/golang/go/issues/77910) x/tools/gopls: add analyzer to report when code isn't gofmt'd properly (open, 2026-03-03, 4 comments)
- [golang/go#31150](https://github.com/golang/go/issues/31150) x/tools/gopls: implement rangeFormatting LSP request (closed, 2019-03-29, 22 comments)
- queries: `"blank lines" in:title repo:golang/go is:issue label:gopls`; `"code action" extra repo:golang/go is:issue label:gopls`; `"code action" "blank lines" repo:golang/go is:issue label:gopls`; `"code action" whitespace repo:golang/go is:issue label:gopls`
