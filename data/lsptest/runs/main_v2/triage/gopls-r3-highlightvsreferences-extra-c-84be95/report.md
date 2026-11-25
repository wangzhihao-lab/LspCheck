# [gopls v0.23.0] highlightVsReferences: two routes to the same fact disagree

Draft for the author (not filed). Group `gopls-r3-highlightvsreferences-extra-c-84be95`, signature `gopls|r3_routes|highlightVsReferences:extra`, case family `c`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `go-gorm/gorm@b3d3bf219f02` (corpus, commit b3d3bf219f0283f8e2e985bac509cb643170f729), language go

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/documentHighlight` and `textDocument/references` (includeDeclaration) on `clause/joins.go` at line 48, column 11 (LSP position {line: 47, character: 10}); every highlight range must be a reference range in that file.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  40,
  12,
  40,
  17
 ],
 [
  46,
  32,
  46,
  37
 ],
 [
  47,
  8,
  47,
  13
 ]
]
```

Actual:

```json
[
 [
  40,
  12,
  40,
  17
 ],
 [
  46,
  32,
  46,
  37
 ],
 [
  47,
  8,
  47,
  13
 ],
 [
  47,
  8,
  49,
  2
 ]
]
```

Project file `clause/joins.go`:

```
   1 | package clause
     ...
   3 | import "gorm.io/gorm/utils"
     ...
   5 | type JoinType string
     ...
   7 | const (
   8 | 	CrossJoin JoinType = "CROSS"
   9 | 	InnerJoin JoinType = "INNER"
  10 | 	LeftJoin  JoinType = "LEFT"
  11 | 	RightJoin JoinType = "RIGHT"
  12 | )
     ...
  14 | type JoinTarget struct {
  15 | 	Type        JoinType
  16 | 	Association string
  17 | 	Subquery    Expression
  18 | 	Table       string
  19 | }
     ...
  21 | func Has(name string) JoinTarget {
  22 | 	return JoinTarget{Type: InnerJoin, Association: name}
  23 | }
     ...
  25 | func (jt JoinType) Association(name string) JoinTarget {
  26 | 	return JoinTarget{Type: jt, Association: name}
  27 | }
     ...
  29 | func (jt JoinType) AssociationFrom(name string, subquery Expression) JoinTarget {
  30 | 	return JoinTarget{Type: jt, Association: name, Subquery: subquery}
  31 | }
     ...
  33 | func (jt JoinTarget) As(name string) JoinTarget {
  34 | 	jt.Table = name
  35 | 	return jt
  36 | }
     ...
  38 | // Join clause for from
  39 | type Join struct {
  40 | 	Type       JoinType
  41 | 	Table      Table
  42 | 	ON         Where
  43 | 	Using      []string
  44 | 	Expression Expression
  45 | }
     ...
  47 | func JoinTable(names ...string) Table {
  48 | 	return Table{
  49 | 		Name: utils.JoinNestedRelationNames(names),
  50 | 	}
  51 | }
     ...
  53 | func (join Join) Build(builder Builder) {
  54 | 	if join.Expression != nil {
  55 | 		join.Expression.Build(builder)
  56 | 	} else {
  57 | 		if join.Type != "" {
  58 | 			builder.WriteString(string(join.Type))
  59 | 			builder.WriteByte(' ')
  60 | 		}
     ...
  62 | 		builder.WriteString("JOIN ")
  63 | 		builder.WriteQuoted(join.Table)
     ...
  65 | 		if len(join.ON.Exprs) > 0 {
  66 | 			builder.WriteString(" ON ")
  67 | 			join.ON.Build(builder)
  68 | 		} else if len(join.Using) > 0 {
  69 | 			builder.WriteString(" USING (")
  70 | 			for idx, c := range join.Using {
  71 | 				if idx > 0 {
  72 | 					builder.WriteByte(',')
  73 | 				}
  74 | 				builder.WriteQuoted(c)
  75 | 			}
  76 | 			builder.WriteByte(')')
  77 | 		}
  78 | 	}
  79 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r3-highlightvsreferences-extra-c-84be95/repro.json
```

## Evidence and reduction

- representative 660200eada5b-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects SagerNet/sing-box@0d91c4547921, abiosoft/colima@bba803d3d6fa, go-gorm/gorm@b3d3bf219f02, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#81462](https://github.com/golang/go/issues/81462) x/tools/gopls: follow linkname references (open, 2026-09-10, 3 comments)
- [golang/go#73781](https://github.com/golang/go/issues/73781) x/tools/gopls: References does not find all references in the workspace (open, 2022-09-08, 24 comments)
- [golang/go#74307](https://github.com/golang/go/issues/74307) x/tools/gopls: References: report unkeyed composite literals as implicit references to struct fields (open, 2025-06-19, 3 comments)
- [golang/go#66356](https://github.com/golang/go/issues/66356) x/tools/gopls: feature: alternative 'references' query that reports implied references to struct fields (etc) (open, 2024-03-16, 7 comments)
- [golang/go#40862](https://github.com/golang/go/issues/40862) x/tools/gopls: add codelens to show number of references to each symbol (open, 2020-08-16, 41 comments)
- [golang/go#74917](https://github.com/golang/go/issues/74917) x/tools/gopls: prefix SignatureHelp label with "func" (open, 2025-08-06, 4 comments)
- [golang/go#63282](https://github.com/golang/go/issues/63282) x/tools/gopls: express completion scoring in terms of down-ranking factors (open, 2023-09-28, 2 comments)
- [golang/go#57963](https://github.com/golang/go/issues/57963) x/tools/gopls: add analyzer that reports broken doc links (open, 2023-01-23, 13 comments)
- queries: `references in:title repo:golang/go is:issue label:gopls`; `highlight extra repo:golang/go is:issue label:gopls`; `highlight references repo:golang/go is:issue label:gopls`; `highlight inconsistent repo:golang/go is:issue label:gopls`
