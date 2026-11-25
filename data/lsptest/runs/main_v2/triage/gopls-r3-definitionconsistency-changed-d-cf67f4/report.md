# [gopls v0.23.0] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `gopls-r3-definitionconsistency-changed-d-cf67f4`, signature `gopls|r3_routes|definitionConsistency:changed`, case family `d`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `beego/beego@939cfde380bb` (corpus, commit 939cfde380bb9f15844ad633b84f037f7da21584), language go

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `task/governor_command_test.go` at line 75, column 5 (LSP position {line: 74, character: 4}) gives the expected set; didOpen `task/governor_command_test.go` and `textDocument/definition` at the reference line 23, column 20 (LSP position {line: 22, character: 19}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "task/governor_command_test.go",
  22,
  1,
  22,
  37
 ]
]
```

Actual:

```json
[
 [
  "<servers>/gopath/pkg/mod/github.com/stretchr/testify@v1.10.0/assert/assertion_compare.go",
  0,
  0,
  7,
  1
 ],
 [
  "<servers>/gopath/pkg/mod/github.com/stretchr/testify@v1.10.0/assert/assertion_format.go",
  2,
  0,
  8,
  1
 ],
 [
  "<servers>/gopath/pkg/mod/github.com/stretchr/testify@v1.10.0/assert/assertion_forward.go",
  2,
  0,
  8,
  1
 ],
 [
  "<servers>/gopath/pkg/mod/github.com/stretchr/testify@v1.10.0/assert/assertion_order.go",
  0,
  0,
  5,
  1
 ],
 [
  "<servers>/gopath/pkg/mod/github.com/stretchr/testify@v1.10.0/assert/assertions.go",
  0,
  0,
  24,
  1
 ],
 [
  "<servers>/gopath/pkg/mod/github.com/stretchr/testify@v1.10.0/assert/doc.go",
  45,
  0,
  45,
  14
 ],
 [
  "<servers>/gopath/pkg/mod/github.com/stretchr/testify@v1.10.0/assert/errors.go",
  0,
  0,
  4,
  1
 ],
 [
  "<servers>/gopath/pkg/mod/github.com/stretchr/testify@v1.10.0/assert/forward_assertions.go",
  0,
  0,
  0,
  14
 ],
 [
  "<servers>/gopath/pkg/mod/github.com/stretchr/testify@v1.10.0/assert/http_assertions.go",
  0,
  0,
  8,
  1
 ]
]
```

Project file `task/governor_command_test.go`:

```
   1 | // Copyright 2020
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
  15 | package task
     ...
  17 | import (
  18 | 	"context"
  19 | 	"errors"
  20 | 	"testing"
  21 | 	"time"
     ...
  23 | 	"github.com/stretchr/testify/assert"
  24 | )
     ...
  26 | type countTask struct {
  27 | 	cnt     int
  28 | 	mockErr error
  29 | }
     ...
  31 | func (c *countTask) GetSpec(ctx context.Context) string {
  32 | 	return "AAA"
  33 | }
     ...
  35 | func (c *countTask) GetStatus(ctx context.Context) string {
  36 | 	return "SUCCESS"
  37 | }
     ...
  39 | func (c *countTask) Run(ctx context.Context) error {
  40 | 	c.cnt++
  41 | 	return c.mockErr
  42 | }
     ...
  44 | func (c *countTask) SetNext(ctx context.Context, time time.Time) {
  45 | }
     ...
  47 | func (c *countTask) GetNext(ctx context.Context) time.Time {
  48 | 	return time.Now()
  49 | }
     ...
  51 | func (c *countTask) SetPrev(ctx context.Context, time time.Time) {
  52 | }
     ...
  54 | func (c *countTask) GetPrev(ctx context.Context) time.Time {
  55 | 	return time.Now()
  56 | }
     ...
  58 | func (c *countTask) GetTimeout(ctx context.Context) time.Duration {
  59 | 	return 0
  60 | }
     ...
  62 | func TestRunTaskCommand_Execute(t *testing.T) {
  63 | 	task := &countTask{}
  64 | 	AddTask("count", task)
     ...
  66 | 	cmd := &runTaskCommand{}
     ...
  68 | 	res := cmd.Execute()
  69 | 	assert.NotNil(t, res)
  70 | 	assert.NotNil(t, res.Error)
  71 | 	assert.Equal(t, "task name not passed", res.Error.Error())
     ...
  73 | 	res = cmd.Execute(10)
  74 | 	assert.NotNil(t, res)
  75 | 	assert.NotNil(t, res.Error)
  76 | 	assert.Equal(t, "parameter is invalid", res.Error.Error())
     ...
  78 | 	res = cmd.Execute("CCCC")
  79 | 	assert.NotNil(t, res)
  80 | 	assert.NotNil(t, res.Error)
  81 | 	assert.Equal(t, "task with name CCCC not found", res.Error.Error())
     ...
  83 | 	res = cmd.Execute("count")
  84 | 	assert.NotNil(t, res)
  85 | 	assert.True(t, res.IsSuccess())
     ...
  87 | 	task.mockErr = errors.New("mock error")
  88 | 	res = cmd.Execute("count")
  89 | 	assert.NotNil(t, res)
  90 | 	assert.NotNil(t, res.Error)
  91 | 	assert.Equal(t, "mock error", res.Error.Error())
  92 | }
     ...
  94 | func TestListTaskCommand_Execute(t *testing.T) {
  95 | 	task := &countTask{}
     ...
  97 | 	cmd := &listTaskCommand{}
     ...
  99 | 	res := cmd.Execute()
     ...
 101 | 	assert.True(t, res.IsSuccess())
     ...
 103 | 	_, ok := res.Content.([][]string)
 104 | 	assert.True(t, ok)
     ...
 106 | 	AddTask("count", task)
     ...
 108 | 	res = cmd.Execute()
     ...
 110 | 	assert.True(t, res.IsSuccess())
     ...
 112 | 	rl, ok := res.Content.([][]string)
 113 | 	assert.True(t, ok)
 114 | 	assert.Equal(t, 1, len(rl))
 115 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r3-definitionconsistency-changed-d-cf67f4/repro.json
```

## Evidence and reduction

- representative 41cf2f692422-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects abiosoft/colima@bba803d3d6fa, beego/beego@939cfde380bb, go-gorm/gorm@b3d3bf219f02, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#66827](https://github.com/golang/go/issues/66827) x/tools/gopls: go to definition within imported modules (open, 2024-04-14, 7 comments)
- [golang/go#40584](https://github.com/golang/go/issues/40584) x/tools/gopls: go to the definition of the only non-test interface implementation (open, 2020-08-05, 2 comments)
- [golang/go#73545](https://github.com/golang/go/issues/73545) x/tools/gopls: go to definition should go to replaced version of module (closed, 2025-04-30, 9 comments)
- [golang/go#70462](https://github.com/golang/go/issues/70462) x/tools/gopls: jump to definition on 'return' should go to the result parameter list (closed, 2024-11-20, 10 comments)
- [golang/go#77131](https://github.com/golang/go/issues/77131) x/tools/gopls: Definition: go:embed directive does not resolve to file location on Windows (closed, 2026-01-08, 12 comments)
- [golang/go#35520](https://github.com/golang/go/issues/35520) x/tools/gopls: improve error message when using wrong go command with Go source distribution (open, 2019-11-12, 16 comments)
- [golang/go#50991](https://github.com/golang/go/issues/50991) x/tools/gopls: -remote=auto doesn't use different addresses for different Go versions (open, 2022-02-03, 7 comments)
- [golang/go#75271](https://github.com/golang/go/issues/75271) x/tools/gopls: InlayHint(constantValues): don't exclude booleans (open, 2025-09-04, 2 comments)
- queries: `"go to definition" in:title repo:golang/go is:issue label:gopls`; `definition wrong repo:golang/go is:issue label:gopls`; `definition "go to definition" repo:golang/go is:issue label:gopls`; `definition inconsistent repo:golang/go is:issue label:gopls`
