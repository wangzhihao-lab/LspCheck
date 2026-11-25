# [ts6 6.0.3] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts6-r3-definitionconsistency-missing-d-0ab4de`, signature `ts6|r3_routes|definitionConsistency:missing`, case family `d`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `umami-software/umami@12ad773d621f` (corpus, commit 12ad773d621f51da6e81e9031b458efe56be3e8e), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `src/app/(main)/settings/websites/WebsitesSettingsPage.tsx` at line 12, column 24 (LSP position {line: 11, character: 23}) gives the expected set; didOpen `src/app/(main)/websites/WebsitesTable.tsx` and `textDocument/definition` at the reference line 46, column 15 (LSP position {line: 45, character: 14}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "node_modules/.pnpm/@types+react@19.3.0/node_modules/@types/react/index.d.ts",
  2903,
  8,
  2903,
  13
 ],
 [
  "src/components/common/SectionHeader.tsx",
  10,
  2,
  10,
  7
 ]
]
```

Actual:

```json
[
 [
  "node_modules/.pnpm/@types+react@19.3.0/node_modules/@types/react/index.d.ts",
  2903,
  8,
  2903,
  13
 ]
]
```

Project file `src/app/(main)/websites/WebsitesTable.tsx`:

```
   1 | import { DataColumn, DataTable, type DataTableProps, Icon, Text } from '@umami/react-zen';
   2 | import { type ReactNode, useMemo } from 'react';
   3 | import { DateDistance } from '@/components/common/DateDistance';
   4 | import { LinkButton } from '@/components/common/LinkButton';
   5 | import { SortableLabel } from '@/components/common/SortableLabel';
   6 | import { useMessages, useNavigation, useWebsiteListChartsQuery } from '@/components/hooks';
   7 | import { SquarePen } from '@/components/icons';
   8 | import { decodePunycodeDomain } from '@/lib/format';
   9 | import { WebsiteSparkline } from './WebsiteSparkline';
     ...
  11 | export interface WebsitesTableProps extends DataTableProps {
  12 |   showActions?: boolean;
  13 |   renderLink?: (row: any) => ReactNode;
  14 | }
     ...
  16 | export function WebsitesTable({
  17 |   showActions,
  18 |   renderLink,
  19 |   data = [],
  20 |   ...props
  21 | }: WebsitesTableProps & { data?: any[] }) {
  22 |   const { t, labels } = useMessages();
  23 |   const { renderUrl } = useNavigation();
  24 |   const websiteIds = useMemo(() => data.map(row => row.id), [data]);
  25 |   const chartsQuery = useWebsiteListChartsQuery(websiteIds);
  26 |   const charts = chartsQuery.data?.data || {};
  27 |   const isChartLoading = chartsQuery.isLoading && !chartsQuery.data;
     ...
  29 |   return (
  30 |     <DataTable {...props} data={data}>
  31 |       <DataColumn
  32 |         id="name"
  33 |         label={<SortableLabel label={t(labels.name)} sortKey="name" />}
  34 |         style={{ minWidth: 0 }}
  35 |       >
  36 |         {renderLink}
  37 |       </DataColumn>
  38 |       <DataColumn
  39 |         id="domain"
  40 |         label={<SortableLabel label={t(labels.domain)} sortKey="domain" />}
  41 |         style={{ minWidth: 0 }}
  42 |       >
  43 |         {(row: any) => (
  44 |           <Text
  45 |             truncate
  46 |             title={decodePunycodeDomain(row.domain) ?? undefined}
  47 |             style={{ maxWidth: '100%' }}
  48 |           >
  49 |             {decodePunycodeDomain(row.domain)}
  50 |           </Text>
  51 |         )}
  52 |       </DataColumn>
  53 |       <DataColumn
  54 |         id="chart"
  55 |         label={<span style={{ whiteSpace: 'normal' }}>{`${t(labels.visitors)} (7d)`}</span>}
  56 |         style={{ minWidth: 0 }}
  57 |       >
  58 |         {(row: any) => {
  59 |           const chart = charts[row.id];
     ...
  61 |           return (
  62 |             <WebsiteSparkline
  63 |               values={chart?.values}
  64 |               total={chart?.total}
  65 |               isLoading={isChartLoading}
  66 |             />
  67 |           );
  68 |         }}
  69 |       </DataColumn>
  70 |       <DataColumn
  71 |         id="created"
  72 |         label={
  73 |           <SortableLabel label={t(labels.created)} sortKey="createdAt" defaultDirection="desc" />
  74 |         }
  75 |         width="180px"
  76 |       >
  77 |         {(row: any) => <DateDistance date={new Date(row.createdAt)} />}
  78 |       </DataColumn>
  79 |       {showActions && (
  80 |         <DataColumn id="action" label=" " align="end" width="48px">
  81 |           {(row: any) => {
  82 |             const websiteId = row.id;
     ...
  84 |             return (
  85 |               <LinkButton href={renderUrl(`/websites/${websiteId}/settings`)} variant="quiet">
  86 |                 <Icon>
  87 |                   <SquarePen />
  88 |                 </Icon>
  89 |               </LinkButton>
  90 |             );
  91 |           }}
  92 |         </DataColumn>
  93 |       )}
  94 |     </DataTable>
  95 |   );
  96 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r3-definitionconsistency-missing-d-0ab4de/repro.json
```

## Evidence and reduction

- representative d6ece30a31a2-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects umami-software/umami@12ad773d621f, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#795](https://github.com/typescript-language-server/typescript-language-server/issues/795) Go to definition is not working on neovim (closed, 2023-11-12, 2 comments)
- [typescript-language-server/typescript-language-server#507](https://github.com/typescript-language-server/typescript-language-server/issues/507) Possibility of including Go to Source Definition? (closed, 2022-07-03, 4 comments)
- [typescript-language-server/typescript-language-server#431](https://github.com/typescript-language-server/typescript-language-server/issues/431) Go to definition function broken in monorepo project (closed, 2022-04-10, 4 comments)
- [typescript-language-server/typescript-language-server#60](https://github.com/typescript-language-server/typescript-language-server/issues/60) Error: No Project. When starting LS from a bundled electron Theia application (closed, 2018-09-02, 9 comments)
- [typescript-language-server/typescript-language-server#679](https://github.com/typescript-language-server/typescript-language-server/issues/679) Inconsistent completion suggestions on JSX attributes (closed, 2023-02-07, 22 comments)
- [typescript-language-server/typescript-language-server#277](https://github.com/typescript-language-server/typescript-language-server/issues/277) Using typescript plugins through neovim-lsp (closed, 2021-10-31, 10 comments)
- [typescript-language-server/typescript-language-server#264](https://github.com/typescript-language-server/typescript-language-server/issues/264) Inlay Hints return empty result (closed, 2021-10-06, 4 comments)
- [typescript-language-server/typescript-language-server#203](https://github.com/typescript-language-server/typescript-language-server/issues/203) Javascript: Jump to declaration still not at JSDT's level (closed, 2021-04-16, 9 comments)
- queries: `"go to definition" in:title repo:typescript-language-server/typescript-language-server is:issue`; `definition missing repo:typescript-language-server/typescript-language-server is:issue`; `definition "go to definition" repo:typescript-language-server/typescript-language-server is:issue`; `definition inconsistent repo:typescript-language-server/typescript-language-server is:issue`; `"go to definition" in:title repo:microsoft/TypeScript is:issue`; `definition missing repo:microsoft/TypeScript is:issue`; `definition "go to definition" repo:microsoft/TypeScript is:issue`; `definition inconsistent repo:microsoft/TypeScript is:issue`
