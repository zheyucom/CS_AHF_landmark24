import argparse
from pathlib import Path
import sys
import warnings
import joblib

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
)
from sklearn.exceptions import ConvergenceWarning

from cs_ahf_ml.config import load_config, project_path
from cs_ahf_ml.data import split_columns, drop_high_missing_and_constant


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=ConvergenceWarning)


def logit_clip(p, eps=1e-6):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p)).reshape(-1, 1)


def apply_platt(prob, calibrator):
    return calibrator.predict_proba(logit_clip(prob))[:, 1]


def is_missingness_feature(col):
    return col.endswith("__missing") or col.endswith("_available_flag")


def is_nee_or_drug_dose_col(col):
    drug_prefixes = (
        "nee_",
        "norepinephrine_",
        "epinephrine_",
        "dopamine_",
        "phenylephrine_",
        "vasopressin_",
        "dobutamine_",
        "milrinone_",
    )

    if col.startswith(drug_prefixes) and (
        col.endswith("_max") or col.endswith("_last") or col.endswith("_mean") or col.endswith("_min")
    ):
        return True

    if col.startswith("nee_"):
        return True

    return False


def build_preprocess_frame_variant(
    df,
    feature_cols,
    cfg,
    fit_stats=None,
    keep_missing_indicators=True,
    nee_missing_fill_zero=True,
    remove_missingness_features=False,
):
    """
    Variant preprocessing for missing-data sensitivity analysis.

    All fit parameters are learned from the training set when fit_stats is None.
    The same parameters are then reused for test data.
    """
    X = df[feature_cols].copy()
    stats = {} if fit_stats is None else fit_stats.copy()

    # Convert all selected columns to numeric if possible.
    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors="coerce")

    # Structural missingness: no vasoactive/NEE record often means no exposure.
    # In current strategy, these missing values are filled with 0 before missing indicators.
    if nee_missing_fill_zero:
        for c in X.columns:
            if is_nee_or_drug_dose_col(c):
                X[c] = X[c].fillna(0)

    # Missing indicators.
    if keep_missing_indicators:
        indicator_frames = []
        for c in list(X.columns):
            if X[c].isna().any():
                indicator_frames.append(
                    pd.Series(X[c].isna().astype(int), name=f"{c}__missing")
                )

        if indicator_frames:
            X = pd.concat([X] + indicator_frames, axis=1)

    # Winsorization using training-set thresholds.
    if cfg["preprocessing"]["winsorize"]["enabled"]:
        lq = cfg["preprocessing"]["winsorize"]["lower_q"]
        uq = cfg["preprocessing"]["winsorize"]["upper_q"]

        for c in X.columns:
            if not pd.api.types.is_numeric_dtype(X[c]):
                continue

            key = f"winsor::{c}"

            if fit_stats is None:
                lo, hi = X[c].quantile([lq, uq])
                stats[key] = (
                    float(lo) if pd.notna(lo) else np.nan,
                    float(hi) if pd.notna(hi) else np.nan,
                )
            else:
                lo, hi = stats.get(key, (np.nan, np.nan))

            if pd.notna(lo) and pd.notna(hi):
                X[c] = X[c].clip(lo, hi)

    # Median imputation using training-set medians.
    for c in X.columns:
        if not pd.api.types.is_numeric_dtype(X[c]):
            continue

        key = f"median::{c}"

        if fit_stats is None:
            med = X[c].median()
            stats[key] = float(med) if pd.notna(med) else 0.0
        else:
            med = stats.get(key, 0.0)

        X[c] = X[c].fillna(med)

    if remove_missingness_features:
        keep_cols = [c for c in X.columns if not is_missingness_feature(c)]
        X = X[keep_cols].copy()

    return X, stats


def make_elasticnet_fixed(seed):
    """
    Fixed elastic-net setting from previous best stable model.
    C=0.02 approximates the value selected in 072C.
    """
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            penalty="elasticnet",
            solver="saga",
            C=0.02,
            l1_ratio=0.5,
            class_weight="balanced",
            max_iter=30000,
            tol=1e-3,
            random_state=seed,
        )),
    ])


