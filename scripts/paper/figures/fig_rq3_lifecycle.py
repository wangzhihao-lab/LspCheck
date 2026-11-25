"""Figure (supplement, Appendix N): the releases on which each distinct bug reproduces, over two years of releases.

Reads lifecycle_cur from data/lsptest/figure_data.json (scripts/paper/numbers_release_cur.py): for every
distinct bug of both corpora, its representative group (release_builds.REP_RULE) replayed three times on
releases of its server line, from about two years before the campaign to the newest releases of 2026-11-18,
and, where it was replayed there, on the gopls development head of that day (a diamond). One row per bug,
grouped by server line (colour, in palette order: gopls, rust-analyzer, TypeScript 6, TypeScript 7, pyright),
bugs by number within a line; x is the release (or commit) date. A filled marker means the bug reproduced in 3
of 3 replays, a half-filled one in 1 or 2, an open one in none; a grey cross marks a release that could not
load the project (an older toolchain or a build that does not start) or was not run. A line joins the
reproducing releases from the oldest to the newest. The height grows with the number of rows; drawn at text
width; writes paper/figures/rq3_lifecycle.{svg,pdf}.

Run line: python3 scripts/paper/figures/fig_rq3_lifecycle.py
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as fs  # noqa: E402

import matplotlib.dates as mdates  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

logger = logging.getLogger(__name__)
LINES: Tuple[Tuple[str, str, str], ...] = (
    ("gopls", "gopls", fs.PALETTE[0]), ("rust-analyzer", "rust-analyzer", fs.PALETTE[1]),
    ("ts6", "TypeScript 6", fs.PALETTE[2]), ("ts7", "TypeScript 7", fs.PALETTE[3]), ("pyright", "pyright", fs.PALETTE[4]))
TICK_COLOUR = {fs.PALETTE[3]: "#3d8fb3", fs.PALETTE[4]: "#9c8a2e"}  # darker shades of the light colours, for text
LABELS: Dict[str, str] = {
    "C1": "C1 rename outside editor", "C2": "C2 request right after open", "C3": "C3 stale code-action resolve",
    "C4": "C4 stale completion resolve", "C5": "C5 “Create variable”", "C6": "C6 “Create function”",
    "C7": "C7 “Remove variable”", "C8": "C8 definitions in expansion", "C9": "C9 test-file references",
    "C10": "C10 references after edit", "C11": "C11 “Add missing properties”", "C12": "C12 configuration change",
    "C13": "C13 root-module files changed", "C14": "C14 go.mod broken and restored", "C15": "C15 “Delete var”",
    "C16": "C16 carriage returns", "C17": "C17 references assertion", "C18": "C18 types after other files",
    "C19": "C19 hover after rename", "C20": "C20 references in unopened files", "C21": "C21 signature after open",
    "C22": "C22 auto-import into __future__", "C23": "C23 references time out",
    "C24": "C24 semantic tokens time out", "C25": "C25 pushed diagnostics stop", "C26": "C26 range semantic tokens",
    "C27": "C27 macro-name completion", "C28": "C28 attribute completion", "C29": "C29 “Add .to_owned() here”",
    "C30": "C30 file open order", "C31": "C31 inlay hint after rename", "C32": "C32 “Convert to async function”",
    "C33": "C33 “Fix all spelling errors”", "C34": "C34 “Change spelling” on a tag",
    "C35": "C35 “Change spelling” in initializer"}
ROW_IN = 0.125                 # inches per bug row
TOP_IN, BOTTOM_IN = 0.52, 0.36  # legends above the axes (markers, then server lines); tick labels and axis label below
LEFT_IN, RIGHT_IN = 1.62, 0.1   # bug labels left of the axes


def date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def rows_in_order(life: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """(cause, line, colour) top to bottom: server lines in LINES order, causes by number within a line."""
    out = []
    for line, _, colour in LINES:
        causes = sorted((c for c, v in life.items() if v["line"] == line), key=lambda c: int(c[1:]))
        out += [(c, line, colour) for c in causes]
    return out


def draw(life: Dict[str, Any]) -> Figure:
    rows = rows_in_order(life)
    n = len(rows)
    height = TOP_IN + n * ROW_IN + BOTTOM_IN
    fig = Figure(figsize=(fs.TEXT_W, height))
    ax = fig.add_axes((LEFT_IN / fs.TEXT_W, BOTTOM_IN / height, 1 - (LEFT_IN + RIGHT_IN) / fs.TEXT_W,
                       n * ROW_IN / height))
    for i, (cause, line, colour) in enumerate(rows):
        y = n - 1 - i
        if i and rows[i - 1][1] != line:  # a light rule between server lines
            ax.axhline(y + 0.5, color=fs.GRID, linewidth=0.5, zorder=0)
        cells = life[cause]["cells"]
        hits = [date(c["released"]) for c in cells if c["state"] in ("reproduced", "partly")]
        if hits:
            ax.plot([min(hits), max(hits)], [y, y], color=colour, linewidth=2.2, alpha=0.35, solid_capstyle="round", zorder=1)
        for c in cells:
            x = date(c["released"])
            if c["state"] == "n/a":
                ax.plot([x], [y], marker="x", color=fs.MUTED, markersize=3.2, markeredgewidth=0.8, zorder=2)
                continue
            fill = {"reproduced": "full", "partly": "left", "not-reproduced": "none"}[c["state"]]
            head = "development head" in c["roles"]
            ax.plot([x], [y], marker="D" if head else "o", color=colour, markersize=3.8 if head else 4.2, fillstyle=fill,
                    markeredgewidth=0.9, markerfacecoloralt="white", markerfacecolor=colour if fill != "none" else "white",
                    zorder=3)
            if "campaign" in c["roles"]:
                ax.plot([x], [y], marker="o", color=fs.INK, markersize=7.0, fillstyle="none", markeredgewidth=0.6, zorder=4)
    ax.set_yticks(range(n), [LABELS.get(c, c) for c, _, _ in reversed(rows)])
    for tick, (_, line, colour) in zip(ax.get_yticklabels(), list(reversed(rows))):
        tick.set_color(TICK_COLOUR.get(colour, colour))
    ax.set_ylim(-0.6, n - 0.4)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(4, 10)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.set_xlim(date("2024-06-01"), date("2026-12-20"))
    ax.set_xlabel("Release date", labelpad=2)
    ax.xaxis.grid(True, color=fs.GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, pad=3)
    ax.spines["left"].set_visible(False)
    legend = [Line2D([], [], linestyle="none", marker="o", color=fs.INK, markersize=4.2, label="reproduces (3 of 3)"),
              Line2D([], [], linestyle="none", marker="o", color=fs.INK, markersize=4.2, fillstyle="left",
                     markerfacecoloralt="white", label="in 1 or 2 of 3"),
              Line2D([], [], linestyle="none", marker="o", color=fs.INK, markersize=4.2, markerfacecolor="white",
                     label="does not reproduce"),
              Line2D([], [], linestyle="none", marker="x", color=fs.MUTED, markersize=3.2, label="could not be run"),
              Line2D([], [], linestyle="none", marker="o", color=fs.INK, markersize=7.0, fillstyle="none",
                     markeredgewidth=0.6, label="release tested in the campaign"),
              Line2D([], [], linestyle="none", marker="D", color=fs.INK, markersize=3.8, markerfacecolor="white",
                     label="gopls development head (2026-11-18)")]
    lines = [Line2D([], [], color=colour, linewidth=2.2, alpha=0.6, label=name)
             for line, name, colour in LINES if any(v["line"] == line for v in life.values())]
    left = LEFT_IN / fs.TEXT_W
    fig.legend(handles=legend, loc="upper left", ncol=3, bbox_to_anchor=(left, 1 - 0.03 / height), handletextpad=0.3,
               columnspacing=1.2, borderaxespad=0.0, labelspacing=0.25)
    fig.legend(handles=lines, loc="upper left", ncol=len(lines), bbox_to_anchor=(left, 1 - 0.31 / height),
               handletextpad=0.4, columnspacing=1.2, borderaxespad=0.0, handlelength=1.6)
    return fig


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fs.configure()
    fig = draw(fs.load_data()["lifecycle_cur"])
    fs.save(fig, "rq3_lifecycle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
