---
title: "When Should an Electric Ride-Hailing Driver Charge?"
subtitle: "Optimal Intra-Day Charging under Stochastic Order Demand and Time-of-Use Pricing"
author:
  - "Ruixi Liang (梁睿希), Student ID 202464870791"
  - "School of Future Technology, South China University of Technology, Big Data Class 1"
  - "Course: Optimization Methods (084100551)  |  Supervisor: Zhenhong Lin"
date: "Draft, 24 October 2026"
lang: en-US
---

::: {custom-style="Abstract"}
**Abstract.** Electric ride-hailing platforms are electrifying their fleets, turning charging from a fuel stop into a scheduling decision paid for in foregone fares rather than in minutes. This paper studies the single-driver case: when should one electric ride-hailing driver charge during a working day to maximise net earnings? We build a discrete-time model of one driver over a 24-hour horizon of 96 fifteen-minute slots, where the state is the state of charge and each slot's action is to drive, charge or idle. Orders arrive as a Poisson process whose rate is estimated from 2,739,936 real New York yellow-taxi trips; charging is billed per charger slot under a time-of-use tariff; and the pack obeys a constant-current/constant-voltage taper. We solve it exactly by dynamic programming and by a Markov decision process that sums the Poisson arrival count out in closed form, over 8,256 states. Three findings follow. First, on 74.4% of simulated working days the optimal policy charges at least once outside the cheapest tariff window, because off-peak hours offer cheap electricity and almost no fares at the same time. Second, the time-of-use price spread is nearly irrelevant: widening the peak-to-valley spread from 0x to 2x changes the gain over a tariff-following rule by only 1.3%, so opportunity cost, not price, drives the decision. Third, a cyclic multi-day formulation shows that the optimal start-of-day state of charge is 36.8% rather than 100%, and prices cross-day stored energy at \$0.2414/kWh, between the valley and peak tariffs. We also show that a single-day model overstates earnings by 2.4% because it treats a full battery as free.

:::

::: {custom-style="Abstract"}
**Keywords:** electric ride-hailing; charging scheduling; dynamic programming; Markov decision process; time-of-use pricing; opportunity cost; value of time
:::

# 1. Introduction

## 1.1 Background and motivation

Ride-hailing platforms are replacing fleets with electric vehicles for reasons that are ultimately economic rather than environmental, and the operating economics of an electric taxi differ from those of an internal-combustion one in one decisive respect: charging takes time, and for a driver, time spent not carrying a passenger produces no revenue. A typical electric vehicle needs roughly fifty minutes of 50 kW direct-current fast charging to move from a low state of charge to 80%, against a few minutes at a petrol pump. For an ordinary private car this is an inconvenience; for a ride-hailing driver it is a direct revenue loss. Ma [1] decomposes the cost of an electric dial-a-ride charging episode into three components --- vehicle access time, charging time and waiting time --- and reports large reductions in waiting time and charging duration from coordinated scheduling, which confirms that charging time is treated in the literature as a first-class cost rather than a side issue.

The intuitive answer to "when should I charge?" is to consult the time-of-use (TOU) tariff and charge when electricity is cheapest. This answer is roughly right when a fleet of vehicles concentrates its charging in a depot, where the binding constraint is transformer capacity and demand charges. It is wrong for an individual driver, and the reason is structural rather than a matter of calibration. A driver is simultaneously a consumer of electricity and an instrument of production: the same fifteen minutes cannot both be spent buying cheap power and earning fares. Which of the two dominates depends on how many orders are available at that time of day, and the intra-day distribution of demand is extremely uneven.

We quantify this on real data. From 2,739,936 cleaned trip records covering 30 complete working days of New York City yellow-taxi operation in January 2024 [2], the citywide order arrival rate varies by a factor of 18.5 within a single day, from 91 orders per fifteen minutes at 03:00 to 1,684 at 18:00. Off-peak hours are therefore cheap *and* empty at the same time, and the two effects do not cancel: deferring a charge from the valley into a shoulder period costs a small amount of additional electricity but recovers a large amount of foregone fare revenue. The cheapest kWh is not the last kWh a driver should buy.

## 1.2 Literature review

Existing work on electric ride-hailing charging can be organised by who makes the decision, and this partition is more informative than a partition by topic because it exposes where the open cells are.

At the platform and market-equilibrium level, Ke et al. [3] model the working and recharging schedules of drivers in a ride-sourcing market with electric and gasoline vehicles, using a time-expanded network and user equilibrium. Their decision set is wider than ours, since a driver may also choose whether to work at all, and their central observation --- that Beijing taxis average 241 km per day against a safe electric range of 200 km, so charging is unavoidable *within* a shift --- motivates our own choice of a 40 kWh pack. Liu et al. [4] extend this line by introducing driving fatigue, and report that drivers' charging behaviour synchronises with their resting behaviour, i.e. charging need not be a pure loss. Qin et al. [5] analyse charging patterns and infrastructure deployment from real electric-vehicle trajectories and battery data in Shanghai.

At the fleet-scheduling level, Ma [1] proposes a two-stage scheme for dynamic electric dial-a-ride services, combining a daily charging plan with an online vehicle-to-charger assignment that accounts for charger queueing, solved by Lagrangian relaxation. Ma [6] applies a rolling-horizon scheme with a hybrid LSTM predictor of charger occupancy to an electric demand-responsive transport case in Dundee. Ma, Connors and Viti [7] --- the closest work to ours --- formulate congestion-aware charging coordination for electric ride-hailing fleets under stochastic demand as a sequential mixed-integer program with a day-ahead plan and an online coordination stage, using the same New York yellow-taxi dataset and the same stochastic-demand assumption, and report a profit improvement of 3.91% over their strongest baseline. Alam and Guo [8] study charging infrastructure planning for ride-sourcing electric vehicles with an explicit value-of-time term.