def crossfit_platt_calibrator(X_train, y_train, seed, n_splits=3):
    skf = StratifiedKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=seed,
    )

    oof_prob = np.zeros(len(y_train), dtype=float)

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train), start=1):
        X_tr = X_train.iloc[tr_idx]
        y_tr = y_train.iloc[tr_idx]
        X_val = X_train.iloc[val_idx]

        model = make_elasticnet_fixed(seed + fold)
        model.fit(X_tr, y_tr)

        oof_prob[val_idx] = model.predict_proba(X_val)[:, 1]

    calibrator = LogisticRegression(
        penalty=None,
        solver="lbfgs",
        max_iter=1000,
    )
    calibrator.fit(logit_clip(oof_prob), y_train)

    return calibrator


def compute_metrics(y_true, y_prob):
    return {
        "auroc": roc_auc_score(y_true, y_prob),
        "auprc": average_precision_score(y_true, y_prob),
        "brier": brier_score_loss(y_true, y_prob),
        "event_rate": float(np.mean(y_true)),
    }


def top_risk_metrics(y_true, y_prob, cutoffs=(0.10, 0.20, 0.30)):
    df = pd.DataFrame({
        "y": np.asarray(y_true),
        "p": np.asarray(y_prob),
    }).sort_values("p", ascending=False).reset_index(drop=True)

    n_total = len(df)
    n_events_total = df["y"].sum()

    rows = []

    for cutoff in cutoffs:
        k = max(1, int(np.ceil(n_total * cutoff)))
        sub = df.iloc[:k]

        rows.append({
            "top_risk_group": f"top_{int(cutoff * 100)}pct",
            "n": k,
            "events": int(sub["y"].sum()),
            "event_rate": float(sub["y"].mean()),
            "capture_rate": float(sub["y"].sum() / n_events_total) if n_events_total > 0 else np.nan,
            "mean_predicted_risk": float(sub["p"].mean()),
        })

    return rows


def load_feature_set(feature_sets_long, feature_set_name, processed_columns):
    sub = feature_sets_long[feature_sets_long["feature_set"] == feature_set_name]
    features = sub.sort_values("rank_in_feature_set")["feature"].tolist()
    features = [f for f in features if f in processed_columns]
    return features


