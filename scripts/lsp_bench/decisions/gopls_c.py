"""Screening decisions: gopls, sheets gopls_08-10.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "gopls"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    67923: ("R1", "C", "Organize-imports code actions hang after a cancelled external import search; a starvation bug leaves later requests waiting and, once triggered, it recurs.", "race: cancel an in-flight source.organizeImports request, then request it again; no response"),
    68918: ("R3", "B", "documentHighlight panics on a nested composite literal without type information when the file has a type error; the fix adds a marker regression test.", "highlight-refs: highlight vs references on nested untyped composite literal in ill-typed file"),
    71111: ("R4", "A", "The minmax modernizer fix rewrites an if statement with an init clause into 'delay := max(adaptive, delay)', leaving undefined identifiers.", "quickfix: apply minmax fix to 'if adaptive := x; adaptive > delay { delay = adaptive }'"),
    71405: ("R2", "B", "codeAction/resolve on two code actions wrongly registered with resolve-edit support executed their commands, applying edits as a side effect instead of returning them.", "resolve: resolve those actions (before/after an edit); record workspace/applyEdit sent during resolve"),
    71967: ("R1", "B", "After initialize with rootUri but no workspaceFolders, didChangeWorkspaceFolders adding the same folder re-adds it and the loading-packages progress never ends.", "config: initialize rootUri only, then didChangeWorkspaceFolders same folder; progress never completes"),
    72726: ("R4", "A", "The rangeint modernizer offered fixes when the limit depends on the loop variable or is an untyped float constant, producing non-compiling code.", "quickfix: apply rangeint fix to 'for j := 0; j < min(n-j, kd+1); j++ {}'"),
    72753: ("R4", "A", "Completion at 'left,ri' returns a zero-length textEdit range, so accepting 'right' yields 'left,riright'.", "completion: accept 'right' at 'left,ri' in func f(left, right string)"),
    73269: ("R4", "A", "The modernizer rewrites a loop over a variadic predicate into slices.ContainsFunc, which does not type-check.", "quickfix: loop calling isEven(num int, opt ...any); apply ContainsFunc fix"),
    73661: ("R4", "A", "The appendclipped modernizer rewrites append([]string{}, a...) to slices.Clone(a) across distinct named slice types, producing an assignment type error.", "quickfix: var b ssb = append([]string{}, a...) with a of type ssa; apply fix"),
    73735: ("R5", "A", "With lineFoldingOnly, no folding range is returned for a function whose opening brace is followed by a trailing comment on the same line.", "comment: add same-line trailing comment after 'func f() {' (outside T1-T3); compare foldingRange"),
    74057: ("R1", "C", "Telemetry crash: DidCreateFiles panicked when the created file was not empty, because completion.NewFile returned nil without an error (condition stated in the fix).", "file-op: send workspace/didCreateFiles for an existing non-empty .go file; later requests fail"),
    74635: ("R5", "B", "Semantic tokens for a Go template file containing a multi-line comment panic with index out of range in line bookkeeping; the fix switches to protocol.Mapper.", "comment: gotmpl file (templateExtensions) with multi-line {{/* */}} comment; semanticTokens/full"),
    74687: ("R4", "B", "The rangeint modernizer qualifies a limit type declared in another package with its full package path, producing invalid syntax.", "quickfix: loop limit of named type from another package; apply rangeint fix, check parse"),
    74709: ("R4", "A", "The fmtappendf modernizer turns a []byte(fmt.Sprintf(...),) conversion with a trailing comma into code that does not compile.", "quickfix: apply fix to multi-line []byte(fmt.Sprintf(\"%d\", 0),) in a composite literal"),
    75000: ("R4", "B", "Without go.mod gopls assumed the latest Go version and offered the WaitGroup.Go modernization, whose fix broke the build on the installed Go 1.24.", "quickfix: ad hoc file, older toolchain; apply waitgroup fix; wg.Go undefined"),
    75283: ("R4", "A", "The stringsbuilder modernizer converts a string that is also directly assigned into a strings.Builder, leaving 'path = components[1]', which no longer type-checks.", "quickfix: apply stringsbuilder fix to var path string with path = x and path += y"),
    75318: ("R4", "A", "The stringsbuilder fix computes a wrong TextEdit end inside a parenthesized var ( ... ) declaration and deletes its closing parenthesis.", "quickfix: apply stringsbuilder fix where msg is declared in var ( broken bool; msg string )"),
    76310: ("R4", "B", "Unimported-package completions and import suggestions used case-escaped module-cache import paths (with '!'), producing invalid imports.", "completion: accept unimported completion from a module path with uppercase letters; check import resolves"),
    77481: ("R4", "A", "Accepting a completion inside syntactically invalid code used a zero-length range, appending the item and deleting following struct fields.", "completion: complete 'colore' to 'colorex' in the reported struct with syntax errors"),
    77675: ("R5", "B", "Hover on a constant expression in a raw string literal with CRLF line endings panics because BasicLit.Value drops carriage returns.", "crlf: convert file to CRLF (outside T1-T3); hover in multi-line raw string constant"),
    80268: ("R4", "A", "Completing 'arr' where a *[10]int argument is expected inserts '(*[10]int)(array)', which is invalid code.", "completion: foo(arr<cursor>) with var array [10]int and func foo(p *[10]int)"),
    80460: ("R4", "A", "The Fill switch code action qualifies generated cases with the declared package name instead of the file's import alias, producing undefined identifiers.", "codeaction-other: fill switch on clock.Month with import clock \"time\"; count new errors"),
    80666: ("R5", "A", "In Go assembly files with CRLF line endings, identifier offsets drift left one byte per preceding line, shifting definition, references, hover and highlight results.", "crlf: convert .s file to CRLF (outside T1-T3); compare definition and references positions"),
    81576: ("R4", "A", "The slicesbackward modernizer rewrites a backward loop with an empty body to 'for _, v := range slices.Backward(s)', which fails with 'declared and not used: v'.", "quickfix: apply fix to 'for i := len(s) - 1; i >= 0; i-- { }'"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "type": (68153, 69505, 70598, 81350),
    "refactor": (70268, 70553, 71473, 73187, 77543),
    "ui": (75442, 79760),
    "crash": (
        68169, 68213, 68819, 69616, 69895, 70418, 70446, 70745, 70791, 70909,
        70927, 71028, 71067, 71352, 71354, 71659, 71812, 71982, 72026, 72907,
        74055, 74056, 74304, 74351, 74564, 74652, 79450, 79803,
    ),
    "perf": (67889, 72769, 76813),
    "feature": (69692, 69937, 69980, 71286, 71888, 73059, 73959, 74595, 74849, 75422, 75810, 76374, 79801),
    "display": (68116, 70905, 72993, 78274, 79023, 79531, 81369),
    "cli": (74904, 75489),
    "semantic_edit": (71725, 72955, 73557, 76210, 76470),
    "other": (
        69624, 70187, 70196, 70342, 70363, 70929, 71045, 71956, 72082, 73268,
        73982, 74072, 74165, 74373, 74580, 74668, 74805, 74820, 75199, 75588,
        75925, 76547, 76869, 76873, 77552, 77756, 78316, 78680, 78835, 79818,
        81281,
    ),
}
