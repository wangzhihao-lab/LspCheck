"""Screening decisions: pyright, sheets pyright_00-02.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "pyright"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    235: ("R5", "B", "A UTF-8 byte order mark at the start of a file is not skipped by the tokenizer, producing an 'Invalid token' error at 1:1 that the same text without the mark does not produce.", "non-ascii: prepend U+FEFF to a file starting with a docstring (transformation outside T1-T3)"),
    494: ("R1", "B", "After the create-type-stub action writes stubs into a newly created typingsPath folder, the missing-stub diagnostics remain until the window is reloaded.", "file-op: create typings stub files after startup; compare diagnostics with a fresh session (needs numpy)"),
    523: ("R1", "B", "A dataclass/circular-reference false positive ('No parameter named my_ref') is reported on the command line, while in the editor results changed after an edit and its undo.", "edit-undo: edit then undo in the snippet file; compare diagnostics with a fresh open"),
    542: ("R4", "A", "Organize imports rewrites wildcard imports without the '*', producing an invalid import statement.", "organize: run organize imports on a file containing 'from x import *'; check for syntax errors"),
    623: ("R1", "B", "After changing the 'capture' argument of a call to an overloaded function, overload evaluation is reported inconsistently; removing and re-adding code resets it.", "typing: edit the Literal argument of the overloaded call back and forth; compare with fresh open"),
    665: ("R4", "B", "An auto-import completion inserts 'from lib.site-packages import xxx' instead of 'import xxx' for a module found under a lib/site-packages folder.", "completion: accept auto-import completion for a module under lib/site-packages; check for syntax error"),
    696: ("R1", "C", "The diagnostic range on an unresolved identifier pasted as 'a = pd' is one character off, usually on the first analysis only.", "typing: paste 'a = pd' into an empty file (no trailing newline); compare range with a fresh open"),
    789: ("R1", "B", "Switching diagnosticMode from workspace to openFilesOnly does not clear the diagnostics already published for files that are not open.", "config: toggle diagnosticMode workspace->openFilesOnly; compare closed-file diagnostics with a fresh session"),
    853: ("R4", "B", "The Create Type Stub quick fix for reportMissingTypeStubs writes the stub under a doubled package path, so the missing-stub diagnostic remains.", "quickfix: create stub for botocore.exceptions (botocore==1.17.23); check the diagnostic clears"),
    881: ("R1", "B", "Opening a typeshed stub file that produces errors and then closing it leaves its diagnostics published until the server is restarted.", "open-close: open and close a bundled typeshed .pyi with errors; check its diagnostics are cleared"),
    937: ("R1", "B", "Changes to a package installed in editable mode are not picked up; errors in the importing script appear only after restarting the server.", "dependency-edit: change a signature in an editable-installed package; compare importer diagnostics with fresh"),
    1044: ("R2", "C", "Completion resolve matches items by a symbol ID that can be invalidated between the completion request and the resolve call, so resolved items come back without details.", "resolve: request completion, edit or rebind, then resolve old items; compare with a fresh resolve"),
    1151: ("R5", "A", "Typing '.' inside a comment on the first line of a file returns completion suggestions; the fix makes comments return none regardless of line.", "file-edge: completion after '.' in a line-1 comment vs the same comment moved down by blank lines"),
    2211: ("R1", "C", "After the type cache is emptied under memory pressure, '# type: ignore' comments in files processed later are ignored and those lines report errors.", "query-order: force a type-cache reset mid-session (large workspace); compare with a fresh session"),
    2526: ("R3", "C", "reveal_type output and hover text disagree for the same expression (tracking bug, details in the linked downstream report); hover vs reveal_type is outside the four designed route checks.", "other-route: compare hover type text with the reveal_type diagnostic at the same expression"),
    2631: ("R1", "B", "The editor reports errors the command line does not; editing a comparison makes them disappear and they reappear after restart, with apparent non-determinism.", "edit-undo: open snippet, edit the elif comparison and revert; compare diagnostics with a fresh open"),
    2759: ("R1", "A", "Hovering 'initial' right after modifying the file makes the lambda types evaluate as Unknown, producing strict-mode errors that do not appear without the hover.", "query-order: edit file (add a space), hover 'initial' before diagnostics; compare with fresh open"),
    2983: ("R1", "A", "Hovering 'e' in the return statement while modifying the file makes the inferred return type Literal[0] instead of 'Unknown | Literal[0]'.", "query-order: edit, then hover the return-statement 'e' first; compare hover and return type with fresh open"),
    3397: ("R1", "C", "A spurious reportInvalidTypeVarUse on an overloaded method occasionally disappears while editing the method body, which the reporter describes as non-deterministic.", "typing: edit and restore the implementation body; compare diagnostics with a fresh open"),
    3482: ("R1", "B", "A ParamSpec-related error is shown in the editor but never on the command line, and editing the code makes it go away and come back.", "edit-undo: edit and revert the snippet; compare diagnostics with a fresh open and with the CLI"),
    3504: ("R1", "C", "A chained overloaded call picks the wrong overload when its lambda calls a function declared later; revealing the intermediate type or declaring the function earlier gives the right result.", "query-order: hover second_func or reveal the intermediate type before checking; compare with fresh open"),
    3585: ("R1", "B", "Protocol assignment errors depend on statement order: swapping two independent assignments makes pyright report an error it otherwise does not.", "query-order: hover the second assignment before the first; compare diagnostics with fresh open"),
    4248: ("R1", "C", "From 1.1.280, diagnostics and semantic highlighting drift from the document text after ordinary edits in one editor client; bisected to commit 04a1058.", "typing: incremental didChange sequences of that client; seven scripted edit shapes did not reproduce"),
    4513: ("R1", "C", "A spurious 'refers to itself' error appears intermittently in the editor; commenting code out and undoing removes it, editing another module can bring it back.", "edit-undo: comment out and undo the function body, edit another module; compare with fresh open"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "type": (
        126, 173, 186, 202, 224, 266, 271, 299, 317, 330, 350, 352, 353, 364, 433, 444, 477,
        567, 609, 645, 672, 695, 724, 739, 831, 854, 1062,
        1094, 1106, 1246, 1299, 1326, 1356, 1410, 1421, 1518, 1710, 1718, 1761, 1784, 1858,
        1887, 1929, 1939, 1940, 1964, 1968, 1982, 2018, 2021, 2069, 2094, 2183, 2197, 2314,
        2322, 2331, 2333, 2354, 2481, 2492, 2531, 2553, 2578, 2609, 2744, 2792, 2911, 2915,
        2930, 2938, 2942, 2962, 3006,
        3017, 3027, 3109, 3111, 3133, 3137, 3159, 3242, 3250, 3308, 3315, 3344, 3387, 3395,
        3440, 3534, 3540, 3551, 3592, 3665, 3710, 3744, 3779, 3786, 3872, 3890, 4074, 4226,
        4230, 4277, 4391, 4403, 4496, 4636, 4637, 4699,
    ),
    "cli": (
        91, 100, 177, 265, 273, 297, 355, 395, 848, 1006, 1581, 2261, 3039, 3218, 3262, 3293,
        3405, 3500, 3503, 3787, 4002, 4336, 4367, 4764,
    ),
    "display": (188, 496, 1078, 1082, 1146, 4479, 4718),
    "refactor": (221,),
    "feature": (294,),
    "crash": (409, 1139),
    "ui": (421,),
    "other": (606, 633, 919, 1159, 2051, 4416),
    "perf": (1642, 3014, 3206, 4484),
}
