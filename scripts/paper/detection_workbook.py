"""One local HTML page on which the author checks the benchmark detections of a campaign (bench_v1).

Inputs: data/lsptest/runs/<campaign>/detection.json (the detected cases and their pre-only
signatures: reported on the version before the fix, not after it), data/lsp_bench/cases/<case>/
case.json (issue title and link, the benchmark's own reproduction steps and probe), the first vid's
data/lsptest/runs/<campaign>/violations/<vid>/repro.json (the tool's finding: ops, query key,
expected and actual answers) and data/lsptest/runs/<campaign>/detection_author.csv (judgements
already made). The page groups the pre-only signatures by case, numbers them 1..N in
detection.json order and asks for each whether the finding is the bug of the issue: yes / no /
partial. Nothing is pre-selected and the page suggests no answer; values already in the CSV show
as judged. Clicks stay in the browser and leave as JSON (the kit of triage_workbook.py);
scripts/paper/import_judgements.py writes them into detection_author.csv.

--rater2 writes detection_workbook_rater2.html instead: the page for a second, independent rater, which shows
the same evidence with no trace of the author's judgements, in an order shuffled with a fixed seed
(scripts/paper/detection_rater2.py; import with scripts/paper/import_rater2_detection.py, agreement with
scripts/paper/detection_agreement.py).

Run line: python3 scripts/paper/detection_workbook.py [bench_v1]
Run line (second rater): python3 scripts/paper/detection_workbook.py bench_v1 --rater2
"""

from __future__ import annotations

import csv
import html
import json
import logging
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from triage_workbook import RELATION, REPO, answer_diff, diff_html, judge_block, load, page_html, seed_entry, \
    summary_head

MAX_TEXT = 160
QUESTION = "工具在修复前版本上报出的这个问题，是不是这条 issue 说的那个 bug？"
RULE = {
    "r0_crash": "未改动的项目上，一个请求不该返回内部错误、把服务器弄死或超时；这里两个独立的新会话都出错。",
    "r1_history": "一串编辑之后文档内容回到 C，各项查询应和“新开会话直接打开 C”一样。",
    "r2_handles": "编辑前拿到的代码操作/补全句柄，编辑后再解析，要么被拒绝，要么和新句柄结果一样。",
    "r3_routes": "同一个事实走不同协议路径，答案要一致（拉取式与推送式诊断、区间与全量语义高亮、文档高亮与引用、从引用跳定义）。",
    "r4_edits": "快速修复应用后目标诊断消失且不引入新错误；格式化/整理导入做两次和做一次一样；插入补全不引入语法错误。",
    "r5_transforms": "只加空行、注释或换行尾风格等语义不变的变换之后，查询结果按位置映射应不变。",
    "r6_crossimpl": "同一项目、同一位置，TypeScript 6 和 TypeScript 7 的答案应一致。"}
EXPECTED = {
    "r0_crash": "预期是一个正常的答案；实际是两个新会话都得到的错误。",
    "r1_history": "预期是新开会话在同样内容上的答案；实际是经历过上面这串操作的会话的答案。",
    "r2_handles": "预期是新句柄解析出的编辑；实际是旧句柄在编辑之后解析出的编辑。",
    "r3_routes": "预期是一条协议路径的答案；实际是另一条应当一致的路径的答案。",
    "r4_edits": "预期是编辑有效时应有的结果（例如没有新增错误、第二次不再改动）；实际是工具看到的结果。",
    "r5_transforms": "预期是原项目上的答案；实际是变换后项目上的答案（位置已映射回原项目）。",
    "r6_crossimpl": "预期是参照实现的答案；实际是被测实现的答案。"}
