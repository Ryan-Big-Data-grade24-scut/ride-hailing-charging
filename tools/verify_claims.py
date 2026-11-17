"""Verify that the numbers quoted in the paper still match results/*.csv.

    python tools/verify_claims.py

Every claim is recomputed from the raw experiment outputs and then looked up
in `submit/paper.md`.  If a number in the paper drifts away from the data,
this fails.  Run it before pushing the paper; it is the cheapest possible
defence against a reviewer asking "where does 74.4% come from?".
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
PAPER = os.path.join(ROOT, "submit", "paper.md")
RESULTS = os.path.join(ROOT, "results")


def load(name):
    with open(os.path.join(RESULTS, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def money(x):
    return f"${x:,.2f}"


def main():
    paper = open(PAPER, encoding="utf-8").read()
    # pandoc escapes $ and % inside markdown; unescape for the lookups
    paper = paper.replace(r"\$", "$").replace(r"\%", "%")
    failures = []
    checked = 0

    def check(label, needle):
        """The paper may write a number with or without a currency sign or a
        percent sign (tables carry bare numbers), so try the plausible
        spellings before declaring a mismatch."""
        nonlocal checked
        checked += 1
        variants = {needle,
                    needle.replace("$", ""),
                    needle.replace("%", ""),
                    needle.replace("$", r"\$")}
        if not any(v in paper for v in variants):
            failures.append(f"{label}: paper does not contain {needle!r}")

    # ---- v2 core comparison -------------------------------------------
    comp = load("policy_comparison.csv")
    by = {r["policy"]: r for r in comp}
    mdp = next(r for r in comp if r["policy"].startswith("MDP"))
    check("MDP net", money(float(mdp["net"])))
    check("MDP feasibility", f"{float(mdp['feasible_rate'])*100:.1f}%")

    rule = next(r for r in comp if "cheapest hour" in r["policy"])
    check("cheapest-hour net", money(float(rule["net"])))
    check("cheapest-hour feasibility",
          f"{float(rule['feasible_rate'])*100:.0f}%")

    ab = {r["ablation"]: r for r in load("ablations.csv")}
    check("baseline gain", money(float(ab["BASELINE"]["gain_vs_tariff_rule"])))
    check("A4 no-cap net",
          money(float(ab["A4 no driver time cap"]["mdp_net"])))
    check("A5 clamp book value",
          money(float(ab["A5 clamped reserve"]["mdp_net"])))

    # ---- v3 excursion -------------------------------------------------
    pol = [r for r in load("v3_policy_comparison.csv")
           if r["calibration"] == "v2-2024"]
    opt = next(r for r in pol if r["policy"].startswith("Optimiser"))
    check("excursion optimiser net", money(float(opt["net"])))
    check("excursion feasibility",
          f"{float(opt['feasible_rate'])*100:.1f}%")
    rules = [r for r in pol if r["policy"].startswith("Rule")]
    best_rule = max(rules, key=lambda r: float(r["net"]))
    check("best rule net", money(float(best_rule["net"])))
    gain = float(opt["net"]) - float(best_rule["net"])
    check("excursion gain", money(gain))

    # ---- queue sweep --------------------------------------------------
    q = [r for r in load("v3_queue_sweep.csv")
         if r["calibration"] == "v2-2024"]
    at2 = [r for r in q if float(r["queue_peak_h"]) == 2.0]
    at0 = float(next(r for r in q if float(r["queue_peak_h"]) == 0)["net"])
    loss_lo = at0 - max(float(r["net"]) for r in at2)
    loss_hi = at0 - min(float(r["net"]) for r in at2)
    check("queue loss low", f"${loss_lo:.0f}")
    check("queue loss high", f"${loss_hi:.0f}")
    feas0 = float(next(r for r in q if float(r["queue_peak_h"]) == 0)
                  ["feasible_rate"])
    feas2 = float(next(r for r in q if r["shape"] == "uniform"
                       and float(r["queue_peak_h"]) == 2.0)["feasible_rate"])
    check("queue feasibility start", f"{feas0*100:.1f}%")
    check("queue feasibility end", f"{feas2*100:.1f}%")

    # ---- budget ratio (E6) --------------------------------------------
    sweep = [r for r in load("v3_master_sweep.csv")
             if r["calibration"] == "v2-2024"]
    for row in sweep:
        ratio = float(row["budget_ratio"])
        if abs(ratio - 1.6018) < 2e-3:      # the headline row
            check("budget ratio row net", money(float(row["net"])))
            check("budget ratio gain",
                  money(float(row["gain_over_best_rule"])))
            check("budget ratio pct", f"{float(row['gain_pct']):.1f}%")
        if abs(ratio - 0.7538) < 2e-3:
            check("budget ratio low net", money(float(row["net"])))
            check("budget ratio low pct", f"{float(row['gain_pct']):.1f}%")

    # ---- off-peak share (policy_stats) --------------------------------
    days = [r for r in load("charge_day_stats.csv") if r["feasible"] == "True"]
    share = sum(int(r["n_off_valley"]) > 0 for r in days) / len(days)
    check("off-valley share", f"{share*100:.1f}%")
    valley_only = sum(int(r["n_off_valley"]) == 0 for r in days) / len(days)
    check("valley-only share", f"{valley_only*100:.1f}%")

    if failures:
        print(f"FAIL — {len(failures)} of {checked} claims disagree "
              f"between the paper and results/*.csv:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"PASS — all {checked} checked claims match results/*.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
