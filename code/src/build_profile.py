"""
Build the 15-minute demand / fare / energy profile for one representative
driver-day from REAL NYC TLC yellow-taxi data.

Design note (why this file exists):
    The project question is "when should an EV ride-hailing driver charge?".
    That question is only interesting if the opportunity cost of being off
    the road is real and time-varying. So the order-arrival rate lambda(t),
    the fare distribution and the per-trip energy draw are all ESTIMATED FROM
    DATA, not invented. Everything downstream (DP / MDP) consumes only this
    compact profile, so the stochastic model is a 96-slot Markov decision
    process rather than a simulation over 3M individual trips.

Inputs
    yellow_tripdata_2024-01.parquet   (NYC TLC, public, 2.96M rows)

Outputs (CSV, in ./profile/)
    demand_profile.csv   t, n_pickups, mean_fare, median_fare, mean_dist_km, ...
    profile.json         everything above + the scalar parameters the DP needs
"""

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "yellow_tripdata_2024-01.parquet")
OUT = os.path.join(HERE, "profile")

SLOT_MIN = 15
N_SLOTS = int(24 * 60 / SLOT_MIN)  # 96


# ---------------------------------------------------------------------------
# Vehicle parameters.
#
# These are the standard, publicly documented figures for the short-range EVs
# that dominate the ride-hailing / taxi fleets in China and other Asian
# markets -- the BYD e6 (36.9 kWh) and the Nissan Leaf (40 kWh) class. That
# class is chosen deliberately, not arbitrarily:
#
#   * It is what these fleets actually buy -- they are the cheapest per-kWh
#     cars in the segment, which is exactly why operators buy them, and it is
#     the class where charging intrudes on the working day rather than being
#     handled overnight at a depot.
#   * 40 kWh against a mean 1.27 kWh per trip means roughly 30 usable trips per
#     charge, so a busy 24 h day genuinely cannot be served on one pack. The
#     energy budget BINDS, which is what makes "when should I charge" a real
#     question instead of a trivial one.
#
# The larger long-range packs (60 kWh and up) are exactly the case where the
# naive "charge once overnight" answer is correct, so they would make for a
# boring study. Battery size is varied in the sensitivity analysis.
# ---------------------------------------------------------------------------
BATTERY_KWH = 40.0        # usable pack energy, BYD e6 / Leaf class
RESERVE_SOC = 0.15        # must not be planned below this
KWH_PER_KM = 0.22         # mixed urban duty incl. HVAC, ~ 20-25 kWh/100km
CHARGE_KW = 60.0          # DC fast charger nominal power
CHARGE_EFF = 0.92
ETA_CC_SOC = 0.80         # above this the pack tapers (constant-voltage phase)


