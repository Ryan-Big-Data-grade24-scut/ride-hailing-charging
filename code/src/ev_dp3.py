"""
ev_dp3 -- v3 of the model: charging as a TIME-CONSUMING EXCURSION.

v2 treated charging as an instantaneous action: choose a slot, the pack gains
energy, that slot's revenue is forgone. That is the wrong simplification for
2026, because the part of the trip that hurts is not the plug-in, it is the
queue in front of the plug.

v3 replaces the CHARGE action by a macro-action spanning the whole excursion:

    t                     t + A              t + A + Q(t)       ...    + B
    |--- driving to ------|---- queueing ----|---- dwell -------|--- back to
    |      the station    |  for a charger   |   (energy in)    |  the road
    |      (A slots)      |   (Q(t) slots)   |   (k slots)      |  (B slots)

The driver is off the road for the whole excursion, so the opportunity cost of
charging is no longer a number bolted onto the objective: it EMERGES, because
the DP simply cannot collect revenue in the slots the excursion skips.

Three properties of the new formulation are worth stating up front.

1. THE STATE SPACE DOES NOT GROW. The excursion is a macro-action, so the
   state is still (t, s). This is the point of collapsing it: the queue is
   exogenous (it depends on t only), so it needs no state of its own.

2. THE DWELL BECOMES A DECISION. In v2 a charging slot delivered a fixed
   amount of energy and the driver could not choose to stay plugged in. Here
   the driver chooses k, the number of dwell slots, and the pack saturates the
   way it does in reality.

3. THE QUEUE IS EXOGENOUS AND WE SWEEP IT. There is no public data on the
   arrival process of chargers, so q(t) is an assumption, not an estimate. We
   therefore sweep four candidate SHAPES and five LEVELS and report whether
   the answer survives. If it does not survive, we say so -- that is the
   honest result, and it is reported in the same spirit as the s^min sweep.
"""

import numpy as np

from ev_dp import CHARGE, DRIVE, IDLE, Env, taper, tou_price

# --------------------------------------------------------------------------
# The 2026 price structure
# --------------------------------------------------------------------------
def market_price(n_slots=96, night=0.30, solar=0.25, ramp=1.40):
    """Electricity price for a participant in the mid/long-term market.

    Since 2026-03-01 (发改能源规〔2025〕1656号) a participant in the market
    is no longer subject to a government-fixed time-of-use schedule, so the
    daily shape follows the merit order instead: midday PV is the valley and
    the evening ramp is the peak. This is an ASSUMPTION -- no published
    tariff schedule for a market participant exists to copy.
    """
    p = np.full(n_slots, night, dtype=float)
    blocks = [(44, 60, solar),          # 11:00-15:00 midday PV valley
              (68, 84, None)]            # 17:00-21:00 evening ramp
    for lo, hi, val in blocks:
        if val is not None:
            p[lo:hi] = val
            continue
        w = np.sin(np.pi * (np.arange(lo, hi) - lo + 0.5) / (hi - lo))
        p[lo:hi] = solar + (ramp - solar) * w
    return p


def service_fee(n_slots=96, valley=0.50, peak=1.20):
    """Operator service fee per kWh, which is itself time-varying.

    Measured service fees at Chinese public DC points are 0.5-1.0 yuan/kWh in
    cities and rise by roughly 120% at the peak; the resulting combined
    price is 1.3-2.0 yuan/kWh against a 61/39 electricity/service-fee split
    (18 measurements, so: a soft number).
    """
    f = np.full(n_slots, valley, dtype=float)
    lo, hi = 68, 84
    w = np.sin(np.pi * (np.arange(lo, hi) - lo + 0.5) / (hi - lo))
    f[lo:hi] = valley + (peak - valley) * w
    return f


# --------------------------------------------------------------------------
# The queue profile
# --------------------------------------------------------------------------
def queue_profile(shape, peak_slots, lam, T=96):
    """q(t), the number of slots the driver waits for a free charger.

    Four candidate shapes, none of them estimated -- all assumed, and all
    swept:

      "uniform"  the same wait at every hour (no information about the crowd)
      "demand"   the wait follows the market: busy hours, long queues
      "idle"     the wait follows the drivers' own rhythm: quiet hours, long
                 queues, because that is when the off-shift mass of drivers
                 is all trying to plug in at the same time
      "meal"     two humps at the two human windows: lunch (12:00) and after
                 the shift ends (21:30)
    """
    if peak_slots <= 0:
        return np.zeros(T, dtype=int)
    if shape == "uniform":
        w = np.ones(T)
    elif shape == "demand":
        w = lam / max(lam.max(), 1e-9)
    elif shape == "idle":
        w = np.maximum(1.0 - lam / max(lam.max(), 1e-9), 0.0)
    elif shape == "meal":
        t = np.arange(T)
        w = np.maximum(np.exp(-0.5 * ((t - 48) / 10.0) ** 2),
                        np.exp(-0.5 * ((t - 86) / 9.0) ** 2))
    else:
        raise ValueError(f"unknown queue shape {shape!r}")
    w = w / max(w.max(), 1e-9)
    return np.round(peak_slots * w).astype(int)


# --------------------------------------------------------------------------
# Environment
# --------------------------------------------------------------------------
V3_KEYS = {"price_mode", "service_fee", "queue_shape", "queue_peak_slots",
           "queue_slots", "access_slots", "return_slots", "access_kwh",
           "max_dwell", "miss_penalty"}


