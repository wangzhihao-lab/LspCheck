"""Screening decisions: gopls, sheets gopls_04-07.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "gopls"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    # R1 history independence
    47436: ("R1", "A", "Fixing a bad //go:embed pattern clears its diagnostic, but re-breaking it leaves diagnostics stale because embed directive changes did not invalidate metadata (header-only parse).", "edit-undo: fix then re-break a //go:embed pattern in main.go; compare diagnostics with fresh open"),
    50267: ("R1", "A", "After didClose followed by didOpen of the same file gopls did not re-send diagnostics, unlike a fresh open; the fix re-publishes diagnostics on open and close events.", "open-close: close and reopen a file with errors; visible when the client drops diagnostics on close"),
    50327: ("R1", "C", "Telemetry panic 'getSnapshot called after shutdown': the goroutine spawned by didChangeConfiguration read a view that could already be deleted; no reproduction steps.", "race: rapid didChangeConfiguration changes that recreate views while diagnosing"),
    51325: ("R1", "B", "After go mod edit -go=1.18 on disk, diagnostics were not re-pushed because the go directive was not hashed into the package key.", "file-op: change the go directive of go.mod on disk; compare generic-code diagnostics with fresh"),
    51732: ("R1", "B", "With go.work, changing the go version in go.mod (go mod edit -go=1.18) left the type-parameter diagnostic in place and no new diagnostics were pushed.", "file-op: go.work plus go.mod at go 1.16 with generic code; edit go directive on disk"),
    52500: ("R1", "A", "Changing a file's package clause from x_test to x and back leaves the file in no package because packages were not invalidated for files whose package name changed.", "edit-undo: toggle package clause x_test -> x -> x_test; compare diagnostics and hover with fresh"),
    52981: ("R1", "A", "Typing the closing paren of an import block leaves 'could not import embed' because metadata was not reloaded when the import header went from unparseable to parseable.", "typing: type 'import ( _ \"embed\"' then ')'; compare diagnostics with fresh open"),
    53631: ("R1", "B", "Changes to a go.work file outside the workspace selected via GOWORK were neither tracked nor watched, so gopls kept the old workspace state.", "file-op: GOWORK points outside the workspace; edit that go.work on disk"),
    54073: ("R1", "B", "Creating a previously missing package on disk did not invalidate 'missing package' errors in its importers (regtest TestCreateDependency).", "file-op: import a missing package, then create its file on disk"),
    54147: ("R1", "A", "Adding //go:build ignore to one of two files declaring main kept the duplicate-main diagnostic until restart; the linked commit only adds a test, the fix was CL 417576.", "typing: add //go:build ignore to bar.go; compare diagnostics with fresh"),
    54180: ("R1", "C", "With experimentalUseInvalidMetadata set, packages diagnosed with invalid metadata were not re-diagnosed when new metadata arrived; the setting was later removed.", "config: enable experimentalUseInvalidMetadata; break then fix go.mod module path"),
    55070: ("R1", "C", "Regtest flake traced to caching file handles whose mtime was too recent, so a same-size rewrite within mtime granularity kept stale file content.", "file-op: two same-size disk writes within mtime granularity; compare with fresh"),
    55995: ("R1", "B", "After go mod vendor (or deleting vendor/), Definition kept reporting the old module location because vendor/modules.txt changes did not invalidate metadata.", "file-op: run go mod vendor or delete vendor/; compare definition with fresh"),
    56731: ("R1", "B", "After didChangeWorkspaceFolders changed the view layout, suppression of stale diagnostics by per-view snapshot ID blocked publishing of new diagnostics.", "config: add a workspace folder at runtime, open a file there; compare diagnostics"),
    57209: ("R1", "C", "In an ad-hoc package outside a module, repeated reloads of b.go sometimes produce 'undefined name: X' although references to X work; race between file and view loads.", "race: repeatedly type an import in b.go while a.go defines X"),
    57558: ("R1", "C", "Tracking issue: gopls' 'seen files' sets are path dependent, so a configuration change can invalidate known files and cause undefined behaviour; no concrete reproduction.", "config: change configuration after files were seen; compare with fresh"),
    57626: ("R1", "C", "A cancelled workspace reinitialization (for example after a go.work change) was marked complete, so later package loads failed.", "race: go.work change followed quickly by another change"),
    57934: ("R1", "B", "After a major options change such as environment variables, gopls reinitialized views and lost track of open-file overlay content.", "config: edit a file unsaved, then change env via didChangeConfiguration"),
    59587: ("R1", "C", "After edits, diagnostics in the current package were cleared only after diagnosticsDelay rather than immediately (regression from CL 477979, possibly pre-release only).", "race: edit that fixes an error; snapshot before diagnosticsDelay elapses"),
    60465: ("R1", "C", "Toggling vulncheck off in the settings did not clear vulnerability diagnostics until the user typed again.", "config: enable then disable vulncheck diagnostics; needs a local vuln database"),
    61005: ("R1", "C", "Test flake: implementation requests running before a package was type-checked intermittently returned no results; the fix memoizes active packages after every operation.", "query-order: request implementation before diagnostics finish"),
    61325: ("R1", "C", "Telemetry crash in View.Options during didChangeWatchedFiles; the fix moves options into snapshots since config changes not creating snapshots caused long-standing bugs.", "config: change settings, then send didChangeWatchedFiles"),
    61512: ("R1", "C", "Occasional panic in typeCheckBatch.importMap after metadata changes because handles were built and invalidated with different metadata; regression was days old, likely never released.", "dependency-edit: add and remove imports repeatedly; watch for request errors"),
    64762: ("R1", "C", "gopls did not register file watchers for locally replaced module directories, so on-disk changes there were not observed.", "file-op: edit a file under a replace-directive directory on disk"),
    65312: ("R1", "C", "Race in diagnostics: a view created while another diagnosis pass ran had its diagnostics pruned as if it were inactive.", "race: open files of two modules or folders in quick succession"),
    65801: ("R1", "B", "A change in one file could wipe out diagnostics of another open package because packages with open files were not treated as workspace packages.", "typing: edit a file in package A, then check diagnostics of open package B"),
    65830: ("R1", "C", "Jumping to definition into a vendored module created a new view, which could increase memory use and give partial references results.", "open-close: open a vendored file, then compare references with fresh"),
    66384: ("R1", "B", "Creating a missing package did not invalidate the 'missing import' diagnostic in its importer.", "file-op: import a missing package, create it on disk, compare diagnostics"),
    # R3 route equivalence
    47564: ("R3", "B", "References and rename started from a call site in another package missed uses in reverse_test.go, while starting from the definition site found them.", "def-consistency: references from hello.go call site vs stringutil.Reverse definition"),
    51672: ("R3", "B", "References on instantiated generic methods or fields used pointer identity of instantiated objects and returned partial results depending on the queried occurrence.", "def-consistency: references from generic declaration vs instantiated uses"),
    59851: ("R3", "C", "References on a method declared in a test file failed with 'package does not contain fakeAer' when expansion came from a test-only type; pre-release regression.", "highlight-refs: documentHighlight vs references at the test-file method"),
    60435: ("R3", "A", "Document highlight on the package name http also highlighted the net/http/httptest import path because import highlighting matched by substring.", "highlight-refs: highlight http in http.X with net/http and net/http/httptest imported"),
    60622: ("R3", "B", "gopls v0.12.0 found no references to methods of generic types because the cross-package index dropped them, while v0.11.0 found them.", "highlight-refs: highlight vs references at a generic-method call in another package"),
    61618: ("R3", "B", "References to struct fields used in type-parameter composite literals were not found after an origin-equality check was dropped.", "def-consistency: references from field declaration vs composite-literal use"),
    # R4 edit validity (non-refactoring)
    54373: ("R4", "B", "The unused-variable quick fix computed over-large deletion edits in some cases (example only in screenshots); the analyzer stayed off by default.", "quickfix: enable unusedvariable, apply its fix, check for new errors"),
    56291: ("R4", "C", "In vendor mode, auto-import added import paths from the vendor directory; the final fix is a Windows-specific one-line change.", "organize: vendored module; organize imports adds a vendor/ path (Windows only)"),
    57480: ("R4", "A", "Completing a test function name at func Te_(t *testing.T) {} inserted the full snippet and duplicated the signature and body.", "completion: complete at 'func Te|(t *testing.T) {}' in a _test.go file"),
    60062: ("R4", "C", "Unimported completion offered packages of the synthetic golang.org/toolchain modules in the module cache, which are not importable.", "completion: accept unimported completion; check for unresolved import"),
    61208: ("R4", "C", "Unimported completion picked a package path from the module cache that is not in go.mod instead of the one required by go.mod.", "completion: accept unimported completion; check for unresolved import"),
    63592: ("R4", "B", "Organize imports on save added an import of a package named error for error.Error (predeclared interface), which broke the code.", "organize: file using error.Error with a package named error findable"),
    67239: ("R4", "C", "The simplifyrange fix removed '_ =' from 'for _ = range f' over a func, which was illegal under the go1.23 development toolchain.", "quickfix: range-over-func with go1.22 GOEXPERIMENT=rangefunc; apply simplifyrange fix"),
    # R5 semantics-preserving transformations
    57484: ("R5", "B", "A suggested fix from the unreachable analyzer ending exactly at EOF failed conversion ('pos not in range') because the EOF offset check was off by one.", "file-edge: unreachable code ending at EOF without trailing newline vs with one"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "type": (58506, 59005, 59888, 63472, 67787),
    "refactor": (54816, 55271, 59403, 60789, 61614, 61640, 63717),
    "ui": (54983, 59635, 65167, 67823),
    "crash": (
        47231, 48249, 48492, 48763, 49600, 50329, 50425, 50430, 50747, 51577, 51843, 51916,
        52211, 54006, 54199, 54798, 55837, 56270, 56466, 56505, 57621, 57625, 59097, 59848,
        59944, 60592, 60605, 60628, 60821, 60890, 60891, 60909, 60952, 60963, 61543, 61670,
        61678, 61692, 61693, 63701, 63933, 64225, 64227, 64233, 64236, 64320, 64488, 64544,
        65516, 65578, 65960, 66109, 66195, 66204, 66449, 66490, 66636, 66731, 66766, 66911,
        66923, 67142, 67144, 67156, 67294, 67360,
    ),
    "perf": (
        53780, 53992, 54473, 56496, 57222, 57795, 57915, 57987, 59184, 59216, 59318, 60089,
        60621, 61049, 61344, 61352, 61508, 62493, 63742, 64011,
    ),
    "feature": (
        47509, 49555, 49657, 50688, 50786, 51086, 51200, 51477, 51478, 52897, 52966, 53880,
        53882, 54065, 54260, 55331, 55333, 56570, 57026, 57300, 57514, 57853, 58663, 59674,
        60682, 61634, 63375, 64178, 64579, 64763, 64888, 64980, 65515, 65795, 66856, 67230,
    ),
    "display": (48938, 56331, 60545, 60959, 65087),
    "cli": (
        48364, 48941, 49668, 50431, 50862, 51825, 51999, 52784, 53586, 57650, 59458, 60379,
        60776, 60969, 63917,
    ),
    "semantic_edit": (59976,),
    "other": (
        49072, 49774, 50707, 50971, 51549, 53735, 53819, 54214, 54294, 54531, 54845, 55080,
        55267, 57092, 57111, 57459, 57627, 58103, 58748, 58750, 59179, 59479, 59841, 61521,
        61550, 62214, 63363, 64229, 64503, 64533, 64973, 65254, 65271, 65561, 66746, 66748,
        67225, 67433, 67865,
    ),
}
