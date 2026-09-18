import argparse
from pathlib import Path
import sys
import json
import joblib

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegressionCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_curve, precision_recall_curve
import matplotlib.pyplot as plt

from cs_ahf_ml.config import load_config, project_path
from cs_ahf_ml.data import split_columns, drop_high_missing_and_constant, build_preprocess_frame
from cs_ahf_ml.metrics import binary_metrics, calibration_table

def save_curve_plot(x, y, xlabel, ylabel, title, path):
    plt.figure(figsize=(5, 4))
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])
    qc_dir = project_path(cfg, cfg["paths"]["qc_dir"])
    model_dir = project_path(cfg, cfg["paths"]["model_dir"])
    fig_dir = project_path(cfg, cfg["paths"]["figure_dir"])
    table_dir = project_path(cfg, cfg["paths"]["table_dir"])
    for d in [qc_dir, model_dir, fig_dir, table_dir]:
        d.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(raw_path)
    feature_cols, label_col, exclude_cols = split_columns(df, cfg)
    kept_cols, feature_qc = drop_high_missing_and_constant(
        df,
        feature_cols,
        high_missing_threshold=cfg["preprocessing"]["high_missing_threshold"],
        unique_threshold=cfg["preprocessing"]["near_zero_variance_unique_threshold"],
    )

    y = df[label_col].astype(int)
    train_idx, test_idx = train_test_split(
        np.arange(len(df)),
        test_size=cfg["preprocessing"]["test_size"],
        random_state=cfg["random_seed"],
        stratify=y,
    )

    train_df = df.iloc[train_idx].reset_index(drop=True)
    test_df = df.iloc[test_idx].reset_index(drop=True)

    X_train, prep_stats = build_preprocess_frame(train_df, kept_cols, cfg, fit_stats=None)
    X_test, _ = build_preprocess_frame(test_df, kept_cols, cfg, fit_stats=prep_stats)

    # Align columns after missing indicators are created
    X_test = X_test.reindex(columns=X_train.columns, fill_value=0)

    y_train = train_df[label_col].astype(int)
    y_test = test_df[label_col].astype(int)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegressionCV(
            Cs=8,
            cv=cfg["models"]["cv_folds"],
            penalty="elasticnet",
            solver="saga",
            l1_ratios=[0.1, 0.5, 0.9],
            scoring="roc_auc",
            max_iter=30000,
            tol=1e-3,
            class_weight="balanced",
            n_jobs=-1,
            random_state=cfg["random_seed"],
        )),
    ])
    model.fit(X_train, y_train)

    p_train = model.predict_proba(X_train)[:, 1]
    p_test = model.predict_proba(X_test)[:, 1]

    metrics = pd.DataFrame([
        {"split": "train", **binary_metrics(y_train, p_train)},
        {"split": "test", **binary_metrics(y_test, p_test)},
    ])
    metrics.to_csv(table_dir / "072_baseline_elasticnet_metrics.csv", index=False)

    calibration_table(y_test, p_test, n_bins=10).to_csv(table_dir / "072_test_calibration_table.csv", index=False)

    fpr, tpr, _ = roc_curve(y_test, p_test)
    precision, recall, _ = precision_recall_curve(y_test, p_test)
    save_curve_plot(fpr, tpr, "False positive rate", "True positive rate", "Test ROC", fig_dir / "072_test_roc.png")
    save_curve_plot(recall, precision, "Recall", "Precision", "Test PR curve", fig_dir / "072_test_pr_curve.png")

    clf = model.named_steps["clf"]
    coefs = clf.coef_.ravel()
    coef_df = pd.DataFrame({"feature": X_train.columns, "coef": coefs})
    coef_df["abs_coef"] = coef_df["coef"].abs()
    coef_df.sort_values("abs_coef", ascending=False).to_csv(table_dir / "072_elasticnet_coefficients.csv", index=False)

    joblib.dump({"model": model, "features": list(X_train.columns), "prep_stats": prep_stats, "config": cfg}, model_dir / "072_elasticnet_model.joblib")

    print("[OK] baseline Elastic Net logistic model complete")
    print(metrics.to_string(index=False))

if __name__ == "__main__":
    main()
