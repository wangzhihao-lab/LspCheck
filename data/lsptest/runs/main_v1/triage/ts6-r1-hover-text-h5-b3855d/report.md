# [ts6 6.0.3] hover shows a different text after file rename round trip

Draft for the author (not filed). Group `ts6-r1-hover-text-h5-b3855d`, signature `ts6|r1_history|hover:text`, case family `H5`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `ChatGPTNextWeb/NextChat@defdcdb55d85` (corpus, commit defdcdb55d850cd12c4c657eb83729fd66e215c0), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open app/locales/index.ts`
3. Timing: wait until the server is idle after every step.
4. textDocument/didOpen `app/api/stability.ts`, `app/client/platforms/glm.ts` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/hover` on `app/locales/index.ts` line 56, column 41 (LSP position {line: 55, character: 40}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "type Lang = \"no\" | \"cn\" | \"en\" | \"tw\" | \"pt\" | \"da\" | \"jp\" | \"ko\" | \"id\" | \"fr\" | \"es\" | \"it\" | \"tr\" | \"de\" | \"vi\" | \"ru\" | \"cs\" | \"ar\" | \"bn\" | \"sk\"",
 [
  55,
  38,
  55,
  42
 ]
]
```

Actual:

```json
[
 "type Lang = \"cn\" | \"en\" | \"tw\" | \"pt\" | \"da\" | \"jp\" | \"ko\" | \"id\" | \"fr\" | \"es\" | \"it\" | \"tr\" | \"de\" | \"vi\" | \"ru\" | \"cs\" | \"no\" | \"ar\" | \"bn\" | \"sk\"",
 [
  55,
  38,
  55,
  42
 ]
]
```

Project file `app/locales/index.ts`:

```
   1 | import cn from "./cn";
   2 | import en from "./en";
   3 | import pt from "./pt";
   4 | import tw from "./tw";
   5 | import da from "./da";
   6 | import id from "./id";
   7 | import fr from "./fr";
   8 | import es from "./es";
   9 | import it from "./it";
  10 | import tr from "./tr";
  11 | import jp from "./jp";
  12 | import de from "./de";
  13 | import vi from "./vi";
  14 | import ru from "./ru";
  15 | import no from "./no";
  16 | import cs from "./cs";
  17 | import ko from "./ko";
  18 | import ar from "./ar";
  19 | import bn from "./bn";
  20 | import sk from "./sk";
  21 | import { merge } from "../utils/merge";
  22 | import { safeLocalStorage } from "@/app/utils";
     ...
  24 | import type { LocaleType } from "./cn";
  25 | export type { LocaleType, PartialLocaleType } from "./cn";
     ...
  27 | const localStorage = safeLocalStorage();
     ...
  29 | const ALL_LANGS = {
  30 |   cn,
  31 |   en,
  32 |   tw,
  33 |   pt,
  34 |   da,
  35 |   jp,
  36 |   ko,
  37 |   id,
  38 |   fr,
  39 |   es,
  40 |   it,
  41 |   tr,
  42 |   de,
  43 |   vi,
  44 |   ru,
  45 |   cs,
  46 |   no,
  47 |   ar,
  48 |   bn,
  49 |   sk,
  50 | };
     ...
  52 | export type Lang = keyof typeof ALL_LANGS;
     ...
  54 | export const AllLangs = Object.keys(ALL_LANGS) as Lang[];
     ...
  56 | export const ALL_LANG_OPTIONS: Record<Lang, string> = {
  57 |   cn: "简体中文",
  58 |   en: "English",
  59 |   pt: "Português",
  60 |   tw: "繁體中文",
  61 |   da: "Dansk",
  62 |   jp: "日本語",
  63 |   ko: "한국어",
  64 |   id: "Indonesia",
  65 |   fr: "Français",
  66 |   es: "Español",
  67 |   it: "Italiano",
  68 |   tr: "Türkçe",
  69 |   de: "Deutsch",
  70 |   vi: "Tiếng Việt",
  71 |   ru: "Русский",
  72 |   cs: "Čeština",
  73 |   no: "Nynorsk",
  74 |   ar: "العربية",
  75 |   bn: "বাংলা",
  76 |   sk: "Slovensky",
  77 | };
     ...
  79 | const LANG_KEY = "lang";
  80 | const DEFAULT_LANG = "en";
     ...
  82 | const fallbackLang = en;
  83 | const targetLang = ALL_LANGS[getLang()] as LocaleType;
     ...
  85 | // if target lang missing some fields, it will use fallback lang string
  86 | merge(fallbackLang, targetLang);
     ...
  88 | export default fallbackLang as LocaleType;
     ...
  90 | function getItem(key: string) {
  91 |   return localStorage.getItem(key);
  92 | }
     ...
  94 | function setItem(key: string, value: string) {
  95 |   localStorage.setItem(key, value);
  96 | }
     ...
  98 | function getLanguage() {
  99 |   try {
 100 |     const locale = new Intl.Locale(navigator.language).maximize();
 101 |     const region = locale?.region?.toLowerCase();
 102 |     // 1. check region code in ALL_LANGS
 103 |     if (AllLangs.includes(region as Lang)) {
 104 |       return region as Lang;
 105 |     }
 106 |     // 2. check language code in ALL_LANGS
 107 |     if (AllLangs.includes(locale.language as Lang)) {
 108 |       return locale.language as Lang;
 109 |     }
 110 |     return DEFAULT_LANG;
 111 |   } catch {
 112 |     return DEFAULT_LANG;
 113 |   }
 114 | }
     ...
 116 | export function getLang(): Lang {
 117 |   const savedLang = getItem(LANG_KEY);
     ...
 119 |   if (AllLangs.includes((savedLang ?? "") as Lang)) {
 120 |     return savedLang as Lang;
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-hover-text-h5-b3855d/repro.json
```

## Evidence and reduction

- representative f361ec20051e-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 1 (6 probes, 358.639 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [typescript-language-server/typescript-language-server#1014](https://github.com/typescript-language-server/typescript-language-server/issues/1014) TypeScript Language Server Hangs on Completion Resolution On Enter Key Pressed (closed, 2025-09-24, 21 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#865](https://github.com/typescript-language-server/typescript-language-server/issues/865) Fully resolve type aliases  (closed, 2024-02-02, 1 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `hover wrong repo:typescript-language-server/typescript-language-server is:issue`; `hover "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `hover stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `hover wrong repo:microsoft/TypeScript is:issue`; `hover "rename file" repo:microsoft/TypeScript is:issue`; `hover stale repo:microsoft/TypeScript is:issue`
