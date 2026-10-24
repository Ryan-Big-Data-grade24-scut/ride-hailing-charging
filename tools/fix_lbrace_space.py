"""Make sure \\lbrace is always followed by a space.

Pandoc's texmath reads "\\lbracea_t" as a control sequence named
"lbracea", fails, and leaves the equation in the document as raw LaTeX
text. A space after the command is enough to fix it, and is harmless for
the cases that already have one.
"""
import io
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "submit/paper.md"
src = io.open(path, encoding="utf-8").read()
out, n = re.subn(r"\\lbrace(?=\S)", r"\\lbrace ", src)
io.open(path, "w", encoding="utf-8").write(out)
print("spaces inserted after \\lbrace:", n)
