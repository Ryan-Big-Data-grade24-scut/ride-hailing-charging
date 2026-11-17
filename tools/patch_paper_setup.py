"""
Fold the "design choices" audit into the paper.

This patch does four things, all of them about making the setup defensible:

  1. renumbers the display equations (a new equation is inserted at 2.1.3),
  2. rewrites the electricity-cost part of 2.1.3 so that the pricing regime
     is an explicit, switchable modelling choice rather than something buried
     in the code, and rewrites 2.1.4 to use the regime-independent cost
     function,
  3. rewrites 2.2.3 with an updated Table 1 (every parameter now says whether
     it is measured, derived or swept) and a new Table 2 that lists every
     design choice, its justification, what the model does not capture, and
     the experiment in which it is tested,
  4. renumbers the tables after the inserted Table 2.

Run:  python tools/patch_paper_setup.py submit/paper.md
"""
import io
import re
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "submit/paper.md"
src = io.open(PATH, encoding="utf-8").read()


def sub(old, new, count=1):
    global src
    if src.count(old) != count:
        raise SystemExit("anchor not found (%d hits): %s"
                         % (src.count(old), old[:70]))
    src = src.replace(old, new, count)


# =====================================================================
# 1. equation renumbering: every display equation from (7) onwards shifts up
# =====================================================================
EQ = re.compile(r"^(\$\$.*\\qquad\\qquad \()(\d+)(\)\$\$)$", re.M)


def bump(m):
    n = int(m.group(2))
    return m.group(1) + str(n + 1 if n >= 7 else n) + m.group(3)


src = EQ.sub(bump, src)

# =====================================================================
# 2. 2.1.3 -- the pricing regime becomes an explicit modelling choice
# =====================================================================
OLD_COST = (
    "Under the tariff, a driver pays for the charger slot at the charger's "
    "rated power, so the electricity cost of charging in slot $t$ is "
    "$\\text{price}(t) \\times P \\times \\Delta t$ regardless of how much "
    "energy the taper allows into the pack. The consequence is that the "
    "*marginal* cost of the next kWh is\n"
    "\n"
    "$$c_{\\textsf{marg}}(s) = \\frac{\\text{price}(t)}{\\eta\\,\\tau(s)}, "
    "\\qquad\\qquad (8)$$\n"
    "\n"
    "which is \\$0.21/kWh while $s \\le 0.80$ and rises to \\$1.38/kWh at "
    "$s = 1.00$ under the shoulder tariff --- a factor of 6.6. We note in "
    "Section 3.3 that at the resolution of our time grid this structure is in "
    "fact not resolvable, and we treat that as a finding rather than "
    "concealing it."
)

NEW_COST = (
    "What the driver pays for a charging slot depends on the **pricing "
    "regime** at the station, and the two regimes in use at Chinese public DC "
    "charging points are not interchangeable:\n"
    "\n"
    "* **Occupancy (slot) billing**, i.e. a time-based fee for occupying the "
    "charger. The driver pays for the charger slot at the charger's rated "
    "power, whether or not the taper lets that energy into the pack.\n"
    "* **Energy billing**, i.e. a fee per kWh drawn from the grid. The driver "
    "pays for the electricity actually drawn, which is the energy the pack "
    "accepts divided by the charging efficiency.\n"
    "\n"
    "The cost of one charging slot started at state of charge $s$ is "
    "therefore\n"
    "\n"
    "$$\\textsf{cost}(t,s) = \\begin{cases} \\text{price}(t)\\,P\\,\\Delta t & "
    "\\textsf{occupancy billing (base case)} \\\\[4pt] \\text{price}(t)\\,"
    "\\min\\!\\left(P\\,\\tau(s)\\,\\Delta t,\\; "
    "\\dfrac{(1-s)\\,Q}{\\eta}\\right) & \\textsf{energy billing} \\end{cases} "
    "\\,,\\qquad\\qquad (7)$$\n"
    "\n"
    "The base case is occupancy billing, but we state the choice explicitly and "
    "test the alternative rather than burying it, because the two regimes imply "
    "different *marginal* costs. Under occupancy billing the marginal cost of "
    "the next kWh is\n"
    "\n"
    "$$c_{\\textsf{marg}}(s) = \\frac{\\text{price}(t)}{\\eta\\,\\tau(s)}, "
    "\\qquad\\qquad (8)$$\n"
    "\n"
    "which is \\$0.21/kWh while $s \\le 0.80$ and rises to \\$1.38/kWh at "
    "$s = 1.00$ under the shoulder tariff --- a factor of 6.6. Under energy "
    "billing the taper cancels from the ratio and the marginal cost is "
    "**flat** at $\\text{price}(t)/\\eta$ at every state of charge: the steep "
    "curve is a property of the pricing regime, not of the battery. Section "
    "3.3 reports ablation A7, in which the entire model is re-solved under the "
    "energy-billing regime; neither the optimal charging schedule nor the "
    "advantage over the baselines changes. We therefore state the marginal-cost "
    "structure as a conditional claim. We note in addition that at the "
    "resolution of our time grid the taper is in any case not resolvable "
    "(Section 3.3, ablation A3), which we treat as a finding rather than "
    "concealing it."
)
sub(OLD_COST, NEW_COST)

