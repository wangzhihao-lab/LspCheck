# [gopls v0.23.0] mutation:M2 edit is not valid (diagnostics:extra:IncompatibleAssign)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-incompatibleassign-mutation-m2-ade1f0`, signature `gopls|r4_edits|diagnostics:extra:IncompatibleAssign`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `beego/beego@939cfde380bb` (corpus, commit 939cfde380bb9f15844ad633b84f037f7da21584), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open client/cache/bloom_filter_cache.go`
3. textDocument/didChange: `change client/cache/bloom_filter_cache.go (37, 1)-(37, 11) "expiraation"`
4. textDocument/didChange: `change client/cache/bloom_filter_cache.go (43, 1)-(43, 1) "expiration := 0\n\t"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `client/orm/ddl.go`, `core/validation/validators.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `client/cache/bloom_filter_cache.go` line 48, column 15 (LSP position {line: 47, character: 14}) (M2:quickfix-errors:Create variable expiration); compare with the same query in a fresh session on the same content (expected).

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
  "cannot use expiration (variable of type int) as time.Duration value in struct literal"
 ]
]
```

Project file `client/cache/bloom_filter_cache.go`:

```
   1 | // Copyright 2014 beego Author. All Rights Reserved.
   2 | //
   3 | // Licensed under the Apache License, Version 2.0 (the "License");
   4 | // you may not use this file except in compliance with the License.
   5 | // You may obtain a copy of the License at
   6 | //
   7 | //      http://www.apache.org/licenses/LICENSE-2.0
   8 | //
   9 | // Unless required by applicable law or agreed to in writing, software
  10 | // distributed under the License is distributed on an "AS IS" BASIS,
  11 | // WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  12 | // See the License for the specific language governing permissions and
  13 | // limitations under the License.
     ...
  15 | package cache
     ...
  17 | import (
  18 | 	"context"
  19 | 	"errors"
  20 | 	"time"
     ...
  22 | 	"github.com/beego/beego/v2/core/berror"
  23 | )
     ...
  25 | type BloomFilterCache struct {
  26 | 	Cache
  27 | 	blm        BloomFilter
  28 | 	loadFunc   func(ctx context.Context, key string) (any, error)
  29 | 	expiration time.Duration // set cache expiration, default never expire
  30 | }
     ...
  32 | type BloomFilter interface {
  33 | 	Test(data string) bool
  34 | 	Add(data string)
  35 | }
     ...
  37 | func NewBloomFilterCache(cache Cache, ln func(ctx context.Context, key string) (any, error), blm BloomFilter,
  38 | 	expiration time.Duration,
  39 | ) (*BloomFilterCache, error) {
  40 | 	if cache == nil || ln == nil || blm == nil {
  41 | 		return nil, berror.Error(InvalidInitParameters, "missing required parameters")
  42 | 	}
     ...
  44 | 	return &BloomFilterCache{
  45 | 		Cache:      cache,
  46 | 		blm:        blm,
  47 | 		loadFunc:   ln,
  48 | 		expiration: expiration,
  49 | 	}, nil
  50 | }
     ...
  52 | func (bfc *BloomFilterCache) Get(ctx context.Context, key string) (any, error) {
  53 | 	val, err := bfc.Cache.Get(ctx, key)
  54 | 	if err != nil && !errors.Is(err, ErrKeyNotExist) {
  55 | 		return nil, err
  56 | 	}
  57 | 	if errors.Is(err, ErrKeyNotExist) {
  58 | 		exist := bfc.blm.Test(key)
  59 | 		if exist {
  60 | 			val, err = bfc.loadFunc(ctx, key)
  61 | 			if err != nil {
  62 | 				return nil, berror.Wrap(err, LoadFuncFailed, "cache unable to load data")
  63 | 			}
  64 | 			err = bfc.Put(ctx, key, val, bfc.expiration)
  65 | 			if err != nil {
  66 | 				return val, err
  67 | 			}
  68 | 		}
  69 | 	}
  70 | 	return val, nil
  71 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r4-diagnostics-extra-incompatibleassign-mutation-m2-ade1f0/repro.json
```

## Evidence and reduction

- representative b6a3bd30c8df-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 4.242 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects beego/beego@939cfde380bb, timings settled, seeds 2

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
