"""
Build the pandoc reference.docx that enforces the course formatting rules.

The guide (section 6) fixes the format precisely, and every one of these is
checked by the marker. Generating a reference document and letting pandoc
use it is the only reliable way to hit all of them at once:

    paper      Times New Roman 14 pt bold
    author     Times New Roman 10.5 pt
    abstract   Times New Roman 10.5 pt
    H1         Times New Roman 12 pt bold
    H2         Times New Roman 10.5 pt bold
    H3         Times New Roman 10.5 pt italic
    body       Times New Roman 10.5 pt, 1.5 line spacing, justified
    captions   Times New Roman 10 pt
    references Times New Roman 10 pt
    page       A4, 2.54 cm margins, page number in the footer

Equations stay native Word equation objects: pandoc turns LaTeX math into
OMML, so nothing is ever pasted as an image.

    python tools/make_reference_docx.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "reference.docx")

FONT = "Times New Roman"


def set_style(doc, name, size=None, bold=None, italic=None,
              align=None, line=None, space_after=None, space_before=None,
              color=None):
    """Patch one named style. Missing styles are skipped (pandoc's default
    reference document does not define every style we might want)."""
    try:
        st = doc.styles[name]
    except KeyError:
        return False
    f = st.font
    f.name = FONT
    rpr = st.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONT)
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color is not None:
        # pandoc's default reference document paints the headings in the
        # theme accent colour; a course paper wants plain black.
        f.color.rgb = RGBColor(0, 0, 0)
    pf = getattr(st, "paragraph_format", None)
    if align is not None and pf is not None:
        pf.alignment = align
    if line is not None and pf is not None:
        pf.line_spacing = line
    if space_after is not None and pf is not None:
        pf.space_after = Pt(space_after)
    if space_before is not None and pf is not None:
        pf.space_before = Pt(space_before)
    return True


def patch_doc_defaults(doc):
    """docDefaults wins over every style, so it has to be right too."""
    styles = doc.styles.element
    dd = styles.find(qn("w:docDefaults"))
    if dd is None:
        return
    rpr_default = dd.find(qn("w:rPrDefault"))
    if rpr_default is None:
        return
    rpr = rpr_default.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        rpr_default.append(rpr)
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONT)
    for tag, val in (("w:sz", "21"), ("w:szCs", "21")):     # 21 half-points = 10.5 pt
        el = rpr.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            rpr.append(el)
        el.set(qn("w:val"), val)


def add_page_number(paragraph):
    """A real PAGE field, so the number is live in Word."""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)
    run.font.name = FONT
    run.font.size = Pt(9)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ref = os.path.join(tmp, "ref.docx")
        # pandoc ships a reference document; start from it so every style
        # pandoc knows about is present.
        subprocess.run(
            ["pandoc", "--print-default-data-file", "reference.docx"],
            check=True, stdout=open(ref, "wb"))
        shutil.copy(ref, OUT)

    doc = Document(OUT)

    # ------------------------------------------------------------- page setup
    for sec in doc.sections:
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.left_margin = Cm(2.54)
        sec.right_margin = Cm(2.54)
        sec.top_margin = Cm(2.54)
        sec.bottom_margin = Cm(2.54)
        sec.footer_distance = Cm(1.27)
        footer = sec.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        fp.text = ""
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_page_number(fp)

    # ---------------------------------------------------------------- styles
    patch_doc_defaults(doc)
    J = WD_ALIGN_PARAGRAPH.JUSTIFY
    C = WD_ALIGN_PARAGRAPH.CENTER

    set_style(doc, "Normal", 10.5, align=J, line=1.5, space_after=0,
              space_before=0, color="black")
    set_style(doc, "Body Text", 10.5, align=J, line=1.5, color="black")
    set_style(doc, "First Paragraph", 10.5, align=J, line=1.5, color="black")
    # "Compact" is what pandoc puts in table cells. 10 pt single-spaced keeps
    # the wide comparison tables on one page instead of stranding them.
    # table cells: LEFT, not justified. In a narrow column, justification
    # stretches the spaces into rivers of white space.
    L = WD_ALIGN_PARAGRAPH.LEFT
    set_style(doc, "Compact", 10, align=L, line=1.0, color="black")
    # Pandoc's own reference document does not define a "Source Code"
    # paragraph style; if it is missing, pandoc invents one in the OUTPUT
    # document, inheriting Normal's justified alignment, and then the first
    # line of every code block is stretched across the page. Define it here
    # so the appendix commands render correctly.
    try:
        doc.styles["Source Code"]
    except KeyError:
        st = doc.styles.add_style("Source Code", WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = doc.styles["Normal"]
    set_style(doc, "Source Code", 9, align=L, line=1.0, color="black")
    set_style(doc, "Verbatim Char", 9, align=L)
    # the guide puts the abstract and keywords at 10.5 pt (五号)
    set_style(doc, "Abstract", 10.5, align=J, line=1.5, color="black")
    set_style(doc, "Abstract Title", 10.5, bold=True, align=J, line=1.5, color="black")
    set_style(doc, "Title", 14, bold=True, align=C, line=1.15,
              space_after=12, color="black")
    set_style(doc, "Subtitle", 10.5, align=C, line=1.15, color="black")
    set_style(doc, "Author", 10.5, align=C, line=1.15, space_after=6, color="black")
    set_style(doc, "Date", 10.5, align=C, line=1.15, color="black")
    set_style(doc, "Heading 1", 12, bold=True, italic=False, align=J,
              line=1.5, space_before=12, space_after=6, color="black")
    set_style(doc, "Heading 2", 10.5, bold=True, italic=False, align=J,
              line=1.5, space_before=10, space_after=4, color="black")
    set_style(doc, "Heading 3", 10.5, bold=False, italic=True, align=J,
              line=1.5, space_before=8, space_after=4, color="black")
    set_style(doc, "Heading 4", 10.5, bold=True, italic=False, align=J,
              line=1.5, color="black")
    # the caption styles inherit from pandoc's "Caption", which is italic;
    # the guide wants plain 10 pt captions, so switch the italic off
    set_style(doc, "Image Caption", 10, italic=False, align=C, line=1.0,
              space_after=10, space_before=4, color="black")
    set_style(doc, "Table Caption", 10, italic=False, align=C, line=1.0,
              space_after=4, space_before=8, color="black")
    set_style(doc, "Bibliography", 10, align=L, line=1.0, space_after=4, color="black")
    set_style(doc, "Block Text", 10.5, align=J, line=1.5, color="black")
    set_style(doc, "Quote", 10.5, align=J, line=1.5, color="black")
    set_style(doc, "Source Code", 9, align=L, line=1.0, color="black")
    set_style(doc, "Verbatim Char", 9)
    set_style(doc, "Macro Text", 10.5, color="black")

    # the table style pandoc uses
    try:
        tbl = doc.styles["Table"]
        rpr = tbl.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rfonts.set(qn(attr), FONT)
    except KeyError:
        pass

    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