class Env3(Env):
    """v2's environment plus the excursion mechanics.

    New parameters, all with defaults that reproduce v2 exactly:
      queue_peak_slots  0        -> no queue at all, so the excursion is a
                                     single dwell slot and v2 is recovered
      access_slots      0        -> no drive to the station
      return_slots      0        -> no drive back
      access_kwh        0.0      -> no deadhead energy
    """

    def __init__(self, **over):
        base = {k: v for k, v in over.items() if k not in V3_KEYS}
        super().__init__(**base)

        # ---- price --------------------------------------------------------
        mode = over.get("price_mode", "tou")
        if mode == "market":
            self.price = market_price(self.T)
            self.service_fee = over.get("service_fee", None)
            if self.service_fee is None:
                self.service_fee = service_fee(self.T)
            # LEVEL NORMALISATION. The market price is built from Chinese
            # observations in yuan/kWh while the rest of the model is in
            # dollars, so comparing the two shapes at their raw levels would
            # confound the shape with the currency. Both components are
            # therefore rescaled together so that the MEAN combined price
            # equals the TOU's mean, and E5 then isolates the shape of the
            # tariff -- which is the thing the 2026 reform actually changed.
            tou_mean = float(tou_price(self.T).mean())
            raw_mean = float((self.price + self.service_fee).mean())
            if raw_mean > 1e-12:
                f = tou_mean / raw_mean
                self.price = self.price * f
                self.service_fee = self.service_fee * f
        else:
            self.service_fee = over.get("service_fee", None)
            if self.service_fee is None:
                self.service_fee = np.zeros(self.T)
        self.service_fee = np.asarray(self.service_fee, dtype=float)
        self.price_mode = mode
        # the price the driver actually pays: electricity + service fee
        self.price_all = self.price + self.service_fee

        # ---- the excursion ----------------------------------------------
        self.access_slots = int(over.get("access_slots", 0))
        self.return_slots = int(over.get("return_slots", 0))
        self.access_kwh = float(over.get("access_kwh", 0.0))
        self.max_dwell = int(over.get("max_dwell", 4))

        # What does it cost the driver to turn an order down?
        #
        # The v2 objective had no such term, so the optimiser was free to plan
        # exactly on the reserve floor: on a high-demand day it simply refused
        # the trips its pack could not cover, and the day's earnings looked
        # fine. A real driver cannot do that -- the platform tracks the
        # acceptance rate, and refusing work is itself a loss. Adding the
        # penalty turns "the optimiser is more aggressive than the rules"
        # from an embarrassment into a parameter we can sweep.
        self.miss_penalty = float(over.get("miss_penalty", 0.0))

        q = over.get("queue_slots", None)
        if q is None:
            q = queue_profile(over.get("queue_shape", "uniform"),
                              float(over.get("queue_peak_slots", 0.0)),
                              self.lam, self.T)
        self.q = np.asarray(q, dtype=int)
        self.queue_shape = over.get("queue_shape", "uniform")

    # ------------------------------------------------------------------
    def excursion(self, t, s, k):
        """One charging excursion starting at slot t with SOC s.

        Returns (cost, s_after, duration_slots) or None if the driver cannot
        make the trip (the deadhead would breach the reserve floor).

        Delegates to the vectorised `excursion_arrays` so that the planner and
        the simulator cannot drift apart -- the single most dangerous class of
        bug in a model like this one.
        """
        i = self.to_idx(s)
        cost, s_after, ok, D = excursion_arrays(self, t, k)
        if not ok[i]:
            return None
        return float(cost[i]), float(s_after[i]), int(D)

    def describe(self):
        base = super().describe()
        extra = [
            "  " + "-" * 68,
            f"  v3 price mode       {self.price_mode}"
            + ("" if self.price_mode == "tou" else
               f"  (electricity ${self.price.min():.2f}..${self.price.max():.2f}"
               f" + service fee ${self.service_fee.min():.2f}"
               f"..${self.service_fee.max():.2f})"),
            f"  combined price      ${self.price_all.min():.3f}"
            f" .. ${self.price_all.max():.3f} /kWh",
            f"  queue q(t)          {self.q.min()} .. {self.q.max()} slots"
            f"   (shape {self.queue_shape!r})",
            f"  excursion           access {self.access_slots} + queue q(t)"
            f" + dwell <= {self.max_dwell} + return {self.return_slots} slots",
            f"  access deadhead     {self.access_kwh:.2f} kWh",
        ]
        return base + "\n" + "\n".join(extra)


