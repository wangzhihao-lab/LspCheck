"""The discussion page on which the first author and the second rater settle the items they judged differently.

Rules (plan/rater2_protocol.md, the rules fixed on 2026-11-18, item 1): only items the two
judged differently are discussed: the finding groups of main_v1 and main_v2 whose verdicts differ (bug /
legitimate / tool-artifact, any difference) and the benchmark signatures of bench_v1 whose answers differ
(yes / partial / no). During the discussion each side may see the other's verdict and reason and may replay.
Each item gets one joint verdict, one sentence of reason and whose original verdict it follows (author,
second rater, both changed). An item still unsettled after the discussion counts as not a bug (groups,
recorded as unresolved) or as not detected (signatures, recorded as no). The counts of the paper use these
joint verdicts; kappa stays on the two independent verdicts.

Inputs (read only): for each triage campaign, triage/triage.json, decisions.csv (the author; the class is
the 'L4：' style prefix of maintainer_response when there is no verdict_reasons.csv), verdict_reasons.csv
(main_v1: the author's class and English reason), rater2_decisions.csv, the groups' report.md,
sweep/older-2025/results.jsonl, root_causes.csv (main_v1) and, when present, evidence/open_groups_push-wait.json
and evidence/open_groups_ts-definition.json (scripts/paper/evidence/open_groups_v2.py); for bench_v1,
detection.json, detection_author.csv, detection_rater2.csv, the first vid's violations/<vid>/repro.json and
data/lsp_bench/cases/<case>/case.json.

Writes data/lsptest/adjudication/adjudication.html: self-contained, works offline, Chinese interface. The
discussion state stays in the browser (localStorage key tse2-adjudication:v1) and leaves as
adjudication_results.json; scripts/paper/import_adjudication.py writes it into the consensus files.

Run line: python3 scripts/paper/adjudication_page.py
"""

from __future__ import annotations

import csv
import html
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import detection_workbook as dw
import rater2_workbook as rw
import triage_workbook as tw

REPO = tw.REPO
PAGE = "adjudication"
STORE_KEY = "tse2-adjudication:v1"
EXPORT_NAME = "adjudication_results.json"
TRIAGE_CAMPAIGNS: Tuple[str, ...] = ("main_v1", "main_v2")
BENCH_CAMPAIGN = "bench_v1"
EXPECTED: Dict[str, int] = {"main_v1": 23, "main_v2": 5, "bench_v1": 7}
BATCH: Dict[str, str] = {"main_v1": "第一批（main_v1）", "main_v2": "第二批（main_v2）", "bench_v1": "基准签名（bench_v1）"}
CHOICES: Dict[str, Tuple[str, ...]] = {"group": ("bug", "legitimate", "tool-artifact"), "signature": ("yes", "no", "partial")}
LABELS: Dict[str, Dict[str, str]] = {"group": dict(rw.LABELS), "signature": dict(tw.LABELS["detection"])}
FOLLOWED: Tuple[Tuple[str, str], ...] = (("author", "作者"), ("rater2", "第二评判人"), ("both", "两人都改"))
CLASS_PREFIX_RE = re.compile(r"^\s*([LA][1-7])\s*[：:]")
CLASS_TEXT: Dict[str, str] = {c: t for cl in rw.CLASSES.values() for c, t in cl}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Side:
    """One judge's original verdict on an item: verdict, class and the notes shown on the page."""
    verdict: str
    cls: str
    notes: Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class Dispute:
    """An item the two judged differently. kind is group or signature; id is the group name or '<case>|<signature>'."""
    kind: str
    campaign: str
    id: str
    author: Side
    rater2: Side

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.campaign}:{self.id}"


def runs_dir(repo: Optional[str] = None) -> str:
    return os.path.join(repo or REPO, "data", "lsptest", "runs")


def csv_rows(path: str) -> List[Dict[str, str]]:
    """The rows of a CSV file ([] when it does not exist)."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in r.items()} for r in csv.DictReader(f)]


def class_prefix(note: str) -> str:
    """The class code written at the start of an author's note ('L4：…' -> 'L4'), or ''."""
    m = CLASS_PREFIX_RE.match(note or "")
    return m.group(1) if m else ""


# ------------------------------------------------------------------ verdicts
def triage_judgements(campaign: str, repo: Optional[str] = None) -> Tuple[Dict[str, Side], Dict[str, Side]]:
    """(author, second rater) sides of every judged group of a triage campaign."""
    tdir = os.path.join(runs_dir(repo), campaign, "triage")
    reasons = {r["group"]: r for r in csv_rows(os.path.join(tdir, "verdict_reasons.csv"))}
    author: Dict[str, Side] = {}
    for r in csv_rows(os.path.join(tdir, "decisions.csv")):
        verdict = r.get("verdict", "").strip()
        if not verdict:
            continue
        note = r.get("maintainer_response", "").strip()
        why = reasons.get(r["group"], {})
        if why and why.get("verdict", verdict) != verdict:
            logger.warning("%s %s: verdict_reasons.csv says %s, decisions.csv %s", campaign, r["group"],
                           why.get("verdict"), verdict)
        notes: List[Tuple[str, str]] = []
        if note:
            notes.append(("判定时的备注（decisions.csv）", note))
        if why.get("reason"):
            notes.append((f"理由（verdict_reasons.csv，{why.get('source') or '来源未记'}）", why["reason"]))
        author[r["group"]] = Side(verdict, why.get("class", "").strip() or class_prefix(note), tuple(notes))
    rater2 = {r["group"]: Side(r["verdict"].strip(), r.get("class", "").strip(),
                               (("备注", r["note"].strip()),) if r.get("note", "").strip() else ())
              for r in csv_rows(os.path.join(tdir, "rater2_decisions.csv")) if r.get("verdict", "").strip()}
    return author, rater2