# ---- 2.1.4 objective: use the regime-independent cost function -----------
sub(
    "$$\\max_{\\pi}\\ \\mathbb{E}\\left[\\sum_{t=0}^{T-1}\\left("
    "\\underbrace{m_t\\,f_t}_{\\textsf{fare revenue}} - "
    "\\underbrace{\\textsf{price}(t)\\,P\\,\\Delta t \\cdot "
    "\\mathbb{1}\\lbrace a_t = \\textsf{CHARGE}\\rbrace}_{\\textsf{electricity "
    "cost}}\\right)\\right], \\qquad\\qquad (9)$$",
    "$$\\max_{\\pi}\\ \\mathbb{E}\\left[\\sum_{t=0}^{T-1}\\left("
    "\\underbrace{m_t\\,f_t}_{\\textsf{fare revenue}} - "
    "\\underbrace{\\textsf{cost}(t,s_t) \\cdot \\mathbb{1}\\lbrace a_t = "
    "\\textsf{CHARGE}\\rbrace}_{\\textsf{electricity cost}}\\right)\\right], "
    "\\qquad\\qquad (9)$$",
)
sub("subject to (1)--(6) and $s_t \\ge s^{\\min}$ for all $t$.",
    "subject to (1)--(6) and $s_t \\ge s^{\\min}$ for all $t$, with "
    "$\\textsf{cost}(\\cdot,\\cdot)$ given by (7).")

# =====================================================================
# 3. 2.2.3 -- updated Table 1, new Table 2, tariff provenance
# =====================================================================
OLD_PARAMS = (
    "| $Q$ | usable pack capacity | 40 kWh | BYD e6 / Nissan Leaf class |\n"
    "| $s^{\\min}$ | reserve floor | 15% | industry practice |\n"
    "| $P$ | charger rated power | 60 kW | DC fast charging |\n"
    "| $\\eta$ | charging efficiency | 92% | --- |\n"
    "| $s^{\\textsf{CC}}$ | CC-to-CV knee | 80% | typical lithium-ion "
    "behaviour |\n"
    "| $\\textsf{CAP}$ | driver time cap | 1.01 trips / 15 min | implied by "
    "14.8 min mean trip duration |\n"
    "| $\\Delta t$ | slot length | 15 min | aligned with the demand profile |\n"
    "| $u_{\\textsf{peak}}$ | peak-hour utilisation | 85% | calibration "
    "assumption, swept in 40%--100% |\n"
    "| $s_0$ | start-of-day state of charge | 80% | full battery; relaxed in "
    "the cyclic extension |\n"
)

