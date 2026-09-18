# MIMIC v3 全链完成报告

日期：2026-08-24  
Run ID：`20260824_v3_init`

## 完成范围

- 从 Navicat 与仓库恢复有效 SQL，原件和 SHA-256 保存在 `sql_v3/`。
- 每次运行先删除并重建且仅重建 `study_ahf_v3`，历史 `study_ahf` 保持不变。
- 执行 010-070G、079A、080A、080G、081A；逐文件日志均无错误。
- 导出 v3 主建模集、事件时间、主结局明细和结构化超声筛查数据。
- 使用独立 `config_v3.yaml` 完整运行 071-078A，结果写入 `outputs_v3/`。

## 数据审计

| 项目 | 结果 |
|---|---:|
| 成人首次 ICU | 65,366 |
| HF ICD candidate | 14,877 |
| strict AHF12 | 7,562 |
| landmark12 risk set | 6,301 |
| early sepsis12 主分析 | 2,424 |
| 主结局事件 | 334 |
| 主结局率 | 13.78% |
| 080G 列数 | 318 |
| 重复 stay | 0 |
| 标签/事件时间 mismatch | 0 |

v3 与历史 cohort flow 各步行数差均为 0。旧、新 080G 仅 6 个实验室均值列有
最大 `7.1e-15` 的浮点聚合差异，标签、ID、列结构完全一致。

## 模型结果

- 30 次主结局分析：AUROC 0.7614，AUPRC 0.3459，Brier 0.1062。
- 20 次重复内部验证 top80 elastic-net + Platt：AUROC 0.7610，AUPRC 0.3478，
  Brier 0.1061。
- 最终候选集 66 个特征，其中 61 个非零。
- 固定测试集：TP 22、FP 75、FN 45、TN 343。
- 9 个结局/队列/时间窗敏感性变体均完成。

## 事实源

- SQL：`sql_v3/executable/`
- SQL 原件：`sql_v3/recovered_original/`
- 数据：`CS_AHF_hemodynamic_deterioration_ml_project/data/raw_v3/`
- 模型和论文表图：`CS_AHF_hemodynamic_deterioration_ml_project/outputs_v3/`
- 日志：`project_control/runs/20260824_v3_init/`
- 哈希：`sql_v3/SOURCE_SHA256.tsv` 与 `run_manifest.json`

## 验证与清理

- `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v`：通过。
- 项目虚拟环境未安装 `pytest`，未为单个 unittest 增加依赖。
- 已删除项目缓存、`.DS_Store` 和 Codex 临时目录。
- 历史 SQL/CSV/outputs 暂保留为只读对照，不属于 v3 事实源。

## 剩余工作

MIMIC 开发阶段完成。全项目尚待本院脱敏样例和全量数据，以完成字段对齐、
外部验证、必要时仅再校准，以及最终论文定稿。