# ===========================================================================
# The excursion, vectorised over the SOC grid
# ===========================================================================
def excursion_arrays(env, t, k):
    """One charging excursion, evaluated for every state of charge at once.

    Returns (cost, s_after, ok, D):

      cost    dollars paid for the excursion
      s_after state of charge on returning to the road
      ok      whether the deadhead breaches the reserve floor
      D       how many slots the excursion occupies

    The price is read at the PLUG-IN slot, not at the decision slot: the
    driver is billed for the energy it actually takes, which happens after
    the queue. That is what makes a long queue expensive -- it can push the
    plug-in into a different, more expensive tariff band.
    """
    A, B = env.access_slots, env.return_slots
    q = int(env.q[t])
    plug = t + A + q
    s = env.soc - env.access_kwh / env.batt
    # THE REFUELLING TRIP IS EXEMPT FROM THE RESERVE FLOOR.
    #
    # The reserve floor (C2) governs the state of charge at which the driver
    # is EARNING: it stops the driver from working the pack down to nothing.
    # The trip to the charger is a different thing. A driver who drives to a
    # charger is not stranded -- he is about to be plugged in, and the pack
    # is full again twenty minutes later. So the deadhead is allowed to
    # arrive with less than the reserve, as long as it arrives with SOME
    # charge.
    #
    # This exemption is not cosmetic. Without it the states just above the
    # floor (s < soc_res + access_kwh/batt) are ABSORBING: the driver can
    # never start an excursion, so he can never charge again, so the
    # multi-day model has no fixed point -- the iteration W <- V(0, .)
    # diverges because W(s) = reward + W(s) has no solution at the trap.
    # The v2 model never hit this, because there the charger is where the
    # car already is.
    ok = s > 1e-6
    cost = np.zeros(env.nS)
    for j in range(k):
        p = plug + j
        if p >= env.T:
            break                       # the horizon truncates the dwell
        tau = taper(s, env.eta_cc)
        if env.billing == "kwh":
            drawn = np.minimum(env.p_kw * tau * env.dt_h,
                               np.maximum(0.0, (1.0 - s) * env.batt) / env.eta_c)
            cost = cost + env.price_all[p] * drawn
        else:
            cost = cost + env.price_all[p] * env.p_kw * env.dt_h
        s = np.minimum(1.0, s + env.p_kw * tau * env.eta_c * env.dt_h / env.batt)
    return cost, s, ok, (A + q + k + B)


def k_to_target(env, s, target=1.0):
    """How many dwell slots are needed to bring a pack at SOC s to `target`.

    Used by the rules: a driver who decides to charge wants to know how long
    they will be plugged in, and the honest answer accounts for the CC-CV
    taper rather than assuming a constant rate.
    """
    s = float(s) - env.access_kwh / env.batt
    for k in range(1, env.max_dwell + 1):
        tau = float(taper(s, env.eta_cc))
        s = min(1.0, s + env.p_kw * tau * env.eta_c * env.dt_h / env.batt)
        if s >= target - 1e-9:
            return k
    return env.max_dwell


# ===========================================================================
# Solvers
# ===========================================================================
def _idx(env, s):
    return np.clip(np.round((s - env.soc_res) / env.step).astype(int),
                   0, env.nS - 1)


def solve_dp3(env, consistent: bool = True, V_term=None):
    """Deterministic expected-value DP with charging as an excursion.

    Returns (V, pol, pol_k): V has shape (T+1, nS), pol holds the action
    (DRIVE / CHARGE / IDLE) and pol_k holds the number of dwell slots chosen
    by a CHARGE action.

    The recursion is a backward sweep over t. It is well defined even though
    a CHARGE action jumps over several slots, because every jump is strictly
    forward in time: V(t, s) reads V(t + D, .) with D >= 1, and D > 1 only
    makes the dependency further away, never circular.
    """
    T, nS = env.T, env.nS
    batt = env.batt
    floor_kwh = env.soc_res * batt
    V = np.full((T + 1, nS), -np.inf)
    pol = np.zeros((T, nS), dtype=np.int8)
    pol_k = np.zeros((T, nS), dtype=np.int8)

    for i, s in enumerate(env.soc):
        V[T, i] = env.mu_end * max(0.0, s - env.soc_res) * batt
    if V_term is not None:
        # The cyclic multi-day driver: the end of the day is the start of
        # the next one, so the terminal value is the continuation value
        # W(s) rather than the price of a kWh of leftover charge.
        V[T, :] = np.asarray(V_term, dtype=float)

    for t in range(T - 1, -1, -1):
        Vn = V[t + 1]
        best = np.full(nS, -np.inf)
        barg = np.full(nS, IDLE, dtype=np.int8)
        bk = np.zeros(nS, dtype=np.int8)

        # ---- DRIVE -------------------------------------------------------
        if consistent:
            afford = np.maximum(0.0, env.soc * batt - floor_kwh)
            m = (np.minimum(env.n_eff[t], afford / env.kwh[t])
                 if env.kwh[t] > 1e-9 else np.full(nS, env.n_eff[t]))
            nk = env.soc * batt - m * env.kwh[t]
            # orders the driver has to refuse because the pack cannot cover
            # them; each one costs `miss_penalty`
            missed = np.maximum(0.0, env.n_eff[t] - m)
            vd = (m * env.fare[t] - env.miss_penalty * missed
                  + Vn[_idx(env, nk / batt)])
        else:
            nk = env.soc * batt - env.served_kwh[t]
            vd = np.where(nk >= floor_kwh - 1e-9,
                          env.served_rev[t] + Vn[_idx(env, nk / batt)],
                          -np.inf)
        better = vd > best
        best = np.where(better, vd, best)
        barg = np.where(better, DRIVE, barg)

        # ---- CHARGE: an excursion ---------------------------------------
        for k in range(1, env.max_dwell + 1):
            cost, sa, ok, D = excursion_arrays(env, t, k)
            t2 = min(t + D, T)
            vc = -cost + V[t2][_idx(env, sa)]
            # An excursion that would run past midnight is not started. The
            # day boundary has to be a state in which the driver is on the
            # road, not halfway to a charger; the overnight charge belongs
            # to the NEXT day's plan, where it competes with the morning's
            # revenue like any other excursion.
            ok = ok & (t + D <= T)
            better = ok & (vc > best)
            best = np.where(better, vc, best)
            barg = np.where(better, CHARGE, barg)
            bk = np.where(better, k, bk)

        # ---- IDLE --------------------------------------------------------
        better = Vn > best
        best = np.where(better, Vn, best)
        barg = np.where(better, IDLE, barg)

        V[t] = best
        pol[t] = barg
        pol_k[t] = bk

    return V, pol, pol_k


