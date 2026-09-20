# 开题报告按当前研究主线重写与图示更新

日期：2026-09-20

## 1. 用户问题与本轮范围

用户提供浙江大学医学院 2026-03-25 版开题报告 DOCX，要求删除旧内容，按项目当前真实研究进展重写，保留学校模板格式，并将新文件放到电脑桌面。本轮同时更新 landmark 时间轴和双库技术路线图，未开展新的患者级分析、临床裁决或模型拟合。

## 2. 使用的文件、版本和数据状态

- 模板：`/workspace/inbox/开题报告_心衰新发心源性休克预测模型_占舒羽_3.25.docx`；SHA-256=`61aceec369ab28a0b02efa7856deae51d504ee287bc65a94c67f8f381f2b715e`。
- 当前状态入口：`project_control/RESEARCH_DASHBOARD.md`。
- 研究定义：`RESEARCH_LOGIC_CHAIN_20260916.md`、`DHF_OPERATIONAL_PHENOTYPE_v20260914.md`、`STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md`、`DHF_PROJECT_REPRODUCIBILITY_CONTRACT_V1.md`。
- 方法与文献：`PROPOSAL_METHODS_DRAFT_20260915.md`、`METHODS_EVIDENCE_MAP_20260915.md`。
- 最新进展：`TASK_REPORT_20260919_MIMIC_LAB_PIPELINE_PHASE_C.md` 与 `TASK_REPORT_20260920_MIMIC_BIGQUERY_PHASE_C.md`。
- 数据状态未改变：最终 DHF 表型、T12 风险集、三态结局和正式模型仍未冻结，`allow_final_run=false`。

## 3. 已验证事实与证据

- 学校封面、学号、姓名、专业、导师、分节和页边距从原模板继承；日期更新为 2026-09-20。
- 题目更新为“ICU失代偿性心力衰竭患者早期血流动力学恶化或死亡的预测模型：基于MIMIC的开发与内部验证及单中心外部验证”。
- 正文按当前六步逻辑链重建：候选分母 → ICU 时间轴 → DHF 多域表型 → T12 风险集 → 三态结局 → 模型开发和验证。
- 图1更新为 T0/T12/T60 landmark 与竞争风险时间轴；图2更新为 MIMIC 开发/内部验证、锁模及本院外部验证技术路线。两图为研究设计示意，不含患者级数据或模型性能。
- 当前进展表明确区分候选分母、数据覆盖、临床预审核、质量控制和正式结果；8,385、7,828、37,778,198、37,732,919 等只按其审核语义出现。
- 文本扫描确认不含旧题目、旧固定时间窗、历史 `4,740/174/3.67%` 或 `new-onset CS` 表述。
- DOCX 压缩包已删除 3 个不再被正文引用的旧图关系，仅保留封面校徽及两幅新版图示。

## 4. 判断与影响

旧开题将历史宽口径模型、固定二分类终点和当时的样本量写成接近正式结果，已不能代表当前项目。新版把主要终点改为治疗升级相关 ICU 血流动力学恶化或 ICU 内死亡，活着离开 index ICU 为竞争事件，并将 MIMIC 与本院角色锁定为开发/内部验证和锁模后外部验证。

新版可用于当前纸质开题讨论，但伦理批件号、最终队列人数、事件数和模型性能仍必须在正式文件或冻结运行完成后补录，不能从本报告推断。

## 5. 新增或确认的研究决策

- 未新增或修改正式研究定义；本轮只把已生效合同转写到学校开题模板。
- 开题报告中不再把主要终点称为纯心源性休克，也不把单项 BNP、心超或治疗医嘱当作 DHF 充分条件。
- 当前 AI 预审核、候选人数和旧模型只作为工作进展或工程可行性，不作为临床金标准或正式结果。
- 图示使用原生可编辑 PPTX 及 SVG/PNG；当前运行环境未暴露可核验的图像生成端点，因此概念生图阶段记录为 `not_run`，不影响纯矢量研究设计示意的内容真实性。

## 6. 未决问题、阻塞项和假设

- 院内伦理批件号、研究覆盖年月和知情同意豁免状态尚未从正式文件核验。
- MIMIC 300 条临床确认和 60 条第二标注者盲法复核尚未完成。
- 双库 DHF 表型、T12 风险集、三态结局、完整 v3.3 依赖链和正式模型仍未冻结。
- Microsoft Word 无界面 PDF 导出在本机 GUI 会话中超时，未生成 PDF；已用 DOCX 结构、ZIP 完整性、系统 Quick Look、图片原图和 SHA-256 完成替代验证。

## 7. 下一步动作

1. 用户/导师审阅开题报告中的题目、研究计划和伦理占位表述。
2. 若学校要求固定页数或特定参考文献格式，再在同一模板上做版面压缩或格式调整。
3. 按现有项目计划继续完成临床裁决、结局冻结、正式建模和外部验证；冻结后再更新开题/中期检查中的最终数字。

## 8. 本轮修改文件

- `deliverables/opening_proposal_20260920/开题报告_ICU失代偿性心力衰竭患者早期血流动力学恶化或死亡预测模型_占舒羽_9.20.docx`
- `deliverables/opening_proposal_20260920/开题报告图示_可编辑源文件_占舒羽_20260920.pptx`
- `deliverables/opening_proposal_20260920/figure_assets/`
- `deliverables/opening_proposal_20260920/BUILD_DESIGN.md`
- `scripts/build_opening_proposal_20260920.py`
- `project_control/task_reports/TASK_REPORT_20260920_PROPOSAL_REPORT_REFRESH.md`
- `project_control/task_reports/README.md`
- `project_control/RESEARCH_DASHBOARD.md`

用户电脑 Desktop 另放置最终 DOCX 和可编辑图示 PPTX，内容与项目交付副本哈希一致。

## 9. 可重复性信息

- 生成脚本 SHA-256：`f322795b6bd001e807ef82ad13d0d9e126c8fe3c30ac96d3bdcdd8cec8cb30dd`。
- 最终 DOCX SHA-256：`89383782f99a57214c1c57eab5706aad5a3c5f71c0219083fe0abe1168915a16`。
- 可编辑图示 PPTX SHA-256：`d4e9babc772019777f0130042bd9335e1a0d62b98dd6be66cc3db54544d87798`。
- 图1 PNG SHA-256：`8f38f51f4c8a657c7a6bab583be562027f6858a052b2955bb39a22aa4095ecb8`。
- 图2 PNG SHA-256：`1b7676506bfd45ff7d4dafe63aa4dd10553e3a7e6e02d832106afe39a6e5e300`。
- 本轮无随机抽样、插补或模型拟合，不涉及 seed。
- Git 状态：本轮文件已在本机 `main` 创建提交；推送时 GitHub SSH 拒绝现有公钥，HTTPS 又无可用写入凭证，因此本地相对 `origin/main` 为 `ahead 1`，远端尚未同步。
