// Asks VS Code's own definition provider (served by the rust-analyzer extension) at two positions until the
// answers stay the same for a minute, then writes them to the output file and lets VS Code exit.
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));

function loc(l) {
  const uri = l.targetUri || l.uri;
  const r = l.targetRange || l.range;
  return { file: uri.fsPath, range: [r.start.line, r.start.character, r.end.line, r.end.character] };
}

async function definition(rel, line, ch) {
  const uri = vscode.Uri.file(path.join(cfg.ws, rel));
  const doc = await vscode.workspace.openTextDocument(uri);
  await vscode.window.showTextDocument(doc, { preview: false });
  const res = await vscode.commands.executeCommand('vscode.executeDefinitionProvider', uri, new vscode.Position(line, ch));
  return (res || []).map(loc);
}

exports.run = async function () {
  const t0 = Date.now();
  const ext = vscode.extensions.getExtension('rust-lang.rust-analyzer');
  await ext.activate();
  const history = [];
  let last = null, stable = 0, a = [], b = [];
  while (Date.now() - t0 < cfg.maxSeconds * 1000) {
    try {
      a = await definition(cfg.refFile, cfg.refLine, cfg.refChar);
      b = await definition(cfg.file, cfg.line, cfg.char);
    } catch (e) {
      history.push({ t: (Date.now() - t0) / 1000, error: String(e) });
    }
    const key = JSON.stringify([a, b]);
    history.push({ t: (Date.now() - t0) / 1000, n_reference_route: a.length, n_tested_route: b.length });
    stable = (a.length && b.length && key === last) ? stable + 1 : 0;
    last = key;
    if (stable >= cfg.stablePolls) break;
    await new Promise((r) => setTimeout(r, cfg.pollMs));
  }
  fs.writeFileSync(cfg.out, JSON.stringify({
    vscode: vscode.version, extension: ext.packageJSON.version, stable_polls: stable,
    elapsed_s: (Date.now() - t0) / 1000, reference_route: a, tested_route: b, history,
  }, null, 1));
};
