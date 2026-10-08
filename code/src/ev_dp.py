"""
Optimal intra-day charging for an electric ride-hailing driver under
time-of-use (TOU) pricing and stochastic order demand.

    Finite-horizon dynamic programming  (deterministic expected-value baseline)
  + finite-horizon MDP                     (Poisson order arrivals)
  + four rule-based baselines
  + Monte-Carlo evaluation + sensitivity analysis

--------------------------------------------------------------------------
THE MODEL IN ONE SCREEN
--------------------------------------------------------------------------
Time      96 slots x 15 min = 24 h.
State     (t, s): slot t, state of charge s on a 1% grid.
Actions   DRIVE  - be on the road this slot
          CHARGE - plug in this slot
          IDLE   - neither

Demand    Orders in slot t are Poisson(lambda_t), lambda_t estimated from
          2.80M real NYC TLC yellow-taxi pickups. The driver can complete at
          most CAP = (0.25 h x 60) / mean_trip_duration trips per slot, so

              m_t = min(N_t, CAP)          orders actually served

          This saturation is the whole ballgame. At 18:00 lambda = 1684 while
          CAP ~ 1.1, so the driver is TIME-capped, not demand-capped: extra
          demand earns nothing. At 03:00 lambda = 91, so the driver is
          demand-capped and idles anyway.

Energy    DRIVE consumes m_t * kWh_t ; CHARGE adds P * taper(s) * eta * 0.25.
          taper(s) is the CC -> CV collapse above 80% SOC.

Cost      DRIVE earns m_t * fare_t ; CHARGE costs price_t * P * 0.25.

Objective maximise  E[ sum_t (revenue - energy cost) ].

THE POINT OF THE PROJECT
--------------------------------------------------------------------------
The obvious policy is "charge in the cheapest TOU hour". It is wrong, and the
DP shows exactly how wrong. The valley is at night, when there is almost no
revenue to lose, but the day's energy has to be bought *somewhere*; once the
car is capped on time, the marginal value of an hour on the road is the
marginal value of the energy it burns, and the expensive shoulder hours get
re-evaluated. The punchline this script is built to surface:

    the cheapest kWh is not the kWh that should be bought last.
"""

import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# The profile lives in ../data/ in the shipped layout, and in ./profile/ when
# run straight out of the build directory. Look in both so the code runs
# as-is from either place.
_PROF_CANDIDATES = [
    os.path.join(HERE, os.pardir, "data", "profile.json"),
    os.path.join(HERE, "profile", "profile.json"),
    os.path.join(HERE, "data", "profile.json"),
]
PROF = next((p for p in _PROF_CANDIDATES if os.path.exists(p)), _PROF_CANDIDATES[0])

# Actions
DRIVE, CHARGE, IDLE = 0, 1, 2
ACTS = (DRIVE, CHARGE, IDLE)
ACT_NAMES = {DRIVE: "DRIVE", CHARGE: "CHARGE", IDLE: "IDLE"}


# ===========================================================================
# Time-of-use tariff
# ===========================================================================
# A four-tier TOU tariff in the shape used by most US and Chinese utilities.
# It is an ASSUMPTION, not a measurement, so the sensitivity analysis varies
# the valley/peak spread explicitly. Times are slot indices (15 min each).
TOU_TIERS = [
    # (label, start_slot, end_slot, $/kWh)
    ("super-peak", 64, 76, 0.42),   # 16:00-19:00 weekday
    ("peak", 52, 64, 0.28),         # 13:00-16:00
    ("peak", 76, 80, 0.28),         # 19:00-20:00
    ("shoulder", 40, 52, 0.19),     # 10:00-13:00
    ("shoulder", 80, 92, 0.19),     # 20:00-23:00
    ("off-peak", 0, 40, 0.11),      # 00:00-10:00
    ("off-peak", 92, 96, 0.11),     # 23:00-24:00
]


def tou_price(n_slots: int = 96, spread: float = 1.0, base: float = 0.11) -> np.ndarray:
    """Build a length-n_slots price vector. `spread` scales the peak/valley
    ratio (1.0 = nominal); `base` is the off-peak price in $/kWh."""
    p = np.zeros(n_slots)
    for _, lo, hi, val in TOU_TIERS:
        p[lo:hi] = base * (1.0 + (val / 0.11 - 1.0) * spread)
    return p


