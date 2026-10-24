"""Give every Word table proportional column widths that respect content.

Pandoc turns a markdown pipe table into a Word table with
`<w:tblLayout w:type="fixed"/>` and a grid in which every column gets the
SAME width, because a pipe table's header separator carries no width
information. A seven-column comparison table then gets seven equal
columns, so a column of money sits next to a column of sentences and the
money wraps mid-number ("946.4" / "6").

The allocation here is two-sided:

  * each column asks for a width proportional to its longest cell;
  * each column also declares a floor -- the width its longest
    UNBREAKABLE token needs (a number like "946.46" cannot be split, so
    the column must be wide enough to hold it on one line).

Columns that are below their floor borrow the width from whichever column
currently has the most slack, so the table still sums to the text width.

Usage:  python tools/fix_table_widths.py <file.docx>
"""
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# usable text width in twips: A4 (11906) minus 2 x 1440 margins
TEXT_WIDTH_TW = 11906 - 2880
TEXT_WIDTH_CM = TEXT_WIDTH_TW / 567.0

# rough Times New Roman metrics at 10 pt, deliberately generous so that a
# number like "946.46" never breaks across two lines
CHAR_CM = 0.20           # average advance width
PAD_CM = 0.45            # cell margins, both sides
CAP = 45                # a cell longer than this does not claim more width


def cells_text(table):
    """Column -> list of cell strings (header first)."""
    cols = []
    for row in table.rows:
        for j, cell in enumerate(row.cells):
            if j >= len(cols):
                cols.append([])
            cols[j].append(cell.text.strip())
    return cols


def longest_token(text):
    """Longest whitespace-separated token, i.e. the part that cannot wrap."""
    best = 1
    for tok in text.split():
        best = max(best, len(tok))
    return best


def allocate(cols):
    want, floor = [], []
    for texts in cols:
        longest_cell = max((len(t) for t in texts), default=1)
        longest_word = max((longest_token(t) for t in texts), default=1)
        want.append(PAD_CM + min(longest_cell, CAP) * CHAR_CM)
        floor.append(PAD_CM + longest_word * CHAR_CM)

    total = sum(want)
    if total <= 0:
        return [TEXT_WIDTH_CM / len(cols)] * len(cols)
    w = [TEXT_WIDTH_CM * x / total for x in want]

    # raise anything below its floor, borrowing from the largest slack
    for _ in range(60):
        deficits = [(floor[i] - w[i], i) for i in range(len(w)) if w[i] < floor[i]]
        if not deficits:
            break
        deficit, i = max(deficits)
        slack = [(w[j] - floor[j], j) for j in range(len(w)) if j != i]
        donors = [(s, j) for s, j in slack if s > 1e-6]
        if not donors:
            break
        slack, j = max(donors)
        take = min(deficit, slack)
        w[i] += take
        w[j] -= take

    # last resort: still too wide, shrink proportionally
    total = sum(w)
    if total > TEXT_WIDTH_CM:
        w = [x * TEXT_WIDTH_CM / total for x in w]
    return w


def set_widths(table, widths_cm):
    widths = [w * 567 for w in widths_cm]
    tbl = table._tbl
    grid = tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(w)))
    for row in table.rows:
        for cell, w in zip(row.cells, widths):
            tcPr = cell._tc.get_or_add_tcPr()
            for old in tcPr.findall(qn("w:tcW")):
                tcPr.remove(old)
            tcW = OxmlElement("w:tcW")
            tcW.set(qn("w:w"), str(int(w)))
            tcW.set(qn("w:type"), "dxa")
            tcPr.append(tcW)


def set_row_properties(table):
    """Repeat the header row on a new page, and never split a row.

    Without the first, a table that breaks across a page shows the second
    half with no column headers at all; without the second, a row's text
    is cut in half by the page break.
    """
    for i, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        if i == 0:
            if trPr.find(qn("w:tblHeader")) is None:
                trPr.append(OxmlElement("w:tblHeader"))
        if trPr.find(qn("w:cantSplit")) is None:
            trPr.append(OxmlElement("w:cantSplit"))


def main(path):
    doc = Document(path)
    for i, table in enumerate(doc.tables, 1):
        cols = cells_text(table)
        if not cols:
            continue
        widths = allocate(cols)
        set_widths(table, widths)
        set_row_properties(table)
        print(f"  table {i}: " + " | ".join(f"{w:.1f}" for w in widths) + " cm")
    doc.save(path)
    print("rewrote", path)


if __name__ == "__main__":
    main(sys.argv[1])