def taper(soc: float) -> float:
    """Charge-power taper as a function of SOC (the CC -> CV transition).

    Piecewise, monotone, continuous at the knee: full power up to 80% SOC,
    then it falls off linearly to 15% of nominal at 100% SOC. This single
    nonlinearity is what makes "charge to 100%" a bad idea and is one of the
    two structural features (the other being TOU pricing) that the optimal
    policy has to respect.
    """
    if soc <= ETA_CC_SOC:
        return 1.0
    span = 1.0 - ETA_CC_SOC
    return max(0.15, 1.0 - 0.85 * (soc - ETA_CC_SOC) / span)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)

    print("loading parquet ...", flush=True)
    df = pd.read_parquet(
        DATA,
        columns=[
            "tpep_pickup_datetime",
            "tpep_dropoff_datetime",
            "trip_distance",
            "total_amount",
            "passenger_count",
        ],
    )
    print(f"  raw rows: {len(df):,}", flush=True)

    # --- clean ------------------------------------------------------------
    # Drop the junk rows TLC is known for: zero/negative distance, absurd
    # durations, driver-side data-entry errors, and the ~4.7% of rows that are
    # null across the board.
    n0 = len(df)
    df = df.dropna(subset=["tpep_pickup_datetime", "trip_distance", "total_amount"])
    df = df[(df["trip_distance"] > 0.3) & (df["trip_distance"] < 200)]
    df = df[(df["total_amount"] > 0) & (df["total_amount"] < 500)]
    df = df[df["passenger_count"].fillna(1) > 0]

    dur = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds()
    df = df[(dur > 60) & (dur < 3 * 3600)]
    df = df[df["tpep_pickup_datetime"] >= df["tpep_dropoff_datetime"] - pd.Timedelta(hours=3)]

    df = df.assign(dur_s=dur)
    print(f"  clean rows: {len(df):,}  ({len(df)/n0:.1%} kept)", flush=True)

    # --- time index -------------------------------------------------------
    t0 = df["tpep_pickup_datetime"].min().normalize()
    df["day"] = (df["tpep_pickup_datetime"].dt.normalize() - t0).dt.days
    df["slot"] = (
        df["tpep_pickup_datetime"].dt.hour * 60 + df["tpep_pickup_datetime"].dt.minute
    ) // SLOT_MIN

    # A "day" here is a calendar day; we keep only days whose 24 h window is
    # essentially complete so the 96-slot profile is not biased by partial days.
    counts = df.groupby("day").size()
    full_days = counts[counts > 0.75 * counts.median()].index
    df = df[df["day"].isin(full_days)]
    n_days = df["day"].nunique()
    print(f"  full days kept: {n_days}", flush=True)

    # --- per-slot profile -------------------------------------------------
    g = df.groupby("slot")
    prof = pd.DataFrame(
        {
            "n_pickups": g.size(),
            "mean_fare": g["total_amount"].mean(),
            "median_fare": g["total_amount"].median(),
            "p90_fare": g["total_amount"].quantile(0.90),
            "mean_dist_km": g["trip_distance"].mean() * 1.609344,  # miles -> km
            "mean_dur_s": g["dur_s"].mean(),
            "mean_kwh": g["trip_distance"].mean() * 1.609344 * KWH_PER_KM,
        }
    )
    prof = prof.reindex(range(N_SLOTS)).interpolate(limit_direction="both")
    prof.index.name = "slot"
    prof.to_csv(os.path.join(OUT, "demand_profile.csv"))

    # --- lambdas ----------------------------------------------------------
    # Order arrivals in a 15-min slot are Poisson(lambda_slot). We estimate
    # lambda by pooling ALL full days (not one day) and dividing by n_days, so
    # the profile is not a single noisy day, then floor it at a small value so
    # the policy is defined even in the dead hours.
    lam = prof["n_pickups"].to_numpy() / float(n_days)
    lam = np.maximum(lam, 0.20)

    params = {
        "n_slots": N_SLOTS,
        "slot_min": SLOT_MIN,
        "n_days_used": int(n_days),
        "n_trips_clean": int(len(df)),
        "battery_kwh": BATTERY_KWH,
        "reserve_soc": RESERVE_SOC,
        "kwh_per_km": KWH_PER_KM,
        "charge_kw": CHARGE_KW,
        "charge_eff": CHARGE_EFF,
        "eta_cc_soc": ETA_CC_SOC,
        "lambda": [round(float(x), 4) for x in lam],
        "fare_mean": [round(float(x), 3) for x in prof["mean_fare"].to_numpy()],
        "fare_median": [round(float(x), 3) for x in prof["median_fare"].to_numpy()],
        "fare_p90": [round(float(x), 3) for x in prof["p90_fare"].to_numpy()],
        "kwh_mean": [round(float(x), 4) for x in prof["mean_kwh"].to_numpy()],
        "dur_mean_s": [round(float(x), 1) for x in prof["mean_dur_s"].to_numpy()],
        "dist_km_mean": [round(float(x), 3) for x in prof["mean_dist_km"].to_numpy()],
    }
    with open(os.path.join(OUT, "profile.json"), "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=1)

    # --- console summary --------------------------------------------------
    tot = lam.sum()
    top = np.argsort(lam)[::-1][:8]
    print(f"\n  mean orders/day profile total = {tot:.1f} pickups")
    print(f"  min lambda = {lam.min():.2f}  max lambda = {lam.max():.2f}"
          f"  ratio = {lam.max()/max(lam.min(),1e-9):.1f}x")
    print("\n  busiest slots (slot -> HH:MM, lambda, mean fare):")
    for s in top:
        print(f"    {s:2d}  {s*SLOT_MIN//60:02d}:{s*SLOT_MIN%60:02d}"
              f"   lambda={lam[s]:6.2f}   fare=${prof['mean_fare'].iloc[s]:6.2f}")
    print(f"\n  mean fare overall = ${prof['mean_fare'].mean():.2f},"
          f" mean kWh/trip = {prof['mean_kwh'].mean():.2f}")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
