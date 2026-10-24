"""Export a .docx to .pdf through Microsoft Word via COM.

Do NOT use LibreOffice for this. LibreOffice's OMML renderer mangles the
parallel-bar operator: it comes out as U+2226 FORCED (the "does not
divide" sign) instead of U+2225 PARALLEL TO, which the paper uses in the
objective function. Word renders the equations correctly, so Word is the
only safe exporter here.

Usage:  python tools/docx_to_pdf.py <input.docx> [output.pdf]
"""
import os
import sys

import win32com.client as win32


def convert(docx_path: str, pdf_path: str) -> None:
    docx_path = os.path.abspath(docx_path)
    pdf_path = os.path.abspath(pdf_path)

    word = win32.gencache.EnsureDispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(docx_path, ReadOnly=True)
        # 17 = wdExportFormatPDF
        doc.ExportAsFixedFormat(OutputFileName=pdf_path, ExportFormat=17)
        doc.Close(False)
    finally:
        word.Quit()
    print("wrote", pdf_path)


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".pdf"
    convert(src, dst)
