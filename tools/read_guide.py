"""Dump the official final-project guide (.docx) as plain text.

Used to re-check the formatting requirements (fonts, sizes, spacing, margins,
abstract length, equation policy, deliverable list) against the paper we are
producing, rather than relying on a remembered paraphrase.
"""
import re
import sys
import zipfile

path = sys.argv[1]
z = zipfile.ZipFile(path)
x = z.read("word/document.xml").decode("utf8")

# paragraphs
x = x.replace("</w:p>", "\n")
x = x.replace("<w:tab/>", "\t")
x = re.sub(r"<w:br[^>]*/>", "\n", x)
txt = re.sub(r"<[^>]+>", "", x)
txt = txt.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
for line in txt.split("\n"):
    line = line.strip()
    if line:
        print(line)
