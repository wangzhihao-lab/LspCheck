"""Figure: bugs found on the current releases as run-hours accumulate, per oracle (RQ2 and RQ3).

Reads bugs_over_time from data/lsptest/figure_data.json (scripts/paper/numbers_figures.py): for every
oracle, the cumulative run-hours of its runs in the order they finished, first in the campaign on the
first corpus and then in the campaign on the second, and the points where a bug group and a distinct
bug were first confirmed, under the final verdicts (distinct bugs are root causes, one numbering for
both corpora). Panel (a) counts bug groups, panel (b) distinct bugs. The five relations are solid
lines in palette order; the crash check and the cross-implementation comparison, the oracles of
existing tools run in the same harness, are dashed. Each oracle has its own run-hours, so the second
corpus starts at a different point on each line: a short vertical bar across the line marks it. A
small tick ends each line. Drawn at text width; writes paper/figures/rq2_over_time.{svg,pdf}.

Run line: python3 scripts/paper/figures/fig_rq2_over_time.py
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as fs  # noqa: E402

from matplotlib.figure import Figure  # noqa: E402

logger = logging.getLogger(__name__)
SERIES: Tuple[Tuple[str, str, str, str, str], ...] = (  # key, label, colour, line style, marker
    ("R1", "R1 history independence", fs.PALETTE[0], "-", "o"),
    ("R2", "R2 handle validity", fs.PALETTE[1], "-", "s"),
    ("R3", "R3 route equivalence", fs.PALETTE[2], "-", "^"),
    ("R4", "R4 edit validity", fs.PALETTE[3], "-", "D"),
    ("R5", "R5 transformations", fs.PALETTE[4], "-", "v"),
    ("R0", "Crash check (R0)", fs.PALETTE[5], "--", "x"),
    ("R6", "TS6 vs TS7 (R6)", fs.PALETTE[6], ":", "+"),
)
PANELS = (("bug_groups", "(a) Bug groups"), ("bugs", "(b) Distinct bugs"))
SECOND = "main_v2"  # the campaign on the second corpus, as keyed in campaign_start_hours


def steps(points: List[Dict[str, Any]], field: str) -> Tuple[List[float], List[int]]:
    return [p["hours"] for p in points], [p[field] for p in points]


def value_at(xs: List[float], ys: List[int], x: float) -> int:
    """The step function's value just before x (the count when the second corpus starts)."""
    return max((y for xx, y in zip(xs, ys) if xx <= x), default=0)


def draw(data: Dict[str, Any]) -> Figure:
    fig = Figure(figsize=(fs.TEXT_W, 1.75))
    gs = fig.add_gridspec(1, 3, width_ratios=(1.0, 1.0, 0.62), wspace=0.28, left=0.055, right=0.995, top=0.88, bottom=0.2)
    handles = []
    xmax = max(v["hours"] for v in data.values())
    for i, (field, title) in enumerate(PANELS):
        ax = fig.add_subplot(gs[0, i])
        for key, label, colour, style, marker in SERIES:
            pts = data[key]["points"]
            xs, ys = steps(pts, field)
            line, = ax.step(xs, ys, where="post", color=colour, linestyle=style, linewidth=1.1, label=label)
            ev = [(x, y) for (x, y), (_, prev) in zip(zip(xs[1:], ys[1:]), zip(xs, ys)) if y > prev]
            if ev:
                ax.plot([x for x, _ in ev], [y for _, y in ev], linestyle="none", marker=marker, color=colour,
                        markersize=3.2, markerfacecolor="white" if marker not in ("x", "+") else colour, markeredgewidth=0.9)
            ax.plot([xs[-1]], [ys[-1]], marker="|", color=colour, markersize=3, markeredgewidth=0.8)
            start = data[key].get("campaign_start_hours", {}).get(SECOND)
            if start:  # where the oracle's runs on the second corpus begin
                ax.plot([start], [value_at(xs, ys, start)], marker="|", color=colour, markersize=9,
                        markeredgewidth=1.6, zorder=4)
            if i == 0:
                handles.append((line, marker, colour, style, label))
        zero = [label.split(" (")[0].split(" ")[0] if key not in ("R0", "R6") else key
                for key, label, *_ in SERIES if max(p[field] for p in data[key]["points"]) == 0]
        if zero:
            ax.text(0.98, 0.1, f"{', '.join(zero)}: none", transform=ax.transAxes, ha="right", va="bottom",
                    fontsize=fs.SMALL_PT, color=fs.MUTED)
        ax.set_title(title, loc="left", pad=3)
        ax.set_xlabel("Run-hours of the oracle, first corpus then second")
        ax.set_xlim(0, xmax * 1.02)
        top = max(max(p[field] for p in data[k]["points"]) for k, *_ in SERIES)
        ax.set_ylim(-0.4, top * 1.12 + 0.5)
        fs.grid_y(ax)
    ax_leg = fig.add_subplot(gs[0, 2])
    ax_leg.axis("off")
    from matplotlib.lines import Line2D
    proxies = [Line2D([], [], color=c, linestyle=st, marker=m, markersize=3.2, linewidth=1.1,
                      markerfacecolor="white" if m not in ("x", "+") else c, markeredgewidth=0.9) for _, m, c, st, _ in handles]
    proxies.append(Line2D([], [], color=fs.INK, linestyle="none", marker="|", markersize=9, markeredgewidth=1.6))
    ax_leg.legend(proxies, [h[4] for h in handles] + ["Second corpus starts"], loc="center left", handlelength=2.2,
                  borderaxespad=0.0, labelspacing=0.45)
    return fig


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fs.configure()
    fig = draw(fs.load_data()["bugs_over_time"])
    fs.save(fig, "rq2_over_time")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