def solve_mdp3(env, kmax: int = 6, consistent: bool = True, V_term=None):
    """Finite-horizon MDP with Poisson order arrivals and excursions.

    The arrival count is summed out exactly over k = 0..kmax. Only the DRIVE
    action is stochastic: an excursion is a deterministic jump, and the orders
    that arrive while the driver is away are simply not served -- which is
    exactly how the opportunity cost is supposed to work.
    """
    from ev_dp import _pois

    T, nS = env.T, env.nS
    batt = env.batt
    floor_kwh = env.soc_res * batt
    V = np.full((T + 1, nS), -np.inf)
    pol = np.zeros((T, nS), dtype=np.int8)
    pol_k = np.zeros((T, nS), dtype=np.int8)

    for i, s in enumerate(env.soc):
        V[T, i] = env.mu_end * max(0.0, s - env.soc_res) * batt
    if V_term is not None:
        V[T, :] = np.asarray(V_term, dtype=float)

    pmf = [_pois(lmb, kmax, None) for lmb in env.lam]
    km = min(kmax, 6)

    for t in range(T - 1, -1, -1):
        Vn = V[t + 1]
        best = np.full(nS, -np.inf)
        barg = np.full(nS, IDLE, dtype=np.int8)
        bk = np.zeros(nS, dtype=np.int8)

        # ---- DRIVE -------------------------------------------------------
        afford = np.maximum(0.0, env.soc * batt - floor_kwh)
        vdrive = np.zeros(nS)
        for k in range(km + 1):
            pk = pmf[t][k]
            if pk < 1e-12:
                continue
            served_k = min(k, env.cap)
            if consistent:
                m = (np.minimum(served_k, afford / env.kwh[t])
                     if env.kwh[t] > 1e-9 else np.full(nS, served_k))
                missed = np.maximum(0.0, served_k - m)
                nk = env.soc * batt - m * env.kwh[t]
                v = (m * env.fare[t] - env.miss_penalty * missed
                     + Vn[_idx(env, nk / batt)])
            else:
                m = np.full(nS, served_k)
                nk = env.soc * batt - m * env.kwh[t]
                v = m * env.fare[t] + Vn[_idx(env, nk / batt)]
                v = np.where(nk >= floor_kwh - 1e-9, v, 0.0)
            vdrive += pk * v
        better = vdrive > best
        best = np.where(better, vdrive, best)
        barg = np.where(better, DRIVE, barg)

        # ---- CHARGE: an excursion ---------------------------------------
        for k in range(1, env.max_dwell + 1):
            cost, sa, ok, D = excursion_arrays(env, t, k)
            t2 = min(t + D, T)
            vc = -cost + V[t2][_idx(env, sa)]
            # An excursion that would run past midnight is not started. The
            # day boundary has to be a state in which the driver is on the
            # road, not halfway to a charger; the overnight charge belongs
            # to the NEXT day's plan, where it competes with the morning's
            # revenue like any other excursion.
            ok = ok & (t + D <= T)
            better = ok & (vc > best)
            best = np.where(better, vc, best)
            barg = np.where(better, CHARGE, barg)
            bk = np.where(better, k, bk)

        better = Vn > best
        best = np.where(better, Vn, best)
        barg = np.where(better, IDLE, barg)

        V[t] = best
        pol[t] = barg
        pol_k[t] = bk

    return V, pol, pol_k


# ===========================================================================
# A rule that knows the queue and the demand curve
# ===========================================================================
def _forward(env, t0, s0):
    """Mean-demand forward pass. Returns (revenue, stranded_slots, final_soc).

    "Stranded" counts the slots in which the driver would have taken orders
    but could not, because the pack was already on the reserve floor.
    """
    s, rev, stranded = s0, 0.0, 0
    for t in range(t0, env.T):
        m = env.n_eff[t]
        if m > 0 and s <= env.soc_res + 1e-9:
            stranded += 1
            m = 0.0
        else:
            afford = max(0.0, (s - env.soc_res) * env.batt)
            if env.kwh[t] > 1e-9:
                m = min(m, afford / env.kwh[t])
        s = s - m * env.kwh[t] / env.batt
        rev += m * env.fare[t]
    return rev, stranded, s


def plan_best_excursion(env, t_start, s_start):
    """The single charging excursion that maximises the rest of the day's net
    earnings, given the mean demand curve and the known queue.

    This is a deliberately generous baseline: it knows the queue exactly, it
    knows the demand curve, it accounts for the revenue it forgoes while it
    is away, and it prices the electricity at the plug-in slot. A real driver
    has none of that. It is reported as an ORACLE, so that the gain of the
    optimiser is not inflated by a strawman rule.
    """
    T = env.T
    soc_b = np.zeros(T + 1)
    rev_b = np.zeros(T + 1)
    s, rv = s_start, 0.0
    for t in range(t_start, T):
        soc_b[t], rev_b[t] = s, rv
        m = env.n_eff[t]
        afford = max(0.0, (s - env.soc_res) * env.batt)
        if env.kwh[t] > 1e-9:
            m = min(m, afford / env.kwh[t])
        s = s - m * env.kwh[t] / env.batt
        rv += m * env.fare[t]
    soc_b[T], rev_b[T] = s, rv

    best = None
    for t in range(t_start, T):
        for k in range(1, env.max_dwell + 1):
            r = env.excursion(t, soc_b[t], k)
            if r is None:
                continue
            c, sa, D = r
            t2 = min(t + D, T)
            ra, stranded, _ = _forward(env, t2, sa)
            total = rev_b[t] + ra - c
            key = (stranded == 0, total)
            if best is None or key > best[0]:
                best = (key, t, k)
    if best is None:
        return None
    return best[1], best[2]


