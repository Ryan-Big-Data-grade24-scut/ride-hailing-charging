"""Propagate the corrected off-valley charging statistic through the docs.

`policy_stats.py` used to count the numerator over all 600 simulated days
while dividing by the 570 feasible ones, which inflated the share from the
true 74.4% to 76.3%. The script has been fixed; this updates every place in
the repository that quoted the inflated number.

Run:  python tools/fix_offvalley_claims.py
"""
import io
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))

EDITS = [
    ("docs/experiment/README.md",
     "在 570 个可行工作日中，**MDP 策略有 76.3% 的日子会在最便宜电价窗口之外充电**（第二格典型落在 11:15–12:30 或 20:30–22:30）；只有 28.9% 的日子完全待在谷段。",
     "在 570 个可行工作日中，**MDP 策略有 74.4% 的日子会在最便宜电价窗口之外充电**（第二格典型落在 11:15–12:30 或 20:30–22:30）；只有 25.6% 的日子完全待在谷段。"),
    ("docs/experiment/README.md",
     '方向一致，但结论从"某一天这样充"升级成"**76.3% 的日子这样充**"。',
     '方向一致，但结论从"某一天这样充"升级成"**74.4% 的日子这样充**"。'),
    ("README.md",
     "> 动态规划给出的策略在 **76.3% 的工作日**里会在最便宜电价窗口**之外**充电 —— 但**每一天**都会选深夜那一格。",
     "> 动态规划给出的策略在 **74.4% 的工作日**里会在最便宜电价窗口**之外**充电 —— 但**每一天**都会选深夜那一格。"),
    ("README.md",
     "| 至少有一格落在最便宜电价窗口**之外**的工作日 | **76.3%**（435 / 570 可行日） |",
     "| 至少有一格落在最便宜电价窗口**之外**的工作日 | **74.4%**（424 / 570 可行日） |"),
    ("README.md",
     "| 完全待在谷段的工作日 | 28.9% |",
     "| 完全待在谷段的工作日 | 25.6% |"),
    ("README.md",
     '> 谷段是 00:00–09:45 和 23:00–23:45。**结论不是"某一天这样充"，而是"76.3% 的日子这样充"。**',
     '> 谷段是 00:00–09:45 和 23:00–23:45。**结论不是"某一天这样充"，而是"74.4% 的日子这样充"。**'),
]

for rel, old, new in EDITS:
    p = os.path.join(ROOT, rel)
    t = io.open(p, encoding="utf-8").read()
    if old not in t:
        print("NOT FOUND in", rel, ":", old[:45])
        continue
    io.open(p, "w", encoding="utf-8").write(t.replace(old, new, 1))
    print("updated", rel)

# nothing should still quote the inflated figure
for rel in ("README.md", "docs/experiment/README.md"):
    t = io.open(os.path.join(ROOT, rel), encoding="utf-8").read()
    for stale in ("76.3", "28.9"):
        if stale in t:
            print("STILL STALE in", rel, ":", stale)
print("done")
