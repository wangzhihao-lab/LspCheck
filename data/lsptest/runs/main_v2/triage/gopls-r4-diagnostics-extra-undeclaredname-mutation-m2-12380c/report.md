# [gopls v0.23.0] mutation:M2 edit is not valid (diagnostics:extra:UndeclaredName)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-undeclaredname-mutation-m2-12380c`, signature `gopls|r4_edits|diagnostics:extra:UndeclaredName`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `abiosoft/colima@bba803d3d6fa` (corpus, commit bba803d3d6fa9372a60f747e5dad4c8e80db7cde), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open core/core.go`
3. textDocument/didChange: `change core/core.go (30, 94)-(30, 102) "qemurch"`
4. textDocument/didChange: `change core/core.go (24, 1)-(25, 1) ""`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `environment/vm/lima/limautil/image_test.go`, `util/downloader/download.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `core/core.go` line 25, column 2 (LSP position {line: 24, character: 1}) (M2:quickfix-errors:Remove variable qemuArch); compare with the same query in a fresh session on the same content (expected).

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
  "undefined: qemuArch"
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "UndeclaredName",
  "compiler",
  "undefined: qemurch"
 ]
]
```

Project file `core/core.go`:

```
   1 | package core
     ...
   3 | import (
   4 | 	"bytes"
   5 | 	"encoding/json"
   6 | 	"fmt"
   7 | 	"strings"
     ...
   9 | 	"github.com/sirupsen/logrus"
     ...
  11 | 	"github.com/abiosoft/colima/cli"
  12 | 	"github.com/abiosoft/colima/environment"
  13 | 	"github.com/coreos/go-semver/semver"
  14 | )
     ...
  16 | const limaVersion = "v0.18.0" // minimum Lima version supported
     ...
  18 | type (
  19 | 	hostActions  = environment.HostActions
  20 | 	guestActions = environment.GuestActions
  21 | )
     ...
  23 | // SetupBinfmt downloads and install binfmt
  24 | func SetupBinfmt(host hostActions, guest guestActions, arch environment.Arch) error {
  25 | 	qemuArch := environment.AARCH64
  26 | 	if arch.Value().GoArch() == "arm64" {
  27 | 		qemuArch = environment.X8664
  28 | 	}
     ...
  30 | 	install := func() error {
  31 | 		if err := guest.Run("sh", "-c", "sudo QEMU_PRESERVE_ARGV0=1 /usr/bin/binfmt --install 386,"+qemuArch.GoArch()); err != nil {
  32 | 			return fmt.Errorf("error installing binfmt: %w", err)
  33 | 		}
  34 | 		return nil
  35 | 	}
     ...
  37 | 	// validate binfmt
  38 | 	if err := guest.RunQuiet("command", "-v", "binfmt"); err != nil {
  39 | 		return fmt.Errorf("binfmt not found: %w", err)
  40 | 	}
     ...
  42 | 	return install()
  43 | }
     ...
  45 | // LimaVersionSupported checks if the currently installed Lima version is supported.
  46 | func LimaVersionSupported() error {
  47 | 	var values struct {
  48 | 		Version string `json:"version"`
  49 | 	}
  50 | 	var buf bytes.Buffer
  51 | 	cmd := cli.Command("limactl", "info")
  52 | 	cmd.Stdout = &buf
     ...
  54 | 	if err := cmd.Run(); err != nil {
  55 | 		return fmt.Errorf("error checking Lima version: %w", err)
  56 | 	}
     ...
  58 | 	if err := json.NewDecoder(&buf).Decode(&values); err != nil {
  59 | 		return fmt.Errorf("error decoding 'limactl info' json: %w", err)
  60 | 	}
  61 | 	// remove pre-release hyphen
  62 | 	parts := strings.SplitN(values.Version, "-", 2)
  63 | 	if len(parts) > 0 {
  64 | 		values.Version = parts[0]
  65 | 	}
     ...
  67 | 	if parts[0] == "HEAD" {
  68 | 		logrus.Warnf("to avoid compatibility issues, ensure lima development version (%s) in use is not lower than %s", values.Version, limaVersion)
  69 | 		return nil
  70 | 	}
     ...
  72 | 	min := semver.New(strings.TrimPrefix(limaVersion, "v"))
  73 | 	current, err := semver.NewVersion(strings.TrimPrefix(values.Version, "v"))
  74 | 	if err != nil {
  75 | 		return fmt.Errorf("invalid semver version for Lima: %w", err)
  76 | 	}
     ...
  78 | 	if min.Compare(*current) > 0 {
  79 | 		return fmt.Errorf("minimum Lima version supported is %s, current version is %s", limaVersion, values.Version)
  80 | 	}
     ...
  82 | 	return nil
  83 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r4-diagnostics-extra-undeclaredname-mutation-m2-12380c/repro.json
```

## Evidence and reduction

- representative f373be50b7d7-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 3.13 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects abiosoft/colima@bba803d3d6fa, timings settled, seeds 2

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
