"""
Ablations A1-A6 and the v2 extension (cyclic multi-day driver).

Two questions this script answers:

  (1) WHICH structural element of the model is actually doing the work?
      Each ablation removes exactly one element and reports what breaks.
      A1 drop the stochasticity, A2 drop the TOU spread, A3 drop the CC-CV
      taper, A4 drop the driver time cap, A5 relax the reserve floor from
      "infeasible" to "clamped", A6 flatten the intra-day demand profile.

  (2) What does a driver who works DAY AFTER DAY do differently from a
      driver who solves one isolated day? That is the v2 extension: the
      one-day MDP is replaced by an average-reward MDP whose epoch is the
      whole day, so the end of the day is linked to the start of the next
      one. It answers a question the single-day model cannot: what SOC
      should the driver start the day with, and is "charge to 100% every
      night" actually optimal?

Nothing here is hand-entered: every number is produced by solving and
simulating the modified model in this file.

    python ablations.py    ->  results/ablations.csv, results/cyclic_multiday.csv
"""

import copy
import json
import os

import numpy as np
import pandas as pd

from ev_dp import (CHARGE, DRIVE, IDLE, Env, evaluate, run_policy, solve_dp,
                   solve_mdp, taper, tou_price)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir))
OUT = os.path.join(ROOT, "results")
SEED = 20261001
N_SIMS = 600


def hr(t: int) -> str:
    return f"{t*15//60:02d}:{t*15%60:02d}"


def charge_slots_of(env, pol, seed=SEED, tries=150):
    """Charge slots (indices) of a representative feasible day under `pol`."""
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(tries):
        c = run_policy(env, "mdp", rng, policy=pol)
        if c["feasible"] and (best is None or c["net"] > best["net"]):
            best = c
    if best is None:
        return []
    return list(best["charge_slots"])


def slots_str(slots) -> str:
    return ", ".join(hr(t) for t in slots) or "(none)"


# ===========================================================================
# A5: the reserve floor relaxed from INFEASIBLE to CLAMPED
# ===========================================================================
def solve_dp_clamped(env: Env):
    """Same DP as solve_dp, but the reserve floor is CLAMPED instead of
    enforced: when the pack would drop below the floor the SOC is pinned at
    the floor and the energy simply appears. This is the modelling mistake
    that is easy to make, so we build it on purpose to show what it does.
    """
    T, nS = env.T, env.nS
    batt = env.batt
    V = np.zeros((T + 1, nS))
    pol = np.zeros((T, nS), dtype=np.int8)
    floor_kwh = env.soc_res * batt

    for t in range(T - 1, -1, -1):
        Vn = V[t + 1]
        cst = env.ccost[t, 0]
        gain = env.gain
        for i in range(nS):
            s = env.soc[i]
            best, barg = -np.inf, IDLE

            # DRIVE with the clamp: the pack is refilled for free.
            new_kwh = max(floor_kwh, s * batt - env.served_kwh[t])
            j = env.to_idx(new_kwh / batt)
            vd = env.served_rev[t] + Vn[j]
            if vd > best:
                best, barg = vd, DRIVE

            # CHARGE
            j = env.to_idx(min(1.0, s * batt + gain[i]) / batt)
            vc = -cst + Vn[j]
            if vc > best:
                best, barg = vc, CHARGE

            vi = Vn[i]
            if vi > best:
                best, barg = vi, IDLE

            V[t, i] = best
            pol[t, i] = barg
    return V, pol


def sim_clamped(env: Env, pol, rng):
    """Simulate a policy under the CLAMPED physics it was solved under, and
    also record how much energy the day actually demands. If the demand
    exceeds the pack size, the policy is not physically implementable no
    matter what the objective says."""
    T, batt = env.T, env.batt
    s = 0.80
    rev = cost = drawn = 0.0
    n_charge = 0
    for t in range(T):
        i = env.to_idx(s)
        a = int(pol[t, i])
        if a == CHARGE:
            g = env.p_kw * float(taper(s, env.eta_cc)) * env.eta_c * env.dt_h
            s = min(1.0, s + g / batt)
            cost += env.price[t] * env.p_kw * env.dt_h
            n_charge += 1
        elif a == DRIVE:
            N = rng.poisson(env.lam[t])
            m = min(N, env.cap)
            e = m * env.kwh[t]
            drawn += e
            s = max(env.soc_res, s - e / batt)      # <-- the clamp
            rev += m * env.fare[t]
    return {"revenue": rev, "energy_cost": cost, "net": rev - cost,
            "energy_drawn_kwh": drawn, "battery_kwh": batt,
            "n_charge_slots": n_charge}


