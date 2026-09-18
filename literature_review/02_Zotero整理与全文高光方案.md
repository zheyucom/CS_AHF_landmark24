# Zotero 整理与全文高光方案

## 1. 已完成的只读盘点

- Zotero Desktop 本地 API 已启用并恢复连接。
- 当前与课题直接相关的主集合包括：
  - `#心衰早期预测`（collection key `4EMWVUHV`）
  - `短期恶化动态预警`（`NSXCD5H9`）
  - `CS`（`RHJE6FI2`）
  - `2.0`（`QINLZ374`）
- 已确认 Beer 2024、Hu 2024、Essay 2020、Metra 2023、Greene 2023、ESC 2021 等具备全文附件。
- 已发现至少两组疑似重复：
  - `4QTPDF2Z` 与 `BRHSEZTK`：Li 2025 AHF mortality。
  - `XAWRJ6VS` 与 `42NNB93T`：Randhawa 2025。
- 标签存在大小写/单复数变体，例如 `Heart failure` 与 `Heart Failure`。

未自动删除、合并或移动任何条目，因为合并会改变库结构，应在 Zotero GUI 中人工确认主条目、附件、笔记和引用键后执行。

## 2. 建议的集合结构

在 `短期恶化动态预警` 下建立以下子集合：

1. `00_核心必读`
2. `01_结局定义_WHF_HD`
3. `02_AHF到CS早期预测`
4. `03_AHF合并Sepsis`
5. `04_动态EHR与方法学`
6. `05_外部验证与临床实施`
7. `06_报告规范_TRIPOD_PROBAST`
8. `90_待筛选`
9. `99_排除_保留记录`

同一条文献可以进入多个集合，不需要复制条目。

## 3. 统一标签

建议只保留下列课题标签，使用小写英文加冒号：

- `topic:whf`
- `topic:hemodynamic-deterioration`
- `topic:cardiogenic-shock`
- `topic:ahf-sepsis`
- `endpoint:treatment-escalation`
- `endpoint:hypoperfusion`
- `design:landmark`
- `design:dynamic`
- `validation:external`
- `method:logistic`
- `method:machine-learning`
- `status:core`
- `status:to-read`
- `status:extracted`
- `use:introduction`
- `use:methods`
- `use:discussion`

避免继续增加同义自由标签；现有大小写变体在确认后批量统一。

## 4. 颜色高光合同

对 `00_核心必读` 的原文 PDF 使用固定颜色：

| 颜色 | 含义 | 必须提取到表格的字段 |
|---|---|---|
| 黄色 | 人群、纳排、landmark、预测窗口 | population / index / predictor window / horizon |
| 红色 | 结局定义、阈值、事件判定 | endpoint / timing / treatment / physiology |
| 蓝色 | 特征、模型、验证流程 | predictors / preprocessing / validation |
| 绿色 | 样本量、事件率、AUROC/AUPRC/校准 | n / events / discrimination / calibration |
| 紫色 | 作者明确局限 | limitation / transportability |
| 橙色 | 可直接用于本课题的设计启示 | design decision / action |

每篇核心文献完成后，在 Zotero 笔记顶部写 6 行结构化摘要：

```text
Population:
Landmark / horizon:
Endpoint:
Model / validation:
Main result:
Direct use for my study:
```

## 5. 第一批必处理文献

1. Beer 2024：已完成 Paper Card；重点标红 WHF/CS 定义。
2. Hu 2024：已完成 Paper Card；重点标蓝动态时序、预训练、外部映射。
3. Rahman 2022：补入 Zotero 后制作 Paper Card；重点关注 FP/TP 人工复核和提前时间。
4. DeVore 2016 ADHERE：作为传统 WHF 风险模型性能基准。
5. 2026 cardiovascular ICU HD study：作为最新直接竞争文献，重点核对时间锚点和严格复合结局。
6. Zhang 2024 HF+sepsis：作为“已有交叉人群研究主要预测死亡”的代表。
7. TRIPOD+AI、PROBAST+AI：作为论文与模型开发 QA。

## 6. 建议导入但尚未自动写入 Zotero 的新文献

| 文献 | DOI/PMID | 目标集合 |
|---|---|---|
| DeVore 2014 in-hospital WHF | 10.1161/JAHA.114.001088 / PMID 25015076 | `01_结局定义_WHF_HD` |
| DeVore 2016 ADHERE risk model | 10.1016/j.ahj.2016.04.021 / PMID 27502870 | `00_核心必读` |
| Rahman 2022 AHF→CS | 10.1016/j.jscai.2022.100308 / PMID 39131966 | `00_核心必读` |
| Chang 2022 early CS | 10.3389/fcvm.2022.862424 / PMID 35911549 | `02_AHF到CS早期预测` |
| Zhang 2024 HF+sepsis | 10.3389/fmed.2024.1410702 | `03_AHF合并Sepsis` |
| 2026 cardiovascular ICU HD | 10.3389/fcvm.2025.1694001 / PMID 41647804 | `00_核心必读` |
TRIPOD+AI（`3QMBEVPV`）和 PROBAST+AI（`F89JZ9FX`）经二次精确检索已确认存在，不应重复导入，只需归入 `06_报告规范_TRIPOD_PROBAST`。

自动导入前应先在 Zotero 选中目标集合。当前 Zotero 选中的是 `CS`，并非计划放置全部新增文献的 `短期恶化动态预警`，因此本轮没有把 6 篇新文献写入错误集合，也没有擅自合并重复条目。
