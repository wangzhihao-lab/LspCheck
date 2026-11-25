// Parse-only syntax check for TypeScript/JavaScript, used by oracles/syntax.py.
//
// Protocol: one JSON request per stdin line {"id", "path", "text"}; one JSON reply per
// stdout line {"id", "errors": ["L:C: TS<code> <message>", ...]} (1-based line/column),
// or {"id", "fatal": "<reason>"} when the parser itself failed. The script kind (TS,
// TSX, JS, JSX) follows the extension of `path`, as in createSourceFile. Only the parse
// diagnostics are reported: no type checking, no program, no file system access.
// The process stays alive until stdin closes, so hundreds of texts cost one start-up.
//
// Run line: node scripts/lsptest/oracles/ts_syntax.js <path to the typescript package>
"use strict";

const readline = require("readline");

const tsPath = process.argv[2];
if (!tsPath) {
  process.stderr.write("usage: node ts_syntax.js <typescript package dir>\n");
  process.exit(2);
}
const ts = require(tsPath);

function reply(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

function parseErrors(path, text) {
  const name = path && /\.[cm]?[jt]sx?$/i.test(path) ? path : "file.ts";
  const sf = ts.createSourceFile(name, text, ts.ScriptTarget.Latest, false);
  return (sf.parseDiagnostics || []).map((d) => {
    const p = sf.getLineAndCharacterOfPosition(d.start || 0);
    const msg = ts.flattenDiagnosticMessageText(d.messageText, " ");
    return `${p.line + 1}:${p.character + 1}: TS${d.code} ${msg}`;
  });
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
rl.on("line", (line) => {
  if (!line.trim()) {
    return;
  }
  let req;
  try {
    req = JSON.parse(line);
  } catch (err) {
    reply({ id: null, fatal: "bad request: " + String(err) });
    return;
  }
  try {
    reply({ id: req.id, errors: parseErrors(String(req.path || ""), String(req.text || "")) });
  } catch (err) {
    reply({ id: req.id, fatal: String((err && err.stack) || err).slice(0, 2000) });
  }
});
rl.on("close", () => process.exit(0));
reply({ id: "ready", version: ts.version });