NEW_PARAMS = (
    "| $Q$ | usable pack capacity | 40 kWh | BYD e6 / Nissan Leaf class; "
    "swept 25--80 kWh (S1) |\n"
    "| $s^{\\min}$ | reserve floor | 15% | assumption; swept 5%--25% (S9) |\n"
    "| $P$ | charger rated power | 60 kW | DC fast charging; swept "
    "7--200 kW (S3) |\n"
    "| $\\eta$ | charging efficiency | 92% | assumption; swept 85%--98% (S8) |\n"
    "| $s^{\\textsf{CC}}$ | CC-to-CV knee | 80% | typical lithium-ion "
    "behaviour |\n"
    "| $\\textsf{CAP}$ | driver time cap | 1.01 trips / 15 min | implied by "
    "14.8 min mean trip duration |\n"
    "| $\\Delta t$ | slot length | 15 min | aligned with the demand profile |\n"
    "| $u_{\\textsf{peak}}$ | peak-hour utilisation | 85% | calibration "
    "assumption; swept 40%--100% (S4) |\n"
    "| $s_0$ | start-of-day state of charge | 80% | full battery; swept "
    "30%--95% (S7) |\n"
    "| $\\textsf{bill}$ | charging pricing regime | occupancy (slot) billing "
    "| both regimes standard at Chinese DC chargers; energy billing re-solved "
    "in A7 |\n"
)
sub(OLD_PARAMS, NEW_PARAMS)

# ---- new Table 2 -------------------------------------------------------
DESIGN_TABLE = (
    "A reader is entitled to ask which of these numbers are measurements and "
    "which are our own invention. Table 2 answers that question for every "
    "modelling choice in the paper, including the ones that are not "
    "parameters: for each choice it states what we assume, where the "
    "assumption comes from, what we deliberately do **not** model, and the "
    "experiment in which it is tested. A choice that is swept is not an "
    "unsupported assumption; it is an assumption whose conclusion has been "
    "shown not to depend on it, except where we say otherwise.\n"
    "\n"
    "::: {custom-style=\"Table Caption\"}\n"
    "Table 2. Design choices, their justification and where each is tested. "
    "\"Not modelled\" states the real-world effect the model omits, so that "
    "the boundary of the model is declared rather than implied.\n"
    ":::\n"
    "\n"
    "| Design choice | What we assume | Why (source) | What we do not model | "
    "Tested in |\n"
    "|---|---|---|---|---|\n"
    "| Decision unit | One driver, one working day, then a cyclic multi-day "
    "version | The fleet-scale literature optimises infrastructure and "
    "assignment [3,4,6]; we shrink the scale until the decision and the "
    "physics are exactly legible | Fleet interaction, station queues, driver "
    "heterogeneity | Sec. 3.4 |\n"
    "| Charging pricing regime | Occupancy (slot) billing: the driver pays "
    "for the charger slot at rated power | Occupancy/time fees and per-energy "
    "fees are both standard at Chinese public DC charging stations | Who owns "
    "the charger; contract tariffs | Sec. 3.3, A7 |\n"
    "| Tariff shape | Four tiers; super-peak-to-valley ratio 3.8:1 | Tier "
    "structure and a peak-to-valley ratio of at least 3:1 (4:1 in "
    "high-spread provinces) follow the national mechanism [13]; the provincial "
    "schedule uses a peak:flat:valley ratio of 1.7:1:0.38 [14] | The "
    "provincial schedule's exact hours | Sec. 3.2, S6 |\n"
    "| Pack capacity $Q$ | 40 kWh usable | BYD e6 / Nissan Leaf class | Cell "
    "ageing, thermal management | Sec. 3.2, S1 |\n"
    "| Charging efficiency $\\eta$ | 92% | Typical DC charger efficiency | "
    "Charger-specific power curves | Sec. 3.2, S8 |\n"
    "| CC--CV knee $s^{\\textsf{CC}}$ | 80% | Typical lithium-ion behaviour "
    "| Cell chemistry | Sec. 3.3, A3 |\n"
    "| Reserve floor $s^{\\min}$ | 15% | Industry practice | Range anxiety, "
    "roadside assistance | Sec. 3.2, S9 |\n"
    "| Driver time cap $\\textsf{CAP}$ | 1.01 trips per 15 min | Implied by "
    "the 14.8-minute mean trip duration | Cruising, deadheading, waiting | "
    "Sec. 3.3, A4 |\n"
    "| Peak-hour utilisation $u_{\\textsf{peak}}$ | 85% | Calibration "
    "assumption that fixes the fleet size | Fleet entry and exit | Sec. 3.2, "
    "S4 |\n"
    "| Opportunity cost | The gross fare the slot would have earned, with no "
    "commission deducted | Deliberately conservative: it overstates the cost "
    "of charging | Platform commission, cruising, waiting | Sec. 3.2, "
    "value-of-time table |\n"
    "\n"
)

