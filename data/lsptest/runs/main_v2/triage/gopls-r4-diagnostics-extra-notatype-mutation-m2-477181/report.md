# [gopls v0.23.0] mutation:M2 edit is not valid (diagnostics:extra:NotAType)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-notatype-mutation-m2-477181`, signature `gopls|r4_edits|diagnostics:extra:NotAType`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `labstack/echo@3d084be90224` (corpus, commit 3d084be9022432c5a5257924c7d74bfc3444b456), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open group_method_handling_test.go`
3. textDocument/didChange: `change group_method_handling_test.go (46, 25)-(46, 32) "Conttext"`
4. textDocument/didChange: `change group_method_handling_test.go (46, 1)-(46, 1) "Conttext := 0\n\t"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `json.go`, `middleware/basic_auth_test.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `group_method_handling_test.go` line 47, column 26 (LSP position {line: 46, character: 25}) (M2:quickfix-errors:Create variable Conttext); compare with the same query in a fresh session on the same content (expected).

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
  "NotAType",
  "compiler",
  "Conttext (local variable) is not a type"
 ]
]
```

Project file `group_method_handling_test.go`:

```
   1 | // SPDX-License-Identifier: MIT
   2 | // SPDX-FileCopyrightText: © 2015 LabStack LLC and Echo contributors
     ...
   4 | package echo
     ...
   6 | import (
   7 | 	"net/http"
   8 | 	"net/http/httptest"
   9 | 	"testing"
     ...
  11 | 	"github.com/stretchr/testify/assert"
  12 | )
     ...
  14 | // These tests lock in v5's method-handling semantics for routes registered through
  15 | // a Group. v5 resolves method mismatches (405) and OPTIONS at the router level and
  16 | // does NOT register any implicit per-group catch-all route.
  17 | //
  18 | // They double as a regression gate. Registering a group-level catch-all — whether
  19 | // manually via g.RouteNotFound("/*", ...) or automatically (as proposed in #2996 to
  20 | // fix CORS-on-group preflight) — makes that catch-all match every method, which masks
  21 | // both 405 and v5's automatic OPTIONS response as 404 — demonstrated directly by
  22 | // TestGroupRoute_catchAllMasksMethodHandling below. If that masking becomes the
  23 | // default (e.g. #2996 lands), the first two tests below fail.
     ...
  25 | // A method mismatch on an existing group route must return 405 with the allowed
  26 | // methods, not be masked to 404.
  27 | func TestGroupRoute_methodMismatchReturns405(t *testing.T) {
  28 | 	e := New()
  29 | 	g := e.Group("/api")
  30 | 	g.GET("/users", func(c *Context) error { return c.String(http.StatusOK, "users") })
     ...
  32 | 	req := httptest.NewRequest(http.MethodPost, "/api/users", nil)
  33 | 	rec := httptest.NewRecorder()
  34 | 	e.ServeHTTP(rec, req)
     ...
  36 | 	assert.Equal(t, http.StatusMethodNotAllowed, rec.Code,
  37 | 		"POST to a GET-only group route must be 405, not masked to 404")
  38 | 	assert.Equal(t, "OPTIONS, GET", rec.Header().Get(HeaderAllow),
  39 | 		"405 response must advertise the allowed methods")
  40 | }
     ...
  42 | // OPTIONS on an existing group route is answered automatically by Echo (204 +
  43 | // Allow). This is the behavior CORS preflight relies on, so it must not be masked.
  44 | func TestGroupRoute_automaticOPTIONS(t *testing.T) {
  45 | 	e := New()
  46 | 	g := e.Group("/api")
  47 | 	g.GET("/users", func(c *Context) error { return c.String(http.StatusOK, "users") })
     ...
  49 | 	req := httptest.NewRequest(http.MethodOptions, "/api/users", nil)
  50 | 	rec := httptest.NewRecorder()
  51 | 	e.ServeHTTP(rec, req)
     ...
  53 | 	assert.Equal(t, http.StatusNoContent, rec.Code,
  54 | 		"OPTIONS on a registered group route must be auto-answered (204), not masked to 404")
  55 | 	assert.Equal(t, "OPTIONS, GET", rec.Header().Get(HeaderAllow),
  56 | 		"automatic OPTIONS response must advertise the allowed methods")
  57 | }
     ...
  59 | // A matched concrete route resolves to its own handler; only a genuinely unmatched
  60 | // path under the prefix is a 404.
  61 | func TestGroupRoute_concreteRoutesResolve(t *testing.T) {
  62 | 	e := New()
  63 | 	g := e.Group("/api")
  64 | 	g.GET("/users", func(c *Context) error { return c.String(http.StatusOK, "users") })
     ...
  66 | 	status, body := request(http.MethodGet, "/api/users", e)
  67 | 	assert.Equal(t, http.StatusOK, status)
  68 | 	assert.Equal(t, "users", body)
     ...
  70 | 	status, _ = request(http.MethodGet, "/api/nope", e)
  71 | 	assert.Equal(t, http.StatusNotFound, status)
  72 | }
     ...
  74 | // A group prefix must not affect routing of routes registered outside the group.
  75 | func TestGroup_doesNotAffectRootRoutes(t *testing.T) {
  76 | 	e := New()
  77 | 	e.GET("/health", func(c *Context) error { return c.String(http.StatusOK, "root") })
  78 | 	g := e.Group("/api")
  79 | 	g.GET("/users", func(c *Context) error { return c.String(http.StatusOK, "users") })
     ...
  81 | 	status, body := request(http.MethodGet, "/health", e)
  82 | 	assert.Equal(t, http.StatusOK, status)
  83 | 	assert.Equal(t, "root", body)
  84 | }
     ...
  86 | // Characterization of the regression the 405/OPTIONS tests above guard against:
  87 | // registering a group-wide catch-all (the manual equivalent of #2996's auto-
  88 | // registration) makes it match every method, so method mismatches and the automatic
  89 | // OPTIONS response are masked as 404 even though the concrete route still resolves.
  90 | // If a future change teaches the catch-all to preserve method semantics, update this.
  91 | func TestGroupRoute_catchAllMasksMethodHandling(t *testing.T) {
  92 | 	e := New()
  93 | 	g := e.Group("/api")
  94 | 	g.GET("/users", func(c *Context) error { return c.String(http.StatusOK, "users") })
  95 | 	g.RouteNotFound("/*", func(c *Context) error { return c.NoContent(http.StatusNotFound) })
     ...
  97 | 	// The concrete route still resolves.
  98 | 	status, body := request(http.MethodGet, "/api/users", e)
  99 | 	assert.Equal(t, http.StatusOK, status)
 100 | 	assert.Equal(t, "users", body)
     ...
 102 | 	// But the catch-all masks the method mismatch (would be 405) ...
 103 | 	post := httptest.NewRequest(http.MethodPost, "/api/users", nil)
 104 | 	postRec := httptest.NewRecorder()
 105 | 	e.ServeHTTP(postRec, post)
 106 | 	assert.Equal(t, http.StatusNotFound, postRec.Code,
 107 | 		"a group-wide catch-all masks the 405 method-mismatch as 404")
     ...
 109 | 	// ... and the automatic OPTIONS response (would be 204).
 110 | 	opts := httptest.NewRequest(http.MethodOptions, "/api/users", nil)
 111 | 	optsRec := httptest.NewRecorder()
 112 | 	e.ServeHTTP(optsRec, opts)
 113 | 	assert.Equal(t, http.StatusNotFound, optsRec.Code,
 114 | 		"a group-wide catch-all masks the automatic OPTIONS (204) response as 404")
 115 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r4-diagnostics-extra-notatype-mutation-m2-477181/repro.json
```

## Evidence and reduction

- representative 508981c8d2e2-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 4.898 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects labstack/echo@3d084be90224, schollz/croc@5890191be511, timings settled, seeds 1, 2

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
