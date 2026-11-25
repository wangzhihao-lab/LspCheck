"""Screening decisions: gopls, second-round sheets gopls_r2_00-01.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "gopls"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    34379: ("R1", "A", "After an import is added in an unsaved buffer of a package that has an in-package test, completions on the new import fail; go/packages added the overlay dependency only to the test variant.", "typing: add import net/http unsaved in simple.go beside simple_test.go; complete http. vs fresh"),
    35458: ("R4", "A", "The organize-imports code action computed its diff from the package clause instead of byte 0, so applying it turned 'package main' into 'package' and broke the file.", "organize: apply the organize-imports edit on a hello-world file; check syntax errors"),
    36824: ("R4", "A", "Organize imports on a single-line file such as 'package x; func hello() { fmt.Print(\"\"); }' drops the function, leaving only the package clause and import; the backfilled commit only skips a regtest.", "organize: organize imports on the single-line file; check deleted code and new errors"),
    38412: ("R4", "A", "Organize imports on save inserted a second package clause into 'package main / func main() {}' because formatting fixes were applied while organizing imports.", "organize: request source.organizeImports on the two-line file; check duplicate package clause"),
    39203: ("R4", "A", "Completion at 'fooBar := fo<>' offers fooBar itself, so accepting it yields 'fooBar := fooBar', an undefined-name type error.", "completion: accept fooBar at 'fooBar := fo<>'; check new undefined-name error"),
    43789: ("R4", "A", "Completing a field name inside '&foo{ Paylo<> }' inserts 'string(Payload: []byte,)', an invalid conversion snippet that does not parse.", "completion: accept Payload inside the struct literal; check syntax errors"),
    44589: ("R4", "A", "With a dot import of bytes, the literal completion for '*Buffer' inserts '&..Buffer{}', which is invalid syntax.", "completion: 'var _ *Buffer = <>' with dot-imported bytes; accept literal item; check syntax"),
    46436: ("R4", "A", "Completion inside an index expression '[]int{}[<>]' offers the conversion 'untyped int()', which is not valid Go when inserted.", "completion: accept the untyped int() item inside the index; check syntax errors"),
    50935: ("R4", "A", "An undeclared-name quick fix is offered for an undefined type constraint in 'func F[T C](m T) T', and applying it fails with a gopls.apply_fix error, leaving the diagnostic.", "quickfix: apply the offered fix for undefined C; command error and diagnostic remains"),
    62141: ("R4", "A", "Accepting a completion in 'x := 1.0 / abcd<>' inserts 'untyped float(abcdef)', which does not parse.", "completion: accept abcdef in the untyped float expression; check syntax errors"),
    71313: ("R4", "B", "The slicescontains modernizer rewrote a loop into slices.Contains although the element and needle types differ, producing 'S (type []ast.Expr) does not satisfy ~[]E'.", "quickfix: loop over []ast.Expr comparing a concrete needle; apply fix; count type errors"),
    71815: ("R4", "B", "Fill struct recursed on pointer element types: stack overflow for 'type P *P' and invalid syntax '&new(int)' for **int fields, per the fix message; not diagnostic-attached.", "codeaction-other: Fill struct on S{} with a **int field; check syntax errors"),
    73037: ("R4", "A", "The rangeint modernizer qualifies a conversion to a type of the current package with its own package name, producing 'mlkem.fieldElement(q)' and 'undefined: mlkem'.", "quickfix: loop 'for a := fieldElement(0); a < q; a++' in package mlkem; apply fix"),
    73547: ("R4", "A", "The stringscutprefix modernizer rewrites an if statement that already has an init statement into 'if auth := ...; after, ok := strings.CutPrefix(...); ok', which does not parse.", "quickfix: apply stringscutprefix to the reported if-with-init snippet; check syntax errors"),
    73564: ("R4", "A", "The slicescontains modernizer replaces a loop with slices.ContainsFunc when the callback takes an interface parameter, causing 'S (type []Fruit) does not satisfy ~[]E'.", "quickfix: apply fix to the reported Fruit/FruitInfo loop; count type errors"),
    73576: ("R4", "A", "The minmax modernizer rewrites an if/else-if/else chain into 'else x = min(index, maxVal)', which is invalid syntax.", "quickfix: apply minmax to the reported SetFocus if-else-if chain; check syntax errors"),
    73663: ("R4", "A", "The slicesdelete modernizer passes uint32 indices to slices.Delete, so the fixed code fails with 'cannot use i (variable of type uint32) as int value'.", "quickfix: append(s[:i], s[i+1:]...) with i uint32; apply fix; count type errors"),
    74708: ("R4", "A", "The waitgroup modernizer printed the receiver of a struct field as '&{s wg}.Go(func() {...})', producing invalid code.", "quickfix: go1.25 file with s.wg.Add(1)/go func(){...}(); apply fix; check syntax errors"),
    74938: ("R4", "A", "The slicescontains modernizer suggests slices.ContainsFunc when the method parameter type (Expression) differs from the slice element type (*Column), producing code that does not compile.", "quickfix: apply fix to the reported InColumnArray loop; count type errors"),
    80459: ("R4", "A", "The simplifycompositelit fix removed the character before the literal type instead of '&' when a comment separates them, producing invalid Go code.", "quickfix: '& /* comment */ Config{...}' in a []*Config literal; apply fix; check syntax errors"),
    81134: ("R4", "A", "Both ptrtoerror fixes for a generic error type insert 'var _ error = *new(MyError)' or '(*MyError)(nil)', which fail with 'cannot use generic type MyError without instantiation'; analyzer exists only at tip.", "quickfix: type MyError[T any] struct{ error; Value T }; apply either fix; count errors"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "feature": (33987, 38467, 39804, 47558, 50825, 51544, 66582, 67733, 70717, 71369, 71481, 74494),
    "display": (34332, 34334, 36363, 47669),
    "crash": (38091, 63921, 64087, 64545, 70666, 71786, 78270),
    "cli": (75358,),
    "refactor": (48963, 67336),
    "semantic_edit": (71296, 71844, 71952, 72727, 72829, 72917, 73686, 75296, 77318),
    "other": (32440, 39296, 39681, 45111, 63821),
}
