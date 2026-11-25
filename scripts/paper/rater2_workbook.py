"""The second rater's judging page for a campaign's finding groups, and its leak check.

Built by `triage_workbook.py --rater2`. The page shows, for every group of data/lsptest/runs/<campaign>/
triage/triage.json, only evidence the tool produced before any judgement: the report's title, server and
project, the relation it violates, the minimal steps, the line diff between expected and actual answer
(from repro.json), the evidence and reduction notes, the year-old version sweep and the full report text
without its keyword search for possibly related issues. It reads nothing the author wrote while judging
(decisions.csv, verdict_reasons.csv, exception_classes.csv, root_causes.csv, judgements/, upstream/).
The groups appear in a random order drawn with a fixed seed (shown on the page). The buttons (bug /
legitimate / tool-artifact), an optional exception-class menu (L1-L7 for legitimate, A1-A4 for
tool-artifact) and a note field are drawn by the page script, so nothing is pre-selected. The choices stay
in the browser under their own localStorage key and leave as rater2_judgements.json ("下载结果文件") or
through the clipboard; scripts/paper/import_rater2.py writes that file into rater2_decisions.csv.

leak_check() searches the written page for everything the author's judging produced (reasons, notes,
root-cause ids C1-C11, upstream issue links, the author page's state strings) and counts the verdict words
and class codes outside the page's fixed text; main_rater2() prints the result and exits 1 on any hit.

Run line: python3 scripts/paper/triage_workbook.py main_v1 --rater2
"""

from __future__ import annotations

import csv
import datetime as dt
import glob
import html
import json
import logging
import os
import random
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import triage_workbook as tw

ORDER_SEED = 20261117
PAGE = "triage-rater2"
EXPORT_NAME = "rater2_judgements.json"
OUT_NAME = "workbook_rater2.html"
CHOICES: Tuple[str, ...] = ("bug", "legitimate", "tool-artifact")
LABELS: Dict[str, str] = {"bug": "是 bug", "legitimate": "不算问题：两边都说得通", "tool-artifact": "工具自己的问题"}
CLASSES: Dict[str, List[Tuple[str, str]]] = {
    "legitimate": [
        ("L1", "同样的内容，只是顺序或打印方式不同"),
        ("L2", "差别只在项目以外的位置（已安装的库、标准库的存根文件等）"),
        ("L3", "服务器文档写明在时间预算或后台分析下尽力而为的结果"),
        ("L4", "协议不要求两条路径一致，差别来自看得见的设计"),
        ("L5", "答案按设计取决于行的排布"),
        ("L6", "TypeScript 6 与 TypeScript 7 之间的差别"),
        ("L7", "其他")],
    "tool-artifact": [
        ("A1", "工具故意埋入的错误（种子变异）带来的副作用"),
        ("A2", "工具给的输入让这个比较不成立"),
        ("A3", "时机（服务器还没准备好之类）"),
        ("A4", "其他")]}
QUESTION = "按论文 VI-A 的书面标准，这一组属于哪一类？"
PLACEHOLDER = "备注：一句理由；拿不准就写“不确定”，并写下你倾向的理由"
CRITERIA_EN = (
    "A bug when the tested answer is wrong for the language or the protocol and no documented behavior "
    "explains it, legitimate when both answers are defensible because the protocol leaves the behavior to "
    "the implementation or the difference is documented, and an artifact when the difference comes from "
    "the harness's inputs or rules. For R1, which compares a session with a fresh session on identical "
    "content, any difference in an answer about project files counts as a bug, whichever session is wrong, "
    "unless the harness caused it or the answers differ only in order or printing, only in locations outside "
    "the project, or in a "
    "result the server documents as best effort under a time budget.")
