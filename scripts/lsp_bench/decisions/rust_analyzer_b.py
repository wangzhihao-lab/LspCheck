"""Screening decisions: rust-analyzer, sheets rust-analyzer_05-08.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "rust-analyzer"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    # R1 history independence
    17592: ("R1", "B", "documentHighlight on a macro_rules name defined by a proc macro panics, but not when the cursor first moves from the defining call; the fix makes Semantics cache file roots consistently.", "query-order: documentHighlight on the second macro_name with and without a prior request on the first; proc-macro crate"),
    18194: ("R1", "B", "Diagnostics visible on first open disappear from all files of an affected crate after saving any file in the project (flycheck regression from commit 03456c5).", "open-close: open, save another file of the crate, compare diagnostics with a fresh open; needs cargo check"),
    18811: ("R1", "C", "Errors stay after a later check build succeeds when a second save starts while the first flycheck runs; the fix handles cancellations leaving stale errors.", "race: save a fix, save again during the running check, compare with fresh; needs cargo check"),
    18936: ("R1", "C", "documentHighlight panics with 'Failed to lookup ... in this Semantics' on a proc-macro repro; the fix is shared with #17592, whose report shows dependence on the previous cursor position.", "query-order: vary the preceding documentHighlight request on the proc-macro repro file"),
    19003: ("R1", "A", "A closure passed as Arc<Mutex<dyn FnMut>> is accepted after a fresh start, but after any edit (even adding a space) the server reports E0308.", "edit-undo: insert and delete a space, compare diagnostics with a fresh open"),
    19489: ("R1", "C", "With workspace.discoverConfig, opening a second discovered workspace makes 'proc-macro-srv is not running' errors appear in all workspaces, though the first expanded fine.", "open-close: open files of two discovered workspaces in sequence; needs a discovery command and proc macros"),
    19854: ("R1", "C", "Flycheck diagnostics of a crate may never be cleared when cargo reports no artifact for it; the fix makes flycheck diagnostics generational.", "open-close: fix an error in such a crate and save, compare with a fresh session; needs cargo"),
    20427: ("R1", "B", "In v0.3.2571 error diagnostics appear briefly and then vanish after saving a file; they persist only on first open (flycheck generation bug).", "open-close: introduce an error, save, compare diagnostics with a fresh open; needs cargo check"),
    20651: ("R1", "B", "Saving a file of a binary target runs cargo check for that target only and drops earlier errors of other targets, so remaining errors disappear.", "open-close: errors in lib and bin, save a bin file, compare with fresh; needs cargo check"),
    20763: ("R1", "C", "trait-impl-incorrect-safety fires for an unsafe impl of an unresolved trait; the reporter's reliable trigger is uncommenting then re-commenting the trait definition.", "edit-undo: uncomment and re-comment the trait, compare with a fresh open of the same text"),
    21173: ("R1", "A", "Any edit, including a whitespace change, to the given const-generic impl makes request handlers panic with 'cannot find !BoundConst'; bisected to #20974.", "edit-undo: insert and delete a space, compare responses with a fresh open"),
    21610: ("R1", "C", "Requests intermittently panic with 'Propagating panic for cycle head that panicked in an earlier execution'; fixed by reverting fine-grained client-side request cancellation.", "race: cancel in-flight requests during edits, then query, compare with fresh"),
    21617: ("R1", "C", "Lint results stop updating on save and CPU stays high in 0.3.2786; fixed by the same cancellation revert as #21610.", "race: edit and save repeatedly with clippy flycheck, compare diagnostics with fresh; needs cargo"),
    # R2 handle validity
    18547: ("R2", "B", "After helix previewed a completion item, completionItem/resolve replaced it with an unrelated item (Either); the fix hashes items so resolve matches the original.", "resolve: complete, apply the item edit, resolve the old item, compare with the original item"),
    18640: ("R2", "C", "completionItem/resolve failed at random with 'Import edit overlaps with the original completion edits'; fixed by the completion-hashing change of #18547.", "resolve: resolve auto-import items after further typing, check edits against the current text"),
    # R3 route equivalence
    18513: ("R3", "B", "Typing an unterminated string inside log::error! makes textDocument/diagnostic panic with 'invalid offset'; the fix corrects related-document diagnostics of the pull handler.", "pull-push: same file under pull and push diagnostics; needs the log crate"),
    # R4 edit validity
    17728: ("R4", "A", "The missing-return-value quick fix for 'fn foo() -> Result<()> {}' produces 'fn foo() -> Result<()> Ok({})', which does not parse.", "quickfix: apply the fix on the empty body, check parse errors"),
    18027: ("R4", "B", "'Fill match arms' inside a #[tokio::main] function inserts an extra closing brace, leaving unbalanced braces.", "quickfix: apply fill match arms under #[tokio::main]; needs tokio"),
    18129: ("R4", "A", "'Remove all the unused imports' removes a used 'use std::io::Error as IoError;', breaking the signature that uses IoError.", "quickfix: request code actions on the aliased import line, apply, check new errors"),
    18298: ("R4", "A", "The wrap-in-Ok fix turns 'return;' in a Result-returning function into 'Ok(return);', which is still an error.", "quickfix: apply the fix on return;, the diagnostic must not remain"),
    18314: ("R4", "B", "In a file include!d inside mod bar, Foo is reported unresolved and the offered 'Qualify as bar::Foo' fix produces code that fails to resolve.", "quickfix: two files with include!, apply the qualify fix, check errors"),
    18572: ("R4", "A", "Accepting the '&mut mod_info' ref completion after typing 'mod' yields 'mod&mmod_info'; the fix corrects the ref-match position for keyword prefixes.", "completion: type mod inside read_to_string(), apply the &mut item, check syntax"),
    18941: ("R4", "A", "'Remove all unused imports' removes the used 'str' from 'use std::{io::Write, str}', breaking str::from_utf8.", "quickfix: apply remove-unused-imports on the use tree, check new errors"),
    19069: ("R4", "A", "Postfix snippets such as .box or .unsafe inside assert!, debug_assert! or format! strip whitespace from the macro input and can insert broken code.", "completion: apply a postfix item inside assert!(...), check syntax errors"),
    19119: ("R4", "B", "'Remove all unused imports' removes imports that are used only by derive macros, breaking the derives.", "quickfix: import a derive macro, derive with it, apply remove-unused-imports"),
    19758: ("R4", "A", "The dbg! postfix snippet on '*x' yields '*dbg!(*x)', dereferencing twice and producing a type error.", "completion: type .dbg after *x and apply, check new errors"),
    20588: ("R4", "A", "The 'Add unsafe block' fix wraps a call followed by 'as *mut u8' without parentheses, producing a syntax error.", "quickfix: apply the missing_unsafe fix on the cast expression, check errors"),
    20987: ("R4", "A", "Completing a unit-returning function inside a call argument inserts 'called_function();' with a semicolon, a syntax error.", "completion: complete ca inside higher_order_function(...), check syntax errors"),
    21016: ("R4", "A", "The increase-visibility fix for private fields inserts 'pub(crate)' before a field's doc comment, producing invalid code.", "quickfix: fields with /// comments accessed outside the module, apply the fix"),
    21204: ("R4", "A", "The add-field fix for no_such_field on an enum variant declared in another file adds 'pub(crate)' to the variant field, which is invalid.", "quickfix: enum in foo.rs, literal with extra field in lib.rs, apply the fix"),
    21288: ("R4", "B", "Generate function for 'bar(&|x| true)' emits 'fn bar(arg: impl Fn(;))', a syntax error; a generate assist, not a diagnostic fix.", "codeaction-other: apply generate function on the unresolved call, check syntax errors"),
    21365: ("R4", "A", "Without InsertReplaceEdit support, completing at 'where$0sheep' also replaces the trailing 'sheep', eating text after the cursor.", "completion: client without insertReplaceSupport, complete mid-identifier, check text"),
    21663: ("R4", "A", "'Implement missing members' for std::alloc::Allocator names a parameter 'std::ptr', which is invalid syntax.", "quickfix: unsafe impl Allocator with empty body, apply, check syntax errors"),
    21873: ("R4", "A", "'Fill struct fields' for a &'static [u8] field emits 'data: &'static', which does not parse, when expressionFillDefault is 'default'.", "quickfix: set assist.expressionFillDefault=default, apply to Foo {}"),
    22281: ("R4", "A", "The qualify-path fix turns 'make::ext::foo' into 'ast::make::foo', dropping a segment and leaving an unresolved path.", "quickfix: apply qualify path on the unresolved path, the diagnostic must clear"),
    22775: ("R4", "B", "'Remove all unused imports' removes a used 'use std::assert_matches;', breaking the macro call.", "quickfix: import and use assert_matches, apply remove-unused-imports; needs Rust 1.96+ sysroot"),
    # R5 semantics-preserving transformations
    18144: ("R5", "A", "A comment placed above the lint name inside #[allow(...)] makes the allow a no-op, so suppressed warnings reappear.", "comment: insert a comment line inside the allow(...) list, compare diagnostics"),
    20240: ("R5", "A", "Since v0.3.2539 the folding range of a doc comment above a function with a multi-line parameter list also covers the signature and body.", "comment: add a /// comment above such a fn; the new fold must cover only the comment"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "type": (
        17852, 17897, 17969, 17978, 18095, 18148, 18201, 18209, 18334, 18345, 18378, 18626,
        18768, 18974, 19048, 19224, 19497, 19668, 19669, 19724, 19813, 19823, 19858, 19957,
        19962, 19965, 20207, 21045, 21386, 21430, 21454, 21478, 21512, 21525, 21621, 21816,
        21934, 22213, 22263, 22353, 22429, 22989, 23052, 23090, 23098, 23132, 23133, 23150,
        23187, 23304,
    ),
    "refactor": (
        17854, 17869, 17964, 17983, 18013, 18679, 18766, 18786, 19254, 19323, 19349, 19426,
        19443, 19547, 19681, 19878, 19886, 19912, 20108, 20162, 20209, 20352, 20716, 20744,
        20965, 21020, 21039, 21063, 21567, 21595, 21686, 21769, 22023, 22071, 22227, 22441,
        22671, 22672, 22691, 22767, 23110,
    ),
    "ui": (17643, 18468, 18767, 18959, 19022, 19165, 19380, 21489, 22817, 22980),
    "crash": (
        17578, 17585, 17710, 17866, 18089, 18109, 18556, 18683, 18780, 18800, 18898, 18918,
        18954, 19177, 19561, 19610, 19715, 19730, 19887, 20127, 20225, 20259, 20398, 20433,
        20501, 20951, 20952, 20975, 21138, 21248, 21638, 21641, 22045, 22102, 22205, 22820,
        22880, 22913, 22920, 23293, 23327, 23338,
    ),
    "perf": (17829, 18736, 19322, 19404, 20436, 20582, 21382),
    "feature": (17796, 19138, 21948),
    "display": (
        18505, 18765, 19027, 19041, 19357, 20034, 20410, 20572, 21615, 21943, 22731, 22893,
        23069,
    ),
    "cli": (
        17664, 17748, 17902, 18141, 18296, 18748, 19272, 19667, 19729, 21150, 21267, 21821,
        22844, 23203,
    ),
    "semantic_edit": (19053, 19784, 20215, 21718, 22443),
    "whitespace_only": (19123,),
    "other": (18424, 18687),
}