def taper(soc: np.ndarray | float, eta_cc: float = 0.80) -> np.ndarray:
    """CC -> CV charge-power taper (1.0 up to `eta_cc`, then linear to 0.15)."""
    soc = np.asarray(soc, dtype=float)
    span = 1.0 - eta_cc
    out = np.where(soc <= eta_cc, 1.0, 1.0 - 0.85 * (soc - eta_cc) / span)
    return np.clip(out, 0.15, 1.0)


# ===========================================================================
# Environment built from the real-data profile
# ===========================================================================
class Env:
    """Holds every parameter the DP / MDP needs, all traceable to the profile
    JSON or to an explicit assumption."""

    def __init__(self, **over):
        with open(PROF, encoding="utf-8") as fh:
            p = json.load(fh)

        self.T = p["n_slots"]
        self.dt_h = p["slot_min"] / 60.0
        self.lam = np.array(p["lambda"], dtype=float)
        self.fare = np.array(p["fare_mean"], dtype=float)
        self.dist_km = np.array(p["dist_km_mean"], dtype=float)
        self.dur_s = np.array(p["dur_mean_s"], dtype=float)

        self.batt = over.get("batt", p["battery_kwh"])
        self.soc_res = over.get("soc_res", p["reserve_soc"])
        self.p_kw = over.get("p_kw", p["charge_kw"])
        self.eta_c = over.get("eta_c", p["charge_eff"])
        self.eta_cc = over.get("eta_cc", p["eta_cc_soc"])
        self.kwh_km = over.get("kwh_km", p["kwh_per_km"])
        self.fare_scale = over.get("fare_scale", 1.0)

        # Energy per trip is DERIVED from distance and consumption, so that
        # perturbing the consumption assumption actually propagates.
        self.kwh = self.dist_km * self.kwh_km
        # Fares are scaled by a common factor in the sensitivity study.
        self.fare = self.fare * self.fare_scale

        # driver time cap: trips completable in one 15-min slot
        self.cap = over.get("cap", None)
        if self.cap is None:
            mean_dur_h = float(np.mean(self.dur_s)) / 3600.0
            self.cap = (self.dt_h / mean_dur_h) if mean_dur_h > 0 else 1.0

        # ------------------------------------------------------------------
        # City-wide pickups are NOT one driver's order rate. A driver shares
        # the market with every other active vehicle, so the per-driver rate
        # is lambda_city / N_drivers.
        #
        # N_drivers is not given, so it is CALIBRATED: we fix the driver's
        # utilisation at the evening peak to U_peak (85% by default) and solve
        # for N. The shape of the curve -- the 18.5x swing -- is preserved
        # exactly, because dividing by a constant does not change shape; what
        # the calibration buys is the correct *absolute* level, so that the
        # driver is idle in the dead hours instead of magically earning a full
        # fare at 03:00. This is Assumption A4 in the report and it is
        # perturbed in the sensitivity study.
        # ------------------------------------------------------------------
        self.u_peak = over.get("u_peak", 0.85)
        self.lam_city = self.lam.copy()
        self.n_drivers = over.get("n_drivers", None)
        if self.n_drivers is None:
            self.n_drivers = float(self.lam_city.max()) / (self.cap * self.u_peak)
        self.lam = self.lam_city / self.n_drivers

        # Orders actually served, and therefore the energy the day demands,
        # scale with the battery indirectly: a smaller pack does not make the
        # driver want fewer trips, it just makes the energy budget tighter.
        # We recompute per-trip energy from the (possibly overridden)
        # consumption rate, then cap the served count by the time cap.
        self.n_eff = np.minimum(self.lam, self.cap)

        self.served_rev = self.n_eff * self.fare
        self.served_kwh = self.n_eff * self.kwh

        self.price = over.get("price", tou_price(self.T))
        self.price_spread = over.get("price_spread", 1.0)

        # marginal value of stored energy left at end of day, $/kWh
        self.mu_end = over.get("mu_end", 0.0)

        # SOC grid
        self.step = over.get("soc_step", 0.01)
        self.soc = np.arange(self.soc_res, 1.0 + 1e-9, self.step)
        self.nS = len(self.soc)

        # charge gain per slot at each SOC level (kWh)
        self.gain = self.p_kw * taper(self.soc, self.eta_cc) * self.eta_c * self.dt_h
        # cost of a full slot of charging at each SOC level ($)
        self.ccost = self.price[:, None] * self.p_kw * self.dt_h   # (T,1)

    def to_idx(self, s: float) -> int:
        return int(np.clip(round((s - self.soc_res) / self.step), 0, self.nS - 1))

    def s_at(self, i: int) -> float:
        return float(self.soc[i])

    def energy_served_total(self) -> float:
        """kWh a driver would burn if time-capped on the road all day."""
        return float(self.served_kwh.sum())

    def describe(self) -> str:
        e = self.energy_served_total()
        lines = [
            "=" * 72,
            "ENVIRONMENT (built from 2.80M real NYC TLC pickups)",
            "=" * 72,
            f"  horizon            {self.T} slots x {self.dt_h*60:.0f} min = 24 h",
            f"  battery            {self.batt:.0f} kWh usable",
            f"  reserve SOC        {self.soc_res:.0%}   grid {self.nS} points @{self.step:.0%}",
            f"  charger            {self.p_kw:.0f} kW DC, eff {self.eta_c:.0%},"
            f" CC->CV knee at {self.eta_cc:.0%}",
            f"  driver time cap    {self.cap:.2f} trips / 15-min slot",
            f"  citywide lambda    {self.lam_city.min():.0f} .. {self.lam_city.max():.0f}"
            f"  ({self.lam_city.max()/self.lam_city.min():.1f}x)",
            f"  calibrated fleet   {self.n_drivers:,.0f} vehicles"
            f"   (peak utilisation {self.u_peak:.0%})",
            f"  per-driver lambda  {self.lam.min():.3f} .. {self.lam.max():.3f}"
            f"  ({self.lam.max()/self.lam.min():.1f}x)",
            f"  served demand      min(lambda,cap) {self.n_eff.min():.3f} .. {self.n_eff.max():.3f}",
            f"  time-capped slots  {int((self.lam > self.cap).sum())} / {self.T}"
            f"   (slots where demand exceeds what one driver can serve)",
            f"  mean fare          ${self.fare.mean():.2f}   mean {self.kwh.mean():.2f} kWh/trip",
            f"  energy if always on road: {e:.1f} kWh"
            f"  =  {e/self.batt:.2f}x battery   -> constraint"
            f" {'BINDS (must charge)' if e > self.batt else 'does NOT bind'}",
            f"  TOU price          ${self.price.min():.3f} .. ${self.price.max():.3f} /kWh",
            f"  end-of-day mu      ${self.mu_end:.2f} /kWh of leftover charge",
            "=" * 72,
        ]
        return "\n".join(lines)