ISSUES_HEAD = "## Possibly related issues"
DRAFT_RE = re.compile(r"Draft for the author \(not filed\)\.\s*")
VERDICT_WORDS: Dict[str, str] = {"bug": r"\bbugs?\b", "legitimate": r"\blegitimate\b", "artifact": r"artifact"}
CLASS_RE = r"(?<![A-Za-z0-9_])[LA][1-7](?![0-9A-Za-z_])"
CAUSE_RE = r"(?<![A-Za-z0-9_])C(?:1[01]|[1-9])(?![0-9A-Za-z_])"
AUTHOR_PAGE_MARKS = ("已判断：", "文件里记的是", "judge-config", "tse2-judging:", "maintainer_response", "minutes_spent",
                     "decisions.csv", "verdict_reasons", "exception_classes", "root_causes", "recheck", "复审",
                     "改判", "一致性校正", "consistency pass", "first pass", "triage_guide_zh", "upstream/")

logger = logging.getLogger(__name__)

EXTRA_CSS = """
.done{background:#117733;color:#fff} .cls-label{display:inline-block;margin:6px 12px 0 0;font-size:14px}
select.cls{font-size:14px;padding:3px} .legend td:first-child{white-space:nowrap;font-weight:bold}
.criteria{border-left:4px solid #332288;background:#f4f3fa;padding:8px 12px;margin:10px 0}
"""
BAR = """<div class="bar"><span id="progress">你已完成 0 / {n}</span>
<button type="button" id="copy">复制结果</button><button type="button" id="download">下载结果文件</button>
<button type="button" id="next">下一条未完成</button>
<label class="restore">从结果文件恢复：<input type="file" id="restore" accept=".json,application/json"></label>
<span id="message"></span>
<span id="storage-warning" hidden>这个浏览器不让本页保存进度：关掉页面前请先点「下载结果文件」。</span></div>
<div id="export-box" hidden><p id="export-why"></p><textarea id="export-text" readonly></textarea></div>
"""
SCRIPT = r"""(function () {
  "use strict";
  var cfg = JSON.parse(document.getElementById("rater2-config").textContent);
  var items = Array.prototype.slice.call(document.querySelectorAll("details.item"));
  var state = {}, current = -1, canStore = true;
  function $(id) { return document.getElementById(id); }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }
  function idOf(item) { return item.getAttribute("data-id"); }
  function classesFor(verdict) { return cfg.classes[verdict] || []; }
  function classOk(verdict, cls) { return classesFor(verdict).some(function (c) { return c[0] === cls; }); }
  function clean(s) {
    s = s && typeof s === "object" ? s : {};
    var v = cfg.choices.indexOf(s.verdict) >= 0 ? s.verdict : "";
    return {verdict: v, cls: classOk(v, s.cls) ? s.cls : "", note: typeof s.note === "string" ? s.note : "",
            judged_at: v && typeof s.judged_at === "string" ? s.judged_at : ""};
  }
  function load() {
    var raw = null, data = null;
    try { raw = window.localStorage.getItem(cfg.key); } catch (e) { canStore = false; }
    try { data = raw ? JSON.parse(raw) : null; } catch (e) { data = null; }
    return data && data.items && typeof data.items === "object" ? data.items : {};
  }
  function save() {
    var out = {};
    items.forEach(function (item) {
      var s = state[idOf(item)];
      if (s.verdict || s.cls || s.note) { out[idOf(item)] = s; }
    });
    try { window.localStorage.setItem(cfg.key, JSON.stringify({version: 1, seed: cfg.seed, items: out})); canStore = true; }
    catch (e) { canStore = false; }
    $("storage-warning").hidden = canStore;
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) { e.className = cls; }
    if (text) { e.textContent = text; }
    return e;
  }
  function build(item) {
    var box = item.querySelector(".judge");
    box.appendChild(el("p", "q", cfg.question));
    cfg.choices.forEach(function (c) {
      var b = el("button", "choice");
      b.type = "button"; b.setAttribute("data-choice", c); b.setAttribute("aria-pressed", "false");
      b.appendChild(el("b", "", c)); b.appendChild(el("small", "", cfg.labels[c]));
      box.appendChild(b);
    });
    var clear = el("button", "clear", "清除选择");
    clear.type = "button"; box.appendChild(clear);
    var lab = el("label", "cls-label", "例外类别（可选）：");
    lab.appendChild(el("select", "cls")); box.appendChild(lab);
    var note = el("textarea", "note");
    note.rows = 2; note.placeholder = cfg.placeholder; box.appendChild(note);
  }
  function fillSelect(sel, s) {
    var list = classesFor(s.verdict);
    while (sel.firstChild) { sel.removeChild(sel.firstChild); }
    var none = el("option", "", list.length ? "（不选）" : "（选了 legitimate 或 tool-artifact 之后才能选）");
    none.value = ""; sel.appendChild(none);
    list.forEach(function (c) { var o = el("option", "", c[0] + "  " + c[1]); o.value = c[0]; sel.appendChild(o); });
    sel.disabled = !list.length; sel.value = s.cls;
  }
  function render(item) {
    var s = state[idOf(item)], note = item.querySelector("textarea.note");
    each(item.querySelectorAll("button.choice"), function (b) {
      var on = b.getAttribute("data-choice") === s.verdict;
      b.classList.toggle("chosen", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    fillSelect(item.querySelector("select.cls"), s);
    var badge = item.querySelector(".state");
    badge.textContent = s.verdict ? "你选了 " + s.verdict + (s.cls ? " / " + s.cls : "") : "未选";
    badge.className = "state " + (s.verdict ? "done" : "open");
    if (note.value !== s.note && document.activeElement !== note) { note.value = s.note; }
  }
  function progress() {
    var done = items.filter(function (item) { return state[idOf(item)].verdict; }).length;
    $("progress").textContent = "你已完成 " + done + " / " + items.length;
  }
  function touch(item) { save(); render(item); progress(); }
  function say(text) { $("message").textContent = text; }
  function exportText() {
    var out = [];
    items.forEach(function (item) {
      var s = state[idOf(item)], note = s.note.trim();
      if (s.verdict || s.cls || note) {
        out.push(JSON.stringify({n: Number(item.getAttribute("data-n")), id: idOf(item), verdict: s.verdict,
                                 "class": s.cls, note: note, judged_at: s.judged_at}));
      }
    });
    var head = JSON.stringify({page: cfg.page, campaign: cfg.campaign, order_seed: cfg.seed,
                               exported_at: new Date().toISOString()});
    $("export-text").value = head.slice(0, -1) + ',"items":[\n' + out.join(",\n") + "\n]}\n";
    return {text: $("export-text").value, count: out.length};
  }
  function manual(why) {
    $("export-why").textContent = why; $("export-box").hidden = false;
    $("export-box").scrollIntoView({block: "center"}); $("export-text").focus(); $("export-text").select();
  }
  var stored = load();
  items.forEach(function (item, i) {
    var id = idOf(item);
    build(item);
    state[id] = clean(Object.prototype.hasOwnProperty.call(stored, id) ? stored[id] : null);
    item.addEventListener("toggle", function () { if (item.open) { current = i; } });
    each(item.querySelectorAll("button.choice"), function (b) {
      b.addEventListener("click", function () {
        var s = state[id], v = b.getAttribute("data-choice");
        if (s.verdict !== v) { s.verdict = v; s.judged_at = new Date().toISOString(); }
        if (!classOk(v, s.cls)) { s.cls = ""; }
        current = i; touch(item);
      });
    });
    item.querySelector("button.clear").addEventListener("click", function () {
      var s = state[id]; s.verdict = ""; s.cls = ""; s.judged_at = ""; touch(item);
    });
    item.querySelector("select.cls").addEventListener("change", function (e) {
      state[id].cls = classOk(state[id].verdict, e.target.value) ? e.target.value : ""; touch(item);
    });
    item.querySelector("textarea.note").addEventListener("input", function (e) { state[id].note = e.target.value; save(); });
    render(item);
  });
  progress();
  $("storage-warning").hidden = canStore;
  $("copy").addEventListener("click", function () {
    var ex = exportText();
    function ok() { say("已复制 " + ex.count + " 条结果。"); }
    function legacy() {
      var ta = document.createElement("textarea"), done = false;
      ta.value = ex.text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.top = "-1000px";
      document.body.appendChild(ta); ta.select();
      try { done = document.execCommand("copy"); } catch (e) { done = false; }
      document.body.removeChild(ta);
      if (done) { ok(); } else { manual("浏览器没让自动复制：请点进下面的框，全选后复制。"); }
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(ex.text).then(ok, legacy); return; }
    } catch (e) { /* the fallback below */ }
    legacy();
  });
  $("download").addEventListener("click", function () {
    var ex = exportText();
    try {
      var url = URL.createObjectURL(new Blob([ex.text], {type: "application/json"})), a = document.createElement("a");
      a.href = url; a.download = cfg.file; document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
      say("已下载 " + cfg.file + "（" + ex.count + " 条，在浏览器的下载文件夹里）。");
    } catch (e) { manual("下载没成功：请复制下面框里的全部内容，存成文本文件发出。"); }
  });
  $("restore").addEventListener("change", function (e) {
    var file = e.target.files && e.target.files[0];
    if (!file) { return; }
    var reader = new FileReader();
    reader.onload = function () {
      var data = null, n = 0;
      try { data = JSON.parse(String(reader.result)); } catch (err) { data = null; }
      if (!data || data.page !== cfg.page || data.campaign !== cfg.campaign || !Array.isArray(data.items)) {
        say("这个文件不是本页导出的结果文件，没有恢复。"); e.target.value = ""; return;
      }
      var known = data.items.filter(function (it) { return it && Object.prototype.hasOwnProperty.call(state, it.id); });
      if (!window.confirm("用文件里的 " + known.length + " 条结果覆盖本页同一组的选择？其他组不变。")) { e.target.value = ""; return; }
      known.forEach(function (it) {
        state[it.id] = clean({verdict: it.verdict, cls: it["class"], note: it.note, judged_at: it.judged_at}); n += 1;
      });
      save(); items.forEach(render); progress(); say("已从文件恢复 " + n + " 条。"); e.target.value = "";
    };
    reader.readAsText(file, "utf-8");
  });
  $("next").addEventListener("click", function () {
    for (var k = 1; k <= items.length; k++) {
      var i = (current + k) % items.length;
      if (!state[idOf(items[i])].verdict) {
        if (current >= 0 && current !== i) { items[current].open = false; }
        items[i].open = true; current = i; items[i].scrollIntoView({block: "start"}); say(""); return;
      }
    }
    say("全部都选过了。");
  });
})();
"""


