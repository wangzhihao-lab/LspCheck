"""Shared style of the evaluation figures (figures 3 to 5 of the paper).

The look follows the evaluation figures of recent TSE testing papers read as exemplars
(refs/tse_exemplars_comparison.md): white background, only the left and bottom axes, light
horizontal grid lines, series told apart by colour and by marker or dash, (a)/(b) panel titles,
Times New Roman text (mathematics in STIX, the matching Times design) at the size of the caption. Colours are the paper palette in its fixed order
(the default for every figure). Figures are drawn at print size, so LaTeX includes them
without scaling, and saved as SVG with editable text and as PDF with embedded TrueType fonts.

Run line: imported by the figure scripts; not run directly.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

logger = logging.getLogger(__name__)

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT_DIR = os.path.join(REPO, "paper", "figures")
DATA = os.path.join(REPO, "data", "lsptest", "figure_data.json")

PALETTE: Tuple[str, ...] = ("#332288", "#117733", "#44AA99", "#88CCEE", "#DDCC77", "#CC6677", "#AA4499", "#882255")
INK = "#1a1a1a"
GRID = "#d9d9d9"
MUTED = "#8c8c8c"          # for oracles that found nothing and for not-applicable marks
COLUMN_W, TEXT_W = 3.5, 7.16   # IEEE two-column widths, inches
FONT_CHOICES = ("Times New Roman", "Times", "STIXGeneral", "DejaVu Serif")  # the default for every figure
BASE_PT, SMALL_PT = 7.0, 7.0  # 7 pt minimum after scaling (figfont_audit; TSE1 reviewer on small figure text)


def configure() -> str:
    """Set the rc parameters shared by all figures; returns the font family used."""
    family = FONT_CHOICES[-1]
    for name in FONT_CHOICES:
        try:
            font_manager.findfont(font_manager.FontProperties(family=name), fallback_to_default=False)
            family = name
            break
        except ValueError:
            continue
    matplotlib.rcParams.update({
        "font.family": "serif", "font.serif": [family], "mathtext.fontset": "stix", "font.size": BASE_PT,
        "axes.titlesize": BASE_PT, "axes.labelsize": BASE_PT, "xtick.labelsize": SMALL_PT, "ytick.labelsize": SMALL_PT,
        "legend.fontsize": SMALL_PT, "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK, "ytick.color": INK, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
        "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5, "lines.linewidth": 1.1,
        "lines.markersize": 3.5, "axes.spines.top": False, "axes.spines.right": False,
        "axes.prop_cycle": matplotlib.cycler(color=list(PALETTE)), "legend.frameon": False,
        "svg.fonttype": "none", "pdf.fonttype": 42, "svg.hashsalt": "lspcheck", "text.hinting": "no_hinting",
    })
    return family


def grid_y(ax: Any) -> None:
    """Light horizontal grid lines behind the data, as in the exemplars."""
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, linewidth=0.5)


def load_data() -> Dict[str, Any]:
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def save(fig: Figure, stem: str) -> Sequence[str]:
    """Write <stem>.svg (text kept as text) and <stem>.pdf under paper/figures/."""
    os.makedirs(OUT_DIR, exist_ok=True)
    paths = []
    for ext in ("svg", "pdf"):
        path = os.path.join(OUT_DIR, f"{stem}.{ext}")
        fig.savefig(path, format=ext, metadata={"Creator": None} if ext == "svg" else {"Creator": None, "Producer": None})
        paths.append(path)
    logger.info("wrote %s", ", ".join(os.path.relpath(p, REPO) for p in paths))
    return paths


__all__ = ["COLUMN_W", "GRID", "INK", "MUTED", "PALETTE", "TEXT_W", "configure", "grid_y", "load_data", "save"]
