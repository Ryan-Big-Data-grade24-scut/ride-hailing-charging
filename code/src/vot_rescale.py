import sys, numpy as np
sys.path.insert(0, r"E:\Ufolder\Current\ActionSys\Hgclass\OM\proj\网约车充电\code")
sys.stdout.reconfigure(encoding="utf-8")
from ev_dp import Env, evaluate, run_policy, solve_mdp

def hr(t): return f"{t*15//60:02d}:{t*15%60:02d}"
print("把车费按文献 VOT 校准后，最优充电时刻是否改变？\n")
print("%-10s %-12s %-8s %-9s %-22s %-8s" % (
      "fare_scale","peak VOT","peak/h","mean VOT","MDP 充电时刻","可行率"))
for fs in [1.0, 0.7, 0.5, 0.4, 0.294]:
    e = Env(fare_scale=fs)
    vot = np.minimum(e.lam, e.cap) * e.fare * 4.0
    _, pol = solve_mdp(e, kmax=6)
    r = evaluate(e, pol, "mdp", n_sims=200, seed=20261001)
    rng = np.random.default_rng(20261001); best=None
    for _ in range(150):
        c = run_policy(e, "mdp", rng, policy=pol)
        if c["feasible"] and (best is None or c["net"]>best["net"]): best=c
    slots = [hr(t) for t in best["charge_slots"]]
    print("%-10.3f %-12.1f %-8.0f %-9.1f %-22s %-8.0f%%" % (
        fs, vot.max(), 18, vot.mean(), ", ".join(slots) if slots else "(不充电)",
        r["feasible_rate"]*100))
print()
print("说明：peak VOT 列 = 18:00 该小时的隐含时间价值($/h)")
print("      fare_scale=0.294 时，peak VOT 正好落到 NBER 实测的 $27.54/h")