# ------------------------------------------------------------------ page
def shuffled(gids: Iterable[str], seed: int = ORDER_SEED) -> List[str]:
    """The group ids sorted by name, then shuffled with random.Random(seed): the same order on every build."""
    order = sorted(gids)
    random.Random(seed).shuffle(order)
    return order


def neutral_report(text: str) -> str:
    """report.md without the 'Draft for the author' remark and without the keyword search for related issues."""
    out: List[str] = []
    skipping = False
    for line in text.splitlines():
        if line.startswith("## "):
            skipping = line.startswith(ISSUES_HEAD)
        if not skipping:
            out.append(DRAFT_RE.sub("", line))
    return "\n".join(out).strip() + "\n"


def sweep_text(sw: Optional[Mapping[str, Any]]) -> str:
    if not sw or sw.get("verdict") == "skipped":
        return "未重放（该组没有一年前的版本可比）"
    return f"{sw['verdict']}（{sw['build']['kind']} {sw['build']['version']}，{sw['reproduced']}/{sw['replays']} 次复现）"


def group_block(n: int, g: Mapping[str, Any], tdir: str, sweep: Mapping[str, Any]) -> str:
    """One group: neutral evidence only, and an empty judging box that the page script fills."""
    gid = g["gid"]
    gdir = os.path.join(tdir, gid)
    with open(os.path.join(gdir, "report.md"), "r", encoding="utf-8") as f:
        report = neutral_report(f.read())
    secs = tw.sections(report)
    repro = tw.load(os.path.join(gdir, "repro.json"))
    kind, oracle, shape = g["signature"].split("|", 2)
    replay = re.search(r"python3 scripts/lsptest/repro_violation\.py \S+", tw.section(secs, "Reproduce"))
    eid = html.escape(gid)
    return f"""
<details class="item" id="{eid}" data-id="{eid}" data-n="{n}"><summary><b class="num">{n}.</b> <span class="state open">未选</span> <code>{eid}</code> · {html.escape(tw.RELATION.get(oracle, oracle))} · {html.escape(kind)} · 成员 {g['members']} · 步骤 {g.get('ops_before')}→{g.get('ops_after')}</summary>
<div class="body">
<h3>{html.escape(secs.get('title', gid))}</h3>
<p><b>服务器与项目</b>：</p><pre>{html.escape(tw.section(secs, 'Server'))}</pre>
<p><b>违反的规则</b>：{html.escape(tw.section(secs, 'Relation violated'))}</p>
<p><b>现象</b>：<code>{html.escape(shape)}</code>；生成器族/子检查：<code>{html.escape(str(g.get('family')))}</code></p>
<h4>最少复现步骤</h4><pre>{html.escape(tw.section(secs, 'Minimal steps'))}</pre>
<h4>预期与实际的差别（红 = 预期，参照会话的答案；绿 = 实际，被测会话的答案）</h4>{tw.diff_html(tw.answer_diff(repro.get('expected'), repro.get('actual'), '下面的完整报告'))}
<h4>证据与缩减</h4><pre>{html.escape(tw.section(secs, 'Evidence and reduction'))}</pre>
<h4>一年前版本上的重放</h4><p>{html.escape(sweep_text(sweep.get(gid)))}</p>
<details class="report"><summary>完整报告（英文原文：项目文件片段、环境、服务器日志）</summary><pre>{html.escape(report)}</pre></details>
<p class="muted">复现命令（需要项目代码和服务器，判断时不必运行）：<code>{html.escape(replay.group(0) if replay else '-')}</code></p>
<div class="judge" data-id="{eid}"></div>
</div></details>"""


