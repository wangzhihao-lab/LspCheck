"""Fig. 2 of the paper: the parts of the harness as a left-to-right pipeline in two rows.

Every box carries a numbered badge on its top-left corner, in the order of the steps that the caption
walks through (as the overview figures of the TSE exemplars do), coloured with the full palette colour
of its phase, its digit white or dark by contrast. Draws the figure at its final print size, a full-width figure* of 7.16 in x 2.0 in, so that the
paper includes it without scaling. All labels use one font (Times New Roman, else Times, STIXGeneral or
DejaVu Serif) at 7 pt or more. Fills are light tints of the paper palette, one colour per phase in
palette order (run, check, triage, verdict); the raters' verdicts, the only manual step, also have a
dashed outline. After drawing, the script checks that every label sits inside its box with a
clearance, that no two labels overlap and that the font has every glyph; it exits with status 1 if
a check fails; the badges are also checked against the labels and the figure edge. Writes paper/figures/architecture.svg (labels kept as <text> elements) and
paper/figures/architecture.pdf (TrueType fonts embedded).

Run line: python3 scripts/paper/figures/fig_architecture.py
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import matplotlib
from matplotlib import font_manager
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgb
from matplotlib.figure import Figure
from matplotlib.ft2font import FT2Font
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path
from matplotlib.text import Text

logger = logging.getLogger(__name__)

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT_DIR = os.path.join(REPO, "paper", "figures")
STEM = "architecture"

FIG_W_IN, FIG_H_IN = 7.16, 2.0
FONT_CHOICES = ("Times New Roman", "Times", "STIXGeneral", "DejaVu Serif")  # the default for every figure
TITLE_PT, BODY_PT, MIN_PT = 8.0, 7.0, 7.0
LINESPACING = 1.2

PALETTE = ("#332288", "#117733", "#44AA99", "#88CCEE", "#DDCC77", "#CC6677", "#AA4499", "#882255")
INK = "#1a1a1a"          # all text: dark on light fills
CONNECTOR = "#3c3c3c"    # arrows and the dashed outline of the manual step
FILL_TINT = 0.2          # share of the palette colour in a fill (the rest is white)
MANUAL_TINT = 0.3        # the light-blue fill needs a little more colour to show

PAD_X, PAD_Y = 5.0, 4.5  # inner padding of a box, pt
TITLE_GAP = 1.5          # between a title and its sub-label, pt
LIST_GAP = 3.0           # between the relations title and its list
COL_GAP = 10.0           # between the two list columns
MARGIN = 1.5             # figure edge to the outermost outline
ROW_GAP = 16.0           # between the rows; the return connector runs in its middle
KEYS_GAP = 10.0          # between the stable-keys box and the relations box
MIN_ARROW = 14.0         # shortest horizontal arrow allowed
CLEARANCE = 1.0          # least space between a label and its box outline
ROUNDING = 3.0
LINE_W = 0.8
ARROW_SCALE = 8.0
BADGE_R = 5.0            # radius of a step badge, pt
BADGE_PT = 7.0           # its digit
BADGE_INSET = 6.5        # badge centre to the box's left edge, pt
BADGE_RISE = 2.0         # badge centre above the box's top edge, so the badge clears the title


@dataclass(frozen=True)
class Stage:
    """One box of the pipeline: a bold title, an optional sub-label and its phase colour."""

    key: str
    title: str
    body: str
    phase: int
    manual: bool = False


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


# Phases in palette order: 0 run (indigo), 1 check (green), 2 triage (teal), 3 verdict (light blue).
STAGES: Tuple[Stage, ...] = (
    Stage("build", "Project + server build", "pinned project commit,\nserver release", 0),
    Stage("driver", "Headless LSP\nclient & driver", "operations, settling", 0),
    Stage("keys", "Stable keys", "fresh baseline + control", 1),
    Stage("filter", "Stability filter", "3 of 3 fresh replays", 1),
    Stage("groups", "Signatures & groups", "", 2),
    Stage("reduction", "Reduction", "delta debugging,\ntarget narrowing", 2),
    Stage("drafts", "Report drafts", "minimal steps, expected vs actual, replay command", 2),
    Stage("verdicts", "Raters' verdicts", "bug / legitimate / artifact", 3, manual=True),
)
RELATIONS_KEY, RELATIONS_PHASE = "relations", 1
RELATIONS_TITLE = "Relations R1–R5 and baselines"
RELATION_INPUTS: Tuple[Tuple[str, ...], ...] = (  # two list columns: the five relations, then the two baselines
    ("histories H1–H9 (R1)", "handles (R2)", "routes (R3)", "edits + seeded errors M1–M4 (R4)"),
    ("transformations T1–T6 (R5)", "baseline: crash check (R0)", "baseline: TS6 vs TS7 (R6)"),
)
ROW1 = ("build", "driver", RELATIONS_KEY, "filter")   # the stable-keys box sits above the relations
ROW2 = ("groups", "reduction", "drafts", "verdicts")  # reached from "filter" by a return connector
STEP_ORDER = ("build", "driver", "keys", RELATIONS_KEY, "filter", "groups", "reduction", "drafts", "verdicts")


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
        logger.info("font: %s (%s)", family, ", ".join(files))
        return files
    raise RuntimeError("no font among " + ", ".join(FONT_CHOICES))


def all_labels() -> List[str]:
    """Every string the figure prints."""
    return [s.title for s in STAGES] + [s.body for s in STAGES] + [RELATIONS_TITLE] + [
        item for col in RELATION_INPUTS for item in col]


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


def put_text(ax: Axes, x: float, y: float, text: str, size: float, bold: bool,
             ha: str = "center", va: str = "top") -> Text:
    """A label in the figure's text style."""
    return ax.text(x, y, text, fontsize=size, fontweight="bold" if bold else "normal", color=INK,
                   ha=ha, va=va, linespacing=LINESPACING, zorder=3)