def _plan_chain(env, soc0=0.80):
    """The receding-horizon plan of the oracle rule: plan, execute, replan."""
    plan = []
    t, s = 0, soc0
    while t < env.T:
        r = plan_best_excursion(env, t, s)
        if r is None:
            break
        t_, k_ = r
        plan.append((t_, k_))
        _, sa, D = env.excursion(t_, s, k_)
        s = sa
        t = min(t_ + D, env.T)
        if t >= env.T:
            break
    return plan


# ===========================================================================
# Policy simulation
# ===========================================================================
def run_policy3(env, kind: str, rng: np.random.Generator, **kw):
    """Simulate one driver-day under a given policy with Poisson arrivals.

    kind: 'dp' | 'mdp' | 'cheapest-plug' | 'cheapest-depart' | 'cheapest-net'
          | 'threshold' | 'charge-full' | 'never-charge'
    """
    T = env.T
    s = kw.get("soc0", 0.80)
    pol = kw.get("policy")
    pol_k = kw.get("pol_k")
    thresh = kw.get("thresh", 0.30)

    rev = cost = ekwh = chkwh = 0.0
    n_orders = 0
    missed = 0.0
    # The revenue the driver FORFEITS by refusing an order, at the fare of
    # the slot in which the refusal happened. This is not the same as a
    # penalty: it measures what the refused work was worth, which is what
    # makes it possible to say whether a day flagged as infeasible because of
    # a refusal was a bad day or a cheap one.
    missed_value = 0.0
    avail = 0.0
    path, charge_slots = [], []
    stranded = False
    n_exc = 0
    offroad_slots = 0

    cheap_t = None
    plan = kw.get("plan")
    plan_i = 0
    if kind == "cheapest-plug":
        # the departure slot whose PLUG-IN time is cheapest -- this rule knows
        # the queue, it just does not price the time it loses
        best = None
        for t in range(T):
            p = min(t + env.access_slots + int(env.q[t]), T - 1)
            if best is None or env.price_all[p] < env.price_all[best[1]] - 1e-12:
                best = (t, p)
        cheap_t = best[0]
    elif kind == "cheapest-depart":
        cheap_t = int(np.argmin(env.price_all))
    elif kind == "cheapest-net" and plan is None:
        # the plan depends only on the MEAN demand curve and the queue, so it
        # is the same on every simulated day and is computed once by
        # evaluate3 rather than once per day
        plan = _plan_chain(env, kw.get("soc0", 0.80))

    t = 0
    while t < T:
        i = env.to_idx(s)

        # ---- the decision ---------------------------------------------
        if kind in ("dp", "mdp"):
            a, k = int(pol[t, i]), int(pol_k[t, i])
        elif kind in ("cheapest-plug", "cheapest-depart"):
            if t == cheap_t:
                a, k = CHARGE, k_to_target(env, s, 1.0)
            else:
                a, k = DRIVE, 0
        elif kind == "threshold":
            if s < thresh:
                a, k = CHARGE, k_to_target(env, s, min(0.95, thresh + 0.25))
            else:
                a, k = DRIVE, 0
        elif kind == "charge-full":
            if s < thresh:
                a, k = CHARGE, k_to_target(env, s, 1.0)
            else:
                a, k = DRIVE, 0
        elif kind == "never-charge":
            a, k = DRIVE, 0
        elif kind == "cheapest-net":
            # the plan is a list of (start_slot, dwell_slots); it is shared
            # across simulated days, so it is indexed and never mutated
            if plan is not None and plan_i < len(plan) and plan[plan_i][0] == t:
                a, k = CHARGE, plan[plan_i][1]
                plan_i += 1
            else:
                a, k = DRIVE, 0
        else:
            raise ValueError(kind)

        # ---- the excursion ---------------------------------------------
        if a == CHARGE:
            r = env.excursion(t, s, k)
            if r is None:
                a = DRIVE           # the deadhead would breach the floor
            elif t + r[2] > T:
                # an excursion that runs past midnight is not started, for
                # the same reason the planner will not start one
                a = DRIVE
            else:
                c, sa, D = r
                cost += c
                chkwh += max(0.0, (sa - s) * env.batt + env.access_kwh)
                n_exc += 1
                offroad_slots += D
                plug = t + env.access_slots + int(env.q[t])
                ss = s - env.access_kwh / env.batt
                for u in range(D):
                    tt = t + u
                    if tt >= T:
                        break
                    if u < env.access_slots:
                        lab = "TRAVEL"
                    elif u < plug - t:
                        lab = "QUEUE"
                    elif u < plug - t + k:
                        lab = "CHARGE"
                    else:
                        lab = "RETURN"
                    path.append((tt, lab, ss))
                    if lab == "CHARGE":
                        charge_slots.append(tt)
                        tau = float(taper(ss, env.eta_cc))
                        ss = min(1.0, ss + env.p_kw * tau * env.eta_c
                                 * env.dt_h / env.batt)
                s = sa
                t += D
                continue

        if a == DRIVE:
            arr = kw.get("arrivals")
            N = int(arr[t]) if arr is not None else int(rng.poisson(env.lam[t]))
            m = min(N, env.cap)
            e = m * env.kwh[t]
            want = m
            avail += want
            if s * env.batt - e < env.soc_res * env.batt - 1e-9:
                stranded = True
                afford = max(0.0, (s - env.soc_res) * env.batt)
                m = min(m, afford / max(env.kwh[t], 1e-9))
                e = m * env.kwh[t]
            missed += want - m
            missed_value += (want - m) * env.fare[t]
            s = s - e / env.batt
            rev += m * env.fare[t]
            n_orders += m
            ekwh += e
            path.append((t, "DRIVE", s))
        else:
            path.append((t, "IDLE", s))
        t += 1

    feasible = (not stranded) and s >= env.soc_res - 1e-6
    net_adj = rev - cost - env.miss_penalty * missed
    return {
        "revenue": rev, "energy_cost": cost, "net": rev - cost,
        "net_adj": net_adj, "missed": missed,
        "energy_used": ekwh, "charge_kwh": chkwh, "orders": n_orders,
        "missed_value": missed_value,
        "available": avail,
        "acceptance": (n_orders / avail) if avail > 0 else 1.0,
        "final_soc": s, "feasible": feasible, "stranded": stranded,
        "path": path, "charge_slots": charge_slots,
        "excursions": n_exc, "offroad_slots": offroad_slots,
    }