def intro(campaign: str, n: int, seed: int, counts: Mapping[str, int]) -> str:
    rows = "".join(f"<tr><td>{html.escape(tw.RELATION.get(o, o))}</td><td>{counts[o]}</td></tr>"
                   for o in tw.ORDER if o in counts)
    legend = "".join(f"<tr><td>{c}</td><td>{html.escape(t)}</td><td>{html.escape(v)}</td></tr>"
                     for v, cl in CLASSES.items() for c, t in cl)
    return f"""<h1>第二评判人甄别页：{html.escape(campaign)}（{n} 组）</h1>
<p>请按论文 VI-A 的书面标准，独立地给每一组选一个判定：<b>bug</b>、<b>legitimate</b> 或 <b>tool-artifact</b>。选了 legitimate 或 tool-artifact 时，可以再选一个例外类别；备注框写一句理由，拿不准就写“不确定”。本页不显示任何别人的判定。操作说明见随页发来的 <code>rater2_manual_zh.html</code>。</p>
<p>进度自动存在这个浏览器里（键名 <code>{html.escape(f'tse2-rater2:triage:{campaign}')}</code>）；换浏览器、换电脑或清除浏览器数据会丢，每次做完请点「下载结果文件」（{EXPORT_NAME}）留底，换电脑时用「从结果文件恢复」接着做。</p>
<p class="muted">组的顺序按固定种子 {seed} 随机排列（Python random.Random({seed}).shuffle，先按组名排序再打乱），每次生成都一样。</p>
<details><summary>判定标准原文（论文 VI-A）</summary><div class="criteria">{html.escape(CRITERIA_EN)}</div></details>
<details><summary>例外类别一览</summary><table class="legend"><tr><th>类别</th><th>含义</th><th>用于</th></tr>{legend}</table></details>
<details><summary>各规则的组数</summary><table><tr><th>规则</th><th>组数</th></tr>{rows}</table></details>
"""


