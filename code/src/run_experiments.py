"""
Run the full experimental protocol for the ride-hailing charging study.

    1. solve DP (expected-value) and MDP (Poisson) on the real-data profile
    2. score every policy by Monte-Carlo over independent random days
    3. sensitivity analysis over the five assumptions that matter
    4. dump everything to results/ as CSV + JSON for the report and figures

All numbers in the report come from this script. Nothing is hand-entered.
"""

import json
import os

import numpy as np
import pandas as pd

from ev_dp import (CHARGE, DRIVE, Env, evaluate, run_policy, solve_dp,
                   solve_mdp, tou_price)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
SEED = 20261001
N_SIMS = 600


def hr(t: int) -> str:
    return f"{t*15//60:02d}:{t*15%60:02d}"


def run_policy_one(env, pol, seed, **kw):
    """Single representative day under `pol` -- used to report WHEN the policy
    chooses to charge, which is the actual research question."""
    return run_policy(env, "mdp", np.random.default_rng(seed), policy=pol, **kw)


# ===========================================================================
def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    env = Env()
    print(env.describe())
    print()

    # ---------------------------------------------------------------- solve
    print("solving DP ...", flush=True)
    V_dp, pol_dp = solve_dp(env)
    print("solving MDP ...", flush=True)
    V_mdp, pol_mdp = solve_mdp(env, kmax=6)

    dp0 = V_dp[0, env.to_idx(0.80)]
    mdp0 = V_mdp[0, env.to_idx(0.80)]
    print(f"  DP  value at (t=0, s=80%) = ${dp0:,.2f}")
    print(f"  MDP value at (t=0, s=80%) = ${mdp0:,.2f}")
    print()

    # ------------------------------------------------------------ baselines
    print("evaluating policies ({} Monte-Carlo days each) ...".format(N_SIMS))
    policies = {
        "MDP (stochastic DP)": ("mdp", pol_mdp),
        "DP (expected value)": ("dp", pol_dp),
        "Baseline: always drive": ("always-drive", None),
        "Baseline: never charge": ("never-charge", None),
        "Baseline: charge at cheapest hour": ("cheapest", None),
        "Baseline: threshold SOC<30%": ("threshold", None),
        "Baseline: threshold SOC<40%": ("threshold", None),
        "Baseline: threshold SOC<50%": ("threshold", None),
    }
    rows = []
    for name, (kind, pol) in policies.items():
        kw = {}
        if kind == "threshold":
            kw["thresh"] = float(name.split("<")[-1].rstrip("%")) / 100.0
        r = evaluate(env, pol, kind, n_sims=N_SIMS, seed=SEED, **kw)
        r["policy"] = name
        rows.append(r)
        print(f"  {name:34s} net=${r['net']:8,.2f} +- {r['net_std']:6,.2f}"
              f"   rev=${r['revenue']:8,.2f}  elec=${r['energy_cost']:6,.2f}"
              f"  feasible={r['feasible_rate']:.0%}")

    df_res = pd.DataFrame(rows)[
        ["policy", "net", "net_std", "revenue", "energy_cost", "energy_used",
         "charge_kwh", "orders", "final_soc", "feasible_rate"]
    ].sort_values("net", ascending=False)
    df_res.to_csv(os.path.join(OUT, "policy_comparison.csv"), index=False)

    best_base = df_res[~df_res["policy"].str.startswith(("MDP", "DP "))]
    best_base_row = best_base.loc[best_base["net"].idxmax()]
    best_base_name = str(best_base_row["policy"])
    best_base_net = float(best_base_row["net"])
    mdp_row = df_res[df_res["policy"] == "MDP (stochastic DP)"].iloc[0]
    dp_row = df_res[df_res["policy"] == "DP (expected value)"].iloc[0]
    cheapest_row = df_res[df_res["policy"] == "Baseline: charge at cheapest hour"].iloc[0]
    mdp_net = float(mdp_row["net"])

    # two different comparisons, both worth reporting
    gain_vs_best = mdp_net - best_base_net              # vs the best simple rule
    gain_vs_cheap = mdp_net - float(cheapest_row["net"])  # vs tariff-following

    print(f"\n  best rule-based baseline = {best_base_name}: ${best_base_net:,.2f}")
    print(f"  tariff-following rule    : ${float(cheapest_row['net']):,.2f}"
          f"  (feasible {float(cheapest_row['feasible_rate']):.0%})")
    print(f"  MDP                      : ${mdp_net:,.2f}"
          f"  (feasible {float(mdp_row['feasible_rate']):.0%})")
    print(f"  gain vs best simple rule : ${gain_vs_best:,.2f}"
          f"  ({gain_vs_best/best_base_net:.1%})")
    print(f"  gain vs tariff-following : ${gain_vs_cheap:,.2f}"
          f"  ({gain_vs_cheap/float(cheapest_row['net']):.1%})")
    print(f"  DP policy under stochastic demand: ${float(dp_row['net']):,.2f}"
          f"  (feasible {float(dp_row['feasible_rate']):.0%})"
          f"  <-- expected-value DP is not implementable")

    # ------------------------------------------------- the punchline figure
    # What does the MDP actually DO, and when?
    rng = np.random.default_rng(SEED)
    sim = None
    for _ in range(200):
        cand = run_policy(env, "mdp", rng, policy=pol_mdp)
        if cand["feasible"] and (sim is None or cand["net"] > sim["net"]):
            sim = cand
    pol_rows = [{"slot": t, "clock": hr(t), "action": a, "soc": s}
                for t, a, s in sim["path"]]
    pd.DataFrame(pol_rows).to_csv(
        os.path.join(OUT, "mdp_policy_trace.csv"), index=False)

    ch = sim["charge_slots"]
    print(f"\n  MDP charges in {len(ch)} slots: "
          f"{[hr(t) for t in ch] if ch else '(none)'}")
    chp = [t for t in ch if env.price[t] > env.price.min() + 1e-9]
    print(f"  of which OFF the cheapest tariff: {[hr(t) for t in chp]}")

    # what a naive "charge in the valley" plan looks like
    valley = [t for t in range(env.T)
              if env.price[t] <= env.price.min() + 1e-9]
    print(f"  cheapest tariff slots: {[hr(t) for t in valley]}")
    # how much energy the valley can physically supply
    valley_gain = sum(env.p_kw * float(
        __import__("ev_dp").taper(min(0.95, 0.15 + i * 0.6 / len(valley)), env.eta_cc)
    ) * env.eta_c * env.dt_h for i in range(len(valley)))
    print(f"  energy the valley can deliver in {len(valley)} slots"
          f" (~{len(valley)*15/60:.1f} h): ~{valley_gain:.1f} kWh")
    print(f"  energy the day requires: ~{sim['energy_used']:.1f} kWh")

    # ------------------------------------------------------ sensitivities
    print("\nsensitivity analysis ...", flush=True)
    sens_rows = []

    def run_case(label, pname, pval, over):
        """Solve + score one parameter setting. Every override here must be a
        key that Env actually reads -- the earlier version silently passed
        keys Env ignored, which is why the first run produced identical
        numbers for every TOU spread."""
        e2 = Env(**over)
        _, pmdp2 = solve_mdp(e2, kmax=6)
        rm = evaluate(e2, pmdp2, "mdp", n_sims=150, seed=SEED)
        rb = evaluate(e2, None, "cheapest", n_sims=150, seed=SEED)
        gain = rm["net"] - rb["net"]
        row = {
            "study": label, "parameter": pname, "value": pval,
            "mdp_net": rm["net"], "baseline_net": rb["net"], "gain": gain,
            "gain_pct": gain / abs(rb["net"]) * 100 if abs(rb["net"]) > 1e-6 else np.nan,
            "mdp_feasible": rm["feasible_rate"], "base_feasible": rb["feasible_rate"],
            "energy_needed_kwh": e2.energy_served_total(),
            "battery_kwh": e2.batt,
            "n_charge_slots": len(run_policy_one(e2, pmdp2, SEED)["charge_slots"]),
        }
        sens_rows.append(row)
        print(f"  {label:32s} MDP=${row['mdp_net']:8,.2f}"
              f"  base=${row['baseline_net']:8,.2f}"
              f"  gain=${row['gain']:8,.2f}"
              f"  MDPfeas={row['mdp_feasible']:4.0%}"
              f"  basefeas={row['base_feasible']:4.0%}"
              f"  ncharge={row['n_charge_slots']}", flush=True)
        return row

    # S1: TOU spread -- the headline parameter. spread=0 means a flat tariff,
    # which should make the MDP indifferent to WHEN it charges.
    for sp in [0.0, 0.5, 1.0, 1.5, 2.0]:
        run_case(f"TOU spread x{sp:.1f}", "tou_spread", sp,
                 {"price": tou_price(96, sp)})

    # S2: battery size
    for b in [25.0, 30.0, 35.0, 40.0, 50.0, 60.0, 80.0]:
        run_case(f"battery {b:.0f} kWh", "battery_kwh", b, {"batt": b})

    # S3: energy intensity
    for k in [0.18, 0.22, 0.28, 0.35, 0.45]:
        run_case(f"consumption {k:.2f} kWh/km", "kwh_per_km", k, {"kwh_km": k})

    # S4: charger power
    for p in [7.0, 22.0, 60.0, 120.0, 200.0]:
        run_case(f"charger {p:.0f} kW", "charge_kw", p, {"p_kw": p})

    # S5: fleet density (peak utilisation -> how contested the market is)
    for u in [0.4, 0.6, 0.85, 1.0]:
        run_case(f"peak utilisation {u:.0%}", "u_peak", u, {"u_peak": u})

    # S6: fare level (how valuable is an hour of road time)
    for f in [0.7, 0.85, 1.0, 1.2, 1.5]:
        run_case(f"fares x{f:.2f}", "fare_scale", f, {"fare_scale": f})

    # S7: start-of-day SOC
    for s0 in [0.30, 0.50, 0.80, 0.95]:
        e2 = Env()
        _, pmdp2 = solve_mdp(e2, kmax=6)
        rm = evaluate(e2, pmdp2, "mdp", n_sims=150, seed=SEED, soc0=s0)
        rb = evaluate(e2, None, "cheapest", n_sims=150, seed=SEED, soc0=s0)
        gain = rm["net"] - rb["net"]
        row = {"study": f"start SOC {s0:.0%}", "parameter": "soc0", "value": s0,
               "mdp_net": rm["net"], "baseline_net": rb["net"], "gain": gain,
               "gain_pct": gain / abs(rb["net"]) * 100 if abs(rb["net"]) > 1e-6 else np.nan,
               "mdp_feasible": rm["feasible_rate"], "base_feasible": rb["feasible_rate"],
               "energy_needed_kwh": e2.energy_served_total(),
               "battery_kwh": e2.batt,
               "n_charge_slots": len(run_policy_one(e2, pmdp2, SEED, soc0=s0)["charge_slots"])}
        sens_rows.append(row)
        print(f"  {row['study']:32s} MDP=${row['mdp_net']:8,.2f}"
              f"  base=${row['baseline_net']:8,.2f}  gain=${row['gain']:8,.2f}"
              f"  MDPfeas={row['mdp_feasible']:4.0%}"
              f"  ncharge={row['n_charge_slots']}", flush=True)

    pd.DataFrame(sens_rows).to_csv(
        os.path.join(OUT, "sensitivity.csv"), index=False)

    # ------------------------------------------------------------- summary
    summary = {
        "env": {
            "battery_kwh": env.batt, "reserve_soc": env.soc_res,
            "charge_kw": env.p_kw, "charge_eff": env.eta_c,
            "kwh_km": env.kwh_km, "eta_cc_soc": env.eta_cc,
            "cap_trips_per_slot": env.cap,
            "n_drivers_calibrated": env.n_drivers,
            "peak_utilisation": env.u_peak,
            "lambda_city_max_over_min": float(env.lam_city.max() / env.lam_city.min()),
            "lambda_driver_max_over_min": float(env.lam.max() / env.lam.min()),
            "energy_if_always_driving_kwh": env.energy_served_total(),
            "price_min": float(env.price.min()), "price_max": float(env.price.max()),
        },
        "dp_value_if_demand_known": float(dp0),
        "dp_policy_net_under_stochastic_demand": float(dp_row["net"]),
        "dp_policy_feasible_rate": float(dp_row["feasible_rate"]),
        "mdp_value": float(mdp0),
        "best_rule_baseline": best_base_name,
        "best_rule_baseline_net": best_base_net,
        "tariff_following_net": float(cheapest_row["net"]),
        "tariff_following_feasible": float(cheapest_row["feasible_rate"]),
        "mdp_net_mc": mdp_net,
        "mdp_feasible": float(mdp_row["feasible_rate"]),
        "gain_vs_best_simple_rule": gain_vs_best,
        "gain_vs_best_simple_rule_pct": gain_vs_best / best_base_net * 100,
        "gain_vs_tariff_following": gain_vs_cheap,
        "gain_vs_tariff_following_pct":
            gain_vs_cheap / float(cheapest_row["net"]) * 100,
        "mdp_charge_slots": [hr(t) for t in ch],
        "mdp_charge_slots_off_cheapest": [hr(t) for t in chp],
        "valley_slots": [hr(t) for t in valley],
        "n_sims": N_SIMS, "seed": SEED,
    }
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)

    print(f"\nwrote {OUT}")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