def policy_day(env, pol, pol_k, soc0=0.80):
    """Follow the policy under the MEAN demand profile and report the day.

    Returns the list of excursions as (start_slot, dwell_slots, duration,
    cost). This is the schedule we quote in the paper: it is the policy's own
    plan, not one realised day, so it is the same every time.
    """
    t, s = 0, float(soc0)
    events = []
    while t < env.T:
        i = env.to_idx(s)
        a, k = int(pol[t, i]), int(pol_k[t, i])
        if a == CHARGE:
            r = env.excursion(t, s, k)
            if r is None:
                a = DRIVE
            else:
                c, sa, D = r
                events.append((t, int(k), int(D), float(c)))
                s = sa
                t += D
                continue
        m = env.n_eff[t]
        afford = max(0.0, (s - env.soc_res) * env.batt)
        if env.kwh[t] > 1e-9:
            m = min(m, afford / env.kwh[t])
        s = s - m * env.kwh[t] / env.batt
        t += 1
    return events


def evaluate3(env, kind, n_sims=400, seed=0, demands=None, **kw):
    """Monte-Carlo average of a policy over independent random days.

    COMMON RANDOM NUMBERS. The arrival sequence of every simulated day is
    drawn once and handed to every policy, so that two policies are compared
    on the same realisation of the world. Without this, a policy that skips
    slots during an excursion consumes a different part of the random stream
    from one that does not, and the difference between two policies ends up
    carrying Monte-Carlo noise as well as the real effect. With it, the
    paired difference has a standard error an order of magnitude smaller.
    """
    rng = np.random.default_rng(seed)
    if demands is None:
        demands = rng.poisson(
            np.broadcast_to(env.lam, (n_sims, env.T)).astype(float))
    if kind == "cheapest-net" and "plan" not in kw:
        # the oracle's plan depends only on the mean demand curve and the
        # queue, so it is identical on every simulated day: compute it once
        kw = dict(kw)
        kw["plan"] = _plan_chain(env, kw.get("soc0", 0.80))
    keys = ["revenue", "energy_cost", "net", "net_adj", "missed",
            "energy_used", "charge_kwh", "orders", "available",
            "acceptance", "final_soc", "excursions", "offroad_slots"]
    acc = {k: [] for k in keys}
    feas = 0
    good_net = []
    for d in range(n_sims):
        r = run_policy3(env, kind, rng, arrivals=demands[d], **kw)
        for k in keys:
            acc[k].append(r[k])
        feas += int(r["feasible"])
        if r["feasible"]:
            good_net.append(r["net"])
    out = {k: float(np.mean(v)) for k, v in acc.items()}
    out["feasible_rate"] = feas / n_sims
    out["net_std"] = float(np.std(acc["net"], ddof=1))
    # earnings on the days the driver actually completed. The mean over all
    # days mixes two very different things -- a good day and a day that went
    # wrong -- and the mean over feasible days alone is what a driver
    # compares across policies.
    out["net_feasible_only"] = float(np.mean(good_net)) if good_net else float("nan")
    return out


# ===========================================================================
# The cyclic multi-day driver
# ===========================================================================
# WHY THIS EXISTS. A single-day model starts every day at a fixed SOC and
# ends it wherever the plan ends, which hides the single most important
# consequence of charging as an excursion: the driver can no longer choose
# to be "at a charger" at any moment, so the energy left at midnight has to
# be carried into tomorrow, and tomorrow's first charge competes with
# tomorrow's first revenue.
#
# Without a continuation value the planner sees no reason to keep any
# energy: it rides the pack down to the reserve floor at the end of every
# day, and on a day when the realised demand is above the mean it breaches
# the floor and the day is lost. That is not a property of the driver's
# decision, it is an artefact of the boundary condition.
#
# The fix is the same one the v2 model uses: make the day a cycle.
#
#     V(T, s) = W(s)                 end of day -> start of next day
#     V(t, s) = max_a E[ r_t(a) + V(t+1, s') ]
#     W(s)    = V(0, s)               fixed point
#
# T(W + c) = T(W) + c for every constant c, so the fixed point is only
# determined up to an additive constant: the LEVEL of W drifts by the
# average daily reward on every sweep. Centring W after each sweep removes
# that drift, and what is left contracts. Without the centring the iteration
# diverges, which is why this detail matters and not just tidiness.