sub("The time-of-use tariff is a **four-tier assumption**, not a measurement, "
    "and is swept in the sensitivity analysis:",
    DESIGN_TABLE +
    "The time-of-use tariff is a **four-tier assumption**, not a measurement, "
    "and is swept in the sensitivity analysis:")

# ---- tariff provenance note --------------------------------------------
TARIFF_NOTE = (
    "The **tier structure** and the **peak-to-valley ratio** of this tariff "
    "follow the Chinese time-of-use mechanism rather than being invented. The "
    "national notice requires a peak-to-valley price ratio of not less than "
    "3:1, and 4:1 in provinces whose system peak-to-valley difference rate "
    "exceeds 40%, with the super-peak tier set at not less than 20% above the "
    "peak tier [13]; the Guangdong provincial schedule implements a "
    "peak:flat:valley ratio of 1.7:1:0.38, i.e. 4.5:1, with the super-peak "
    "tier 25% above the peak tier [14]. Our stylised tariff is deliberately "
    "**flatter than any compliant schedule**: its super-peak-to-valley ratio "
    "is 3.8:1 and its peak-to-valley ratio 2.5:1, below the 3:1 floor. We "
    "keep our own hours because they are aligned to the demand profile that "
    "drives the decision, and we cover the compliant range by sweeping the "
    "spread: at a spread multiplier of 1.5 the peak-to-valley ratio reaches "
    "3.3:1, and at 2.0 it reaches 4.1:1. Across that whole sweep the gain of "
    "optimisation changes by 1.3% (Section 3.2, S6). The tariff therefore "
    "cannot be the reason for the result.\n"
    "\n"
)
sub("| off-peak | 00:00--10:00, 23:00--24:00 | 0.11 |\n",
    "| off-peak | 00:00--10:00, 23:00--24:00 | 0.11 |\n" + TARIFF_NOTE)

# ---- wrong cross-reference in 2.2.4 ------------------------------------
sub("then re-solve. Section 3.4 reports the outcome:",
    "then re-solve. Section 3.2 reports the outcome:")

# =====================================================================
# 4. table renumbering (the new Table 2 pushes the rest along)
# =====================================================================
CAPTION_SHIFTS = [
    ("Table 9. Model parameters not listed in Section 2.2.",
     "Table 10. Model parameters not listed in Section 2.2."),
    ("Table 8. Planner-implied value against simulated net earnings",
     "Table 9. Planner-implied value against simulated net earnings"),
    ("Table 7. Cyclic (multi-day) results.",
     "Table 8. Cyclic (multi-day) results."),
    ("Table 6. Ablations A1--A6.",
     "Table 7. Ablations A1--A7."),
    ("Table 5. Robustness of the optimal charging schedule",
     "Table 6. Robustness of the optimal charging schedule"),
    ("Table 4. One-factor sensitivity.",
     "Table 5. One-factor sensitivity."),
    ("Table 3. Policy comparison over 600 Monte-Carlo working days.",
     "Table 4. Policy comparison over 600 Monte-Carlo working days."),
    ("Table 2. The assumed four-tier time-of-use tariff.",
     "Table 3. The assumed four-tier time-of-use tariff."),
]
for old, new in CAPTION_SHIFTS:
    sub(old, new)

io.open(PATH, "w", encoding="utf-8").write(src)
print("patched " + PATH)
