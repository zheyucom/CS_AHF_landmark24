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


def save_curve_plot(x, y, xlabel, ylabel, title, path):
    plt.figure(figsize=(5, 4))
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def save_selection_frequency_plot(freq_df, path, top_n=30):
    plot_df = freq_df.head(top_n).iloc[::-1]

    plt.figure(figsize=(7, 8))
    plt.barh(plot_df["feature"], plot_df["selection_frequency"])
    plt.xlabel("Selection frequency")
    plt.ylabel("Feature")
    plt.title(f"Top {top_n} stable selected features")
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def fit_full_elasticnet_cv(X_train, y_train, cfg):
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

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ConvergenceWarning)
        model.fit(X_train, y_train)

    clf = model.named_steps["clf"]

    # LogisticRegressionCV stores selected values differently depending on sklearn version.
    best_c = float(np.ravel(clf.C_)[0])

    try:
        best_l1_ratio = float(np.ravel(clf.l1_ratio_)[0])
    except Exception:
        best_l1_ratio = 0.5

    return model, best_c, best_l1_ratio


def bootstrap_stability_selection(
    train_df,
    kept_raw_features,
    label_col,
    cfg,
    reference_processed_cols,
    best_c,
    best_l1_ratio,
    n_bootstraps=50,
    random_seed=2026,
):
    rng = np.random.default_rng(random_seed)

    selected_counts = pd.Series(0, index=reference_processed_cols, dtype=float)
    coef_sum = pd.Series(0.0, index=reference_processed_cols, dtype=float)
    convergence_warnings = 0

    n_train = len(train_df)

    for b in range(n_bootstraps):
        boot_idx = rng.integers(0, n_train, size=n_train)
        boot_df = train_df.iloc[boot_idx].reset_index(drop=True)

        X_boot, _ = build_preprocess_frame(
            boot_df,
            kept_raw_features,
            cfg,
            fit_stats=None,
        )

        # Align to reference feature space from the original training set.
        X_boot = X_boot.reindex(columns=reference_processed_cols, fill_value=0)
        y_boot = boot_df[label_col].astype(int)

        model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                penalty="elasticnet",
                solver="saga",
                C=best_c,
                l1_ratio=best_l1_ratio,
                class_weight="balanced",
                max_iter=15000,
                tol=1e-3,
                random_state=random_seed + b,
            )),
        ])

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", category=ConvergenceWarning)
            model.fit(X_boot, y_boot)

            if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                convergence_warnings += 1

        coefs = model.named_steps["clf"].coef_.ravel()
        selected = np.abs(coefs) > 1e-8

        selected_counts += selected.astype(float)
        coef_sum += coefs

        if (b + 1) % 10 == 0:
            print(f"[BOOT] completed {b + 1}/{n_bootstraps}")

    freq_df = pd.DataFrame({
        "feature": reference_processed_cols,
        "selection_count": selected_counts.values,
        "selection_frequency": selected_counts.values / n_bootstraps,
        "mean_coef_over_bootstraps": coef_sum.values / n_bootstraps,
    })

    freq_df["abs_mean_coef"] = freq_df["mean_coef_over_bootstraps"].abs()
    freq_df = freq_df.sort_values(
        ["selection_frequency", "abs_mean_coef"],
        ascending=[False, False],
    ).reset_index(drop=True)

    return freq_df, convergence_warnings