def assemble(campaign: str, seed: int, head: str, content: str, n: int) -> str:
    """The whole page: head text, sticky bar, the items, the embedded config and the script."""
    config = {"page": PAGE, "campaign": campaign, "key": f"tse2-rater2:triage:{campaign}", "seed": seed,
              "file": EXPORT_NAME, "choices": list(CHOICES), "labels": LABELS, "question": QUESTION,
              "placeholder": PLACEHOLDER, "classes": {v: [list(c) for c in cl] for v, cl in CLASSES.items()}}
    data = json.dumps(config, ensure_ascii=False, sort_keys=True)
    data = data.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return "".join([
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>第二评判人甄别页 {html.escape(campaign)}</title><style>{tw.CSS}{EXTRA_CSS}</style></head><body>\n",
        head, BAR.format(n=n), content,
        f'\n<script type="application/json" id="rater2-config">{data}</script>\n<script>\n{SCRIPT}</script>\n',
        "</body></html>\n"])


def read_sweep(root: str) -> Dict[str, Any]:
    path = os.path.join(root, "sweep", "older-2025", "results.jsonl")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return {r["gid"]: r for r in (json.loads(line) for line in f if line.strip())}


def build_rater2(campaign: str, root: Optional[str] = None, seed: int = ORDER_SEED) -> Tuple[str, List[str], str]:
    """(page, the shuffled group order, the page built with no groups). Reads no judgement file; writes nothing."""
    root = root or os.path.join(tw.REPO, "data", "lsptest", "runs", campaign)
    tdir = os.path.join(root, "triage")
    groups = {g["gid"]: g for g in tw.load(os.path.join(tdir, "triage.json"))["groups"]}
    order = shuffled(groups, seed)
    sweep = read_sweep(root)
    counts: Dict[str, int] = {}
    for g in groups.values():
        oracle = g["signature"].split("|")[1]
        counts[oracle] = counts.get(oracle, 0) + 1
    blocks = "\n".join(group_block(i, groups[gid], tdir, sweep) for i, gid in enumerate(order, 1))
    head = intro(campaign, len(order), seed, counts)
    return assemble(campaign, seed, head, blocks, len(order)), order, assemble(campaign, seed, head, "", len(order))


