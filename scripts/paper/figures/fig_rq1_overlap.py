"""Figure: historical bugs detected by each oracle and their overlaps (an UpSet plot), for RQ1 and RQ2.

Reads benchmark_overlap from data/lsptest/figure_data.json (scripts/paper/numbers_figures.py): the
reproduced benchmark bugs detected by at least one oracle under the joint verdicts of the two raters on
the pre-only signatures (the discussion's consensus, else the verdict both gave), with the oracles that
detected each. Sets are the five relations, the failing-request observer and the crash
check. The top bars count the bugs detected by exactly one combination of oracles, the left bars the
bugs each oracle detects; dark segments are bugs not run before the tool was frozen, light ones the
six run before. Drawn at one column width; writes paper/figures/rq1_overlap.{svg,pdf}.

Run line: python3 scripts/paper/figures/fig_rq1_overlap.py
"""

from __future__ import annotations

import collections
import logging
import os
import sys
from typing import Dict, FrozenSet, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as fs  # noqa: E402

from matplotlib.figure import Figure  # noqa: E402

logger = logging.getLogger(__name__)
SETS: Tuple[Tuple[str, str], ...] = (("R1", "R1 history"), ("R2", "R2 handles"), ("R3", "R3 routes"), ("R4", "R4 edits"),
                                     ("R5", "R5 transforms"), ("error", "Failing request"), ("R0", "Crash (R0)"))
HELD, DEV = fs.PALETTE[0], "#aaa3d6"   # indigo and a light tint of it


def tallies(rows: List[dict]) -> Tuple[List[Tuple[FrozenSet[str], int, int]], Dict[str, Tuple[int, int]]]:
    inter: Dict[FrozenSet[str], List[int]] = collections.defaultdict(lambda: [0, 0])
    size: Dict[str, List[int]] = {k: [0, 0] for k, _ in SETS}
    for r in rows:
        key = frozenset(o for o in r["oracles"] if o in size)
        if not key:
            continue
        inter[key][0 if r["held_out"] else 1] += 1
        for o in key:
            size[o][0 if r["held_out"] else 1] += 1
    ordered = sorted(inter.items(), key=lambda kv: (-(kv[1][0] + kv[1][1]), -kv[1][0], sorted(kv[0])))
    return [(k, v[0], v[1]) for k, v in ordered], {k: (v[0], v[1]) for k, v in size.items()}


def draw(rows: List[dict]) -> Figure:
    inters, sizes = tallies(rows)
    fig = Figure(figsize=(fs.COLUMN_W, 2.45))
    gs = fig.add_gridspec(2, 3, width_ratios=(0.75, 0.78, 2.3), height_ratios=(1.3, 1.0), wspace=0.0, hspace=0.06,
                          left=0.02, right=0.99, top=0.97, bottom=0.15)
    ax_bar = fig.add_subplot(gs[0, 2])
    ax_mat = fig.add_subplot(gs[1, 2], sharex=ax_bar)
    ax_set = fig.add_subplot(gs[1, 0], sharey=ax_mat)
    ax_lab = fig.add_subplot(gs[1, 1], sharey=ax_mat)
    xs = range(len(inters))
    held = [h for _, h, _ in inters]
    dev = [d for _, _, d in inters]
    ax_bar.bar(xs, held, color=HELD, width=0.62, label="not run before the freeze")
    ax_bar.bar(xs, dev, bottom=held, color=DEV, width=0.62, label="run before the freeze")
    for x, (h, d) in enumerate(zip(held, dev)):
        ax_bar.text(x, h + d + 0.3, str(h + d), ha="center", va="bottom", fontsize=fs.SMALL_PT)
    ax_bar.set_ylabel("Bugs")
    ax_bar.set_ylim(0, max(h + d for h, d in zip(held, dev)) * 1.18)
    fs.grid_y(ax_bar)
    ax_bar.tick_params(axis="x", bottom=False, labelbottom=False)
    ax_bar.legend(loc="upper right", handlelength=1.0, borderaxespad=0.1)
    names = [k for k, _ in SETS]
    ys = {k: len(SETS) - 1 - i for i, k in enumerate(names)}
    for x, (key, _, _) in enumerate(inters):
        ax_mat.scatter([x] * len(names), [ys[k] for k in names], s=9, color="#e3e3e3", zorder=1)
        on = sorted(ys[k] for k in key)
        ax_mat.scatter([x] * len(on), on, s=11, color=fs.INK, zorder=3)
        if len(on) > 1:
            ax_mat.plot([x, x], [on[0], on[-1]], color=fs.INK, linewidth=1.0, zorder=2)
    ax_mat.tick_params(axis="y", left=False, labelleft=False)
    ax_mat.tick_params(axis="x", bottom=False, labelbottom=False)
    for side in ("left", "bottom", "right"):
        ax_mat.spines[side].set_visible(False)
    ax_lab.axis("off")
    for k, label in SETS:
        ax_lab.text(0.5, ys[k], label, ha="center", va="center", fontsize=fs.SMALL_PT)
    ax_mat.set_xlim(-0.6, len(inters) - 0.4)
    for k in names:
        h, d = sizes[k]
        y = ys[k]
        ax_set.barh(y, h, color=HELD, height=0.55)
        ax_set.barh(y, d, left=h, color=DEV, height=0.55)
        ax_set.text(h + d + 0.5, y, str(h + d), va="center", ha="right", fontsize=fs.SMALL_PT)
    top = max(sum(v) for v in sizes.values())
    ax_set.set_xlim(top * 1.45, 0)
    ax_set.set_ylim(-0.6, len(SETS) - 0.4)
    ax_set.tick_params(axis="y", left=False, labelleft=False)
    ax_set.set_xlabel("Bugs per oracle", labelpad=1.5)
    ax_set.spines["left"].set_visible(False)
    ax_set.spines["right"].set_visible(False)
    ax_set.spines["top"].set_visible(False)
    return fig


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fs.configure()
    rows = fs.load_data()["benchmark_overlap"]["rows"]
    fig = draw(rows)
    fs.save(fig, "rq1_overlap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
