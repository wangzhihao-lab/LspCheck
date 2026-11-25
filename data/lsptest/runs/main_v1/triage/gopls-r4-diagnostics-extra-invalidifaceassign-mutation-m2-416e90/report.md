# [gopls v0.23.0] mutation:M2 edit is not valid (diagnostics:extra:InvalidIfaceAssign)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-invalidifaceassign-mutation-m2-416e90`, signature `gopls|r4_edits|diagnostics:extra:InvalidIfaceAssign`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `XTLS/Xray-core@d562d8947d31` (corpus, commit d562d8947d3175db86b4fa849742433a9876cb63), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open common/crypto/io.go`
3. textDocument/didChange: `change common/crypto/io.go (17, 10)-(17, 16) "reaer"`
4. textDocument/didChange: `change common/crypto/io.go (15, 3)-(15, 3) "aer := 0\n\tre"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `proxy/tun/stack_gvisor_icmp_handler.go`, `transport/internet/finalmask/xicmp/xicmp_test.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `common/crypto/io.go` line 18, column 11 (LSP position {line: 17, character: 10}) (M2:quickfix-errors:Create variable reaer); compare with the same query in a fresh session on the same content (expected).

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
  "InvalidIfaceAssign",
  "compiler",
  "cannot use reaer (variable of type int) as io.Reader value in struct literal: int does not implement io.Reader (missing method Read)"
 ]
]
```

Project file `common/crypto/io.go`:

```
   1 | package crypto
     ...
   3 | import (
   4 | 	"crypto/cipher"
   5 | 	"io"
     ...
   7 | 	"github.com/xtls/xray-core/common/buf"
   8 | )
     ...
  10 | type CryptionReader struct {
  11 | 	stream cipher.Stream
  12 | 	reader io.Reader
  13 | }
     ...
  15 | func NewCryptionReader(stream cipher.Stream, reader io.Reader) *CryptionReader {
  16 | 	return &CryptionReader{
  17 | 		stream: stream,
  18 | 		reader: reader,
  19 | 	}
  20 | }
     ...
  22 | func (r *CryptionReader) Read(data []byte) (int, error) {
  23 | 	nBytes, err := r.reader.Read(data)
  24 | 	if nBytes > 0 {
  25 | 		r.stream.XORKeyStream(data[:nBytes], data[:nBytes])
  26 | 	}
  27 | 	return nBytes, err
  28 | }
     ...
  30 | var _ buf.Writer = (*CryptionWriter)(nil)
     ...
  32 | type CryptionWriter struct {
  33 | 	stream    cipher.Stream
  34 | 	writer    io.Writer
  35 | 	bufWriter buf.Writer
  36 | }
     ...
  38 | // NewCryptionWriter creates a new CryptionWriter.
  39 | func NewCryptionWriter(stream cipher.Stream, writer io.Writer) *CryptionWriter {
  40 | 	return &CryptionWriter{
  41 | 		stream:    stream,
  42 | 		writer:    writer,
  43 | 		bufWriter: buf.NewWriter(writer),
  44 | 	}
  45 | }
     ...
  47 | // Write implements io.Writer.Write().
  48 | func (w *CryptionWriter) Write(data []byte) (int, error) {
  49 | 	w.stream.XORKeyStream(data, data)
     ...
  51 | 	if err := buf.WriteAllBytes(w.writer, data, nil); err != nil {
  52 | 		return 0, err
  53 | 	}
  54 | 	return len(data), nil
  55 | }
     ...
  57 | // WriteMultiBuffer implements buf.Writer.
  58 | func (w *CryptionWriter) WriteMultiBuffer(mb buf.MultiBuffer) error {
  59 | 	for _, b := range mb {
  60 | 		w.stream.XORKeyStream(b.Bytes(), b.Bytes())
  61 | 	}
     ...
  63 | 	return w.bufWriter.WriteMultiBuffer(mb)
  64 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r4-diagnostics-extra-invalidifaceassign-mutation-m2-416e90/repro.json
```

## Evidence and reduction

- representative 07c55fb203fd-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 4.5 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects XTLS/Xray-core@d562d8947d31, timings settled, seeds 1

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