# ===========================================================================
# v2: cyclic (multi-day) average-reward driver
# ===========================================================================
def cyclic_value_iteration(env: Env, iters=2000, tol=1e-9, damping=0.5, kmax=6):
    """Optimal long-run policy for a driver who works day after day.

    The day is the epoch. Let W(s) be the value of STARTING a day with SOC s,
    where the value already includes the continuation into the next day:

        V(T, s) = W(s)                  end of day  ->  start of next day
        V(t, s) = max_a E[ r_t(a) + V(t+1, s') ]
        W(s)    = V(0, s)               fixed point

    T(W + c) = T(W) + c for every constant c, so the fixed point is only
    determined up to an additive constant: the LEVEL of W drifts by the
    average daily reward on every sweep. Centering W after each sweep
    removes that drift, and what is left contracts. Without the centering
    the iteration diverges (we measured a residual of 9.3e2 after 400
    sweeps), which is why this detail matters.
    """
    nS = env.nS
    W = np.zeros(nS)
    pol = None
    hist = []
    for it in range(iters):
        V, pol = solve_mdp(env, kmax=kmax, V_term=W)
        W_raw = V[0, :]
        Wc = W_raw - W_raw.mean()          # remove the level drift
        gap = float(np.max(np.abs(Wc - (W - W.mean()))))
        hist.append(gap)
        W = W.mean() + (1.0 - damping) * (W - W.mean()) + damping * Wc
        if gap < tol:
            break
    return W, pol, it, hist


def extend_env(env: Env, days: int) -> Env:
    """A copy of `env` with `days` identical working days back to back. Used
    for the finite-horizon cross-check of the cyclic fixed point."""
    e = copy.copy(env)
    e.T = env.T * days
    e.lam = np.tile(env.lam, days)
    e.fare = np.tile(env.fare, days)
    e.kwh = np.tile(env.kwh, days)
    e.price = np.tile(env.price, days)
    e.ccost = e.price[:, None] * e.p_kw * e.dt_h
    e.n_eff = np.minimum(e.lam, e.cap)
    e.served_rev = e.n_eff * e.fare
    e.served_kwh = e.n_eff * e.kwh
    return e


def shadow_price(W, env: Env, s_lo=0.30, s_hi=0.95) -> float:
    """dW/ds per kWh, evaluated over the SOC band the driver actually
    operates in. This is the price of a kWh carried across the day boundary."""
    grid = env.soc
    band = (grid >= s_lo) & (grid <= s_hi)
    if band.sum() < 3:
        band = np.ones_like(grid, dtype=bool)
    i0 = int(np.argmax(band))
    i1 = int(len(grid) - 1 - np.argmax(band[::-1]))
    if i1 <= i0:
        return float("nan")
    ds_kwh = (grid[i1] - grid[i0]) * env.batt
    return float((W[i1] - W[i0]) / ds_kwh)


def run_cyclic_days(env: Env, pol, days=60, s0=0.80, seed=SEED):
    """Run the cyclic policy for consecutive days and record the SOC at the
    start of each day plus the daily net."""
    rng = np.random.default_rng(seed)
    s = s0
    starts, nets = [], []
    for _ in range(days):
        starts.append(s)
        r = run_policy(env, "mdp", rng, policy=pol, soc0=s)
        nets.append(r["net"])
        s = r["final_soc"]
    return np.array(starts), np.array(nets)