def plot_metric_boxplot(metrics_df, metric, fig_path):
    models = list(metrics_df["strategy"].unique())
    data = [metrics_df.loc[metrics_df["strategy"] == m, metric].dropna().values for m in models]

    plt.figure(figsize=(10, 5))
    plt.boxplot(data, labels=models, showmeans=True)
    plt.xticks(rotation=30, ha="right")
    plt.ylabel(metric)
    plt.title(f"075B missing data sensitivity: {metric}")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=240)
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--n_repeats", type=int, default=20)
    parser.add_argument("--calibration_folds", type=int, default=3)
    parser.add_argument("--test_size", type=float, default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)

    table_dir = project_path(cfg, cfg["paths"]["table_dir"])
    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])
    feature_sets_path = table_dir / "072D_feature_sets_long.csv"
    fig_dir = project_path(cfg, cfg["paths"]["figure_dir"])
    model_dir = project_path(cfg, cfg["paths"]["model_dir"])

    for d in [table_dir, fig_dir, model_dir]:
        d.mkdir(parents=True, exist_ok=True)

    if not feature_sets_path.exists():
        raise FileNotFoundError("072D_feature_sets_long.csv not found. Please run 072D first.")

    df = pd.read_csv(raw_path)
    feature_sets_long = pd.read_csv(feature_sets_path)

    all_raw_features, label_col, exclude_cols = split_columns(df, cfg)
    y_all = df[label_col].astype(int)

    test_size = args.test_size
    if test_size is None:
        test_size = cfg["preprocessing"]["test_size"]

    strategies = [
        {
            "strategy": "current_strategy",
            "keep_missing_indicators": True,
            "nee_missing_fill_zero": True,
            "remove_missingness_features": False,
            "low_missing30": False,
        },
        {
            "strategy": "no_generated_missing_indicators",
            "keep_missing_indicators": False,
            "nee_missing_fill_zero": True,
            "remove_missingness_features": False,
            "low_missing30": False,
        },
        {
            "strategy": "no_missingness_features",
            "keep_missing_indicators": False,
            "nee_missing_fill_zero": True,
            "remove_missingness_features": True,
            "low_missing30": False,
        },
        {
            "strategy": "low_missing30_current",
            "keep_missing_indicators": True,
            "nee_missing_fill_zero": True,
            "remove_missingness_features": False,
            "low_missing30": True,
        },
        {
            "strategy": "nee_median_instead_of_zero",
            "keep_missing_indicators": True,
            "nee_missing_fill_zero": False,
            "remove_missingness_features": False,
            "low_missing30": False,
        },
    ]

    metric_rows = []
    top_rows = []
    split_rows = []

    for r in range(args.n_repeats):
        seed = cfg["random_seed"] + r

        print(f"\n[REPEAT] {r + 1}/{args.n_repeats}, seed={seed}")

        train_idx, test_idx = train_test_split(
            np.arange(len(df)),
            test_size=test_size,
            random_state=seed,
            stratify=y_all,
        )

        train_df = df.iloc[train_idx].reset_index(drop=True)
        test_df = df.iloc[test_idx].reset_index(drop=True)

        y_train = train_df[label_col].astype(int)
        y_test = test_df[label_col].astype(int)

        base_kept_raw_features, raw_feature_qc = drop_high_missing_and_constant(
            train_df,
            all_raw_features,
            high_missing_threshold=cfg["preprocessing"]["high_missing_threshold"],
            unique_threshold=cfg["preprocessing"]["near_zero_variance_unique_threshold"],
        )

        for s in strategies:
            strategy_name = s["strategy"]

            kept_raw_features = list(base_kept_raw_features)

            if s["low_missing30"]:
                kept_raw_features = [
                    c for c in kept_raw_features
                    if train_df[c].isna().mean() <= 0.30
                ]

            X_train_all, prep_stats = build_preprocess_frame_variant(
                train_df,
                kept_raw_features,
                cfg,
                fit_stats=None,
                keep_missing_indicators=s["keep_missing_indicators"],
                nee_missing_fill_zero=s["nee_missing_fill_zero"],
                remove_missingness_features=s["remove_missingness_features"],
            )

            X_test_all, _ = build_preprocess_frame_variant(
                test_df,
                kept_raw_features,
                cfg,
                fit_stats=prep_stats,
                keep_missing_indicators=s["keep_missing_indicators"],
                nee_missing_fill_zero=s["nee_missing_fill_zero"],
                remove_missingness_features=s["remove_missingness_features"],
            )

            X_test_all = X_test_all.reindex(columns=X_train_all.columns, fill_value=0)
            processed_columns = list(X_train_all.columns)

            selected_features = load_feature_set(
                feature_sets_long,
                "top80_compact",
                processed_columns,
            )

            if s["remove_missingness_features"]:
                selected_features = [
                    f for f in selected_features
                    if not is_missingness_feature(f)
                ]

            selected_features = [f for f in selected_features if f in processed_columns]

            if len(selected_features) < 5:
                print(f"  [SKIP] {strategy_name}: only {len(selected_features)} features available")
                continue

            X_train = X_train_all[selected_features].copy()
            X_test = X_test_all[selected_features].copy()

            print(f"  [RUN] {strategy_name}: {len(selected_features)} features")

            calibrator = crossfit_platt_calibrator(
                X_train,
                y_train,
                seed=seed,
                n_splits=args.calibration_folds,
            )

            model = make_elasticnet_fixed(seed)
            model.fit(X_train, y_train)

            p_train_raw = model.predict_proba(X_train)[:, 1]
            p_test_raw = model.predict_proba(X_test)[:, 1]

            p_train = apply_platt(p_train_raw, calibrator)
            p_test = apply_platt(p_test_raw, calibrator)

            train_metrics = compute_metrics(y_train, p_train)
            test_metrics = compute_metrics(y_test, p_test)

            metric_rows.append({
                "repeat": r + 1,
                "seed": seed,
                "strategy": strategy_name,
                "split": "train",
                "n_train": len(train_df),
                "n_test": len(test_df),
                "n_features": len(selected_features),
                "n_events_train": int(y_train.sum()),
                "n_events_test": int(y_test.sum()),
                **train_metrics,
            })

            metric_rows.append({
                "repeat": r + 1,
                "seed": seed,
                "strategy": strategy_name,
                "split": "test",
                "n_train": len(train_df),
                "n_test": len(test_df),
                "n_features": len(selected_features),
                "n_events_train": int(y_train.sum()),
                "n_events_test": int(y_test.sum()),
                **test_metrics,
            })

            for row in top_risk_metrics(y_test, p_test):
                row.update({
                    "repeat": r + 1,
                    "seed": seed,
                    "strategy": strategy_name,
                })
                top_rows.append(row)

            if r == args.n_repeats - 1:
                joblib.dump(
                    {
                        "model": model,
                        "calibrator": calibrator,
                        "features": selected_features,
                        "prep_stats": prep_stats,
                        "strategy": strategy_name,
                        "config": cfg,
                        "seed": seed,
                    },
                    model_dir / f"075B_last_repeat_{strategy_name}.joblib",
                )

        split_rows.append({
            "repeat": r + 1,
            "seed": seed,
            "n_train": len(train_df),
            "n_test": len(test_df),
            "n_events_train": int(y_train.sum()),
            "n_events_test": int(y_test.sum()),
            "event_rate_train": float(y_train.mean()),
            "event_rate_test": float(y_test.mean()),
        })

    metrics_df = pd.DataFrame(metric_rows)
    top_df = pd.DataFrame(top_rows)
    split_df = pd.DataFrame(split_rows)

    metrics_df.to_csv(
        table_dir / "075B_missing_data_sensitivity_metrics_long.csv",
        index=False,
    )

    top_df.to_csv(
        table_dir / "075B_missing_data_sensitivity_top_risk_long.csv",
        index=False,
    )

    split_df.to_csv(
        table_dir / "075B_missing_data_sensitivity_splits.csv",
        index=False,
    )

    test_metrics = metrics_df[metrics_df["split"] == "test"].copy()

    summary = test_metrics.groupby("strategy").agg(
        n_repeats=("repeat", "count"),
        n_features_mean=("n_features", "mean"),
        auroc_mean=("auroc", "mean"),
        auroc_sd=("auroc", "std"),
        auroc_median=("auroc", "median"),
        auprc_mean=("auprc", "mean"),
        auprc_sd=("auprc", "std"),
        auprc_median=("auprc", "median"),
        brier_mean=("brier", "mean"),
        brier_sd=("brier", "std"),
        brier_median=("brier", "median"),
        event_rate_mean=("event_rate", "mean"),
    ).reset_index()

    summary.to_csv(
        table_dir / "075B_missing_data_sensitivity_summary.csv",
        index=False,
    )

    top_summary = top_df.groupby(["strategy", "top_risk_group"]).agg(
        n_repeats=("repeat", "count"),
        event_rate_mean=("event_rate", "mean"),
        event_rate_sd=("event_rate", "std"),
        capture_rate_mean=("capture_rate", "mean"),
        capture_rate_sd=("capture_rate", "std"),
        mean_predicted_risk_mean=("mean_predicted_risk", "mean"),
    ).reset_index()

    top_summary.to_csv(
        table_dir / "075B_missing_data_sensitivity_top_risk_summary.csv",
        index=False,
    )

    plot_metric_boxplot(
        test_metrics,
        "auroc",
        fig_dir / "075B_missing_data_sensitivity_auroc_boxplot.png",
    )

    plot_metric_boxplot(
        test_metrics,
        "auprc",
        fig_dir / "075B_missing_data_sensitivity_auprc_boxplot.png",
    )

    plot_metric_boxplot(
        test_metrics,
        "brier",
        fig_dir / "075B_missing_data_sensitivity_brier_boxplot.png",
    )

    top20 = top_df[top_df["top_risk_group"] == "top_20pct"].copy()
    top20 = top20.rename(columns={"event_rate": "top20_event_rate"})

    plot_metric_boxplot(
        top20,
        "top20_event_rate",
        fig_dir / "075B_missing_data_sensitivity_top20_event_rate_boxplot.png",
    )

    run_summary = pd.DataFrame([{
        "n_rows": len(df),
        "n_repeats": args.n_repeats,
        "test_size": test_size,
        "calibration_folds": args.calibration_folds,
        "base_feature_set": "top80_compact",
        "model": "fixed_elasticnet_platt",
        "strategies": ",".join([s["strategy"] for s in strategies]),
    }])

    run_summary.to_csv(
        table_dir / "075B_missing_data_sensitivity_run_summary.csv",
        index=False,
    )

    print("\n[OK] 075B missing data sensitivity complete")
    print(summary.sort_values("auroc_mean", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
