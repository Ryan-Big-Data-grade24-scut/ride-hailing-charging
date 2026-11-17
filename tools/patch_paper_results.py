"""
Fold the re-run sensitivity results, the billing-regime ablation and the two
policy references into the paper.

Every number written here is the one produced by
code/src/run_experiments.py and code/src/ablations.py at 600 Monte-Carlo days
per point (results/sensitivity.csv, results/ablations.csv).

Run:  python tools/patch_paper_results.py submit/paper.md
"""
import io
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "submit/paper.md"
src = io.open(PATH, encoding="utf-8").read()


def sub(old, new, count=1):
    global src
    if src.count(old) != count:
        raise SystemExit("anchor not found (%d hits): %s"
                         % (src.count(old), old[:80]))
    src = src.replace(old, new, count)


# =====================================================================
# abstract
# =====================================================================
sub("Second, the time-of-use price spread is nearly irrelevant: widening the "
    "peak-to-valley spread from 0x to 2x changes the gain over a "
    "tariff-following rule by only 1.3%, so opportunity cost, not price, "
    "drives the decision.",
    "Second, the time-of-use price spread is nearly irrelevant: widening the "
    "peak-to-valley spread from 0x to 2x changes the gain over a "
    "tariff-following rule by only 0.5%, so opportunity cost, not price, "
    "drives the decision, and the conclusion is unchanged when the charging "
    "is billed per kWh instead of per charger slot.")

# =====================================================================
# contribution 3 and 4
# =====================================================================
sub("3. **A robust counter-intuitive result.** The optimal charging schedule "
    "lies outside the cheapest tariff window on 74.4% of simulated working "
    "days, and the conclusion survives a 3.4-fold rescaling of the implied "
    "value of time to the range measured in the literature.",
    "3. **A robust counter-intuitive result.** The optimal charging schedule "
    "lies outside the cheapest tariff window on 74.4% of simulated working "
    "days, and the conclusion survives a 3.4-fold rescaling of the implied "
    "value of time to the range measured in the literature, a switch of the "
    "charging pricing regime from occupancy billing to per-energy billing, "
    "and a 5%--25% range of the reserve floor.")

sub("4. **A negative result with direct managerial implications.** Widening "
    "the TOU spread from flat to twice the base spread changes the value of "
    "optimisation by only 1.3%.",
    "4. **A negative result with direct managerial implications.** Widening "
    "the TOU spread from flat to twice the base spread changes the value of "
    "optimisation by only 0.5%.")

# =====================================================================
# 2.2.3 tariff note: the spread sweep is now 0.5%
# =====================================================================
sub("Across that whole sweep the gain of optimisation changes by 1.3% "
    "(Section 3.2, S6).",
    "Across that whole sweep the gain of optimisation changes by 0.5% "
    "(Section 3.2, S6).")

# =====================================================================
# 3.2 -- ten sweeps instead of seven
# =====================================================================
sub("Seven one-at-a-time sweeps hold all other parameters at their base "
    "values. The quantity reported is the gain of the MDP over the "
    "tariff-following rule, re-solved for each parameter value.",
    "Ten one-at-a-time sweeps hold all other parameters at their base "
    "values. The quantity reported is the gain of the MDP over the "
    "tariff-following rule, re-solved for each parameter value. Every sweep "
    "point is evaluated with the same simulation budget and the same random "
    "seed as the main comparison, so the base row of each sweep reproduces "
    "Table 4 exactly and the two tables can be read against each other. The "
    "sweep identifiers below are the `parameter` column of "
    "`results/sensitivity.csv`.")

