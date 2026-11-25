"""One local HTML page on which the author judges a campaign's finding groups.

For every group of data/lsptest/runs/<campaign>/triage/triage.json the page shows the report's
title, relation and minimal steps, a line diff between the expected and the actual answer (from
the group's repro.json; red = expected, green = actual), the evidence and reduction notes, the
possibly related issues, the result of the year-old version sweep when it exists, and the replay
command, with links to the full report. Groups are numbered 1..N in the order the triage guide
suggests (R0, R2, R4, R3, R6, R5, R1; then server, then gid). Each has three buttons (bug /
legitimate / tool-artifact), a clear link and a note field; nothing is pre-selected and the page
suggests no answer. Verdicts already in decisions.csv show as judged. Clicks stay in the browser
(localStorage) and leave as JSON through "复制结果" / "下载结果文件"; scripts/paper/
import_judgements.py writes that JSON into decisions.csv. The judging kit below (buttons, sticky
progress bar, state and export script, diff) is shared with scripts/paper/detection_workbook.py.

--rater2 writes workbook_rater2.html instead: the page for a second, independent rater, which shows
no trace of the author's judgements, shuffles the groups with a fixed seed and keeps its choices
apart from this page's (scripts/paper/rater2_workbook.py; import with scripts/paper/import_rater2.py).

Run line: python3 scripts/paper/triage_workbook.py [main_v1]
Run line (second rater): python3 scripts/paper/triage_workbook.py main_v1 --rater2
"""

from __future__ import annotations

import csv
import difflib
import html
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from import_judgements import CHOICES

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ORDER = ("r0_crash", "r2_handles", "r4_edits", "r3_routes", "r6_crossimpl", "r5_transforms", "r1_history")
RELATION = {"r0_crash": "R0 崩溃", "r1_history": "R1 历史无关", "r2_handles": "R2 句柄有效", "r3_routes": "R3 路径等价",
            "r4_edits": "R4 编辑有效", "r5_transforms": "R5 语义不变变换", "r6_crossimpl": "R6 TS6 对 TS7"}
LABELS: Dict[str, Dict[str, str]] = {
    "triage": {"bug": "是 bug", "legitimate": "不算问题：两边都说得通", "tool-artifact": "工具自己的问题"},
    "detection": {"yes": "就是这个 bug", "no": "不是这个 bug", "partial": "部分是"}}
