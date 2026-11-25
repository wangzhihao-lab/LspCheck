# [gopls v0.23.0] codeAction adds entries after transformation T2

Draft for the author (not filed). Group `gopls-r5-codeaction-extra-t2-86a8ac`, signature `gopls|r5_transforms|codeAction:extra`, case family `T2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `go-gorm/gorm@b3d3bf219f02` (corpus, commit b3d3bf219f0283f8e2e985bac509cb643170f729), language go

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T2 applied to `migrator/column_type.go` (1 edit(s), first [6, 0, 6, 0]).
3. Query `textDocument/codeAction` on `migrator/column_type.go` line 20, column 22 (LSP position {line: 19, character: 21}) (pos); compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Add struct tags",
  "refactor.rewrite.addTags"
 ],
 [
  "Browse documentation for package sql",
  "source.doc"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Show compiler optimization details for \"migrator\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"migrator\"",
  "source.splitPackage"
 ]
]
```

Actual:

```json
[
 [
  "Add struct tags",
  "refactor.rewrite.addTags"
 ],
 [
  "Browse documentation for package sql",
  "source.doc"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Organize Imports",
  "source.organizeImports"
 ],
 [
  "Show compiler optimization details for \"migrator\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"migrator\"",
  "source.splitPackage"
 ]
]
```

Project file `migrator/column_type.go`:

```
   1 | package migrator
     ...
   3 | import (
   4 | 	"database/sql"
   5 | 	"reflect"
   6 | )
     ...
   8 | // ColumnType column type implements ColumnType interface
   9 | type ColumnType struct {
  10 | 	SQLColumnType      *sql.ColumnType
  11 | 	NameValue          sql.NullString
  12 | 	DataTypeValue      sql.NullString
  13 | 	ColumnTypeValue    sql.NullString
  14 | 	PrimaryKeyValue    sql.NullBool
  15 | 	UniqueValue        sql.NullBool
  16 | 	AutoIncrementValue sql.NullBool
  17 | 	LengthValue        sql.NullInt64
  18 | 	DecimalSizeValue   sql.NullInt64
  19 | 	ScaleValue         sql.NullInt64
  20 | 	NullableValue      sql.NullBool
  21 | 	ScanTypeValue      reflect.Type
  22 | 	CommentValue       sql.NullString
  23 | 	DefaultValueValue  sql.NullString
  24 | }
     ...
  26 | // Name returns the name or alias of the column.
  27 | func (ct ColumnType) Name() string {
  28 | 	if ct.NameValue.Valid {
  29 | 		return ct.NameValue.String
  30 | 	}
  31 | 	if ct.SQLColumnType != nil {
  32 | 		return ct.SQLColumnType.Name()
  33 | 	}
  34 | 	return ""
  35 | }
     ...
  37 | // DatabaseTypeName returns the database system name of the column type. If an empty
  38 | // string is returned, then the driver type name is not supported.
  39 | // Consult your driver documentation for a list of driver data types. Length specifiers
  40 | // are not included.
  41 | // Common type names include "VARCHAR", "TEXT", "NVARCHAR", "DECIMAL", "BOOL",
  42 | // "INT", and "BIGINT".
  43 | func (ct ColumnType) DatabaseTypeName() string {
  44 | 	if ct.DataTypeValue.Valid {
  45 | 		return ct.DataTypeValue.String
  46 | 	}
  47 | 	if ct.SQLColumnType != nil {
  48 | 		return ct.SQLColumnType.DatabaseTypeName()
  49 | 	}
  50 | 	return ""
  51 | }
     ...
  53 | // ColumnType returns the database type of the column. like `varchar(16)`
  54 | func (ct ColumnType) ColumnType() (columnType string, ok bool) {
  55 | 	return ct.ColumnTypeValue.String, ct.ColumnTypeValue.Valid
  56 | }
     ...
  58 | // PrimaryKey returns the column is primary key or not.
  59 | func (ct ColumnType) PrimaryKey() (isPrimaryKey bool, ok bool) {
  60 | 	return ct.PrimaryKeyValue.Bool, ct.PrimaryKeyValue.Valid
  61 | }
     ...
  63 | // AutoIncrement returns the column is auto increment or not.
  64 | func (ct ColumnType) AutoIncrement() (isAutoIncrement bool, ok bool) {
  65 | 	return ct.AutoIncrementValue.Bool, ct.AutoIncrementValue.Valid
  66 | }
     ...
  68 | // Length returns the column type length for variable length column types
  69 | func (ct ColumnType) Length() (length int64, ok bool) {
  70 | 	if ct.LengthValue.Valid {
  71 | 		return ct.LengthValue.Int64, true
  72 | 	}
  73 | 	if ct.SQLColumnType != nil {
  74 | 		return ct.SQLColumnType.Length()
  75 | 	}
  76 | 	return 0, false
  77 | }
     ...
  79 | // DecimalSize returns the scale and precision of a decimal type.
  80 | func (ct ColumnType) DecimalSize() (precision int64, scale int64, ok bool) {
  81 | 	if ct.DecimalSizeValue.Valid {
  82 | 		return ct.DecimalSizeValue.Int64, ct.ScaleValue.Int64, true
  83 | 	}
  84 | 	if ct.SQLColumnType != nil {
  85 | 		return ct.SQLColumnType.DecimalSize()
  86 | 	}
  87 | 	return 0, 0, false
  88 | }
     ...
  90 | // Nullable reports whether the column may be null.
  91 | func (ct ColumnType) Nullable() (nullable bool, ok bool) {
  92 | 	if ct.NullableValue.Valid {
  93 | 		return ct.NullableValue.Bool, true
  94 | 	}
  95 | 	if ct.SQLColumnType != nil {
  96 | 		return ct.SQLColumnType.Nullable()
  97 | 	}
  98 | 	return false, false
  99 | }
     ...
 101 | // Unique reports whether the column may be unique.
 102 | func (ct ColumnType) Unique() (unique bool, ok bool) {
 103 | 	return ct.UniqueValue.Bool, ct.UniqueValue.Valid
 104 | }
     ...
 106 | // ScanType returns a Go type suitable for scanning into using Rows.Scan.
 107 | func (ct ColumnType) ScanType() reflect.Type {
 108 | 	if ct.ScanTypeValue != nil {
 109 | 		return ct.ScanTypeValue
 110 | 	}
 111 | 	if ct.SQLColumnType != nil {
 112 | 		return ct.SQLColumnType.ScanType()
 113 | 	}
 114 | 	return nil
 115 | }
     ...
 117 | // Comment returns the comment of current column.
 118 | func (ct ColumnType) Comment() (value string, ok bool) {
 119 | 	return ct.CommentValue.String, ct.CommentValue.Valid
 120 | }
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r5-codeaction-extra-t2-86a8ac/repro.json
```

