# [pyright 1.1.414] references adds entries after configuration toggle a->b->a

Draft for the author (not filed). Group `pyright-r1-references-extra-h4-a63d47`, signature `pyright|r1_history|references:extra`, case family `H4`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `Graphify-Labs/graphify@a5957aa6ef51` (corpus, commit a5957aa6ef51c9be8d054de9783d25046c187f3f), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open worked/example/raw/api.py`
3. workspace/didChangeConfiguration: `set_config {"python": {"analysis": {"diagnosticMode": "workspace"}}}`
4. workspace/didChangeConfiguration: `set_config {"python": {"analysis": {"diagnosticMode": "openFilesOnly"}}}`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `tests/test_hypergraph.py`, `tests/test_merge_chunks_validation.py` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/references` on `worked/example/raw/api.py` line 20, column 22 (LSP position {line: 19, character: 21}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/builtins.pyi",
  1826,
  4,
  1826,
  7
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  227,
  16,
  227,
  19
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  246,
  16,
  246,
  19
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  498,
  22,
  498,
  25
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  562,
  21,
  562,
  24
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  569,
  29,
  569,
  32
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  619,
  23,
  619,
  26
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  635,
  15,
  635,
  18
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  642,
  11,
  642,
  14
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  656,
  11,
  656,
  14
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  660,
  19,
  660,
  22
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  663,
  41,
  663,
  44
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  684,
  15,
  684,
  18
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  902,
  9,
  902,
  1
... (186183 characters)
```

Actual:

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/builtins.pyi",
  1826,
  4,
  1826,
  7
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  227,
  16,
  227,
  19
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  246,
  16,
  246,
  19
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  498,
  22,
  498,
  25
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  562,
  21,
  562,
  24
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  569,
  29,
  569,
  32
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  619,
  23,
  619,
  26
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  635,
  15,
  635,
  18
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  642,
  11,
  642,
  14
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  656,
  11,
  656,
  14
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  660,
  19,
  660,
  22
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  663,
  41,
  663,
  44
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  684,
  15,
  684,
  18
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/IPython/lib/pretty.py",
  902,
  9,
  902,
  1
... (192448 characters)
```

Project file `worked/example/raw/api.py`:

```
   1 | """
   2 | API module - exposes the document pipeline over HTTP.
   3 | Thin layer over parser, validator, processor, and storage.
   4 | """
   5 | from parser import batch_parse, parse_file
   6 | from validator import validate_document, ValidationError
   7 | from processor import process_and_save, enrich_document
   8 | from storage import load_record, delete_record, list_records, load_index
     ...
  11 | def handle_upload(paths: list) -> dict:
  12 |     """
  13 |     Accept a list of file paths, run the full pipeline on each,
  14 |     and return a summary of what succeeded and what failed.
  15 |     """
  16 |     results = batch_parse(paths)
  17 |     succeeded = [r for r in results if r["ok"]]
  18 |     failed = [r for r in results if not r["ok"]]
  19 |     return {
  20 |         "uploaded": len(succeeded),
  21 |         "failed": len(failed),
  22 |         "ids": [r["id"] for r in succeeded],
  23 |         "errors": failed,
  24 |     }
     ...
  27 | def handle_get(record_id: str) -> dict:
  28 |     """Fetch a document by ID and return it."""
  29 |     try:
  30 |         return load_record(record_id)
  31 |     except KeyError:
  32 |         return {"error": f"Record {record_id} not found"}
     ...
  35 | def handle_delete(record_id: str) -> dict:
  36 |     """Delete a document by ID."""
  37 |     deleted = delete_record(record_id)
  38 |     if deleted:
  39 |         return {"deleted": record_id}
  40 |     return {"error": f"Record {record_id} not found"}
     ...
  43 | def handle_list() -> dict:
  44 |     """List all document IDs in storage."""
  45 |     return {"records": list_records()}
     ...
  48 | def handle_search(query: str) -> dict:
  49 |     """
  50 |     Simple keyword search over the index.
  51 |     Returns documents whose keyword list overlaps with the query terms.
  52 |     """
  53 |     terms = set(query.lower().split())
  54 |     index = load_index()
  55 |     matches = []
  56 |     for record_id, entry in index.items():
  57 |         keywords = set(entry.get("keywords", []))
  58 |         if terms & keywords:
  59 |             matches.append({
  60 |                 "id": record_id,
  61 |                 "title": entry.get("title", ""),
  62 |                 "matched_keywords": list(terms & keywords),
  63 |             })
  64 |     return {"query": query, "results": matches}
     ...
  67 | def handle_enrich(record_id: str) -> dict:
  68 |     """Re-enrich a document to pick up new cross-references."""
  69 |     try:
  70 |         doc = load_record(record_id)
  71 |     except KeyError:
  72 |         return {"error": f"Record {record_id} not found"}
  73 |     try:
  74 |         validated = validate_document(doc)
  75 |     except ValidationError as e:
  76 |         return {"error": str(e)}
  77 |     enriched_id = process_and_save(validated)
  78 |     return {"enriched": enriched_id}
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/pyright-r1-references-extra-h4-a63d47/repro.json
```

## Evidence and reduction

- representative 535608cb8838-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 3 (10 probes, 704.865 s, reduced ops confirmed 3/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects Graphify-Labs/graphify@a5957aa6ef51, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#10279](https://github.com/microsoft/pyright/issues/10279) Unknown Send type in generator with yield from (closed, 2025-04-08, 4 comments)
- [microsoft/pyright#10414](https://github.com/microsoft/pyright/issues/10414) "Type is partially unknown" on typed functions when using `--verifytypes`, even with `--ignoreexternal` (closed, 2025-05-05, 5 comments)
- [microsoft/pyright#10715](https://github.com/microsoft/pyright/issues/10715) @overload function gives incorrect revealed type for Pylance but not for pyright/mypy (closed, 2025-07-16, 38 comments)
- [microsoft/pyright#10053](https://github.com/microsoft/pyright/issues/10053) Django BooleanField default value error (closed, 2025-03-10, 5 comments)
- [microsoft/pyright#9304](https://github.com/microsoft/pyright/issues/9304) Ignores configuation (closed, 2024-10-24, 1 comments)
- [microsoft/pyright#6776](https://github.com/microsoft/pyright/issues/6776) False negative with `Class1 | Class2` union syntax prior to Python 3.10, when `__future__.annotations` is imported (closed, 2023-12-18, 9 comments)
- queries: `"configuration change" in:title repo:microsoft/pyright is:issue`; `references extra repo:microsoft/pyright is:issue`; `references "configuration change" repo:microsoft/pyright is:issue`; `references stale repo:microsoft/pyright is:issue`
