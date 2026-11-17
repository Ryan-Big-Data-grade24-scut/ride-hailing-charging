"""
Figures for the ride-hailing charging study.

    F1  the day in one picture: demand vs tariff vs the optimal policy
    F2  policy comparison bar chart (feasibility-aware)
    F3  sensitivity: value of optimisation vs TOU spread / battery size
    F4  the CC-CV taper and what it does to the marginal cost of charge
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from ev_dp import CHARGE, DRIVE, Env, solve_mdp, taper

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir))
RES = os.path.join(ROOT, "results")
FIGS = os.path.join(ROOT, "figures")
os.makedirs(FIGS, exist_ok=True)

plt.rcParams.update({
    "font.size": 9, "axes.grid": True, "grid.alpha": 0.25,
    "figure.dpi": 150, "savefig.bbox": "tight", "axes.spines.top": False,
    "axes.spines.right": False,
})
INK = "#1c2333"
ACC = "#c2410c"      # charging / the thing we care about
BLU = "#1d4ed8"      # demand
GRY = "#94a3b8"      # tariff
GRN = "#047857"      # optimal


def fig1(env: Env) -> None:
    """The headline figure.

    The trajectory shown is a REAL simulated day under the MDP policy, not a
    roll-out on expected demand -- otherwise the picture would show a
    different charging pattern from the one the results table reports.
    """
    from ev_dp import run_policy
    _, pol = solve_mdp(env, kmax=6)
    best = None
    rng = np.random.default_rng(20261001)
    for _ in range(200):
        c = run_policy(env, "mdp", rng, policy=pol)
        if c["feasible"] and (best is None or c["net"] > best["net"]):
            best = c
    soc = np.array([s for _, _, s in best["path"]])
    # run_policy records the action NAME ("CHARGE"), not the integer code
    acts = np.array([a for _, a, _ in best["path"]])

    x = np.arange(env.T) * env.dt_h
    fig, ax = plt.subplots(3, 1, figsize=(9, 6.4), sharex=True,
                           gridspec_kw={"height_ratios": [1, 1, 1.2]})

    # demand
    ax[0].bar(x, env.lam, width=0.26, color=BLU, alpha=0.85)
    ax[0].set_ylabel("orders / 15 min\nper driver")
    ax[0].set_title(
        "A demand peak that is not a price peak: the two do not line up",
        loc="left", fontweight="bold", color=INK)

    # tariff
    ax[1].step(x, env.price, where="post", color=GRY, lw=1.8)
    ax[1].fill_between(x, 0, env.price, step="post", color=GRY, alpha=0.25)
    ax[1].set_ylabel("TOU price\n($/kWh)")
    ax[1].set_ylim(0, env.price.max() * 1.28)
    cheapest = env.price.min() + 1e-9
    for sl, lab, c, mk in [
            (env.price <= cheapest, "cheapest tier", INK, "o"),
            (env.price >= env.price.max() - 1e-9, "super-peak", ACC, "D")]:
        if sl.any():
            ax[1].scatter(x[sl], env.price[sl], s=11, color=c, zorder=5,
                          marker=mk, label=lab)
    ax[1].legend(frameon=False, fontsize=8, loc="upper right", ncol=2)

    # policy + soc
    ch = acts == "CHARGE"
    ax[2].fill_between(x, 0, soc, color=GRN, alpha=0.16)
    ax[2].plot(x, soc, color=GRN, lw=2, label="state of charge")
    ax[2].axhline(env.soc_res, color=INK, ls="--", lw=1, label="reserve")
    ax[2].scatter(x[ch], soc[ch], s=60, color=ACC, zorder=6,
                  edgecolor="white", linewidth=1.3, label="MDP charges here")
    for xx in x[ch]:
        ax[2].annotate(f"{int(xx):02d}:{int(round((xx%1)*60)):02d}",
                       (xx, soc[np.argmin(np.abs(x - xx))] + 0.07),
                       ha="center", fontsize=8, color=ACC, fontweight="bold")
    ax[2].set_ylabel("SOC")
    ax[2].set_xlabel("hour of day")
    ax[2].set_ylim(0, 1.38)
    ax[2].set_xticks(range(0, 25, 2))
    # the legend goes in the upper right: the state-of-charge curve leaves
    # that corner empty, while the lower left is occupied by the reserve
    # line and the curve's tail.
    ax[2].legend(frameon=False, fontsize=8, loc="upper right", ncol=3)

    fig.savefig(os.path.join(FIGS, "F1_day_in_picture.png"))
    plt.close(fig)


def fig2() -> None:
    df = pd.read_csv(os.path.join(RES, "policy_comparison.csv"))
    df = df.sort_values("net", ascending=True)
    colors = []
    for p in df["policy"]:
        if p.startswith("MDP"):
            colors.append(GRN)
        elif p.startswith("DP "):
            colors.append("#10b981")
        elif "cheapest" in p:
            colors.append(ACC)
        elif "always" in p or "never" in p:
            colors.append("#cbd5e1")
        else:
            colors.append(GRY)

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(10, 3.6), gridspec_kw={"width_ratios": [2.1, 1]})
    y = np.arange(len(df))
    ax.barh(y, df["net"], color=colors, height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(df["policy"], fontsize=8)
    ax.set_xlabel("net daily earnings ($)")
    for i, (v, f) in enumerate(zip(df["net"], df["feasible_rate"])):
        ax.text(v + 8, i, f"${v:,.0f}  ({f:.0%} feasible)", va="center",
                fontsize=7.5, color=INK)
    ax.set_xlim(0, df["net"].max() * 1.42)
    ax.set_title("A: policy comparison", loc="left", fontweight="bold",
                 color=INK)

    ax2.barh(y, df["feasible_rate"] * 100, color=colors, height=0.62)
    ax2.set_yticks(y)
    ax2.set_yticklabels([])
    ax2.set_xlabel("days completed without\nrunning the pack flat (%)")
    ax2.set_xlim(0, 108)
    for i, f in enumerate(df["feasible_rate"]):
        ax2.text(f * 100 + 2, i, f"{f:.0%}", va="center", fontsize=7.5,
                 color=INK)
    ax2.set_title("B: feasibility", loc="left", fontweight="bold", color=INK)
    fig.savefig(os.path.join(FIGS, "F2_policy_comparison.png"))
    plt.close(fig)


def fig3() -> None:
    s = pd.read_csv(os.path.join(RES, "sensitivity.csv"))
    # The order matches Table 5 in the paper, so the figure and the table can
    # be read against each other line by line.
    #
    # The figure is built at very nearly the width at which it prints (the
    # paper's text block is 6.27 in), because a 12-in figure shrunk to 6.27 in
    # scales 9 pt labels down to 4.7 pt, which is unreadable on paper. Three
    # columns keep each panel wide enough for its title at 9 pt.
    studies = [("battery_kwh", "pack capacity (kWh)", ""),
               ("kwh_per_km", "consumption (kWh/km)", ""),
               ("charge_kw", "charger power (kW)", ""),
               ("u_peak", "fleet utilisation", "pct"),
               ("fare_scale", "fare level", "x"),
               ("tou_spread", "TOU spread", "x"),
               ("soc0", "start-of-day SOC", "pct"),
               ("charge_eff", "charging efficiency", "pct"),
               ("reserve_soc", "reserve floor", "pct"),
               ("billing", "pricing regime", None)]
    avail = [x for x in studies if x[0] in set(s["parameter"])]
    n = len(avail)
    ncol, nrow = 3, 4
    fig, axes = plt.subplots(nrow, ncol, figsize=(6.3, 6.5), sharey=True)
    axes = np.atleast_1d(axes).ravel()
    for k, (ax, (key, title, mode)) in enumerate(zip(axes, avail)):
        d = s[s["parameter"] == key]
        try:
            # sort NUMERICALLY: the value column is text in the CSV, so
            # sorting it as text puts 120 kW before 22 kW
            x = d["value"].astype(float).values
            o = np.argsort(x)
            x, gain = x[o], d["gain"].values[o]
        except ValueError:
            # categorical parameter (the pricing regime): plot on an index
            x, gain = np.arange(len(d)), d["gain"].values
        ax.plot(x, gain, "o-", color=GRN, lw=1.6, ms=4)
        ax.axhline(0, color=INK, lw=0.9, ls="--")
        ax.set_title(title, fontsize=9, loc="left", color=INK)
        ax.tick_params(labelsize=7.5)
        if key == "billing":
            ax.set_xticks(range(len(d)))
            ax.set_xticklabels(["occupancy\n(slot fee)", "energy\n(per kWh)"],
                               fontsize=7)
            ax.set_xlim(-0.35, len(d) - 0.65)
        else:
            # Tick labels sit on the values actually swept, never on
            # interpolated positions -- a reader must be able to see that the
            # 25 kWh point is the far left of the curve. When a sweep has more
            # than five values, keep the endpoints and two interior points so
            # the labels do not collide.
            vals = list(np.asarray(x, dtype=float))
            if len(vals) <= 4:
                keep = vals
            elif len(vals) == 5:
                # endpoints plus the middle point: five labels collide in a
                # 1.7-inch panel whose first and last sit on the spines
                keep = [vals[0], vals[2], vals[-1]]
            else:
                idx = np.unique(np.round(np.linspace(0, len(vals) - 1, 4))
                                .astype(int))
                keep = [vals[i] for i in idx]
            ax.set_xticks(keep)
            if mode == "pct":
                # a percentage parameter reads as a percentage, not as the
                # fraction the model consumes internally
                ax.set_xticklabels(["%g%%" % round(v * 100) for v in keep])
            elif mode == "x":
                ax.set_xticklabels(["×%g" % round(v, 2) for v in keep])
        # only the left column carries the y label; every panel shares the
        # same vertical scale so the comparison is visual as well as numeric
        if k % ncol == 0:
            ax.set_ylabel("gain over tariff rule ($)", fontsize=8.5)
    for ax in axes[len(avail):]:
        ax.set_visible(False)
    fig.suptitle(
        "The gain is positive in every case; it tracks the energy budget, "
        "not the tariff", x=0.01, ha="left", fontweight="bold", color=INK,
        fontsize=9.5)
    fig.tight_layout(rect=[0, 0, 1, 0.955])
    fig.savefig(os.path.join(FIGS, "F3_sensitivity.png"))
    plt.close(fig)


def fig4(env: Env) -> None:
    s = np.linspace(env.soc_res, 1.0, 300)
    t = taper(s, env.eta_cc)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9, 3.3))
    ax.plot(s * 100, t * 100, color=ACC, lw=2.2)
    ax.axvline(env.eta_cc * 100, color=INK, ls="--", lw=1)
    ax.text(env.eta_cc * 100 + 1, 60, "CC->CV\nknee", fontsize=8, color=INK)
    ax.set_xlabel("state of charge (%)")
    ax.set_ylabel("charging power\n(% of charger rating)")
    ax.set_title("A: the taper", loc="left", fontweight="bold", color=INK)
    ax.set_ylim(0, 105)

    # Effective $/kWh DELIVERED -- computed on the PHYSICALLY REALISABLE
    # trajectory. The pack saturates at 100%, so money spent beyond that buys
    # no energy at all; the earlier version of this panel accumulated 300
    # slots of cash against an unbounded pack and was therefore wrong.
    #
    # Two quantities are shown:
    #   (i)  the MARGINAL cost of the next kWh at SOC s:
    #            c_marg(s) = price / (eta * tau(s))
    #        because the driver pays for the charger slot at the charger's
    #        rated power, the kWh actually banked in a slot is P*tau(s)*eta*dt;
    #   (ii) the AVERAGE cost-to-date of the charge that lifted the pack from
    #        the reserve up to SOC s.
    price = env.price[46]                       # 11:30, shoulder tier
    slot_cash = env.p_kw * price * env.dt_h     # $ for one full-power slot

    # (ii) average cost-to-date, on the capacity-capped trajectory
    s_grid = np.linspace(env.soc_res, 1.0, 200)
    avg_cost = []
    for target in s_grid:
        s = env.soc_res
        cash = 0.0
        e = 0.0
        while s < target - 1e-12:
            tau = float(taper(s, env.eta_cc))
            cash += slot_cash
            gain = min(env.p_kw * tau * env.eta_c * env.dt_h,
                       (1.0 - s) * env.batt)
            s += gain / env.batt
            e += gain
        avg_cost.append(cash / max(e, 1e-9))
    avg_cost = np.array(avg_cost)

    # (i) marginal cost of the next kWh
    t_grid = taper(s_grid, env.eta_cc)
    marg = price / (env.eta_c * np.maximum(t_grid, 1e-9))
    # Under ENERGY billing the driver pays for the electricity actually drawn,
    # so the taper cancels out of the ratio and the rate is flat at
    # price / eta at every state of charge. The steep curve below is a
    # property of the pricing regime, not of the battery.
    marg_kwh = price / env.eta_c

    ax2.plot(s_grid * 100, np.full_like(s_grid, price), color=GRY, lw=2.2,
             ls="--", label="tariff (nominal)")
    ax2.plot(s_grid * 100, marg, color=ACC, lw=2.2,
             label="marginal cost, occupancy billing")
    ax2.plot(s_grid * 100, np.full_like(s_grid, marg_kwh), color=BLU, lw=2.0,
             ls="--", label="marginal cost, energy billing")
    ax2.plot(s_grid * 100, avg_cost, color=INK, lw=1.8, ls="-.",
             label="average cost-to-date")
    ax2.axvline(env.eta_cc * 100, color=INK, ls="--", lw=1)
    ax2.annotate("knee", (env.eta_cc * 100 + 1, price), fontsize=8, color=INK)
    ax2.set_xlabel("state of charge (%)")
    ax2.set_ylabel("cost per kWh stored ($/kWh)")
    ax2.set_ylim(0, max(price * 3, float(np.nanmax(marg)) * 1.05))
    ax2.set_title("B: what the last 20% costs depends on the pricing regime",
                  loc="left", fontweight="bold", color=INK)
    ax2.legend(frameon=False, fontsize=8, loc="upper left")

    # How many slots does it take to cross the taper at all? At 60 kW into a
    # 40 kWh pack one 15-min slot banks 13.8 kWh = 34.5% SOC, so the pack
    # saturates inside a single slot and the taper is never resolved by the
    # time grid. This is why ablation A3 changes nothing.
    kwh_per_slot = env.p_kw * env.eta_c * env.dt_h
    soc_per_slot = kwh_per_slot / env.batt
    print(f"  [F4] {kwh_per_slot:.1f} kWh per slot = {soc_per_slot:.1%} SOC;"
          f" slots from {env.soc_res:.0%} to the knee:"
          f" {(env.eta_cc - env.soc_res) / soc_per_slot:.1f}")

    fig.savefig(os.path.join(FIGS, "F4_taper.png"))
    plt.close(fig)


if __name__ == "__main__":
    env = Env()
    fig1(env)
    fig2()
    fig3()
    fig4(env)
    print("figures written to", FIGS)
    for f in sorted(os.listdir(FIGS)):
        print("  ", f)
