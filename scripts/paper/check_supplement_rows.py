"""Check that every row of every longtable in the supplement reaches the PDF.

A longtable whose first row is tall can lose the rest of its first chunk when the page builder breaks
just before the table (Table G2 once printed only C1 of its eleven rows). This check reads the body rows
of every generated table under paper/supplement/tables, takes the text of each row's first cell (and the
next cells while the key is short), and
looks for it in the PDF text in drawing order (pdftotext -raw), with case, spacing, hyphenation and
punctuation removed, within the table's own stretch of the PDF (from its caption to the next table's), so
that a key that other tables share does not hide a lost row. It reports every table with rows not found.

Run line: python3 scripts/paper/check_supplement_rows.py [path/to/supplement.pdf]
"""

from __future__ import annotations

import glob
import logging
import os
import re
import subprocess
import sys
from typing import Dict, List, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TABLES = os.path.join(REPO, "paper", "supplement", "tables")
PDF = os.path.join(REPO, "paper", "supplement", "supplement.pdf")
MIN_KEY = 8
logger = logging.getLogger("check_supplement_rows")


def normalize(text: str) -> str:
    """Lowercase letters and digits only, so that line breaks, hyphenation and spacing do not matter."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def brace_groups(text: str, start: int) -> List[Tuple[int, int]]:
    """Spans (inside the braces) of the consecutive top-level brace groups that begin at text[start]."""
    spans, i = [], start
    while i < len(text) and text[i] == "{":
        depth, j = 0, i
        while j < len(text):
            depth += {"{": 1, "}": -1}.get(text[j], 0) if text[j - 1:j] != "\\" else 0
            if depth == 0:
                break
            j += 1
        spans.append((i + 1, j))
        i = j + 1
    return spans


def latex_text(cell: str) -> str:
    """The printed text of a table cell: commands dropped, their arguments kept."""
    cell = cell.strip()
    if cell.startswith(r"\multicolumn"):
        spans = brace_groups(cell, len(r"\multicolumn"))
        if len(spans) >= 3:
            cell = cell[spans[2][0]:spans[2][1]]
    cell = re.sub(r"\\rel\{(\d)\}", r"R\1", cell)
    cell = re.sub(r"\\(apxbrk|allowbreak|hangindent=[^ ]*|hangafter=[^ ]*|newline|linebreak|par)\b(\{\})?", " ", cell)
    cell = re.sub(r"\\(textless|textgreater|textbackslash|rightarrow|to)\b", " ", cell)
    cell = re.sub(r"\\[a-zA-Z]+\*?", " ", cell)
    return re.sub(r"[{}$\\]", " ", cell)


def body_rows(tex: str) -> List[List[str]]:
    """Cells of the body rows of the first longtable in a generated table file."""
    start = max(tex.rfind(marker) for marker in (r"\endfirsthead", r"\endhead", r"\endfoot", r"\endlastfoot"))
    end = tex.find(r"\end{longtable}")
    rows = []
    for line in tex[start:end].splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith(("&", "\\midrule", "\\bottomrule", "\\toprule", "\\addlinespace", "%")):
            continue
        cells = re.split(r"(?<!\\)&", re.sub(r"\\\\\*?\s*$", "", line))
        rows.append(cells)
    return rows


def row_key(cells: List[str]) -> str:
    """The first cell of a row, extended by the next cells (which pdftotext -raw prints right after it) while
    the key is shorter than MIN_KEY characters."""
    key = ""
    for cell in cells[:3]:
        key += normalize(latex_text(cell))
        if len(key) >= MIN_KEY:
            break
    return key


def table_stretches(path: str) -> Dict[str, str]:
    """Normalized PDF text per table id, from the table's caption to the caption of the next table."""
    raw = subprocess.run(["pdftotext", "-raw", path, "-"], capture_output=True, text=True, check=True).stdout
    anchors = [(m.start(), m.group(1)) for m in re.finditer(r"TABLE ([A-Z]\d?): (?!\(continued\))", raw)]
    return {tid: normalize(raw[pos:anchors[i + 1][0] if i + 1 < len(anchors) else len(raw)])
            for i, (pos, tid) in enumerate(anchors)}


def check(pdf: str) -> Dict[str, Tuple[int, List[str]]]:
    stretches = table_stretches(pdf)
    report: Dict[str, Tuple[int, List[str]]] = {}
    for path in sorted(glob.glob(os.path.join(TABLES, "*.tex"))):
        with open(path, encoding="utf-8") as f:
            tex = f.read()
        if r"\begin{longtable}" not in tex:
            continue
        tid = os.path.basename(path).split("_")[0]
        text = stretches.get(tid, "")
        keys = [row_key(cells) for cells in body_rows(tex)]
        missing = [k for k in keys if len(k) >= MIN_KEY and k not in text]
        report[os.path.basename(path)] = (len(keys), missing)
    return report


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    pdf = sys.argv[1] if len(sys.argv) > 1 else PDF
    report = check(pdf)
    bad = 0
    for name, (n, missing) in report.items():
        if missing:
            bad += 1
            logger.error("%s: %d of %d rows not found, first: %s", name, len(missing), n, ", ".join(missing[:3]))
        else:
            logger.info("%s: all %d rows found", name, n)
    logger.info("%d tables checked, %d with missing rows (%s)", len(report), bad, os.path.relpath(pdf, REPO))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
