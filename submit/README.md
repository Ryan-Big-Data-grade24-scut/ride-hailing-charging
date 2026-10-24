# Submit — 需要提交什么

> 本文件说明**最终要交给课程的东西**。仓库其余部分都是内部工作区。
> 依据：`raw/优化方法/期末大作业/2026_Optimization_Methods_Final_Project.docx`（官方指南原件）

---

## 必须交的东西

课程指南第 1 节原文：

> Submission materials should include at least **the final paper in PDF/Word format**, **the core code**, and **the main dataset or a clear description of the data sources**.

| # | 交付物 | 形式 | 状态 |
|---|---|---|---|
| **1** | **英文论文** | Word（.docx）+ PDF | ✅ **已写完**：6,200 词 / 18 页 / 13 个原生公式 / 9 表 4 图 |
| **2** | **核心代码** | 本仓库 `code/`（连同 `data/` 需求画像） | ✅ 已就绪 |
| **3** | **主要数据集 或 数据来源说明** | 数据是 NYC TLC 公开数据，**写清楚来源+清洗规则即可** | ✅ 见 `docs/experiment/` §1 |
| **4** | **答辩 PPT** | .pptx（另存 PDF 备份） | ✅ 12 页，指南 §7 的 9 段结构全覆盖 |

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

### ✅ 格式自查结果（2026-10-24，已逐条核验 `.docx` 内部 XML）

| 项 | 要求 | 实测 | 怎么验的 |
|---|---|---|---|
| 纸张/页边距 | A4 / 2.54 cm | `pgSz 11906×16838`、`pgMar 1440` twips | ✅ |
| 页码 | 底部 | footer 里的真实 `PAGE` 域 | ✅ |
| 字体 | Times New Roman 全文 | 样式全部 TNR，**正文无任何直接字号覆盖** | ✅ |
| 标题/作者/摘要/H1/H2/H3 | 14pt粗 / 10.5 / 10.5 / 12粗 / 10.5粗 / 10.5斜 | 28/21/21/24/21/21 半磅 | ✅ |
| 正文 | 10.5pt / 1.5 倍 / 两端对齐 | `sz=21`、`line=360 auto`、`jc=both` | ✅ |
| 题注 / 参考文献 | 约 10pt / 10pt | `sz=20` | ✅ |
| **公式** | **Word 公式对象，禁止贴图** | **101 个 `<m:oMath>`，media 里只有 4 张图（无公式图片）** | ✅ |
| 公式编号 | 顺序 (1)…(13) | 全部存在 | ✅ |
| 图表编号 | 按首次出现顺序 | 图 1–4、表 1–9 | ✅ |
| 图题在下、表题在上 | 指南 §6.4 | 已核对 | ✅ |
| 摘要 | ≤250 词 | 239 词 | ✅ |
| 关键词 | 3–7 个 | 7 个 | ✅ |
| 参考文献 | 按首次出现编号、含 DOI | [1]–[12] 顺序无缺漏 | ✅ |

> ⚠️ **两个必须走 Word 的坑**：
> 1. **`	ag{n}` 会被 pandoc 吞掉** —— texmath 不支持它，公式编号会整段消失。已改用 `\qquad\qquad (n)` 内嵌编号。
> 2. **导 PDF 必须用 Word（`tools/docx_to_pdf.py`）** —— LibreOffice 会把 `\left\lVert` 渲染成 `∦`（U+2226 FORCED）而不是 `∥`（U+2225 PARALLEL TO）。

---

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
| **实验、敏感性 & 洞察** | **30** | ✅ 8 策略对比 + 7 组敏感性 + **消融 A1–A6** + **循环多日扩展** + 充电时刻分布统计 |
| 工作量 & 可复现性 | 10 | ✅ 代码+数据+种子齐全 |
| 学术写作 & 格式 | 15 | ✅ 已完成并逐条自查（含原生公式、图题在下/表题在上、编号按首次出现） |

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

## 时间表（2026-10-10 群通知，**已确认**）

| 日期 | 事项 | 链接 / 状态 |
|---|---|---|
| **10 月 14 日** | 完成组队 + 填在线分组表（**单人也必须填**；未填默认随机分到 4–5 人组） | <https://docs.qq.com/sheet/DUUxCbmZPemNERkpp?tab=BB08J2> |
| **11 月 20 日** | 提交**论文初稿 + 答辩 PPT** | <https://docs.qq.com/form/page/DVk5QYmJ6Qm1xaXpU> |
| **11 月 21 日（周六）** | **大作业答辩**（具体时间地点后续通知） | |
| **12 月 5 日** | 提交**修改后的终稿**（链接后续通知） | |

> 📌 距初稿还有 **27 天**（按 2026-10-24 计）。**初稿 + PPT 同一天交**，PPT 不能拖到最后。

## 提交时待确认

以下由课程团队后续公布，**目前仍未知**：

- [ ] 终稿提交链接（12/5）
- [ ] 文件命名规则
- [ ] 答辩具体时间与地点
- [ ] 论文与答辩之间的最终权重

---

## 建议的提交包

```
submit/
├── Final_Paper_梁睿希_202464870791.docx      ← 英文论文（提交用，18 页）
├── Final_Paper_梁睿希_202464870791.pdf       ← 同上导出的 PDF（用 Word 导，勿用 LibreOffice）
├── paper.md                                   ← 论文 Markdown 源（改内容改这个）
├── Defense_梁睿希_202464870791.pptx            ← 答辩 PPT（12 页，11/20 同批交）
├── Defense_梁睿希_202464870791.pdf             ← PPT 的 PDF 备份
├── code/                                      ← 核心代码（src/ + build_profile.py）
├── data/
│   ├── profile.json                           ← 需求画像（生成物，直接给）
│   ├── demand_profile.csv                     ← 96 格明细（人类可读）
│   └── DATA_SOURCE.md                         ← 数据来源与清洗规则说明
├── figures/                                   ← 4 张图
├── tools/                                     ← 排版与导出脚本（复现用，可不打包）
│   ├── make_reference_docx.py                 ← 定义全部 Word 样式（字号/行距/字体）
│   ├── fix_table_widths.py                    ← 表格列宽按内容分配，数字不断行
│   ├── fix_eq_tags.py / fix_lbrace_space.py   ← 修公式编号与 \lbrace 粘连
│   ├── docx_to_pdf.py                         ← Word COM 导 PDF（唯一安全路径）
│   ├── make_ppt.py                            ← 生成答辩 PPT
│   └── read_guide.py                          ← 从指南原件提取格式条款
└── README.md                                  ← 本文件
```

**修改论文的正确流程**：`submit/paper.md` 改内容 → `tools/make_reference_docx.py`（若改样式）→ pandoc 出 docx → `tools/fix_*.py` 依次修 → `tools/docx_to_pdf.py` 导 PDF。

**注意**：原始 parquet（47.6 MB）**不必打包**，在 `DATA_SOURCE.md` 里写清下载地址与清洗规则即可（指南允许"数据集 **或** 清楚的数据来源说明"）。