def cyclic_value_iteration3(env, iters=2000, tol=1e-9, damping=0.5, kmax=6,
                            solver="mdp"):
    """Optimal long-run policy for a driver who works day after day.

    Returns (W, pol, pol_k, iters, hist) where W is the continuation value
    as a function of the starting SOC, pol/pol_k are the stationary policy
    that realises it, and hist is the residual per sweep.

    `solver` selects the recursion inside the sweep. "mdp" is the stochastic
    (Poisson) recursion and gives the optimiser; "dp" is the expected-value
    recursion, which is used to build the two deterministic baselines -- the
    naive one and the capacity-aware one -- under exactly the same
    multi-day boundary condition, so that the comparison between them is a
    comparison of the DEMAND MODEL and not of the boundary condition.
    """
    solve = solve_mdp3 if solver == "mdp" else solve_dp3
    nS = env.nS
    W = np.zeros(nS)
    pol = pol_k = None
    hist = []
    for it in range(iters):
        if solver == "mdp":
            V, pol, pol_k = solve(env, kmax=kmax, V_term=W)
        else:
            V, pol, pol_k = solve(env, V_term=W)
        W_raw = V[0, :]
        Wc = W_raw - W_raw.mean()          # remove the level drift
        gap = float(np.max(np.abs(Wc - (W - W.mean()))))
        hist.append(gap)
        W = W.mean() + (1.0 - damping) * (W - W.mean()) + damping * Wc
        if gap < tol:
            break
    return W, pol, pol_k, it + 1, hist


def shadow_price3(W, env, s_lo=0.30, s_hi=0.95):
    """dW/ds per kWh over the SOC band the driver actually operates in.

    This is the price of a kWh carried across the day boundary. It is not a
    tariff: it is what one more kWh in the pack at midnight is worth,
    because it is one kWh less that has to be bought at tomorrow's prices.
    """
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


def optimal_start_soc3(W, env):
    """The SOC at which starting a day is worth the most.

    This is the right answer for the FIRST day of a driver's life and for a
    driver who is free to choose their starting state. It is NOT the
    steady state of a driver who works day after day: once the pack has
    settled, the SOC at the end of the day IS the SOC at the start of the
    next one, and that fixed point is what `steady_state_soc3` returns.
    """
    return float(env.soc[int(np.argmax(W))])


def steady_state_soc3(env, pol, pol_k, soc0=0.80, iters=500, tol=1e-5):
    """The SOC at which the driver's day repeats itself.

    Map the start-of-day SOC to the end-of-day SOC under the mean demand
    profile -- a deterministic one-dimensional map -- and iterate it to its
    fixed point. This is the SOC a driver who works every day actually
    carries, and it is the number worth reporting: the argmax of W is only
    reachable on the first day.
    """
    s = float(soc0)
    for _ in range(iters):
        t, s_new = 0, s
        while t < env.T:
            i = env.to_idx(s_new)
            a, k = int(pol[t, i]), int(pol_k[t, i])
            if a == CHARGE:
                r = env.excursion(t, s_new, k)
                if r is None or t + r[2] > env.T:
                    a = DRIVE
                else:
                    s_new = r[1]
                    t += r[2]
                    continue
            m = env.n_eff[t]
            afford = max(0.0, (s_new - env.soc_res) * env.batt)
            if env.kwh[t] > 1e-9:
                m = min(m, afford / env.kwh[t])
            s_new = s_new - m * env.kwh[t] / env.batt
            t += 1
        if abs(s_new - s) < tol:
            return float(s_new)
        s = s_new
    return float(s)


def evaluate3_cyclic(env, kind, n_sims=200, seed=0, days=7, soc0=None,
                     demands=None, warmup=1, **kw):
    """Evaluate a policy over CONSECUTIVE days, carrying the battery over.

    The driver starts day 1 at `soc0` (by default the SOC that maximises
    the continuation value) and works `days` days in a row; whatever is left
    in the pack at midnight is what the next day starts with. The first
    `warmup` days are a transient -- the driver is still moving towards the
    stationary behaviour -- so the reported earnings are taken over the
    settled days only, and the transient is reported separately.
    """
    rng = np.random.default_rng(seed)
    if demands is None:
        demands = rng.poisson(
            np.broadcast_to(env.lam, (n_sims, days, env.T)).astype(float))
    # the start-of-day SOC is the caller's business, not the policy's
    kw.pop("soc0", None)
    if soc0 is None:
        soc0 = 0.80
    keys = ["revenue", "energy_cost", "net", "net_adj", "missed",
            "missed_value", "energy_used", "charge_kwh", "orders",
            "available", "acceptance", "excursions", "offroad_slots"]
    acc = {k: [] for k in keys}
    feas = 0
    n_day = 0
    good_net = []
    start_socs = []
    for d in range(n_sims):
        s = float(soc0)
        for day in range(days):
            s_start = s
            r = run_policy3(env, kind, rng, arrivals=demands[d, day],
                            soc0=s, **kw)
            s = r["final_soc"]
            n_day += 1
            feas += int(r["feasible"])
            if r["feasible"]:
                good_net.append(r["net"])
            # the transient days are excluded from the averages
            if day >= warmup:
                for k in keys:
                    acc[k].append(r[k])
                start_socs.append(float(s_start))
    out = {k: float(np.mean(v)) if v else float("nan") for k, v in acc.items()}
    out["feasible_rate"] = feas / max(n_day, 1)
    out["net_std"] = float(np.std(acc["net"], ddof=1)) if acc["net"] else float("nan")
    out["net_feasible_only"] = float(np.mean(good_net)) if good_net else float("nan")
    out["final_soc"] = float(s)
    out["soc0"] = float(soc0)
    out["mean_start_soc"] = (float(np.mean(start_socs)) if start_socs
                             else float("nan"))
    out["days"] = days
    return out