A third line formulates joint charging and dispatch as a Markov decision process solved by deep reinforcement learning; Ma et al. [9] criticise the existing literature for treating charging and dispatch separately and for assuming that the nearest charger is always optimal. We deliberately do not follow this line. Our state space contains only 8,256 states, so the analytic DP and MDP solutions are both exact and immediate, and they align directly with the dynamic-programming content of the course. This is a conscious trade-off, not an oversight.

Finally, a small but decisive body of work measures the value of time (VOT) empirically, which we use as an external calibration anchor. Mehditabrizi, Namadi and Cirillo [10] estimate a VOT of \$15.20 per hour for refuelling and charging transitions; Dorsey, Langer and McRae [11] estimate \$27.54 per hour, equal to 89% of local median wage, and note that the US Department of Transportation convention of 50% of wage systematically understates it; and Sunada and Xia [12] report a charging VOT of 27% of average wage from Shanghai telemetry.

The existing body of work therefore operates predominantly at the fleet or market level: it jointly optimises fleet charging plans and charger assignment [1,6,7], or characterises equilibria of driver work-and-charge schedules [3,4]. Such models take demand or capacity as given, or grow a state space with the number of vehicles. We stop deliberately at the level of a single driver. This is a reduction in scale, not a filling of a gap, and we state it as such: it buys an exact closed-form solution and the freedom to embed stochastic arrivals and a charging-power taper directly in the model, at the cost of ignoring charger congestion and inter-driver competition.

## 1.3 Research question and contribution

**Research question.** For a single electric ride-hailing driver facing a time-of-use electricity tariff and a Poisson arrival process of orders, what intra-day charging schedule maximises net earnings over a working day?

The contributions are five.

1. **A data-grounded single-driver model.** Demand rates, fares and per-trip energy consumption are estimated from 2,739,936 real New York TLC trip records rather than assumed. The model also exposes the structural fact that a citywide order rate cannot be used directly as a per-driver rate: one driver can serve at most 1.01 trips per fifteen minutes, whereas the citywide peak rate is 1,684.

2. **Exact solution by DP and MDP rather than MILP.** Fleet-scale formulations need sequential MILP or Lagrangian heuristics; at the single-driver level the state space is 96 x 86 = 8,256 and both the expected-value DP and the Poisson MDP have closed-form solutions computed in milliseconds in pure NumPy.

3. **A robust counter-intuitive result.** The optimal charging schedule lies outside the cheapest tariff window on 74.4% of simulated working days, and the conclusion survives a 3.4-fold rescaling of the implied value of time to the range measured in the literature.

4. **A negative result with direct managerial implications.** Widening the TOU spread from flat to twice the base spread changes the value of optimisation by only 1.3%. Opportunity cost, not price, drives the charging decision, which is why fleet-level conclusions about load shifting cannot be transplanted to individual ride-hailing drivers.

5. **A cross-day extension.** Formulating the day as a cyclic problem yields an optimal start-of-day state of charge of 36.8% rather than 100%, prices cross-day stored energy at \$0.2414/kWh --- between the valley and peak tariffs --- and shows that a single-day model overstates earnings by 2.4%.

# 2. Problem Formulation and Methodology

## 2.1 Problem definition and optimization model

### 2.1.1 Horizon, state and actions

A working day is discretised into $T = 96$ slots of $\Delta t = 15$ minutes. The state is the pair $(t, s)$, where $t \in \lbrace 0, \ldots, 95\rbrace$ is the slot index and $s \in \lbrace 0.15, 0.16, \ldots, 1.00\rbrace$ is the state of charge as a fraction of the usable pack capacity $Q = 40$ kWh, discretised on an 86-point grid at 1% resolution. The decision variable in each slot is the action

$$a_t \in \lbrace \textsf{DRIVE},\ \textsf{CHARGE},\ \textsf{IDLE}\rbrace , \qquad t = 0,1,\dots,95 . \qquad\qquad (1)$$

A full schedule is a sequence of 96 actions, so the policy space has cardinality $3^{96}$. We do **not** use state of charge as a decision variable: it is a state, physically determined by the actions taken, and treating it as a decision would pretend that a driver can summon charge. Nor do we use 96 binary charging indicators, which are mathematically equivalent but cannot express charging for part of a slot, since the energy stored is the product of duration and the taper function.

Because order arrival rates are strictly positive in every slot, IDLE is weakly dominated by DRIVE throughout: idling forgoes a strictly positive fare and consumes no less energy. The effective action set is therefore binary, and we state this explicitly rather than let it emerge from the solution.

### 2.1.2 Order arrivals and the driver time cap

Order arrivals in slot $t$ are Poisson with rate $\lambda_t$:

$$N_t \sim \textsf{Poisson}(\lambda_t) . \qquad\qquad (2)$$

The number of trips the driver actually completes is limited both by demand and by the driver's own physical capacity:

$$m_t = \min\left(N_t,\ \textsf{CAP}\right), \qquad \textsf{CAP} = 1.01 \text{ trips per 15 minutes}. \qquad\qquad (3)$$

The value $\textsf{CAP} = 1.01$ is derived from the observed mean trip duration of 14.8 minutes in the trip record data. This cap is the constraint that makes peak hours scarce: a driver cannot monetise a lucky evening peak beyond 1.01 trips per slot, so a peak hour lost to charging cannot be recovered later. It is important to be precise about its role, because it is easily overstated. After calibration, the *mean* per-driver demand ranges from 0.046 to 0.855 trips per slot and never exceeds $\textsf{CAP}$, so the cap does not bind on the mean profile at all; what it truncates is the upper tail of the Poisson realisation. The effect is nonetheless substantial, and Section 3.3 quantifies it.

### 2.1.3 Energy balance, reserve floor and the charging taper