MAX_DIFF_LINES = 90

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ judging kit (shared with detection_workbook.py)
CSS = """
body{font-family:-apple-system,"PingFang SC",sans-serif;max-width:1100px;margin:0 auto;padding:0 16px 48px;line-height:1.55;color:#222;background:#fff}
h1{font-size:1.5em;border-bottom:2px solid #332288;margin-top:20px} h2{margin-top:1.6em;color:#332288}
details{border:1px solid #ccc;border-radius:6px;margin:6px 0;padding:4px 10px;scroll-margin-top:80px} summary{cursor:pointer}
pre{background:#f6f6f6;padding:8px;overflow-x:auto;font-size:12px;white-space:pre-wrap}
.diff .add{background:#e6f4ea;color:#0b5c1a} .diff .del{background:#fce8e6;color:#8a1c12} .diff .hunk{color:#555}
.state{padding:1px 6px;border-radius:4px;font-size:12px} .judged{background:#117733;color:#fff} .open{background:#DDCC77}
.num{font-weight:bold;display:inline-block;min-width:2.4em} .differ{color:#882255;font-size:12px}
.muted{color:#666;font-size:.9em} table{border-collapse:collapse} td,th{border:1px solid #bbb;padding:3px 8px}
.bar{position:sticky;top:0;z-index:10;background:#fff;border-bottom:2px solid #332288;padding:8px 0;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.bar button{font-size:15px;padding:6px 14px;border:1px solid #332288;border-radius:6px;background:#fff;color:#332288;cursor:pointer}
#progress{font-weight:bold;margin-right:6px} #message{color:#117733} #storage-warning{color:#882255}
#export-box{border:2px solid #882255;border-radius:6px;padding:8px;margin:8px 0} #export-box textarea{width:100%;height:180px;box-sizing:border-box}
.judge{border-top:1px dashed #999;margin-top:14px;padding:10px 0 4px} .judge .q{font-weight:bold;margin:0 0 6px}
button.choice{font-size:16px;min-width:180px;padding:10px 14px;margin:4px 8px 4px 0;border:2px solid #888;border-radius:8px;background:#fff;color:#222;cursor:pointer}
button.choice small{display:block;font-size:12px;color:#555;font-weight:normal}
button.choice.chosen{background:#332288;border-color:#332288;color:#fff} button.choice.chosen small{color:#eee}
button.clear{border:none;background:none;color:#666;text-decoration:underline;cursor:pointer;font-size:13px}
textarea.note{display:block;width:100%;box-sizing:border-box;margin-top:6px;font:inherit;font-size:14px}
"""
BAR = """<div class="bar"><span id="progress">已判断 {judged} / {n}</span>
<button type="button" id="copy">复制结果</button><button type="button" id="download">下载结果文件</button>
<button type="button" id="next">下一条未判断</button><span id="message"></span>
<span id="storage-warning" hidden>这个浏览器不让本页保存进度：关掉页面前请先点「复制结果」。</span></div>
<div id="export-box" hidden><p id="export-why"></p><textarea id="export-text" readonly></textarea></div>
"""
SCRIPT = r"""(function () {
  "use strict";
  var cfg = JSON.parse(document.getElementById("judge-config").textContent);
  var items = Array.prototype.slice.call(document.querySelectorAll("details.item"));
  var state = {}, local = {}, current = -1, canStore = true, lastMark = Date.now();
  function $(id) { return document.getElementById(id); }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }
  function idOf(item) { return item.getAttribute("data-id"); }
  function clean(s) {
    s = s || {};
    return {choice: cfg.choices.indexOf(s.choice) >= 0 ? s.choice : "", note: typeof s.note === "string" ? s.note : "",
            minutes: typeof s.minutes === "number" && s.minutes > 0 ? Math.round(s.minutes * 10) / 10 : 0};
  }
  function load() {
    var raw = null, data = null;
    try { raw = window.localStorage.getItem(cfg.key); } catch (e) { canStore = false; }
    try { data = raw ? JSON.parse(raw) : null; } catch (e) { data = null; }
    local = data && data.items && typeof data.items === "object" ? data.items : {};
  }
  function save() {
    try { window.localStorage.setItem(cfg.key, JSON.stringify({version: 1, items: local})); canStore = true; }
    catch (e) { canStore = false; }
    $("storage-warning").hidden = canStore;
  }
  function render(item) {
    var s = state[idOf(item)], file = (cfg.seed[idOf(item)] || {}).file || "", note = item.querySelector("textarea.note");
    each(item.querySelectorAll("button.choice"), function (b) {
      var on = b.getAttribute("data-choice") === s.choice;
      b.classList.toggle("chosen", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var badge = item.querySelector(".state");
    badge.textContent = s.choice ? "已判断：" + s.choice : "未判断";
    badge.className = "state " + (s.choice ? "judged" : "open");
    item.querySelector(".differ").textContent = file && file !== s.choice ? "（文件里记的是 " + file + "）" : "";
    if (note.value !== s.note && document.activeElement !== note) { note.value = s.note; }
  }
  function progress() {
    var done = items.filter(function (item) { return state[idOf(item)].choice; }).length;
    $("progress").textContent = "已判断 " + done + " / " + items.length;
  }
  function touch(item) { local[idOf(item)] = state[idOf(item)]; save(); render(item); progress(); }
  function say(text) { $("message").textContent = text; }
  function exportText() {
    var out = [];
    items.forEach(function (item) {
      var s = state[idOf(item)], note = s.note.trim();
      if (s.choice || note) {
        out.push(JSON.stringify({n: Number(item.getAttribute("data-n")), id: idOf(item), choice: s.choice, note: note,
                                 minutes: s.minutes}));
      }
    });
    var head = JSON.stringify({page: cfg.page, campaign: cfg.campaign, exported_at: new Date().toISOString()});
    $("export-text").value = head.slice(0, -1) + ',"items":[\n' + out.join(",\n") + "\n]}\n";
    return {text: $("export-text").value, count: out.length};
  }
  function manual(why) {
    $("export-why").textContent = why; $("export-box").hidden = false;
    $("export-box").scrollIntoView({block: "center"}); $("export-text").focus(); $("export-text").select();
  }
  load();
  items.forEach(function (item, i) {
    var id = idOf(item);
    state[id] = clean(Object.prototype.hasOwnProperty.call(local, id) ? local[id] : cfg.seed[id]);
    item.addEventListener("toggle", function () {
      if (item.open) { current = i; }
    });
    each(item.querySelectorAll("button.choice"), function (b) {
      b.addEventListener("click", function () {
        var s = state[id];
        s.choice = b.getAttribute("data-choice"); current = i;
        // time since the previous judgement on this page (or since the page opened), capped at 30 min for breaks
        var now = Date.now();
        if (!s.minutes) { s.minutes = Math.max(0.1, Math.round(Math.min(1800, (now - lastMark) / 1000) / 6) / 10); }
        lastMark = now;
        touch(item);
      });
    });
    item.querySelector("button.clear").addEventListener("click", function () { state[id].choice = ""; touch(item); });
    item.querySelector("textarea.note").addEventListener("input", function (e) { state[id].note = e.target.value; touch(item); });
    render(item);
  });
  progress();
  $("storage-warning").hidden = canStore;
  $("copy").addEventListener("click", function () {
    var ex = exportText();
    function ok() { say("已复制 " + ex.count + " 条结果，请粘贴到对话里发给我。"); }
    function legacy() {
      var ta = document.createElement("textarea"), done = false;
      ta.value = ex.text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.top = "-1000px";
      document.body.appendChild(ta); ta.select();
      try { done = document.execCommand("copy"); } catch (e) { done = false; }
      document.body.removeChild(ta);
      if (done) { ok(); } else { manual("浏览器没让自动复制：请点进下面的框，全选（⌘A）后复制（⌘C），再粘贴到对话里。"); }
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(ex.text).then(ok, legacy); return; }
    } catch (e) { /* the fallback below */ }
    legacy();
  });
  $("download").addEventListener("click", function () {
    var ex = exportText(), stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    var name = "judgements-" + cfg.page + "-" + cfg.campaign + "-" + stamp + ".json";
    try {
      var url = URL.createObjectURL(new Blob([ex.text], {type: "application/json"})), a = document.createElement("a");
      a.href = url; a.download = name; document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
      say("已下载 " + name + "（" + ex.count + " 条，在浏览器的下载文件夹里）。");
    } catch (e) { manual("下载没成功：请复制下面框里的内容发给我。"); }
  });
  $("next").addEventListener("click", function () {
    for (var k = 1; k <= items.length; k++) {
      var i = (current + k) % items.length;
      if (!state[idOf(items[i])].choice) {
        if (current >= 0 && current !== i) { items[current].open = false; }
        items[i].open = true; current = i; items[i].scrollIntoView({block: "start"}); say(""); return;
      }
    }
    say("全部都判断过了。");
  });
})();
"""


