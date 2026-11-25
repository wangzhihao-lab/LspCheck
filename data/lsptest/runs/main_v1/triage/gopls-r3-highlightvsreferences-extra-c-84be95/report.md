# [gopls v0.23.0] highlightVsReferences: two routes to the same fact disagree

Draft for the author (not filed). Group `gopls-r3-highlightvsreferences-extra-c-84be95`, signature `gopls|r3_routes|highlightVsReferences:extra`, case family `c`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `fatedier/frp@d20a23299600` (corpus, commit d20a232996007dfe6ab425abc0a39a3ae9a0889b), language go

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/documentHighlight` and `textDocument/references` (includeDeclaration) on `pkg/transport/tls.go` at line 81, column 37 (LSP position {line: 80, character: 36}); every highlight range must be a reference range in that file.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  20,
  1,
  20,
  14
 ],
 [
  54,
  13,
  54,
  17
 ],
 [
  60,
  17,
  60,
  21
 ],
 [
  69,
  73,
  69,
  77
 ],
 [
  80,
  34,
  80,
  38
 ],
 [
  81,
  9,
  81,
  13
 ],
 [
  163,
  9,
  163,
  13
 ]
]
```

Actual:

```json
[
 [
  20,
  1,
  20,
  14
 ],
 [
  54,
  13,
  54,
  17
 ],
 [
  60,
  17,
  60,
  21
 ],
 [
  69,
  73,
  69,
  77
 ],
 [
  80,
  33,
  80,
  47
 ],
 [
  80,
  34,
  80,
  38
 ],
 [
  81,
  9,
  81,
  13
 ],
 [
  85,
  9,
  85,
  12
 ],
 [
  89,
  9,
  89,
  12
 ],
 [
  92,
  8,
  92,
  12
 ],
 [
  163,
  9,
  163,
  13
 ]
]
```

Project file `pkg/transport/tls.go`:

```
   1 | // Copyright 2023 The frp Authors
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
  15 | package transport
     ...
  17 | import (
  18 | 	"crypto/rand"
  19 | 	"crypto/rsa"
  20 | 	"crypto/tls"
  21 | 	"crypto/x509"
  22 | 	"encoding/pem"
  23 | 	"fmt"
  24 | 	"math/big"
  25 | 	"os"
  26 | 	"time"
  27 | )
     ...
  29 | func newCustomTLSKeyPair(certfile, keyfile string) (*tls.Certificate, error) {
  30 | 	tlsCert, err := tls.LoadX509KeyPair(certfile, keyfile)
  31 | 	if err != nil {
  32 | 		return nil, err
  33 | 	}
  34 | 	return &tlsCert, nil
  35 | }
     ...
  37 | func newRandomTLSKeyPair() (*tls.Certificate, error) {
  38 | 	key, err := rsa.GenerateKey(rand.Reader, 2048)
  39 | 	if err != nil {
  40 | 		return nil, err
  41 | 	}
     ...
  43 | 	// Generate a random positive serial number with 128 bits of entropy.
  44 | 	// RFC 5280 requires serial numbers to be positive integers (not zero).
  45 | 	serialNumberLimit := new(big.Int).Lsh(big.NewInt(1), 128)
  46 | 	serialNumber, err := rand.Int(rand.Reader, serialNumberLimit)
  47 | 	if err != nil {
  48 | 		return nil, err
  49 | 	}
  50 | 	// Ensure serial number is positive (not zero)
  51 | 	if serialNumber.Sign() == 0 {
  52 | 		serialNumber = big.NewInt(1)
  53 | 	}
     ...
  55 | 	template := x509.Certificate{
  56 | 		SerialNumber: serialNumber,
  57 | 		NotBefore:    time.Now().Add(-1 * time.Hour),
  58 | 		NotAfter:     time.Now().Add(365 * 24 * time.Hour * 10),
  59 | 	}
     ...
  61 | 	certDER, err := x509.CreateCertificate(
  62 | 		rand.Reader,
  63 | 		&template,
  64 | 		&template,
  65 | 		&key.PublicKey,
  66 | 		key)
  67 | 	if err != nil {
  68 | 		return nil, err
  69 | 	}
  70 | 	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)})
  71 | 	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: certDER})
     ...
  73 | 	tlsCert, err := tls.X509KeyPair(certPEM, keyPEM)
  74 | 	if err != nil {
  75 | 		return nil, err
  76 | 	}
  77 | 	return &tlsCert, nil
  78 | }
     ...
  80 | // Only support one ca file to add
  81 | func newCertPool(caPath string) (*x509.CertPool, error) {
  82 | 	pool := x509.NewCertPool()
     ...
  84 | 	caCrt, err := os.ReadFile(caPath)
  85 | 	if err != nil {
  86 | 		return nil, err
  87 | 	}
     ...
  89 | 	if !pool.AppendCertsFromPEM(caCrt) {
  90 | 		return nil, fmt.Errorf("failed to parse CA certificate from file %q: no valid PEM certificates found", caPath)
  91 | 	}
     ...
  93 | 	return pool, nil
  94 | }
     ...
  96 | func NewServerTLSConfig(certPath, keyPath, caPath string) (*tls.Config, error) {
  97 | 	base := &tls.Config{}
     ...
  99 | 	if certPath == "" || keyPath == "" {
 100 | 		// server will generate tls conf by itself
 101 | 		cert, err := newRandomTLSKeyPair()
 102 | 		if err != nil {
 103 | 			return nil, err
 104 | 		}
 105 | 		base.Certificates = []tls.Certificate{*cert}
 106 | 	} else {
 107 | 		cert, err := newCustomTLSKeyPair(certPath, keyPath)
 108 | 		if err != nil {
 109 | 			return nil, err
 110 | 		}
     ...
 112 | 		base.Certificates = []tls.Certificate{*cert}
 113 | 	}
     ...
 115 | 	if caPath != "" {
 116 | 		pool, err := newCertPool(caPath)
 117 | 		if err != nil {
 118 | 			return nil, err
 119 | 		}
     ...
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r3-highlightvsreferences-extra-c-84be95/repro.json
```

## Evidence and reduction

- representative 5f7120bd44c4-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects caddyserver/caddy@c18099a0af5e, fatedier/frp@d20a23299600, jesseduffield/lazydocker@7e7aadc2071d, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#81462](https://github.com/golang/go/issues/81462) x/tools/gopls: follow linkname references (open, 2026-09-10, 3 comments)
- [golang/go#73781](https://github.com/golang/go/issues/73781) x/tools/gopls: References does not find all references in the workspace (open, 2022-09-08, 24 comments)
- [golang/go#74307](https://github.com/golang/go/issues/74307) x/tools/gopls: References: report unkeyed composite literals as implicit references to struct fields (open, 2025-06-19, 3 comments)
- [golang/go#66356](https://github.com/golang/go/issues/66356) x/tools/gopls: feature: alternative 'references' query that reports implied references to struct fields (etc) (open, 2024-03-16, 7 comments)
- [golang/go#40862](https://github.com/golang/go/issues/40862) x/tools/gopls: add codelens to show number of references to each symbol (open, 2020-08-16, 41 comments)
- [golang/go#74917](https://github.com/golang/go/issues/74917) x/tools/gopls: prefix SignatureHelp label with "func" (open, 2025-08-06, 4 comments)
- [golang/go#63282](https://github.com/golang/go/issues/63282) x/tools/gopls: express completion scoring in terms of down-ranking factors (open, 2023-09-28, 2 comments)
- [golang/go#57963](https://github.com/golang/go/issues/57963) x/tools/gopls: add analyzer that reports broken doc links (open, 2023-01-23, 13 comments)
- queries: `references in:title repo:golang/go is:issue label:gopls`; `highlight extra repo:golang/go is:issue label:gopls`; `highlight references repo:golang/go is:issue label:gopls`; `highlight inconsistent repo:golang/go is:issue label:gopls`