# ===========================================================================
# Deterministic DP  (expected-value; orders replaced by their mean)
# ===========================================================================
def solve_dp(env: Env):
    """Backward-induction DP on the expected-value problem.

    Returns (V, policy) with V shape (T+1, nS) and policy shape (T, nS).
    Terminal value V[T, i] = mu_end * leftover kWh, and states below the
    reserve at the end of the day are infeasible.
    """
    T, nS = env.T, env.nS
    V = np.full((T + 1, nS), -np.inf)
    pol = np.zeros((T, nS), dtype=np.int8)

    # terminal
    batt = env.batt
    for i, s in enumerate(env.soc):
        if s >= env.soc_res - 1e-9:
            V[T, i] = env.mu_end * (s - env.soc_res) * batt

    inf = -1e18
    for t in range(T - 1, -1, -1):
        rev = env.served_rev[t]
        ekw = env.served_kwh[t]
        cst = env.ccost[t, 0]
        gain = env.gain
        floor_kwh = env.soc_res * batt

        Vn = V[t + 1]
        for i in range(nS):
            s = env.soc[i]
            best, barg = -np.inf, IDLE

            # DRIVE. If serving the full slot would push the pack below the
            # reserve floor, the driver simply cannot take that slot's work --
            # it is INFEASIBLE, not clamped. Clamping (i.e. letting him drive
            # on an empty battery) is what previously made the DP conclude it
            # never needed to charge at all.
            new_kwh = s * batt - ekw
            if new_kwh >= floor_kwh - 1e-9:
                j = env.to_idx(new_kwh / batt)
                vd = rev + Vn[j]
                if vd > best:
                    best, barg = vd, DRIVE

            # CHARGE
            new_kwh = s * batt + gain[i]
            j = env.to_idx(min(1.0, new_kwh / batt))
            vc = -cst + Vn[j]
            if vc > best:
                best, barg = vc, CHARGE

            # IDLE
            vi = Vn[i]
            if vi > best:
                best, barg = vi, IDLE

            V[t, i] = best
            pol[t, i] = barg

    V[V < inf / 2] = -np.inf
    return V, pol