def seed_entry(page: str, raw: Optional[str], note: Optional[str], minutes: Optional[str] = None) -> Dict[str, Any]:
    """A judgement already in the CSV: a valid choice (else ''), the note, the minutes and the raw cell."""
    file = (raw or "").strip()
    choice = file.lower() if file.lower() in CHOICES[page] else ""
    try:
        mins = max(0, int(round(float(minutes or ""))))
    except (ValueError, OverflowError):
        mins = 0
    return {"choice": choice, "note": (note or "").strip(), "minutes": mins, "file": choice or file}


def summary_head(n: int, seed: Mapping[str, Any]) -> str:
    """Number, judged badge and file note that start an item's summary line."""
    choice, file = seed.get("choice", ""), seed.get("file", "")
    badge = f'<span class="state judged">已判断：{html.escape(choice)}</span>' if choice else \
        '<span class="state open">未判断</span>'
    differ = f"（文件里记的是 {html.escape(file)}）" if file and file != choice else ""
    return f'<b class="num">{n}.</b> {badge}<span class="differ">{differ}</span>'


def judge_block(page: str, question: str, seed: Mapping[str, Any],
                placeholder: str = "备注（可选）：一句理由、unsure、对上号的 issue 链接……") -> str:
    """The three choice buttons (the CSV's choice pressed, none otherwise), the clear link and the note."""
    chosen = seed.get("choice", "")
    buttons = "".join(
        f'<button type="button" class="choice{" chosen" if c == chosen else ""}" data-choice="{c}" '
        f'aria-pressed="{"true" if c == chosen else "false"}"><b>{c}</b><small>{html.escape(label)}</small></button>'
        for c, label in LABELS[page].items())
    return (f'<div class="judge"><p class="q">{html.escape(question)}</p>{buttons}'
            '<button type="button" class="clear">清除</button><textarea class="note" rows="2" '
            f'placeholder="{html.escape(placeholder)}">{html.escape(seed.get("note", ""))}</textarea></div>')


