# [gopls v0.23.0] codeAction adds entries after transformation T1

Draft for the author (not filed). Group `gopls-r5-codeaction-extra-t1-6dfb45`, signature `gopls|r5_transforms|codeAction:extra`, case family `T1`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `gin-gonic/gin@3b08cd7235bd` (corpus, commit 3b08cd7235bd5ad2f055aa9e38135f111f6c5926), language go

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T1 applied to `binding/json.go` (1 edit(s), first [14, 0, 14, 0]).
3. Query `textDocument/codeAction` on `binding/json.go` line 29, column 22 (LSP position {line: 28, character: 21}) (pos); compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Add test for Name",
  "source.addTest"
 ],
 [
  "Browse arm64 assembly for Name",
  "source.assembly"
 ],
 [
  "Browse documentation for package binding",
  "source.doc"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Extract declarations to new file",
  "refactor.extract.toNewFile"
 ],
 [
  "Show compiler optimization details for \"binding\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"binding\"",
  "source.splitPackage"
 ]
]
```

Actual:

```json
[
 [
  "Add test for Name",
  "source.addTest"
 ],
 [
  "Browse arm64 assembly for Name",
  "source.assembly"
 ],
 [
  "Browse documentation for package binding",
  "source.doc"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Extract declarations to new file",
  "refactor.extract.toNewFile"
 ],
 [
  "Organize Imports",
  "source.organizeImports"
 ],
 [
  "Show compiler optimization details for \"binding\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"binding\"",
  "source.splitPackage"
 ]
]
```

Project file `binding/json.go`:

```
   1 | // Copyright 2014 Manu Martinez-Almeida. All rights reserved.
   2 | // Use of this source code is governed by a MIT style
   3 | // license that can be found in the LICENSE file.
     ...
   5 | package binding
     ...
   7 | import (
   8 | 	"bytes"
   9 | 	"errors"
  10 | 	"io"
  11 | 	"net/http"
     ...
  13 | 	"github.com/gin-gonic/gin/codec/json"
  14 | )
     ...
  16 | // EnableDecoderUseNumber is used to call the UseNumber method on the JSON
  17 | // Decoder instance. UseNumber causes the Decoder to unmarshal a number into an
  18 | // any as a Number instead of as a float64.
  19 | var EnableDecoderUseNumber = false
     ...
  21 | // EnableDecoderDisallowUnknownFields is used to call the DisallowUnknownFields method
  22 | // on the JSON Decoder instance. DisallowUnknownFields causes the Decoder to
  23 | // return an error when the destination is a struct and the input contains object
  24 | // keys which do not match any non-ignored, exported fields in the destination.
  25 | var EnableDecoderDisallowUnknownFields = false
     ...
  27 | type jsonBinding struct{}
     ...
  29 | func (jsonBinding) Name() string {
  30 | 	return "json"
  31 | }
     ...
  33 | func (jsonBinding) Bind(req *http.Request, obj any) error {
  34 | 	if req == nil || req.Body == nil {
  35 | 		return errors.New("invalid request")
  36 | 	}
  37 | 	return decodeJSON(req.Body, obj)
  38 | }
     ...
  40 | func (jsonBinding) BindBody(body []byte, obj any) error {
  41 | 	return decodeJSON(bytes.NewReader(body), obj)
  42 | }
     ...
  44 | func decodeJSON(r io.Reader, obj any) error {
  45 | 	decoder := json.API.NewDecoder(r)
  46 | 	if EnableDecoderUseNumber {
  47 | 		decoder.UseNumber()
  48 | 	}
  49 | 	if EnableDecoderDisallowUnknownFields {
  50 | 		decoder.DisallowUnknownFields()
  51 | 	}
  52 | 	if err := decoder.Decode(obj); err != nil {
  53 | 		return err
  54 | 	}
  55 | 	return validate(obj)
  56 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r5-codeaction-extra-t1-6dfb45/repro.json
```

## Evidence and reduction

- representative 0c88a9c856de-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects gin-gonic/gin@3b08cd7235bd, timings settled, seeds 1

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