## Evidence and reduction

- representative 9b3bd893b17f-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects go-gorm/gorm@b3d3bf219f02, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#64936](https://github.com/golang/go/issues/64936) x/tools/gopls: support for comment rendering (open, 2024-01-02, 9 comments)
- [golang/go#43735](https://github.com/golang/go/issues/43735) x/tools/gopls: rearranging struct fields deletes comments (open, 2021-01-15, 7 comments)
- [golang/go#48200](https://github.com/golang/go/issues/48200) x/tools/gopls: show full comments for constant or variable declaration (open, 2021-09-05, 3 comments)
- [golang/go#44684](https://github.com/golang/go/issues/44684) x/tools/gopls: add an option to keep original line breaks in documentation comments (open, 2021-02-28, 5 comments)
- [golang/go#74607](https://github.com/golang/go/issues/74607) x/tools/gopls: Semantic tokens not generated for local unexported symbols referenced in comment links (open, 2025-07-14, 2 comments)
- [golang/go#70085](https://github.com/golang/go/issues/70085) x/tools/gopls: add refactor.inline.variable-all code action (open, 2024-10-29, 11 comments)
- [golang/go#39805](https://github.com/golang/go/issues/39805) x/tools/gopls: convert 'gofumpt' from formatter to code action provider (open, 2020-06-24, 5 comments)
- [golang/go#56403](https://github.com/golang/go/issues/56403) x/tools/gopls: allow enabling gofumpt extra rules (open, 2022-10-24, 5 comments)
- queries: `comment in:title repo:golang/go is:issue label:gopls`; `"code action" extra repo:golang/go is:issue label:gopls`; `"code action" comment repo:golang/go is:issue label:gopls`; `"code action" whitespace repo:golang/go is:issue label:gopls`