def page_html(page: str, campaign: str, title: str, head: str, content: str,
              seeds: Mapping[str, Mapping[str, Any]], n: int) -> str:
    """The whole page: head text, sticky bar, items, the embedded config (seeds) and the script."""
    config = {"page": page, "campaign": campaign, "key": f"tse2-judging:{page}:{campaign}",
              "choices": list(CHOICES[page]), "seed": {k: dict(v) for k, v in seeds.items()}}
    data = json.dumps(config, ensure_ascii=False, sort_keys=True)
    data = data.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    judged = sum(1 for s in seeds.values() if s.get("choice"))
    return "".join([
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>\n", head,
        BAR.format(judged=judged, n=n), content,
        f'\n<script type="application/json" id="judge-config">{data}</script>\n<script>\n{SCRIPT}</script>\n',
        "</body></html>\n"])


def answer_diff(expected: Any, actual: Any, where: str = "报告") -> List[str]:
    a = json.dumps(expected, indent=1, sort_keys=True, ensure_ascii=False).splitlines()
    b = json.dumps(actual, indent=1, sort_keys=True, ensure_ascii=False).splitlines()
    lines = list(difflib.unified_diff(a, b, "expected", "actual", lineterm="", n=2))
    if len(lines) > MAX_DIFF_LINES:
        lines = lines[:MAX_DIFF_LINES] + [f"……（还有 {len(lines) - MAX_DIFF_LINES} 行差别没显示，完整内容见{where}）"]
    return lines or [f"（两边的答案打印出来一样；差别的形态见{where}）"]


def diff_html(lines: List[str]) -> str:
    out = []
    for line in lines:
        cls = "add" if line.startswith("+") and not line.startswith("+++") else \
              "del" if line.startswith("-") and not line.startswith("---") else "hunk" if line.startswith("@@") else ""
        out.append(f'<span class="{cls}">{html.escape(line)}</span>' if cls else html.escape(line))
    return "<pre class=\"diff\">" + "\n".join(out) + "</pre>"


