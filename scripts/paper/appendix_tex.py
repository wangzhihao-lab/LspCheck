"""LaTeX longtables of the appendix tables, for the supplemental material.

Reads the appendix tables that scripts/paper/paper_numbers.py writes to paper/appendix/tables
(C_capabilities, D_corpus, E_benchmark, F_detection, G_groups, G2_root_causes, G3_sensitivity, I_sweep, J_cost,
K_freeze, M_evidence, M2_isolation, M3_cross, M4_c1_checks, N1_lifecycle, N2_newest, N3_upstream) and one analysis
record, data/lsptest/runs/bench_v1/missed_attribution.csv (table F2_missed). G2_root_causes holds the root-cause
tables of both campaigns (one row per cause with the groups it merges, each marked with its corpus) and M_evidence
both evidence summaries (scripts/paper/numbers_release_cur.py).
Writes one longtable per table to paper/supplement/tables/<name>.tex, rows in
CSV order. Every cell is escaped (& % $ # _ { } ~ ^ \\ and, since the fonts are OT1, < > | and
straight quotes, which become curly ones); text in backticks becomes \\texttt, "->" an arrow,
relation names such as r1_history \\rel{1}; issue URLs are \\url{} (in the text font, to save width).

Layout. Every column has a fixed width (one column per table may take the rest of the 7.16 in
text width), so each table's width is known here. A table wider than 3.4 in does not fit an
IEEEtran column (3.5 in) and is set in one-column mode, which longtable needs anyway: its file
starts with \\onecolumn behind a test that makes it a no-op on a one-column page. supplement.tex
switches to one column before the heading of section D, back to two at L, and to one again at M, so
no heading is left alone at the foot of a two-column page. Decisions (width in inches at the chosen
size); no table fits 3.4 in, so all twelve are one-column:
    D_corpus 5.5 footnotesize, E_benchmark 7.2 scriptsize, F_detection 6.7 footnotesize,
    F2_missed 7.2 footnotesize, G_groups 7.2 scriptsize, G2_root_causes 7.2 scriptsize,
    I_sweep 7.2 scriptsize, J_cost 7.1 scriptsize, K_freeze 7.2 footnotesize,
    M_evidence 7.2 footnotesize, M2_isolation 7.2 footnotesize, M3_cross 7.2 footnotesize.
To stay within the text width, the server kind (the campaign in J) is a heading row instead of a
column; E puts the pre-fix and post-fix builds in one column; long or sparse text (D note, E
reason, F2 reason, detail and evidence) is a line under its row; a column that is empty in every
row (G known_issue_link, I error) is left out and logged; wrapped group ids are indented.

Run line: python3 scripts/paper/appendix_tex.py
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("appendix_tex")

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TABLES = "paper/appendix/tables"
OUT_DIR = "paper/supplement/tables"
PT_PER_IN = 72.27
TEXT_WIDTH = 516.0  # pt, \textwidth of the IEEEtran journal layout (43pc), as the TSE template
ONE_COLUMN_OVER = 252.0  # pt (21pc); a wider table does not fit one IEEEtran column
MIN_FLEX = 60.0  # pt, narrowest acceptable width of the column that takes the rest
FOOT, SCRIPT = r"\footnotesize", r"\scriptsize"

Row = Dict[str, str]
Render = Callable[[Row], str]

SPECIAL = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&", "#": r"\#",
           "%": r"\%", "_": r"\_", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
           "<": r"\textless{}", ">": r"\textgreater{}", "|": r"\textbar{}"}
CURLY = {("'", True): "`", ("'", False): "'", ('"', True): "``", ('"', False): "''"}
OPENERS = "([{<,="  # a quote after one of these (or a space, or nothing) opens
BREAK = r"\apxbrk{}"  # line-break opportunity, defined in each table file
HANG = r"\hangindent=1em "  # indent the continuation lines of a wrapped cell
REL_NAME = re.compile(r"[rR](\d)(?:_[a-z]+)?")
URL_OK = re.compile(r"[A-Za-z0-9:/?=._+-]+")
ALIGN = {"l": r"\raggedright", "c": r"\centering", "r": r"\raggedleft"}


def tex_tt(code: str) -> str:
    """A code span: specials escaped, quotes straight, no dash ligatures."""
    out = [r"\textquotesingle{}" if c == "'" else SPECIAL.get(c, "-{}" if code[i:i + 2] == "--" else c)
           for i, c in enumerate(code)]
    return r"\texttt{" + "".join(out) + "}"


def tex_text(text: str, breaks: str = "/_") -> str:
    """Escape one cell for LaTeX; a line may break after any character in `breaks` (and after hyphens)."""
    text = re.sub(r"\s", " ", text)
    out: List[str] = []
    prev_open: Optional[bool] = None  # set when the previous character was a quote: did it open?
    i = 0
    while i < len(text):
        c, prev = text[i], text[i - 1] if i else ""
        end = text.find("`", i + 1) if c == "`" else -1
        if end > i + 1:  # a code span
            out.append(tex_tt(text[i + 1:end]))
            i, prev_open = end + 1, None
            continue
        if c in "'\"":
            if prev_open is not None:  # two quotes in a row: after an opening one of the other kind, open
                opening = prev_open and prev != c
                out.append(r"\,")
            else:
                opening = not prev or prev.isspace() or prev in OPENERS
            out.append(CURLY[(c, opening)])
            i, prev_open = i + 1, opening
            continue
        if text[i:i + 2] == "->":
            out.append(r"$\rightarrow$")
            i, prev_open = i + 2, None
            continue
        if c == "`":
            out.append(r"\textasciigrave{}")
        else:
            out.append(SPECIAL.get(c, "-{}" if text[i:i + 2] == "--" else c))
        if c in breaks:
            out.append(BREAK)
        i, prev_open = i + 1, None
    return "".join(out)


def tex_url(url: str) -> str:
    url = url.strip()
    if url and not URL_OK.fullmatch(url):
        raise ValueError(f"URL with characters that would need escaping inside \\url: {url!r}")
    return rf"\url{{{url}}}" if url else ""


def tex_rel(text: str) -> str:
    """'r1_history, r4_edits' -> '\\rel{1}, \\rel{4}'; other tokens ('-', 'none') are escaped text."""
    out = []
    for token in (t.strip() for t in text.split(",")):
        m = REL_NAME.fullmatch(token)
        out.append(rf"\rel{{{m.group(1)}}}" if m else tex_text(token))
    return ", ".join(out)


@dataclass(frozen=True)
class Col:
    """A column: CSV keys shown, header, width in pt (0 = the rest of the text width), alignment, renderer."""

    keys: Tuple[str, ...]
    header: str
    width: float
    render: Render
    align: str = "l"
    optional: bool = False  # left out when every row is empty in its keys


def text(key: str, header: str, width: float, align: str = "l", breaks: str = "/_",
         optional: bool = False, hang: bool = False) -> Col:
    return Col((key,), header, width, lambda r: (HANG if hang else "") + tex_text(r[key], breaks), align, optional)


def rel(key: str, header: str, width: float, align: str = "c") -> Col:
    return Col((key,), header, width, lambda r: tex_rel(r[key]), align)


def flag(key: str, header: str, width: float) -> Col:
    """yes/no; the Python booleans True/False of the analysis records print the same way."""
    return Col((key,), header, width, lambda r: {"True": "yes", "False": "no"}.get(r[key], tex_text(r[key])), "c")


def class_subtype(keys: Tuple[str, ...], width: float) -> Col:
    """'R4 / organize' (one key) or class and subtype keys -> '\\rel{4} / organize'."""
    def render(r: Row) -> str:
        cls, _, sub = r[keys[0]].partition(" / ") if len(keys) == 1 else (r[keys[0]], "", r[keys[1]])
        return f"{tex_rel(cls)} / {tex_text(sub)}"
    return Col(keys, "Class / subtype", width, render)


def title_url(title: str, url: str) -> Col:
    return Col((title, url), "Issue title and URL", 0, lambda r: tex_text(r[title]) + r"\newline " + tex_url(r[url]))


def two_lines(first: str, second: str, header: str, width: float, breaks: str) -> Col:
    return Col((first, second), header, width,
               lambda r: tex_text(r[first], breaks) + r"\newline " + tex_text(r[second], breaks))


def listing(key: str, header: str, width: float) -> Col:
    """One entry per line (merged rows); an entry that wraps is indented."""
    return Col((key,), header, width, lambda r: r"\par ".join(HANG + tex_text(v) for v in r[key].split("\n")))


@dataclass(frozen=True)
class Spec:
    """A table: file stem, letter, source CSV, caption, columns and layout options."""

    name: str
    letter: str
    source: str
    caption: str
    columns: Tuple[Col, ...]
    size: str = FOOT
    tabcolsep: float = 4.0
    group: Optional[str] = None  # key shown as a heading row whenever its value changes, not as a column
    notes: Tuple[Tuple[str, str], ...] = ()  # (key, label): a line under the row when the value is not empty
    merge: Optional[Tuple[str, str]] = None  # (key, list key): consecutive rows with one key value become one
    gap: float = 0.0  # pt of extra space between rows
    heading: Optional[Callable[[Row], str]] = None  # text of the heading row (default: the value of `group`)
    keep: Optional[Callable[[Row], bool]] = None  # rows shown (default: all rows of the source)


CORPUS_NAME = {"first": "First corpus", "second": "Second corpus"}
CAMPAIGN_NAME = {"main_v1": "main_v1: current releases, first corpus",
                 "main_v2": "main_v2: current releases, second corpus", "bench_v1": "bench_v1: benchmark"}


def corpus_and(key: str) -> Callable[[Row], str]:
    """Heading 'First corpus, gopls' from the corpus column and another column."""
    return lambda r: f"{CORPUS_NAME[r['corpus']]}, {r[key]}"


def capitalized(key: str) -> Callable[[Row], str]:
    return lambda r: r[key][:1].upper() + r[key][1:]


def starred(key: str, header: str, width: float) -> Col:
    """The value with an asterisk when the row's `discussed` column is yes (settled in the raters' discussion)."""
    return Col((key, "discussed"), header, width,
               lambda r: tex_text(r[key]) + ("*" if r["discussed"] == "yes" else ""))


ISO_BUILDS = ('TS 5.9.3 + tsls 6.0.0', 'TS 6.0.3 + tsls 5.0.0', 'TS 6.0.3 + tsls 6.0.1', 'TS 6.0.3 + tsls 6.0.0 (control)',
              'TS 5.9.3 + tsls 5.0.0 (year-old)', 'TS 7.0.2')  # M2 columns, as numbers_evidence names them

SPECS: Tuple[Spec, ...] = (
    Spec("C_capabilities", "C", f"{TABLES}/C_capabilities.csv",
         "Capabilities of the current-release servers that decide where the relations can run (from the initialize "
         "results of the smoke sessions; every server also pushes diagnostics)",
         (text("server", "Server", 0), text("version", "Version", 50), flag("pulled diagnostics", "Pulled diagnostics", 44),
          flag("code action resolve", "Code action resolve", 44), flag("completion resolve", "Completion resolve", 44),
          text("semantic tokens", "Semantic tokens", 64), text("file operations", "File operations", 56),
          text("settled by", "Settled by", 40)),
         tabcolsep=4),
    Spec("D_corpus", "D", f"{TABLES}/D_corpus.csv",
         "Projects of the first and the second corpus, pinned commits, paired servers and the seconds each server "
         "took to settle",
         (text("corpus", "Corpus", 30), text("project", "Project", 146), text("language", "Language", 36),
          text("commit", "Commit", 52),
          text("servers", "Servers", 47.5), text("settle_seconds", "Seconds to settle", 68)),
         tabcolsep=6, notes=(("note", "Note"),)),
    Spec("E_benchmark", "E", f"{TABLES}/E_benchmark.csv", "Attempted benchmark cases and their reproduction",
         (text("case", "Case", 62), title_url("title", "issue_url"), class_subtype(("class_subtype",), 52),
          two_lines("pre_build", "post_build", "Pre-fix and post-fix build", 47, "+"),
          text("probe", "Probe", 42), flag("spec_probe", "Specification probe", 40),
          flag("reproduced", "Reproduced", 38.5)),
         size=SCRIPT, tabcolsep=3.5, group="kind", notes=(("reason_if_not", "Reason"),), gap=2),
    Spec("F_detection", "F", f"{TABLES}/F_detection.csv",
         "Detection of the reproduced benchmark bugs, with the joint verdicts of the two raters on whether the "
         "pre-only signatures show the reported bug (* = at least one of the case's verdicts settled in discussion, "
         "Table G5)",
         (text("case", "Case", 70), class_subtype(("class_subtype",), 80),
          flag("spec_probe", "Specification probe", 45.5), flag("detected", "Pre-only", 32),
          flag("complete", "All runs finished", 33), rel("oracles_pre_only", "Relations with pre-only signatures", 60, "l"),
          text("pre_only_signatures", "Pre-only signatures", 37, "r"), starred("joint_verdicts", "Joint verdicts", 60)),
         tabcolsep=6, group="kind"),
    Spec("F2_missed", "F2", "data/lsptest/runs/bench_v1/missed_attribution.csv",
         "Attribution of every missed benchmark bug",
         (text("case", "Case", 70), class_subtype(("class", "subtype"), 57),
          flag("spec_probe", "Specification probe", 45.5), text("category", "Category", 75.5),
          rel("relation_that_could_see", "Relation that could see it", 38), text("confidence", "Confidence", 40.5),
          title_url("title", "url")),
         group="kind", notes=(("reason", "Reason"), ("detail", "Detail"), ("evidence", "Evidence")), gap=4),
    Spec("G_groups", "G", f"{TABLES}/G_groups.csv",
         "Triage groups of both current-release campaigns with the final verdicts (* = settled in discussion, "
         "Table G5; otherwise the verdict both raters gave) and, for a group that is not a bug, the final exception class",
         (text("gid", "Group", 0, hang=True), rel("oracle", "Relation", 26), text("shape", "Shape", 80, breaks=":,_"),
          text("family", "Family", 40.5, breaks=":"), text("members", "Members", 29.5, "r"),
          text("ops", "Operations", 35, "r"), text("reduced_confirmed", "Reduced case confirmed", 32, "r"),
          flag("narrowed", "Narrowed", 32.5), starred("verdict", "Verdict", 40),
          Col(("known_issue_link",), "Known issue", 90, lambda r: tex_url(r["known_issue_link"]), optional=True),
          text("sweep_older_2025", "Year-old release", 37), text("class", "Class", 20)),
         size=SCRIPT, tabcolsep=2.5, group="kind", heading=corpus_and("kind"), notes=(("reason", "Reason"),), gap=1),
    Spec("G3_sensitivity", "G3", f"{TABLES}/G3_sensitivity.csv",
         "Bug groups and distinct bugs of both corpora under four sets of verdicts: each rater's before the discussion, "
         "the agreed ones, and the agreed ones counting only the bugs with decisive evidence from outside the server "
         "(Appendix~\\ref{app:evidence}); per relation, bug groups / distinct bugs; -- where the set gives no such count",
         (text("verdicts", "Verdicts", 0), text("bug groups", "Bug groups", 34, "r"),
          text("distinct bugs", "Distinct bugs", 34, "r"), text("R0", "R0", 30, "r"), text("R1", "R1", 30, "r"),
          text("R2", "R2", 30, "r"), text("R3", "R3", 30, "r"), text("R4", "R4", 30, "r"), text("R5", "R5", 30, "r"),
          text("R6", "R6", 30, "r")),
         tabcolsep=4),
    Spec("G4_rater2", "G4", f"{TABLES}/G4_rater2.csv",
         "Agreement of the first author and the second rater before the discussion: on the verdicts of the triage "
         "groups of each campaign, per relation, and on the benchmark's pre-only signatures, whose three verdicts are "
         "yes, partial and no and whose two are detected or not (blank: kappa undefined, because both raters gave "
         "every item the same verdict)",
         (rel("oracle", "Relation", 76, "l"), text("items", "Groups or signatures", 46, "r"),
          text("same verdict", "Same verdict", 45, "r"), text("agreement %", "Agreement (%)", 50, "r"),
          text("kappa (three verdicts)", "Kappa, three verdicts", 60, "r"),
          text("kappa (bug or not)", "Kappa, two verdicts", 60, "r")),
         tabcolsep=5, group="batch", heading=capitalized("batch")),
    Spec("G5_rater2_disagreements", "G5", f"{TABLES}/G5_rater2_disagreements.csv",
         "Every item the two raters judged differently, all settled in discussion: the triage groups of both "
         "campaigns and the benchmark signatures (case and signature), with each rater's verdict before the "
         "discussion, the joint verdict, the reason agreed in the discussion and the second rater's own reason "
         "(both translated)",
         (rel("oracle", "Relation", 26), text("item", "Group or signature", 0), text("first author", "First author", 64),
          text("second rater", "Second rater", 64), text("joint verdict", "Joint verdict", 64)),
         size=SCRIPT, tabcolsep=3, group="batch", heading=capitalized("batch"),
         notes=(("discussion", "Discussion"), ("second rater's reason", "Second rater's reason")), gap=2),
    Spec("G2_root_causes", "G2", f"{TABLES}/G2_root_causes.csv",
         "Distinct bugs of both corpora: bug groups merged by minimal trigger and kind of symptom (each group marked "
         "with its corpus)",
         (text("cause", "Cause", 19.5), text("server", "Server", 41.5), text("trigger", "Trigger", 62),
          text("description", "Description", 0), listing("group", "Groups", 175)),
         size=SCRIPT, merge=("cause", "group"), gap=3),
    Spec("I_sweep", "I", f"{TABLES}/I_sweep.csv", "Triage groups of both campaigns replayed on the releases of a year earlier",
         (text("gid", "Group", 0, hang=True), rel("oracle", "Relation", 26), text("build", "Build", 77, breaks="+"),
          text("verdict", "Verdict", 49), text("reproduced", "Reproduced", 38.5, "r"),
          text("settled", "Settled", 21.5, "r"), text("control_stable", "Control stable", 24, "r"),
          text("seconds", "Seconds", 25.5, "r"), text("error", "Error", 60, optional=True)),
         size=SCRIPT, tabcolsep=3.5, group="from_kind", heading=corpus_and("from_kind")),
    Spec("J_cost", "J", f"{TABLES}/J_cost.csv",
         "Runs, run time and candidate outcomes per campaign, relation and server",
         (rel("oracle", "Relation", 26), text("kind", "Server", 41.5), text("runs", "Runs", 16.5, "r"),
          text("runs_not_ok", "Runs not OK", 22, "r"), text("mean_s", "Mean (s)", 19.5, "r"),
          text("median_s", "Median (s)", 24.5, "r"), text("p90_s", "P90 (s)", 19.5, "r"),
          text("run_hours", "Run hours", 18, "r"), text("candidates", "Candidates", 35.5, "r"),
          text("candidate_signatures", "Candidate signatures", 32.5, "r"), text("confirmed", "Confirmed", 34, "r"),
          text("flaky", "Flaky", 17.5, "r"), text("not_reproduced", "Not reproduced", 36.5, "r"),
          text("capped", "Capped", 25, "r"), text("labelled_legitimate", "Labelled legitimate", 31.5, "r"),
          text("incomplete", "Incomplete", 35.5, "r")),
         size=SCRIPT, tabcolsep=2.5, group="campaign", heading=lambda r: CAMPAIGN_NAME.get(r["campaign"], r["campaign"])),
    Spec("K_freeze", "K", f"{TABLES}/K_freeze.csv", "Tool freezes",
         (text("id", "Freeze", 23.5), text("created", "Created", 89.5), text("tree_digest", "Tree digest", 66.5),
          text("files", "Files", 16.5, "r"), text("note", "Note", 0)),
         tabcolsep=5),
    Spec("M_evidence", "M", f"{TABLES}/M_evidence.csv",
         "Checks of the candidate bugs that do not rest on the tested server, and related tracker reports",
         (text("cause", "Cause", 22), text("server", "Server", 84), text("independent", "Check outside the server", 42),
          text("check", "Check", 0)),
         notes=(("result", "Result"), ("related_possible", "Possibly the same defect"),
                ("related_other", "Closest other reports")), gap=4),
    Spec("M2_isolation", "M2", f"{TABLES}/M2_isolation.csv",
         "Component isolation of the TypeScript bugs: reproducing replays out of three, per group and build "
         "(TS = TypeScript, tsls = typescript-language-server; the campaign ran TS 6.0.3 + tsls 6.0.0)",
         (text("cause", "Cause", 22), text("group", "Group", 0, hang=True))
         + tuple(text(k, k, 40, "r", breaks="+") for k in ISO_BUILDS),
         tabcolsep=3.5),
    Spec("M4_c1_checks", "M4", f"{TABLES}/M4_c1_checks.csv",
         "The history bugs replayed with the willRenameFiles edit applied (C1), as a rename outside the editor (C1), "
         "and with waits of 0 to 60 s after the history (reproducing replays out of three for the renames; after a "
         "wait, yes or no is the outcome of one replay, and k/3 counts a group replayed twice more after 60 s). In the "
         "second corpus, the eight history groups first merged into C1, of which b9d052 is now C31, were replayed with the "
         "renames only (-: not replayed); unsettled (k/3): not every replay settled, and k of the three reproduced",
         (text("group", "Group", 0, hang=True), text("cause", "Cause", 22),
          text("rename edit applied", "Rename edit applied", 44, "r"),
          text("rename outside the editor", "Rename outside the editor", 48, "r"),
          text("after 0 s", "After 0 s", 30, "c"), text("after 5 s", "After 5 s", 30, "c"),
          text("after 30 s", "After 30 s", 32, "c"), text("after 60 s", "After 60 s", 32, "c")),
         tabcolsep=3.5, group="corpus", heading=lambda r: CORPUS_NAME[r["corpus"]]),
    Spec("N1_lifecycle", "N1", f"{TABLES}/N1_lifecycle.csv",
         "Each bug's representative group, from either corpus, replayed three times on releases of its server line, from "
         "about two years before the campaign to the newest release of 2026-11-18, and for C3, C5--C7 and C9 on the gopls "
         "development head of that day (reproducing replays out of three; could not be judged = the build does not start, "
         "cannot load the project with the toolchain it needs, or its sessions did not settle, or the group was not "
         "replayed on it; a seeded quick-fix replay that ran to the end without the violation does not reproduce)",
         (text("cause", "Cause", 24), text("line", "Line", 50), text("build", "Build", 78, breaks="+-"),
          text("released", "Released", 46), text("reproduced", "Replays", 34, "r"), text("result", "Result", 80),
          text("role", "Role", 60)),
         tabcolsep=3.5),
    Spec("N2_newest", "N2", f"{TABLES}/N2_newest.csv",
         "Every bug group of both corpora replayed three times on the newest release of its server line as of 2026-11-18, "
         "then the first corpus's groups of C3, C5--C7 and C9 on the gopls development head of that day (Verdict: "
         "the frozen sweep's; Result: as read in the paper, where a seeded quick-fix replay that ran to the end without the "
         "violation does not reproduce)",
         (text("group", "Group", 0, hang=True), text("cause", "Cause", 24), text("build", "Build", 100, breaks="+-"),
          text("reproduced", "Replays", 30, "r"), text("verdict", "Verdict", 48), text("result", "Result", 56)),
         tabcolsep=3.5, group="corpus", heading=lambda r: f"{CORPUS_NAME[r['corpus']]}, {r['replay']}"),
    Spec("N3_upstream", "N3", f"{TABLES}/N3_upstream.csv",
         "The upstream reports filed after the campaign and the maintainers' responses, classified by the author from the "
         "issue threads (fixed: closed with a fix; fix planned: a maintainer scheduled a fix or has one under review; "
         "confirmed: called a bug by the maintainers; investigating: a maintainer took the issue, with no verdict yet; info "
         "asked: a maintainer asked whether it reproduces in a common editor; cause found: a maintainer reproduced the bug "
         "and traced its cause, without planning a fix; disputed: called expected behavior or a client error by a maintainer)",
         (text("cause", "Cause", 24), text("issue", "Issue", 150, breaks="/#"), text("reported", "Reported", 46),
          text("status", "Status", 76), text("note", "Note", 0)),
         tabcolsep=3.5),
    Spec("M3_cross", "M3", f"{TABLES}/M3_cross.csv",
         "The TypeScript history groups replayed on the other TypeScript implementation: the version sweep "
         "(reproducing replays out of three) and one replay that records the other implementation's answer after the "
         "history (n = entries of the answer on the group's key; diagnostics compared by code and line, semantic "
         "tokens by position)",
         (text("group", "Group", 0, hang=True), text("cause", "Cause", 22), text("verdict", "Verdict", 47),
          text("other implementation", "Replayed on", 36),
          text("replays on it", "Replays on it", 30, "r"), text("fresh n", "Fresh n", 26, "r"),
          text("history n", "History n", 28, "r"), text("other history n", "Other history n", 32, "r"),
          text("other history agrees with", "Other history agrees with", 44)),
         tabcolsep=3.5, gap=1),
)


def read_rows(rel_path: str, keys: Sequence[str]) -> List[Row]:
    """Rows of a CSV file; fails when a key the table shows is missing."""
    try:
        with open(os.path.join(REPO, rel_path), encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing = sorted(set(keys) - set(reader.fieldnames or []))
            if missing:
                raise KeyError(f"{rel_path}: missing columns {missing}")
            return [dict(r) for r in reader]
    except FileNotFoundError:
        logger.error("input file not found: %s", rel_path)
        raise


def merge_rows(rows: Sequence[Row], key: str, list_key: str) -> List[Row]:
    """Consecutive rows with the same `key` become one row whose `list_key` lists theirs, one per line."""
    out: List[Row] = []
    for r in rows:
        if out and out[-1][key] == r[key]:
            differ = sorted(k for k in r if k != list_key and r[k] != out[-1][k])
            if differ:
                logger.warning("%s %s: rows differ in %s; the first row is kept", key, r[key], differ)
            out[-1] = {**out[-1], list_key: out[-1][list_key] + "\n" + r[list_key]}
        else:
            out.append(dict(r))
    return out


def fit_columns(spec: Spec, rows: Sequence[Row]) -> List[Col]:
    """Drop optional columns that are empty in every row; give the flexible column the remaining width."""
    cols = []
    for c in spec.columns:
        if c.optional and not any(r[k].strip() for r in rows for k in c.keys):
            logger.info("%s: column %r is empty in every row and left out", spec.name, c.header)
        else:
            cols.append(c)
    flex = [i for i, c in enumerate(cols) if c.width == 0]
    if len(flex) > 1:
        raise ValueError(f"{spec.name}: more than one flexible column")
    if flex:
        rest = TEXT_WIDTH - sum(c.width for c in cols) - 2 * spec.tabcolsep * (len(cols) - 1)
        if rest < MIN_FLEX:
            raise ValueError(f"{spec.name}: only {rest:.1f}pt left for column {cols[flex[0]].header!r}")
        cols[flex[0]] = replace(cols[flex[0]], width=int(rest * 10) / 10)
    return cols


def colspec(c: Col, box: str = "p") -> str:
    return rf">{{{ALIGN[c.align]}\arraybackslash}}{box}{{{c.width:.1f}pt}}"


def header_row(cols: Sequence[Col]) -> str:
    """Headers bottom-aligned (b columns) so that multi-line headers end on the same line."""
    last = len(cols) - 1
    return " & ".join(rf"\multicolumn{{1}}{{{'@{}' if i == 0 else ''}{colspec(c, 'b')}{'@{}' if i == last else ''}}}"
                      rf"{{{tex_text(c.header)}}}" for i, c in enumerate(cols)) + r" \\"


def span(cols: Sequence[Col], first: int, content: str, tabcolsep: float) -> str:
    """A cell from column `first` to the last column, as wide as the columns it covers."""
    k = len(cols) - first
    width = sum(c.width for c in cols[first:]) + 2 * tabcolsep * (k - 1)
    edge = "@{}" if first == 0 else ""
    return "& " * first + rf"\multicolumn{{{k}}}{{{edge}>{{\raggedright\arraybackslash}}p{{{width:.1f}pt}}@{{}}}}{{{content}}}"


def body(spec: Spec, cols: Sequence[Col], rows: Sequence[Row]) -> List[str]:
    """Table rows: group headings, the rows, and the note lines under a row (kept on its page)."""
    lines: List[str] = []
    current: Optional[str] = None
    for i, r in enumerate(rows):
        heading = (spec.heading(r) if spec.heading else r[spec.group]) if spec.group else None
        if spec.group and heading != current:
            current = heading
            lines += [r"\addlinespace[4pt]"] if i else []
            lines.append(span(cols, 0, rf"\textit{{{tex_text(current or '')}}}", spec.tabcolsep) + r" \\*")
        elif i and spec.gap:
            lines.append(rf"\addlinespace[{spec.gap:g}pt]")
        notes = [(label, r[key]) for key, label in spec.notes if r[key].strip()]
        lines.append(" & ".join(c.render(r) for c in cols) + (r" \\*" if notes else r" \\"))
        for j, (label, value) in enumerate(notes):
            end = r" \\*" if j < len(notes) - 1 else r" \\"
            lines.append(span(cols, 1, rf"\textit{{{label}:}} {tex_text(value)}", spec.tabcolsep) + end)
    return lines


def render(spec: Spec, rows: Sequence[Row]) -> Tuple[str, float]:
    """The LaTeX file of one table and its width in pt."""
    cols = fit_columns(spec, rows)
    width = sum(c.width for c in cols) + 2 * spec.tabcolsep * (len(cols) - 1)
    if width > TEXT_WIDTH + 0.01:
        raise ValueError(f"{spec.name}: {width:.1f}pt is wider than the text ({TEXT_WIDTH}pt)")
    one_column = width > ONE_COLUMN_OVER
    head, size = header_row(cols), spec.size.lstrip("\\")
    lines = [f"% Table {spec.letter}: generated by scripts/paper/appendix_tex.py from {spec.source}; do not edit.",
             f"% {width / PT_PER_IN:.2f} in wide in {size}: "
             + ("wider than 3.5 in, so one-column (longtable needs that mode)." if one_column
                else "fits a column, but longtable needs a one-column page."),
             r"\providecommand{\apxbrk}{\penalty50\relax}"]
    lines += [r"\ifdim\columnwidth<\textwidth\expandafter\onecolumn\fi"] if one_column else []
    lines += [r"\begingroup", spec.size, rf"\setlength{{\tabcolsep}}{{{spec.tabcolsep:g}pt}}",
              r"\hyphenpenalty=10000 \urlstyle{same}",
              rf"\def\thetable{{{spec.letter}}}\def\theHtable{{app.{spec.letter}}}",
              r"\begin{longtable}{@{}" + "".join(colspec(c) for c in cols) + "@{}}",
              rf"\caption{{{spec.caption}}}\label{{tab:app-{spec.letter}}}\\",
              r"\toprule", head, r"\midrule", r"\endfirsthead",
              r"\caption[]{(continued)}\\", r"\toprule", head, r"\midrule", r"\endhead",
              r"\bottomrule", r"\endfoot", r"\bottomrule", r"\endlastfoot"]
    lines += body(spec, cols, rows)
    lines += [r"\end{longtable}", r"\addtocounter{table}{-1}", r"\endgroup", ""]
    return "\n".join(lines), width


def build(spec: Spec, out_dir: str) -> str:
    """Read the source rows of one table and write its .tex file; returns the path."""
    keys = {k for c in spec.columns for k in c.keys} | {k for k, _ in spec.notes} | ({spec.group} if spec.group else set())
    rows = read_rows(spec.source, sorted(keys))
    rows = [r for r in rows if spec.keep(r)] if spec.keep else rows
    rows = merge_rows(rows, *spec.merge) if spec.merge else rows
    tex, width = render(spec, rows)
    path = os.path.join(out_dir, f"{spec.name}.tex")
    with open(path, "w", encoding="utf-8") as f:
        f.write(tex)
    logger.info("%-15s %3d rows  %.2f in  %-12s %s", spec.name, len(rows), width / PT_PER_IN,
                spec.size.lstrip("\\"), "one-column" if width > ONE_COLUMN_OVER else "fits a column")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT_DIR, help="output directory (repository-relative)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    out_dir = os.path.join(REPO, args.out)
    os.makedirs(out_dir, exist_ok=True)
    for spec in SPECS:
        build(spec, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
