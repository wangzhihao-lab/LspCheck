"""Fig. 1 of the paper: the motivating example, a file rename round trip after which the editor
session's references query loses its answer.

The finding is typescript-language-server with TypeScript 6.0.3 on pmndrs/zustand (triage group
ts6-r1-references-lost-h5-d24ca6). Everything the figure prints about it is read from the group's
repro.json at run time: the history steps from `ops`, the query method and position from `key`
(printed 1-based as file:line:col) and the two answers as the number of locations in `expected`
(fresh session) and in `actual` (the session after the history). Two lanes at the final
single-column size (3.5 in x 2.2 in) with time flowing left to right: the editor session that went
through the history (top) and a fresh session on the same final project (bottom), separated by a
dashed line. The answers meet at the right end; the history session's answer is outlined in rose,
with a not-equal sign between the two. The content needs about 2.0 in of height; FIG_H_IN adds the
rest to the vertical arrows and the gap between the answers. After drawing, the script checks that
labels sit inside their boxes, that nothing overlaps and that the font has every glyph; it exits
with status 1 if a check fails. Writes paper/figures/motivation.svg (labels kept as <text>
elements) and paper/figures/motivation.pdf (TrueType fonts embedded).

Run line: python3 scripts/paper/figures/fig_motivation.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

import matplotlib
from matplotlib import font_manager
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgb
from matplotlib.figure import Figure
from matplotlib.ft2font import FT2Font
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path
from matplotlib.text import Text

logger = logging.getLogger(__name__)

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
REPRO = os.path.join(REPO, "data", "lsptest", "runs", "main_v1", "triage",
                     "ts6-r1-references-lost-h5-d24ca6", "repro.json")
OUT_DIR = os.path.join(REPO, "paper", "figures")
STEM = "motivation"

FIG_W_IN, FIG_H_IN = 3.5, 1.95
FONT_CHOICES = ("Times New Roman", "Times", "STIXGeneral", "DejaVu Serif")  # the default for every figure
LANE_PT, STEP_PT, ANSWER_PT, NE_PT, MIN_PT = 8.0, 7.0, 9.0, 11.0, 7.0
LINESPACING = 1.2
LANE_LABELS = ("Session after the history", "Fresh session")
FRESH_STEPS = ("open the same final project", "the same query")

PALETTE = ("#332288", "#117733", "#44AA99", "#88CCEE", "#DDCC77", "#CC6677", "#AA4499", "#882255")
HISTORY, FRESH, MISMATCH = PALETTE[0], PALETTE[1], PALETTE[5]  # indigo, green, rose
INK = "#1a1a1a"
CONNECTOR = "#3c3c3c"
SEPARATOR = "#8a8a8a"  # the dashed line between the lanes
FILL_TINT = 0.2

PAD_X, PAD_Y = 2.5, 3.5          # inner padding of a step box, pt
ANS_PAD_X, ANS_PAD_Y = 6.0, 3.5  # inner padding of an answer box
MARGIN = 1.5                     # figure edge to the outermost outline
LABEL_GAP = 2.5                  # lane label to its boxes
ARROW_V = 9.0                    # least length of the vertical arrows into the answers
NE_GAP = 14.0                    # least space between the two answers (holds the sign)
MIN_ARROW = 6.0                  # shortest horizontal arrow allowed
CLEARANCE = 1.0
ROUNDING = 3.0
SEPARATOR_END = 8.0              # the lane separator stops this far left of the answers
LINE_W, MISMATCH_W, SEPARATOR_W = 0.8, 1.4, 0.6
ARROW_SCALE = 7.0


@dataclass(frozen=True)
class Box:
    """A rectangle in figure points (origin bottom left)."""

    x: float
    y: float
    w: float
    h: float

    @property
    def x1(self) -> float:
        return self.x + self.w

    @property
    def y1(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass(frozen=True)
class Example:
    """The labels of the finding, as printed."""

    steps: Tuple[str, ...]  # history steps, then the query
    history_answer: str
    fresh_answer: str


def step_labels(ops: Sequence[Dict[str, Any]]) -> List[str]:
    """One label per history operation; a rename to a path seen before is a rename back."""
    labels, seen = [], set()
    for op in ops:
        if op.get("kind") == "open":
            labels.append(f"open\n{op['path']}")
        elif op.get("kind") == "fs_rename":
            back = op["new_path"] in seen
            labels.append(f"rename\nback to\n{op['new_path']}" if back else f"rename to\n{op['new_path']}")
        else:
            raise ValueError(f"no label for operation {op!r}")
        seen.update(p for p in (op.get("path"), op.get("new_path")) if p)
    return labels


def count_label(locations: Sequence[Any]) -> str:
    """'N references' for a references answer given as a list of locations."""
    return f"{len(locations)} reference" + ("" if len(locations) == 1 else "s")


def load_example(path: str) -> Example:
    """Read ops, key, expected and actual from repro.json."""
    try:
        with open(path, encoding="utf-8") as f:
            repro = json.load(f)
    except FileNotFoundError:
        logger.error("repro file not found: %s", path)
        raise
    key = repro["key"]
    if key["method"] != "references":
        raise ValueError(f"the figure is drawn for a references query, not {key['method']!r}")
    query = f"query {key['method']} at\n{key['path']}:{key['line'] + 1}:{key['character'] + 1}"
    logger.info("key %s; expected %d locations, actual %d", query.replace("\n", " "),
                len(repro["expected"]), len(repro["actual"]))
    return Example(tuple(step_labels(repro["ops"])) + (query,), count_label(repro["actual"]),
                   count_label(repro["expected"]))


def configure_fonts() -> List[str]:
    """Choose the first available family of FONT_CHOICES (Times New Roman first) and set the vector-output options.

    Returns:
        The regular and bold font files of the chosen family, for the glyph check.

    Raises:
        RuntimeError: When none of FONT_CHOICES is installed.
    """
    for family in FONT_CHOICES:
        try:
            files = [font_manager.findfont(font_manager.FontProperties(family=family, weight=w),
                                           fallback_to_default=False) for w in ("normal", "bold")]
        except ValueError:
            continue
        matplotlib.rcParams.update({
            "font.family": "serif", "font.serif": [family], "mathtext.fontset": "stix", "text.hinting": "no_hinting",
            "svg.fonttype": "none", "svg.hashsalt": STEM, "pdf.fonttype": 42,
        })
        logger.info("font: %s", family)
        return files
    raise RuntimeError("no font among " + ", ".join(FONT_CHOICES))


def label_problems(font_files: Sequence[str], labels: Sequence[str]) -> List[str]:
    """Missing glyphs and forbidden characters (em dashes) in the labels."""
    chars = sorted({ch for label in labels for ch in label if ch != "\n"})
    problems = [f"glyph U+{ord(ch):04X} missing from {path}" for path in font_files
                for ch in chars if FT2Font(path).get_char_index(ord(ch)) == 0]
    return problems + [f"em dash in label {label!r}" for label in labels if "—" in label]


def tint(colour: str, amount: float) -> Tuple[float, float, float]:
    """The colour mixed with white; `amount` is the share of the colour."""
    r, g, b = to_rgb(colour)
    return (1 - amount * (1 - r), 1 - amount * (1 - g), 1 - amount * (1 - b))


def new_canvas() -> Tuple[Figure, Axes]:
    """A figure at print size whose data coordinates are points."""
    fig = Figure(figsize=(FIG_W_IN, FIG_H_IN), dpi=300)
    FigureCanvasAgg(fig)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, FIG_W_IN * 72)
    ax.set_ylim(0, FIG_H_IN * 72)
    ax.axis("off")
    return fig, ax


def put_text(ax: Axes, x: float, y: float, text: str, size: float, bold: bool = False,
             ha: str = "center", va: str = "center", color: str = INK) -> Text:
    """A label in the figure's text style."""
    return ax.text(x, y, text, fontsize=size, fontweight="bold" if bold else "normal", color=color,
                   ha=ha, va=va, linespacing=LINESPACING, zorder=3)