PROBE = {
    "differs_from_fresh": "操作之后的查询答案与新开会话不同",
    "error_response": "操作之后的一个查询返回错误",
    "edit_breaks_syntax": "应用服务器给出的编辑（代码操作、补全或格式化）后出现语法错误",
    "edit_leaves_diagnostic": "应用编辑后，新会话里目标诊断仍在，或出现编辑前没有的错误",
    "diagnostic_present": "出现一条不该有的诊断（误报）",
    "diagnostic_absent": "缺少一条该有的诊断（漏报）",
    "two_routes_differ": "同一会话里的两条查询不满足应有的关系",
    "transform_differs": "语义不变的变换（插入行或换行符改成 CRLF）之后答案不同",
    "stale_code_action": "过期的代码操作句柄解析出与新句柄不同的编辑",
    "edit_text_differs": "编辑结果与 issue 或回归测试给出的预期文本不同（规格探针）"}

logger = logging.getLogger(__name__)


def quote(text: str) -> str:
    s = json.dumps(text, ensure_ascii=False)
    return s if len(s) <= MAX_TEXT else s[:MAX_TEXT] + f"…（共 {len(text)} 个字符）"


def at(pos: Sequence[Any]) -> str:
    return f"第 {int(pos[0]) + 1} 行第 {int(pos[1]) + 1} 列"


def step_text(op: Mapping[str, Any]) -> str:
    """One op of repro.json in plain words (positions 1-based)."""
    kind, path = str(op.get("kind")), f"<code>{html.escape(str(op.get('path', '')))}</code>"
    text = str(op.get("text", ""))
    if kind in ("open", "close", "save"):
        out = {"open": "打开", "close": "关闭", "save": "保存"}[kind] + f" {path}"
    elif kind == "change":
        start, end = op.get("start") or [0, 0], op.get("end") or [0, 0]
        span = f"{path} 的{at(start)}到{at(end)}"
        out = f"在 {path} 的{at(start)}插入 {html.escape(quote(text))}" if list(start) == list(end) else \
            f"删除 {span}" if not text else f"把 {span} 替换为 {html.escape(quote(text))}"
    elif kind == "fs_write":
        out = f"在磁盘上写入 {path}（{len(text)} 个字符）：{html.escape(quote(text))}"
    elif kind == "fs_rename":
        out = f"在磁盘上把 {path} 改名为 <code>{html.escape(str(op.get('new_path', '')))}</code>"
    elif kind == "set_config":
        out = f"修改设置 <code>{html.escape(json.dumps(op.get('settings'), ensure_ascii=False, sort_keys=True))}</code>"
    elif kind == "request":
        out = f"发一次请求 <code>{html.escape(text)}</code>（{path} 的{at(op.get('start') or [0, 0])}）"
    else:
        out = f"{html.escape(kind)} <code>{html.escape(json.dumps(op, ensure_ascii=False, sort_keys=True))}</code>"
    return out + (f"，之后等 {int(op['delay_ms'])} 毫秒" if op.get("delay_ms") else "")


def ops_html(repro: Mapping[str, Any]) -> str:
    ops = repro.get("ops") or []
    if not ops:
        return '<p class="muted">（没有编辑步骤：在项目上直接做下面的查询）</p>'
    timing = str((repro.get("context") or {}).get("timing") or "settled")
    pace = "每一步之后等服务器空闲再做下一步。" if timing == "settled" else \
        f"各步之间不等服务器空闲（{html.escape(timing)}），最后等服务器空闲。"
    return "<ol>" + "".join(f"<li>{step_text(o)}</li>" for o in ops) + f'</ol><p class="muted">{pace}</p>'


def key_text(key: Mapping[str, Any]) -> str:
    line, ch = int(key.get("line", -1)), int(key.get("character", -1))
    where = "整个文件" if line < 0 else at([line, ch])
    extra = f"；附加信息 <code>{html.escape(str(key['extra']))}</code>" if key.get("extra") else ""
    return (f"<code>{html.escape(str(key.get('method')))}</code> · 文件 <code>{html.escape(str(key.get('path')))}</code>"
            f" · {where}{extra}")