def train_evaluate_fixed_feature_model(
    model_name,
    X_train_all,
    X_test_all,
    y_train,
    y_test,
    selected_processed_features,
    cfg,
    model_type="l2",
):
    X_train = X_train_all[selected_processed_features].copy()
    X_test = X_test_all[selected_processed_features].copy()

    if model_type == "l2":
        model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                penalty="l2",
                solver="lbfgs",
                class_weight="balanced",
                max_iter=5000,
                random_state=cfg["random_seed"],
            )),
        ])
    elif model_type == "elasticnet":
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
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ConvergenceWarning)
        model.fit(X_train, y_train)

    p_train = model.predict_proba(X_train)[:, 1]
    p_test = model.predict_proba(X_test)[:, 1]

    metrics = [
        {"model": model_name, "split": "train", **binary_metrics(y_train, p_train)},
        {"model": model_name, "split": "test", **binary_metrics(y_test, p_test)},
    ]

    return model, metrics, p_test


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--n_bootstraps", type=int, default=50)
    parser.add_argument("--selection_threshold", type=float, default=0.30)
    parser.add_argument("--min_selected_features", type=int, default=25)
    parser.add_argument("--top_k_fallback", type=int, default=40)
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

    # Drop high-missing and constant variables using training set only.
    kept_raw_features, raw_feature_qc = drop_high_missing_and_constant(
        train_df,
        all_raw_features,
        high_missing_threshold=cfg["preprocessing"]["high_missing_threshold"],
        unique_threshold=cfg["preprocessing"]["near_zero_variance_unique_threshold"],
    )

    raw_feature_qc.to_csv(
        qc_dir / "072C_raw_feature_qc_train_only.csv",
        index=False,
    )

    # Build processed training/test matrices using training-set fitted preprocessing.
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
    processed_features = list(X_train_all.columns)

    print(f"[INFO] raw candidate features: {len(all_raw_features)}")
    print(f"[INFO] kept raw features after train-only QC: {len(kept_raw_features)}")
    print(f"[INFO] processed features after missing indicators: {len(processed_features)}")

    # Full elastic-net CV to obtain tuning parameters.
    print("[RUN] fitting full elastic-net CV for reference tuning")
    full_en_model, best_c, best_l1_ratio = fit_full_elasticnet_cv(
        X_train_all,
        y_train,
        cfg,
    )

    p_train_full = full_en_model.predict_proba(X_train_all)[:, 1]
    p_test_full = full_en_model.predict_proba(X_test_all)[:, 1]

    full_metrics = [
        {"model": "full_elasticnet_reference", "split": "train", **binary_metrics(y_train, p_train_full)},
        {"model": "full_elasticnet_reference", "split": "test", **binary_metrics(y_test, p_test_full)},
    ]

    print(f"[INFO] best C from full elastic-net CV: {best_c}")
    print(f"[INFO] best l1_ratio from full elastic-net CV: {best_l1_ratio}")

    # Bootstrap stability selection.
    print("[RUN] bootstrap stability selection")
    freq_df, n_conv_warn = bootstrap_stability_selection(
        train_df=train_df,
        kept_raw_features=kept_raw_features,
        label_col=label_col,
        cfg=cfg,
        reference_processed_cols=processed_features,
        best_c=best_c,
        best_l1_ratio=best_l1_ratio,
        n_bootstraps=args.n_bootstraps,
        random_seed=cfg["random_seed"],
    )

    freq_df.to_csv(
        table_dir / "072C_feature_selection_frequency.csv",
        index=False,
    )

    # Select stable features.
    selected = freq_df.loc[
        freq_df["selection_frequency"] >= args.selection_threshold,
        "feature"
    ].tolist()

    if len(selected) < args.min_selected_features:
        selected = freq_df.head(args.top_k_fallback)["feature"].tolist()
        selection_rule = f"top_{args.top_k_fallback}_fallback"
    else:
        selection_rule = f"frequency_ge_{args.selection_threshold}"

    selected_df = pd.DataFrame({
        "selected_feature": selected,
        "selection_rule": selection_rule,
    })

    selected_df = selected_df.merge(
        freq_df,
        left_on="selected_feature",
        right_on="feature",
        how="left",
    ).drop(columns=["feature"])

    selected_df.to_csv(
        table_dir / "072C_selected_features_final.csv",
        index=False,
    )

    print(f"[INFO] selected features: {len(selected)} by {selection_rule}")
    print(f"[INFO] bootstrap convergence warnings: {n_conv_warn}/{args.n_bootstraps}")

    save_selection_frequency_plot(
        freq_df,
        fig_dir / "072C_top_feature_selection_frequency.png",
        top_n=30,
    )

    # Train selected-feature models.
    all_metrics = []
    all_metrics.extend(full_metrics)

    selected_l2_model, selected_l2_metrics, p_test_l2 = train_evaluate_fixed_feature_model(
        model_name="stability_selected_l2",
        X_train_all=X_train_all,
        X_test_all=X_test_all,
        y_train=y_train,
        y_test=y_test,
        selected_processed_features=selected,
        cfg=cfg,
        model_type="l2",
    )
    all_metrics.extend(selected_l2_metrics)

    selected_en_model, selected_en_metrics, p_test_en = train_evaluate_fixed_feature_model(
        model_name="stability_selected_elasticnet",
        X_train_all=X_train_all,
        X_test_all=X_test_all,
        y_train=y_train,
        y_test=y_test,
        selected_processed_features=selected,
        cfg=cfg,
        model_type="elasticnet",
    )
    all_metrics.extend(selected_en_metrics)

    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.to_csv(
        table_dir / "072C_selected_feature_model_metrics.csv",
        index=False,
    )

    calibration_table(y_test, p_test_en, n_bins=10).to_csv(
        table_dir / "072C_selected_elasticnet_calibration_table.csv",
        index=False,
    )

    fpr, tpr, _ = roc_curve(y_test, p_test_en)
    precision, recall, _ = precision_recall_curve(y_test, p_test_en)

    save_curve_plot(
        fpr,
        tpr,
        "False positive rate",
        "True positive rate",
        "Test ROC - stability selected elastic-net",
        fig_dir / "072C_test_roc_selected_elasticnet.png",
    )

    save_curve_plot(
        recall,
        precision,
        "Recall",
        "Precision",
        "Test PR - stability selected elastic-net",
        fig_dir / "072C_test_pr_selected_elasticnet.png",
    )

    # Save models.
    joblib.dump(
        {
            "model": full_en_model,
            "features": processed_features,
            "prep_stats": prep_stats,
            "config": cfg,
        },
        model_dir / "072C_full_elasticnet_reference.joblib",
    )

    joblib.dump(
        {
            "model": selected_l2_model,
            "features": selected,
            "prep_stats": prep_stats,
            "config": cfg,
        },
        model_dir / "072C_stability_selected_l2.joblib",
    )

    joblib.dump(
        {
            "model": selected_en_model,
            "features": selected,
            "prep_stats": prep_stats,
            "config": cfg,
        },
        model_dir / "072C_stability_selected_elasticnet.joblib",
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
        "n_processed_features": len(processed_features),
        "n_selected_features": len(selected),
        "selection_rule": selection_rule,
        "n_bootstraps": args.n_bootstraps,
        "selection_threshold": args.selection_threshold,
        "bootstrap_convergence_warnings": n_conv_warn,
        "best_c": best_c,
        "best_l1_ratio": best_l1_ratio,
    }])

    run_summary.to_csv(
        table_dir / "072C_run_summary.csv",
        index=False,
    )

    print("[OK] 072C algorithmic feature selection complete")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()