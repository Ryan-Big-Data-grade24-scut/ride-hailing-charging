"""Export a .pptx to .pdf through Microsoft PowerPoint via COM.

Usage:  python tools/pptx_to_pdf.py <input.pptx> [output.pdf]
"""
import os
import sys

import win32com.client as win32


def convert(pptx_path: str, pdf_path: str) -> None:
    pptx_path = os.path.abspath(pptx_path)
    pdf_path = os.path.abspath(pdf_path)
    app = win32.gencache.EnsureDispatch("PowerPoint.Application")
    pres = app.Presentations.Open(pptx_path, WithWindow=False)
    try:
        pres.SaveAs(pdf_path, 32)  # 32 = ppSaveAsPDF
    finally:
        pres.Close()


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".pdf"
    convert(src, dst)
    print("wrote", dst)