def evidence_html(case: Mapping[str, Any], p: Mapping[str, Any], repro: Mapping[str, Any],
                  where: str = "原始记录 repro.json") -> str:
    """The evidence of one pre-only signature, shared by the author's page and the second rater's page: the issue,
    the rule, the signature, the tool's note, the ops on the pre-fix build, the query and the answer diff."""
    oracle, sig = str(p["oracle"]), str(p["signature"])
    server = repro.get("server") or {}
    note = str(repro.get("note") or "").split("; flake ")[0].strip()
    vids = p.get("vids") or []
    title = f'<a href="{html.escape(case["url"])}" target="_blank" rel="noopener">{html.escape(case["title"])}</a>'
    return f"""<p class="muted">对照的 issue：{title}</p>
<p><b>规则</b>：{html.escape(RELATION.get(oracle, oracle))}——{html.escape(RULE.get(oracle, ''))}</p>
<p><b>签名</b>：<code>{html.escape(sig)}</code>（复现 {html.escape(str(repro.get('reproduced', '?')))}；这个签名共 {len(vids)} 个实例，下面是第一个）</p>
{f'<p><b>工具的说明</b>：{html.escape(note)}</p>' if note else ''}
<h4>工具在修复前版本（{html.escape(str(server.get('kind', '')))} {html.escape(str(server.get('version', '')))}）上做的操作</h4>
{ops_html(repro)}
<p><b>然后查询</b>：{key_text(repro.get('key') or {})}</p>
<h4>预期与实际的差别（红 = 预期，参照答案；绿 = 实际，被测答案）</h4>
<p class="muted">{html.escape(EXPECTED.get(oracle, ''))}</p>
{diff_html(answer_diff(repro.get('expected'), repro.get('actual'), where))}"""


def item_html(n: int, case: Mapping[str, Any], p: Mapping[str, Any], repro: Mapping[str, Any], vid: str,
              seed: Mapping[str, Any]) -> str:
    oracle, sig = str(p["oracle"]), str(p["signature"])
    item_id = f"{case['case']}|{oracle}|{sig}"
    return f"""
<details class="item" id="item-{n}" data-id="{html.escape(item_id)}" data-n="{n}"><summary>{summary_head(n, seed)} {html.escape(case['case'])} · {html.escape(RELATION.get(oracle, oracle))} · <code>{html.escape(sig.split('|', 2)[-1])}</code></summary>
<div class="body">
{evidence_html(case, p, repro)}
<p class="muted">原始记录：<a href="violations/{html.escape(vid)}/repro.json" target="_blank" rel="noopener">violations/{html.escape(vid)}/repro.json</a></p>
{judge_block("detection", QUESTION, seed, "备注（可选）：一句理由，或 unsure……")}
</div></details>"""


def case_head(case: Mapping[str, Any], spec: Mapping[str, Any], count: str = "条待核对") -> str:
    """A case's heading: the issue, the builds, the number of items, the benchmark's steps and probe."""
    repro = spec.get("repro") or {}
    probe = str((repro.get("probe") or {}).get("type") or case.get("probe") or "")
    builds = case.get("builds") or {}
    return (f'<section class="case" id="case-{html.escape(case["case"])}"><h2>{html.escape(case["case"])}</h2>\n'
            f'<p><a href="{html.escape(case["url"])}" target="_blank" rel="noopener">{html.escape(case["title"])}</a> '
            f'<span class="muted">（{html.escape(str(case.get("kind", "")))}，修复前 {html.escape(str(builds.get("pre", "?")))}'
            f'，修复后 {html.escape(str(builds.get("post", "?")))}；{len(case["pre_only"])} {count}）</span></p>\n'
            f'<p><b>基准里这个 bug 的复现步骤</b>：{html.escape(str(repro.get("steps") or "（case.json 里没有）"))}</p>\n'
            f'<p><b>基准的探针</b>：<code>{html.escape(probe)}</code>'
            + (f"（{html.escape(PROBE[probe])}）" if probe in PROBE else "") + "</p>\n")