def extent(ax: Axes, artist: Text) -> Tuple[float, float, float, float]:
    """(x0, y0, x1, y1) of a label in points."""
    bb = artist.get_window_extent(ax.figure.canvas.get_renderer()).transformed(ax.transData.inverted())
    return bb.x0, bb.y0, bb.x1, bb.y1


def measure(ax: Axes, text: str, size: float, bold: bool) -> Tuple[float, float]:
    """Width and height in points of a possibly multi-line label."""
    if not text:
        return 0.0, 0.0
    artist = put_text(ax, 0, 0, text, size, bold)
    x0, y0, x1, y1 = extent(ax, artist)
    artist.remove()
    return x1 - x0, y1 - y0


def content_sizes(ax: Axes) -> Dict[str, Tuple[float, float]]:
    """Width and height of the text block of every box."""
    sizes = {}
    for stage in STAGES:
        tw, th = measure(ax, stage.title, TITLE_PT, True)
        bw, bh = measure(ax, stage.body, BODY_PT, False)
        sizes[stage.key] = (max(tw, bw), th + (TITLE_GAP + bh if stage.body else 0.0))
    tw, th = measure(ax, RELATIONS_TITLE, TITLE_PT, True)
    cols = [measure(ax, "\n".join(col), BODY_PT, False) for col in RELATION_INPUTS]
    list_w = sum(w for w, _ in cols) + COL_GAP * (len(cols) - 1)
    sizes[RELATIONS_KEY] = (max(tw, list_w), th + LIST_GAP + max(h for _, h in cols))
    return sizes


def layout(sizes: Dict[str, Tuple[float, float]]) -> Tuple[Dict[str, Box], float]:
    """Boxes on a four-column grid shared by both rows, and the horizontal arrow length."""
    width, height = FIG_W_IN * 72, FIG_H_IN * 72
    need_w = {k: w + 2 * PAD_X for k, (w, _) in sizes.items()}
    need_h = {k: h + 2 * PAD_Y for k, (_, h) in sizes.items()}
    cols = [max(need_w[a], need_w[b]) for a, b in zip(ROW1, ROW2)]
    gap = (width - 2 * MARGIN - sum(cols)) / (len(cols) - 1)
    row_h = max(need_h[k] for k in ROW1 + ROW2 if k != RELATIONS_KEY)
    rel_y = MARGIN + row_h + ROW_GAP
    rel_h = need_h[RELATIONS_KEY]
    boxes: Dict[str, Box] = {}
    x = MARGIN
    for col_w, top_key, bottom_key in zip(cols, ROW1, ROW2):
        boxes[bottom_key] = Box(x, MARGIN, col_w, row_h)
        if top_key == RELATIONS_KEY:
            boxes[top_key] = Box(x, rel_y, col_w, rel_h)
            boxes["keys"] = Box(x + (col_w - need_w["keys"]) / 2, rel_y + rel_h + KEYS_GAP,
                                need_w["keys"], need_h["keys"])
        else:
            boxes[top_key] = Box(x, rel_y + (rel_h - row_h) / 2, col_w, row_h)
        x += col_w + gap
    logger.info("columns %s pt, arrows %.1f pt, top of stable keys %.1f of %.1f pt",
                [round(c, 1) for c in cols], gap, boxes["keys"].y1, height)
    return boxes, gap


