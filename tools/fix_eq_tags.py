"""Replace LaTeX \\tag{n} with an in-equation right-hand number \\qquad\\qquad (n).

Pandoc's texmath does not implement \\tag, so tagged equations lose their
numbers on conversion to Word. Putting the number inside the equation body
keeps every cross-reference in the text valid and renders as native OMML.
"""
import io
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "paper.md"
src = io.open(path, encoding="utf-8").read()

pattern = re.compile(r"\\tag\{(\d+)\}")
n = len(pattern.findall(src))
src = pattern.sub(lambda m: "\\qquad\\qquad (" + m.group(1) + ")", src)

io.open(path, "w", encoding="utf-8").write(src)
print("replaced", n, "equation tags in", path)
