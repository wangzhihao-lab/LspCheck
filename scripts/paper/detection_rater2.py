"""The second rater's page for the benchmark's pre-only signatures, and its leak check.

Built by `detection_workbook.py <campaign> --rater2`. For every pre-only signature of the detected cases in
data/lsptest/runs/<campaign>/detection.json (a signature reported on the version before the fix and not after
it) the page shows the evidence of the author's page (detection_workbook.evidence_html: issue title and link,
the rule, the signature, the tool's note, the ops on the pre-fix build, the query, the line diff between
expected and actual answer) under the same case heading (the benchmark's own reproduction steps and probe),
and embeds the full repro.json that the author's page links to. It asks the author page's question with three
buttons (yes / no / partial, in the author page's order) and an optional note; the buttons are drawn by the page script, so nothing is
pre-selected. The page reads only the case metadata, the signatures and their vids from detection.json (the
author_match field there is dropped on load) and never opens detection_author.csv. The cases appear in a
random order drawn with a fixed seed, and the signatures inside each case too; items are numbered in that
order. The choices stay in the browser under their own localStorage key and leave as
detection_rater2_judgements.json ("下载结果文件") or through the clipboard;
scripts/paper/import_rater2_detection.py writes that file into detection_rater2.csv.

leak_check() searches the page for everything the author's judging produced (notes, the triage campaigns'
reasons and notes, our upstream report links and ids, root-cause ids C1-C11, the author page's strings, the
paper's detection counts that come from the author's check, pre-selected buttons) and rebuilds the page with
a planted author_match in every signature to show that the page does not depend on it; main_rater2() writes
the page only when every check is clean. overlap_report() lists the text shared with the author's page in
fragments of at least 30 characters, split into the fixed text and the evidence of the same item.

Run line: python3 scripts/paper/detection_workbook.py bench_v1 --rater2
"""

from __future__ import annotations

import copy
import datetime as dt
import glob
import html
import json
import logging
import os
import random
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import detection_workbook as dw
import rater2_workbook as rw
import triage_workbook as tw

ORDER_SEED = 20261118
PAGE = "detection-rater2"
EXPORT_NAME = "detection_rater2_judgements.json"
OUT_NAME = "detection_workbook_rater2.html"
# Same buttons, labels and order as the author page (triage_workbook.LABELS["detection"]).
CHOICES: Tuple[str, ...] = ("yes", "no", "partial")
LABELS: Dict[str, str] = {"yes": "就是这个 bug", "no": "不是这个 bug", "partial": "部分是"}
MEANING: Tuple[Tuple[str, str], ...] = (
    ("yes", "就是这个 bug：这条发现表现出的正是 issue 报告的那个 bug（论文的说法：shows the reported bug）。"),
    ("no", "不是这个 bug：是别的差异，只是修复恰好把它也去掉了（another difference that the fix happened to "
           "remove）。"),
    ("partial", "部分是：相关但不完全是，只表现出这个 bug 的一部分（shows part of it）。"))
QUESTION = dw.QUESTION
# The author page states how the verdicts are counted; the second rater sees the same sentence (equal conditions).
COUNT_RULE = "一个历史 bug 只有在它至少有一条被你判为 yes 时，才算工具检出了它；判为 partial 的单独报告，不算进检出。"
PLACEHOLDER = "备注（可选）：一句理由；拿不准就写“不确定”，并写下你倾向的理由"
CASE_KEYS: Tuple[str, ...] = ("case", "title", "url", "kind", "builds", "probe")
SIGNATURE_KEYS: Tuple[str, ...] = ("oracle", "signature", "vids")
AUTHOR_PAGE_MARKS: Tuple[str, ...] = rw.AUTHOR_PAGE_MARKS + (
    "author_match", "detection_author", "import_judgements", "after_author", "author_check_effect", "检出核对",
    "待核对", "judgements-detection")  # the counting rule sentence is shared with the author page on purpose (COUNT_RULE)