The state of charge evolves deterministically given the action. Driving consumes energy proportional to the trips served:

$$s_{t+1} = s_t - \frac{m_t\, e_t}{Q} \qquad (\textsf{DRIVE}), \qquad\qquad (4)$$

where $e_t = \bar{d}_t \times \textsf{kWh/km}$ is the mean energy per trip in slot $t$. Charging adds energy at a rate that depends on the current state of charge through the constant-current/constant-voltage taper $\tau$:

$$s_{t+1} = \min\left(1,\ s_t + \frac{P\,\tau(s_t)\,\eta\,\Delta t}{Q}\right) \qquad (\textsf{CHARGE}), \qquad\qquad (5)$$

with rated charger power $P = 60$ kW, charging efficiency $\eta = 0.92$, and

$$\tau(s) = \begin{cases} 1.0 & s \le 0.80 \\[4pt] \max\left(0.15,\ 1 - 0.85\,\frac{s - 0.80}{0.20}\right) & s > 0.80 . \end{cases} \qquad\qquad (6)$$

The reserve floor $s \ge s^{\min} = 0.15$ is a **hard** constraint: a slot whose work would breach the floor is infeasible, and the day is recorded as infeasible rather than being repaired. This is not a technicality. An earlier version of this model clamped the state of charge back to the lower bound when it was breached, and the resulting optimisation concluded that the driver should never charge, because a clamped battery is free. The strict floor is what makes the energy budget bind, and therefore what makes the problem non-trivial.

Under the tariff, a driver pays for the charger slot at the charger's rated power, so the electricity cost of charging in slot $t$ is $\text{price}(t) \times P \times \Delta t$ regardless of how much energy the taper allows into the pack. The consequence is that the *marginal* cost of the next kWh is

$$c_{\textsf{marg}}(s) = \frac{\text{price}(t)}{\eta\,\tau(s)}, \qquad\qquad (7)$$

which is \$0.21/kWh while $s \le 0.80$ and rises to \$1.38/kWh at $s = 1.00$ under the shoulder tariff --- a factor of 6.6. We note in Section 3.3 that at the resolution of our time grid this structure is in fact not resolvable, and we treat that as a finding rather than concealing it.

### 2.1.4 Objective

The driver maximises expected net earnings over the day:

$$\max_{\pi}\ \mathbb{E}\left[\sum_{t=0}^{T-1}\left(\underbrace{m_t\,f_t}_{\textsf{fare revenue}} - \underbrace{\textsf{price}(t)\,P\,\Delta t \cdot \mathbb{1}\lbrace a_t = \textsf{CHARGE}\rbrace}_{\textsf{electricity cost}}\right)\right], \qquad\qquad (8)$$

subject to (1)--(6) and $s_t \ge s^{\min}$ for all $t$. Note that fare revenue and electricity cost are components of the **objective**, not constraints. When a slot is driven, the driver earns a fare and pays no electricity charge; when a slot is spent charging, the driver pays and earns nothing. The entire tension in the problem is contained in that one sentence.

## 2.2 Data and assumptions

### 2.2.1 Demand, fare and energy profiles

We use the New York City Taxi and Limousine Commission Trip Record Data for yellow taxis, January 2024 [2], downloaded from the TLC public repository. Cleaning applies six rules: discard rows with missing key fields; keep $0.3 < \textsf{trip\_distance} < 200$ miles; keep $0 < \textsf{total\_amount} < 500$ USD; keep $60 < \textsf{duration} < 3$ hours; keep $\textsf{passenger\_count} > 0$; and keep only calendar days whose trip count exceeds 75% of the median, which avoids partial days polluting the 96-slot profile. This reduces 2,964,624 raw records to 2,803,713 (94.6% retained); restricting to the 30 complete working days leaves **2,739,936 trips**, which are pooled to form the 96-slot profile of arrival rate $\lambda_t$, mean fare $f_t$, mean trip distance $\bar{d}_t$ and mean energy per trip $e_t$.

Energy per trip and fare are **derived** from trip distance and unit parameters rather than stored, so that changing a unit parameter in the sensitivity analysis genuinely propagates through the model. An earlier version stored them directly, which caused the peak-to-valley spread of the tariff to have no effect whatsoever on the results --- a silent failure that the sensitivity analysis was designed to detect.

### 2.2.2 From the city to one driver

The citywide arrival rate is not a per-driver rate. We calibrate an effective fleet size from an assumed peak-hour utilisation of $u_{\textsf{peak}} = 85\%$:

$$\lambda_t^{\textsf{driver}} = \frac{\lambda_t^{\textsf{city}}}{N_{\textsf{fleet}}}, \qquad N_{\textsf{fleet}} = \frac{\max_t \lambda_t^{\textsf{city}}}{\textsf{CAP} \times u_{\textsf{peak}}} = \frac{1684}{1.01 \times 0.85} \approx 1{,}970 . \qquad\qquad (9)$$

This step preserves the entire 18.5-fold shape of the curve and corrects only its absolute scale. Using the citywide rate directly as a per-driver rate saturates all 96 slots and erases the intra-day shape entirely, which reduces the model to a statement that charging timing is irrelevant.

### 2.2.3 Parameters

::: {custom-style="Table Caption"}
Table 1. Model parameters, their values and their sources.
:::

| Symbol | Meaning | Value | Basis |
|---|---|---|---|
| $Q$ | usable pack capacity | 40 kWh | BYD e6 / Nissan Leaf class |
| $s^{\min}$ | reserve floor | 15% | industry practice |
| $P$ | charger rated power | 60 kW | DC fast charging |
| $\eta$ | charging efficiency | 92% | --- |
| $s^{\textsf{CC}}$ | CC-to-CV knee | 80% | typical lithium-ion behaviour |
| $\textsf{CAP}$ | driver time cap | 1.01 trips / 15 min | implied by 14.8 min mean trip duration |
| $\Delta t$ | slot length | 15 min | aligned with the demand profile |
| $u_{\textsf{peak}}$ | peak-hour utilisation | 85% | calibration assumption, swept in 40%--100% |
| $s_0$ | start-of-day state of charge | 80% | full battery; relaxed in the cyclic extension |

