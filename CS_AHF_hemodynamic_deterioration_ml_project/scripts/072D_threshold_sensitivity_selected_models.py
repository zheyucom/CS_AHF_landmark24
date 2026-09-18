import argparse
from pathlib import Path
import sys
import warnings
import joblib

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_curve, precision_recall_curve
from sklearn.exceptions import ConvergenceWarning

from cs_ahf_ml.config import load_config, project_path
from cs_ahf_ml.data import (
    split_columns,
    drop_high_missing_and_constant,
    build_preprocess_frame,
)
from cs_ahf_ml.metrics import binary_metrics, calibration_table


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)


def save_curve_plot(x, y, xlabel, ylabel, title, path):
    plt.figure(figsize=(5, 4))
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_performance_summary(metrics_df, path):
    test_df = metrics_df[metrics_df["split"] == "test"].copy()
    test_df = test_df.sort_values("n_features")

    plt.figure(figsize=(7, 5))
    for model_type in sorted(test_df["model_type"].unique()):
        sub = test_df[test_df["model_type"] == model_type]
        plt.plot(sub["n_features"], sub["auroc"], marker="o", label=f"{model_type} AUROC")
    plt.xlabel("Number of selected features")
    plt.ylabel("Test AUROC")
    plt.title("072D threshold sensitivity: AUROC")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path.parent / "072D_test_auroc_by_feature_count.png", dpi=220)
    plt.close()

    plt.figure(figsize=(7, 5))
    for model_type in sorted(test_df["model_type"].unique()):
        sub = test_df[test_df["model_type"] == model_type]
        plt.plot(sub["n_features"], sub["auprc"], marker="o", label=f"{model_type} AUPRC")
    plt.xlabel("Number of selected features")
    plt.ylabel("Test AUPRC")
    plt.title("072D threshold sensitivity: AUPRC")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path.parent / "072D_test_auprc_by_feature_count.png", dpi=220)
    plt.close()


def compact_missing_indicators(features, available_columns):
    """
    Reduce duplicated missing indicators.

    Example:
      lactate_first__missing, lactate_last__missing, lactate_max__missing
    are all replaced by lactate_available_flag if that column exists.

    This improves interpretability and external validation portability.
    """
    prefix_to_flag = {
        "lactate_": "lactate_available_flag",
        "ph_": "ph_available_flag",
        "creatinine_": "creatinine_available_flag",
        "bun_": "bun_available_flag",
        "wbc_": "wbc_available_flag",
        "platelet_": "platelet_available_flag",
        "inr_": "inr_available_flag",
        "nee_": "nee_available_0_12h_flag",
        "urineoutput_": "urineoutput_available_flag",
        "gcs_": "gcs_available_flag",
        "hr_": "hr_available_flag",
        "sbp_": "sbp_available_flag",
        "mbp_": "mbp_available_flag",
        "rr_": "rr_available_flag",
        "temp_": "temp_available_flag",
        "spo2_": "spo2_available_flag",
    }

    compacted = []
    for f in features:
        if f.endswith("__missing"):
            replaced = False
            for prefix, flag in prefix_to_flag.items():
                if f.startswith(prefix) and flag in available_columns:
                    compacted.append(flag)
                    replaced = True
                    break
            if not replaced:
                compacted.append(f)
        else:
            compacted.append(f)

    # Preserve order and remove duplicates.
    out = []
    seen = set()
    for f in compacted:
        if f not in seen and f in available_columns:
            out.append(f)
            seen.add(f)

    return out


