# 071 Modeling QC Template

建议先运行脚本：

```bash
python scripts/071_data_qc.py --config config/config.yaml
python scripts/072_train_baseline_models.py --config config/config.yaml
```

然后检查：
- `outputs/qc/071_dataset_summary.csv`
- `outputs/qc/071_feature_qc.csv`
- `outputs/tables/072_baseline_elasticnet_metrics.csv`
- `outputs/tables/072_elasticnet_coefficients.csv`
- `outputs/figures/072_test_roc.png`
- `outputs/figures/072_test_pr_curve.png`
