# [gopls v0.23.0] a stale codeAction handle resolves to a different edit after an intervening edit

Draft for the author (not filed). Group `gopls-r2-codeactionresolve-changed-codeaction-70b3e9`, signature `gopls|r2_handles|codeActionResolve:changed`, case family `codeAction`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `nektos/act@4f411281417e` (corpus, commit 4f411281417e88660bea1c1a1749aa71ae0bd60f), language go

## Relation violated

Handle validity (R2): a code-action or completion handle minted before an edit and resolved after it must fail, return no edit, or return the same edit as a fresh handle for the same item.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. didOpen `pkg/container/linux_container_environment_extensions_test.go`; request code actions at line 35, column 39 (LSP position {line: 34, character: 38}) and resolve them; didChange: insert `"\n"` at line 1 (top); wait until idle; resolve the OLD code action `Split arguments into separate lines`; request and resolve a fresh one at the mapped position: the old handle must fail, give no edit, or give the fresh handle's edit.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "pkg/container/linux_container_environment_extensions_test.go",
  35,
  16,
  35,
  16,
  "\n\t\t\t\t"
 ],
 [
  "pkg/container/linux_container_environment_extensions_test.go",
  35,
  29,
  35,
  31,
  ",\n\t\t\t\t"
 ],
 [
  "pkg/container/linux_container_environment_extensions_test.go",
  35,
  46,
  35,
  46,
  ",\n\t\t\t"
 ]
]
```

Actual:

```json
[
 [
  "pkg/container/linux_container_environment_extensions_test.go",
  34,
  28,
  34,
  30,
  ",\n\t\t\t\t"
 ],
 [
  "pkg/container/linux_container_environment_extensions_test.go",
  34,
  4,
  34,
  4,
  "\n\t\t\t\t"
 ],
 [
  "pkg/container/linux_container_environment_extensions_test.go",
  34,
  49,
  34,
  51,
  ",\n\t\t\t\t"
 ],
 [
  "pkg/container/linux_container_environment_extensions_test.go",
  34,
  81,
  34,
  81,
  ",\n\t\t\t"
 ]
]
```

Project file `pkg/container/linux_container_environment_extensions_test.go`:

```
   1 | package container
     ...
   3 | import (
   4 | 	"fmt"
   5 | 	"os"
   6 | 	"runtime"
   7 | 	"strings"
   8 | 	"testing"
     ...
  10 | 	log "github.com/sirupsen/logrus"
  11 | 	"github.com/stretchr/testify/assert"
  12 | )
     ...
  14 | func TestContainerPath(t *testing.T) {
  15 | 	type containerPathJob struct {
  16 | 		destinationPath string
  17 | 		sourcePath      string
  18 | 		workDir         string
  19 | 	}
     ...
  21 | 	linuxcontainerext := &LinuxContainerEnvironmentExtensions{}
     ...
  23 | 	if runtime.GOOS == "windows" {
  24 | 		cwd, err := os.Getwd()
  25 | 		if err != nil {
  26 | 			log.Error(err)
  27 | 		}
     ...
  29 | 		rootDrive := os.Getenv("SystemDrive")
  30 | 		rootDriveLetter := strings.ReplaceAll(strings.ToLower(rootDrive), `:`, "")
  31 | 		for _, v := range []containerPathJob{
  32 | 			{"/mnt/c/Users/act/go/src/github.com/nektos/act", "C:\\Users\\act\\go\\src\\github.com\\nektos\\act\\", ""},
  33 | 			{"/mnt/f/work/dir", `F:\work\dir`, ""},
  34 | 			{"/mnt/c/windows/to/unix", "windows\\to\\unix", fmt.Sprintf("%s\\", rootDrive)},
  35 | 			{fmt.Sprintf("/mnt/%v/act", rootDriveLetter), "act", fmt.Sprintf("%s\\", rootDrive)},
  36 | 		} {
  37 | 			if v.workDir != "" {
  38 | 				if err := os.Chdir(v.workDir); err != nil {
  39 | 					log.Error(err)
  40 | 					t.Fail()
  41 | 				}
  42 | 			}
     ...
  44 | 			assert.Equal(t, v.destinationPath, linuxcontainerext.ToContainerPath(v.sourcePath))
  45 | 		}
     ...
  47 | 		if err := os.Chdir(cwd); err != nil {
  48 | 			log.Error(err)
  49 | 		}
  50 | 	} else {
  51 | 		cwd, err := os.Getwd()
  52 | 		if err != nil {
  53 | 			log.Error(err)
  54 | 		}
  55 | 		for _, v := range []containerPathJob{
  56 | 			{"/home/act/go/src/github.com/nektos/act", "/home/act/go/src/github.com/nektos/act", ""},
  57 | 			{"/home/act", `/home/act/`, ""},
  58 | 			{cwd, ".", ""},
  59 | 		} {
  60 | 			assert.Equal(t, v.destinationPath, linuxcontainerext.ToContainerPath(v.sourcePath))
  61 | 		}
  62 | 	}
  63 | }
     ...
  65 | type typeAssertMockContainer struct {
  66 | 	Container
  67 | 	LinuxContainerEnvironmentExtensions
  68 | }
     ...
  70 | // Type assert Container + LinuxContainerEnvironmentExtensions implements ExecutionsEnvironment
  71 | var _ ExecutionsEnvironment = &typeAssertMockContainer{}
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r2-codeactionresolve-changed-codeaction-70b3e9/repro.json
```

## Evidence and reduction

- representative 8253217867f9-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects caddyserver/caddy@c18099a0af5e, charmbracelet/bubbletea@657aaae216e3, nektos/act@4f411281417e, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [golang/go#71314](https://github.com/golang/go/issues/71314) x/tools/gopls: gopls Extracts declarations to new file when a liveshare guest puts a cursor on a function name (closed, 2025-01-17, 4 comments)
- queries: `"code action resolve" wrong repo:golang/go is:issue label:gopls`; `"code action resolve" stale repo:golang/go is:issue label:gopls`
