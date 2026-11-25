# [pyright 1.1.414] references misses entries after file rename round trip

Draft for the author (not filed). Group `pyright-r1-references-missing-h5-64453c`, signature `pyright|r1_history|references:missing`, case family `H5`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `pallets/flask@d73fa1cdcbd8` (corpus, commit d73fa1cdcbd8b1465c151db8924ba58b1dd14e35), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open examples/javascript/js_example/views.py`
3. Timing: send the steps 0 ms apart without waiting, then wait until idle.
4. textDocument/didOpen `examples/celery/src/task_app/tasks.py`, `examples/javascript/tests/test_js_example.py` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/references` on `examples/javascript/js_example/views.py` line 17, column 41 (LSP position {line: 16, character: 40}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_socket.pyi",
  845,
  25,
  845,
  30
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_socket.pyi",
  868,
  28,
  868,
  33
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_socket.pyi",
  906,
  32,
  906,
  37
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_socket.pyi",
  945,
  27,
  945,
  32
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_socket.pyi",
  948,
  31,
  948,
  36
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  17,
  54,
  17,
  59
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  29,
  32,
  29,
  37
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  39,
  58,
  39,
  63
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  43,
  63,
  43,
  68
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  57,
  58,
  57,
  63
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  61,
  63,
  61,
  68
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  93,
  19,
  93,
  24
 ],

... (29233 characters)
```

Actual:

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  17,
  54,
  17,
  59
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  29,
  32,
  29,
  37
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  39,
  58,
  39,
  63
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  43,
  63,
  43,
  68
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  57,
  58,
  57,
  63
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  61,
  63,
  61,
  68
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_thread.pyi",
  93,
  19,
  93,
  24
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/ast.pyi",
  1109,
  73,
  1109,
  78
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/builtins.pyi",
  301,
  44,
  301,
  49
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/builtins.pyi",
  308,
  45,
  308,
  50
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/builtins.pyi",
  319,
  71,
  319,
  76
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/builtins.pyi",
  356,
  27,
  356,
  32
 ]
... (28244 characters)
```

Project file `examples/javascript/js_example/views.py`:

```
   1 | from flask import jsonify
   2 | from flask import render_template
   3 | from flask import request
     ...
   5 | from . import app
     ...
   8 | @app.route("/", defaults={"js": "fetch"})
   9 | @app.route("/<any(xhr, jquery, fetch):js>")
  10 | def index(js):
  11 |     return render_template(f"{js}.html", js=js)
     ...
  14 | @app.route("/add", methods=["POST"])
  15 | def add():
  16 |     a = request.form.get("a", 0, type=float)
  17 |     b = request.form.get("b", 0, type=float)
  18 |     return jsonify(result=a + b)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/pyright-r1-references-missing-h5-64453c/repro.json
```

## Evidence and reduction

- representative ec02b35ad43d-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 1 (6 probes, 47.483 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects pallets/flask@d73fa1cdcbd8, timings race0, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#375](https://github.com/microsoft/pyright/issues/375) rename symbol only seems to apply to open files (closed, 2019-11-28, 7 comments)
- [microsoft/pyright#3075](https://github.com/microsoft/pyright/issues/3075) Lazy analysis for LSP (closed, 2022-02-18, 6 comments)
- [microsoft/pyright#10086](https://github.com/microsoft/pyright/issues/10086) Pyright LSP Returns Incomplete References Without Explicit didOpen for All Files (closed, 2025-03-14, 5 comments)
- [microsoft/pyright#10715](https://github.com/microsoft/pyright/issues/10715) @overload function gives incorrect revealed type for Pylance but not for pyright/mypy (closed, 2025-07-16, 38 comments)
- [microsoft/pyright#10053](https://github.com/microsoft/pyright/issues/10053) Django BooleanField default value error (closed, 2025-03-10, 5 comments)
- [microsoft/pyright#8693](https://github.com/microsoft/pyright/issues/8693) Provide diagnostics for missing brackets. (closed, 2024-08-08, 2 comments)
- [microsoft/pyright#395](https://github.com/microsoft/pyright/issues/395)  1.1.8 not work when using multi-root workspace (closed, 2019-12-06, 21 comments)
- queries: `"rename file" in:title repo:microsoft/pyright is:issue`; `references missing repo:microsoft/pyright is:issue`; `references "rename file" repo:microsoft/pyright is:issue`; `references stale repo:microsoft/pyright is:issue`