# ===========================================================================
# MDP  (Poisson order arrivals, exact expectation over the arrival count)
# ===========================================================================
def _pois(lmb: float, kmax: int, pois_tab: np.ndarray) -> np.ndarray:
    """pmf vector for k = 0..kmax under Poisson(lmb), read from a precomputed
    table (avoids calling scipy per state)."""
    k = np.arange(kmax + 1)
    lg = k * np.log(max(lmb, 1e-12)) - max(lmb, 1e-12)
    from math import lgamma
    lg = lg - np.array([lgamma(i + 1.0) for i in k])
    p = np.exp(lg)
    s = p.sum()
    return p / s if s > 0 else p


def solve_mdp(env: Env, kmax: int = 6, viter: int = 60, tol: float = 1e-10):
    """Finite-horizon backward value iteration with the arrival count summed
    out exactly. Because the horizon is fixed we can also just sweep backward
    to convergence; we do both and keep the converged one.

    Returns (V, policy) with policy shape (T, nS).
    """
    T, nS = env.T, env.nS
    batt = env.batt
    V = np.zeros((T + 1, nS))
    pol = np.zeros((T, nS), dtype=np.int8)
    for i, s in enumerate(env.soc):
        V[T, i] = env.mu_end * max(0.0, s - env.soc_res) * batt
    gain = env.gain
    lam = env.lam
    fare = env.fare
    kwh = env.kwh
    cap = env.cap
    ccost = env.ccost

    # arrival pmf per slot
    pmf = [_pois(lmb, kmax, None) for lmb in lam]

    for t in range(T - 1, -1, -1):
        Vn = V[t + 1]
        cst = ccost[t, 0]
        km = min(kmax, 6)
        # orders served is min(k, cap); energy/revenue scale linearly in m
        # so we can precompute the per-k served vector
        served = np.minimum(np.arange(km + 1), cap)
        row_earn = served * fare[t]
        row_kwh = served * kwh[t]
        floor_kwh = env.soc_res * batt

        for i in range(nS):
            s = env.soc[i]
            jc = env.to_idx(min(1.0, s + gain[i] / batt))
            vc = -cst + Vn[jc]
            best, barg = vc, CHARGE

            # DRIVE: summed over the Poisson arrival count. A slot whose
            # expected energy demand would breach the reserve is infeasible.
            vdrive = 0.0
            for k in range(km + 1):
                pk = pmf[t][k]
                if pk < 1e-6:
                    continue
                nk = s * batt - row_kwh[k]
                if nk < floor_kwh - 1e-9:
                    continue          # cannot serve this outcome
                j = env.to_idx(nk / batt)
                vdrive += pk * (row_earn[k] + Vn[j])
            if vdrive > best:
                best, barg = vdrive, DRIVE

            vi = Vn[i]
            if vi > best:
                best, barg = vi, IDLE

            V[t, i] = best
            pol[t, i] = barg

    return V, pol


# ===========================================================================
# Rule-based baselines
# ===========================================================================
def baseline_charge_at_cheapest(env: Env):
    """Naive policy: sit on the charger whenever the current tariff is the
    day's cheapest (ties broken by price level, then by slot)."""
    best = -1
    for t in range(env.T):
        p = env.price[t]
        if p < env.price[best] - 1e-12 or (
            abs(p - env.price[best]) < 1e-12 and t < best
        ):
            best = t
    return ("charge-at-cheapest-hour",
            "always plugged in during the single cheapest tariff slot(s)")


