"""Screening decisions: tsserver, sheets tsserver_00-03.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "tsserver"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    # R1 history independence
    29393: ("R1", "C", "Whether a constraint error is reported on an unrelated class line depends on another statement being present; the fix removes diagnostic-dependent output from the cached relation check.", "query-order: hover/complete on MyInfo before diagnostics vs fresh diagnostics (needs io-ts)"),
    45030: ("R1", "C", "Auto-import completions work once after opening the project and then fail with a debug failure in rehydrateCachedInfo on later requests.", "query-order: repeat completion requests after edits; compare with a fresh session"),
    45101: ("R1", "C", "Auto-import fails when a re-export alias merges with an augmentation; the fix stores the symbol-table key in the cached export info used by later requests.", "query-order: request auto-import completions twice; second one rehydrates cached export info"),
    45320: ("R1", "B", "After quick typing, inlay hints and semantic highlighting are shifted because provideInlayHints did not apply pending document updates before answering.", "typing: didChange then immediately inlayHint; compare with fresh session"),
    46024: ("R1", "C", "In the devtools-frontend codebase auto-import completions work once and then fail with a debug failure on later typing.", "query-order: repeated completions while typing; compare with fresh session"),
    46564: ("R1", "B", "After auto-importing from a relative path, undoing, and switching the specifier to the linked package name, the next auto-import completion fails with a debug assertion.", "edit-undo: accept auto-import, undo, edit import path, complete again (file: dependency)"),
    47779: ("R1", "C", "IDisposable stopped appearing in auto-import completions in the VS Code codebase; the fix is titled 'auto-import completions sometimes not updating existing imports'.", "typing: edit existing imports then request completions; compare with fresh session"),
    52316: ("R1", "C", "Find-all-references fails with 'Could not find source file' because projects were not updated before the search; found by the crawler on remotion.", "open-close: open or add a file then request references immediately"),
    52792: ("R1", "A", "Requesting completions, opening the imported utils.ts, then erasing one character makes the next completion request fail.", "open-close: complete, open utils.ts, delete one char, complete again"),
    # R3 route equivalence
    33017: ("R3", "C", "Find-all-references for type Foo re-exported through a namespace import returns nothing while go-to-definition resolves it; the reporter saw it only in a large project.", "highlight-refs: documentHighlight vs references on types.Foo in main.ts (3-file layout)"),
    35883: ("R3", "C", "Find-all-references on a #private field returns no results although the field declaration and its uses exist; highlights may share the failing path.", "other-route: definition of this.#foo vs references at its declaration"),
    37830: ("R3", "A", "Find-all-references on instance method foo also returns a same-named static method of a subclass, grouping two different declarations.", "def-consistency: definition at each returned reference should give one target"),
    39895: ("R3", "C", "Go-to-definition on a call of a destructured require binding returns both the require line and the function definition.", "def-consistency: definition from the binding vs from the call site in JS"),
    # R4 edit validity
    29908: ("R4", "A", "The declare-static-method fix on Foo.bard() inserts 'static bard(): any;' into interface Foo, which is invalid in an interface.", "quickfix: apply declare-static-method fix on Foo.bard(); count errors"),
    31219: ("R4", "A", "With module esnext the add-import fix for an export= module inserts 'import foo = require(...)', raising 'Import assignment cannot be used when targeting ECMAScript modules'.", "quickfix: tsconfig module esnext, d.ts with export=; apply import fix; count errors"),
    31304: ("R4", "A", "Accepting a string-literal completion after typing 'one/two' inserts the whole option instead of replacing the typed prefix, giving a literal outside the union.", "completion: accept literal completion inside 'one/two'; check new type error"),
    32068: ("R4", "A", "Format Document turns '<number>foo < <number>bar' into '<number>foo <<number>bar', which no longer compiles.", "format: format twice; check errors and idempotence on the cast comparison"),
    32843: ("R4", "C", "The unused-type-parameter check reports all JSDoc @template parameters unused although V is used, so its remove fix targets a used type parameter.", "quickfix: JS with checkJs; apply remove-template fix; count errors"),
    33021: ("R4", "B", "The prefix-with-underscore fix for an unused parameter leaves the JSDoc @param naming the old parameter.", "quickfix: JS with checkJs; apply prefix fix; check @param-name mismatch error"),
    33511: ("R4", "B", "On the opening <Text> tag the quick fix offers importing default React instead of Text; the fix limits that offer to when React is not already in scope.", "quickfix: react-native types, React imported; apply fix at <Text>; Text error remains"),
    35954: ("R4", "A", "The change-spelling fix for this.foobar with a #foobar field rewrites it to a string element access this['#foobar'], which still does not type-check.", "quickfix: apply spelling fix; diagnostic remains or new error"),
    36002: ("R4", "B", "Auto-importing createSourceFile adds it to an existing 'import type' declaration, so the value is imported type-only and errors.", "completion: accept auto-import next to an import type; count errors"),
    36102: ("R4", "A", "Organize Imports inserts another newline after a trailing 'export { ... };' on each run, so repeated runs keep changing the file.", "organize: run organize imports twice; second run must be a no-op"),
    38507: ("R4", "A", "Organize imports replicates the last comment line of the import block under the imports on each run.", "organize: run organize imports twice with comments between imports"),
    39515: ("R4", "B", "In CRLF files 'Add all missing imports' inserts text before the line break at wrong positions, producing broken import statements.", "quickfix: CRLF file with several missing imports; apply fix-all; count errors"),
    40257: ("R4", "A", "The remove-all-type-parameters fix on a multi-line type parameter list leaves the closing '>' behind, producing 'CCResponsePredicate> ='.", "quickfix: apply remove-unused-type-parameters fix; check syntax error"),
    40756: ("R4", "B", "The infer-parameter-types-from-usage fix truncates deeply nested inferred types with an ellipsis, inserting a syntax error.", "quickfix: implicit-any parameter used with nested object; apply infer fix"),
    41088: ("R4", "B", "Accepting a path completion after typing part of a nested paths alias duplicates the typed part of the module path.", "completion: tsconfig paths alias; accept mid-path completion; check unresolved module"),
    41194: ("R4", "A", "Sort/organize imports removes the frag import named by a @jsxFrag pragma although the fragment uses it.", "organize: run organize imports on the tsx snippet; count errors"),
    41526: ("R4", "A", "Infer-parameter-types on an arrow callback parameter in a checked JS file inserts the @param JSDoc before the return statement, so the parameter stays untyped.", "quickfix: apply infer-from-usage on name; its implicit-any suggestion should disappear"),
    41786: ("R4", "A", "With noPropertyAccessFromIndexSignature the use-element-access fix rewrites x.y instead of .yadda, leaving the error on yadda.", "quickfix: apply fix at x.y.yadda; diagnostic on yadda remains"),
    41920: ("R4", "B", "With jsx react-jsxdev, 'Add all missing imports' first inserts an unneeded React import and leaves 'Cannot find name Foo' until applied again.", "quickfix: jsx react-jsxdev; apply fix-all once; Foo error remains"),
    41963: ("R4", "A", "Accepting the Form.Item completion in a closing tag '</Form.' replaces only the text after the dot, producing '</Form.Form.Item>'.", "completion: accept closing-tag completion; check JSX closing-tag syntax error"),
    43278: ("R4", "A", "The convert-to-ES-module suggestion fix on require('node-fetch') with a .default access generates 'import { default } from ...; default()', which is invalid.", "quickfix: apply convert-to-ES-module suggestion fix; check syntax errors"),
    43495: ("R4", "A", "The noImplicitOverride fix inserts 'override' before 'public', raising 'public modifier must precede override modifier'.", "quickfix: noImplicitOverride; apply add-override fix; count errors"),
    44123: ("R4", "A", "Convert-to-async is suggested for a promise .then with a generator callback; applying it yields code that no longer compiles.", "quickfix: apply convert-to-async suggestion fix; count errors"),
    44363: ("R4", "A", "Completions are offered right after the bigint literal 0n, so accepting one on Enter corrupts the literal.", "completion: complete right after 0n; accept top item; check syntax error"),
    44830: ("R4", "B", "Import statement completions in a JS file insert TypeScript-only import-equals syntax for export= modules.", "completion: JS file, export= module; accept import-statement completion; count errors"),
    45270: ("R4", "B", "The add-override fix on an abstract method inserts 'override' before 'abstract', raising 'abstract modifier must precede override modifier'.", "quickfix: noImplicitOverride with abstract member; apply fix; count errors"),
    46466: ("R4", "A", "The add-async fix for await inside a generic arrow function inserts 'async' after the type parameters, producing '<T>async (x: T)'.", "quickfix: apply add-async fix on generic arrow; check syntax error"),
    47746: ("R4", "A", "The add-missing-properties fix for Foo<string> generates a method returning T, which is not in scope.", "quickfix: apply add-missing-properties; check 'Cannot find name T'"),
    48006: ("R4", "B", "Format on paste of a word pasted into a string removes the pasted text.", "format: insert text into a string, range-format that span; non-whitespace deleted"),
    49001: ("R4", "A", "The add-missing-properties fix generates a method returning SomeType without importing it, causing 'Cannot find name SomeType'.", "quickfix: two files; apply add-missing-properties; count errors"),
    49693: ("R4", "B", "The add-missing-function-declaration fix omits type parameters, so the generated function refers to an undeclared type parameter.", "quickfix: call with generic-typed argument; apply fix; count errors"),
    49964: ("R4", "A", "The add-extends-constraint fix for a type parameter used twice produces 'T extends {} extends {}'.", "quickfix: strict; apply extends-constraint fix; check syntax error"),
    49965: ("R4", "A", "The add-extends-constraint fix inserts 'T extends MyType' without importing MyType from ./bar.", "quickfix: two files; apply fix; check 'Cannot find name MyType'"),
    50076: ("R4", "A", "Range formatting that ends mid-token (format on paste after a template expression) deletes text including the closing brace.", "format: paste after '}' in template string, range-format; non-whitespace deleted"),
    50188: ("R4", "A", "Declare-missing-function is offered for an unresolved argument in f(asdfasdfa); applying it passes a function where number is expected.", "quickfix: apply declare-function fix on the argument; count errors"),
    50243: ("R4", "C", "'Fix all detected spelling errors' does nothing for an uncorrected spelling error; the fix makes diagnostic deduplication ignore related information.", "quickfix: apply fix-all spelling; spelling diagnostics remain"),
    51170: ("R4", "B", "Accepting a completion for an unimplemented class property replaces the rest of the line, including content to the right of the cursor.", "completion: class member completion with text after cursor; check eaten text"),
    51667: ("R4", "A", "In a JSX element, completions on the line after a string-literal attribute offer literal values; accepting one inserts a bare string, which is invalid JSX.", "completion: accept literal completion on the attribute line; check syntax error"),
    51920: ("R4", "A", "Add-missing-properties in a checked JS file generates TypeScript type annotations, which are errors in JavaScript files.", "quickfix: JS with @ts-check; apply fix; count errors"),
    52263: ("R4", "B", "The add-import fix inserts the import above a '/// <reference lib=...>' directive after a header comment, so the directive no longer applies.", "quickfix: use an es2017 string method; apply import fix; count errors"),
    52274: ("R4", "A", "'Delete unused @param tag' inserts another JSDoc comment instead of deleting the tag, so the mismatched-@param diagnostic persists.", "quickfix: apply delete-param-tag fix; suggestion diagnostic should disappear"),
    52288: ("R4", "B", "Inside a JSX expression, completing a partial identifier inserts attribute snippet text '={}', producing invalid JSX.", "completion: tsx, partial identifier inside {...}; accept item; check syntax error"),
    52543: ("R4", "B", "Import-statement snippet completions do not escape '$' in module specifiers, so '$another' is lost when the snippet is inserted.", "completion: snippets on, file $another.ts; accept import completion; unresolved module"),
    52675: ("R4", "A", "Completions requested right after a closing quote suggest string literals; accepting one appends a second literal after the string.", "completion: accept completion after the closing quote; check syntax error"),
    53008: ("R4", "B", "Auto-import for useEffect adds it to the first import from react, an 'import type' declaration, so the value import is type-only.", "quickfix: react types; apply import fix for useEffect; count errors"),
    53290: ("R4", "B", "Import-statement completion for a paths alias starting with '$' inserts the module path without the '$lib/' prefix.", "completion: tsconfig paths '$lib/*'; accept import completion; unresolved module"),
    54818: ("R4", "A", "In JS files, completions at 'import Foo fro' list identifiers containing 'from' such as fromBar; accepting one breaks the import statement.", "completion: JS file; complete at 'fro'; accept top item; check syntax error"),
    57497: ("R4", "A", "With noUnusedLocals, remove-unused-declaration on an overloaded function removes only one overload, leaving the unused diagnostic.", "quickfix: apply remove-unused fix; diagnostic should disappear without new errors"),
    59116: ("R4", "A", "Add-missing-function-declaration for X.foobar() on an imported namespace inserts the function in the wrong file, so the error remains.", "quickfix: two files; apply fix; property error on X.foobar remains"),
    59304: ("R4", "A", "Converting require(`@swc/core`) to an import keeps the template literal, producing an import with backticks, which is a syntax error.", "quickfix: apply require-to-import suggestion fix; check syntax error"),
    60186: ("R4", "A", "Add-missing-properties with an enum from another module generates a member initializer like 'file:///E'.A, which does not type-check.", "quickfix: two files; apply add-missing-properties; count errors"),
    # R5 semantics-preserving transformations
    35632: ("R5", "B", "Completions crash in tryGetClassLikeCompletionSymbols when the preceding token is a JSDoc comment without tags; the fix finds tagless JSDoc as the preceding token.", "comment: insert a tagless /** */ comment in a class body before the completion point"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "crash": (
        29330, 29358, 29565, 34982, 35094, 35944, 39923, 40991, 41925, 42718, 43107,
        46332, 46615, 47398, 47415, 47417, 47428, 47787, 47788, 48008, 48963, 49058,
        49217, 49629, 50048, 50392, 50867, 51221, 51963, 52137, 52661, 52662, 54366,
        55946, 58044, 58740, 59115, 63598,
    ),
    "refactor": (
        31195, 33518, 37817, 38017, 38177, 38461, 40671, 42829, 43442, 45659, 45687,
        48109, 48281, 49784, 49838, 50427, 52418, 53482, 54285, 54463, 55404, 58806,
    ),
    "semantic_edit": (
        29406, 30044, 33377, 34620, 35069, 37781, 38082, 39458, 39922, 40223, 41244,
        41787, 41827, 41868, 43006, 44059, 44511, 45109, 45225, 46609, 46803, 46833,
        47733, 48191, 50888, 51615, 54023, 54068, 54324, 55863, 56756,
    ),
    "whitespace_only": (
        30675, 31237, 32923, 35179, 35474, 37431, 39047, 40854, 44637, 44694, 45501,
        45526, 51686, 52050, 52177, 54243, 55694, 56699, 60887,
    ),
    "display": (
        35187, 35511, 36933, 40817, 41761, 42094, 45607, 46696, 47009, 47081, 47451,
        48904, 50435, 54013, 55937, 57368, 57740, 62609,
    ),
    "feature": (
        32848, 34895, 34996, 36101, 36116, 39440, 41861, 42923, 45591, 46402, 48673,
        50644, 54383, 55998, 59842,
    ),
    "type": (43316, 46240, 47949),
    "perf": (44826,),
    "other": (35014, 39453, 40136, 56706, 59779),
}