# ------------------------------------------------------------------ leak check
def _csv_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def author_texts(root: str) -> Dict[str, List[str]]:
    """Every text the author's judging produced, by source: reasons, notes, cause descriptions, upstream links."""
    tdir = os.path.join(root, "triage")
    out: Dict[str, List[str]] = {}

    def add(source: str, values: Iterable[Optional[str]]) -> None:
        vals = sorted({(v or "").strip() for v in values} - {""})
        if vals:
            out.setdefault(source, []).extend(vals)

    rows = _csv_rows(os.path.join(tdir, "decisions.csv"))
    add("decisions.csv notes and links", (r.get(c) for r in rows for c in ("maintainer_response", "known_issue_link",
                                                                           "report_link")))
    add("verdict_reasons.csv reasons", (r.get("reason") for r in _csv_rows(os.path.join(tdir, "verdict_reasons.csv"))))
    add("exception_classes.csv reasons",
        (r.get("reason") for r in _csv_rows(os.path.join(tdir, "exception_classes.csv"))))
    add("root_causes.csv descriptions",
        (r.get("description") for r in _csv_rows(os.path.join(tdir, "root_causes.csv"))))
    notes: List[str] = []
    for path in sorted(glob.glob(os.path.join(tdir, "judgements", "*.json"))):
        notes += [it.get("note") or "" for it in tw.load(path).get("items", []) if isinstance(it, dict)]
    add("judgements/*.json notes", notes)
    up = _csv_rows(os.path.join(root, "upstream", "feedback.csv"))
    add("upstream/feedback.csv links and notes", (r.get(c) for r in up for c in ("url", "note")))
    add("upstream issue ids", (f"{r['tracker']}#{r['number']}" for r in up if r.get("tracker") and r.get("number")))
    return out


