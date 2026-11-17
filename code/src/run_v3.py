"""
The v3 experiments: charging as an excursion, on a MULTI-DAY cycle.

    E1  the queue sweep        -- does the queue change the optimal schedule?
    E2  the policy comparison  -- does the optimiser still beat every rule?
    E3  the refusal penalty    -- what does it cost to refuse an order?
    E4  the hardware calibration -- 2026 cars against the 2024 working model
    E5  the price structure    -- the regulated TOU against the 2026 market
    E6  the master sweep       -- how tight is the energy budget?
    E7  the demand model       -- book value is not executability

Everything is computed on the CYCLIC model: the driver works day after day,
the battery carries over midnight, and the value of the pack at the end of
the day is the value of the pack at the start of the next one. The single-
day model turned out to be an artefact of an unhandled boundary condition
(see docs/experiment/v3-results.md).

Every number written to results/ comes from this file, at the same seed as
the v2 suite (20261001), so the base row of every sweep reproduces the main
table exactly and the two can be read against each other.

Run:  python run_v3.py
"""

import os

import numpy as np
import pandas as pd

from ev_dp3 import (Env3, cyclic_value_iteration3, evaluate3_cyclic,
                    optimal_start_soc3, policy_day, shadow_price3,
                    steady_state_soc3)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir))
RES = os.path.join(ROOT, "results")
os.makedirs(RES, exist_ok=True)

SEED = 20261001
NSIMS = 200
DAYS = 8           # consecutive days per simulated driver
WARMUP = 2         # the first two days are the transient

# Two calibrations of the car. The first is the one the 2024 paper used; the
# second is what a ride-hailing EV looks like in 2026 (a 57.6 kWh pack on a
# 90 kW charger, and a real EV's consumption rather than the working
# model's). They are kept side by side rather than swapped in silently,
# because the difference between them is itself a result.
CALIBRATIONS = {
    "v2-2024": dict(batt=40.0, p_kw=60.0, kwh_km=0.22),
    "2026": dict(batt=57.6, p_kw=90.0, kwh_km=0.19),
}

# The reference configuration: a queue that peaks at 1 h in the two human
# windows, a 15-min drive to the station each way, a 0.7 kWh deadhead, and
# at most 4 dwell slots per visit.
BASE = dict(queue_shape="meal", queue_peak_slots=4.0, access_slots=1,
            return_slots=1, access_kwh=0.7, max_dwell=4, miss_penalty=0.0)

# The starting SOC for the comparison. Every policy starts from the SAME
# pack, so the table measures the policy and not the initial condition; the
# optimiser's own steady state is reported separately as a column.
SOC0 = 0.80

RULES = ["cheapest-net", "cheapest-plug", "cheapest-depart",
         "threshold", "charge-full", "never-charge"]


def _mk(cal, **over):
    kw = dict(BASE)
    kw.update(CALIBRATIONS[cal])
    kw.update(over)
    return Env3(**kw)


def _solve(env, solver="mdp"):
    """The cyclic optimiser (or one of the deterministic baselines).

    The returned dict carries everything the write-up needs: the
    convergence record of the fixed-point iteration, the shadow price of
    the pack carried across midnight, and the two different senses of "the
    SOC the driver carries" -- the one that maximises the FIRST day's
    continuation value, and the one that the daily cycle actually settles
    into.
    """
    W, pol, pol_k, iters, hist = cyclic_value_iteration3(env, kmax=6,
                                                          solver=solver)
    s_ss = steady_state_soc3(env, pol, pol_k)
    return {
        "W": W, "pol": pol, "pol_k": pol_k,
        "iters": iters, "resid": float(hist[-1]) if hist else float("nan"),
        "mu": shadow_price3(W, env),
        "s_first": optimal_start_soc3(W, env),
        "s_ss": s_ss,
    }