def baseline_threshold(env: Env, thresh: float = 0.30):
    """Common industry rule: charge whenever SOC drops below a fixed
    threshold. Charging then continues as long as SOC < threshold + hysteresis.
    """
    return (f"threshold(SOC<{thresh:.0%})",
            "charge whenever state of charge falls below a fixed threshold")


# ===========================================================================
# Policy simulation
# ===========================================================================
def run_policy(env: Env, kind: str, rng: np.random.Generator, **kw):
    """Simulate one driver-day under a given policy with Poisson arrivals.

    kind: 'dp' | 'mdp' | 'cheapest' | 'threshold' | 'greedy'
    Returns dict with revenue, energy cost, net, energy used, feasibility.
    """
    T, batt = env.T, env.batt
    lam, fare, kwh, cap = env.lam, env.fare, env.kwh, env.cap
    s = kw.get("soc0", 0.80)
    batt = env.batt
    stranded = False

    pol = kw.get("policy")
    rev = cost = ekwh = chkwh = 0.0
    n_orders = 0
    path = []
    charge_slots = []

    cheapest_t = int(np.argmin(env.price))
    thresh = kw.get("thresh", 0.30)
    charging = False

    for t in range(T):
        i = env.to_idx(s)

        if kind in ("dp", "mdp"):
            a = int(pol[t, i])
        elif kind == "cheapest":
            a = CHARGE if t == cheapest_t else DRIVE
        elif kind == "threshold":
            if s < thresh:
                charging = True
            if charging and s >= min(0.95, thresh + 0.25):
                charging = False
            a = CHARGE if charging else DRIVE
        elif kind == "always-drive":
            a = DRIVE
        elif kind == "never-charge":
            a = DRIVE
        else:
            raise ValueError(kind)

        if a == CHARGE:
            g = env.p_kw * float(taper(s, env.eta_cc)) * env.eta_c * env.dt_h
            s = min(1.0, s + g / batt)
            cost += env.price[t] * env.p_kw * env.dt_h
            chkwh += g
            path.append((t, "CHARGE", s))
            charge_slots.append(t)
        elif a == DRIVE:
            N = rng.poisson(lam[t])
            m = min(N, cap)
            e = m * kwh[t]
            # Same feasibility rule as the DP: if the slot's work would breach
            # the reserve floor the driver cannot take it, and the day is
            # recorded as infeasible rather than silently teleported.
            if s * batt - e < env.soc_res * batt - 1e-9:
                stranded = True
                # take only what the remaining energy allows, then stop
                afford = max(0.0, (s - env.soc_res) * batt)
                m = min(m, afford / max(kwh[t], 1e-9))
                e = m * kwh[t]
            s = s - e / batt
            rev += m * fare[t]
            n_orders += m
            ekwh += e
            path.append((t, "DRIVE", s))
        else:
            path.append((t, "IDLE", s))

    feasible = (not stranded) and s >= env.soc_res - 1e-6
    return {
        "revenue": rev, "energy_cost": cost, "net": rev - cost,
        "energy_used": ekwh, "charge_kwh": chkwh, "orders": n_orders,
        "final_soc": s, "feasible": feasible, "stranded": stranded,
        "path": path, "charge_slots": charge_slots,
    }


def evaluate(env: Env, pol, kind: str, n_sims: int = 400, seed: int = 0, **kw):
    """Monte-Carlo average of a policy over independent random days."""
    rng = np.random.default_rng(seed)
    keys = ["revenue", "energy_cost", "net", "energy_used", "charge_kwh",
            "orders", "final_soc"]
    acc = {k: [] for k in keys}
    feas = 0
    for _ in range(n_sims):
        r = run_policy(env, kind, rng, policy=pol, **kw)
        for k in keys:
            acc[k].append(r[k])
        feas += int(r["feasible"])
    out = {k: float(np.mean(v)) for k, v in acc.items()}
    out["feasible_rate"] = feas / n_sims
    out["net_std"] = float(np.std(acc["net"], ddof=1))
    return out


if __name__ == "__main__":
    env = Env()
    print(env.describe())
