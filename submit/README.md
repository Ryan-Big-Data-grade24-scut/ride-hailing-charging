# Submit — 需要提交什么

> 本文件说明**最终要交给课程的东西**。仓库其余部分都是内部工作区。
> 依据：`raw/优化方法/期末大作业/2026_Optimization_Methods_Final_Project.docx`（官方指南原件）

---

## 必须交的东西

课程指南第 1 节原文：

> Submission materials should include at least **the final paper in PDF/Word format**, **the core code**, and **the main dataset or a clear description of the data sources**.

| # | 交付物 | 形式 | 状态 |
|---|---|---|---|
| **1** | **英文论文** | Word（.docx）+ PDF | ⬜ **0 字，最重要的交付物** |
| **2** | **核心代码** | 本仓库 `code/`（连同 `data/` 需求画像） | ✅ 已就绪 |
| **3** | **主要数据集 或 数据来源说明** | 数据是 NYC TLC 公开数据，**写清楚来源+清洗规则即可** | ✅ 见 `docs/experiment/` §1 |

**成绩构成**：课堂互动 30% + 期末大作业 **70%**

**论文与答辩都很重要**，两者之间的最终权重"将由课程团队另行公布"。

---

## 论文格式硬约束（逐条自查）

来自指南第 6 节，**违反任一条都会在 15 分的"学术写作与格式"上扣分**：

| 项 | 要求 |
|---|---|
| 纸张 | A4，四边页边距 **2.54 cm** |
| 页码 | 页面底部 |
| 字体 | **Times New Roman**（全文） |
| 论文标题 | **14 pt，粗体** |
| 作者/学号信息 | 10.5 pt |
| 摘要 / 关键词 | 10.5 pt |
| 一级标题 | **12 pt，粗体** |
| 二级标题 | 10.5 pt，粗体 |
| 三级标题 | 10.5 pt，斜体 |
| 正文 | **10.5 pt，1.5 倍行距，两端对齐** |
| 图/表题注 | 约 10 pt |
| 参考文献 | 10 pt |

### ⚠️ 两条最容易踩的

**1. 公式不能贴图。**
> *"Use the Microsoft Word Equation Editor or MathType. **Do not paste equations as screenshots/images.**"*

**2. 用了生成式 AI 必须声明。**
指南 §6.8 **AI Use Statement**：若使用生成式 AI，需简要说明所用工具及主要用途。本项目（Claude Code / MiniMax Code 用于建模、文献理解、代码调试与英文润色）**需要写这一节**。

> 同一节还写明：**学生对提交的全部内容负责，必须理解关键模型、方程、代码逻辑、结果与结论。** 答辩有专门一题问 "How did AI tools assist your work, and which parts were completed and verified by your team?" —— **必须能自己讲清楚。**

---

## 论文推荐结构（指南 §6.3）

```
Title / 学生信息
Abstract            ≤250 词（含研究问题、方法、主要结果、结论）
Keywords            3–7 个
1. Introduction
   1.1 Background and motivation
   1.2 Literature review        用 [1][2–4] 编号引用
   1.3 Research question and contribution
2. Problem Formulation and Methodology
   2.1 Problem definition and optimization model    公式用 Word 公式编辑器
   2.2 Data and assumptions
   2.3 Optimization method and solution procedure
3. Results and Discussion
   3.1 Main optimization results
   3.2 Sensitivity / scenario analysis or extension
4. Conclusion
AI Use Statement
References
Appendix
```

> ⚠️ 注意：**这是"论文 + 口头答辩"，不是海报。** 官方指南已把早期的海报说法改掉了。

---

## 评分表（按它倒推写多少）

### 论文 100 分

| 项 | 分值 | 我们的状态 |
|---|---|---|
| 研究问题 & 文献综述 | 20 | ✅ 材料齐（8 篇 DOI 全核验） |
| 优化模型 & 方法 | 25 | ✅ 完成 |
| **实验、敏感性 & 洞察** | **30** | ✅ 对比+7组敏感性+消融2项（**待补 4 项**） |
| 工作量 & 可复现性 | 10 | ✅ 代码+数据+种子齐全 |
| 学术写作 & 格式 | 15 | ⬜ 未开始 |

### 答辩 100 分

| 项 | 分值 |
|---|---|
| 问题与模型 | 20 |
| 方法与方案 | 20 |
| **结果与洞察** | **30** |
| 展示 | 15 |
| **问答与理解** | **15** |

### 评分原则

> *"A simple optimization model with a strong research question and clear insight can score higher than a complicated algorithm with weak interpretation."*

**并且明确说：不按论文长度评分**，不需要 Highlights / Graphical Abstracts / TIFF 文件。

---

## 答辩要点（指南 §7）

**英文展示 + 英文答辩**，时长与地点待通知。推荐 9 段结构：标题与团队 → 背景与研究问题 → 优化问题 → 数据与假设 → 方法 → 基线与对比 → 敏感性与扩展 → 核心洞察 → 结论。

**会被问到的 8 个问题**：

1. Why is this an optimization problem?
2. Why did you choose this objective function?
3. Why is this constraint necessary?
4. Why did you choose this optimization method?
5. Why does the optimal solution have this value or shape?
6. What happens if a key parameter increases or decreases?
7. Would your conclusion still hold under a different assumption?
8. How did AI tools assist your work, and which parts were completed and verified by your team?

> 我们对 **3、6、7** 已有现成答案（reserve 约束的必要性和不可行性证明、七组敏感性、VOT 重标定稳健性）。**1、2、5** 需要组员自己内化 `docs/framework/`。

**所有人必须能解释核心模型、方法、假设、结论。** 不要求背下每个长公式，但**必须能解释其物理/工程含义**。

---

## 提交时待确认

以下由课程团队在 QQ 群公布，**目前均未知**：

- [ ] 提交链接
- [ ] 文件命名规则
- [ ] 截止日期
- [ ] 答辩时间与地点
- [ ] 论文与答辩之间的最终权重

---

## 建议的提交包

```
submit/
├── Final_Paper_梁睿希_202464870791.docx      ← 英文论文
├── Final_Paper_梁睿希_202464870791.pdf       ← 同上导出的 PDF
├── code/                                      ← 核心代码（src/ + build_profile.py）
├── data/
│   ├── profile.json                           ← 需求画像（生成物，直接给）
│   ├── demand_profile.csv                     ← 96 格明细（人类可读）
│   └── DATA_SOURCE.md                         ← 数据来源与清洗规则说明
├── figures/                                   ← 4 张图
└── README.md                                  ← 本文件
```

**注意**：原始 parquet（47.6 MB）**不必打包**，在 `DATA_SOURCE.md` 里写清下载地址与清洗规则即可（指南允许"数据集 **或** 清楚的数据来源说明"）。