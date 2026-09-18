# CS_AHF Hemodynamic Deterioration ML Project

主研究问题：急性心力衰竭合并早期脓毒症 ICU 患者，在 ICU 入科 12 h landmark 后未来 48 h 发生血流动力学恶化的早期预测模型。

## 当前数据版本

- 输入表：`model_070G_modeling_dataset_v1.csv`
- 样本量：2424
- 主结局：`primary_outcome_flag`
- 事件数：334
- 事件率：13.78%

## 推荐运行顺序

```bash
python scripts/071_data_qc.py --config config/config.yaml
python scripts/072_train_baseline_models.py --config config/config.yaml
```

## 数据泄露控制

建模时自动排除：
- `subject_id`, `hadm_id`, `stay_id`
- `intime`, `landmark12_time`, `window60_time`
- `primary_outcome_flag`
- 所有 `label_` 开头的列

所有候选预测变量均应来自 ICU 入科 0–12 h。
后续如果纳入 echo / note 特征，必须明确检查时间或报告可用时间在 landmark 前。

## 目录说明

- `data/raw/`：原始导出数据，只读保存。
- `data/processed/`：Python 预处理后的建模数据。
- `docs/`：变量清单、数据字典、方法记录。
- `src/cs_ahf_ml/`：可复用函数。
- `scripts/`：可重复执行的分析脚本。
- `outputs/qc/`：QC 表格。
- `outputs/models/`：模型文件。
- `outputs/figures/`：图。
- `outputs/tables/`：论文表格。
