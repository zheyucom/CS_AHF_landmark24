# 任务报告：阶段定位与缺失数据/心超处理方案

日期：2026-09-04  
状态：已完成阶段定位、心超缺失性质判定、常规变量缺失处理方案和下一步执行清单

## 本轮回答的问题

1. 当前研究处于哪个大框架阶段；
2. 现有数据能否进入下一步；
3. 心超缺失是否需要插补；
4. 常规实验室/生命体征缺失有哪些处理方法，哪种适合本项目；
5. 还需要从文献和前人研究中借鉴什么。

## 阶段判断

当前处于：**阶段 3：最终 DHF 表型冻结与无泄露预测变量重建**。

队列与结局已经完成第一轮审计，MIMIC-IV-Echo 也已经完成真实 schema 和时间窗核验；但 5,549 例目前仍是 rule-supported broad/multidomain audit layer，不能直接称为全量 Echo-confirmed DHF。最终模型必须等主表型和最终有效参数数冻结后重建。

## 关键数据判断

- broad HF-anchor audit layer：5,549 stays，452 events，2,934 alive ICU discharges，2,163 administrative censoring；
- 当前 45 个候选变量中，乳酸相关缺失约 57.44%，pH/base excess 约 46.34%，INR 约 29.36%；生命体征大多低于 1%；
- MIMIC-IV-Echo 在 `[T0-24 h,T12)` 内只有 61 个 linked studies，9 个关联 note 在 T12 前，6 个同时达到 draft strict echo-supported 条件；
- 因此心超缺失主要是检查选择性和数据覆盖问题，不是可用 MICE 恢复的普通数值缺失。

## 已确定的处理原则

- 心超：不做“未检查=正常/异常”的数值插补；保存 performed、result available、abnormal support 和 unknown/not assessable 四类状态；作为验证、高特异性敏感性和检查选择性分析层。
- 常规实验室/生命体征：按变量逐一判断是 structural zero、measurement missing 还是 informative missing；保留的测量变量主方案采用外层训练折内 MICE，多重插补数据集建议 20 个；中位数插补、缺失指示器、complete-case 和测量/缺失加权作为预设敏感性或诊断分析。
- 所有插补、标准化、缺失指示、变量选择和惩罚参数选择必须在训练折内完成。
- 高缺失且临床贡献有限的变量优先从低维主模型删除或合并生理域，不因插补后性能好看而保留。

## 现阶段可以立即做的工作

1. 冻结 DHF 主队列层级和最终标签字段；
2. 生成最终 predictor manifest，并给每个变量标记缺失类别与允许的处理方式；
3. 对最终队列重算缺失率、检测率、缺失模式和每个事件状态的分布；
4. 按最终事件数重新限制有效参数数，不能直接把 broad v3.3 的 45 个变量搬过去；
5. 实现严格折内 MICE、折内中位数和缺失指示器三条分析分支；
6. 表型冻结后运行 Fine-Gray 主模型、1 h person-period 补充模型及预设敏感性分析。

## 主要阻塞点

当前唯一实质性高风险决策是：MIMIC 主开发队列最终采用哪一层 DHF operational phenotype。心超缺失本身不是主模型启动的阻塞点。院内严格验证仍需另行提取心超三级 QC 字段。

详细方案见：

`project_control/MISSING_DATA_AND_ECHO_HANDLING_PLAN_V1.md`

