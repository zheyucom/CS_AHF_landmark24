# 任务报告：研究一 G7 前合并症映射与 T0 候选因素合同

日期：2026-09-24

状态：G7_FACTOR_CONTRACT_FROZEN_COMORBIDITIES_DESCRIPTIVE_ONLY

## 1. 完成内容

- 对冻结 A+B+C 主队列 773 个 ICU episode 做 T0 前诊断和入院病史来源映射。
- 使用版本化关键词和否定词保留来源、时间、证据方向及 unknown。
- 未使用院内死亡结局字段，不做结果驱动变量筛选。
- 生成逐条证据账本、episode 级摘要和聚合审计。

## 2. 数据覆盖

- T0 前诊断记录：632/773。
- T0 前创建的入院病史：262/773。
- 证据账本：1,227 条。
- 主要域状态均保留 present、negative、conflict、unknown；unknown 不等于阴性。

## 3. 合并症状态

高血压、糖尿病、缺血性心脏病、慢性肾病、房颤/心律失常、慢性阻塞性肺病、脑血管病和慢性肝病均完成候选域映射。由于来源覆盖和时间可用性不足，合并症不进入本版调整后主模型，只进入描述性和缺失结构报告。

## 4. 冻结的主关联因素

- 年龄：连续线性项，1 df。
- 性别：1 df。
- 入院途径：急诊 vs 非急诊，1 df。
- 总有效自由度：3；不为凑满事件预算而加入未知语义的合并症。

主结局为院内死亡 62 例；主模型使用 Firth/Jeffreys 惩罚 Logistic。该分析不开发第二个预测工具，不做单因素筛选或逐步回归。

## 5. 输出文件

- project_control/designs/INTERNAL_DHF_STAGE1_T0_FACTOR_CONTRACT_V1_20260924.md
- project_control/runs/20260924_internal_stage1_g7_comorbidity_mapping/comorbidity_evidence_ledger_v1.csv
- project_control/runs/20260924_internal_stage1_g7_comorbidity_mapping/comorbidity_episode_summary_v1.csv
- project_control/runs/20260924_internal_stage1_g7_comorbidity_mapping/comorbidity_mapping_audit_v1.json

## 6. 边界

本轮尚未运行死亡关联模型。模型运行必须读取本合同，且只能使用合同中的三个因素。原始 DHF_SRR 未修改。