def _sched(env, sol, soc0=None):
    """The policy's own plan, as a readable string, followed under the mean
    demand profile from the stated starting SOC."""
    s = sol["s_ss"] if soc0 is None else soc0
    ev = policy_day(env, sol["pol"], sol["pol_k"], soc0=s)
    return "|".join(f"{t * 15 // 60:02d}:{t * 15 % 60:02d}(k{k})"
                    for t, k, _D, _c in ev)


def _eval(env, kind, sol=None, nsims=NSIMS, seed=SEED, **kw):
    extra = dict(kw)
    if kind in ("mdp", "dp") and sol is not None:
        extra["policy"] = sol["pol"]
        extra["pol_k"] = sol["pol_k"]
    return evaluate3_cyclic(env, kind, n_sims=nsims, seed=seed, days=DAYS,
                             soc0=SOC0, warmup=WARMUP, **extra)


def _best_rule(env, **kw):
    """The strongest rule, so the gain of the optimiser is measured against
    the best thing a driver could do without an optimiser -- not against a
    strawman."""
    best = (None, -np.inf)
    for kind in RULES:
        r = _eval(env, kind, **kw)
        if r["net"] > best[1]:
            best = (kind, r["net"])
    return best


# ===========================================================================
# E1  the queue sweep
# ===========================================================================
def e1_queue_sweep():
    """Does the queue change WHEN the driver charges, or only HOW MUCH it
    costs?

    Four queue shapes x five levels. The shapes are not estimates -- there is
    no public data on the arrival process of chargers -- so the question is
    not which shape is right but whether the answer survives all of them.
    """
    rows = []
    for cal in CALIBRATIONS:
        for shape in ["uniform", "demand", "idle", "meal"]:
            for hours in [0.0, 0.5, 1.0, 1.5, 2.0]:
                env = _mk(cal, queue_shape=shape,
                          queue_peak_slots=int(round(hours * 4)))
                sol = _solve(env)
                r = _eval(env, "mdp", sol)
                rows.append({
                    "calibration": cal, "shape": shape,
                    "queue_peak_h": hours,
                    "queue_slots": int(env.q.max()),
                    "net": r["net"], "net_adj": r["net_adj"],
                    "net_feasible_only": r["net_feasible_only"],
                    "revenue": r["revenue"], "energy_cost": r["energy_cost"],
                    "feasible_rate": r["feasible_rate"],
                    "missed": r["missed"], "acceptance": r["acceptance"],
                    "excursions": r["excursions"],
                    "offroad_slots": r["offroad_slots"],
                    "charge_kwh": r["charge_kwh"],
                    "mean_start_soc": r["mean_start_soc"],
                    "shadow_price": sol["mu"], "steady_soc": sol["s_ss"],
                    "iters": sol["iters"], "resid": sol["resid"],
                    "schedule": _sched(env, sol),
                })
                print(f"  [E1] {cal:8s} {shape:8s} q<={hours:.1f}h  "
                      f"net ${r['net']:8,.2f}  feas {r['feasible_rate']:6.1%}  "
                      f"offroad {r['offroad_slots']:5.1f}  "
                      f"{rows[-1]['schedule']}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "v3_queue_sweep.csv"), index=False)
    return df


# ===========================================================================
# E2  the policy comparison
# ===========================================================================
def e2_policy_comparison():
    """The main table. The optimiser against every rule, including the
    oracle rule that knows the queue and the demand curve exactly, and
    against the two deterministic baselines under the same multi-day
    boundary condition."""
    rows = []
    for cal in CALIBRATIONS:
        env = _mk(cal)
        sol = _solve(env)
        sol_dp = _solve(env, solver="dp")
        env_ca = _mk(cal, cap_aware=True)
        sol_ca = _solve(env_ca, solver="dp")

        entries = [
            ("Optimiser (cyclic MDP)", "mdp", sol, env),
            ("DP (expected value)", "dp", sol_dp, env),
            ("DP (capacity-aware)", "dp", sol_ca, env_ca),
        ]
        for kind in RULES:
            entries.append((f"Rule: {kind}", kind, None, env))

        for label, kind, s, e in entries:
            r = _eval(e, kind, s)
            rows.append({
                "calibration": cal, "policy": label,
                "net": r["net"], "net_adj": r["net_adj"],
                "net_feasible_only": r["net_feasible_only"],
                "revenue": r["revenue"], "energy_cost": r["energy_cost"],
                "feasible_rate": r["feasible_rate"], "missed": r["missed"],
                "acceptance": r["acceptance"],
                "missed_value": r["missed_value"],
                "orders": r["orders"], "excursions": r["excursions"],
                "offroad_slots": r["offroad_slots"],
                "charge_kwh": r["charge_kwh"], "final_soc": r["final_soc"],
                "mean_start_soc": r["mean_start_soc"],
                "shadow_price": (s["mu"] if s else np.nan),
                "steady_soc": (s["s_ss"] if s else np.nan),
                "iters": (s["iters"] if s else np.nan),
                "resid": (s["resid"] if s else np.nan),
                "schedule": (_sched(e, s) if s else ""),
            })
            print(f"  [E2] {cal:8s} {label:26s} net ${r['net']:8,.2f}  "
                  f"feas {r['feasible_rate']:6.1%}  missed {r['missed']:5.2f}  "
                  f"offroad {r['offroad_slots']:5.1f}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "v3_policy_comparison.csv"), index=False)
    return df


# ===========================================================================
# E3  the refusal penalty
# ===========================================================================
def e3_penalty_sweep():
    """What is it worth to the driver to turn an order down?

    v2 had no such term, so the optimiser was free to plan exactly on the
    reserve floor. This sweep shows what a non-zero penalty buys.
    """
    rows = []
    for cal in CALIBRATIONS:
        for pen in [0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 28.0, 50.0]:
            env = _mk(cal, miss_penalty=pen)
            sol = _solve(env)
            r = _eval(env, "mdp", sol)
            rows.append({
                "calibration": cal, "miss_penalty": pen,
                "net": r["net"], "net_adj": r["net_adj"],
                "feasible_rate": r["feasible_rate"], "missed": r["missed"],
                "acceptance": r["acceptance"],
                "excursions": r["excursions"],
                "shadow_price": sol["mu"], "steady_soc": sol["s_ss"],
                "schedule": _sched(env, sol),
            })
            print(f"  [E3] {cal:8s} penalty ${pen:5.1f}  net ${r['net']:8,.2f}"
                  f"  feas {r['feasible_rate']:6.1%}  "
                  f"missed {r['missed']:5.2f}  {rows[-1]['schedule']}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "v3_penalty_sweep.csv"), index=False)
    return df


# ===========================================================================
# E4  the hardware calibration
# ===========================================================================
def e4_calibration():
    """How much of the 2024 result survives 2026 hardware?

    The battery is swept across the range of packs actually fitted to
    ride-hailing EVs, the charger across the public-DC power range, and the
    consumption across the efficiency of a modern EV.
    """
    rows = []
    grid = []
    for batt in [25.0, 40.0, 57.6, 80.0]:
        grid.append(("battery_kwh", batt, dict(batt=batt)))
    for p_kw in [30.0, 60.0, 90.0, 120.0, 250.0]:
        grid.append(("charge_kw", p_kw, dict(p_kw=p_kw)))
    for kwh_km in [0.15, 0.17, 0.19, 0.22, 0.25]:
        grid.append(("kwh_per_km", kwh_km, dict(kwh_km=kwh_km)))
    for soc_res in [0.05, 0.10, 0.15, 0.20, 0.25]:
        grid.append(("reserve_soc", soc_res, dict(soc_res=soc_res)))
    for shape in ["uniform", "demand", "idle", "meal"]:
        grid.append(("queue_shape", shape, dict(queue_shape=shape)))

    for cal in CALIBRATIONS:
        for param, value, over in grid:
            env = _mk(cal, **over)
            sol = _solve(env)
            r = _eval(env, "mdp", sol)
            # the gain of the optimiser over the strongest rule
            gname, gnet = _best_rule(env)
            rows.append({
                "calibration": cal, "parameter": param, "value": value,
                "net": r["net"], "feasible_rate": r["feasible_rate"],
                "missed": r["missed"], "acceptance": r["acceptance"],
                "best_rule": gname, "gain_over_best_rule": r["net"] - gnet,
                "shadow_price": sol["mu"], "steady_soc": sol["s_ss"],
                "schedule": _sched(env, sol),
            })
            print(f"  [E4] {cal:8s} {param:14s} {str(value):8s} "
                  f"net ${r['net']:8,.2f}  feas {r['feasible_rate']:6.1%}  "
                  f"gain over {gname:16s} ${r['net'] - gnet:7,.2f}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "v3_calibration.csv"), index=False)
    return df


# ===========================================================================
# E5  the price structure
# ===========================================================================
def e5_price_mode():
    """The regulated four-tier TOU against the 2026 market price.

    Since 2026-03-01 a participant in the market is no longer on a
    government-fixed schedule, so the daily shape follows the merit order:
    midday solar is the valley and the evening ramp is the peak, and the
    operator's service fee is itself time-varying.
    """
    rows = []
    for cal in CALIBRATIONS:
        for mode in ["tou", "market"]:
            env = _mk(cal, price_mode=mode)
            sol = _solve(env)
            r = _eval(env, "mdp", sol)
            gname, gnet = _best_rule(env)
            rows.append({
                "calibration": cal, "price_mode": mode,
                "price_min": float(env.price_all.min()),
                "price_max": float(env.price_all.max()),
                "spread_ratio": float(env.price_all.max() / env.price_all.min()),
                "net": r["net"], "energy_cost": r["energy_cost"],
                "feasible_rate": r["feasible_rate"],
                "best_rule": gname,
                "gain_over_best_rule": r["net"] - gnet,
                "shadow_price": sol["mu"], "steady_soc": sol["s_ss"],
                "schedule": _sched(env, sol),
            })
            print(f"  [E5] {cal:8s} {mode:7s} net ${r['net']:8,.2f}  "
                  f"spread {rows[-1]['spread_ratio']:.1f}x  "
                  f"gain over {gname:16s} ${r['net'] - gnet:7,.2f}  "
                  f"{rows[-1]['schedule']}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "v3_price_mode.csv"), index=False)
    return df


# ===========================================================================
# E6  the master sweep: how tight is the energy budget?
# ===========================================================================
def e6_master_sweep():
    """The daily distance is the input our own field research could not pin
    down. The platform data puts an active Guangdong driver at 134.9 km/day,
    an industry report says 328 km/day, and our own demand profile implies
    248 km/day -- a 2.4x spread. It is also the input that decides whether
    the driver has to charge at all, so it gets its own sweep.

    `u_peak` scales the driver's order rate, and therefore the distance
    driven, without touching the SHAPE of the demand curve.
    """
    rows = []
    for cal in CALIBRATIONS:
        for u in [0.40, 0.55, 0.70, 0.85, 1.00]:
            for batt in [40.0, 57.6]:
                env = _mk(cal, u_peak=u, batt=batt)
                e_day = env.energy_served_total()
                usable = env.batt * (1.0 - env.soc_res)
                km = e_day / env.kwh_km
                sol = _solve(env)
                r = _eval(env, "mdp", sol)
                gname, gnet = _best_rule(env)
                rows.append({
                    "calibration": cal, "u_peak": u, "battery_kwh": batt,
                    "km_per_day": km, "energy_per_day_kwh": e_day,
                    "usable_kwh": usable,
                    "budget_ratio": e_day / usable,
                    "net": r["net"], "feasible_rate": r["feasible_rate"],
                    "acceptance": r["acceptance"],
                    "best_rule": gname,
                    "gain_over_best_rule": r["net"] - gnet,
                    "gain_pct": 100.0 * (r["net"] - gnet) / max(gnet, 1e-9),
                    "excursions": r["excursions"],
                    "shadow_price": sol["mu"], "steady_soc": sol["s_ss"],
                    "schedule": _sched(env, sol),
                })
                print(f"  [E6] {cal:8s} u={u:.2f} batt={batt:5.1f}  "
                      f"{km:6.1f} km/day  budget {e_day / usable:.2f}  "
                      f"net ${r['net']:8,.2f}  "
                      f"gain over {gname:16s} ${r['net'] - gnet:7,.2f} "
                      f"({100.0 * (r['net'] - gnet) / max(gnet, 1e-9):5.1f}%)",
                      flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "v3_master_sweep.csv"), index=False)
    return df


# ===========================================================================
# E7  the demand model: book value is not executability
# ===========================================================================
def e7_demand_model():
    """The v2 suite found that the gap between the expected-value DP and the
    MDP is 95% a Jensen artefact: a deterministic plan that books the
    MEAN arrival count cannot serve the tail, so the plan's book value is
    not a number the driver can ever earn. Here the same check is run
    inside the v3 excursion model, because the excursion makes the point
    sharper: a deterministic plan also assumes the excursion happens at the
    moment it was planned.

    The three solvers differ ONLY in the demand model -- same boundary
    condition, same queue, same excursion mechanics:

        dp     books min(lambda, cap)          -- what a deterministic plan
                                                    assumes
        dp_ca  books E[min(N, cap)]            -- the honest expectation
        mdp    integrates over the Poisson law  -- the stochastic optimum
    """
    rows = []
    for cal in CALIBRATIONS:
        env = _mk(cal)
        sol = _solve(env)
        sol_dp = _solve(env, solver="dp")
        env_ca = _mk(cal, cap_aware=True)
        sol_ca = _solve(env_ca, solver="dp")

        # the book value each plan claims, in the units of its own model
        i0 = env.to_idx(SOC0)
        book_dp = float(sol_dp["W"][i0])
        book_ca = float(sol_ca["W"][i0])
        book_mdp = float(sol["W"][i0])

        r_dp = _eval(env, "dp", sol_dp)
        r_ca = _eval(env_ca, "dp", sol_ca)
        r_mdp = _eval(env, "mdp", sol)

        rows.append({
            "calibration": cal,
            "book_dp": book_dp, "book_dp_ca": book_ca, "book_mdp": book_mdp,
            "gap_naive_to_mdp": book_dp - book_mdp,
            "gap_ca_to_mdp": book_ca - book_mdp,
            "net_dp": r_dp["net"], "net_dp_ca": r_ca["net"],
            "net_mdp": r_mdp["net"],
            "feas_dp": r_dp["feasible_rate"], "feas_dp_ca": r_ca["feasible_rate"],
            "feas_mdp": r_mdp["feasible_rate"],
            "energy_naive_kwh": float(env.energy_served_total()),
            "energy_honest_kwh": float(env_ca.energy_served_total()),
        })
        print(f"  [E7] {cal:8s} book dp ${book_dp:8,.2f}  "
              f"dp_ca ${book_ca:8,.2f}  mdp ${book_mdp:8,.2f}   "
              f"gap {book_dp - book_mdp:7,.2f} -> {book_ca - book_mdp:6,.2f}",
              flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "v3_demand_model.csv"), index=False)
    return df


if __name__ == "__main__":
    import sys

    STAGES = [
        ("E1", "the queue sweep", e1_queue_sweep),
        ("E2", "the policy comparison", e2_policy_comparison),
        ("E3", "the refusal penalty", e3_penalty_sweep),
        ("E4", "the hardware calibration", e4_calibration),
        ("E5", "the price structure", e5_price_mode),
        ("E6", "the master sweep: how tight is the energy budget?", e6_master_sweep),
        ("E7", "the demand model: book value is not executability", e7_demand_model),
    ]

    want = [a.strip().upper() for a in sys.argv[1:]] or [k for k, _, _ in STAGES]

    for key, title, fn in STAGES:
        if key not in want:
            continue
        print("=" * 72)
        print(key, " ", title)
        print("=" * 72)
        fn()
        print()

    print("results written to", RES)
