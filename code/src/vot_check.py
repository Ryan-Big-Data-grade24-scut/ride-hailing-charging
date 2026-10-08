import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from ev_dp import Env
env = Env()
lam, fare, cap = env.lam, env.fare, env.cap
rev_slot = np.minimum(lam, cap) * fare
vot = rev_slot * 4.0     # $/hour

def hr(t): return f"{t*15//60:02d}:{t*15%60:02d}"
print("=== 模型内生的时间价值 (implied VOT) —— 用每司机订单率 ===")
print("  fleet size = %.0f vehicles" % env.n_drivers)
print("  %-7s %12s %10s" % ("time","orders/15m/drv","VOT $/h"))
for t in [8, 20, 32, 40, 46, 52, 60, 68, 72, 80, 88]:
    print("  %-7s %12.3f %10.1f" % (hr(t), lam[t], vot[t]))
print()
print("  min VOT = $%.1f/h  @ %s" % (vot.min(), hr(int(vot.argmin()))))
print("  max VOT = $%.1f/h  @ %s" % (vot.max(), hr(int(vot.argmax()))))
print("  mean VOT= $%.1f/h" % vot.mean())
print()
print("=== 文献经验值 ===")
print("  Mehditabrizi/Namadi/Cirillo (2026, TBS 44:101279)  $15.20/h")
print("  Dorsey/Langer/McRae (2022, NBER WP 29831)          $27.54/h  (=中位工资 89%)")
print("  Sunada & Xia (2026, SSRN 6296418)                  平均工资的 27%")
print()
for thr,lab in [(15.2,"$15.20"),(27.54,"$27.54")]:
    n = int((vot > thr).sum())
    print("  VOT 高于 %-6s 的时段: %2d / 96" % (lab, n))
print()
below = int((vot < 15.2).sum())
print("=== 关键诊断 ===")
print("  本模型中『上路一小时< $15.2，不值得』的时段: %d / 96" % below)
if below:
    print("  -> 深夜时段司机本来就该下线；我们模型没有『下线』这个动作。")
print("  本模型 min VOT $%.1f/h 相对文献下界 $15.2/h 高 %.1f 倍" %
      (vot.min(), vot.min()/15.2))
print("  说明：模型用『原始订单到达率×车费』当作机会成本，")
print("        未扣空驶(cruising)、等单、以及平台抽成，因此系统性偏乐观。")