logger = logging.getLogger(__name__)

SCRIPT = r"""(function () {
  "use strict";
  var cfg = JSON.parse(document.getElementById("rater2-config").textContent);
  var items = Array.prototype.slice.call(document.querySelectorAll("details.item"));
  var state = {}, current = -1, canStore = true;
  function $(id) { return document.getElementById(id); }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }
  function idOf(item) { return item.getAttribute("data-id"); }
  function clean(s) {
    s = s && typeof s === "object" ? s : {};
    var v = cfg.choices.indexOf(s.verdict) >= 0 ? s.verdict : "";
    return {verdict: v, note: typeof s.note === "string" ? s.note : "",
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
      if (s.verdict || s.note) { out[idOf(item)] = s; }
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
    var note = el("textarea", "note");
    note.rows = 2; note.placeholder = cfg.placeholder; box.appendChild(note);
  }
  function render(item) {
    var s = state[idOf(item)], note = item.querySelector("textarea.note");
    each(item.querySelectorAll("button.choice"), function (b) {
      var on = b.getAttribute("data-choice") === s.verdict;
      b.classList.toggle("chosen", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var badge = item.querySelector(".state");
    badge.textContent = s.verdict ? "你选了 " + s.verdict : "未选";
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
      if (s.verdict || note) {
        out.push(JSON.stringify({n: Number(item.getAttribute("data-n")), id: idOf(item),
                                 "case": item.getAttribute("data-case"), signature: item.getAttribute("data-signature"),
                                 verdict: s.verdict, note: note, judged_at: s.judged_at}));
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
        current = i; touch(item);
      });
    });
    item.querySelector("button.clear").addEventListener("click", function () {
      var s = state[id]; s.verdict = ""; s.judged_at = ""; touch(item);
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
      if (!window.confirm("用文件里的 " + known.length + " 条结果覆盖本页同一条的选择？其他条不变。")) { e.target.value = ""; return; }
      known.forEach(function (it) { state[it.id] = clean({verdict: it.verdict, note: it.note, judged_at: it.judged_at}); n += 1; });
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
def item_id(case: str, p: Mapping[str, Any]) -> str:
    """The item key, the same as on the author's page: '<case>|<oracle>|<signature>'."""
    return f"{case}|{p['oracle']}|{p['signature']}"


