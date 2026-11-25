"""Screening decisions: pyright, sheets pyright_03-05.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "pyright"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    4844: ("R1", "B", "Identical calls f(0) against a Self-returning protocol are rejected before f(int(0)) is evaluated and accepted after it, pointing to a cached protocol match that depends on evaluation order.", "query-order: open with f(int(0)) only, insert f(0) above it, compare diagnostics with fresh open"),
    4994: ("R1", "C", "After switching buffers between a root file and a sub-project file, the server reports stdlib modules such as os as unresolved; the earlier headless spike (0/20 runs) did not reproduce it.", "open-close: open root and projects/example.py, alternate close/open, add sub-folder; compare import diagnostics"),
    5179: ("R1", "C", "In workspace diagnosticMode, reportUnnecessaryTypeIgnoreComment diagnostics are published before the checker has run on the file and rescinded later, so a mid-analysis snapshot differs from the settled one.", "race: workspace mode with the rule on; snapshot pushed diagnostics early and late; compare with fresh"),
    5202: ("R1", "C", "After the type cache is emptied under heap pressure, unnecessary type-ignore diagnostics stop being reported for files analysed before the purge (1378 reported with a large heap, 1 without).", "query-order: low heap limit and many open files, then compare type-ignore diagnostics with a fresh session"),
    5554: ("R1", "C", "Members inherited through conditional base classes resolve as Unknown in the steam.py project; the fix hardens circular-dependency handling in class evaluation and the reporter could not reduce it.", "query-order: open steam/friend.py before or after its base modules; compare diagnostics; needs steam.py checkout"),
    6146: ("R1", "B", "After a rename edits a module inside a symlinked directory, the importer keeps reporting the new member as unknown until the window is reloaded; the same layout without the symlink works.", "dependency-edit: rename method in symlinked module (didChange or on-disk write); compare importer diagnostics with fresh"),
    6629: ("R1", "B", "With a forward-reference union alias, ~v is flagged; in the editor, changing the __invert__ annotation clears the error only sometimes while the CLI on the same text still reports it.", "typing: edit the __invert__ annotation, settle; compare the ~v diagnostic with a fresh session on same text"),
    6679: ("R1", "C", "An argument-type error on Dagster appears on some runs and not on others; the fix concerns return type inference being disabled when analyzeUnannotatedFunctions is false.", "query-order: vary file open order and toggle analyzeUnannotatedFunctions; compare diagnostics; needs Dagster checkout"),
    7466: ("R3", "C", "In a loop with codependent variables, reveal_type reports int while hover on the same variable shows Never; hover vs reveal_type is outside the four designed route checks.", "other-route: compare hover type with reveal_type diagnostic at same node; also try hover-before-check order"),
    7516: ("R1", "B", "A dataclass field whose default references an earlier annotated field gets a false positive circular-dependency error that the fix commit describes as intermittent.", "query-order: hover dir_a/dir_b before diagnostics vs fresh open; repeat to catch the intermittent error"),
    8133: ("R5", "B", "An attrs field with default and validator gets a false positive that disappears when the validator argument is wrapped in redundant parentheses; one fix removes parenthesis-dependent diagnostics.", "whitespace: outside T1-T3, wrap an argument in redundant parentheses; needs attrs installed"),
    8946: ("R1", "A", "Deleting the multiprocessing Pool import and undoing it leaves Pool unresolved, so diagnostics and definition differ from a fresh open of identical text; reproduced on 1.1.380 in the spike.", "edit-undo: delete import line, settle past collection, undo; compare diagnostics and definition with fresh"),
    9015: ("R1", "C", "On main after 1.1.380 a cached cancellation source stays cancelled, so the server stops publishing diagnostics after a cancellation; fixed before 1.1.381, so no npm release may carry it.", "race: edit during analysis to trigger cancellation, check diagnostics keep updating; needs a source build"),
    9204: ("R1", "B", "A small asyncio snippet gets a false positive that Coroutine[Any, Any, None] is not awaitable; the fix commit calls the error non-deterministic.", "query-order: hover or complete on test() before diagnostics vs fresh open; repeat runs"),
    9205: ("R1", "B", "A pydantic field default is flagged in the CLI only when model_config precedes it, while the language server flags it in both orders, so server and CLI disagree on identical text.", "query-order: open and hover model fields in different orders; compare diagnostics with fresh; needs pydantic"),
    9642: ("R1", "C", "Checking a 6K-file workspace at once misses errors reported when files are checked individually; the fix removes a type evaluation order dependency in recursive return type inference.", "query-order: open and check files in different orders; compare per-file diagnostics; no public reproduction"),
    9681: ("R5", "A", "A multi-line triple-quoted string assigned to a Literal type is accepted with LF line endings but flagged with CRLF line endings, although the runtime value is the same.", "crlf: outside T1-T3, convert the file from LF to CRLF; compare diagnostics"),
    9702: ("R1", "C", "The CLI reports 'No parameter named' errors on a universal-pathlib UPath call while the language server reports none on the same text; no mechanism is stated in the report.", "query-order: compare server diagnostics under different query orders with CLI output; needs universal-pathlib 0.1.4"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "type": (
        4966, 5032, 5036, 5050, 5147, 5153, 5256, 5384, 5404, 5428, 5429, 5454, 5492, 5495,
        5611, 5628, 5636, 5737, 5755, 5768, 5798, 5887, 5907, 5932, 5947, 5966, 5968, 6064,
        6077, 6213, 6226, 6456, 6458, 6461, 6527, 6654,
        6958, 7151, 7160, 7260, 7537, 7538, 7550, 7741, 7764, 7937, 7988, 8001, 8090, 8184,
        8229, 8285, 8316, 8343, 8350, 8388, 8417, 8436, 8521, 8575, 8641, 8658, 8842, 8898,
        9036, 9053, 9054, 9059, 9253,
        9418, 9610, 9630, 9789, 9901, 9916, 10011, 10068, 10120, 10222, 10318, 10388, 10443,
        10490, 10543, 10549, 10814, 10906, 10988, 11081, 11470, 11472,
    ),
    "crash": (4798, 5140, 5355, 5622, 6116, 6737, 8191, 8228, 8509, 8694, 8823, 9283),
    "cli": (
        4999, 5582, 5612, 6673, 6722, 6742, 6758, 7365, 7439, 8102, 8775, 9412, 9446, 9583,
        10350,
    ),
    "perf": (5594, 6280, 6890, 8275, 8276, 10000),
    "display": (4972, 7405, 9289),
    "feature": (8947, 9747),
    "ui": (9146,),
    "other": (7016, 8719),
}
