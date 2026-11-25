// TypeScript compiler-API helpers for the second-corpus evidence checks (called by checks_ts.py).
// What it checks: syntax or types of the files given, with the TypeScript module given; it reads those files
// and the tsconfig, and writes nothing (it prints one JSON object on stdout).
//   node ts_api.js <typescript module dir> parse <file.tsx>
//       syntactic diagnostics of one file (parser only, no program, no types)
//   node ts_api.js <typescript module dir> vartype <tsconfig.json> <file> <line1> <name>
//       type of the variable <name> declared on 1-based line <line1> of <file>, in a fresh program
//   node ts_api.js <typescript module dir> narrowany
//       type of `typeof v.value === 'string' ? v.value : ''` when v is any (a fresh in-memory program)
// Run line: node scripts/paper/evidence/second_corpus/ts_api.js <ts dir> <command> [args]
"use strict";
const path = require("path");
const fs = require("fs");
const ts = require(path.resolve(process.argv[2]));
const cmd = process.argv[3];

function diagText(d) {
  const msg = ts.flattenDiagnosticMessageText(d.messageText, " ");
  let where = "";
  if (d.file && d.start !== undefined) {
    const p = d.file.getLineAndCharacterOfPosition(d.start);
    where = `${p.line + 1}:${p.character + 1} `;
  }
  return `${where}TS${d.code} ${msg}`;
}

if (cmd === "parse") {
  const file = process.argv[4];
  const sf = ts.createSourceFile(file, fs.readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true,
    file.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  console.log(JSON.stringify({ version: ts.version, parseDiagnostics: sf.parseDiagnostics.map(diagText) }));
} else if (cmd === "vartype") {
  const [tsconfig, file, line1, name] = process.argv.slice(4);
  const cfg = ts.getParsedCommandLineOfConfigFile(path.resolve(tsconfig), {}, {
    ...ts.sys, onUnRecoverableConfigFileDiagnostic: () => {} });
  const program = ts.createProgram({ rootNames: cfg.fileNames, options: cfg.options });
  const checker = program.getTypeChecker();
  const sf = program.getSourceFile(path.resolve(file));
  let found = null;
  function visit(n) {
    if (ts.isVariableDeclaration(n) && n.name.getText(sf) === name &&
        sf.getLineAndCharacterOfPosition(n.name.getStart(sf)).line + 1 === Number(line1)) found = n;
    ts.forEachChild(n, visit);
  }
  if (sf) visit(sf);
  const out = { version: ts.version, inProgram: !!sf, found: !!found };
  if (found) {
    out.type = checker.typeToString(checker.getTypeAtLocation(found.name));
    out.initializer = found.initializer ? found.initializer.getText(sf).replace(/\s+/g, " ") : null;
    const acc = found.initializer && found.initializer.whenTrue;
    if (acc && ts.isPropertyAccessExpression(acc)) {
      out.objectType = checker.typeToString(checker.getTypeAtLocation(acc.expression));
      out.declaredPropertyType = checker.typeToString(checker.getTypeAtLocation(acc));
    }
    out.fileDiagnostics = ts.getPreEmitDiagnostics(program, sf).map(diagText).slice(0, 10);
  }
  console.log(JSON.stringify(out));
} else if (cmd === "narrowany") {
  const text = "declare const v: any;\nconst m = typeof v.value === 'string' ? v.value : '';\n";
  const name = "/virtual/narrow.ts";
  const host = ts.createCompilerHost({ strict: true, noEmit: true });
  const orig = host.getSourceFile.bind(host);
  host.getSourceFile = (f, lang) => f === name ? ts.createSourceFile(f, text, lang) : orig(f, lang);
  host.fileExists = ((fe) => (f) => f === name || fe(f))(host.fileExists.bind(host));
  const program = ts.createProgram([name], { strict: true, noEmit: true }, host);
  const sf = program.getSourceFile(name);
  const decl = sf.statements[1].declarationList.declarations[0];
  console.log(JSON.stringify({ version: ts.version, source: text,
    type: program.getTypeChecker().typeToString(program.getTypeChecker().getTypeAtLocation(decl.name)) }));
} else {
  console.error("unknown command " + cmd);
  process.exit(2);
}