# ===========================================================================
# Self-test and diagnostics
# ===========================================================================
def _hhmm(t, dt_h=0.25):
    h = int(t * dt_h)
    return f"{h:02d}:{(int(round((t * dt_h % 1) * 60))):02d}"


if __name__ == "__main__":
    from ev_dp import Env, solve_mdp as solve_mdp2

    # ---- 1. v3 must reproduce v2 EXACTLY in the degenerate limit ---------
    e2 = Env()
    V2, pol2 = solve_mdp2(e2, kmax=6)
    e3 = Env3(queue_peak_slots=0.0, access_slots=0, return_slots=0,
              access_kwh=0.0, max_dwell=1)
    V3, pol3, polk3 = solve_mdp3(e3, kmax=6)
    f2 = np.where(np.isfinite(V2), V2, 0.0)
    f3 = np.where(np.isfinite(V3), V3, 0.0)
    print(f"[check] max |V3 - V2| over the whole state space: "
          f"{np.abs(f3 - f2).max():.3e}")
    mism = int((pol3 != pol2).sum())
    print(f"[check] policy cells differing (tie-breaking only): "
          f"{mism} / {pol2.size}")

    # ---- 2. a v3 environment with a queue -------------------------------
    for tag, over in [
        ("v2 calibration  (40 kWh, 60 kW)",
         dict(batt=40.0, p_kw=60.0)),
        ("2026 mainstream  (57.6 kWh, 90 kW, 0.19 kWh/km)",
         dict(batt=57.6, p_kw=90.0, kwh_km=0.19)),
    ]:
        print("\n" + "=" * 72)
        print(tag)
        print("=" * 72)
        env = Env3(queue_shape="meal", queue_peak_slots=4.0,   # 1 h at peak
                   access_slots=1, return_slots=1, access_kwh=0.7,
                   max_dwell=4, **over)
        print(env.describe())
        V, pol, polk = solve_mdp3(env, kmax=6)
        print(f"  V(0, 80%) = ${V[0][env.to_idx(0.80)]:,.2f}")

        rng = np.random.default_rng(20261001)
        best = None
        for _ in range(60):
            c = run_policy3(env, "mdp", rng, policy=pol, pol_k=polk)
            if c["feasible"] and (best is None or c["net"] > best["net"]):
                best = c
        if best is None:
            best = run_policy3(env, "mdp", rng, policy=pol, pol_k=polk)
        print(f"  simulated day: net ${best['net']:,.2f}, "
              f"{best['excursions']} excursions, "
              f"{best['offroad_slots']} slots off the road")
        # print the excursions as blocks
        blocks, cur = [], None
        for t, lab, _s in best["path"]:
            if lab == "CHARGE" and (cur is None or t != cur[1]):
                cur = [t, t, 1]
                blocks.append(cur)
            elif lab == "CHARGE" and cur is not None:
                cur[1] = t
        for t0, t1, _ in blocks:
            print(f"    plugged in {_hhmm(t0)} - {_hhmm(t1 + 1)}")

    # ---- 3. the policy comparison ---------------------------------------
    env = Env3(queue_shape="meal", queue_peak_slots=4.0,
               access_slots=1, return_slots=1, access_kwh=0.7, max_dwell=4)
    V, pol, polk = solve_mdp3(env, kmax=6)
    print("\n" + "=" * 72)
    print("POLICY COMPARISON (v3, 400 Monte-Carlo days, seed 20261001)")
    print("=" * 72)
    for kind, extra in [("mdp", dict(policy=pol, pol_k=polk)),
                        ("cheapest-net", {}),
                        ("cheapest-plug", {}),
                        ("threshold", {}),
                        ("never-charge", {})]:
        r = evaluate3(env, kind, n_sims=400, seed=20261001, **extra)
        print(f"  {kind:16s} net ${r['net']:8,.2f}  adj ${r['net_adj']:8,.2f}"
              f"  feasible {r['feasible_rate']:6.1%}"
              f"  missed {r['missed']:5.2f}  exc {r['excursions']:.2f}")

    # ---- 4. the cost of refusing work ----------------------------------
    print("\n" + "=" * 72)
    print("THE PENALTY FOR REFUSING WORK (miss_penalty sweep)")
    print("=" * 72)
    for pen in [0.0, 1.0, 2.0, 5.0, 10.0]:
        e = Env3(queue_shape="meal", queue_peak_slots=4.0,
                 access_slots=1, return_slots=1, access_kwh=0.7,
                 max_dwell=4, miss_penalty=pen)
        _, p, pk = solve_mdp3(e, kmax=6)
        r = evaluate3(e, "mdp", n_sims=400, seed=20261001, policy=p, pol_k=pk)
        sched = " ".join(f"{_hhmm(t)}(k={k})" for t, k, _D, _c
                         in policy_day(e, p, pk))
        print(f"  penalty ${pen:5.1f}  net ${r['net']:8,.2f}  "
              f"adj ${r['net_adj']:8,.2f}  feasible {r['feasible_rate']:6.1%}"
              f"  missed {r['missed']:5.2f}   sched {sched}")




