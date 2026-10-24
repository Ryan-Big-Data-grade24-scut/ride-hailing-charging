"""Apply the formatting fixes required by the official Final Project Guide.

Guide clauses being enforced (2026_Optimization_Methods_Final_Project.docx):

  6.2  Abstract / Keywords: 10.5 pt          -> Abstract / AbstractTitle styles
  6.2  References: 10 pt                     -> wrap the reference list in the
                                                "Bibliography" style
  6.4  "Place figure captions below figures
       and table titles above tables"          -> move every figure caption
                                                under its image
  6.4  "Number figures and tables in order of
       first appearance"                       -> number the value-of-time
                                                table and shift the rest
  6.6  numbered references in order of first
       appearance                             -> (verified separately)

Also replaces the bare \{ \} escapes with \lbrace \rbrace, because CommonMark
eats the backslash and GitHub then renders a stray brace.

Run:  python tools/fix_paper_format.py submit/paper.md
"""
import io
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "submit/paper.md"
src = io.open(path, encoding="utf-8").read()
before = src

# ---------------------------------------------------------------- 1. braces
src = src.replace(r"\{", r"\lbrace").replace(r"\}", r"\rbrace")

# ------------------------------------------- 2. figure captions below images
CAP = re.compile(
    r'::: \{custom-style="Figure Caption"\}\n(.*?)\n:::\n\n(!\[[^\]]*\]\([^\)]*\))\n',
    re.S,
)


def _cap_below(m):
    return m.group(2) + "\n\n::: {custom-style=\"Figure Caption\"}\n" + m.group(1) + "\n:::\n"


src, n_cap = CAP.subn(_cap_below, src)

# --------------------------------------------- 3. table renumbering (desc.)
src = src.replace(
    "Table 5. Planner-implied value against simulated net earnings",
    "Table 6. Planner-implied value against simulated net earnings")
src = src.replace(
    "Table 4. Cyclic (multi-day) results.",
    "Table 5. Cyclic (multi-day) results.")
src = src.replace(
    "Table 3. Ablations A1--A6.",
    "Table 4. Ablations A1--A6.")

# ---------------------------------- 3b. caption for the value-of-time table
VOT_ANCHOR = (
    "| Fare scale | Peak VOT | Mean VOT | Optimal charging slots | Feasible |"
)
VOT_CAP = (
    '::: {custom-style="Table Caption"}\n'
    "Table 3. Robustness of the optimal charging schedule to the implied "
    "value of time. Fares are rescaled so that the peak-hour implied VOT "
    "matches the \$27.54/h measured by Dorsey et al. (2022).\n"
    ":::\n\n"
)
if VOT_CAP not in src:
    src = src.replace(VOT_ANCHOR, VOT_CAP + VOT_ANCHOR, 1)

# ------------------------------- 3c. caption for the appendix parameter table
APP_ANCHOR = "| Symbol | Meaning | Value |\n|---|---|---|\n| $\\Delta t$ | slot duration in hours | 0.25 |"
APP_CAP = (
    '::: {custom-style="Table Caption"}\n'
    "Table 7. Model parameters not listed in Section 2.2.\n"
    ":::\n\n"
)
if APP_CAP not in src:
    src = src.replace(APP_ANCHOR, APP_CAP + APP_ANCHOR, 1)

# ------------------------------------------------ 4. abstract / keywords style
src = src.replace(
    "# Abstract\n\nElectric ride-hailing platforms",
    '::: {custom-style="Abstract"}\n'
    "**Abstract.** Electric ride-hailing platforms",
    1,
)
src = src.replace(
    "\n**Keywords:** electric ride-hailing;",
    "\n:::\n\n::: {custom-style=\"Abstract\"}\n"
    "**Keywords:** electric ride-hailing;",
    1,
)
src = src.replace(
    "value of time\n\n# 1. Introduction",
    "value of time\n:::\n\n# 1. Introduction",
    1,
)

# ------------------------------------------------------- 5. references style
src = re.sub(
    r"(# References\n\n)(?=\[1\])",
    r'\1::: {custom-style="Bibliography"}\n\n',
    src,
)
src = src.replace(
    "\n\n# Appendix",
    "\n\n:::\n\n# Appendix",
    1,
)

io.open(path, "w", encoding="utf-8").write(src)
print("figure captions moved below images:", n_cap)
print("changed:", "yes" if src != before else "no")
