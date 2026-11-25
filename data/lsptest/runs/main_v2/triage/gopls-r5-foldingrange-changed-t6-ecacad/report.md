# [gopls v0.23.0] foldingRange changes its answer after transformation T6

Draft for the author (not filed). Group `gopls-r5-foldingrange-changed-t6-ecacad`, signature `gopls|r5_transforms|foldingRange:changed`, case family `T6`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `beego/beego@939cfde380bb` (corpus, commit 939cfde380bb9f15844ad633b84f037f7da21584), language go

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T6 applied to `task/governor_command_test.go` (1 edit(s), first [68, 15, 68, 15]).
3. Query `textDocument/foldingRange` on `task/governor_command_test.go` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  17,
  12,
  33,
  "comment"
 ],
 [
  100,
  13,
  100,
  31,
  ""
 ],
 [
  103,
  13,
  103,
  18,
  ""
 ],
 [
  105,
  9,
  105,
  22,
  ""
 ],
 [
  109,
  13,
  109,
  31,
  ""
 ],
 [
  112,
  13,
  112,
  18,
  ""
 ],
 [
  113,
  14,
  113,
  27,
  ""
 ],
 [
  113,
  24,
  113,
  26,
  ""
 ],
 [
  16,
  8,
  23,
  0,
  "imports"
 ],
 [
  25,
  23,
  28,
  0,
  ""
 ],
 [
  30,
  28,
  30,
  47,
  ""
 ],
 [
  30,
  57,
  32,
  0,
  ""
 ],
 [
  30,
  6,
  30,
  18,
  ""
 ],
 [
  34,
  30,
  34,
  49,
  ""
 ],
 [
  34,
  59,
  36,
  0,
  ""
 ],
 [
  34,
  6,
  34,
  18,
  ""
 ],
 [
  38,
  24,
  38,
  43,
  ""
 ],
 [
  38,
  52,
  41,
  0,
  ""
 ],
 [
  38,
  6,
  38,
  18,
  ""
 ],
 [
  43,
  28,
  43,
  63,
  ""
 ],
 [
  43,
  6,
  43,
  18,
  ""
 ],
 [
  43,
  66,
  44,
  0,
  ""
 ],
 [
  46,
  28,
  46,
  47,
  ""
 ],
 [
  46,
  6,
  46,
  18,
  ""
 ],
 [
  46,
  60,
  48,
  0,
  ""
 ],
 [
  50,
  28,
  50,
  63,
  ""
 ],
 [
  50,
  6,
  50,
  18,
  ""
 ],
 [
  50,
  66,
  51,
  0,
  ""
 ],
 [
  53,
  28,
  53,
  47,
  ""
 ],
 [
  53,
  6,
  53,
  18,
  ""
 ],
 [
  53,
  60,
  55,
  0,
  ""
 ],
 [
  57,
  31,
  57,
  50,
  ""
 ],
 [
  57,
  6,
  57,
  18,
  ""
 ],
 [
  57,
  67,
  59,
  0,
  ""
 ],
 [
  61,
  32,
  61,
  44,
  ""
 ],
 [
  61,
  47,
  91,
  0,
  ""
 ],
 [
  63,
  9,
  63,
  22,
  ""
 ],
 [
  68,
  26,
  68,
  32,
  ""
 ],
 [
  69,
  15,
  69,
  27,
  ""
 ],
 [
  70,
  14,
  70,
  58,
  ""
 ],
 [
  72,
  19,
  72,
  21,
  ""
 ],
 [
  73,
  15,
  
... (2095 characters)
```

Actual:

```json
[
 [
  0,
  17,
  12,
  33,
  "comment"
 ],
 [
  100,
  13,
  100,
  31,
  ""
 ],
 [
  103,
  13,
  103,
  18,
  ""
 ],
 [
  105,
  9,
  105,
  22,
  ""
 ],
 [
  109,
  13,
  109,
  31,
  ""
 ],
 [
  112,
  13,
  112,
  18,
  ""
 ],
 [
  113,
  14,
  113,
  27,
  ""
 ],
 [
  113,
  24,
  113,
  26,
  ""
 ],
 [
  16,
  8,
  23,
  0,
  "imports"
 ],
 [
  25,
  23,
  28,
  0,
  ""
 ],
 [
  30,
  28,
  30,
  47,
  ""
 ],
 [
  30,
  57,
  32,
  0,
  ""
 ],
 [
  30,
  6,
  30,
  18,
  ""
 ],
 [
  34,
  30,
  34,
  49,
  ""
 ],
 [
  34,
  59,
  36,
  0,
  ""
 ],
 [
  34,
  6,
  34,
  18,
  ""
 ],
 [
  38,
  24,
  38,
  43,
  ""
 ],
 [
  38,
  52,
  41,
  0,
  ""
 ],
 [
  38,
  6,
  38,
  18,
  ""
 ],
 [
  43,
  28,
  43,
  63,
  ""
 ],
 [
  43,
  6,
  43,
  18,
  ""
 ],
 [
  43,
  66,
  44,
  0,
  ""
 ],
 [
  46,
  28,
  46,
  47,
  ""
 ],
 [
  46,
  6,
  46,
  18,
  ""
 ],
 [
  46,
  60,
  48,
  0,
  ""
 ],
 [
  50,
  28,
  50,
  63,
  ""
 ],
 [
  50,
  6,
  50,
  18,
  ""
 ],
 [
  50,
  66,
  51,
  0,
  ""
 ],
 [
  53,
  28,
  53,
  47,
  ""
 ],
 [
  53,
  6,
  53,
  18,
  ""
 ],
 [
  53,
  60,
  55,
  0,
  ""
 ],
 [
  57,
  31,
  57,
  50,
  ""
 ],
 [
  57,
  6,
  57,
  18,
  ""
 ],
 [
  57,
  67,
  59,
  0,
  ""
 ],
 [
  61,
  32,
  61,
  44,
  ""
 ],
 [
  61,
  47,
  91,
  0,
  ""
 ],
 [
  63,
  9,
  63,
  22,
  ""
 ],
 [
  68,
  15,
  68,
  32,
  ""
 ],
 [
  69,
  15,
  69,
  27,
  ""
 ],
 [
  70,
  14,
  70,
  58,
  ""
 ],
 [
  72,
  19,
  72,
  21,
  ""
 ],
 [
  73,
  15,
  
... (2095 characters)
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r5-foldingrange-changed-t6-ecacad/repro.json
```

## Evidence and reduction

- representative 2628b01ed446-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects beego/beego@939cfde380bb, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#29149](https://github.com/golang/go/issues/29149) x/tools/internal/lsp: handle unicode code points that are encoded as multiple bytes (closed, 2018-12-07, 2 comments)
- [golang/go#71489](https://github.com/golang/go/issues/71489) x/tools/gopls: FoldingRange omitempty causes EndCharacter=0 to be omitted, changing its semantics in clients that distinguish 0 from missing (closed, 2025-01-30, 15 comments)
- [golang/go#79524](https://github.com/golang/go/issues/79524) x/tools/gopls: semantic tokens no longer returned (regression in v0.22.0) (closed, 2026-05-19, 11 comments)
- queries: `unicode in:title repo:golang/go is:issue label:gopls`; `"folding range" wrong repo:golang/go is:issue label:gopls`; `"folding range" unicode repo:golang/go is:issue label:gopls`; `"folding range" whitespace repo:golang/go is:issue label:gopls`
