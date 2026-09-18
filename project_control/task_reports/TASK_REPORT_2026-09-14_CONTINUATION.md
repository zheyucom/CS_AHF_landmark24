# 任务报告：中断任务续接与冻结门槛（2026-09-14）

## 本次完成

- 复核三级审计 CSV、QC JSON 和报告：8,385 行、男女 2,842/5,543、窗口心超 2,519/2,517/2,475，45 例语义抽审 8 retain、37 exclude、8,340 未抽审，全部一致。
- 复核 7 条影像边界行：均已有可追溯草判；未发现需要新增用户语义确认的异常。其余自动标签继续保持 `draft/weak label`。
- 新增院内最小数据补提规格：`project_control/INTERNAL_DHF_MINIMUM_DATA_REQUEST_v20260914.md`。
- 对 `DHF_SRR` 原始导出完成只读源审计：25 个 CSV、全部文书 775,853 行（非空正文 775,837 行），并生成 `project_control/internal_dhf_source_inventory_20260914.json`。
- 生成就诊号级文书高召回筛查层 `project_control/internal_dhf_document_recall_screen_20260914.csv`（8,653 个成人就诊号，已排除 9204020）；该层仅用于后续 NLP/人工排序，未将关键词计数当作 DHF 纳入人数。

## 当前可冻结与不可冻结内容

- **已冻结**：成人 index ICU 分母 8,385；T0/T12 规则；报告时间心超门控；A+B+C DHF 操作性表型框架；MIMIC 主开发端不设心超硬门槛、院内严格验证保留 echo-supported 层。
- **不可冻结**：全量 `confirmed_dhf/probable_dhf/not_supported/unknown`；事件、存活转 ICU 外竞争事件和删失；最终预测器数量。

## 下一执行顺序

1. 将最小数据补提规格交给数据管理员，并要求保留多次 ICU episode、原始来源时间和执行级治疗状态。
2. 收到补提数据后，先做主键/时间/episode QC，再在不读取结局的前提下完成全量 A+B+C 语义抽取与人工抽样校准。
3. 冻结 DHF 分层后按事件数重定预测器，再重跑 Fine–Gray 主模型、person-period 补充模型、内部验证和院内外部验证。

## 研究记录边界

本次未修改原始院内数据，未把 45 例或 300 条影像抽样结果外推到全量，也未用医嘱时间、文书创建时间或自动出院字段猜测结局。