def remove_portability_sensitive_features(features):
    """
    Remove variables likely to be institution/process/coding dependent.
    These can remain in extended/full models but should not dominate
    portable external-validation-oriented models.
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
        "male",
        "hf_icd_primary_seq",
        "hf_icd_seq_le5",
    }

    portable = []
    for f in features:
        if f in exclude_exact:
            continue
        if f.startswith(exclude_prefixes):
            continue
        portable.append(f)

    return portable


def get_feature_set_from_frequency(freq_df, processed_columns, mode, compact=True, portable=False):
    """
    mode examples:
      freq_ge_0_80
      freq_ge_0_50
      freq_ge_0_30
      top30
      top50
      top80
    """
    freq_df = freq_df[freq_df["feature"].isin(processed_columns)].copy()

    if mode.startswith("freq_ge_"):
        threshold_str = mode.replace("freq_ge_", "").replace("_", ".")
        threshold = float(threshold_str)
        features = freq_df.loc[freq_df["selection_frequency"] >= threshold, "feature"].tolist()
    elif mode.startswith("top"):
        k = int(mode.replace("top", ""))
        features = freq_df.head(k)["feature"].tolist()
    else:
        raise ValueError(f"Unknown mode: {mode}")

    if portable:
        features = remove_portability_sensitive_features(features)

    if compact:
        features = compact_missing_indicators(features, processed_columns)

    return features


def make_model(model_type, cfg):
    if model_type == "l2":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                penalty="l2",
                solver="lbfgs",
                class_weight="balanced",
                max_iter=5000,
                random_state=cfg["random_seed"],
            )),
        ])

    if model_type == "elasticnet":
        return Pipeline([
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

    raise ValueError(f"Unknown model_type: {model_type}")


def train_evaluate(
    feature_set_name,
    model_type,
    features,
    X_train_all,
    X_test_all,
    y_train,
    y_test,
    cfg,
    model_dir,
    fig_dir,
    table_dir,
):
    X_train = X_train_all[features].copy()
    X_test = X_test_all[features].copy()

    model = make_model(model_type, cfg)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ConvergenceWarning)
        model.fit(X_train, y_train)

    p_train = model.predict_proba(X_train)[:, 1]
    p_test = model.predict_proba(X_test)[:, 1]

    metrics = [
        {
            "feature_set": feature_set_name,
            "model_type": model_type,
            "split": "train",
            "n_features": len(features),
            **binary_metrics(y_train, p_train),
        },
        {
            "feature_set": feature_set_name,
            "model_type": model_type,
            "split": "test",
            "n_features": len(features),
            **binary_metrics(y_test, p_test),
        },
    ]

    calibration_table(y_test, p_test, n_bins=10).to_csv(
        table_dir / f"072D_calibration_{feature_set_name}_{model_type}.csv",
        index=False,
    )

    fpr, tpr, _ = roc_curve(y_test, p_test)
    precision, recall, _ = precision_recall_curve(y_test, p_test)

    save_curve_plot(
        fpr,
        tpr,
        "False positive rate",
        "True positive rate",
        f"Test ROC - {feature_set_name} - {model_type}",
        fig_dir / f"072D_test_roc_{feature_set_name}_{model_type}.png",
    )

    save_curve_plot(
        recall,
        precision,
        "Recall",
        "Precision",
        f"Test PR - {feature_set_name} - {model_type}",
        fig_dir / f"072D_test_pr_{feature_set_name}_{model_type}.png",
    )

    joblib.dump(
        {
            "model": model,
            "features": features,
            "config": cfg,
        },
        model_dir / f"072D_{feature_set_name}_{model_type}.joblib",
    )

    coef_rows = []
    try:
        coefs = model.named_steps["clf"].coef_.ravel()
        for f, coef in zip(features, coefs):
            coef_rows.append({
                "feature_set": feature_set_name,
                "model_type": model_type,
                "feature": f,
                "coef": coef,
                "abs_coef": abs(coef),
            })
    except Exception:
        pass

    return metrics, coef_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument(
        "--model_types",
        default="both",
        choices=["both", "l2", "elasticnet"],
        help="Use both for full comparison. Use l2 for quick screening.",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])

    qc_dir = project_path(cfg, cfg["paths"]["qc_dir"])
    model_dir = project_path(cfg, cfg["paths"]["model_dir"])
    fig_dir = project_path(cfg, cfg["paths"]["figure_dir"])
    table_dir = project_path(cfg, cfg["paths"]["table_dir"])
    freq_path = table_dir / "072C_feature_selection_frequency.csv"

    for d in [qc_dir, model_dir, fig_dir, table_dir]:
        d.mkdir(parents=True, exist_ok=True)

    if not freq_path.exists():
        raise FileNotFoundError(
            f"{freq_path} not found. Please run 072C first."
        )

    df = pd.read_csv(raw_path)
    freq_df = pd.read_csv(freq_path)

    all_raw_features, label_col, exclude_cols = split_columns(df, cfg)
    y = df[label_col].astype(int)

    train_idx, test_idx = train_test_split(
        np.arange(len(df)),
        test_size=cfg["preprocessing"]["test_size"],
        random_state=cfg["random_seed"],
        stratify=y,
    )

    train_df = df.iloc[train_idx].reset_index(drop=True)
    test_df = df.iloc[test_idx].reset_index(drop=True)

    y_train = train_df[label_col].astype(int)
    y_test = test_df[label_col].astype(int)

    kept_raw_features, raw_feature_qc = drop_high_missing_and_constant(
        train_df,
        all_raw_features,
        high_missing_threshold=cfg["preprocessing"]["high_missing_threshold"],
        unique_threshold=cfg["preprocessing"]["near_zero_variance_unique_threshold"],
    )

    X_train_all, prep_stats = build_preprocess_frame(
        train_df,
        kept_raw_features,
        cfg,
        fit_stats=None,
    )

    X_test_all, _ = build_preprocess_frame(
        test_df,
        kept_raw_features,
        cfg,
        fit_stats=prep_stats,
    )

    X_test_all = X_test_all.reindex(columns=X_train_all.columns, fill_value=0)
    processed_columns = list(X_train_all.columns)

    selection_modes = [
        "freq_ge_0_80",
        "freq_ge_0_50",
        "freq_ge_0_30",
        "top30",
        "top50",
        "top80",
    ]

    feature_sets = {}

    for mode in selection_modes:
        feature_sets[f"{mode}_compact"] = get_feature_set_from_frequency(
            freq_df,
            processed_columns,
            mode=mode,
            compact=True,
            portable=False,
        )

    feature_sets["portable_freq_ge_0_50_compact"] = get_feature_set_from_frequency(
        freq_df,
        processed_columns,
        mode="freq_ge_0_50",
        compact=True,
        portable=True,
    )

    feature_sets["portable_top50_compact"] = get_feature_set_from_frequency(
        freq_df,
        processed_columns,
        mode="top50",
        compact=True,
        portable=True,
    )

    feature_sets["portable_top30_compact"] = get_feature_set_from_frequency(
        freq_df,
        processed_columns,
        mode="top30",
        compact=True,
        portable=True,
    )

    # Remove any empty or tiny feature sets.
    feature_sets = {
        name: feats
        for name, feats in feature_sets.items()
        if len(feats) >= 5
    }

    model_types = ["l2", "elasticnet"] if args.model_types == "both" else [args.model_types]

    all_metrics = []
    all_coef_rows = []
    feature_set_rows = []

    for name, features in feature_sets.items():
        feature_set_rows.append({
            "feature_set": name,
            "n_features": len(features),
            "features": "|".join(features),
        })

        print(f"[RUN] {name}: {len(features)} features")

        for model_type in model_types:
            print(f"      model={model_type}")
            metrics, coef_rows = train_evaluate(
                feature_set_name=name,
                model_type=model_type,
                features=features,
                X_train_all=X_train_all,
                X_test_all=X_test_all,
                y_train=y_train,
                y_test=y_test,
                cfg=cfg,
                model_dir=model_dir,
                fig_dir=fig_dir,
                table_dir=table_dir,
            )

            all_metrics.extend(metrics)
            all_coef_rows.extend(coef_rows)

    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.to_csv(
        table_dir / "072D_threshold_sensitivity_metrics.csv",
        index=False,
    )

    feature_set_df = pd.DataFrame(feature_set_rows)
    feature_set_df.to_csv(
        table_dir / "072D_feature_set_counts.csv",
        index=False,
    )

    pd.DataFrame(all_coef_rows).sort_values(
        ["feature_set", "model_type", "abs_coef"],
        ascending=[True, True, False],
    ).to_csv(
        table_dir / "072D_coefficients_by_feature_set.csv",
        index=False,
    )

    # Long feature membership table.
    long_rows = []
    for name, features in feature_sets.items():
        for rank, f in enumerate(features, start=1):
            long_rows.append({
                "feature_set": name,
                "rank_in_feature_set": rank,
                "feature": f,
            })

    pd.DataFrame(long_rows).to_csv(
        table_dir / "072D_feature_sets_long.csv",
        index=False,
    )

    plot_performance_summary(
        metrics_df,
        fig_dir / "072D_test_performance_by_feature_count.png",
    )

    run_summary = pd.DataFrame([{
        "n_rows": len(df),
        "n_train": len(train_df),
        "n_test": len(test_df),
        "n_events_total": int(df[label_col].sum()),
        "n_events_train": int(y_train.sum()),
        "n_events_test": int(y_test.sum()),
        "n_raw_candidate_features": len(all_raw_features),
        "n_kept_raw_features": len(kept_raw_features),
        "n_processed_features": len(processed_columns),
        "n_feature_sets": len(feature_sets),
        "model_types": ",".join(model_types),
    }])

    run_summary.to_csv(
        table_dir / "072D_run_summary.csv",
        index=False,
    )

    print("[OK] 072D threshold sensitivity complete")
    print(metrics_df[metrics_df["split"] == "test"].sort_values(
        ["auroc", "auprc"],
        ascending=False,
    ).to_string(index=False))


if __name__ == "__main__":
    main()