OLD_ROWS = (
    "| S1 | Pack capacity | 25 → 80 kWh | +453.58 → +15.97 | **Strongest "
    "driver**: a bigger pack trivialises the problem |\n"
    "| S2 | Energy consumption | 0.18 → 0.45 kWh/km | +46.21 → +532.06 | "
    "Tighter energy budget, more value in scheduling |\n"
    "| S3 | Charger power | 7 → 200 kW | +263.72 → +158.87 | Slower chargers "
    "make scheduling *more* valuable |\n"
    "| S4 | Peak utilisation | 40% → 100% | -0.71 → +284.56 | Busier market, "
    "stronger opportunity cost |\n"
    "| S5 | Fare level | x0.7 → x1.5 | +117.89 → +255.27 | Higher fares "
    "raise the opportunity cost |\n"
    "| S6 | TOU price spread | x0 (flat) → x2 | +168.46 → +170.72 | "
    "**Counter-intuitive: almost no effect** |\n"
    "| S7 | Start-of-day SOC | 30% → 95% | +497.45 → +164.15 | Emptier "
    "start, more careful schedule |\n"
)
NEW_ROWS = (
    "| S1 | Pack capacity | 25 → 80 kWh | +447.46 → +6.92 | **Strongest "
    "driver**: a bigger pack trivialises the problem |\n"
    "| S2 | Energy consumption | 0.18 → 0.45 kWh/km | +41.79 → +528.09 | "
    "Tighter energy budget, more value in scheduling |\n"
    "| S3 | Charger power | 7 → 200 kW | +262.30 → +157.83 | Slower chargers "
    "make scheduling *more* valuable |\n"
    "| S4 | Peak utilisation | 40% → 100% | +2.77 → +266.57 | Busier market, "
    "stronger opportunity cost |\n"
    "| S5 | Fare level | x0.7 → x1.5 | +110.34 → +238.55 | Higher fares "
    "raise the opportunity cost |\n"
    "| S6 | TOU price spread | x0 (flat) → x2 | +158.80 → +159.61 | "
    "**Counter-intuitive: almost no effect** |\n"
    "| S7 | Start-of-day SOC | 30% → 95% | +491.56 → +162.12 | Emptier "
    "start, more careful schedule |\n"
    "| S8 | Charging efficiency | 85% → 98% | +155.25 → +157.96 | **No "
    "effect**: the conclusion does not rest on $\\eta$ |\n"
    "| S9 | Reserve floor | 5% → 25% | +88.51 → +241.92 | The *size* of the "
    "gain depends on the floor; the *sign* never does |\n"
    "| S10 | Charging pricing regime | occupancy → energy | +158.25 → "
    "+159.05 | **No effect**: schedule and gap are invariant |\n"
)
sub(OLD_ROWS, NEW_ROWS)

sub("Figure 3. The seven one-factor sensitivity sweeps.",
    "Figure 3. The ten one-factor sensitivity sweeps. Each panel varies one "
    "parameter over the stated range and reports the gain of the MDP over "
    "the tariff-following rule; the broken horizontal line is zero gain.")

# =====================================================================
# 3.2 -- the spread paragraph, and the new subsection on unsourced assumptions
# =====================================================================
sub("Widening the peak-to-valley spread from flat to twice the base spread "
    "changes the gain of optimisation by 1.3% (\\$168.46 to \\$170.72), and "
    "the optimal charging slots are **identical** at both extremes (Section "
    "3.3, ablation A2). The two effects cancel almost exactly: a wider spread "
    "makes the tariff-following rule look smarter, but it simultaneously "
    "makes running during the expensive hours more costly, so both the "
    "optimiser and the rule it beats improve by about the same amount.",
    "Widening the peak-to-valley spread from flat to twice the base spread "
    "changes the gain of optimisation by 0.5% (\\$158.80 to \\$159.61), and "
    "the optimal charging slots are **identical** at both extremes (Section "
    "3.3, ablation A2). The raw numbers show why, and the reason is simpler "
    "than an offsetting pair of effects: the tariff-following rule buys "
    "exactly one valley slot, and the valley price is the reference against "
    "which the spread is measured, so its earnings are literally constant at "
    "\\$788.21 across the whole sweep. The optimiser's own net earnings also "
    "barely move, from \\$947.01 to \\$947.82, because it does almost all of "
    "its charging in the valley and the valley price does not change. Neither "
    "side of the comparison is made much better by a steeper tariff.")

NEW_SUBSECTION = (
    "### The three assumptions we cannot source\n"
    "\n"
    "Three quantities in the model are not measurements and cannot be traced "
    "to a published source: the charging efficiency $\\eta$, the reserve floor "
    "$s^{\\min}$ and the charging pricing regime. We therefore treat each as "
    "a swept assumption rather than as a constant, and we report the outcome "
    "even where it is unflattering.\n"
    "\n"
    "**The charging efficiency does not matter (S8).** Across an 85--98% "
    "range the MDP's net earnings move between \\$943.45 and \\$948.11, a "
    "spread of \\$4.66 or 0.5%, the gain over the tariff-following rule moves "
    "between \\$155.25 and \\$159.90, and the number of charging slots does "
    "not change at all. This follows directly from the pricing regime: a "
    "driver who pays for the charger slot rather than for the energy bought "
    "is charged the same whether the pack is 40% or 80% full, so $\\eta$ "
    "enters only through how much energy a single slot delivers, and the pack "
    "saturates within a slot in any case (Section 3.3, A3).\n"
    "\n"
    "**The reserve floor changes the size of the prize but not its sign "
    "(S9).** The MDP's own net earnings are nearly flat across a 5--25% "
    "floor, from \\$951.75 down to \\$938.95, a spread of 1.4%, but the gain "
    "over the tariff-following rule ranges from \\$88.51 to \\$241.92, "
    "because a tighter floor makes the myopic rule strand more often: its "
    "feasible share falls from 26% to 2%. We report this as the one genuinely "
    "load-bearing free parameter in the paper. **The value of scheduling a "
    "ride-hailing driver's charging grows with how tight the driver's range "
    "anxiety is**, and correspondingly a driver willing to run the pack down "
    "to 5% has far less to gain from an optimiser than one who insists on "
    "keeping 25% in reserve. The qualitative conclusion --- that the "
    "optimiser dominates every simple rule at every floor level tested --- is "
    "unchanged.\n"
    "\n"
    "**The pricing regime does not matter (S10).** Re-solving the entire "
    "model under energy billing instead of occupancy billing changes the "
    "MDP's net earnings by \\$1.49 and the gain by \\$0.80, and leaves the "
    "charging slots untouched. What the regime does change is the "
    "*interpretation* of Figure 4: under occupancy billing the marginal cost "
    "of the next kWh rises six-fold as the pack fills, and under energy "
    "billing the taper cancels out of the ratio and the rate is flat (Section "
    "3.3, A7). We therefore report the steep marginal-cost curve as a "
    "property of the pricing regime and not as a property of the battery.\n"
    "\n"
)
sub("## 3.3 Ablation analysis", NEW_SUBSECTION + "## 3.3 Ablation analysis")

