"""Number every table in order of first appearance.

Guide 6.4: "Number figures and tables in order of first appearance: Figure 1,
Figure 2, ...; Table 1, Table 2, ..."

Two tables in section 2.2.3 (the parameter table and the tariff table) had no
caption at all, so they had to be slotted in at the front and every later
table shifted. No prose in the paper refers to a table by number, so the
renumbering is invisible except in the captions and the appendix.

Run:  python tools/renumber_tables.py submit/paper.md
"""
import io
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "submit/paper.md"
src = io.open(path, encoding="utf-8").read()

# ------------------------------------------- 1. shift existing captions (desc.)
shifts = [
    ("Table 7. Model parameters not listed in Section 2.2.",
     "Table 9. Model parameters not listed in Section 2.2."),
    ("Table 6. Planner-implied value against simulated net earnings",
     "Table 8. Planner-implied value against simulated net earnings"),
    ("Table 5. Cyclic (multi-day) results.",
     "Table 7. Cyclic (multi-day) results."),
    ("Table 4. Ablations A1--A6.",
     "Table 6. Ablations A1--A6."),
    ("Table 3. Robustness of the optimal charging schedule",
     "Table 5. Robustness of the optimal charging schedule"),
    ("Table 2. One-factor sensitivity.",
     "Table 4. One-factor sensitivity."),
    ("Table 1. Policy comparison over 600 Monte-Carlo working days.",
     "Table 3. Policy comparison over 600 Monte-Carlo working days."),
]
for old, new in shifts:
    if old not in src:
        raise SystemExit("caption not found: " + old[:50])
    src = src.replace(old, new, 1)

# ------------------------------------- 2. caption the two section 2.2.3 tables
PARAM_ANCHOR = "| Symbol | Meaning | Value | Basis |\n|---|---|---|---|"
PARAM_CAP = ('::: {custom-style="Table Caption"}\n'
             "Table 1. Model parameters, their values and their sources.\n"
             ":::\n\n")
if PARAM_CAP not in src:
    if PARAM_ANCHOR not in src:
        raise SystemExit("parameter table anchor not found")
    src = src.replace(PARAM_ANCHOR, PARAM_CAP + PARAM_ANCHOR, 1)

TOU_ANCHOR = "| Tier | Hours | Price (\\$/kWh) |\n|---|---|---|"
TOU_CAP = ('::: {custom-style="Table Caption"}\n'
           "Table 2. The assumed four-tier time-of-use tariff.\n"
           ":::\n\n")
if TOU_CAP not in src:
    if TOU_ANCHOR not in src:
        raise SystemExit("tariff table anchor not found")
    src = src.replace(TOU_ANCHOR, TOU_CAP + TOU_ANCHOR, 1)

# --------------------------------------- 3. appendix script comments follow on
src = src.replace(
    "python run_experiments.py    # Table 1, Table 2, Figures 1-2",
    "python run_experiments.py    # Tables 3-4, Figures 1-2")
src = src.replace(
    "python ablations.py          # Table 3, Table 4",
    "python ablations.py          # Tables 6-7")
src = src.replace(
    "python vot_rescale.py        # the value-of-time robustness table",
    "python vot_rescale.py        # the value-of-time robustness table (Table 5)")
src = src.replace(
    "python policy_stats.py       # the 600-day charging-slot distribution",
    "python policy_stats.py       # the 600-day charging-slot distribution")

io.open(path, "w", encoding="utf-8").write(src)
print("tables renumbered")
