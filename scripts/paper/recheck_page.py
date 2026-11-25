"""A short judging page for the author's second look after the first internal review
(plan/revision_round1.md, concern M3): the six groups whose verdicts look inconsistent with similar
groups, and the 23 groups judged bugs, each to be kept or changed with a one-sentence reason.

The page reuses the judging kit of triage_workbook.py. The author's current verdict is shown as the
starting state (it is the author's own judgement, not a suggestion). Results leave through
"复制结果" and are imported with:
  python3 scripts/paper/import_judgements.py <pasted.json> --csv data/lsptest/runs/main_v1/triage/decisions.csv
The note of each item goes into the maintainer_response column, which holds the author's notes.

Run line: python3 scripts/paper/recheck_page.py
"""

from __future__ import annotations

import html
import logging
import os
import sys
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from triage_workbook import (REPO, group_html, load, ordered, page_html, read_decisions)  # noqa: E402

CAMPAIGN = "main_v1"
FLAGGED: Dict[str, str] = {
    "gopls-r4-diagnostics-extra-invalidifaceassign-mutation-m2-416e90":
        "同样是 gopls 的“创建变量”生成 x := 0 后在使用处出现类型错误；NotAType 那一组你判的是 bug，这一组判的是 legitimate。",
    "gopls-r4-diagnostics-extra-nonindexableoperand-mutation-m2-ba152b":
        "同上：“创建变量”生成 x := 0 后该变量被当作可索引的值使用；类似的 NotAType 组判的是 bug。",
    "gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a":
        "同上：“创建变量”生成 x := 0 后该变量被切片使用；类似的 NotAType 组判的是 bug。",
    "ts7-r1-references-missing-h9-2dd24a":
        "TS7 在一次编辑后只返回新会话 6 个引用中的 1 个；TS6 上同样丢引用的组你判的是 bug。",
    "gopls-r1-references-extra-h9-0290a7":
        "新会话漏掉了测试文件里的一个引用，而历史会话能找到；这和基准里维护者修过的 gopls-43144（查引用不总搜测试文件）是同一种现象。",
    "rust-analyzer-r3-definitionconsistency-changed-d-2c6179":
        "同一服务器、同一检查（从引用跳定义）的另外两组你判的是 bug（C8），这一组判的是 legitimate。",
}

INTRO = """<h1>复看：{n} 组（约 1 小时）</h1>
<p>审稿模拟指出两件事：一是有 6 组的判断和相似的组看起来不一致；二是所有判断都没写理由。请按下面的顺序做：</p>
<ol>
<li><b>前 6 组（标了“为什么请你再看”）</b>：按判断准则重新看一遍，维持原判就不用动按钮，要改就点另一个按钮。无论改不改，都在备注框里写一句理由。</li>
<li><b>其余 {bugs} 组（你判为 bug 的）</b>：按钮已是你原来的判断，只需在备注框里写一句理由，例如“改名再改回后引用全部丢失，新会话能找到，属于状态错误”。想改判也可以。</li>
</ol>
<p><b>判断准则</b>（论文里写的就是这三条）：<b>bug</b>＝被测会话的答案按语言或协议是错的，且没有文档说明这种行为；<b>legitimate</b>＝两边都说得通，因为协议把这件事留给实现决定，或者差异有文档说明；<b>tool-artifact</b>＝差异来自测试工具的输入或规则。</p>
<p>做完点「复制结果」，粘贴到对话里发给我。随时可以停，下次打开会接着上次的进度。</p>
"""


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root = os.path.join(REPO, "data", "lsptest", "runs", CAMPAIGN)
    tdir = os.path.join(root, "triage")
    seeds = read_decisions(os.path.join(tdir, "decisions.csv"))
    bugs = [gid for gid, s in seeds.items() if s["choice"] == "bug"]
    groups = ordered(load(os.path.join(tdir, "triage.json"))["groups"])
    flagged = [g for g in groups if g["gid"] in FLAGGED]
    rest = [g for g in groups if g["gid"] in bugs and g["gid"] not in FLAGGED]
    body: List[str] = ["<h2>一、判断看起来不一致的 6 组</h2>"]
    for n, g in enumerate(flagged, 1):
        body.append(f'<p class="differ">为什么请你再看：{html.escape(FLAGGED[g["gid"]])}</p>')
        body.append(group_html(n, g, tdir, {}, seeds.get(g["gid"], {})))
    body.append("<h2>二、判为 bug 的组：每组写一句理由</h2>")
    for n, g in enumerate(rest, len(flagged) + 1):
        body.append(group_html(n, g, tdir, {}, seeds.get(g["gid"], {})))
    chosen = {g["gid"]: seeds[g["gid"]] for g in flagged + rest if g["gid"] in seeds}
    head = INTRO.format(n=len(flagged) + len(rest), bugs=len(rest))
    page = page_html("triage", f"{CAMPAIGN}-recheck", "复看", head, "\n".join(body), chosen, len(flagged) + len(rest))
    out = os.path.join(tdir, "recheck.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {os.path.relpath(out, REPO)}: {len(flagged)} flagged + {len(rest)} bug groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
