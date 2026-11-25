# [ts6 6.0.3] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts6-r3-definitionconsistency-lost-d-fb78dd`, signature `ts6|r3_routes|definitionConsistency:lost`, case family `d`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `DayuanJiang/next-ai-draw-io@58b73ef761d8` (corpus, commit 58b73ef761d8a5e5b2afa2c360428d3dea996312), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `components/ui/command.tsx` at line 178, column 13 (LSP position {line: 177, character: 12}) gives the expected set; didOpen `components/ui/command.tsx` and `textDocument/definition` at the reference line 169, column 8 (LSP position {line: 168, character: 7}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "components/ui/command.tsx",
  168,
  5,
  168,
  10
 ]
]
```

Actual:

```json
[]
```

Project file `components/ui/command.tsx`:

```
   1 | "use client"
     ...
   3 | import * as React from "react"
   4 | import { Command as CommandPrimitive } from "cmdk"
   5 | import { SearchIcon } from "lucide-react"
     ...
   7 | import { cn } from "@/lib/utils"
   8 | import {
   9 |   Dialog,
  10 |   DialogContent,
  11 |   DialogDescription,
  12 |   DialogHeader,
  13 |   DialogTitle,
  14 | } from "@/components/ui/dialog"
     ...
  16 | function Command({
  17 |   className,
  18 |   ...props
  19 | }: React.ComponentProps<typeof CommandPrimitive>) {
  20 |   return (
  21 |     <CommandPrimitive
  22 |       data-slot="command"
  23 |       className={cn(
  24 |         "bg-popover text-popover-foreground flex h-full w-full flex-col overflow-hidden rounded-md",
  25 |         className
  26 |       )}
  27 |       {...props}
  28 |     />
  29 |   )
  30 | }
     ...
  32 | function CommandDialog({
  33 |   title = "Command Palette",
  34 |   description = "Search for a command to run...",
  35 |   children,
  36 |   className,
  37 |   ...props
  38 | }: React.ComponentProps<typeof Dialog> & {
  39 |   title?: string
  40 |   description?: string
  41 |   className?: string
  42 | }) {
  43 |   return (
  44 |     <Dialog {...props}>
  45 |       <DialogHeader className="sr-only">
  46 |         <DialogTitle>{title}</DialogTitle>
  47 |         <DialogDescription>{description}</DialogDescription>
  48 |       </DialogHeader>
  49 |       <DialogContent className={cn("overflow-hidden p-0", className)}>
  50 |         <Command className="[&_[cmdk-group-heading]]:text-muted-foreground **:data-[slot=command-input-wrapper]:h-12 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group]]:px-2 [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-input-wrapper]_svg]:h-5 [&_[cmdk-input-wrapper]_svg]:w-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5">
  51 |           {children}
  52 |         </Command>
  53 |       </DialogContent>
  54 |     </Dialog>
  55 |   )
  56 | }
     ...
  58 | function CommandInput({
  59 |   className,
  60 |   ...props
  61 | }: React.ComponentProps<typeof CommandPrimitive.Input>) {
  62 |   return (
  63 |     <div
  64 |       data-slot="command-input-wrapper"
  65 |       className="flex h-9 items-center gap-2 border-b px-3"
  66 |     >
  67 |       <SearchIcon className="size-4 shrink-0 opacity-50" />
  68 |       <CommandPrimitive.Input
  69 |         data-slot="command-input"
  70 |         className={cn(
  71 |           "placeholder:text-muted-foreground flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-hidden disabled:cursor-not-allowed disabled:opacity-50",
  72 |           className
  73 |         )}
  74 |         {...props}
  75 |       />
  76 |     </div>
  77 |   )
  78 | }
     ...
  80 | const CommandList = React.forwardRef<
  81 |   React.ElementRef<typeof CommandPrimitive.List>,
  82 |   React.ComponentPropsWithoutRef<typeof CommandPrimitive.List>
  83 | >(({ className, ...props }, ref) => {
  84 |   return (
  85 |     <CommandPrimitive.List
  86 |       ref={ref}
  87 |       data-slot="command-list"
  88 |       className={cn(
  89 |         "max-h-[300px] scroll-py-1 overflow-x-hidden overflow-y-auto",
  90 |         className
  91 |       )}
  92 |       {...props}
  93 |     />
  94 |   )
  95 | })
  96 | CommandList.displayName = CommandPrimitive.List.displayName ?? "CommandList"
     ...
  98 | function CommandEmpty({
  99 |   ...props
 100 | }: React.ComponentProps<typeof CommandPrimitive.Empty>) {
 101 |   return (
 102 |     <CommandPrimitive.Empty
 103 |       data-slot="command-empty"
 104 |       className="py-6 text-center text-sm"
 105 |       {...props}
 106 |     />
 107 |   )
 108 | }
     ...
 110 | function CommandGroup({
 111 |   className,
 112 |   ...props
 113 | }: React.ComponentProps<typeof CommandPrimitive.Group>) {
 114 |   return (
 115 |     <CommandPrimitive.Group
 116 |       data-slot="command-group"
 117 |       className={cn(
 118 |         "text-foreground [&_[cmdk-group-heading]]:text-muted-foreground overflow-hidden p-1 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium",
 119 |         className
 120 |       )}
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r3-definitionconsistency-lost-d-fb78dd/repro.json
```

## Evidence and reduction

- representative 14b6c42ad69a-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects DayuanJiang/next-ai-draw-io@58b73ef761d8, vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 2

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