def extent(ax: Axes, artist: Text) -> Tuple[float, float, float, float]:
    """(x0, y0, x1, y1) of a label in points."""
    bb = artist.get_window_extent(ax.figure.canvas.get_renderer()).transformed(ax.transData.inverted())
    return bb.x0, bb.y0, bb.x1, bb.y1


def measure(ax: Axes, text: str, size: float, bold: bool = False) -> Tuple[float, float]:
    """Width and height in points of a possibly multi-line label."""
    artist = put_text(ax, 0, 0, text, size, bold)
    x0, y0, x1, y1 = extent(ax, artist)
    artist.remove()
    return x1 - x0, y1 - y0


def layout(ax: Axes, ex: Example) -> Tuple[Dict[str, Any], float]:
    """Boxes of both lanes and the answers, the horizontal arrow length and the lane-label tops.

    Time runs left to right. The fresh lane's open box spans the history steps and its query box
    sits under the history query, so both queries share a column; the answers are stacked in
    that column between the lanes. Height left over is shared by the arrows and the answer gap.
    """
    width, height = FIG_W_IN * 72, FIG_H_IN * 72
    sizes = [measure(ax, s, STEP_PT) for s in ex.steps]
    widths = [w + 2 * PAD_X for w, _ in sizes]
    gap = (width - 2 * MARGIN - sum(widths)) / (len(widths) - 1)
    top_h = max(h for _, h in sizes) + 2 * PAD_Y
    bot_h = max(measure(ax, s, STEP_PT)[1] for s in FRESH_STEPS) + 2 * PAD_Y + 4.0
    ans_w = max(measure(ax, s, ANSWER_PT, True)[0] for s in (ex.history_answer, ex.fresh_answer))
    ans_h = measure(ax, ex.history_answer, ANSWER_PT, True)[1] + 2 * ANS_PAD_Y
    lane_h = measure(ax, LANE_LABELS[0], LANE_PT, True)[1]
    fixed = 2 * MARGIN + lane_h + LABEL_GAP + top_h + 2 * ans_h + bot_h
    spare = height - fixed - 2 * ARROW_V - NE_GAP
    arrow_v, ne_gap = ARROW_V + spare / 3, NE_GAP + spare / 3
    y = height - MARGIN - lane_h - LABEL_GAP - top_h
    top, x = [], MARGIN
    for w in widths:
        top.append(Box(x, y, w, top_h))
        x += w + gap
    query = top[-1]
    hist_ans = Box(query.cx - ans_w / 2 - ANS_PAD_X, y - arrow_v - ans_h, ans_w + 2 * ANS_PAD_X, ans_h)
    fresh_ans = Box(hist_ans.x, hist_ans.y - ne_gap - ans_h, hist_ans.w, ans_h)
    y_bot = fresh_ans.y - arrow_v - bot_h
    bottom = [Box(MARGIN, y_bot, top[-2].x1 - MARGIN, bot_h), Box(query.x, y_bot, query.w, bot_h)]
    logger.info("height %.1f pt (%.1f spare), horizontal arrows %.1f pt, vertical arrows %.1f pt",
                height, spare, gap, arrow_v)
    separator = (MARGIN, hist_ans.x - SEPARATOR_END, (hist_ans.y + fresh_ans.y1) / 2)
    return {"top": top, "bottom": bottom, "hist_ans": hist_ans, "fresh_ans": fresh_ans,
            "lane_tops": (height - MARGIN, bottom[0].y1 + LABEL_GAP + lane_h),
            "separator": separator}, gap


