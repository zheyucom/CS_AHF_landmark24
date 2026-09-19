# MIMIC 实验室 SQL 静态质量门

这是论文流水线的项目内权威实现。它只读取 Git 跟踪的 SQL 文本、权威清单和规则包，不连接数据库，也不处理患者级数据。

## 运行

在仓库根目录执行：

```bash
python3 project_control/quality_gates/mimic_lab/quality_gate.py check \
  --project-root . \
  --manifest project_control/PIPELINE_AUTHORITY_MANIFEST.csv \
  --contract project_control/quality_gates/mimic_lab/lab_contract_v1.json \
  --report-csv project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_20260919.csv \
  --summary-md project_control/quality_gates/mimic_lab/reports/sql_risk_summary_20260919.md
```

退出码：`0` 表示没有阻断正式运行的问题；`1` 表示发现 fail-closed 阻断项；`2` 表示输入、Git 或文件读取失败。`LEGACY_BLOCKED`、`SUPERSEDED` 和 `AUDIT_ONLY` 中的风险会进入账本，但不会被误写成当前正式运行已经失败或数据库执行已经完成。

## 硬门规则

- Git 跟踪 SQL 必须在权威清单中恰好登记一次。
- 只有 `ACTIVE` 且 `allow_final_run=true` 的工件可进入正式执行计划。
- ACTIVE 不能读取只由 blocked、superseded 或 audit-only SQL 生成的表。
- 正式实验室工件不得使用 derived 表生成队列、表型、结局或特征。
- raw `labevents` 必须显式实现 availability、unit、fluid、category 和 specimen 重复合同。
- 模糊 label/metadata 纳入、错误体液 itemid、未登记 itemid、缺失补零以及范围外值静默置 NULL 均会被识别。

## 权威边界

`lab_contract_v1.json` 的 active 规则来自项目 V2 审计及其正式执行证据。增加 itemid、单位或转换规则时，必须先完成来源核验、合成失败夹具、回归测试和项目批准；扫描器不会从旧 SQL 的数值外观“自行推断”新规则。

`PIPELINE_AUTHORITY_MANIFEST.csv` 是静态代码权威表；每次实际运行仍需另存 Git HEAD、SQL/规则哈希、输入快照指纹、执行顺序、引擎和退出码。