def fragments(text: str, width: int = 32) -> List[str]:
    """The text itself and, for long texts, its first, middle and last `width` characters."""
    if len(text) < 2 * width:
        return [text]
    mid = len(text) // 2 - width // 2
    return [text, text[:width], text[mid:mid + width], text[-width:]]


def _contexts(hay: str, pattern: str, limit: int = 5) -> Tuple[int, List[str]]:
    found = list(re.finditer(pattern, hay))
    return len(found), [hay[max(0, m.start() - 50):m.end() + 50].replace("\n", " ") for m in found[:limit]]


def judgement_time(root: str) -> Optional[dt.datetime]:
    """The earliest time the author's judging left a trace: an export of the judging page or a CSV backup."""
    tdir = os.path.join(root, "triage")
    times: List[dt.datetime] = []
    for path in glob.glob(os.path.join(tdir, "judgements", "*.json")):
        stamp = str(tw.load(path).get("exported_at") or "")
        try:
            times.append(dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone().replace(tzinfo=None))
        except ValueError:
            continue
    for path in glob.glob(os.path.join(tdir, "decisions.csv.bak-*")):
        m = re.search(r"\.bak-(\d{8}-\d{6})", path)
        if m:
            times.append(dt.datetime.strptime(m.group(1), "%Y%m%d-%H%M%S"))
    return min(times) if times else None


def input_time(root: str, gids: Sequence[str]) -> dt.datetime:
    """The newest modification time among the files the page is built from."""
    tdir = os.path.join(root, "triage")
    paths = [os.path.join(tdir, "triage.json"), os.path.join(root, "sweep", "older-2025", "results.jsonl")]
    paths += [os.path.join(tdir, g, f) for g in gids for f in ("report.md", "repro.json")]
    return dt.datetime.fromtimestamp(max(os.path.getmtime(p) for p in paths if os.path.exists(p)))


def leak_check(page: str, template: str, root: str, gids: Sequence[str]) -> List[Dict[str, Any]]:
    """Searches of the page for traces of the author's judgements; each with its number of hits and examples."""
    views = {"page": page, "page, HTML entities decoded": html.unescape(page)}
    checks: List[Dict[str, Any]] = []
    for source, texts in author_texts(root).items():
        hits: List[str] = []
        searched = 0
        for text in texts:
            for frag in fragments(text):
                searched += 1
                if any(frag in v for v in views.values()):
                    hits.append(frag[:80])
        checks.append({"check": f"author text: {source}", "texts": len(texts), "searched": searched,
                       "hits": len(hits), "examples": hits[:5]})
    for label, pattern in (("root-cause id C1-C11", CAUSE_RE),
                           ("author page strings", "|".join(re.escape(m) for m in AUTHOR_PAGE_MARKS))):
        n, ex = _contexts(views["page, HTML entities decoded"], pattern)
        checks.append({"check": label, "hits": n, "examples": ex})
    decoded, fixed = html.unescape(page), html.unescape(template)
    for label, pattern in [(f"verdict word '{w}' outside the fixed page text", p) for w, p in VERDICT_WORDS.items()] + \
            [("class code L1-L7/A1-A4 outside the fixed page text", CLASS_RE),
             ("pre-selected button outside the fixed page text", r'class="[^"]*\bchosen\b|aria-pressed="true"')]:
        total, ex = _contexts(decoded, pattern)
        base = len(re.findall(pattern, fixed))
        checks.append({"check": label, "hits": total - base, "in_fixed_text": base,
                       "examples": ex if total != base else []})
    config = re.search(r'<script type="application/json" id="rater2-config">(.*?)</script>', page, re.S)
    in_config = [g for g in gids if config and g in config.group(1)]
    checks.append({"check": "group ids inside the page config", "hits": len(in_config), "examples": in_config[:5]})
    first, newest = judgement_time(root), input_time(root, gids)
    checks.append({"check": "inputs written after the author's first judgement", "hits": int(bool(first and newest >= first)),
                   "examples": [f"newest input {newest:%Y-%m-%d %H:%M}, first judgement "
                                f"{first:%Y-%m-%d %H:%M}" if first else "no judgement trace found"]})
    return checks