def draw_box(ax: Axes, box: Box, phase: int, manual: bool) -> None:
    """A rounded box with a light fill; the manual step gets a dashed outline."""
    colour = PALETTE[phase]
    ax.add_patch(FancyBboxPatch(
        (box.x, box.y), box.w, box.h, boxstyle=f"round,pad=0,rounding_size={ROUNDING}",
        facecolor=tint(colour, MANUAL_TINT if manual else FILL_TINT),
        edgecolor=CONNECTOR if manual else colour, linewidth=LINE_W,
        linestyle=(0, (3.0, 1.6)) if manual else "solid", zorder=2))


def draw_arrow(ax: Axes, points: Sequence[Tuple[float, float]]) -> None:
    """A polyline ending in a filled arrowhead whose tip is the last point."""
    path = Path(list(points), [Path.MOVETO] + [Path.LINETO] * (len(points) - 1))
    ax.add_patch(FancyArrowPatch(path=path, arrowstyle="-|>", mutation_scale=ARROW_SCALE,
                                 linewidth=LINE_W, color=CONNECTOR, joinstyle="miter",
                                 capstyle="butt", zorder=1))


def stage_texts(ax: Axes, stage: Stage, box: Box) -> List[Text]:
    """Title and sub-label, centred as one block in the box."""
    _, th = measure(ax, stage.title, TITLE_PT, True)
    _, bh = measure(ax, stage.body, BODY_PT, False)
    top = box.cy + (th + (TITLE_GAP + bh if stage.body else 0.0)) / 2
    texts = [put_text(ax, box.cx, top, stage.title, TITLE_PT, True)]
    if stage.body:
        texts.append(put_text(ax, box.cx, top - th - TITLE_GAP, stage.body, BODY_PT, False))
    return texts


def relations_texts(ax: Axes, box: Box) -> List[Text]:
    """The relations title over a two-column list of the inputs each relation generates."""
    _, th = measure(ax, RELATIONS_TITLE, TITLE_PT, True)
    cols = [measure(ax, "\n".join(col), BODY_PT, False) for col in RELATION_INPUTS]
    list_w = sum(w for w, _ in cols) + COL_GAP * (len(cols) - 1)
    top = box.cy + (th + LIST_GAP + max(h for _, h in cols)) / 2
    texts = [put_text(ax, box.cx, top, RELATIONS_TITLE, TITLE_PT, True)]
    x = box.cx - list_w / 2
    for col, (w, _) in zip(RELATION_INPUTS, cols):
        texts.append(put_text(ax, x, top - th - LIST_GAP, "\n".join(col), BODY_PT, False, ha="left"))
        x += w + COL_GAP
    return texts


def draw(ax: Axes, boxes: Dict[str, Box]) -> List[Tuple[str, Box, List[Text]]]:
    """All boxes, labels and arrows; returns each box with its labels for the checks."""
    placed = []
    for stage in STAGES:
        draw_box(ax, boxes[stage.key], stage.phase, stage.manual)
        placed.append((stage.key, boxes[stage.key], stage_texts(ax, stage, boxes[stage.key])))
    rel = boxes[RELATIONS_KEY]
    draw_box(ax, rel, RELATIONS_PHASE, False)
    placed.append((RELATIONS_KEY, rel, relations_texts(ax, rel)))
    for row in (ROW1, ROW2):
        for a, b in zip(row, row[1:]):
            y = boxes[a].cy if row is ROW2 else rel.cy
            draw_arrow(ax, [(boxes[a].x1, y), (boxes[b].x, y)])
    keys = boxes["keys"]
    draw_arrow(ax, [(rel.cx, keys.y), (rel.cx, rel.y1)])
    last, first = boxes[ROW1[-1]], boxes[ROW2[0]]
    y_mid = (rel.y + first.y1) / 2
    draw_arrow(ax, [(last.cx, last.y), (last.cx, y_mid), (first.cx, y_mid), (first.cx, first.y1)])
    return placed


