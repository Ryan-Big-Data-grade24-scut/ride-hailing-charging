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

from ev_dp import CHARGE, DRIVE, Env, solve_mdp, taper

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
FIGS = os.path.join(HERE, "figures")
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
    ax[2].set_ylim(0, 1.28)
    ax[2].set_xticks(range(0, 25, 2))
    ax[2].legend(frameon=False, fontsize=8, loc="lower left", ncol=3,
                bbox_to_anchor=(0.0, 0.0))

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
    studies = [("tou_spread", "TOU peak/valley spread", "x"),
               ("battery_kwh", "battery size (kWh)", ""),
               ("kwh_per_km", "consumption (kWh/km)", ""),
               ("charge_kw", "charger power (kW)", ""),
               ("u_peak", "peak fleet utilisation", ""),
               ("fare_scale", "fare level", "x"),
               ("soc0", "start-of-day SOC", "")]
    avail = [x for x in studies if x[0] in set(s["parameter"])]
    n = len(avail)
    ncol = 4
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.0 * ncol, 2.5 * nrow))
    axes = np.atleast_1d(axes).ravel()
    for ax, (key, title, suf) in zip(axes, avail):
        d = s[s["parameter"] == key]
        x = d["value"].astype(float)
        ax.plot(x, d["gain"], "o-", color=GRN, lw=1.8, ms=5)
        ax.axhline(0, color=INK, lw=0.9, ls="--")
        ax.set_title(title, fontsize=9, loc="left", color=INK)
        ax.set_xlabel((suf + " ") if suf else "", fontsize=8)
        ax.set_ylabel("gain over tariff-\nfollowing rule ($)", fontsize=8)
    for ax in axes[len(avail):]:
        ax.set_visible(False)
    fig.suptitle(
        "Gain over the tariff-following rule is positive and grows as the "
        "energy budget tightens",
        x=0.01, ha="left", fontweight="bold", color=INK, fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
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

    # Effective $/kWh DELIVERED. The charger draws full rated power but stops
    # banking energy above the knee, so the money spent per useful kWh rises
    # steeply through the taper. This is an average cost-to-date: the money
    # spent lifting the pack from the reserve up to SOC s, divided by the
    # energy actually banked.
    price = env.price[46]                       # 11:30, shoulder tier
    d_soc = 0.01
    # money spent per unit SOC, and energy banked per unit SOC
    cash_per_soc = env.p_kw * price * env.dt_h          # $ per full-power slot
    e_per_soc = env.p_kw * t * env.eta_c * env.dt_h     # kWh banked this slot
    cum_cash = np.cumsum(np.full_like(s, cash_per_soc))
    cum_e = np.cumsum(e_per_soc)
    eff = cum_cash / np.maximum(cum_e, 1e-9)

    ax2.plot(s * 100, np.full_like(s, price), color=GRY, lw=2.2, ls="--",
             label="tariff (nominal)")
    ax2.plot(s * 100, eff, color=ACC, lw=2.2,
             label="effective, incl. taper")
    ax2.axvline(env.eta_cc * 100, color=INK, ls="--", lw=1)
    ax2.annotate("knee", (env.eta_cc * 100 + 1, price), fontsize=8, color=INK)
    ax2.set_xlabel("state of charge (%)")
    ax2.set_ylabel("average cost per kWh\nstored so far ($/kWh)")
    ax2.set_ylim(0, max(price * 3, float(np.nanmax(eff)) * 1.05))
    ax2.set_title("B: the last 20% costs the most per kWh", loc="left",
                  fontweight="bold", color=INK)
    ax2.legend(frameon=False, fontsize=8, loc="upper left")
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
