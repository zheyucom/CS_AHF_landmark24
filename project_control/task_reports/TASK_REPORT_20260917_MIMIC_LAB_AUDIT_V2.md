# 任务报告：MIMIC-IV 实验室审计 V2

日期：2026-09-17

## 结论

旧 V1 不能继续作为特征冻结依据。V2 已完成本地实现与回归验证，将名称候选发现与精确患者级审计分离，并加入标本/类别/单位、结果可用时间、重复、删失值和 raw/derived 双向覆盖。

患者级状态更新为 `not_run_access_denied`：已修复本机 CLI 绕过系统代理的问题，`gcloud/bq` 现在经本机 `127.0.0.1:7897` 代理工作；V2 BigQuery dry-run 已成功。但只读字典候选查询返回 `Access Denied`（账号 `zheyu.sy@gmail.com` 无权读取 `physionet-data:mimiciv_hosp.d_labitems`），因此正式患者级审计未执行。

## 修改

- 新增 `MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql/.md`。
- 新增字典级 `MIMIC_LABITEM_CANDIDATE_DISCOVERY_V1.sql`。
- V1 标记为 `superseded_not_run`，仅保留历史原则。
- 新增 8 项 SQL 结构回归测试；其中一项强制 V1 在患者级读取前 fail closed。
- MIMIC 清洗 Skill 的 BUN quarantine 从 3 个扩充至 8 个有来源的非血液 itemid，并新增防止 quarantine 审计误报的回归测试。
- Skill 扫描器改为先剥离 SQL 注释，并区分字典级候选发现与患者级纳入，避免把注释或 `d_labitems` quarantine 清单误判为患者数据污染。

## 已验证

- SQL 结构测试：8/8 通过。
- Skill 合成回归：13/13 通过。
- 规则包校验通过。
- V2 经 Skill 静态扫描：无硬失败。
- 候选发现 SQL 不读取 `labevents`、subject_id 或 hadm_id。
- 网络与权限分层验证：经代理的 `bq SELECT 1` 成功；V2 dry-run 成功；受控 MIMIC 表访问被拒绝。连接成功不被误记为数据授权成功。

## 数据合同

- 正式审计合同：BUN 51006、乳酸 50813、肌酐 50912、pH 50820、NT-proBNP 50963、Troponin T 51003。
- BUN 非血液隔离：51104、51045、50851、51804、51825、51842、51922、51951。
- 时间窗 `[T0,T12)`；实验室结果必须满足 `GREATEST(charttime, COALESCE(storetime, charttime)) < T12`。
- 比较符号和区间保留边界；缺失不补零；未知单位、重复 specimen、跨 episode 和迟到结果进入 quarantine。

## 仍需执行

完成 PhysioNet/MIMIC-IV 数据使用授权并让同一 Google 账号获得 `physionet-data` 表读取权限后，先重跑字典候选查询，再重跑 V2 dry-run 和聚合查询；登记处理字节、SQL hash、reason code 分布及 BUN/乳酸 raw-only、derived-only、both。未获得这些输出前不得冻结实验室变量。