def sanitize(doc: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """The detected cases of detection.json with only the fields the page shows: the case metadata and, per
    pre-only signature, its oracle, signature and vids. Everything else (author_match among it) is dropped."""
    out: List[Dict[str, Any]] = []
    for c in doc.get("cases", []):
        if not c.get("detected"):
            continue
        case = {k: copy.deepcopy(c[k]) for k in CASE_KEYS if k in c}
        case["pre_only"] = [{k: copy.deepcopy(p[k]) for k in SIGNATURE_KEYS if k in p} for p in c.get("pre_only", [])]
        out.append(case)
    return out


def shuffled(cases: Iterable[Mapping[str, Any]], seed: int = ORDER_SEED) -> List[Tuple[Mapping[str, Any], List[Any]]]:
    """(case, its signatures) in the page's order: one random.Random(seed) shuffles the case names (sorted first),
    then, case by case in that order, the case's signatures (sorted by signature first)."""
    by_name = {str(c["case"]): c for c in cases}
    rng = random.Random(seed)
    names = sorted(by_name)
    rng.shuffle(names)
    out: List[Tuple[Mapping[str, Any], List[Any]]] = []
    for name in names:
        sigs = sorted(by_name[name]["pre_only"], key=lambda p: (str(p["signature"]), str(p["oracle"])))
        rng.shuffle(sigs)
        out.append((by_name[name], sigs))
    return out


def order_of(cases: Iterable[Mapping[str, Any]], seed: int = ORDER_SEED) -> List[str]:
    """The item keys in page order (item n is entry n - 1)."""
    return [item_id(str(c["case"]), p) for c, sigs in shuffled(cases, seed) for p in sigs]


def item_block(n: int, case: Mapping[str, Any], p: Mapping[str, Any], repro: Mapping[str, Any]) -> str:
    """One signature: the author page's evidence, the full repro.json, and an empty judging box."""
    oracle, sig = str(p["oracle"]), str(p["signature"])
    eid = html.escape(item_id(str(case["case"]), p))
    raw = json.dumps(repro, indent=1, ensure_ascii=False, sort_keys=True)
    return f"""
<details class="item" id="item-{n}" data-id="{eid}" data-n="{n}" data-case="{html.escape(str(case['case']))}" data-signature="{html.escape(sig)}"><summary><b class="num">{n}.</b> <span class="state open">未选</span> {html.escape(str(case['case']))} · {html.escape(tw.RELATION.get(oracle, oracle))} · <code>{html.escape(sig.split('|', 2)[-1])}</code></summary>
<div class="body">
{dw.evidence_html(case, p, repro, '下面的完整原始记录')}
<details class="report"><summary>完整原始记录（repro.json 原文，英文：操作、查询、两边的完整答案、项目文件）</summary><pre>{html.escape(raw)}</pre></details>
<div class="judge" data-id="{eid}"></div>
</div></details>"""


def intro(campaign: str, n: int, seed: int) -> str:
    meaning = "".join(f"<tr><td>{c}</td><td>{html.escape(t)}</td></tr>" for c, t in MEANING)
    return f"""<h1>第二评判人：基准签名核对页 {html.escape(campaign)}（{n} 条发现，按历史 bug 分组）</h1>
<p>下面每一条，是工具在某个历史 bug 的修复前版本上报出、而在修复后版本上没有报出的一类问题。{html.escape(COUNT_RULE)}请对照 issue 原文，独立地给每一条回答同一个问题：<b>{html.escape(QUESTION)}</b></p>
<table class="legend">{meaning}</table>
<p>拿不准时，选最可能的一项，并在备注里写“不确定”。备注可以不写。本页不显示任何别人的判定。</p>
<p>进度自动存在这个浏览器里（键名 <code>{html.escape(f'tse2-rater2:detection:{campaign}')}</code>）；换浏览器、换电脑或清除浏览器数据会丢，每次做完请点「下载结果文件」（{EXPORT_NAME}）留底，换电脑时用「从结果文件恢复」接着做。</p>
<p class="muted">差别里红色是预期（参照答案），绿色是实际（被测答案）。同一个 bug 的几条放在一起，连着看会快很多。每条的完整原始记录嵌在本页里，不用另外的文件，也不用运行任何东西。</p>
<p class="muted">历史 bug 的顺序和每个 bug 里各条的顺序按固定种子 {seed} 随机排列（Python random.Random({seed})：先把 bug 按名字排序后打乱，再依次把每个 bug 的各条按签名排序后打乱），每次生成都一样；编号按打乱后的顺序。</p>
"""


def assemble(campaign: str, seed: int, head: str, content: str, n: int) -> str:
    """The whole page: head text, sticky bar, the items, the embedded config and the script."""
    config = {"page": PAGE, "campaign": campaign, "key": f"tse2-rater2:detection:{campaign}", "seed": seed,
              "file": EXPORT_NAME, "choices": list(CHOICES), "labels": LABELS, "question": QUESTION,
              "placeholder": PLACEHOLDER}
    data = json.dumps(config, ensure_ascii=False, sort_keys=True)
    data = data.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return "".join([
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>第二评判人：基准签名核对页 {html.escape(campaign)}</title><style>{tw.CSS}{rw.EXTRA_CSS}</style></head><body>\n",
        head, rw.BAR.format(n=n), content,
        f'\n<script type="application/json" id="rater2-config">{data}</script>\n<script>\n{SCRIPT}</script>\n',
        "</body></html>\n"])


def paths(campaign: str, run_dir: Optional[str] = None, bench_dir: Optional[str] = None) -> Tuple[str, str]:
    return (run_dir or os.path.join(tw.REPO, "data", "lsptest", "runs", campaign),
            bench_dir or os.path.join(tw.REPO, "data", "lsp_bench", "cases"))


def build_rater2(campaign: str, run_dir: Optional[str] = None, bench_dir: Optional[str] = None,
                 seed: int = ORDER_SEED, doc: Optional[Mapping[str, Any]] = None) -> Tuple[str, List[str], str]:
    """(page, the item keys in page order, the page built with no items). Reads detection.json (or doc), the
    cases' case.json and the first vid's repro.json; reads no judgement file and writes nothing."""
    run_dir, bench_dir = paths(campaign, run_dir, bench_dir)
    cases = sanitize(doc if doc is not None else tw.load(os.path.join(run_dir, "detection.json")))
    body: List[str] = []
    order: List[str] = []
    for case, sigs in shuffled(cases, seed):
        spec = tw.load(os.path.join(bench_dir, str(case["case"]), "case.json"))
        body.append(dw.case_head(case, spec, count="条"))
        for p in sigs:
            order.append(item_id(str(case["case"]), p))
            repro = tw.load(os.path.join(run_dir, "violations", str(p["vids"][0]), "repro.json"))
            if repro.get("signature") != p["signature"]:
                logger.warning("%s: repro.json signature %s differs from %s", p["vids"][0], repro.get("signature"),
                               p["signature"])
            body.append(item_block(len(order), case, p, repro))
        body.append("</section>")
    head = intro(campaign, len(order), seed)
    return (assemble(campaign, seed, head, "\n".join(body), len(order)), order,
            assemble(campaign, seed, head, "", len(order)))


# ------------------------------------------------------------------ leak check
def author_texts(run_dir: str) -> Dict[str, List[str]]:
    """Every text the author's judging produced: the notes of detection_author.csv and of the detection page's
    exports, and, for every campaign with a triage, what rater2_workbook.author_texts collects (reasons, notes,
    root-cause descriptions, our upstream report links and issue ids)."""
    out: Dict[str, List[str]] = {}

    def add(source: str, values: Iterable[Optional[str]]) -> None:
        vals = sorted({(v or "").strip() for v in values} - {""})
        if vals:
            out.setdefault(source, []).extend(vals)

    add("detection_author.csv notes", (r.get("note") for r in rw._csv_rows(os.path.join(run_dir, "detection_author.csv"))))
    notes: List[str] = []
    for path in sorted(glob.glob(os.path.join(run_dir, "judgements", "*.json"))):
        notes += [it.get("note") or "" for it in tw.load(path).get("items", []) if isinstance(it, dict)]
    add("detection judgements/*.json notes", notes)
    runs = os.path.dirname(os.path.abspath(run_dir))
    for root in sorted(glob.glob(os.path.join(runs, "*"))):
        if os.path.abspath(root) == os.path.abspath(run_dir) or not os.path.isdir(os.path.join(root, "triage")):
            continue
        for source, texts in rw.author_texts(root).items():
            add(f"{os.path.basename(root)} {source}", texts)
    return out


def author_numbers(numbers_json: str) -> Dict[str, int]:
    """The paper's detection counts (paper_numbers.json): those from the author's check and the case count of the
    pre-only rule, 10 and above (smaller numbers occur in any page text)."""
    if not os.path.exists(numbers_json):
        return {}
    det = tw.load(numbers_json).get("detection") or {}
    after = det.get("after_author") or {}
    found = {f"after_author.values.{k}": v for k, v in (after.get("values") or {}).items()}
    found["after_author.all.detected"] = (after.get("all") or {}).get("detected")
    found["after_author.generic.detected"] = (after.get("generic") or {}).get("detected")
    found["all.detected"] = (det.get("all") or {}).get("detected")
    found.update({f"author_check_effect.{k}": v for k, v in (det.get("author_check_effect") or {}).items()})
    return {k: int(v) for k, v in found.items() if isinstance(v, int) and v >= 10}


def visible(page: str) -> str:
    """The page's text without tags, styles and scripts, entities decoded, white space collapsed."""
    text = re.sub(r"<(style|script)\b.*?</\1>", " ", page, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def first_judgement(run_dir: str) -> Optional[dt.datetime]:
    """The earliest trace of the author's check: an export of the author's page or a backup of the CSV."""
    times: List[dt.datetime] = []
    for path in glob.glob(os.path.join(run_dir, "judgements", "*.json")):
        stamp = str(tw.load(path).get("exported_at") or "")
        try:
            times.append(dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone().replace(tzinfo=None))
        except ValueError:
            continue
    for path in glob.glob(os.path.join(run_dir, "detection_author.csv.bak-*")):
        m = re.search(r"\.bak-(\d{8}-\d{6})", path)
        if m:
            times.append(dt.datetime.strptime(m.group(1), "%Y%m%d-%H%M%S"))
    return min(times) if times else None


def input_time(run_dir: str, bench_dir: str, cases: Sequence[Mapping[str, Any]]) -> Optional[dt.datetime]:
    """The newest modification time of the case.json and repro.json files the page shows."""
    files = [os.path.join(bench_dir, str(c["case"]), "case.json") for c in cases]
    files += [os.path.join(run_dir, "violations", str(p["vids"][0]), "repro.json") for c in cases for p in c["pre_only"]]
    stamps = [os.path.getmtime(f) for f in files if os.path.exists(f)]
    return dt.datetime.fromtimestamp(max(stamps)) if stamps else None


def planted(doc: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """A copy of detection.json with a distinctive author_match (and note) in every pre-only signature."""
    out = copy.deepcopy(dict(doc))
    marks: List[str] = []
    for c in out.get("cases", []):
        for p in c.get("pre_only", []):
            mark = f"PLANTED-AUTHOR-MATCH-{len(marks):03d}-partial"
            p["author_match"], p["note"] = mark, mark
            marks.append(mark)
    return out, marks


def leak_check(page: str, template: str, run_dir: str, order: Sequence[str], campaign: str = "bench_v1",
               bench_dir: Optional[str] = None, doc: Optional[Mapping[str, Any]] = None,
               numbers_json: Optional[str] = None) -> List[Dict[str, Any]]:
    """Searches of the page for traces of the author's check; each with its number of hits and examples."""
    run_dir, bench_dir = paths(campaign, run_dir, bench_dir)
    doc = doc if doc is not None else tw.load(os.path.join(run_dir, "detection.json"))
    decoded = html.unescape(page)
    views = (page, decoded)
    checks: List[Dict[str, Any]] = []
    for source, texts in author_texts(run_dir).items():
        hits: List[str] = []
        searched = 0
        for text in texts:
            for frag in rw.fragments(text):
                searched += 1
                if any(frag in v for v in views):
                    hits.append(frag[:80])
        checks.append({"check": f"author text: {source}", "texts": len(texts), "searched": searched,
                       "hits": len(hits), "examples": hits[:5]})
    for label, pattern in (("root-cause id C1-C11", rw.CAUSE_RE),
                           ("author page strings", "|".join(re.escape(m) for m in AUTHOR_PAGE_MARKS))):
        n, ex = rw._contexts(decoded, pattern)
        checks.append({"check": label, "hits": n, "examples": ex})
    fixed = html.unescape(template)
    pattern = r'class="[^"]*\bchosen\b|aria-pressed="true"'
    total, ex = rw._contexts(decoded, pattern)
    base = len(re.findall(pattern, fixed))
    checks.append({"check": "pre-selected button outside the fixed page text", "hits": total - base,
                   "in_fixed_text": base, "examples": ex if total != base else []})
    text = visible(template)
    nums = author_numbers(numbers_json or os.path.join(tw.REPO, "data", "lsptest", "paper_numbers.json"))
    found = [f"{k} = {v}" for k, v in nums.items() if re.search(rf"(?<![\d.]){v}(?![\d.])", text)]
    checks.append({"check": f"paper's detection counts in the fixed text ({len(nums)} numbers)",
                   "hits": len(found), "examples": found[:5]})
    config = re.search(r'<script type="application/json" id="rater2-config">(.*?)</script>', page, re.S)
    in_config = [i for i in order if config and i in config.group(1)]
    checks.append({"check": "item keys inside the page config", "hits": len(in_config), "examples": in_config[:5]})
    other, marks = planted(doc)
    again = build_rater2(campaign, run_dir, bench_dir, json.loads(_seed_of(page)), other)[0]
    seen = [m for m in marks if m in again]
    checks.append({"check": "page changes when author_match is planted in detection.json",
                   "hits": int(again != page) + len(seen), "examples": seen[:3]})
    first, newest = first_judgement(run_dir), input_time(run_dir, bench_dir, sanitize(doc))
    checks.append({"check": "case.json or repro.json written after the author's first judgement",
                   "hits": int(bool(first and newest and newest >= first)),
                   "examples": [f"newest input {newest:%Y-%m-%d %H:%M}, first judgement {first:%Y-%m-%d %H:%M}"
                                if first and newest else "no judgement trace found"]})
    return checks


def _seed_of(page: str) -> str:
    m = re.search(r'"seed": (\d+)', page)
    return m.group(1) if m else str(ORDER_SEED)


# ------------------------------------------------------------------ overlap with the author's page
def coverage(text: str, other: str, width: int = 30) -> List[bool]:
    """For each character of text: whether a window of `width` characters around it also occurs in other."""
    windows = {other[i:i + width] for i in range(max(0, len(other) - width + 1))}
    covered = [False] * len(text)
    for i in range(max(0, len(text) - width + 1)):
        if text[i:i + width] in windows:
            covered[i:i + width] = [True] * width
    return covered


def runs(text: str, covered: Sequence[bool], width: int = 30) -> List[str]:
    """The maximal stretches of covered characters, `width` characters or longer."""
    out: List[str] = []
    start: Optional[int] = None
    for i, c in enumerate(list(covered) + [False]):
        if c and start is None:
            start = i
        elif not c and start is not None:
            if i - start >= width:
                out.append(text[start:i].strip())
            start = None
    return out


def common_fragments(text: str, other: str, width: int = 30) -> List[str]:
    """The maximal stretches of text covered by windows of `width` characters that also occur in other."""
    return runs(text, coverage(text, other, width), width)


RAW_RE = re.compile(r'<details class="report">.*?</details>', re.S)


def split_page(page: str) -> Tuple[str, Dict[str, str], Dict[str, str]]:
    """(text before the first case, case id -> case heading, item key -> item) of a judging page."""
    first = page.find('<section class="case"')
    head = page[:first] if first >= 0 else page
    cases = {m.group(1): m.group(2) for m in re.finditer(
        r'<section class="case" id="case-([^"]+)">(.*?)(?=<details class="item")', page, re.S)}
    items = {html.unescape(m.group(1)): m.group(0) for m in re.finditer(
        r'<details class="item" id="item-\d+" data-id="([^"]+)".*?</div></details>', page, re.S)}
    return head, cases, items


def overlap_report(page: str, author_page: str, width: int = 30) -> Dict[str, Any]:
    """Text shared with the author's page, in fragments of at least `width` characters: in the fixed text before
    the items; in each case heading and item, against the same case or item of the author's page (the shared
    evidence); and stretches of a heading or item found on the author's page only outside that same case or item.
    The embedded repro.json (absent from the author's page, which links to the file) is left out."""
    head, cases, items = split_page(page)
    a_head, a_cases, a_items = split_page(author_page)
    a_all = visible(author_page)
    fixed = common_fragments(visible(head), visible(a_head), width)
    elsewhere: List[str] = []
    chars = shared = 0
    for key, block, a_block in [(k, v, a_cases.get(k, "")) for k, v in cases.items()] + \
            [(k, v, a_items.get(k, "")) for k, v in items.items()]:
        text = visible(RAW_RE.sub(" ", block))
        same = coverage(text, visible(a_block), width)
        anywhere = coverage(text, a_all, width)
        chars += len(text)
        shared += sum(same)
        elsewhere += [f"{key}: {frag}" for frag in runs(text, [a and not s for a, s in zip(anywhere, same)], width)]
    return {"width": width, "fixed_text": fixed,
            "same_case_or_item": {"blocks": len(cases) + len(items), "shared_chars": shared, "chars": chars},
            "elsewhere": sorted(set(elsewhere)),
            "author_items_missing": sorted(set(a_items) - set(items)),
            "rater_items_missing": sorted(set(items) - set(a_items))}


# ------------------------------------------------------------------ main
def main_rater2(campaign: str) -> int:
    """Build the page, run the leak check, and write detection_workbook_rater2.html only when it is clean."""
    run_dir, bench_dir = paths(campaign)
    doc = tw.load(os.path.join(run_dir, "detection.json"))
    page, order, template = build_rater2(campaign, run_dir, bench_dir, ORDER_SEED, doc)
    checks = leak_check(page, template, run_dir, order, campaign, bench_dir, doc)
    for c in checks:
        extra = f" ({c['texts']} texts, {c['searched']} strings searched)" if "texts" in c else \
            f" (fixed page text: {c['in_fixed_text']})" if "in_fixed_text" in c else ""
        print(f"  {'LEAK' if c['hits'] else 'ok  '} {c['check']}: {c['hits']} hit(s){extra}")
        for e in c["examples"] if c["hits"] or "written after" in c["check"] else []:
            print(f"       {e}")
    out = os.path.join(run_dir, OUT_NAME)
    if any(c["hits"] for c in checks):
        logger.error("leak check failed: %s not written", os.path.relpath(out, tw.REPO))
        return 1
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    with open(out, "r", encoding="utf-8") as f:
        if f.read() != page:
            logger.error("%s reads back different from the page built", out)
            return 1
    print(f"wrote {os.path.relpath(out, tw.REPO)}: {len(order)} items, seed {ORDER_SEED}, "
          f"{len(page.encode()) // 1024} KB")
    author_page = dw.build(campaign, run_dir, bench_dir)[0]
    ov = overlap_report(page, author_page)
    s = ov["same_case_or_item"]
    print(f"  overlap with the author's page ({ov['width']}-character fragments):")
    print(f"    fixed text: {len(ov['fixed_text'])} fragment(s)")
    for frag in ov["fixed_text"]:
        print(f"       {frag[:200]}")
    print(f"    same case or item: {s['shared_chars']} of {s['chars']} characters in {s['blocks']} blocks are shared "
          f"with the same case heading or item of the author's page (the shared evidence; embedded repro.json left out)")
    print(f"    found only elsewhere on the author's page: {len(ov['elsewhere'])}")
    for frag in ov["elsewhere"][:40]:
        print(f"       {frag[:200]}")
    print(f"    items missing: on this page {len(ov['author_items_missing'])}, "
          f"on the author's page {len(ov['rater_items_missing'])}")
    author_order = [item_id(str(c["case"]), p) for c in sanitize(doc) for p in c["pre_only"]]
    ov2 = rw.order_overlap(order, author_order)
    print(f"  order vs the author page order: {ov2['same_position']} of {ov2['groups']} items at the same position, "
          f"Spearman {ov2['spearman']}")
    return 0
