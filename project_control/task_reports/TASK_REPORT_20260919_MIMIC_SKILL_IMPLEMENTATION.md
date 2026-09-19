# MIMIC-IV 清洗 skill 实施报告

日期：2026-09-19
状态：完成（skill 级静态与合成夹具验证通过；未执行患者级 MIMIC 查询）

## 本阶段完成

本阶段将原有草案补成可运行的依赖零安装 skill。规则以版本化 JSON 保存，验证器对规则形状、精确 itemid 合同、时间合同、隔离集合和 active 审批做 fail-closed 校验；SQL 扫描器保持只读，不改写历史 SQL。

已固化的 BUN 血液合同：

- 仅允许 itemid 51006、label Urea Nitrogen、fluid Blood、category Chemistry、unit mg/dL。
- 51104、51045、50851、51804、51825、51842、51922、51951 仅进入 quarantine。
- 可用时间为 GREATEST(charttime, COALESCE(storetime, charttime))，窗口末端使用严格 `<`。
- 未知/空单位、fluid/category 不匹配、缺 specimen、缺 charttime、storetime 早于 charttime、迟到结果、重复 specimen × itemid、缺原值和区间值均 fail-closed。
- `<x`、`>x`、`<=x`、`>=x` 保留 raw_value、censor_type 和 raw_boundary，不伪装为精确值。
- derived 表只能做 raw↔derived 双向对账，不能作为唯一 raw 来源。

## 验证证据

- 原有回归夹具：13/13 通过。
- 新增边界夹具：3/3 通过。
- Phase C 原有项目测试：11/11 通过。
- 规则包验证器：通过。
- 对 Phase C 合同 SQL 的静态扫描：无 finding。
- 未连接 BigQuery/MIMIC 受控表，故本报告不是患者级运行通过证明；患者级状态仍应记录为 `not_run` 或 `not_run_access_denied`。

## 规则治理

`lab-bun-blood-v1` 的 active 状态只表示项目负责人已明确批准将该合同用于 skill enforcement；不等同于将历史 SQL 或正式研究结果晋级为 ACTIVE。任何新 analyte 仍需 source、失败夹具、回归通过和明确审批，不能由 skill 自行激活。

## 产物完整路径

- `/Users/zheyu/Desktop/CS_AHF_landmark24/phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/SKILL.md`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/references/mimic-iv-lab-rules.json`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/references/rule-schema.md`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/references/source-provenance.md`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/scripts/validate_rule_pack.py`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/scripts/audit_mimic_sql.py`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/scripts/test_edge_cases.py`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/task_reports/TASK_REPORT_20260919_MIMIC_SKILL_IMPLEMENTATION.md`

## 后续动作

下一步可以把同一规则包接入待审计的正式 SQL 清单，逐条生成静态 preflight 报告，再由项目负责人决定哪些新规则进入 proposed 或 active。当前没有需要用户在本机执行的命令。
