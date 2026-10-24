"""How often, and when, does the MDP policy actually charge?

`run_experiments.py` reports the charging slots of the *best* of 200
simulated days. That is a punchline, not a statistic: a single lucky day
cannot support a claim like "the optimal policy charges outside the valley".

This script computes the distribution over the full evaluation sample
(the same 600 Monte-Carlo days, same seed) so the claim can be stated as
a frequency rather than as an anecdote.

Writes:
    results/charge_slot_stats.csv   slot -> share of days the policy charges
    results/charge_day_stats.csv    per-day summary rows
"""
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir))
OUT = os.path.join(ROOT, "results")
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8")

from ev_dp import Env, run_policy, solve_mdp

SEED = 20261001
N_SIMS = 600


def hr(t):
    return f"{t * 15 // 60:02d}:{t * 15 % 60:02d}"


def main():
    env = Env()
    _, pol = solve_mdp(env, kmax=6)

    valley = [t for t in range(env.T) if env.price[t] <= env.price.min() + 1e-9]
    valley_set = set(valley)

    rng = np.random.default_rng(SEED)
    slot_counts = Counter()
    per_day = []
    n_off = 0
    n_valley_only = 0

    for d in range(N_SIMS):
        r = run_policy(env, "mdp", rng, policy=pol)
        ch = list(r["charge_slots"])
        slot_counts.update(ch)
        off = [t for t in ch if t not in valley_set]
        if off:
            n_off += 1
        if ch and not off:
            n_valley_only += 1
        per_day.append({
            "day": d,
            "net": r["net"],
            "feasible": bool(r["feasible"]),
            "n_charge_slots": len(ch),
            "charge_slots": ",".join(hr(t) for t in ch),
            "n_off_valley": len(off),
            "off_valley_slots": ",".join(hr(t) for t in off),
            "final_soc": r["final_soc"],
        })

    per_day_df = pd.DataFrame(per_day)
    per_day_df.to_csv(os.path.join(OUT, "charge_day_stats.csv"), index=False)

    slot_df = pd.DataFrame(
        [{"clock": hr(t), "slot": t,
          "share_of_days": slot_counts[t] / N_SIMS,
          "in_valley": t in valley_set}
         for t in sorted(slot_counts)],
    )
    slot_df.to_csv(os.path.join(OUT, "charge_slot_stats.csv"), index=False)

    feasible = per_day_df[per_day_df["feasible"]]
    nf = len(feasible)

    # Count the two kinds of day over the FEASIBLE days only. Counting the
    # numerator over all 600 days while dividing by the 570 feasible ones
    # silently inflates both shares (it used to report 76.3% / 28.9%).
    off_feasible = int((feasible["n_off_valley"] > 0).sum())
    valley_only_feasible = int(
        ((feasible["n_off_valley"] == 0) & (feasible["n_charge_slots"] > 0)).sum())

    print("=" * 72)
    print("MDP policy: charging behaviour over {} Monte-Carlo days".format(N_SIMS))
    print("=" * 72)
    print(f"  feasible days                  : {nf} / {N_SIMS}")
    print(f"  days charging OUTSIDE the valley: {off_feasible} / {nf}"
          f"  ({off_feasible / max(nf, 1):.1%} of feasible days)")
    print(f"  days charging ONLY in the valley: {valley_only_feasible} / {nf}"
          f"  ({valley_only_feasible / max(nf, 1):.1%})")
    print()
    print("  number of charging slots per day:")
    vc = feasible["n_charge_slots"].value_counts().sort_index()
    for k, v in vc.items():
        print(f"    {k} slot(s): {v:4d} days ({v / nf:.1%})")
    print()
    print("  most frequent charging slots (share of ALL days):")
    for _, row in slot_df.sort_values("share_of_days", ascending=False).head(12).iterrows():
        tag = "valley" if row["in_valley"] else "OFF-valley"
        print(f"    {row['clock']}  {row['share_of_days']:6.1%}   [{tag}]")
    print()
    print("  modal charge-slot set:")
    modes = per_day_df["charge_slots"].value_counts()
    for s, c in modes.head(5).items():
        print(f"    {s:34s} {c:4d} days ({c / N_SIMS:.1%})")
    print()
    print(f"wrote {os.path.join(OUT, 'charge_slot_stats.csv')}")
    print(f"wrote {os.path.join(OUT, 'charge_day_stats.csv')}")


if __name__ == "__main__":
    main()
