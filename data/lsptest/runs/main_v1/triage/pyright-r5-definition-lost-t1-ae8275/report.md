# [pyright 1.1.414] definition loses its answer after transformation T1

Draft for the author (not filed). Group `pyright-r5-definition-lost-t1-ae8275`, signature `pyright|r5_transforms|definition:lost`, case family `T1`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `TheAlgorithms/Python@60cea20f8537` (corpus, commit 60cea20f8537466e90b019f2a8fb2714165d10c5), language python

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T1 applied to `boolean_algebra/multiplexer.py` (1 edit(s), first [0, 0, 0, 0]).
3. Query `textDocument/definition` on `boolean_algebra/multiplexer.py` line 39, column 8 (LSP position {line: 38, character: 7}); compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "boolean_algebra/multiplexer.py",
  3,
  0,
  3,
  0
 ]
]
```

Actual:

```json
[]
```

Project file `boolean_algebra/multiplexer.py`:

```
   1 | def mux(input0: int, input1: int, select: int) -> int:
   2 |     """
   3 |     Implement a 2-to-1 Multiplexer.
     ...
   5 |     :param input0: The first input value (0 or 1).
   6 |     :param input1: The second input value (0 or 1).
   7 |     :param select: The select signal (0 or 1) to choose between input0 and input1.
   8 |     :return: The output based on the select signal.  input1 if select else input0.
     ...
  10 |     https://www.electrically4u.com/solved-problems-on-multiplexer
  11 |     https://en.wikipedia.org/wiki/Multiplexer
     ...
  13 |     >>> mux(0, 1, 0)
  14 |     0
  15 |     >>> mux(0, 1, 1)
  16 |     1
  17 |     >>> mux(1, 0, 0)
  18 |     1
  19 |     >>> mux(1, 0, 1)
  20 |     0
  21 |     >>> mux(2, 1, 0)
  22 |     Traceback (most recent call last):
  23 |         ...
  24 |     ValueError: Inputs and select signal must be 0 or 1
  25 |     >>> mux(0, -1, 0)
  26 |     Traceback (most recent call last):
  27 |         ...
  28 |     ValueError: Inputs and select signal must be 0 or 1
  29 |     >>> mux(0, 1, 1.1)
  30 |     Traceback (most recent call last):
  31 |         ...
  32 |     ValueError: Inputs and select signal must be 0 or 1
  33 |     """
  34 |     if all(i in (0, 1) for i in (input0, input1, select)):
  35 |         return input1 if select else input0
  36 |     raise ValueError("Inputs and select signal must be 0 or 1")
     ...
  39 | if __name__ == "__main__":
  40 |     import doctest
     ...
  42 |     doctest.testmod()
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/pyright-r5-definition-lost-t1-ae8275/repro.json
```

## Evidence and reduction

- representative 1862963f2542-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects TheAlgorithms/Python@60cea20f8537, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#11470](https://github.com/microsoft/pyright/issues/11470) Pyright is incorrectly handling overload functions (closed, 2026-05-28, 3 comments)
- [microsoft/pyright#10845](https://github.com/microsoft/pyright/issues/10845) Methods of a variadic generic class become uncallable when specified with TypeVarTuple and a suffix (closed, 2025-08-25, 1 comments)
- [microsoft/pyright#3968](https://github.com/microsoft/pyright/issues/3968) Pyright reports reportMissingSuperCall in a class that is not a subclass (closed, 2022-09-20, 8 comments)
- [microsoft/pyright#3013](https://github.com/microsoft/pyright/issues/3013) Strict Setting for Return Types (closed, 2022-02-09, 22 comments)
- [microsoft/pyright#6237](https://github.com/microsoft/pyright/issues/6237) reportUnsupportedDunderAll does not consider submodule names in __all__ (closed, 2023-10-26, 6 comments)
- [microsoft/pyright#9660](https://github.com/microsoft/pyright/issues/9660) FP and inconsistent analysis of classes as callables (closed, 2025-01-04, 2 comments)
- [microsoft/pyright#5966](https://github.com/microsoft/pyright/issues/5966) `deprecated` decorator with multi line reason string doesn't work on implementation when function has overloads (closed, 2023-09-17, 7 comments)
- queries: `"blank lines" in:title repo:microsoft/pyright is:issue`; `definition missing repo:microsoft/pyright is:issue`; `definition "blank lines" repo:microsoft/pyright is:issue`; `definition whitespace repo:microsoft/pyright is:issue`
