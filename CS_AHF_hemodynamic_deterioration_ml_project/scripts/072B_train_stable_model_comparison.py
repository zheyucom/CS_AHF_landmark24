import argparse
from pathlib import Path
import sys
import json
import joblib

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
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


def select_core_features(feature_cols):
    """
    Core clinical features:
    Keep variables that are clinically stable and easier to validate externally.
    Exclude coding/process/unit variables and AHF evidence-selection variables.
    """
    exclude_prefixes = (
        "first_unit_",
        "hf_icd_",
        "acute_hf_icd",
        "iv_loop_",
        "ntprobnp_",
        "ahf_evidence_",
        "suspected_infection_",
    )

    exclude_exact = {
        "male",  # keep female only to avoid redundancy
        "hf_icd_seq_le5",
        "hf_icd_primary_seq",
    }

    core = []
    for c in feature_cols:
        if c in exclude_exact:
            continue
        if c.startswith(exclude_prefixes):
            continue
        core.append(c)

    return core


def select_extended_features(feature_cols):
    """
    Extended model:
    Keep most variables but still exclude high-risk external validation/process variables.
    """
    exclude_prefixes = (
        "first_unit_",
    )

    exclude_exact = {
        "male",
    }

    extended = []
    for c in feature_cols:
        if c in exclude_exact:
            continue
        if c.startswith(exclude_prefixes):
            continue
        extended.append(c)

    return extended


def train_and_eval_model(model_name, model, train_df, test_df, feature_cols, cfg):
    label_col = cfg["target"]["label_col"]

    kept_cols, feature_qc = drop_high_missing_and_constant(
        train_df,
        feature_cols,
        high_missing_threshold=cfg["preprocessing"]["high_missing_threshold"],
        unique_threshold=cfg["preprocessing"]["near_zero_variance_unique_threshold"],
    )

    X_train, prep_stats = build_preprocess_frame(train_df, kept_cols, cfg, fit_stats=None)
    X_test, _ = build_preprocess_frame(test_df, kept_cols, cfg, fit_stats=prep_stats)
    X_test = X_test.reindex(columns=X_train.columns, fill_value=0)

    y_train = train_df[label_col].astype(int)
    y_test = test_df[label_col].astype(int)

    model.fit(X_train, y_train)

    p_train = model.predict_proba(X_train)[:, 1]
    p_test = model.predict_proba(X_test)[:, 1]

    metrics_train = {"model": model_name, "split": "train", **binary_metrics(y_train, p_train)}
    metrics_test = {"model": model_name, "split": "test", **binary_metrics(y_test, p_test)}

    return {
        "model_name": model_name,
        "model": model,
        "features": list(X_train.columns),
        "prep_stats": prep_stats,
        "metrics": [metrics_train, metrics_test],
        "y_test": y_test,
        "p_test": p_test,
    }


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

    all_feature_cols, label_col, exclude_cols = split_columns(df, cfg)
    y = df[label_col].astype(int)

    train_idx, test_idx = train_test_split(
        np.arange(len(df)),
        test_size=cfg["preprocessing"]["test_size"],
        random_state=cfg["random_seed"],
        stratify=y,
    )

    train_df = df.iloc[train_idx].reset_index(drop=True)
    test_df = df.iloc[test_idx].reset_index(drop=True)

    core_features = select_core_features(all_feature_cols)
    extended_features = select_extended_features(all_feature_cols)
    full_features = all_feature_cols

    model_specs = [
        (
            "core_l2_logistic",
            core_features,
            Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(
                    penalty="l2",
                    solver="lbfgs",
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=cfg["random_seed"],
                )),
            ]),
        ),
        (
            "extended_l2_logistic",
            extended_features,
            Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(
                    penalty="l2",
                    solver="lbfgs",
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=cfg["random_seed"],
                )),
            ]),
        ),
        (
            "full_l2_logistic",
            full_features,
            Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(
                    penalty="l2",
                    solver="lbfgs",
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=cfg["random_seed"],
                )),
            ]),
        ),
        (
            "full_elasticnet_logistic",
            full_features,
            Pipeline([
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
            ]),
        ),
    ]

    all_metrics = []
    model_summary = []

    for model_name, feature_set, model in model_specs:
        print(f"[RUN] {model_name} with {len(feature_set)} candidate features")

        result = train_and_eval_model(
            model_name=model_name,
            model=model,
            train_df=train_df,
            test_df=test_df,
            feature_cols=feature_set,
            cfg=cfg,
        )

        all_metrics.extend(result["metrics"])

        model_summary.append({
            "model": model_name,
            "n_final_features_after_preprocessing": len(result["features"]),
        })

        joblib.dump(
            {
                "model": result["model"],
                "features": result["features"],
                "prep_stats": result["prep_stats"],
                "config": cfg,
            },
            model_dir / f"072B_{model_name}.joblib",
        )

        # Curves for each model
        fpr, tpr, _ = roc_curve(result["y_test"], result["p_test"])
        precision, recall, _ = precision_recall_curve(result["y_test"], result["p_test"])

        save_curve_plot(
            fpr,
            tpr,
            "False positive rate",
            "True positive rate",
            f"Test ROC - {model_name}",
            fig_dir / f"072B_test_roc_{model_name}.png",
        )

        save_curve_plot(
            recall,
            precision,
            "Recall",
            "Precision",
            f"Test PR - {model_name}",
            fig_dir / f"072B_test_pr_{model_name}.png",
        )

        calibration_table(
            result["y_test"],
            result["p_test"],
            n_bins=10,
        ).to_csv(
            table_dir / f"072B_test_calibration_{model_name}.csv",
            index=False,
        )

    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.to_csv(table_dir / "072B_model_comparison_metrics.csv", index=False)

    pd.DataFrame(model_summary).to_csv(
        table_dir / "072B_model_feature_counts.csv",
        index=False,
    )

    print("[OK] 072B model comparison complete")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()