# Related Works

> 文献调研与定位。**对应论文章节 §1.2 Literature Review。**
> ⚠️ **所有 DOI 已用 Crossref / arXiv API 逐条核验**（见文末核验记录）。

---

## 1. 按"谁做决策"分组

这个分法比按主题分更有用，因为它直接暴露了我们站在哪里。

| 组 | 代表 | 决策主体 | 规模 | 方法 |
|---|---|---|---|---|
| **A. 平台 / 市场均衡** | Ke et al. 2019 [1]；Liu et al. 2023 [5] | 司机群体的**工作时段 + 充电时段** | 车队 / 市场（含油电混编） | 时间展开网络 + 用户均衡 |
| **B. 车队调度** | Ma 2021 [2]；Ma 2023 [3]；Ma et al. 2024 [4] | 车队的充电计划 + 车-桩分配 | 100 辆 | 序贯 MILP / 拉格朗日松弛 / 滚动时域 |
| **C. 强化学习联合决策** | Ma et al. 2023 [7] | 充电 + 派单**联合**策略 | 车队 | MDP + 分布式 DQN |
| **D. 单司机决策** | **（空）** | **一个司机自己的日内充电决策** | **1 辆** | **—** |

---

## 2. 逐篇笔记

### A 组 · 平台与市场均衡

**[1] Ke, J., Cen, X., Yang, H., Chen, X. (2019).** *Modelling drivers' working and recharging schedules in a ride-sourcing market with electric vehicles and gasoline vehicles.* **Transportation Research Part E: Logistics and Transportation Review**, 125, 160–180.
DOI: `10.1016/j.tre.2019.03.010`

- **决策**：工作时段 **和** 充电时段一起选 —— 比我们宽（他们允许"不上班"，我们只有"待机"）
- **关键论证**：北京出租车日均里程 241 km > EV 安全续航 200 km → **班内必须充电**。这跟我们选 40 kWh 而非 60 kWh 的逻辑一模一样
- **建模**：时间展开网络 + 用户均衡；弹性劳动力供给
- **结论**：平台利润、消费者剩余、供应商剩余随**充电价格单调下降**、随**充电容量单调上升**

**[5] Liu, Y., Chen, Z., Xie, C., Liu, K. (2023).** *Temporal equilibrium for electrified ride-sourcing markets considering charging capacity and driving fatigue.* **Transportation Research Part C**, 147, 104008.
DOI: `10.1016/j.trc.2022.104008`

- **新增维度**：驾驶疲劳
- **有趣发现**：司机的充电行为**与其休息行为同步** —— 充电不纯粹是损失，午休时段充电等于同时在休息
- **我们没采纳**：疲劳建模需要额外的长时间驾驶成本项，与我们的日尺度模型不匹配

### B 组 · 车队充电调度

**[2] Ma, T.-Y. (2021).** *Two-stage battery recharge scheduling and vehicle-charger assignment policy for dynamic electric dial-a-ride services.* **PLOS ONE**, 16(5), e0251582.
DOI: `10.1371/journal.pone.0251582` ｜ 开放获取，代码 <https://github.com/tym2021>

- **两阶段**：① 日充电计划 ② 在线车-桩匹配（考虑**充电桩排队**）
- **成本明确拆成三项**：**车辆接近时间 + 充电时间 + 等待时间**
- **算法**：拉格朗日松弛，解大规模车-桩分配
- **结果**：相对最近充电桩策略与 FCFS 策略，等待 −74.9%、充电时长 −38.6%、充电成本 −27.4%
- **对我们的意义**：这三项时间成本我们**一项都没建模**，已在 Framework §3.2 列为局限

**[3] Ma, T.-Y. (2023).** *Dynamic Charging Management for Electric Vehicle Demand Responsive Transport.* **Lecture Notes in Intelligent Transportation and Infrastructure**, 171–182.
DOI: `10.1007/978-3-031-23721-8_14`

- **滚动时域 + 混合 LSTM 预测充电桩占用率**
- **案例**：英国 Dundee 真实仿真
- **结果**：等待 −48.3%，充电量 −35.3%

**[4] Ma, T.-Y., Connors, R. D., Viti, F. (2024).** ⭐ *Congestion-Aware Charging Coordination for Electric Ride-Hailing Fleets under Stochastic Demand.* **arXiv:2412.09978**（v4）

> ⚠️ **这是跟我们最近的一篇，也是必须正面处理的竞品。**

- **同网约车充电、同随机需求、同样用 NYC yellow taxi 数据**
- **方法**：序贯 MILP（day-ahead 计划 + 在线协调）
- **规模**：100 辆车，3000 / 4000 客户/天，Manhattan-like 区域
- **结果**：相对最强基线 OptChg，利润 **+3.91%**、服务率 **+4.60%**；相对最弱基线 +19.32% / +20.03%

**我们与它的关系（诚实表述）**：它做的是**车队**（含桩位拥堵与车-桩分配），我们做的是**单司机**（连续时间、精确 DP、含 CC-CV 与机会成本）。我们**不是填空，是缩小规模换取精确解**。指南第 6 节明确"简单模型 + 强问题 + 清晰洞察"优于"复杂算法 + 弱解释"，这个取舍要在论文里主动讲清楚，不能等答辩被问。

**[6] Alam, S., Guo, R. (2022).** *Charging infrastructure planning for ride-sourcing electric vehicles considering drivers' value of time.* **Transportation Letters**, 15, 573–583.
DOI: `10.1080/19427867.2022.2077003`

