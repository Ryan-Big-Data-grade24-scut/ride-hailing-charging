"""
Figure F5 for the v3 extension: what the charging queue costs.

    F5  the queue sweep -- net earnings and feasibility against the queue
        level, for the 2024 hardware (where the queue bites) and the 2026
        hardware (where it does not)

Run:  python make_figures3.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
ACC = "#c2410c"
BLU = "#1d4ed8"
GRY = "#94a3b8"
GRN = "#047857"

SHAPES = ["uniform", "demand", "idle", "meal"]
COLORS = {"uniform": ACC, "demand": BLU, "idle": GRN, "meal": "#a21caf"}


def fig5() -> None:
    df = pd.read_csv(os.path.join(RES, "v3_queue_sweep.csv"))

    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.5))

    # ---- panel 1: the 2024 hardware, where the queue bites ---------------
    ax = axes[0]
    d = df[df["calibration"] == "v2-2024"]
    for sh in SHAPES:
        s = d[d["shape"] == sh].sort_values("queue_peak_h")
        ax.plot(s["queue_peak_h"], s["net"], "-o", color=COLORS[sh],
                label=sh, ms=4, lw=1.6)
    base = d[d["queue_peak_h"] == 0.0]["net"].mean()
    ax.axhline(base, color=GRY, lw=1, ls=":")
    ax.annotate(f"no queue: ${base:,.0f}", xy=(0.02, base), xycoords=("axes fraction", "data"),
                fontsize=8, color=GRY, va="bottom")
    ax.set_title("2024 hardware (40 kWh)\nnet earnings fall as the queue grows",
                 fontsize=9.5)
    ax.set_xlabel("peak queue at the charger (hours)")
    ax.set_ylabel("net earnings (\$/day)")
    ax.set_ylim(bottom=min(d["net"]) - 15)
    ax.legend(frameon=False, fontsize=8, ncol=2)

    # ---- panel 2: the 2026 hardware, where it does not -------------------
    ax = axes[1]
    d = df[df["calibration"] == "2026"]
    for sh in SHAPES:
        s = d[d["shape"] == sh].sort_values("queue_peak_h")
        ax.plot(s["queue_peak_h"], s["net"], "-o", color=COLORS[sh],
                label=sh, ms=4, lw=1.6)
    base = d[d["queue_peak_h"] == 0.0]["net"].mean()
    ax.axhline(base, color=GRY, lw=1, ls=":")
    ax.annotate(f"no queue: ${base:,.0f}", xy=(0.02, base), xycoords=("axes fraction", "data"),
                fontsize=8, color=GRY, va="bottom")
    ax.set_title("2026 hardware (57.6 kWh)\nthe queue is almost free",
                 fontsize=9.5)
    ax.set_xlabel("peak queue at the charger (hours)")
    ax.set_ylim(base - 30, base + 12)

    # ---- panel 3: the mechanism -- off-road time ------------------------
    ax = axes[2]
    d = df[df["calibration"] == "v2-2024"]
    for sh in SHAPES:
        s = d[d["shape"] == sh].sort_values("queue_peak_h")
        ax.plot(s["queue_peak_h"], s["offroad_slots"], "-o", color=COLORS[sh],
                label=sh, ms=4, lw=1.6)
    ax.set_title("the mechanism: time off the road\n(rising, then partly absorbed)",
                 fontsize=9.5)
    ax.set_xlabel("peak queue at the charger (hours)")
    ax.set_ylabel("off-road slots per day (15 min each)")

    fig.suptitle("Figure F5. What the charging queue costs, and when it costs "
                 "anything.", fontsize=10, y=1.02)
    fig.tight_layout()
    out = os.path.join(FIGS, "F5_queue_cost.png")
    fig.savefig(out)
    print("wrote", out)


if __name__ == "__main__":
    fig5()