# =====================================================================
# 3.3 -- the A7 row and its discussion
# =====================================================================
sub("| **A6** | Intra-day demand shape | \\$1,009.28; slots 02:30, 07:45, "
    "08:45, **all in the valley** | When opportunity cost is constant, **the "
    "tariff decides again** |\n",
    "| **A6** | Intra-day demand shape | \\$1,009.28; slots 02:30, 07:45, "
    "08:45, **all in the valley** | When opportunity cost is constant, **the "
    "tariff decides again** |\n"
    "| **A7** | Occupancy (slot) pricing | \\$947.95 under energy billing; "
    "gain +158.25 → **+159.05**; slots **identical** | The pricing regime is "
    "**not load-bearing**; only the marginal-cost *illustration* is |\n")

A7_TEXT = (
    "**A7 is the ablation that turns our weakest modelling choice into a "
    "reported result.** The pricing regime is the one assumption in the model "
    "that is neither measured nor uniform across operators: a driver may pay "
    "for the charger slot at rated power or for the electricity actually "
    "drawn, and the two imply different marginal costs (Section 2.1.3). "
    "Re-solving the entire model under the alternative regime changes the net "
    "earnings by \\$1.49 out of \\$946.46, i.e. 0.16%, the gain over the "
    "tariff-following rule by \\$0.80, the feasible share by one percentage "
    "point, and **not the charging schedule at all** --- 04:45, 11:15 and "
    "20:30 under both. What does change is the interpretation of Figure 4: "
    "under occupancy billing the marginal cost of the next kWh rises from "
    "\\$0.21 to \\$1.38 as the pack approaches full; under energy billing it "
    "is flat at \\$0.21 at every state of charge, because the taper cancels "
    "from the ratio. The steep curve is therefore a property of the tariff, "
    "not of the battery. We report this because a reader who disagrees with "
    "our choice of regime can now read off exactly what changes --- and what "
    "changes is the cost structure, not the schedule.\n"
    "\n"
)
sub("**A4 shows that the driver time cap is the pivot of the model.**",
    A7_TEXT + "**A4 shows that the driver time cap is the pivot of the "
              "model.**")

# =====================================================================
# 4 -- conclusion
# =====================================================================
sub("First, widening the peak-to-valley spread by a factor of two changes the "
    "value of optimisation by 1.3%,",
    "First, widening the peak-to-valley spread by a factor of two changes the "
    "value of optimisation by 0.5%,")

# =====================================================================
# references -- the two policy documents
# =====================================================================
sub("[12] Sunada, and Xia (2026). *From pumps to plugs: Value of time and "
    "charging policies* (SSRN Working Paper 6296418). Social Science Research "
    "Network. https://doi.org/10.2139/ssrn.6296418\n",
    "[12] Sunada, and Xia (2026). *From pumps to plugs: Value of time and "
    "charging policies* (SSRN Working Paper 6296418). Social Science Research "
    "Network. https://doi.org/10.2139/ssrn.6296418\n"
    "\n"
    "[13] National Development and Reform Commission (2021). *Notice on "
    "further improving the time-of-use pricing mechanism* "
    "(发改价格〔2021〕1093号). "
    "https://www.ndrc.gov.cn/xxgk/zcfb/tz/202107/t20210729_1292067.html\n"
    "\n"
    "[14] Guangdong Provincial Development and Reform Commission (2021). "
    "*Notice on further improving the peak and valley time-of-use electricity "
    "pricing policy of Guangdong Province* (粤发改价格〔2021〕331号). "
    "https://drc.gd.gov.cn/ywtz/content/post_3500421.html\n")

io.open(PATH, "w", encoding="utf-8").write(src)
print("patched " + PATH)