- 主题就是"网约车 EV + **时间价值**" —— 我们的直接邻居，也是我们把 VOT 当作独立敏感性的依据来源之一

### C 组 · 强化学习

**[7] Ma, J., Zhang, Y., Duan, L., et al. (2023).** *PROLIFIC: Deep Reinforcement Learning for Efficient EV Fleet Scheduling and Charging.* **Sustainability**, 15(18), 13553.
DOI: `10.3390/su151813553`

- 把**充电与派单联合**建模为 MDP，分布式 DQN 共享充电与运力信息
- **批评既有工作**："把充电决策和派单决策割裂开，或假设最近充电站永远最优，忽略了二者的相互依赖"

**我们的定位**：课程主线是 DP/MDP，不是强化学习。我们用 **DP/MDP 的解析解**而非 DQN，因为状态空间只有 8,256，解析解既精确又快，且**方法与课程章节直接对应**。这是一个有意识的取舍。

### D 组 · 时间价值（VOT）—— 我们的校准锚

**[8] Mehditabrizi, A., Namadi, S. S., Cirillo, C. (2026).** *From pumps to plugs: valuing time in refueling and EV charging transitions.* **Travel Behaviour and Society**, 44, 101279.
DOI: `10.1016/j.tbs.2026.101279`

- **VOT ≈ \$15.20/h**（加油站选择的 MNL 估计）

**[9] Dorsey, J., Langer, A., McRae, S. (2022).** *Fueling Alternatives: Gas Station Choice and the Implications for Electric Charging.* **NBER Working Paper 29831**.

- **VOT = \$27.54/h = 当地中位工资的 89%**（美国交通部仅按工资的 50% 估，系统性低估）
- **公共充电平均多花 30.6 分钟出行时间**（等待 + 步行）；加油站只多花 2.5 分钟
- **快充比多建桩更值钱**：充电速度每提高 1% 的收益，是充电站数量增加 1% 的 **4.7 倍**

**[10] Sunada & Xia (2026).** *From Pumps to Plugs: Value of Time and Charging Policies.* SSRN 6296418.
DOI: `10.2139/ssrn.6296418`

- 上海高频车辆遥测，**充电 VOT = 平均工资的 27%**

### 背景文献

**Qin, Y., Dai, Y., Huang, J., Xu, H., Lu, L., Han, X., Du, J., Ouyang, M. (2023).** *Charging patterns analysis and multiscale infrastructure deployment: based on the real trajectories and battery data of the plug-in electric vehicles in Shanghai.* **Journal of Cleaner Production**, 425, 138847.
DOI: `10.1016/j.jclepro.2023.138847` —— 上海真实 EV 轨迹与电池数据

---

## 3. 定位陈述（论文 §1.2 最后一段要写的话）

> 现有关于电动网约车充电的工作主要在**车队或市场层面**运作：它们联合优化车队充电计划与充电站分配 [2–4]，或刻画司机群体的工作-充电排班均衡 [1,5]。这些模型把需求或运力视为**给定的外生条件**，或需要用序贯 MILP、拉格朗日松弛、用户均衡求解，状态空间随车辆数增长。
>
> 我们的工作刻意停在**单个司机**这一格：这使得连续时间的状态空间只有 $96\times86$，可用**动态规划闭式精确求解**，从而可以把**随机订单到达**与**CC–CV 充电衰减**这两个非线性结构直接写进模型，而不必为它们设计启发式或分解算法。
>
> 代价是我们不处理**充电站拥堵与司机间博弈**——这是车队模型的核心，也是本工作明确列出的局限 [2–4]。我们认为这一取舍符合本课程对"简单模型 + 强问题 + 清晰洞察"的评价取向，但它是**缩小规模**而非**填补空白**。

---

## 4. 引言可用的一句话综述

> Electric ride-hailing drivers face a scheduling problem in which the cheapest hour to charge is rarely the hour they should charge: off-peak hours coincide with both low tariffs *and* low order availability, so the opportunity cost of an hour spent charging can dominate the tariff saving.

---

## 5. DOI 核验记录

核验方式：Crossref REST API（按标题反查 + 按 DOI 校验）+ arXiv API（`id_list` 核标题与 DOI 字段）。
日期：2026-10-07。

**踩过的坑**：最初凭印象写的 3 个 DOI **全部错误**（`10.1016/j.tre.2019.01.024`、`10.1016/j.trc.2023.104008`、`10.1016/j.tbs.2026.101279` 均 404）。正确编号见下表。**任何 arXiv ID 或 DOI 都不得凭记忆填写。**

| 文献 | 已核验 DOI |
|---|---|
| Ke et al. 2019 | `10.1016/j.tre.2019.03.010` ✅ |
| Ma 2021 | `10.1371/journal.pone.0251582` ✅ |
| Ma 2023 | `10.1007/978-3-031-23721-8_14` ✅ |
| Ma, Connors, Viti 2024 | arXiv:2412.09978（API 确认无 DOI） ✅ |
| Liu et al. 2023 | `10.1016/j.trc.2022.104008` ✅ |
| Alam & Guo 2022 | `10.1080/19427867.2022.2077003` ✅ |
| Ma et al. 2023 (PROLIFIC) | `10.3390/su151813553` ✅ |
| Mehditabrizi et al. 2026 | `10.1016/j.tbs.2026.101279` ✅ |
| Sunada & Xia 2026 | `10.2139/ssrn.6296418` ✅ |
| Qin et al. 2023 | `10.1016/j.jclepro.2023.138847` ✅ |