def group_signatures(campaign: str, repo: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """gid -> the group's entry of triage.json."""
    return {g["gid"]: g for g in tw.load(os.path.join(runs_dir(repo), campaign, "triage", "triage.json"))["groups"]}


def relation_rank(signature: str) -> int:
    oracle = signature.split("|")[1] if signature.count("|") >= 1 else ""
    return int(oracle[1]) if len(oracle) > 1 and oracle[1].isdigit() else 99


def triage_disputes(campaign: str, repo: Optional[str] = None) -> List[Dispute]:
    """The groups of a campaign both judged with different verdicts, by relation R0..R6, then group name."""
    author, rater2 = triage_judgements(campaign, repo)
    groups = group_signatures(campaign, repo)
    out = [Dispute("group", campaign, g, author[g], rater2[g]) for g in author
           if g in rater2 and author[g].verdict != rater2[g].verdict]
    unknown = [d.id for d in out if d.id not in groups]
    if unknown:
        raise ValueError(f"{campaign}: disputed groups not in triage.json: {unknown}")
    return sorted(out, key=lambda d: (relation_rank(groups[d.id]["signature"]), d.id))


def detection_judgements(repo: Optional[str] = None) -> Tuple[Dict[str, Side], Dict[str, Side]]:
    """(author, second rater) sides of the benchmark signatures, keyed '<case>|<signature>'."""
    run = os.path.join(runs_dir(repo), BENCH_CAMPAIGN)
    author = {f"{r['case']}|{r['signature']}": Side(r["author_match"].strip(), "",
                                                     (("备注", r["note"].strip()),) if r.get("note", "").strip() else ())
              for r in csv_rows(os.path.join(run, "detection_author.csv")) if r.get("author_match", "").strip()}
    rater2 = {f"{r['case']}|{r['signature']}": Side(r["verdict"].strip(), "",
                                                     (("备注", r["note"].strip()),) if r.get("note", "").strip() else ())
              for r in csv_rows(os.path.join(run, "detection_rater2.csv")) if r.get("verdict", "").strip()}
    return author, rater2


def detection_disputes(repo: Optional[str] = None) -> List[Dispute]:
    """The signatures both judged with different answers, by case, then signature."""
    author, rater2 = detection_judgements(repo)
    out = [Dispute("signature", BENCH_CAMPAIGN, k, author[k], rater2[k]) for k in author
           if k in rater2 and author[k].verdict != rater2[k].verdict]
    return sorted(out, key=lambda d: tuple(d.id.split("|", 1)))


def all_disputes(repo: Optional[str] = None) -> List[Dispute]:
    """Every item to discuss, in page order: main_v1 groups, main_v2 groups, bench_v1 signatures."""
    out: List[Dispute] = []
    for campaign in TRIAGE_CAMPAIGNS:
        out += triage_disputes(campaign, repo)
    return out + detection_disputes(repo)


def auto_verdict(d: Dispute) -> str:
    """The verdict an unresolved item gets: a group takes the non-bug original verdict (the author's when both
    are non-bug); a signature takes no."""
    if d.kind == "signature":
        return "no"
    return d.author.verdict if d.author.verdict != "bug" else d.rater2.verdict


def cross_batch(disputes: Sequence[Dispute], repo: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """For each disputed group whose name also occurs in the other triage campaign: that campaign, the two
    verdicts and classes there and, when it is disputed there too, its position on this page."""
    sides = {c: triage_judgements(c, repo) for c in TRIAGE_CAMPAIGNS}
    names = {c: set(group_signatures(c, repo)) for c in TRIAGE_CAMPAIGNS}
    position = {d.key: i for i, d in enumerate(disputes, 1)}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for d in disputes:
        if d.kind != "group":
            continue
        for other in TRIAGE_CAMPAIGNS:
            if other == d.campaign or d.id not in names[other]:
                continue
            a, r = sides[other][0].get(d.id), sides[other][1].get(d.id)
            out.setdefault(d.key, []).append({
                "campaign": other, "author": a, "rater2": r,
                "position": position.get(f"group:{other}:{d.id}")})
    return out


# ------------------------------------------------------------------ evidence
INLINE_RE = re.compile(r"`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\((https?://[^)\s]+)\)")


def _inline(text: str) -> str:
    """Inline markdown of one escaped line: code spans, bold and http links."""
    out, last = [], 0
    for m in INLINE_RE.finditer(text):
        out.append(html.escape(text[last:m.start()]))
        if m.group(1) is not None:
            out.append(f"<code>{html.escape(m.group(1))}</code>")
        elif m.group(2) is not None:
            out.append(f"<b>{html.escape(m.group(2))}</b>")
        else:
            out.append(f'<a href="{html.escape(m.group(4))}" target="_blank" rel="noopener">{html.escape(m.group(3))}</a>')
        last = m.end()
    return "".join(out) + html.escape(text[last:])


def markdown_html(text: str) -> str:
    """The simple markdown of report.md as HTML: headings, fenced code, lists, paragraphs, inline code and links."""
    out: List[str] = []
    para: List[str] = []
    lst = ""
    fence: Optional[List[str]] = None

    def flush() -> None:
        nonlocal lst
        if para:
            out.append("<p>" + " ".join(_inline(x) for x in para) + "</p>")
            para.clear()
        if lst:
            out.append(f"</{lst}>")
            lst = ""

    for line in text.splitlines():
        if fence is not None:
            if line.strip().startswith("```"):
                out.append("<pre>" + html.escape("\n".join(fence)) + "</pre>")
                fence = None
            else:
                fence.append(line)
            continue
        if line.strip().startswith("```"):
            flush()
            fence = []
            continue
        head = re.match(r"^(#{1,6})\s+(.*)$", line)
        item = re.match(r"^\s*(?:([-*])|(\d+)\.)\s+(.*)$", line)
        if head:
            flush()
            level = min(6, len(head.group(1)) + 3)
            out.append(f"<h{level}>{_inline(head.group(2))}</h{level}>")
        elif item:
            kind = "ul" if item.group(1) else "ol"
            if para:
                out.append("<p>" + " ".join(_inline(x) for x in para) + "</p>")
                para.clear()
            if lst != kind:
                if lst:
                    out.append(f"</{lst}>")
                out.append(f"<{kind}>")
                lst = kind
            out.append(f"<li>{_inline(item.group(3))}</li>")
        elif not line.strip():
            flush()
        else:
            if lst:
                out.append(f"</{lst}>")
                lst = ""
            para.append(line.strip())
    if fence is not None:
        out.append("<pre>" + html.escape("\n".join(fence)) + "</pre>")
    flush()
    return '<div class="md">' + "\n".join(out) + "</div>"


def sweep_rows(campaign: str, repo: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    return rw.read_sweep(os.path.join(runs_dir(repo), campaign))


def sweep_html(row: Optional[Mapping[str, Any]]) -> str:
    """The year-old version sweep of one group: the sentence of the judging pages and the raw fields."""
    if not row:
        return "<p>未重放（该组没有一年前版本的重放记录）</p>"
    fields = {k: row.get(k) for k in ("verdict", "build", "replays", "settled", "control_stable", "reproduced",
                                      "seconds", "error") if k in row}
    return (f"<p>{html.escape(rw.sweep_text(row))}</p>"
            f"<pre>{html.escape(json.dumps(fields, ensure_ascii=False, sort_keys=True))}</pre>")


def root_causes(campaign: str, repo: Optional[str] = None) -> Dict[str, Tuple[str, str]]:
    """gid -> (cause id, description) from the campaign's root_causes.csv ({} when there is none)."""
    path = os.path.join(runs_dir(repo), campaign, "triage", "root_causes.csv")
    return {r["group"]: (r["cause"], r.get("description", "")) for r in csv_rows(path)}


def open_group_rows(campaign: str, repo: Optional[str] = None) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """subcommand -> gid -> rows of the campaign's evidence/open_groups_<subcommand>.json files that exist."""
    out: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for sub in ("push-wait", "ts-definition"):
        path = os.path.join(runs_dir(repo), campaign, "evidence", f"open_groups_{sub}.json")
        if not os.path.exists(path):
            continue
        for row in tw.load(path).get("rows", []):
            out.setdefault(sub, {}).setdefault(str(row.get("gid")), []).append(row)
    return out


def _codes(codes: Optional[Mapping[str, int]]) -> str:
    return "、".join(f"{k} × {v}" for k, v in (codes or {}).items()) or "无"


def push_wait_text(row: Mapping[str, Any]) -> str:
    """One push-wait row in Chinese: how long the push session stayed open after it settled, whether new
    publications came, and what the pull session gave."""
    if row.get("error"):
        return f"重放出错：{row['error']}"
    server = row.get("server") or {}
    timeline = list(row.get("push_timeline") or [])
    first = timeline[0] if timeline else None
    later = [t for t in timeline[1:]]
    pull_decl = "声明了" if row.get("push_pull_mode") else "没有声明"
    start = ("稳定时文件上还没有任何发布" if not first or first.get("n") is None else
             f"稳定时文件上是第 {first.get('publish_index')} 次发布（{first.get('n')} 条：{_codes(first.get('codes'))}）")
    if later:
        news = "；".join(f"第 {t.get('after_snapshot_s')} 秒 {t.get('n')} 条（{_codes(t.get('codes'))}）" for t in later)
        news = f"期间有 {len(later)} 次新的推送：{news}"
    else:
        news = "期间没有新的推送"
    pull = (f"拉取会话出错：{row['pull_error']}" if row.get("pull_error") else
            f"随后的拉取会话在同一文件给出 {row.get('pull_n')} 条诊断（{_codes(row.get('pull_codes'))}）")
    return (f"{server.get('kind', '')} {server.get('version', '')}，文件 <code>{html.escape(str(row.get('path', '')))}</code>："
            f"推送会话的客户端{pull_decl}拉取能力；{html.escape(start)}；稳定后再开 {row.get('wait_s')} 秒，"
            f"{html.escape(news)}。{html.escape(pull)}。")


def _place(spot: Optional[Sequence[Any]]) -> str:
    return f"{spot[0]} {spot[1]}:{spot[2]}" if spot and len(spot) >= 3 else "?"


def _defs(defs: Optional[Sequence[Sequence[Any]]], err: Any) -> str:
    if err:
        return f"出错（{err}）"
    defs = list(defs or [])
    if not defs:
        return "为空"
    shown = "；".join(f"{d[0]} {d[1]}:{d[2]}" for d in defs[:4])
    return f"{len(defs)} 处（{shown}{'……' if len(defs) > 4 else ''}）"


def ts_definition_text(row: Mapping[str, Any]) -> str:
    """One ts-definition row in Chinese: go-to-definition at both places, hover and diagnostics of the line."""
    build = " ".join(str(x) for x in row.get("build") or [])
    if row.get("error"):
        return f"{html.escape(build)}：重放出错：{html.escape(str(row['error']))}"
    diags = "；".join(f"{d.get('code')} “{d.get('message')}”" for d in row.get("diagnostics_on_reference_line") or [])
    hover = str(row.get("hover_at_reference") or "").replace("```typescript", "").replace("```", "").strip()
    return html.escape(
        f"{build}：在 {_place(row.get('target'))} 跳定义 {_defs(row.get('definition_at_target'), row.get('definition_at_target_error'))}；"
        f"在 {_place(row.get('reference'))} 跳定义 {_defs(row.get('definition_at_reference'), row.get('definition_at_reference_error'))}；"
        f"那一行的诊断：{diags or '无'}；那个文件的诊断：{_codes(row.get('diagnostics_reference_file_codes'))}；"
        f"悬停：{hover or '无'}")


def open_groups_html(gid: str, rows: Mapping[str, Mapping[str, List[Dict[str, Any]]]]) -> str:
    """The extra replay evidence of one group, or '' when there is none."""
    parts: List[str] = []
    for row in rows.get("push-wait", {}).get(gid, []):
        parts.append(f"<li>推送等待（{html.escape(str(row.get('wait_s')))} 秒）：{push_wait_text(row)}</li>")
    for row in rows.get("ts-definition", {}).get(gid, []):
        parts.append(f"<li>跳定义对照：{ts_definition_text(row)}</li>")
    if not parts:
        return ""
    return ('<div class="extra"><b>补充重放证据（scripts/paper/evidence/open_groups_v2.py）</b><ul>'
            + "".join(parts) + "</ul></div>")


# ------------------------------------------------------------------ items
def side_html(title: str, side: Side, kind: str) -> str:
    """One judge's column: verdict, class with its meaning, notes."""
    label = LABELS[kind].get(side.verdict, "")
    cls = (f'<p>类别：<b>{html.escape(side.cls)}</b> {html.escape(CLASS_TEXT.get(side.cls, ""))}</p>'
           if side.cls else ('<p class="muted">类别：未选</p>' if kind == "group" and side.verdict != "bug" else ""))
    notes = "".join(f'<p class="muted">{html.escape(t)}</p><p class="why">{html.escape(x)}</p>' for t, x in side.notes) \
        or '<p class="muted">（没写理由）</p>'
    return (f'<div class="side"><h4>{html.escape(title)}</h4><p class="verdict">{html.escape(side.verdict)}'
            f' <small>{html.escape(label)}</small></p>{cls}{notes}</div>')


def sides_html(d: Dispute) -> str:
    return f'<div class="sides">{side_html("作者", d.author, d.kind)}{side_html("第二评判人", d.rater2, d.kind)}</div>'


def _short(side: Optional[Side]) -> str:
    if side is None:
        return "未判"
    return side.verdict + (f" / {side.cls}" if side.cls else "")


def cross_html(hints: Sequence[Mapping[str, Any]]) -> str:
    """The prompt for a group name that also occurs in the other batch."""
    parts: List[str] = []
    for h in hints:
        a, r = h["author"], h["rater2"]
        same = a is not None and r is not None and a.verdict == r.verdict
        where = (f"那一组也在本页讨论（第 {h['position']} 条）" if h.get("position") else
                 "那一组两人判得一样，不在本页讨论" if same else "那一组不在本页讨论")
        parts.append(f"<li>{html.escape(BATCH[h['campaign']])}也有同名的组：作者 <b>{html.escape(_short(a))}</b>，"
                     f"第二评判人 <b>{html.escape(_short(r))}</b>；{where}。</li>")
    return ('<div class="cross"><b>跨批同组</b>（两批的组号由签名和用例族决定，会重复；项目和现场可能不同）：<ul>'
            + "".join(parts) + "</ul>讨论时请前后一致；判得不同，理由里写明两批差在哪里。</div>")


def group_item(n: int, d: Dispute, k: int, total: int, g: Mapping[str, Any], report: str,
               sweep: Optional[Mapping[str, Any]], cause: Optional[Tuple[str, str]], extra: str,
               hints: Sequence[Mapping[str, Any]]) -> str:
    """One disputed group: who said what, then the evidence, then an empty discussion box."""
    secs = tw.sections(report)
    kind, oracle = g["signature"].split("|")[:2]
    relation = tw.RELATION.get(oracle, oracle)
    server = tw.section(secs, "Server")
    eid = html.escape(d.id)
    cause_html = (f'<p><b>根因</b>：{html.escape(cause[0])}（root_causes.csv）：{html.escape(cause[1])}</p>'
                  if cause else "")
    return f"""
<details class="item" id="item-{n}" data-key="{html.escape(d.key)}" data-kind="group" data-campaign="{html.escape(d.campaign)}" data-id="{eid}" data-n="{n}" data-auto="{html.escape(auto_verdict(d))}" data-author="{html.escape(d.author.verdict)}" data-rater2="{html.escape(d.rater2.verdict)}"><summary><b class="num">{n}.</b> <span class="state open">未开始</span> <span class="batch">{html.escape(BATCH[d.campaign])} 组 {k}/{total}</span> <code>{eid}</code> · {html.escape(relation)} · {html.escape(kind)} · 作者 {html.escape(_short(d.author))} ↔ 第二评判人 {html.escape(_short(d.rater2))}{' · <span class="crossmark">跨批同组</span>' if hints else ''}</summary>
<div class="body">
<h3>{html.escape(secs.get('title', d.id))}</h3>
<p><b>批次</b>：{html.escape(BATCH[d.campaign])}；<b>组号</b>：<code>{eid}</code>；<b>关系</b>：{html.escape(relation)}；<b>服务器</b>：{html.escape(kind)}；成员 {g.get('members')}，步骤 {g.get('ops_before')}→{g.get('ops_after')}</p>
<p><b>服务器与项目</b>：</p><pre>{html.escape(server)}</pre>
{sides_html(d)}
{cross_html(hints) if hints else ''}
{cause_html}
{extra}
<details class="evidence"><summary>证据：一年前版本上的重放</summary>{sweep_html(sweep)}</details>
<details class="evidence"><summary>证据：完整报告（triage/{eid}/report.md）</summary>{markdown_html(report)}</details>
<div class="judge"></div>
</div></details>"""


def case_info_html(case: Mapping[str, Any], spec: Mapping[str, Any]) -> str:
    """The benchmark's own description of the historical bug: builds, reproduction steps and probe."""
    repro = spec.get("repro") or {}
    probe = str((repro.get("probe") or {}).get("type") or case.get("probe") or "")
    builds = case.get("builds") or {}
    return (f'<p><b>历史 bug</b>：<a href="{html.escape(str(case["url"]))}" target="_blank" rel="noopener">'
            f'{html.escape(str(case["title"]))}</a> <span class="muted">（{html.escape(str(case.get("kind", "")))}，'
            f'修复前 {html.escape(str(builds.get("pre", "?")))}，修复后 {html.escape(str(builds.get("post", "?")))}）</span></p>'
            f'<p><b>基准里这个 bug 的复现步骤</b>：{html.escape(str(repro.get("steps") or "（case.json 里没有）"))}</p>'
            f'<p><b>基准的探针</b>：<code>{html.escape(probe)}</code>'
            + (f"（{html.escape(dw.PROBE[probe])}）" if probe in dw.PROBE else "") + "</p>")


def signature_item(n: int, d: Dispute, k: int, total: int, case: Mapping[str, Any], p: Mapping[str, Any],
                   spec: Mapping[str, Any], repro: Mapping[str, Any]) -> str:
    """One disputed benchmark signature: who said what, the evidence of the detection pages, an empty box."""
    case_name, sig = d.id.split("|", 1)
    oracle = str(p.get("oracle", ""))
    raw = json.dumps(repro, indent=1, ensure_ascii=False, sort_keys=True)
    return f"""
<details class="item" id="item-{n}" data-key="{html.escape(d.key)}" data-kind="signature" data-campaign="{html.escape(d.campaign)}" data-id="{html.escape(d.id)}" data-n="{n}" data-auto="no" data-author="{html.escape(d.author.verdict)}" data-rater2="{html.escape(d.rater2.verdict)}"><summary><b class="num">{n}.</b> <span class="state open">未开始</span> <span class="batch">{html.escape(BATCH[d.campaign])} 第 {k}/{total} 条</span> {html.escape(case_name)} · {html.escape(tw.RELATION.get(oracle, oracle))} · <code>{html.escape(sig.split('|', 2)[-1])}</code> · 作者 {html.escape(d.author.verdict)} ↔ 第二评判人 {html.escape(d.rater2.verdict)}</summary>
<div class="body">
<p><b>批次</b>：{html.escape(BATCH[d.campaign])}；<b>历史 bug</b>：{html.escape(case_name)}；<b>签名</b>：<code>{html.escape(sig)}</code>；<b>关系</b>：{html.escape(tw.RELATION.get(oracle, oracle))}；<b>服务器</b>：{html.escape(str(case.get('kind', '')))}</p>
<p class="q2">问题：{html.escape(dw.QUESTION)}</p>
{sides_html(d)}
<details class="evidence" open><summary>证据：issue、基准的复现步骤与探针、工具在修复前版本上的发现</summary>
{case_info_html(case, spec)}
{dw.evidence_html(case, p, repro, '下面的完整原始记录')}
<details class="report"><summary>完整原始记录（repro.json 原文）</summary><pre>{html.escape(raw)}</pre></details>
</details>
<div class="judge"></div>
</div></details>"""


# ------------------------------------------------------------------ page
EXTRA_CSS = """
.sides{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0} .side{border:1px solid #bbb;border-radius:6px;padding:6px 10px}
.side h4{margin:2px 0 4px;color:#332288} .verdict{font-size:1.2em;font-weight:bold;margin:2px 0} .verdict small{font-size:12px;font-weight:normal;color:#555}
.why{white-space:pre-wrap;margin:0 0 8px} .batch{color:#332288;font-size:12px} .crossmark{color:#CC6677;font-size:12px}
.cross{border-left:4px solid #CC6677;background:#fbf0f2;padding:6px 10px;margin:8px 0}
.extra{border-left:4px solid #44AA99;background:#eef7f5;padding:6px 10px;margin:8px 0}
.part{background:#88CCEE} button.choice:disabled{opacity:.35;cursor:not-allowed} .warn{color:#882255;font-weight:bold}
.followed label,.unresolved{display:inline-block;margin:6px 14px 0 0;font-size:14px} .rules li{margin:3px 0}
.md h4,.md h5,.md h6{margin:.8em 0 .3em} .q2{font-weight:bold}
@media (max-width:760px){.sides{grid-template-columns:1fr}}
"""
BAR = """<div class="bar"><span id="progress">已完成 0 / {n}</span>
<button type="button" id="copy">复制结果</button><button type="button" id="download">下载结果文件</button>
<button type="button" id="next">下一条未完成</button>
<label class="restore">从结果文件恢复：<input type="file" id="restore" accept=".json,application/json"></label>
<span id="message"></span>
<span id="storage-warning" hidden>这个浏览器不让本页保存进度：关掉页面前请先点「下载结果文件」。</span></div>
<div id="export-box" hidden><p id="export-why"></p><textarea id="export-text" readonly></textarea></div>
"""


def intro(counts: Mapping[str, int], cross: int) -> str:
    """The rules of the discussion (as fixed beforehand), the judging criteria and the class table."""
    import detection_rater2 as dr  # the meanings of yes / no / partial shown to the second rater
    n = sum(counts.values())
    legend = "".join(f"<tr><td>{c}</td><td>{html.escape(t)}</td><td>{html.escape(v)}</td></tr>"
                     for v, cl in rw.CLASSES.items() for c, t in cl)
    meaning = "".join(f"<tr><td>{c}</td><td>{html.escape(t)}</td></tr>" for c, t in dr.MEANING)
    return f"""<h1>分歧讨论页：第一作者与第二评判人（{n} 条）</h1>
<p>本页列出两人各自独立判过、而判定不同的全部条目：{html.escape(BATCH['main_v1'])}的组 {counts.get('main_v1', 0)} 组，{html.escape(BATCH['main_v2'])}的组 {counts.get('main_v2', 0)} 组，{html.escape(BATCH['bench_v1'])} {counts.get('bench_v1', 0)} 条。规则是两批开判之前事先定的（plan/rater2_protocol.md，11-18 定的规则第 1 条）：</p>
<ul class="rules">
<li><b>只讨论两人判定不同的条目</b>：组的三类判定（bug、legitimate、tool-artifact）任何不同都算，包括 legitimate 和 tool-artifact 之分；基准签名 yes、partial、no 不同的。两人判定相同的不再讨论，本页也不列。</li>
<li><b>怎么讨论</b>：可以看对方的判定和理由（每条下面左右并排），可以重放复现命令。</li>
<li><b>每条定一个共同判定</b>，写一句理由，并记下最后跟的是谁的原判：共同判定等于作者的原判，选“作者”；等于第二评判人的原判，选“第二评判人”；两边的原判都不是，选“两人都改”。只看判定（三类或 yes、no、partial），类别不同不影响这一项。</li>
<li><b>讨论后仍定不下来的</b>：勾“讨论后仍定不下来”。组按不是 bug 算（记 unresolved；判定自动取两人原判里不是 bug 的那个，可改选另一种不是 bug 的判定），签名按不算检出算（记 no）。往少算的方向定，存疑的不进 bug 数和检出数；附件里单独列出。</li>
<li><b>论文怎么算</b>：bug 组数、不同 bug 数、基准检出数用讨论后的判定；κ 仍按讨论前两人各自的判定算。讨论后新成为 bug 的组，由第一作者归到已有的根因或新根因（C 编号），不同 bug 数重算。</li>
<li><b>记在哪</b>：讨论结果单独存（各批 triage 目录下的 consensus.csv，基准在 bench_v1/detection_consensus.csv）；decisions.csv、rater2_decisions.csv、detection_author.csv、detection_rater2.csv 和评判人的原始导出都不动。</li>
</ul>
<p>顺序：{html.escape(BATCH['main_v1'])}的组（按关系 R0→R6，再按组号），{html.escape(BATCH['main_v2'])}的组（同样排），最后是基准签名（按历史 bug、再按签名）。组号在另一批也出现的（{cross} 条），标“跨批同组”，并列出另一批里两人各自的判定，讨论时请前后一致。</p>
<p>进度自动存在这个浏览器里（键名 <code>{STORE_KEY}</code>）；换浏览器、换电脑或清除浏览器数据会丢。讨论完（或中途停下）请点「下载结果文件」（{EXPORT_NAME}）留底，换电脑时用「从结果文件恢复」接着做。导入：<code>python3 scripts/paper/import_adjudication.py {EXPORT_NAME} --dry-run</code>，再去掉 <code>--dry-run</code>。</p>
<details><summary>判定标准原文（论文 VI-A）</summary><div class="criteria">{html.escape(rw.CRITERIA_EN)}</div></details>
<details><summary>例外类别一览</summary><table class="legend"><tr><th>类别</th><th>含义</th><th>用于</th></tr>{legend}</table></details>
<details><summary>基准签名的问题和 yes、no、partial 的含义</summary><p>{html.escape(dw.QUESTION)}</p><table class="legend">{meaning}</table><p>{html.escape(dr.COUNT_RULE)}</p></details>
"""


SCRIPT = r"""(function () {
  "use strict";
  var cfg = JSON.parse(document.getElementById("adjudication-config").textContent);
  var items = Array.prototype.slice.call(document.querySelectorAll("details.item"));
  var state = {}, byKey = {}, current = -1, canStore = true;
  function $(id) { return document.getElementById(id); }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }
  function keyOf(item) { return item.getAttribute("data-key"); }
  function kindOf(item) { return item.getAttribute("data-kind"); }
  function now() { return new Date().toISOString(); }
  function classesFor(item, v) { return kindOf(item) === "group" ? (cfg.classes[v] || []) : []; }
  function classOk(item, v, c) { return classesFor(item, v).some(function (x) { return x[0] === c; }); }
  function allowed(item, s, v) { return !s.unresolved || cfg.unresolvedOk[kindOf(item)].indexOf(v) >= 0; }
  function followedOk(f) { return cfg.followed.some(function (x) { return x[0] === f; }); }
  function clean(item, s) {
    s = s && typeof s === "object" ? s : {};
    var st = {verdict: cfg.choices[kindOf(item)].indexOf(s.verdict) >= 0 ? s.verdict : "", cls: "",
              followed: followedOk(s.followed) ? s.followed : "", unresolved: s.unresolved === true,
              reason: typeof s.reason === "string" ? s.reason : "",
              decided_at: typeof s.decided_at === "string" ? s.decided_at : ""};
    if (st.unresolved && !allowed(item, st, st.verdict)) { st.verdict = item.getAttribute("data-auto"); }
    st.cls = classOk(item, st.verdict, s["class"] !== undefined ? s["class"] : s.cls) ? (s["class"] !== undefined ? s["class"] : s.cls) : "";
    if (!st.verdict) { st.decided_at = ""; }
    return st;
  }
  function complete(s) { return !!(s.verdict && (s.followed || s.unresolved) && s.reason.trim()); }
  function touched(s) { return !!(s.verdict || s.followed || s.unresolved || s.reason.trim()); }
  function load() {
    var raw = null, data = null;
    try { raw = window.localStorage.getItem(cfg.key); } catch (e) { canStore = false; }
    try { data = raw ? JSON.parse(raw) : null; } catch (e) { data = null; }
    return data && data.items && typeof data.items === "object" ? data.items : {};
  }
  function save() {
    var out = {};
    items.forEach(function (item) { var s = state[keyOf(item)]; if (touched(s)) { out[keyOf(item)] = s; } });
    try { window.localStorage.setItem(cfg.key, JSON.stringify({version: 1, items: out})); canStore = true; }
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
    var box = item.querySelector(".judge"), kind = kindOf(item), n = item.getAttribute("data-n");
    box.appendChild(el("p", "q", cfg.question[kind]));
    cfg.choices[kind].forEach(function (c) {
      var b = el("button", "choice");
      b.type = "button"; b.setAttribute("data-choice", c); b.setAttribute("aria-pressed", "false");
      b.appendChild(el("b", "", c)); b.appendChild(el("small", "", cfg.labels[kind][c]));
      box.appendChild(b);
    });
    var clear = el("button", "clear", "清除判定"); clear.type = "button"; box.appendChild(clear);
    if (kind === "group") {
      var lab = el("label", "cls-label", "类别（不是 bug 时可选）：");
      lab.appendChild(el("select", "cls")); box.appendChild(lab);
    }
    var fol = el("div", "followed"); fol.appendChild(el("span", "", "跟的是谁的原判："));
    cfg.followed.forEach(function (f) {
      var l = el("label"), r = el("input");
      r.type = "radio"; r.name = "followed-" + n; r.value = f[0]; l.appendChild(r); l.appendChild(document.createTextNode(" " + f[1]));
      fol.appendChild(l);
    });
    box.appendChild(fol);
    var un = el("label", "unresolved"), cb = el("input");
    cb.type = "checkbox"; cb.className = "unresolved-box"; un.appendChild(cb);
    un.appendChild(document.createTextNode(" " + cfg.unresolvedText[kind])); box.appendChild(un);
    var note = el("textarea", "note"); note.rows = 2; note.placeholder = cfg.placeholder; box.appendChild(note);
    box.appendChild(el("p", "warn"));
  }
  function fillSelect(item, sel, s) {
    var list = classesFor(item, s.verdict);
    while (sel.firstChild) { sel.removeChild(sel.firstChild); }
    var none = el("option", "", list.length ? "（不选）" : "（选了 legitimate 或 tool-artifact 之后才能选）");
    none.value = ""; sel.appendChild(none);
    list.forEach(function (c) { var o = el("option", "", c[0] + "  " + c[1]); o.value = c[0]; sel.appendChild(o); });
    sel.disabled = !list.length; sel.value = s.cls;
  }
  function warning(item, s) {
    var f = s.followed, v = s.verdict, a = item.getAttribute("data-author"), r = item.getAttribute("data-rater2");
    if (!f || !v) { return ""; }
    if (f === "author" && v !== a) { return "选了“作者”，但共同判定 " + v + " 不是作者的原判 " + a + "。"; }
    if (f === "rater2" && v !== r) { return "选了“第二评判人”，但共同判定 " + v + " 不是第二评判人的原判 " + r + "。"; }
    if (f === "both" && (v === a || v === r)) { return "选了“两人都改”，但共同判定 " + v + " 就是一方的原判。"; }
    return "";
  }
  function render(item) {
    var s = state[keyOf(item)], note = item.querySelector("textarea.note");
    each(item.querySelectorAll("button.choice"), function (b) {
      var c = b.getAttribute("data-choice"), on = c === s.verdict;
      b.classList.toggle("chosen", on); b.setAttribute("aria-pressed", on ? "true" : "false");
      b.disabled = !allowed(item, s, c);
    });
    var sel = item.querySelector("select.cls");
    if (sel) { fillSelect(item, sel, s); }
    each(item.querySelectorAll(".followed input"), function (r) { r.checked = r.value === s.followed; });
    item.querySelector("input.unresolved-box").checked = s.unresolved;
    var badge = item.querySelector(".state");
    if (complete(s)) {
      badge.textContent = "已定：" + s.verdict + (s.cls ? " / " + s.cls : "") + (s.unresolved ? "（未定下来）" : "");
      badge.className = "state done";
    } else {
      badge.textContent = touched(s) ? "未完成" : "未开始";
      badge.className = "state " + (touched(s) ? "part" : "open");
    }
    item.querySelector("p.warn").textContent = warning(item, s);
    if (note.value !== s.reason && document.activeElement !== note) { note.value = s.reason; }
  }
  function progress() {
    var done = items.filter(function (item) { return complete(state[keyOf(item)]); }).length;
    $("progress").textContent = "已完成 " + done + " / " + items.length;
  }
  function touch(item) { save(); render(item); progress(); }
  function say(text) { $("message").textContent = text; }
  function exportText() {
    var out = [];
    items.forEach(function (item) {
      var s = state[keyOf(item)];
      if (touched(s)) {
        out.push(JSON.stringify({n: Number(item.getAttribute("data-n")), kind: kindOf(item),
                                 campaign: item.getAttribute("data-campaign"), id: item.getAttribute("data-id"),
                                 verdict: s.verdict, "class": s.cls, followed: s.followed, unresolved: s.unresolved,
                                 reason: s.reason.trim(), decided_at: s.decided_at}));
      }
    });
    var head = JSON.stringify({page: cfg.page, generated_at: now(), total: items.length});
    $("export-text").value = head.slice(0, -1) + ',"items":[\n' + out.join(",\n") + "\n]}\n";
    return {text: $("export-text").value, count: out.length};
  }
  function manual(why) {
    $("export-why").textContent = why; $("export-box").hidden = false;
    $("export-box").scrollIntoView({block: "center"}); $("export-text").focus(); $("export-text").select();
  }
  var stored = load();
  items.forEach(function (item, i) {
    var key = keyOf(item);
    byKey[key] = item;
    build(item);
    state[key] = clean(item, Object.prototype.hasOwnProperty.call(stored, key) ? stored[key] : null);
    item.addEventListener("toggle", function () { if (item.open) { current = i; } });
    each(item.querySelectorAll("button.choice"), function (b) {
      b.addEventListener("click", function () {
        var s = state[key], v = b.getAttribute("data-choice");
        if (!allowed(item, s, v)) { return; }
        if (s.verdict !== v) { s.verdict = v; s.decided_at = now(); }
        if (!classOk(item, v, s.cls)) { s.cls = ""; }
        current = i; touch(item);
      });
    });
    item.querySelector("button.clear").addEventListener("click", function () {
      var s = state[key]; s.verdict = ""; s.cls = ""; s.decided_at = ""; s.unresolved = false; touch(item);
    });
    var sel = item.querySelector("select.cls");
    if (sel) {
      sel.addEventListener("change", function (e) {
        state[key].cls = classOk(item, state[key].verdict, e.target.value) ? e.target.value : ""; touch(item);
      });
    }
    each(item.querySelectorAll(".followed input"), function (r) {
      r.addEventListener("change", function () { if (r.checked) { state[key].followed = r.value; touch(item); } });
    });
    item.querySelector("input.unresolved-box").addEventListener("change", function (e) {
      var s = state[key];
      s.unresolved = e.target.checked;
      if (s.unresolved && !allowed(item, s, s.verdict)) {
        s.verdict = item.getAttribute("data-auto");
        if (!classOk(item, s.verdict, s.cls)) { s.cls = ""; }
      }
      if (s.verdict) { s.decided_at = now(); }
      touch(item);
    });
    item.querySelector("textarea.note").addEventListener("input", function (e) {
      state[key].reason = e.target.value; save(); render(item); progress();
    });
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
    } catch (e) { manual("下载没成功：请复制下面框里的全部内容，存成文本文件。"); }
  });
  $("restore").addEventListener("change", function (e) {
    var file = e.target.files && e.target.files[0];
    if (!file) { return; }
    var reader = new FileReader();
    reader.onload = function () {
      var data = null, n = 0;
      try { data = JSON.parse(String(reader.result)); } catch (err) { data = null; }
      if (!data || data.page !== cfg.page || !Array.isArray(data.items)) {
        say("这个文件不是本页导出的结果文件，没有恢复。"); e.target.value = ""; return;
      }
      var known = data.items.filter(function (it) {
        return it && Object.prototype.hasOwnProperty.call(byKey, it.kind + ":" + it.campaign + ":" + it.id);
      });
      if (!window.confirm("用文件里的 " + known.length + " 条结果覆盖本页同一条的内容？其他条不变。")) { e.target.value = ""; return; }
      known.forEach(function (it) {
        var key = it.kind + ":" + it.campaign + ":" + it.id;
        state[key] = clean(byKey[key], it); n += 1;
      });
      save(); items.forEach(render); progress(); say("已从文件恢复 " + n + " 条。"); e.target.value = "";
    };
    reader.readAsText(file, "utf-8");
  });
  $("next").addEventListener("click", function () {
    for (var k = 1; k <= items.length; k++) {
      var i = (current + k) % items.length;
      if (!complete(state[keyOf(items[i])])) {
        if (current >= 0 && current !== i) { items[current].open = false; }
        items[i].open = true; current = i; items[i].scrollIntoView({block: "start"}); say(""); return;
      }
    }
    say("全部都定了。");
  });
})();
"""


def config() -> Dict[str, Any]:
    """What the page script needs: choices, labels, classes, the followed options and the unresolved rule."""
    return {"page": PAGE, "key": STORE_KEY, "file": EXPORT_NAME,
            "choices": {k: list(v) for k, v in CHOICES.items()}, "labels": LABELS,
            "classes": {v: [list(c) for c in cl] for v, cl in rw.CLASSES.items()},
            "followed": [list(f) for f in FOLLOWED],
            "unresolvedOk": {"group": ["legitimate", "tool-artifact"], "signature": ["no"]},
            "unresolvedText": {"group": "讨论后仍定不下来（按规则记为不是 bug，标 unresolved）",
                               "signature": "讨论后仍定不下来（按规则记为 no，不算检出，标 unresolved）"},
            "question": {"group": "讨论后的共同判定（按论文 VI-A 的书面标准）：",
                         "signature": "讨论后的共同判定：" + dw.QUESTION},
            "placeholder": "理由：一句话，说明为什么这样定（讨论里看到的关键证据）"}


def build(repo: Optional[str] = None) -> Tuple[str, List[Dispute], Dict[str, List[Dict[str, Any]]]]:
    """(page, the disputed items in page order, the cross-batch hints by item key). Reads only; writes nothing."""
    repo = repo or REPO
    disputes = all_disputes(repo)
    hints = cross_batch(disputes, repo)
    counts = {c: sum(1 for d in disputes if d.campaign == c) for c in TRIAGE_CAMPAIGNS + (BENCH_CAMPAIGN,)}
    body: List[str] = []
    for campaign in TRIAGE_CAMPAIGNS:
        mine = [d for d in disputes if d.campaign == campaign]
        if not mine:
            continue
        body.append(f"<h2>{html.escape(BATCH[campaign])}：{len(mine)} 组</h2>")
        groups = group_signatures(campaign, repo)
        sweep = sweep_rows(campaign, repo)
        causes = root_causes(campaign, repo)
        extra = open_group_rows(campaign, repo)
        tdir = os.path.join(runs_dir(repo), campaign, "triage")
        for k, d in enumerate(mine, 1):
            with open(os.path.join(tdir, d.id, "report.md"), "r", encoding="utf-8") as f:
                report = f.read()
            n = disputes.index(d) + 1
            body.append(group_item(n, d, k, len(mine), groups[d.id], report, sweep.get(d.id), causes.get(d.id),
                                   open_groups_html(d.id, extra), hints.get(d.key, [])))
    sigs = [d for d in disputes if d.kind == "signature"]
    if sigs:
        run = os.path.join(runs_dir(repo), BENCH_CAMPAIGN)
        bench = os.path.join(repo, "data", "lsp_bench", "cases")
        cases = {str(c["case"]): c for c in tw.load(os.path.join(run, "detection.json"))["cases"]}
        body.append(f"<h2>{html.escape(BATCH[BENCH_CAMPAIGN])}：{len(sigs)} 条</h2>")
        for k, d in enumerate(sigs, 1):
            case_name, sig = d.id.split("|", 1)
            case = cases[case_name]
            p = next(x for x in case.get("pre_only", []) if str(x.get("signature")) == sig)
            spec = tw.load(os.path.join(bench, case_name, "case.json"))
            repro = tw.load(os.path.join(run, "violations", str(p["vids"][0]), "repro.json"))
            body.append(signature_item(disputes.index(d) + 1, d, k, len(sigs), case, p, spec, repro))
    data = json.dumps(config(), ensure_ascii=False, sort_keys=True)
    data = data.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    page = "".join([
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>分歧讨论页（{len(disputes)} 条）</title><style>{tw.CSS}{rw.EXTRA_CSS}{EXTRA_CSS}</style></head><body>\n",
        intro(counts, len(hints)), BAR.format(n=len(disputes)), "\n".join(body),
        f'\n<script type="application/json" id="adjudication-config">{data}</script>\n<script>\n{SCRIPT}</script>\n',
        "</body></html>\n"])
    return page, disputes, hints


def out_path(repo: Optional[str] = None) -> str:
    return os.path.join(repo or REPO, "data", "lsptest", "adjudication", "adjudication.html")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Write the page and print the disputed items; 1 when the counts differ from the expected 23 / 5 / 7."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    repo = args[args.index("--repo") + 1] if "--repo" in args else None
    page, disputes, hints = build(repo)
    path = out_path(repo)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    counts = {c: sum(1 for d in disputes if d.campaign == c) for c in EXPECTED}
    print(f"wrote {path}: {len(disputes)} items, {len(page.encode()) // 1024} KB")
    for i, d in enumerate(disputes, 1):
        mark = "  [cross-batch]" if d.key in hints else ""
        print(f"{i:3d} {d.campaign} {d.id}: author {d.author.verdict}{'/' + d.author.cls if d.author.cls else ''}"
              f", rater2 {d.rater2.verdict}{'/' + d.rater2.cls if d.rater2.cls else ''}{mark}")
    print("counts: " + ", ".join(f"{c} {n}" for c, n in counts.items()))
    if repo is None and counts != EXPECTED:
        logger.error("the counts differ from the expected %s", EXPECTED)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