INTRO = """<h1>检出核对：{campaign}（{cases} 个历史 bug，{n} 条修复前独有的发现）</h1>
<p>下面每一条，是工具在某个历史 bug 的修复前版本上报出、而在修复后版本上没有报出的一类问题。一个历史 bug 只有在它至少有一条被你判为 yes 时，才算工具检出了它；判为 partial 的单独报告，不算进检出。</p>
<p>每条对照 issue 原文回答一个问题：<b>{question}</b>点 <b>yes</b>（就是这个 bug）、<b>no</b>（不是这个 bug：是别的差异）或 <b>partial</b>（部分是：相关但不完全是）。点错了直接点另一个，或点「清除」。做完一批就点「复制结果」，把内容粘贴到对话里发给我；随时可以停，下次打开会接着上次的进度。</p>
<p class="muted">差别里红色是预期（参照答案），绿色是实际（被测答案）。同一个 bug 的几条连着看会快很多。</p>
"""


def read_author(path: str) -> Dict[str, Dict[str, Any]]:
    """'<case>|<oracle>|<signature>' -> seed for the rows of detection_author.csv with a value or a note."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {f"{r['case']}|{r['oracle']}|{r['signature']}": seed_entry("detection", r.get("author_match"), r.get("note"))
            for r in rows if (r.get("author_match") or "").strip() or (r.get("note") or "").strip()}


def build(campaign: str = "bench_v1", run_dir: Optional[str] = None, bench_dir: Optional[str] = None,
          author_csv: Optional[str] = None) -> Tuple[str, int, int]:
    """The page: (html, number of items, items judged in the CSV). Nothing is written."""
    run_dir = run_dir or os.path.join(REPO, "data", "lsptest", "runs", campaign)
    bench_dir = bench_dir or os.path.join(REPO, "data", "lsp_bench", "cases")
    cases = [c for c in load(os.path.join(run_dir, "detection.json"))["cases"] if c.get("detected")]
    known = read_author(author_csv or os.path.join(run_dir, "detection_author.csv"))
    body: List[str] = []
    seeds: Dict[str, Dict[str, Any]] = {}
    n = 0
    for case in cases:
        body.append(case_head(case, load(os.path.join(bench_dir, case["case"], "case.json"))))
        for p in case["pre_only"]:
            n += 1
            item_id = f"{case['case']}|{p['oracle']}|{p['signature']}"
            if item_id in known:
                seeds[item_id] = known[item_id]
            vid = str(p["vids"][0])
            repro = load(os.path.join(run_dir, "violations", vid, "repro.json"))
            if repro.get("signature") != p["signature"]:
                logger.warning("%s: repro.json signature %s differs from %s", vid, repro.get("signature"), p["signature"])
            body.append(item_html(n, case, p, repro, vid, seeds.get(item_id, {})))
        body.append("</section>")
    unmatched = sorted(set(known) - set(seeds))
    if unmatched:
        logger.warning("%d judged row(s) of the CSV are not on the page: %s", len(unmatched), unmatched[:5])
    head = INTRO.format(campaign=html.escape(campaign), cases=len(cases), n=n, question=QUESTION)
    page = page_html("detection", campaign, f"检出核对 {campaign}", head, "\n".join(body), seeds, n)
    return page, n, sum(1 for s in seeds.values() if s["choice"])


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    rater2 = "--rater2" in args
    args = [a for a in args if a != "--rater2"]
    campaign = args[0] if args else "bench_v1"
    if rater2:
        import detection_rater2  # imported here: it builds on this module
        return detection_rater2.main_rater2(campaign)
    page, n, judged = build(campaign)
    out = os.path.join(REPO, "data", "lsptest", "runs", campaign, "detection_workbook.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {os.path.relpath(out, REPO)}: {n} items, {judged} judged in detection_author.csv, "
          f"{len(page.encode()) // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