def draw_box(ax: Axes, box: Box, fill: str, edge: str, lw: float = LINE_W) -> None:
    """A rounded box with a light fill."""
    ax.add_patch(FancyBboxPatch((box.x, box.y), box.w, box.h,
                                boxstyle=f"round,pad=0,rounding_size={ROUNDING}",
                                facecolor=tint(fill, FILL_TINT), edgecolor=edge, linewidth=lw, zorder=2))


def draw_arrow(ax: Axes, start: Tuple[float, float], end: Tuple[float, float]) -> None:
    """A straight arrow whose tip is `end`."""
    ax.add_patch(FancyArrowPatch(path=Path([start, end], [Path.MOVETO, Path.LINETO]),
                                 arrowstyle="-|>", mutation_scale=ARROW_SCALE, linewidth=LINE_W,
                                 color=CONNECTOR, capstyle="butt", zorder=1))


def draw(ax: Axes, ex: Example, geo: Dict[str, Any]) -> Tuple[List[Tuple[str, Box, List[Text]]], List[Text]]:
    """Lanes, answers and arrows; returns boxed labels and free labels for the checks."""
    top, bottom = geo["top"], geo["bottom"]
    hist_ans, fresh_ans = geo["hist_ans"], geo["fresh_ans"]
    boxed = []
    for lane, labels, colour in ((top, ex.steps, HISTORY), (bottom, FRESH_STEPS, FRESH)):
        for box, label in zip(lane, labels):
            draw_box(ax, box, colour, colour)
            boxed.append((label, box, [put_text(ax, box.cx, box.cy, label, STEP_PT)]))
        for a, b in zip(lane, lane[1:]):
            draw_arrow(ax, (a.x1, a.cy), (b.x, b.cy))
    draw_box(ax, hist_ans, HISTORY, MISMATCH, MISMATCH_W)
    draw_box(ax, fresh_ans, FRESH, FRESH)
    for box, label in ((hist_ans, ex.history_answer), (fresh_ans, ex.fresh_answer)):
        boxed.append((label, box, [put_text(ax, box.cx, box.cy, label, ANSWER_PT, True)]))
    draw_arrow(ax, (top[-1].cx, top[-1].y), (hist_ans.cx, hist_ans.y1))
    draw_arrow(ax, (bottom[-1].cx, bottom[-1].y1), (fresh_ans.cx, fresh_ans.y))
    sep_x0, sep_x1, sep_y = geo["separator"]
    ax.plot([sep_x0, sep_x1], [sep_y, sep_y], color=SEPARATOR, linewidth=SEPARATOR_W,
            linestyle=(0, (3.0, 2.0)), solid_capstyle="butt", zorder=0)
    free = [put_text(ax, MARGIN, y, label, LANE_PT, True, ha="left", va="top")
            for y, label in zip(geo["lane_tops"], LANE_LABELS)]
    free.append(put_text(ax, hist_ans.cx, (hist_ans.y + fresh_ans.y1) / 2, "≠", NE_PT, True,
                         color=MISMATCH))
    return boxed, free