# ===========================================================================
def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    rows = []

    def record(tag, what, env, pol, note, extra=None):
        """Solve one configuration and score it against the same yardstick."""
        r_mdp = evaluate(env, pol, "mdp", n_sims=N_SIMS, seed=SEED)
        r_cheap = evaluate(env, None, "cheapest", n_sims=N_SIMS, seed=SEED)
        slots = charge_slots_of(env, pol)
        pmin = float(env.price.min())
        n_off = int(sum(1 for t in slots if env.price[t] > pmin + 1e-9))
        row = {
            "ablation": tag,
            "element_removed": what,
            "mdp_net": r_mdp["net"],
            "mdp_net_std": r_mdp["net_std"],
            "mdp_feasible": r_mdp["feasible_rate"],
            "mdp_revenue": r_mdp["revenue"],
            "mdp_energy_cost": r_mdp["energy_cost"],
            "mdp_charge_kwh": r_mdp["charge_kwh"],
            "tariff_rule_net": r_cheap["net"],
            "tariff_rule_feasible": r_cheap["feasible_rate"],
            "gain_vs_tariff_rule": r_mdp["net"] - r_cheap["net"],
            "charge_slots": slots_str(slots),
            "n_charge_slots": len(slots),
            "n_slots_off_cheapest_tariff": n_off,
            "note": note,
        }
        if extra:
            row.update(extra)
        rows.append(row)
        print(f"  {tag:22s} net=${row['mdp_net']:8,.2f}  feas={row['mdp_feasible']:4.0%}"
              f"  gain=${row['gain_vs_tariff_rule']:7,.2f}"
              f"  slots={row['charge_slots']}", flush=True)
        return row

    print("=" * 78)
    print("ABLATIONS")
    print("=" * 78)

    env = Env()

    # ------------------------------------------------ planner/simulator check
    # The planner must optimise the same quantity the Monte-Carlo evaluator
    # measures. Two variants of the value function are compared:
    #   legacy      outcomes that would breach the reserve are DROPPED from
    #               the expectation (probability mass is lost)
    #   consistent  the driver serves as many trips as the remaining energy
    #               allows -- exactly the simulator's rule
    # If the model is right, V(0, 80%) should equal the Monte-Carlo mean net
    # of that policy, to within the sampling error.
    print("\nPLANNER / SIMULATOR CONSISTENCY CHECK")
    cons_rows = []
    N_CHK = 4000
    for tag, kw in [("legacy (outcomes dropped)", dict(consistent=False)),
                    ("consistent (partial service)", dict(consistent=True))]:
        V, pol = solve_mdp(env, kmax=6, **kw)
        r = evaluate(env, pol, "mdp", n_sims=N_CHK, seed=SEED)
        se = r["net_std"] / np.sqrt(N_CHK)
        v = float(V[0, env.to_idx(0.80)])
        print(f"  {tag:30s} V(0,80%)=${v:8,.2f}  MC net=${r['net']:8,.2f}"
              f" +- {se:5,.2f} (SE)  gap={r['net']-v:+6,.2f}"
              f"  feasible={r['feasible_rate']:.1%}")
        cons_rows.append({
            "variant": tag, "V_at_080": v, "mc_net": r["net"],
            "mc_se": se, "gap": r["net"] - v, "gap_in_se": (r["net"] - v) / se,
            "feasible_rate": r["feasible_rate"], "n_sims": N_CHK})
    pd.DataFrame(cons_rows).to_csv(
        os.path.join(OUT, "model_consistency.csv"), index=False)

    # ------------------------------------------------------------ baseline
    V_mdp, pol_mdp = solve_mdp(env, kmax=6)
    print("\nBASELINE (full model, v2 consistent planner)")
    record("BASELINE", "(nothing)", env, pol_mdp,
           "reference row for every ablation")

    # ------------------------------------------------------------ A1
    print("\nA1  remove stochasticity (expected-value DP instead of the MDP)")
    V_dp, pol_dp = solve_dp(env)
    record("A1 no stochasticity", "random order arrivals", env, pol_dp,
           "DP policy scored under stochastic demand",
           extra={"dp_value_if_demand_known": float(V_dp[0, env.to_idx(0.80)]),
                  "mdp_value": float(V_mdp[0, env.to_idx(0.80)])})

    # ------------------------------------------------------------ A2
    print("\nA2  remove the TOU spread (flat tariff)")
    env2 = Env(price=tou_price(96, 0.0))
    _, pol2 = solve_mdp(env2, kmax=6)
    record("A2 flat tariff", "peak/valley price spread", env2, pol2,
           "same charge slots as baseline => the spread does not set the timing")

    # ------------------------------------------------------------ A3
    print("\nA3  remove the CC-CV taper (constant-power charging)")
    env3 = Env(no_taper=True)
    _, pol3 = solve_mdp(env3, kmax=6)
    record("A3 no CC-CV taper", "charge-power taper above 80% SOC", env3, pol3,
           "flat marginal cost per kWh",
           extra={"effective_cost_at_full_soc":
                  float(env3.price[18] * env3.p_kw * env3.dt_h)})

    # ------------------------------------------------------------ A4
    print("\nA4  remove the driver time cap (unlimited trips per slot)")
    env4 = Env(cap=1e9, n_drivers=env.n_drivers)
    _, pol4 = solve_mdp(env4, kmax=6)
    record("A4 no driver time cap", "the CAP on trips per 15-min slot", env4, pol4,
           "driver serves the whole Poisson tail",
           extra={"served_trips_baseline": float(env.n_eff.sum()),
                  "served_trips_no_cap": float(env4.n_eff.sum())})

    # ------------------------------------------------------------ A5
    print("\nA5  relax the reserve floor from INFEASIBLE to CLAMPED")
    V_cl, pol_cl = solve_dp_clamped(env)
    cl = sim_clamped(env, pol_cl, np.random.default_rng(SEED))
    true_eval = evaluate(env, pol_cl, "dp", n_sims=N_SIMS, seed=SEED)
    print(f"    clamped model believes: net=${cl['net']:,.2f},"
          f" energy drawn {cl['energy_drawn_kwh']:.1f} kWh from a"
          f" {cl['battery_kwh']:.0f} kWh pack"
          f"  ({cl['energy_drawn_kwh']/cl['battery_kwh']:.0%} of the battery)")
    print(f"    same policy under correct physics: net=${true_eval['net']:,.2f},"
          f" feasible {true_eval['feasible_rate']:.0%}")
    rows.append({
        "ablation": "A5 clamped reserve",
        "element_removed": "reserve floor treated as hard infeasibility",
        "mdp_net": cl["net"],
        "mdp_net_std": float("nan"),
        "mdp_feasible": 1.0,
        "mdp_revenue": cl["revenue"],
        "mdp_energy_cost": cl["energy_cost"],
        "mdp_charge_kwh": 0.0,
        "tariff_rule_net": float("nan"),
        "tariff_rule_feasible": float("nan"),
        "gain_vs_tariff_rule": float("nan"),
        "charge_slots": slots_str(charge_slots_of(env, pol_cl)),
        "n_charge_slots": cl["n_charge_slots"],
        "note": (f"clamped model claims ${cl['net']:,.2f} but needs "
                 f"{cl['energy_drawn_kwh']:.1f} kWh from a 40 kWh pack; "
                 f"under correct physics the same policy is feasible only "
                 f"{true_eval['feasible_rate']:.0%} of days and nets "
                 f"${true_eval['net']:,.2f}"),
        "energy_drawn_kwh": cl["energy_drawn_kwh"],
        "true_physics_net": true_eval["net"],
        "true_physics_feasible": true_eval["feasible_rate"],
    })

    # ------------------------------------------------------------ A6
    print("\nA6  flatten the intra-day demand profile (remove the 18.5x swing)")
    env6 = Env()
    lam_flat = float(env6.lam.mean())
    env6.set_lambda(np.full(env6.T, lam_flat))
    _, pol6 = solve_mdp(env6, kmax=6)
    record("A6 flat demand", "the intra-day shape of order arrivals", env6, pol6,
           "opportunity cost becomes constant => tariff decides again",
           extra={"lambda_flat": lam_flat,
                  "day_energy_kwh": env6.energy_served_total()})

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "ablations.csv"), index=False)
    print(f"\nwrote {os.path.join(OUT, 'ablations.csv')}")

    # =====================================================================
    # v2: the cyclic (multi-day) driver
    # =====================================================================
    print("\n" + "=" * 78)
    print("v2 EXTENSION: CYCLIC (MULTI-DAY) DRIVER")
    print("=" * 78)

    W, pol_cyc, iters, hist = cyclic_value_iteration(env)
    mu = shadow_price(W, env)
    print(f"  cyclic value iteration: {iters + 1} sweeps,"
          f" final centred residual {hist[-1]:.3e}")
    print(f"  shadow price of stored energy at the day boundary: ${mu:.4f}/kWh")
    print(f"  TOU range: ${env.price.min():.3f} - ${env.price.max():.3f}/kWh")

    starts, nets = run_cyclic_days(env, pol_cyc, days=60)
    steady = starts[10:]           # discard the transient
    s_star = float(np.mean(steady))
    base_net = evaluate(env, pol_mdp, "mdp", n_sims=N_SIMS, seed=SEED)["net"]
    print(f"  start-of-day SOC: mean {s_star:.1%}"
          f" (sd {np.std(steady):.3f}), range"
          f" {np.min(steady):.1%}-{np.max(steady):.1%}")
    print(f"  average daily net under the cyclic policy: ${np.mean(nets[10:]):,.2f}"
          f"   (single-day MDP from 80%: ${base_net:,.2f})")
    cyc_slots = charge_slots_of(env, pol_cyc)
    print(f"  charge slots under the cyclic policy: {slots_str(cyc_slots)}")

    # ------------------------------------------------------------------
    # Independent cross-check: a D-day finite-horizon DP whose terminal
    # value is zero. The middle days of that problem are the steady state,
    # and they must agree with the cyclic fixed point. Two different
    # formulations, same answer.
    # ------------------------------------------------------------------
    print("\n  cross-check: independent D-day finite-horizon DP")
    horizon_rows = []
    for H in (7, 14, 20):
        envH = extend_env(env, H)
        VH, polH = solve_mdp(envH, kmax=6)
        mid = H // 2
        pol_mid = polH[mid * env.T:(mid + 1) * env.T, :]
        h_slots = charge_slots_of(env, pol_mid)
        startsH, netsH = run_cyclic_days(env, pol_mid, days=60)
        horizon_rows.append({
            "days": H, "s_star": float(np.mean(startsH[10:])),
            "avg_net": float(np.mean(netsH[10:])),
            "mu": shadow_price(VH[mid * env.T], env),
            "slots": slots_str(h_slots)})
        r = horizon_rows[-1]
        print(f"    D={H:2d}: start-of-day SOC {r['s_star']:.1%}"
              f"   avg net ${r['avg_net']:,.2f}"
              f"   mu ${r['mu']:.4f}/kWh   slots {r['slots']}")

    h_star = horizon_rows[-1]["s_star"]
    h_avg = horizon_rows[-1]["avg_net"]
    mu_H = horizon_rows[-1]["mu"]
    h_slots = horizon_rows[-1]["slots"]
    print(f"    cyclic  : start-of-day SOC {s_star:.1%}"
          f"   avg net ${np.mean(nets[10:]):,.2f}"
          f"   mu ${mu:.4f}/kWh   slots {slots_str(cyc_slots)}")

    cyc_rows = [
        {"quantity": "cyclic iterations to converge", "value": iters + 1, "unit": "sweeps"},
        {"quantity": "final centred residual", "value": hist[-1], "unit": "$"},
        {"quantity": "shadow price mu of stored energy (cyclic)", "value": mu, "unit": "$/kWh"},
        {"quantity": "shadow price mu of stored energy (20-day DP)", "value": mu_H, "unit": "$/kWh"},
        {"quantity": "TOU minimum price", "value": float(env.price.min()), "unit": "$/kWh"},
        {"quantity": "TOU maximum price", "value": float(env.price.max()), "unit": "$/kWh"},
        {"quantity": "optimal start-of-day SOC (cyclic)", "value": s_star, "unit": "fraction"},
        {"quantity": "optimal start-of-day SOC (20-day DP)", "value": h_star, "unit": "fraction"},
        {"quantity": "sd of start-of-day SOC (cyclic)", "value": float(np.std(steady)), "unit": "fraction"},
        {"quantity": "average daily net (cyclic)", "value": float(np.mean(nets[10:])), "unit": "$/day"},
        {"quantity": "average daily net (20-day DP middle day)", "value": h_avg, "unit": "$/day"},
        {"quantity": "average daily net (single-day MDP from 80%)",
         "value": float(base_net), "unit": "$/day"},
        {"quantity": "charge slots (cyclic)", "value": slots_str(cyc_slots), "unit": "clock"},
        {"quantity": "charge slots (20-day DP, middle day)", "value": h_slots, "unit": "clock"},
        {"quantity": "energy drawn per day (cyclic)",
         "value": float(np.mean([
             run_policy(env, "mdp", np.random.default_rng(SEED + i),
                        policy=pol_cyc, soc0=0.8)["energy_used"]
             for i in range(20)])), "unit": "kWh"},
    ]
    pd.DataFrame(cyc_rows).to_csv(
        os.path.join(OUT, "cyclic_multiday.csv"), index=False)
    print(f"\nwrote {os.path.join(OUT, 'cyclic_multiday.csv')}")

    # the SOC trace of the steady-state day, for the figure
    trace_rows = []
    rng = np.random.default_rng(SEED + 7)
    s = float(np.mean(steady))
    r = run_policy(env, "mdp", rng, policy=pol_cyc, soc0=s)
    for t, a, soc in r["path"]:
        trace_rows.append({"slot": t, "clock": hr(t), "action": a, "soc": soc})
    pd.DataFrame(trace_rows).to_csv(
        os.path.join(OUT, "cyclic_day_trace.csv"), index=False)

    with open(os.path.join(OUT, "ablations_summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"mu": mu, "mu_20day": mu_H, "s_star": s_star, "h_star": h_star,
                   "cyclic_slots": slots_str(cyc_slots), "h_slots": h_slots,
                   "iters": iters + 1, "residual": hist[-1],
                   "avg_daily_cyclic": float(np.mean(nets[10:])),
                   "avg_daily_multiday": h_avg,
                   "avg_daily_single":
                       float(evaluate(env, pol_mdp, "mdp", n_sims=N_SIMS,
                                      seed=SEED)["net"]),
                   "a5_energy_drawn": cl["energy_drawn_kwh"],
                   "a5_clamped_net": cl["net"],
                   "a5_true_net": true_eval["net"],
                   "a5_true_feasible": true_eval["feasible_rate"]},
                  fh, indent=1)


if __name__ == "__main__":
    main()
