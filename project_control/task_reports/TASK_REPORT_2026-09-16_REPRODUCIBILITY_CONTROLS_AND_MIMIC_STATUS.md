# 任务报告：复现性控制补全与MIMIC执行状态核对

日期：2026-09-16（CST）

## 本轮目标

继续DHF临床预测模型的论文级工作流，吸收外部“科研平台实验方案与标准答案”工作簿的检查维度，同时保持本项目自己的科学问题、时间轴、表型和结局定义。

## 已完成

1. 明确工作簿的边界：仅作为漏项检查和复现性审计参照，不要求项目改成597篇工作簿的同款格式，也不把工作簿的标准答案移植为DHF结果。
2. 建立`acceptance_criteria_frozen.csv`：16项预先封存的验收标准，覆盖数据版本、键和episode、T0/T12/T60、DHF A/B/C、语义留痕、实验室截断、缺失、医嘱代理、风险集、三态结局、泄漏、复杂度、内部验证、外部验证和报告。所有`measured_value`均为空，状态均为`pending_measurement`。
3. 建立`run_registry.csv`：记录控制文件创建run；后续数据处理必须追加run，写入数据快照、脚本哈希、seed、折索引、输出哈希和偏差说明。
4. 建立`ORDER_PROXY_CLASSIFICATION_SPEC_V1.md`：把持续泵入、区间重叠、单次静脉点用、T0前延续不确定、文书支持、计划性错位和阴性对照分开；明确医嘱不是eMAR，不从总剂量推导泵速或NEE。
5. 将控制文件和边界接入`RESEARCH_DASHBOARD.md`及工作簿字段映射。

## 验证

- `mimic-iv-data-extraction` skill目录的资源校验通过：40张表、422个字段、65个概念、182个依赖和145个来源条目。
- 院内语义回归测试通过：11个测试全部通过。
- 总览中的相对链接逐一存在；新增CSV按表头和行结构检查通过。
- 当前会话无法使用浏览器控制面，且没有本地患者级MIMIC数据库连接；因此`MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql`未执行，执行状态保持`not_run`。

## 科学解释

这些控制文件解决的是“每一步是否有定义、是否先于结果封存、是否能复跑”的问题，不会改变DHF的纳入人群。正式队列、三态结局、实验室特征和模型性能仍必须来自同一冻结run；在门控通过前，历史或工作数字只能作为审计材料。

## 当前未完成项

- 院内优先队列、T12观察链、HF锚点和规则阴性抽样的临床裁决。
- MIMIC `labevents` 的itemid、单位、比较符号和截断值审计。
- 双库DHF队列冻结、三态结局冻结和锁模后的内部/外部验证。

## 入口文件

- `project_control/DHF_PROJECT_REPRODUCIBILITY_CONTRACT_V1.md`
- `project_control/DHF_EXPERIMENT_FIELD_MAPPING_V1.csv`
- `project_control/acceptance_criteria_frozen.csv`
- `project_control/run_registry.csv`
- `project_control/ORDER_PROXY_CLASSIFICATION_SPEC_V1.md`
- `project_control/MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql`