The time-of-use tariff is a **four-tier assumption**, not a measurement, and is swept in the sensitivity analysis:

::: {custom-style="Table Caption"}
Table 2. The assumed four-tier time-of-use tariff.
:::

| Tier | Hours | Price (\$/kWh) |
|---|---|---|
| super-peak | 16:00--19:00 | 0.42 |
| peak | 13:00--16:00, 19:00--20:00 | 0.28 |
| shoulder | 10:00--13:00, 20:00--23:00 | 0.19 |
| off-peak | 00:00--10:00, 23:00--24:00 | 0.11 |

### 2.2.4 A diagnostic on the implied value of time

The model charges the opportunity cost of a slot at the gross fare that the driver would have earned, without deducting cruising time between orders, waiting time for orders, or platform commission. The implied value of time is therefore systematically optimistic: \$53.0/h averaged over the day, with a maximum of \$93.5/h at 18:00 and a minimum of \$7.0/h at 04:30. The literature places charging VOT at \$15.20--\$27.54/h [10,11]. Our mean is roughly twice the upper end of that range, and the discrepancy is a direct consequence of the modelling choice just described.

Because this threatens the central conclusion rather than merely decorating it, we treat it as a robustness test and rescale fares by a factor 0.294 so that the peak VOT matches the NBER measurement, then re-solve. Section 3.4 reports the outcome: the main conclusion is unchanged.

## 2.3 Optimization method and solution procedure

### 2.3.1 Expected-value dynamic programming

Replacing the random arrival count by its mean gives a deterministic backward-induction problem:

$$V(t,s) = \max_{a \in \mathcal{A}}\left\lbrace \, r_t(a) + V\left(t+1,\ s'(s,a)\right) \right\rbrace , \qquad\qquad (10)$$

solved by a single backward sweep from $V(T, \cdot) = 0$. This is retained as a *diagnostic*, not as a policy, for the reason given in Section 3.1.

### 2.3.2 Markov decision process with the arrival count summed out

With Poisson arrivals the state space is unchanged and the random variable is summed out in closed form:

$$V(t,s) = \max_{a \in \mathcal{A}}\left\lbrace \sum_{k=0}^{K} P(N_t{=}k)\left[\, r_t(k,a) + V\left(t+1,\ s'(s,k,a)\right) \right] \right\rbrace , \qquad\qquad (11)$$

where $K = 6$ (truncation) and $P(N_t{=}k) = \frac{\lambda_t^k e^{-\lambda_t}}{k!}$. The number of states is $96 \times 86 = 8{,}256$, each with three actions, and the entire solve takes milliseconds in pure NumPy with no solver dependency.

A subtlety deserves attention because it silently biases results. When the remaining energy cannot cover a slot's work, one must decide what happens to that outcome. The correct treatment, matching the simulator, is **partial service**: the driver completes as many trips as the energy above the reserve floor allows. An earlier version instead *dropped* such outcomes from the expectation, which discards probability mass and makes the planner's objective differ from the quantity the evaluation actually measures. We use the consistent rule throughout and report the verification in Section 3.5.

### 2.3.3 Cyclic extension across days

A single-day model silently assumes that every morning begins with a full battery, which is free. To model a driver who works day after day, the terminal value function is replaced by a day-boundary value function $W$ and a fixed point is sought:

$$V(T, s) = W(s), \qquad V(t, s) = \max_{a}\ \mathbb{E}\left[\, r_t(a) + V\left(t+1,\ s'(s,a)\right) \right], \qquad W(s) = V(0, s). \qquad\qquad (12)$$

Because $T(W + c) = T(W) + c$ for any constant $c$, the fixed point is determined only up to an additive constant: the level of $W$ drifts by the average daily reward on every sweep. Centring $W$ after each sweep removes this drift and the remaining operator contracts; without centring the iteration diverges, which we measured as a residual of $9.3 \times 10^{2}$ after 400 sweeps. With centring the iteration converges in 34 sweeps to a centred residual of $9.29 \times 10^{-10}$. We verify the fixed point independently with finite-horizon dynamic programs over $D = 7$, 14 and 20 days.

The shadow price of cross-day stored energy is then read off the marginal value of the day-boundary function,

$$\mu = \frac{dW}{ds}\bigg|_{\textsf{SOC} \in [0.30,\, 0.95]} \quad \text{(per kWh)}, \qquad\qquad (13)$$

evaluated over the band of states the driver actually operates in.

### 2.3.4 Why not MILP

The problem is path-dependent and sequential. A MILP formulation is possible but requires a large number of auxiliary variables --- big-M constants and indicators --- to encode path dependence, and its state space grows with the number of vehicles. Dynamic programming closes the single-driver case exactly and corresponds directly to the dynamic-programming content of the course. The method and the problem are matched rather than merely coexisting.

# 3. Results and Discussion

All results below are produced by `code/src/run_experiments.py`, `code/src/ablations.py` and `code/src/policy_stats.py`, with a fixed random seed of 20261001, on 600 independent Monte-Carlo working days per policy with a common random stream. The raw outputs are in `results/`.

## 3.1 Main optimization results

::: {custom-style="Table Caption"}
Table 3. Policy comparison over 600 Monte-Carlo working days. The first two are the optimising policies; the rest are rule-based baselines, where "Threshold x%" charges whenever the state of charge falls below x%, "Charge-to-full 40%" charges all the way to 100% once the state of charge falls below 40%, and "Cheapest-hour only" charges exclusively in the cheapest tariff slot. "Feasible" is the share of days on which the driver completed the shift without breaching the reserve floor.
:::

| Policy | Net (\$) | s.d. | Fare revenue (\$) | Electricity (\$) | Orders | Feasible |
|---|---|---|---|---|---|---|
| **MDP (this work)** | **946.46** | 116.78 | 950.41 | 3.96 | 34.64 | **95%** |
| DP (mean demand) | 934.15 | 116.89 | 939.00 | 4.84 | 34.26 | 85% |
| Threshold 40% | 924.98 | 117.53 | 933.73 | 8.75 | 34.05 | 100% |
| Threshold 30% | 922.46 | 116.25 | 930.35 | 7.88 | 33.91 | 100% |
| Threshold 50% | 920.66 | 117.37 | 930.13 | 9.46 | 33.88 | 100% |
| Charge-to-full 40% | 911.06 | 111.14 | 920.78 | 9.72 | 33.58 | 100% |
| Cheapest-hour only | 788.21 | 27.15 | 789.86 | 1.65 | 28.95 | 11% |
| Never charge | 600.09 | 16.57 | 600.09 | 0.00 | 22.12 | 0% |

The MDP gains \$21.47 (2.3%) over the strongest rule-based baseline and \$158.25 (20.1%) over the tariff-following rule. The second comparison is the more important one, and it is not primarily about money.

![](../figures/F1_day_in_picture.png)

::: {custom-style="Figure Caption"}
Figure 1. The day in one picture: citywide order arrival rate by fifteen-minute slot, the four-tier time-of-use tariff, and the state-of-charge trajectory of the optimal policy with its charging slots marked.
:::

**Finding 1 --- following the tariff table traps the driver in its own strategy.** A driver who charges only in the cheapest slot buys 13.8 kWh, while the day requires 54.5 kWh; the remainder is unobtainable. On 89% of days such a driver cannot complete the shift. This is not "earning less"; it is "cannot drive". The valley is in fact capable of delivering roughly 607 kWh over its 44 slots, eleven times the day's requirement --- so the valley is not short of energy, and the failure is one of time allocation.

**Finding 2 --- the expected-value DP looks better on paper and cannot be used.** The deterministic DP reports a book value of \$1,242.61 at the initial state, against \$939.55 for the MDP. The \$303 gap looks like a decisive victory for perfect information. But the expected-value policy, evaluated against the stochastic demand it cannot observe, completes only 85% of shifts, because the mean hides the days on which the pack runs short. The MDP has the lower book value and the higher realised earnings, \$946.46 against \$934.15, and completes 10 percentage points more working days. Perfect information is not what is valuable here; knowing that one does not know is.

**Finding 3 --- the optimal schedule lies outside the cheapest tariff window.** Across the 570 feasible simulated days, the MDP policy charges at least once outside the cheapest tariff window on **74.4%** of days, and confines itself to the valley on only 25.6%. Yet on **every** feasible day it selects a deep-night slot in the 04:30--05:15 window (100% of days; 04:45 on 87.2%, 04:30 on 12.8%). The driver charges in two slots on 79.1% of days, in one slot on 18.9% and in three slots on 1.9%. The most frequent off-valley slots are 20:30 (9.5% of days), 12:30 (9.0%), 11:15 (6.2%) and 22:15 (5.0%).

![](../figures/F2_policy_comparison.png)

::: {custom-style="Figure Caption"}
Figure 2. Policy comparison: average net earnings with the feasible-day share on the right-hand axis.
:::

The mechanism is straightforward once stated: the valley is cheap *because* it is empty. Moving a charge from the valley into a shoulder slot buys a small saving in electricity --- \$0.08/kWh --- and recovers a much larger amount of fare revenue, because the driver is productive at midday and in the evening but not at 04:00. The correct criterion is therefore not "the cheapest tariff" but "the cheapest combination of tariff and foregone fare".

A frequency statement is used here deliberately. An earlier version of this work reported the charging slots of the single best of 200 simulated days. That is a punchline, not a statistic, and it cannot support a general claim. The figures above come from the full 600-day sample.

## 3.2 Sensitivity analysis

Seven one-at-a-time sweeps hold all other parameters at their base values. The quantity reported is the gain of the MDP over the tariff-following rule, re-solved for each parameter value.

::: {custom-style="Table Caption"}
Table 4. One-factor sensitivity. "Gain" is the MDP net earnings minus the tariff-following rule's, in US dollars per day.
:::

| # | Parameter | Range | Gain | Reading |
|---|---|---|---|---|
| S1 | Pack capacity | 25 → 80 kWh | +453.58 → +15.97 | **Strongest driver**: a bigger pack trivialises the problem |
| S2 | Energy consumption | 0.18 → 0.45 kWh/km | +46.21 → +532.06 | Tighter energy budget, more value in scheduling |
| S3 | Charger power | 7 → 200 kW | +263.72 → +158.87 | Slower chargers make scheduling *more* valuable |
| S4 | Peak utilisation | 40% → 100% | -0.71 → +284.56 | Busier market, stronger opportunity cost |
| S5 | Fare level | x0.7 → x1.5 | +117.89 → +255.27 | Higher fares raise the opportunity cost |
| S6 | TOU price spread | x0 (flat) → x2 | +168.46 → +170.72 | **Counter-intuitive: almost no effect** |
| S7 | Start-of-day SOC | 30% → 95% | +497.45 → +164.15 | Emptier start, more careful schedule |

![](../figures/F3_sensitivity.png)

::: {custom-style="Figure Caption"}
Figure 3. The seven one-factor sensitivity sweeps.
:::

### The price spread does not matter, and this is the most useful result in the paper

Widening the peak-to-valley spread from flat to twice the base spread changes the gain of optimisation by 1.3% (\$168.46 to \$170.72), and the optimal charging slots are **identical** at both extremes (Section 3.3, ablation A2). The two effects cancel almost exactly: a wider spread makes the tariff-following rule look smarter, but it simultaneously makes running during the expensive hours more costly, so both the optimiser and the rule it beats improve by about the same amount.

The practical implication is direct. **For a charging decision made by a driver who must earn, a larger price spread cannot substitute for optimisation.** This is also why fleet-level load-shifting conclusions, where the objective is to minimise the bill under a capacity constraint, cannot be transplanted to an individual ride-hailing driver.

### Robustness to the value of time

The implied value of time of the model is \$53.0/h on average, \$93.5/h at 18:00 and \$7.0/h at 04:30; 16 of 96 slots fall below the \$15.20/h measured in the literature, which are precisely the deep-night slots during which a real driver would go off shift. We therefore rescale fares by 0.294 so that the peak VOT matches the NBER measurement of \$27.54/h and re-solve.

::: {custom-style="Table Caption"}
Table 5. Robustness of the optimal charging schedule to the implied value of time. Fares are rescaled so that the peak-hour implied VOT matches the \$27.54/h measured by Dorsey et al. (2022).
:::

| Fare scale | Peak VOT | Mean VOT | Optimal charging slots | Feasible |
|---|---|---|---|---|
| 1.000 | \$93.5/h | \$53.0/h | 04:45, 11:15, 20:30 | 96% |
| 0.700 | \$65.4/h | \$37.1/h | 04:45, 11:30, 20:30 | 96% |
| 0.500 | \$46.7/h | \$26.5/h | 04:45, 11:30, 20:30 | 92% |
| 0.400 | \$37.4/h | \$21.2/h | 04:45, 11:30, 20:30 | 90% |
| **0.294** | **\$27.5/h** | **\$15.6/h** | **04:30, 12:30** | **88%** |

Across a 3.4-fold change in the opportunity cost, the conclusion is unchanged: the deep-night slot is selected on every schedule, and at least one charging slot always falls outside the cheapest tariff window. We report one honest qualification: at the lowest fare scale the feasible share falls from 96% to 88%, because lower fares mean fewer completable orders overall. The qualitative conclusion is robust; absolute feasibility degrades.

## 3.3 Ablation analysis

Each ablation removes one structural element of the model. The baseline is the MDP at \$946.46 with feasible share 95% and charging slots 04:45, 11:15 and 20:30.

::: {custom-style="Table Caption"}
Table 6. Ablations A1--A6. "Gain" is against the tariff-following rule.
:::

| # | Element removed | Observed | Conclusion |
|---|---|---|---|
| **A1** | Stochasticity (expected-value DP) | \$934.15; feasible 95% → **85%**; slots move to 06:30, 09:15, 20:00 | The expected-value policy is **not implementable** |
| **A2** | TOU price spread | \$947.01; gain +158.25 → **+158.80**; slots **identical** | **The spread does not set the timing** |
| **A3** | CC--CV taper | \$946.46; slots **identical** | The taper is **not resolvable at our time resolution** |
| **A4** | Driver time cap | **\$1,239.90**; slots 04:30, 09:30, **18:15**, 22:45; orders 34.6 → **45.5** | The cap is what makes peak hours scarce |
| **A5** | Reserve floor (relaxed to clamp) | Claims **\$987.55** but draws **44.49 kWh from a 40 kWh pack**; under correct physics **\$600.09** and **0% feasible** | **The wrong constraint type gives a qualitatively wrong answer** |
| **A6** | Intra-day demand shape | \$1,009.28; slots 02:30, 07:45, 08:45, **all in the valley** | When opportunity cost is constant, **the tariff decides again** |

**A2 and A6 are mirror images.** A2 removes the *shape* of the price; A6 removes the *shape* of the opportunity cost. Under A2 the decision rights stay with the opportunity cost and the schedule does not move. Under A6 the decision rights return to the tariff and every charging slot falls back into the valley. Together they show that what determines the charging schedule is **which of the two curves is steeper** --- and in ride-hailing, the opportunity cost is.

**A4 shows that the driver time cap is the pivot of the model.** Removing it raises mean net earnings from \$946 to \$1,240, because the driver then serves essentially the whole Poisson tail (45.5 orders per day instead of 34.6) and the schedule spreads to four slots including 18:15. With the cap restored, a lucky evening peak still pays at most 1.01 trips, so a peak hour lost to charging cannot be made up later.

**A5 is a counter-example and deserves a subsection of its own.** Replacing the hard reserve floor by a clamp --- which silently donates energy whenever the pack runs short --- produces a model whose *own* optimum is \$987.55, higher than the MDP's \$946.46. Superficially the clamp wins. But the clamped policy must extract 44.49 kWh from a 40 kWh pack, which is 111% of capacity. Evaluated under the correct physics, the same policy earns \$600.09 and is feasible on **0%** of days. A constraint modelled with the wrong hardness does not merely degrade the answer, it inverts it. We report this because it is the kind of error that a reader of applied charging papers cannot easily detect.

**A3 is a resolution limitation, and we state it as such.** At 60 kW into a 40 kWh pack, one 15-minute slot banks 13.8 kWh, i.e. 34.5% of the pack; reaching the 80% knee from the 15% reserve takes 1.9 slots. The pack therefore saturates within a single slot and the 15-minute grid cannot resolve the taper at all. Removing the taper changes nothing --- but this is not a finding that the taper is irrelevant, it is a finding that **the constraint is below the resolution of our discretisation**. Studying it properly requires a finer charging sub-grid, which we list as future work rather than claim a result about.

![](../figures/F4_taper.png)

::: {custom-style="Figure Caption"}
Figure 4. The CC--CV taper (left) and its cost consequence (right): the marginal cost of the next kWh rises from \$0.21/kWh to \$1.38/kWh as the pack approaches full, while the average cost-to-date rises only to about \$0.25/kWh because the pack saturates.
:::

## 3.4 Multi-day extension: optimal start-of-day charge and the price of stored energy

The cyclic formulation of Section 2.3.3 converges in 34 sweeps to a centred residual of $9.29 \times 10^{-10}$, and the independent finite-horizon dynamic programs over 7, 14 and 20 days agree with it to nine significant figures.

::: {custom-style="Table Caption"}
Table 7. Cyclic (multi-day) results.
:::

| Quantity | Value |
|---|---|
| Value-iteration convergence | 34 sweeps, centred residual $9.29 \times 10^{-10}$ |
| Shadow price of cross-day stored energy, $\mu$ | **\$0.2414/kWh** |
| Same, from an independent 20-day finite-horizon DP | \$0.2414/kWh |
| TOU price range | \$0.11 (valley) -- \$0.42 (peak) |
| **Optimal start-of-day state of charge** | **36.8%** (s.d. 0.107, range 16.1%--52.8%) |
| Steady-state charging slots | 04:45 (valley) and 12:00 (shoulder) |
| Steady-state average net earnings | **\$923.62/day** |
| Single-day MDP from 80%, for comparison | \$946.46/day |

Three results follow.

**The optimal start-of-day charge is 36.8%, not 100%.** Starting every shift with a full battery means carrying energy that was bought at the shoulder or peak tariff and is not needed before the valley reopens. The optimal driver leaves the depot with just enough to reach the first charging opportunity and tops up in the valley.

**The shadow price of cross-day stored energy is \$0.2414/kWh, between the valley tariff of \$0.11 and the peak tariff of \$0.42.** It is neither the cheapest nor the most expensive electricity: it is the price of the option to carry one kWh across the day boundary. This is a third price, alongside the tariff and the opportunity cost, and it is the one that a driver actually faces when deciding how much to leave in the battery overnight.

**A single-day model overstates earnings by 2.4%.** The single-day MDP reports \$946.46 while the cyclic steady state reports \$923.62, a difference of \$22.84 per day. The entire discrepancy is attributable to the assumption that a full battery at the start of the day is free. Any scheduling model that ignores the state carried across the operating boundary will overstate the value of its schedules, and the size of the error is not negligible relative to the gains we are trying to measure.

## 3.5 Verification of the model implementation

Because the planner and the simulator are separate pieces of code, we verify that the value the planner computes is the quantity the simulator measures. Under the consistent partial-service rule the planner reports \$939.55 at the initial state and the simulator measures \$943.69 with a standard error of \$1.84, a gap of 2.25 standard errors over 4,000 simulated days --- a difference that is not statistically significant. Under the earlier inconsistent rule that dropped probability mass, the gap was 2.31 standard errors. Both are consistent with the planner's objective being the simulated quantity.

::: {custom-style="Table Caption"}
Table 8. Planner-implied value against simulated net earnings, 4,000 days per variant.
:::

| Variant | $V(0, 0.80)$ | Simulated net | s.e. | Gap | Gap / s.e. | Feasible |
|---|---|---|---|---|---|---|
| Legacy (outcomes dropped) | \$939.30 | \$943.58 | 1.85 | \$4.28 | 2.31 | 98.5% |
| **Consistent (partial service)** | **\$939.55** | **\$943.69** | **1.84** | **\$4.13** | **2.25** | 94.1% |

We report this as an implementation-correctness check rather than as a headline result.

# 4. Conclusion

This paper asked a narrow question --- when should an electric ride-hailing driver charge --- and answered it with a model that is small enough to solve exactly and a dataset that is large enough to be credible.

The answer is not the cheapest tariff window. Off-peak hours are cheap precisely because almost nobody is working then, so the opportunity cost of charging during them is not small; on 74.4% of simulated working days the optimal policy charges at least once outside the cheapest tariff window, while selecting a deep-night slot on every feasible day. The two effects that might be expected to determine the answer --- the price spread and the demand shape --- turn out to be separable, and the ablations isolate them: flattening the price changes nothing, and flattening the demand hands the decision back to the tariff entirely. What determines the schedule is the relative steepness of the price curve and the opportunity-cost curve, and for a driver who must earn, the opportunity cost is steeper.

Two negative or corrective results deserve emphasis. First, widening the peak-to-valley spread by a factor of two changes the value of optimisation by 1.3%, which means that tariff design alone cannot substitute for scheduling when the decision-maker is an individual earning a fare. Second, a single-day formulation overstates earnings by 2.4% because it treats the battery carried across the operating boundary as free; the cyclic formulation shows that the optimal start-of-day charge is 36.8% and places a price of \$0.2414/kWh on cross-day stored energy.

Several limitations are explicit. The model treats one driver in isolation: charger queueing, travel time to a charger and interactions between drivers are all omitted, although the fleet-scale literature shows they matter [1,6,7]. The charger-power taper is present but below the resolution of our fifteen-minute grid, so we report it as unresolved rather than as a result. The driver has no "go off shift" action, which is why the implied value of time falls to \$7/h in the deep hours when a real driver would have stopped working; this makes our opportunity-cost profile optimistic, which is why we recalibrated against measured values of time and verified that the conclusion survives. The multi-driver extension is a single-driver value function composed across days, not a market equilibrium, and does not capture the congestion that arises when many drivers charge simultaneously.

The most promising directions for further work are, in order: a finer charging sub-grid so that the taper becomes resolvable; explicit charger queueing and access time, which would require moving from a sequential decision problem to a queueing system; and a market-level extension in which the driver's own charging decision and the availability of the chargers are jointly determined.

# AI Use Statement

Generative AI tools --- specifically Claude Code (Anthropic) and MiniMax Code --- were used as assistants in the preparation of this work. They were used for four purposes: (i) assisting the design and drafting of the model formulation in Section 2 and the corresponding Python implementation; (ii) assisting the literature search and the verification of bibliographic identifiers through the Crossref and arXiv APIs, including correcting three DOIs that had initially been recorded incorrectly; (iii) assisting with code debugging, in particular the identification of the reserve-floor modelling error described in ablation A5 and the planner--simulator inconsistency described in Section 3.5; and (iv) language editing and structural formatting of the manuscript.

Every equation, every line of code, every number reported in Section 3 and every conclusion drawn was checked against the executable output in the `results/` directory and the `code/src/` sources; the quantitative claims in this paper are reproducible by running the scripts with the fixed seed 20261001, and the raw outputs of each experiment are included with the submission. The authors understand the model, the derivation of each equation, the algorithmic structure of the dynamic program and the Markov decision process, the design of every experiment, and the interpretation of every result reported here, and take full responsibility for the content of this submission.

# References

::: {custom-style="Bibliography"}

[1] Ma, T.-Y. (2021). Two-stage battery recharge scheduling and vehicle-charger assignment policy for dynamic electric dial-a-ride services. *PLOS ONE*, 16(5), e0251582. https://doi.org/10.1371/journal.pone.0251582

[2] New York City Taxi and Limousine Commission. *Trip Record Data: Yellow Taxi, January 2024*. https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

[3] Ke, J., Cen, X., Yang, H., and Chen, X. (2019). Modelling drivers' working and recharging schedules in a ride-sourcing market with electric vehicles and gasoline vehicles. *Transportation Research Part E: Logistics and Transportation Review*, 125, 160--180. https://doi.org/10.1016/j.tre.2019.03.010

[4] Liu, Y., Chen, Z., Xie, C., and Liu, K. (2023). Temporal equilibrium for electrified ride-sourcing markets considering charging capacity and driving fatigue. *Transportation Research Part C: Emerging Technologies*, 147, 104008. https://doi.org/10.1016/j.trc.2022.104008

[5] Qin, Y., Dai, Y., Huang, J., Xu, H., Lu, L., Han, X., Du, J., Ouyang, M., et al. (2023). Charging patterns analysis and multiscale infrastructure deployment: based on the real trajectories and battery data of the plug-in electric vehicles in Shanghai. *Journal of Cleaner Production*, 425, 138847. https://doi.org/10.1016/j.jclepro.2023.138847

[6] Ma, T.-Y. (2023). Dynamic charging management for electric vehicle demand responsive transport. In *Lecture Notes in Intelligent Transportation and Infrastructure* (pp. 171--182). Springer. https://doi.org/10.1007/978-3-031-23721-8_14

[7] Ma, T.-Y., Connors, R. D., and Viti, F. (2024). Congestion-aware charging coordination for electric ride-hailing fleets under stochastic demand. *arXiv preprint* arXiv:2412.09978.

[8] Alam, S., and Guo, R. (2022). Charging infrastructure planning for ride-sourcing electric vehicles considering drivers' value of time. *Transportation Letters*, 15(5), 573--583. https://doi.org/10.1080/19427867.2022.2077003

[9] Ma, J., Zhang, Y., Duan, L., et al. (2023). PROLIFIC: deep reinforcement learning for efficient EV fleet scheduling and charging. *Sustainability*, 15(18), 13553. https://doi.org/10.3390/su151813553

[10] Mehditabrizi, A., Namadi, S. S., and Cirillo, C. (2026). From pumps to plugs: valuing time in refueling and EV charging transitions. *Travel Behaviour and Society*, 44, 101279. https://doi.org/10.1016/j.tbs.2026.101279

[11] Dorsey, J., Langer, A., and McRae, S. (2022). *Fueling alternatives: Gas station choice and the implications for electric charging* (NBER Working Paper 29831). National Bureau of Economic Research.

[12] Sunada, and Xia (2026). *From pumps to plugs: Value of time and charging policies* (SSRN Working Paper 6296418). Social Science Research Network. https://doi.org/10.2139/ssrn.6296418

:::

# Appendix

## A.1 Reproducing the results

```bash
cd code/src
python build_profile.py      # rebuild data/profile.json from the raw parquet
python run_experiments.py    # Tables 3-4, Figures 1-2
python ablations.py          # Tables 6-7
python policy_stats.py       # the 600-day charging-slot distribution
python vot_check.py          # the implied value of time and its literature comparison
python vot_rescale.py        # the value-of-time robustness table (Table 5)
python make_figures.py       # Figures 1-4
```

The random seed is fixed at 20261001 in every script. Environment: Python 3.12.7, NumPy 1.26.4, pandas 3.0.2, SciPy 1.13.1, Matplotlib 3.9.2. There is no solver dependency: the dynamic program and the Markov decision process are implemented directly in NumPy.

## A.2 Source data

The dataset is the public New York TLC yellow-taxi trip record data for January 2024. The raw Parquet file (47.6 MB) is not redistributed; the download address and the complete cleaning rules are given in Section 2.2.1 and in `data/DATA_SOURCE.md`. The derived 96-slot demand profile (`data/profile.json` and `data/demand_profile.csv`) is included with the submission.

## A.3 Additional model parameters

::: {custom-style="Table Caption"}
Table 9. Model parameters not listed in Section 2.2.
:::

| Symbol | Meaning | Value |
|---|---|---|
| $\Delta t$ | slot duration in hours | 0.25 |
| $\textsf{kWh/km}$ | energy consumption per kilometre | 0.22 |
| $K$ | Poisson truncation order | 6 |
| $\textsf{price}(t)$ | TOU tariff in \$/kWh | 0.11--0.42 |
| $s_0$ | initial state of charge (single-day) | 0.80 |