def order_overlap(order: Sequence[str], other: Sequence[str]) -> Dict[str, Any]:
    """Groups at the same position in both orders and Spearman's rank correlation of the positions."""
    pos = {g: i for i, g in enumerate(other)}
    common = [g for g in order if g in pos]
    n = len(common)
    if n < 2:
        return {"groups": n, "same_position": 0, "spearman": None}
    ranks_a = {g: i for i, g in enumerate(common)}
    ranks_b = {g: i for i, g in enumerate(sorted(common, key=pos.__getitem__))}
    d2 = sum((ranks_a[g] - ranks_b[g]) ** 2 for g in common)
    return {"groups": n, "same_position": sum(1 for g in common if ranks_a[g] == ranks_b[g]),
            "spearman": round(1 - 6 * d2 / (n * (n * n - 1)), 3)}


def author_orders(root: str) -> Dict[str, List[str]]:
    """The order of the author's page and of the author's first-pass export (by its item numbers)."""
    tdir = os.path.join(root, "triage")
    out = {"author page order": [g["gid"] for g in tw.ordered(tw.load(os.path.join(tdir, "triage.json"))["groups"])]}
    first = sorted(glob.glob(os.path.join(tdir, "judgements", "triage_*.json")))
    if first:
        items = [it for it in tw.load(first[0]).get("items", []) if isinstance(it, dict)]
        out["author first-pass export order"] = [it["id"] for it in sorted(items, key=lambda it: it.get("n", 0))]
    return out


def main_rater2(campaign: str) -> int:
    """Write workbook_rater2.html for the campaign, then print the leak check; 1 when anything leaked."""
    root = os.path.join(tw.REPO, "data", "lsptest", "runs", campaign)
    page, order, template = build_rater2(campaign, root)
    out = os.path.join(root, "triage", OUT_NAME)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    with open(out, "r", encoding="utf-8") as f:
        written = f.read()
    print(f"wrote {os.path.relpath(out, tw.REPO)}: {len(order)} groups, seed {ORDER_SEED}, "
          f"{len(written.encode()) // 1024} KB")
    checks = leak_check(written, template, root, order)
    for c in checks:
        extra = f" ({c['texts']} texts, {c['searched']} strings searched)" if "texts" in c else \
            f" (fixed page text: {c['in_fixed_text']})" if "in_fixed_text" in c else ""
        print(f"  {'LEAK' if c['hits'] else 'ok  '} {c['check']}: {c['hits']} hit(s){extra}")
        for e in c["examples"] if c["hits"] or "inputs written" in c["check"] else []:
            print(f"       {e}")
    for label, other in author_orders(root).items():
        ov = order_overlap(order, other)
        print(f"  order vs {label}: {ov['same_position']} of {ov['groups']} groups at the same position, "
              f"Spearman {ov['spearman']}")
    return 1 if any(c["hits"] for c in checks) else 0
