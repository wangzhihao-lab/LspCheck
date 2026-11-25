# [gopls v0.23.0] foldingRange changes its answer after transformation T6

Draft for the author (not filed). Group `gopls-r5-foldingrange-changed-t6-ecacad`, signature `gopls|r5_transforms|foldingRange:changed`, case family `T6`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `router-for-me/CLIProxyAPI@673131f57484` (corpus, commit 673131f57484517c3a1eae7e36c4cfa7b9bb4efc), language go

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T6 applied to `sdk/cliproxy/auth/conductor_oauth_alias_suspension_test.go` (1 edit(s), first [73, 35, 73, 35]).
3. Query `textDocument/foldingRange` on `sdk/cliproxy/auth/conductor_oauth_alias_suspension_test.go` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  100,
  20,
  100,
  97,
  ""
 ],
 [
  100,
  61,
  100,
  96,
  ""
 ],
 [
  100,
  62,
  100,
  76,
  ""
 ],
 [
  100,
  80,
  100,
  95,
  ""
 ],
 [
  101,
  11,
  103,
  2,
  ""
 ],
 [
  101,
  19,
  103,
  1,
  ""
 ],
 [
  102,
  23,
  102,
  30,
  ""
 ],
 [
  104,
  31,
  104,
  38,
  ""
 ],
 [
  106,
  104,
  106,
  121,
  ""
 ],
 [
  106,
  37,
  106,
  150,
  ""
 ],
 [
  106,
  68,
  106,
  76,
  ""
 ],
 [
  107,
  23,
  109,
  1,
  ""
 ],
 [
  108,
  11,
  108,
  57,
  ""
 ],
 [
  110,
  11,
  110,
  23,
  ""
 ],
 [
  110,
  41,
  112,
  1,
  ""
 ],
 [
  111,
  11,
  111,
  77,
  ""
 ],
 [
  111,
  51,
  111,
  63,
  ""
 ],
 [
  115,
  25,
  117,
  1,
  ""
 ],
 [
  115,
  8,
  115,
  17,
  ""
 ],
 [
  116,
  11,
  116,
  60,
  ""
 ],
 [
  116,
  50,
  116,
  59,
  ""
 ],
 [
  118,
  33,
  120,
  1,
  ""
 ],
 [
  119,
  11,
  119,
  67,
  ""
 ],
 [
  123,
  26,
  125,
  1,
  ""
 ],
 [
  123,
  8,
  123,
  18,
  ""
 ],
 [
  124,
  11,
  124,
  62,
  ""
 ],
 [
  124,
  51,
  124,
  61,
  ""
 ],
 [
  126,
  33,
  128,
  1,
  ""
 ],
 [
  127,
  11,
  127,
  67,
  ""
 ],
 [
  15,
  34,
  21,
  0,
  ""
 ],
 [
  2,
  8,
  13,
  0,
  "imports"
 ],
 [
  23,
  52,
  23,
  65,
  ""
 ],
 [
  23,
  6,
  23,
  29,
  ""
 ],
 [
  25,
  128,
  25,
  160,
  ""
 ],
 [
  25,
  163,
  31,
  0,
  ""
 ],
 [
  25,
  39,
  25,
  125,
  ""
 ],
 [
  25,
  6,
  25,
  29,
  ""
 ],
 [
  27,
  26,
  27,
  52,
  ""
 ],
 [
  28,
  27,
  28,
  90,
  ""
 ],
 [
  28,
  86,
  28,
  89,
  ""
 ],
 [

... (3212 characters)
```

Actual:

```json
[
 [
  100,
  20,
  100,
  97,
  ""
 ],
 [
  100,
  61,
  100,
  96,
  ""
 ],
 [
  100,
  62,
  100,
  76,
  ""
 ],
 [
  100,
  80,
  100,
  95,
  ""
 ],
 [
  101,
  11,
  103,
  2,
  ""
 ],
 [
  101,
  19,
  103,
  1,
  ""
 ],
 [
  102,
  23,
  102,
  30,
  ""
 ],
 [
  104,
  31,
  104,
  38,
  ""
 ],
 [
  106,
  104,
  106,
  121,
  ""
 ],
 [
  106,
  37,
  106,
  150,
  ""
 ],
 [
  106,
  68,
  106,
  76,
  ""
 ],
 [
  107,
  23,
  109,
  1,
  ""
 ],
 [
  108,
  11,
  108,
  57,
  ""
 ],
 [
  110,
  11,
  110,
  23,
  ""
 ],
 [
  110,
  41,
  112,
  1,
  ""
 ],
 [
  111,
  11,
  111,
  77,
  ""
 ],
 [
  111,
  51,
  111,
  63,
  ""
 ],
 [
  115,
  25,
  117,
  1,
  ""
 ],
 [
  115,
  8,
  115,
  17,
  ""
 ],
 [
  116,
  11,
  116,
  60,
  ""
 ],
 [
  116,
  50,
  116,
  59,
  ""
 ],
 [
  118,
  33,
  120,
  1,
  ""
 ],
 [
  119,
  11,
  119,
  67,
  ""
 ],
 [
  123,
  26,
  125,
  1,
  ""
 ],
 [
  123,
  8,
  123,
  18,
  ""
 ],
 [
  124,
  11,
  124,
  62,
  ""
 ],
 [
  124,
  51,
  124,
  61,
  ""
 ],
 [
  126,
  33,
  128,
  1,
  ""
 ],
 [
  127,
  11,
  127,
  67,
  ""
 ],
 [
  15,
  34,
  21,
  0,
  ""
 ],
 [
  2,
  8,
  13,
  0,
  "imports"
 ],
 [
  23,
  52,
  23,
  65,
  ""
 ],
 [
  23,
  6,
  23,
  29,
  ""
 ],
 [
  25,
  128,
  25,
  160,
  ""
 ],
 [
  25,
  163,
  31,
  0,
  ""
 ],
 [
  25,
  39,
  25,
  125,
  ""
 ],
 [
  25,
  6,
  25,
  29,
  ""
 ],
 [
  27,
  26,
  27,
  52,
  ""
 ],
 [
  28,
  27,
  28,
  90,
  ""
 ],
 [
  28,
  86,
  28,
  89,
  ""
 ],
 [

... (3212 characters)
```

Project file `sdk/cliproxy/auth/conductor_oauth_alias_suspension_test.go`:

```
   1 | package auth
     ...
   3 | import (
   4 | 	"context"
   5 | 	"net/http"
   6 | 	"sync"
   7 | 	"testing"
   8 | 	"time"
     ...
  10 | 	internalconfig "github.com/router-for-me/CLIProxyAPI/v7/internal/config"
  11 | 	"github.com/router-for-me/CLIProxyAPI/v7/internal/registry"
  12 | 	cliproxyexecutor "github.com/router-for-me/CLIProxyAPI/v7/sdk/cliproxy/executor"
  13 | 	coreusage "github.com/router-for-me/CLIProxyAPI/v7/sdk/cliproxy/usage"
  14 | )
     ...
  16 | type aliasRoutingExecutor struct {
  17 | 	id string
     ...
  19 | 	mu             sync.Mutex
  20 | 	executeModels  []string
  21 | 	executeAliases []string
  22 | }
     ...
  24 | func (e *aliasRoutingExecutor) Identifier() string { return e.id }
     ...
  26 | func (e *aliasRoutingExecutor) Execute(ctx context.Context, _ *Auth, req cliproxyexecutor.Request, _ cliproxyexecutor.Options) (cliproxyexecutor.Response, error) {
  27 | 	e.mu.Lock()
  28 | 	e.executeModels = append(e.executeModels, req.Model)
  29 | 	e.executeAliases = append(e.executeAliases, coreusage.RequestedModelAliasFromContext(ctx))
  30 | 	e.mu.Unlock()
  31 | 	return cliproxyexecutor.Response{Payload: []byte(req.Model)}, nil
  32 | }
     ...
  34 | func (e *aliasRoutingExecutor) ExecuteStream(context.Context, *Auth, cliproxyexecutor.Request, cliproxyexecutor.Options) (*cliproxyexecutor.StreamResult, error) {
  35 | 	return nil, &Error{HTTPStatus: http.StatusNotImplemented, Message: "ExecuteStream not implemented"}
  36 | }
     ...
  38 | func (e *aliasRoutingExecutor) Refresh(_ context.Context, auth *Auth) (*Auth, error) {
  39 | 	return auth, nil
  40 | }
     ...
  42 | func (e *aliasRoutingExecutor) CountTokens(context.Context, *Auth, cliproxyexecutor.Request, cliproxyexecutor.Options) (cliproxyexecutor.Response, error) {
  43 | 	return cliproxyexecutor.Response{}, &Error{HTTPStatus: http.StatusNotImplemented, Message: "CountTokens not implemented"}
  44 | }
     ...
  46 | func (e *aliasRoutingExecutor) HttpRequest(context.Context, *Auth, *http.Request) (*http.Response, error) {
  47 | 	return nil, &Error{HTTPStatus: http.StatusNotImplemented, Message: "HttpRequest not implemented"}
  48 | }
     ...
  50 | func (e *aliasRoutingExecutor) ExecuteModels() []string {
  51 | 	e.mu.Lock()
  52 | 	defer e.mu.Unlock()
  53 | 	out := make([]string, len(e.executeModels))
  54 | 	copy(out, e.executeModels)
  55 | 	return out
  56 | }
     ...
  58 | func (e *aliasRoutingExecutor) ExecuteAliases() []string {
  59 | 	e.mu.Lock()
  60 | 	defer e.mu.Unlock()
  61 | 	out := make([]string, len(e.executeAliases))
  62 | 	copy(out, e.executeAliases)
  63 | 	return out
  64 | }
     ...
  66 | func TestManagerExecute_OAuthAliasBypassesBlockedRouteModel(t *testing.T) {
  67 | 	const (
  68 | 		provider    = "antigravity"
  69 | 		routeModel  = "claude-opus-4-6"
  70 | 		targetModel = "claude-opus-4-6-thinking"
  71 | 	)
     ...
  73 | 	manager := NewManager(nil, nil, nil)
  74 | 	executor := &aliasRoutingExecutor{id: provider}
  75 | 	manager.RegisterExecutor(executor)
  76 | 	manager.SetOAuthModelAlias(map[string][]internalconfig.OAuthModelAlias{
  77 | 		provider: {{
  78 | 			Name:  targetModel,
  79 | 			Alias: routeModel,
  80 | 			Fork:  true,
  81 | 		}},
  82 | 	})
     ...
  84 | 	auth := &Auth{
  85 | 		ID:       "oauth-alias-auth",
  86 | 		Provider: provider,
  87 | 		Status:   StatusActive,
  88 | 		ModelStates: map[string]*ModelState{
  89 | 			routeModel: {
  90 | 				Unavailable:    true,
  91 | 				Status:         StatusError,
  92 | 				NextRetryAfter: time.Now().Add(1 * time.Hour),
  93 | 			},
  94 | 		},
  95 | 	}
  96 | 	if _, errRegister := manager.Register(context.Background(), auth); errRegister != nil {
  97 | 		t.Fatalf("register auth: %v", errRegister)
  98 | 	}
     ...
 100 | 	reg := registry.GetGlobalRegistry()
 101 | 	reg.RegisterClient(auth.ID, provider, []*registry.ModelInfo{{ID: routeModel}, {ID: targetModel}})
 102 | 	t.Cleanup(func() {
 103 | 		reg.UnregisterClient(auth.ID)
 104 | 	})
 105 | 	manager.RefreshSchedulerEntry(auth.ID)
     ...
 107 | 	resp, errExecute := manager.Execute(context.Background(), []string{provider}, cliproxyexecutor.Request{Model: routeModel}, cliproxyexecutor.Options{})
 108 | 	if errExecute != nil {
 109 | 		t.Fatalf("execute error = %v, want success", errExecute)
 110 | 	}
 111 | 	if string(resp.Payload) != targetModel {
 112 | 		t.Fatalf("execute payload = %q, want %q", string(resp.Payload), targetModel)
 113 | 	}
     ...
 115 | 	gotModels := executor.ExecuteModels()
 116 | 	if len(gotModels) != 1 {
 117 | 		t.Fatalf("execute models len = %d, want 1", len(gotModels))
 118 | 	}
 119 | 	if gotModels[0] != targetModel {
 120 | 		t.Fatalf("execute model = %q, want %q", gotModels[0], targetModel)
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r5-foldingrange-changed-t6-ecacad/repro.json
```

## Evidence and reduction

- representative 4b8ebf18dab2-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects router-for-me/CLIProxyAPI@673131f57484, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#29149](https://github.com/golang/go/issues/29149) x/tools/internal/lsp: handle unicode code points that are encoded as multiple bytes (closed, 2018-12-07, 2 comments)
- [golang/go#71489](https://github.com/golang/go/issues/71489) x/tools/gopls: FoldingRange omitempty causes EndCharacter=0 to be omitted, changing its semantics in clients that distinguish 0 from missing (closed, 2025-01-30, 15 comments)
- [golang/go#79524](https://github.com/golang/go/issues/79524) x/tools/gopls: semantic tokens no longer returned (regression in v0.22.0) (closed, 2026-05-19, 11 comments)
- queries: `unicode in:title repo:golang/go is:issue label:gopls`; `"folding range" wrong repo:golang/go is:issue label:gopls`; `"folding range" unicode repo:golang/go is:issue label:gopls`; `"folding range" whitespace repo:golang/go is:issue label:gopls`