def load(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ triage page
def sections(text: str) -> Dict[str, str]:
    """Report sections by '## ' heading; the '# ' title under key 'title'."""
    out: Dict[str, str] = {}
    name, buf = "", []
    for line in text.splitlines():
        if line.startswith("# ") and "title" not in out:
            out["title"] = line[2:].strip()
        elif line.startswith("## "):
            out[name] = "\n".join(buf).strip()
            name, buf = line[3:].strip(), []
        else:
            buf.append(line)
    out[name] = "\n".join(buf).strip()
    return out


def section(secs: Mapping[str, str], prefix: str) -> str:
    return next((v for k, v in secs.items() if k.startswith(prefix)), "")


def group_html(n: int, g: Mapping[str, Any], tdir: str, sweep: Mapping[str, Any], seed: Mapping[str, Any]) -> str:
    gid = g["gid"]
    gdir = os.path.join(tdir, gid)
    with open(os.path.join(gdir, "report.md"), "r", encoding="utf-8") as f:
        secs = sections(f.read())
    repro = load(os.path.join(gdir, "repro.json"))
    issues = load(os.path.join(gdir, "issues.json")) if os.path.exists(os.path.join(gdir, "issues.json")) else {}
    kind, oracle, shape = g["signature"].split("|", 2)
    sw = sweep.get(gid)
    sw_text = "未重放（该组没有一年前的版本可比）" if not sw or sw.get("verdict") == "skipped" else \
        f"{sw['verdict']}（{sw['build']['kind']} {sw['build']['version']}，{sw['reproduced']}/{sw['replays']} 次复现）"
    matches = (issues.get("matches") or [])[:5]
    issue_items = "".join(f'<li><a href="{html.escape(m["url"])}" target="_blank" rel="noopener">'
                          f'{html.escape(m["repo"])}#{m["number"]}</a> {html.escape(m["title"])} '
                          f'<span class="muted">({html.escape(m["state"])}, {html.escape(m["created"])})</span></li>'
                          for m in matches) or "<li class=\"muted\">无</li>"
    replay = re.search(r"python3 scripts/lsptest/repro_violation\.py \S+", section(secs, "Reproduce"))
    eid = html.escape(gid)
    return f"""
<details class="item" id="{eid}" data-id="{eid}" data-n="{n}"><summary>{summary_head(n, seed)} <code>{eid}</code> · {html.escape(RELATION.get(oracle, oracle))} · {html.escape(kind)} · 成员 {g['members']} · 步骤 {g.get('ops_before')}→{g.get('ops_after')}</summary>
<div class="body">
<h3>{html.escape(secs.get('title', gid))}</h3>
<p><b>违反的规则</b>：{html.escape(section(secs, 'Relation violated'))}</p>
<p><b>现象</b>：<code>{html.escape(shape)}</code>；历史族/子检查：<code>{html.escape(str(g.get('family')))}</code></p>
<h4>最少复现步骤</h4><pre>{html.escape(section(secs, 'Minimal steps'))}</pre>
<h4>预期与实际的差别（红 = 预期，参照会话的答案；绿 = 实际，被测会话的答案）</h4>{diff_html(answer_diff(repro.get('expected'), repro.get('actual')))}
<h4>证据与缩减</h4><pre>{html.escape(section(secs, 'Evidence and reduction'))}</pre>
<h4>一年前版本上的重放</h4><p>{html.escape(sw_text)}</p>
<h4>可能相关的已有 issue（关键词搜索结果，要你核对）</h4><ul>{issue_items}</ul>
<p class="muted">完整报告：<a href="{eid}/report.md" target="_blank" rel="noopener">{eid}/report.md</a> ·
复现命令（在项目根目录运行）：<code>{html.escape(replay.group(0) if replay else '-')}</code></p>
{judge_block("triage", "你的判断：实际（被测会话）这边的答案错了吗？", seed)}
</div></details>"""


INTRO = """<h1>甄别工作台：{campaign}（{n} 组）</h1>
<p>每组只回答一个问题：<b>实际（被测会话）这边的答案错了吗？</b>展开一组，看完后点一个按钮：<b>bug</b>（是 bug：实际这边错了）、<b>legitimate</b>（不算问题：两边都说得通）、<b>tool-artifact</b>（工具自己的问题：差别是测试工具造成的）。点错了直接点另一个，或点「清除」。拿不准就先运行该组的复现命令；仍拿不准就点 legitimate，并在备注里写 unsure。做完一批就点「复制结果」，把内容粘贴到对话里发给我；随时可以停，下次打开会接着上次的进度。</p>
<p class="muted">差别里红色是预期（参照会话的答案），绿色是实际（被测会话的答案）。完整说明见 <code>plan/triage_guide_zh.html</code>。</p>
"""


def read_decisions(path: str) -> Dict[str, Dict[str, Any]]:
    """group -> seed for the rows of decisions.csv that have a verdict or a note."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["group"]: seed_entry("triage", r.get("verdict"), r.get("maintainer_response"), r.get("minutes_spent"))
            for r in rows if (r.get("verdict") or "").strip() or (r.get("maintainer_response") or "").strip()}


def ordered(groups: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    rank = {o: i for i, o in enumerate(ORDER)}
    return sorted(groups, key=lambda g: (rank.get(g["signature"].split("|")[1], 99), g["signature"].split("|")[0],
                                         g["gid"]))


def build(campaign: str, root: Optional[str] = None, decisions: Optional[str] = None) -> Tuple[str, int, int]:
    """The page for a campaign: (html, number of groups, groups judged in the CSV). Nothing is written."""
    root = root or os.path.join(REPO, "data", "lsptest", "runs", campaign)
    tdir = os.path.join(root, "triage")
    groups = ordered(load(os.path.join(tdir, "triage.json"))["groups"])
    seeds = read_decisions(decisions or os.path.join(tdir, "decisions.csv"))
    seeds = {g["gid"]: seeds[g["gid"]] for g in groups if g["gid"] in seeds}
    sweep: Dict[str, Any] = {}
    sweep_path = os.path.join(root, "sweep", "older-2025", "results.jsonl")
    if os.path.exists(sweep_path):
        with open(sweep_path, "r", encoding="utf-8") as f:
            sweep = {r["gid"]: r for r in (json.loads(line) for line in f if line.strip())}
    counts: Dict[str, Dict[str, int]] = {}
    for g in groups:
        kind, oracle = g["signature"].split("|")[:2]
        counts.setdefault(oracle, {})[kind] = counts.setdefault(oracle, {}).get(kind, 0) + 1
    kinds = sorted({k for c in counts.values() for k in c})
    table = "<table><tr><th>规则</th>" + "".join(f"<th>{html.escape(k)}</th>" for k in kinds) + "<th>合计</th></tr>" + "".join(
        f"<tr><td>{html.escape(RELATION.get(o, o))}</td>" + "".join(f"<td>{counts[o].get(k, 0) or ''}</td>" for k in kinds)
        + f"<td>{sum(counts[o].values())}</td></tr>" for o in ORDER if o in counts) + "</table>"
    body, current = [table], ""
    for n, g in enumerate(groups, 1):
        oracle = g["signature"].split("|")[1]
        if oracle != current:
            body.append(f"<h2>{html.escape(RELATION.get(oracle, oracle))}</h2>")
            current = oracle
        body.append(group_html(n, g, tdir, sweep, seeds.get(g["gid"], {})))
    head = INTRO.format(campaign=html.escape(campaign), n=len(groups))
    page = page_html("triage", campaign, f"甄别工作台 {campaign}", head, "\n".join(body), seeds, len(groups))
    return page, len(groups), sum(1 for s in seeds.values() if s["choice"])


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    rater2 = "--rater2" in args
    args = [a for a in args if a != "--rater2"]
    campaign = args[0] if args else "main_v1"
    if rater2:
        import rater2_workbook  # imported here: it builds on this module
        return rater2_workbook.main_rater2(campaign)
    page, n, judged = build(campaign)
    out = os.path.join(REPO, "data", "lsptest", "runs", campaign, "triage", "workbook.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {os.path.relpath(out, REPO)}: {n} groups, {judged} judged in decisions.csv, {len(page.encode()) // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
