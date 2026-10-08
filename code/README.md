# Code

全部源码。纯 numpy / pandas / matplotlib，**无求解器依赖**（不需要 Gurobi / CVXPY / PuLP）。

---

## 运行

```bash
cd code/src

# 0) 首次运行前，下载原始数据（47.6 MB，只需一次）
#    放到 <repo>/data/yellow_tripdata_2024-01.parquet

# 1) 从原始订单生成 96 格需求画像  →  data/profile.json
python build_profile.py

# 2) 跑全部实验（策略对比 + 7 组敏感性）→ results/
python run_experiments.py

# 3) 时间价值校准与稳健性检验（独立脚本）
python vot_check.py        # 计算模型隐含的时间价值
python vot_rescale.py      # 按文献 VOT 重标定后重解 MDP

# 4) 生成 4 张图 → figures/
python make_figures.py
```

**随机种子固定为 `20261001`**（在 `run_experiments.py` 顶部）。改参数后重跑，结果应完全一致。

---

## 文件职责

| 文件 | 职责 |
|---|---|
| `build_profile.py` | 读 47.6 MB parquet → 清洗 → 96 格需求画像。**能耗/车费由距离推导**，不直接存 |
| `ev_dp.py` | 核心：环境 `Env` + 期望值 DP + MDP + 策略仿真 + 4 个规则基线 |
| `run_experiments.py` | 实验总入口。产出 `results/*.csv` 与 `summary.json` |
| `vot_check.py` | 诊断：模型隐含的时间价值 vs 文献实测值 |
| `vot_rescale.py` | 按文献 VOT 重标定车费，验证主结论是否稳健 |
| `make_figures.py` | F1–F4 四张图 |

---

## 关键参数在 `ev_dp.py` 的 `Env.__init__`

```python
Env(
    batt=40.0,        # 电池容量 kWh
    soc_res=0.15,     # reserve 下限
    p_kw=60.0,        # 充电桩额定功率
    eta_c=0.92,       # 充电效率
    eta_cc=0.80,      # CC→CV 拐点
    kwh_km=0.22,      # 百公里能耗
    u_peak=0.85,      # 晚高峰载客率（用于标定车队规模）
    fare_scale=1.0,   # 车费缩放（VOT 校准用）
    soc_step=0.01,    # SOC 网格粒度
)
```

---

## 三个必须知道的实现坑

**1. 跌破 reserve 必须判 infeasible，不能 clamp。**
把跌破的 SOC 夹回下界 = 白送电，DP 会得出"永远不充电"的荒谬解。见 `solve_dp` 中 `if new_kwh >= floor_kwh`。

**2. 敏感性参数必须真的接进 `Env`。**
第一版把 `kwh_km` / `fare_scale` 传进去但没读，导致峰谷价差 0→2× 结果完全一样。现在 `self.kwh = self.dist_km * self.kwh_km` 是推导出来的。

**3. 仿真与模型必须用同一套可行性判据。**
`run_policy` 与 `solve_dp` 都要用「跌破 reserve 即不可行」，否则 DP 报 99% 可行、蒙特卡洛跑出别的东西。

---

## 环境

Python 3.12.7 · numpy 1.26.4 · pandas 3.0.2 · matplotlib 3.9.2

其他可选：scipy 1.13.1（未使用）。