def crosses(span: Tuple[float, float, float, float], separator: Tuple[float, float, float]) -> bool:
    """Whether a rectangle (x0, y0, x1, y1) comes within CLEARANCE of the lane separator."""
    x0, x1, y = separator
    return span[0] < x1 and x0 < span[2] and span[1] - CLEARANCE < y < span[3] + CLEARANCE


def check(ax: Axes, boxed: Sequence[Tuple[str, Box, List[Text]]], free: Sequence[Text],
          gap: float, separator: Tuple[float, float, float]) -> List[str]:
    """Labels inside their boxes with clearance, free labels clear of boxes and of the lane
    separator, no overlapping labels, font sizes and the horizontal arrow length."""
    width, height = FIG_W_IN * 72, FIG_H_IN * 72
    problems = [] if gap >= MIN_ARROW else [f"arrows {gap:.1f} pt, shorter than {MIN_ARROW} pt"]
    spans, boxes = [], [box for _, box, _ in boxed]
    problems += [f"box {name!r} crosses the lane separator" for name, b, _ in boxed
                 if crosses((b.x, b.y, b.x1, b.y1), separator)]
    problems += [f"{t.get_text()!r} crosses the lane separator" for t in free
                 if crosses(extent(ax, t), separator)]
    for name, box, texts in boxed:
        if box.x < 0.5 or box.y < 0.5 or box.x1 > width - 0.5 or box.y1 > height - 0.5:
            problems.append(f"box {name!r} leaves the figure: {box}")
        for t in texts:
            x0, y0, x1, y1 = extent(ax, t)
            if (x0 < box.x + CLEARANCE or x1 > box.x1 - CLEARANCE
                    or y0 < box.y + CLEARANCE or y1 > box.y1 - CLEARANCE):
                problems.append(f"{t.get_text()!r} not {CLEARANCE} pt inside its box")
            spans.append((t, (x0, y0, x1, y1)))
    for t in free:
        x0, y0, x1, y1 = extent(ax, t)
        if x0 < 0.5 or y0 < 0.5 or x1 > width - 0.5 or y1 > height - 0.5:
            problems.append(f"{t.get_text()!r} leaves the figure")
        problems += [f"{t.get_text()!r} overlaps a box" for b in boxes
                     if x0 < b.x1 and b.x < x1 and y0 < b.y1 and b.y < y1]
        spans.append((t, (x0, y0, x1, y1)))
    problems += [f"{t.get_text()!r} is {t.get_fontsize()} pt" for t, _ in spans if t.get_fontsize() < MIN_PT]
    for i, (ta, a) in enumerate(spans):
        for tb, b in spans[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                problems.append(f"labels overlap: {ta.get_text()!r} and {tb.get_text()!r}")
    return problems


def main() -> int:
    """Draw, check and write the figure; 0 on success, 1 when a check fails."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    ex = load_example(REPRO)
    font_files = configure_fonts()
    problems = label_problems(font_files, list(ex.steps) + list(FRESH_STEPS) + list(LANE_LABELS)
                              + [ex.history_answer, ex.fresh_answer, "≠"])
    fig, ax = new_canvas()
    geo, gap = layout(ax, ex)
    boxed, free = draw(ax, ex, geo)
    problems += check(ax, boxed, free, gap, geo["separator"])
    for problem in problems:
        logger.error(problem)
    if problems:
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)
    fig.savefig(os.path.join(OUT_DIR, f"{STEM}.svg"), format="svg", metadata={"Date": None})
    fig.savefig(os.path.join(OUT_DIR, f"{STEM}.pdf"), format="pdf", metadata={"CreationDate": None})
    logger.info("wrote %s.{svg,pdf} in %s (%.2f x %.2f in)", STEM, OUT_DIR, FIG_W_IN, FIG_H_IN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