def phase_of(key: str) -> int:
    """The phase of a box, for the colour of its badge."""
    return RELATIONS_PHASE if key == RELATIONS_KEY else next(s.phase for s in STAGES if s.key == key)


def digit_colour(fill: str) -> str:
    """White or the ink colour, whichever contrasts more with the badge fill (WCAG luminance)."""
    def lum(rgb: Tuple[float, float, float]) -> float:
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    l_fill = lum(to_rgb(fill))
    on_white = 1.05 / (l_fill + 0.05)
    on_ink = (l_fill + 0.05) / (lum(to_rgb(INK)) + 0.05)
    return "white" if on_white >= on_ink else INK


def draw_badges(ax: Axes, boxes: Dict[str, Box]) -> List[Tuple[str, Box]]:
    """A filled circle with a step number (white or ink, by contrast) on the top-left corner of every box.

    Returns:
        Each badge's number and the square that bounds its circle, for the checks.
    """
    badges = []
    for number, key in enumerate(STEP_ORDER, start=1):
        box = boxes[key]
        cx, cy = box.x + BADGE_INSET, box.y1 + BADGE_RISE
        ax.add_patch(Circle((cx, cy), BADGE_R, facecolor=PALETTE[phase_of(key)], edgecolor="white",
                            linewidth=0.6, zorder=4))
        ax.text(cx, cy, str(number), fontsize=BADGE_PT, fontweight="bold", color=digit_colour(PALETTE[phase_of(key)]),
                ha="center", va="center_baseline", zorder=5)
        badges.append((str(number), Box(cx - BADGE_R, cy - BADGE_R, 2 * BADGE_R, 2 * BADGE_R)))
    return badges


def check_badges(ax: Axes, badges: Sequence[Tuple[str, Box]],
                 placed: Sequence[Tuple[str, Box, List[Text]]]) -> List[str]:
    """Badges inside the figure and clear of every label."""
    width, height = FIG_W_IN * 72, FIG_H_IN * 72
    problems = []
    for number, b in badges:
        if b.x < 0.5 or b.y < 0.5 or b.x1 > width - 0.5 or b.y1 > height - 0.5:
            problems.append(f"badge {number} leaves the figure: {b}")
        for name, _, texts in placed:
            for t in texts:
                x0, y0, x1, y1 = extent(ax, t)
                if b.x < x1 + CLEARANCE and x0 - CLEARANCE < b.x1 and b.y < y1 + CLEARANCE and y0 - CLEARANCE < b.y1:
                    problems.append(f"badge {number} touches label {t.get_text()!r} of {name}")
    return problems


def check(ax: Axes, placed: Sequence[Tuple[str, Box, List[Text]]], gap: float) -> List[str]:
    """Labels inside their boxes with clearance, no overlapping labels, sizes, arrow lengths."""
    width, height = FIG_W_IN * 72, FIG_H_IN * 72
    problems = [] if gap >= MIN_ARROW else [f"arrows {gap:.1f} pt, shorter than {MIN_ARROW} pt"]
    spans = []
    for name, box, texts in placed:
        if box.x < 0.5 or box.y < 0.5 or box.x1 > width - 0.5 or box.y1 > height - 0.5:
            problems.append(f"box {name} leaves the figure: {box}")
        for t in texts:
            x0, y0, x1, y1 = extent(ax, t)
            if t.get_fontsize() < MIN_PT:
                problems.append(f"{name}: {t.get_text()!r} is {t.get_fontsize()} pt")
            if (x0 < box.x + CLEARANCE or x1 > box.x1 - CLEARANCE
                    or y0 < box.y + CLEARANCE or y1 > box.y1 - CLEARANCE):
                problems.append(f"{name}: {t.get_text()!r} not {CLEARANCE} pt inside its box")
            spans.append((t.get_text(), (x0, y0, x1, y1)))
    for i, (ta, a) in enumerate(spans):
        for tb, b in spans[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                problems.append(f"labels overlap: {ta!r} and {tb!r}")
    return problems


def main() -> int:
    """Draw, check and write the figure; 0 on success, 1 when a check fails."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    font_files = configure_fonts()
    problems = label_problems(font_files, all_labels())
    fig, ax = new_canvas()
    boxes, gap = layout(content_sizes(ax))
    placed = draw(ax, boxes)
    problems += check(ax, placed, gap) + check_badges(ax, draw_badges(ax, boxes), placed)
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
