# [gopls v0.23.0] a stale codeAction handle resolves to a different edit after an intervening edit

Draft for the author (not filed). Group `gopls-r2-codeactionresolve-changed-codeaction-70b3e9`, signature `gopls|r2_handles|codeActionResolve:changed`, case family `codeAction`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `labstack/echo@3d084be90224` (corpus, commit 3d084be9022432c5a5257924c7d74bfc3444b456), language go

## Relation violated

Handle validity (R2): a code-action or completion handle minted before an edit and resolved after it must fail, return no edit, or return the same edit as a fresh handle for the same item.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. didOpen `group_method_handling_test.go`; request code actions at line 83, column 15 (LSP position {line: 82, character: 14}) and resolve them; didChange: insert `"\n"` at line 1 (top); wait until idle; resolve the OLD code action `Split arguments into separate lines`; request and resolve a fresh one at the mapped position: the old handle must fail, give no edit, or give the fresh handle's edit.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "group_method_handling_test.go",
  83,
  14,
  83,
  14,
  "\n\t\t"
 ],
 [
  "group_method_handling_test.go",
  83,
  15,
  83,
  17,
  ",\n\t\t"
 ],
 [
  "group_method_handling_test.go",
  83,
  23,
  83,
  25,
  ",\n\t\t"
 ],
 [
  "group_method_handling_test.go",
  83,
  29,
  83,
  29,
  ",\n\t"
 ]
]
```

Actual:

```json
[
 [
  "group_method_handling_test.go",
  82,
  14,
  82,
  14,
  "\n\t\t"
 ],
 [
  "group_method_handling_test.go",
  82,
  15,
  82,
  17,
  ",\n\t\t"
 ],
 [
  "group_method_handling_test.go",
  82,
  30,
  82,
  32,
  ",\n\t\t"
 ],
 [
  "group_method_handling_test.go",
  82,
  38,
  82,
  38,
  ",\n\t"
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r2-codeactionresolve-changed-codeaction-70b3e9/repro.json
```

## Evidence and reduction

- representative 4cb90eb12df9-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects abiosoft/colima@bba803d3d6fa, docker/compose@c6dffb26bdfd, labstack/echo@3d084be90224, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [golang/go#71314](https://github.com/golang/go/issues/71314) x/tools/gopls: gopls Extracts declarations to new file when a liveshare guest puts a cursor on a function name (closed, 2025-01-17, 4 comments)
- queries: `"code action resolve" wrong repo:golang/go is:issue label:gopls`; `"code action resolve" stale repo:golang/go is:issue label:gopls`
