# 外部验证最小字段清单

更新时间：2026-09-03

## 目的

院内外部验证不需要一次性拿到所有 070 系列特征。严格院内验证队列还必须能确认：患者为 ICU 患者，且在 `T12` 前完成 TTE、TEE 或心脏 POCUS/床旁心超，有可解析结果支持心脏结构或功能异常，并有 DHF 的失代偿和治疗强化证据。

提数阶段仍需保留完整连续成年 ICU 候选宇宙，以估计心超完成率、结果可用率及检查选择性；未做心超或结果缺失不能编码为心超阴性。

## 必须字段

### 1. 队列与时间锚点

- 患者标识：`subject_id`
- 住院标识：`hadm_id`
- ICU stay 标识：`stay_id`
- 住院开始：`admittime`
- ICU 入科：`intime`
- ICU 出科：`outtime`
- 住院出院：`dischtime`
- 死亡时间：`deathtime` 或等价字段
- ICU 再入或后续 ICU stay 链接键

### 2. DHF 复刻字段

必须能判断：

- 是否存在 HF 诊断锚点，并保留 acute/acute-on-chronic、既往 HF 和 de novo HF 的来源/状态
- ICD 序位 / 诊断顺序
- IV loop diuretic 给药时间
- IV loop diuretic 给药剂量
- 给药途径 / 记录类型
- NT-proBNP 检验时间
- NT-proBNP 数值
- NT-proBNP 单位

### 3. 严格 DHF 入组所需心超字段

必须能够逐例判断：

- 是否为 index ICU stay，及 `T0=intime`、`T12=T0+12 h`；
- 心超类型：TTE、TEE、心脏 POCUS/床旁心超；
- 检查完成时间、报告形成/可见时间、签署时间和报告状态；
- `echo_performed_flag`；
- `echo_result_available_flag`；
- `echo_abnormal_support_flag`；
- LVEF 及单位/测量方法；LV/RV 收缩功能、舒张功能/E/e'、瓣膜、肺动脉压、IVC、心包积液等可用结果；
- 完整去标识化报告或最小可审计证据片段；
- 否定、不确定、检查质量和人工复核状态。

严格队列要求上述三个 flag 均为 1，且心超结果时间在 `[T0-24 h,T12)` 内。仅有检查医嘱、procedure flag、检查名称或“床旁心超已做”而无实际结果，不满足严格纳入。

### 4. 0-12 h 预测变量字段

至少要有时间戳和数值：

- vital signs：HR, SBP, MAP/MBP, DBP, RR, SpO2, temperature
- labs：lactate, creatinine, BUN, sodium, potassium, chloride, bicarbonate, albumin, WBC, hemoglobin, platelet, INR/PT/PTT, pH, base excess, pCO2, pO2
- support：vasoactive/inotrope start/end time, drug name, dose, route
- urine output
- respiratory support
- GCS / mental status if used

### 5. 结局字段

必须能复刻：

- support escalation start time
- vasoactive / inotrope agent count
- norepinephrine-equivalent dose
- ICU death time
- alive ICU discharge
- alive ICU discharge 后是否再入 ICU（若做扩展敏感性）

### 6. 预设亚组字段

如果要复刻 early sepsis 亚组，还需要：

- suspected infection 时间
- antibiotic 时间
- culture 时间
- SOFA 相关字段 / 计算所需组件

## 不能省略的时间逻辑

外部验证至少要能判断：

1. `admittime <= predictor_time < intime`
2. `intime + 12 h <= outcome_time <= intime + 60 h`
3. `alive ICU discharge` 是否早于事件
4. `deathtime` 是否发生在 ICU 内或 ICU 后

此外，严格 DHF 队列必须能判断：

5. `T0-24 h <= echo_exam_time < T12`
6. `echo_result_available_time < T12`
7. 心超结果为异常支持、阴性、缺失或不可解析，而不是只有“做过/没做过”二元标记

## 最低接收标准

如果院内只能先给一小批样例，优先给：

1. 20-50 行脱敏样例
2. 字段字典
3. 时间单位说明
4. 药物剂量单位说明
5. ICU 出科、死亡、再入 ICU 的定义说明

样例通过后再给全量。
