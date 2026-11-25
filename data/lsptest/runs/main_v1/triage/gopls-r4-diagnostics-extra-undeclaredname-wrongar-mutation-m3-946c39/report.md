# [gopls v0.23.0] mutation:M3 edit is not valid (diagnostics:extra:UndeclaredName,WrongArgCount)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-undeclaredname-wrongar-mutation-m3-946c39`, signature `gopls|r4_edits|diagnostics:extra:UndeclaredName,WrongArgCount`, case family `mutation:M3`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `fatedier/frp@d20a23299600` (corpus, commit d20a232996007dfe6ab425abc0a39a3ae9a0889b), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open pkg/config/legacy/value.go`
3. textDocument/didChange: `change pkg/config/legacy/value.go (71, 26)-(71, 27) ""`
4. textDocument/didChange: `change pkg/config/legacy/value.go (65, 1)-(66, 1) ""`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `pkg/config/load_test.go`, `pkg/transport/tls.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `pkg/config/legacy/value.go` line 66, column 6 (LSP position {line: 65, character: 5}) (M3:quickfix-errors:Remove variable b); compare with the same query in a fresh session on the same content (expected).

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
  "UndeclaredName",
  "compiler",
  "undefined: b"
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "WrongArgCount",
  "compiler",
  "not enough arguments in call to RenderContent have () want ([]byte)"
 ]
]
```

Project file `pkg/config/legacy/value.go`:

```
   1 | // Copyright 2020 The frp Authors
   2 | //
   3 | // Licensed under the Apache License, Version 2.0 (the "License");
   4 | // you may not use this file except in compliance with the License.
   5 | // You may obtain a copy of the License at
   6 | //
   7 | //     http://www.apache.org/licenses/LICENSE-2.0
   8 | //
   9 | // Unless required by applicable law or agreed to in writing, software
  10 | // distributed under the License is distributed on an "AS IS" BASIS,
  11 | // WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  12 | // See the License for the specific language governing permissions and
  13 | // limitations under the License.
     ...
  15 | package legacy
     ...
  17 | import (
  18 | 	"bytes"
  19 | 	"os"
  20 | 	"strings"
  21 | 	"text/template"
  22 | )
     ...
  24 | var glbEnvs map[string]string
     ...
  26 | func init() {
  27 | 	glbEnvs = make(map[string]string)
  28 | 	envs := os.Environ()
  29 | 	for _, env := range envs {
  30 | 		pair := strings.SplitN(env, "=", 2)
  31 | 		if len(pair) != 2 {
  32 | 			continue
  33 | 		}
  34 | 		glbEnvs[pair[0]] = pair[1]
  35 | 	}
  36 | }
     ...
  38 | type Values struct {
  39 | 	Envs map[string]string // environment vars
  40 | }
     ...
  42 | func GetValues() *Values {
  43 | 	return &Values{
  44 | 		Envs: glbEnvs,
  45 | 	}
  46 | }
     ...
  48 | func RenderContent(in []byte) (out []byte, err error) {
  49 | 	tmpl, errRet := template.New("frp").Parse(string(in))
  50 | 	if errRet != nil {
  51 | 		err = errRet
  52 | 		return
  53 | 	}
     ...
  55 | 	buffer := bytes.NewBufferString("")
  56 | 	v := GetValues()
  57 | 	err = tmpl.Execute(buffer, v)
  58 | 	if err != nil {
  59 | 		return
  60 | 	}
  61 | 	out = buffer.Bytes()
  62 | 	return
  63 | }
     ...
  65 | func GetRenderedConfFromFile(path string) (out []byte, err error) {
  66 | 	var b []byte
  67 | 	b, err = os.ReadFile(path)
  68 | 	if err != nil {
  69 | 		return
  70 | 	}
     ...
  72 | 	out, err = RenderContent(b)
  73 | 	return
  74 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r4-diagnostics-extra-undeclaredname-wrongar-mutation-m3-946c39/repro.json
```

## Evidence and reduction

- representative ced4ef795b99-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 4.418 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects fatedier/frp@d20a23299600, timings settled, seeds 1

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
