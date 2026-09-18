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
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
)
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.exceptions import ConvergenceWarning

from cs_ahf_ml.config import load_config, project_path
from cs_ahf_ml.data import (
    split_columns,
    drop_high_missing_and_constant,
    build_preprocess_frame,
)


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=ConvergenceWarning)


def try_import_lightgbm():
    try:
        from lightgbm import LGBMClassifier
        return LGBMClassifier
    except Exception:
        return None


def logit_clip(p, eps=1e-6):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p)).reshape(-1, 1)


def apply_platt(prob, calibrator):
    return calibrator.predict_proba(logit_clip(prob))[:, 1]


def make_model(model_type, random_seed):
    if model_type == "elasticnet_fixed":
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
                random_state=random_seed,
            )),
        ])

    if model_type == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            learning_rate=0.03,
            max_iter=300,
            max_leaf_nodes=15,
            min_samples_leaf=30,
            l2_regularization=0.1,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=random_seed,
        )

    if model_type == "lightgbm":
        LGBMClassifier = try_import_lightgbm()
        if LGBMClassifier is None:
            raise RuntimeError("lightgbm is not installed.")

        return LGBMClassifier(
            n_estimators=500,
            learning_rate=0.03,
            num_leaves=15,
            max_depth=4,
            min_child_samples=30,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            class_weight="balanced",
            random_state=random_seed,
            n_jobs=-1,
            verbose=-1,
        )

    raise ValueError(f"Unknown model_type: {model_type}")


def fit_model(model, X, y, model_type):
    if model_type == "hist_gradient_boosting":
        sample_weight = compute_sample_weight(class_weight="balanced", y=y)
        model.fit(X, y, sample_weight=sample_weight)
    else:
        model.fit(X, y)
    return model


def crossfit_platt_calibrator(X_train, y_train, model_type, seed, n_splits=3):
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

        model = make_model(model_type, seed + fold)
        model = fit_model(model, X_tr, y_tr, model_type)

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
    test_df = metrics_df.copy()
    models = list(test_df["model"].unique())
    data = [test_df.loc[test_df["model"] == m, metric].dropna().values for m in models]

    plt.figure(figsize=(9, 5))
    plt.boxplot(data, labels=models, showmeans=True)
    plt.xticks(rotation=30, ha="right")
    plt.ylabel(metric)
    plt.title(f"075 repeated internal validation: {metric}")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=240)
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--n_repeats", type=int, default=20)
    parser.add_argument("--test_size", type=float, default=None)
    parser.add_argument("--calibration_folds", type=int, default=3)
    parser.add_argument("--include_lightgbm", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)

    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])

    table_dir = project_path(cfg, cfg["paths"]["table_dir"])
    fig_dir = project_path(cfg, cfg["paths"]["figure_dir"])
    model_dir = project_path(cfg, cfg["paths"]["model_dir"])
    feature_sets_path = table_dir / "072D_feature_sets_long.csv"

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

    model_specs = [
        {
            "model": "top80_elasticnet_platt",
            "feature_set": "top80_compact",
            "model_type": "elasticnet_fixed",
        },
        {
            "model": "top50_histgb_platt",
            "feature_set": "top50_compact",
            "model_type": "hist_gradient_boosting",
        },
        {
            "model": "portable_top50_histgb_platt",
            "feature_set": "portable_top50_compact",
            "model_type": "hist_gradient_boosting",
        },
    ]

    if args.include_lightgbm:
        if try_import_lightgbm() is not None:
            model_specs.append({
                "model": "top80_lightgbm_platt",
                "feature_set": "top80_compact",
                "model_type": "lightgbm",
            })
        else:
            print("[WARN] lightgbm not installed. Skipping top80_lightgbm_platt.")

    metric_rows = []
    top_rows = []
    run_rows = []

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

        for spec in model_specs:
            model_label = spec["model"]
            feature_set_name = spec["feature_set"]
            model_type = spec["model_type"]

            features = load_feature_set(
                feature_sets_long,
                feature_set_name,
                processed_columns,
            )

            X_train = X_train_all[features].copy()
            X_test = X_test_all[features].copy()

            print(f"  [RUN] {model_label}: {len(features)} features")

            calibrator = crossfit_platt_calibrator(
                X_train,
                y_train,
                model_type=model_type,
                seed=seed,
                n_splits=args.calibration_folds,
            )

            model = make_model(model_type, seed)
            model = fit_model(model, X_train, y_train, model_type)

            p_train_raw = model.predict_proba(X_train)[:, 1]
            p_test_raw = model.predict_proba(X_test)[:, 1]

            p_train = apply_platt(p_train_raw, calibrator)
            p_test = apply_platt(p_test_raw, calibrator)

            train_metrics = compute_metrics(y_train, p_train)
            test_metrics = compute_metrics(y_test, p_test)

            metric_rows.append({
                "repeat": r + 1,
                "seed": seed,
                "model": model_label,
                "split": "train",
                "n_train": len(train_df),
                "n_test": len(test_df),
                "n_features": len(features),
                "n_events_train": int(y_train.sum()),
                "n_events_test": int(y_test.sum()),
                **train_metrics,
            })

            metric_rows.append({
                "repeat": r + 1,
                "seed": seed,
                "model": model_label,
                "split": "test",
                "n_train": len(train_df),
                "n_test": len(test_df),
                "n_features": len(features),
                "n_events_train": int(y_train.sum()),
                "n_events_test": int(y_test.sum()),
                **test_metrics,
            })

            for row in top_risk_metrics(y_test, p_test):
                row.update({
                    "repeat": r + 1,
                    "seed": seed,
                    "model": model_label,
                })
                top_rows.append(row)

            # Save only last repeat model files to avoid huge outputs.
            if r == args.n_repeats - 1:
                joblib.dump(
                    {
                        "model": model,
                        "calibrator": calibrator,
                        "features": features,
                        "prep_stats": prep_stats,
                        "config": cfg,
                        "seed": seed,
                    },
                    model_dir / f"075_last_repeat_{model_label}.joblib",
                )

        run_rows.append({
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
    run_df = pd.DataFrame(run_rows)

    metrics_df.to_csv(
        table_dir / "075_repeated_validation_metrics_long.csv",
        index=False,
    )

    top_df.to_csv(
        table_dir / "075_repeated_validation_top_risk_long.csv",
        index=False,
    )

    run_df.to_csv(
        table_dir / "075_repeated_validation_splits.csv",
        index=False,
    )

    test_metrics = metrics_df[metrics_df["split"] == "test"].copy()

    summary = test_metrics.groupby("model").agg(
        n_repeats=("repeat", "count"),
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
        table_dir / "075_repeated_validation_summary.csv",
        index=False,
    )

    top_summary = top_df.groupby(["model", "top_risk_group"]).agg(
        n_repeats=("repeat", "count"),
        event_rate_mean=("event_rate", "mean"),
        event_rate_sd=("event_rate", "std"),
        capture_rate_mean=("capture_rate", "mean"),
        capture_rate_sd=("capture_rate", "std"),
        mean_predicted_risk_mean=("mean_predicted_risk", "mean"),
    ).reset_index()

    top_summary.to_csv(
        table_dir / "075_repeated_validation_top_risk_summary.csv",
        index=False,
    )

    plot_metric_boxplot(
        test_metrics,
        "auroc",
        fig_dir / "075_repeated_validation_auroc_boxplot.png",
    )

    plot_metric_boxplot(
        test_metrics,
        "auprc",
        fig_dir / "075_repeated_validation_auprc_boxplot.png",
    )

    plot_metric_boxplot(
        test_metrics,
        "brier",
        fig_dir / "075_repeated_validation_brier_boxplot.png",
    )

    top20 = top_df[top_df["top_risk_group"] == "top_20pct"].copy()
    plot_metric_boxplot(
        top20.rename(columns={"event_rate": "top20_event_rate"}),
        "top20_event_rate",
        fig_dir / "075_repeated_validation_top20_event_rate_boxplot.png",
    )

    run_summary = pd.DataFrame([{
        "n_rows": len(df),
        "n_repeats": args.n_repeats,
        "test_size": test_size,
        "calibration_folds": args.calibration_folds,
        "include_lightgbm": args.include_lightgbm,
        "models": ",".join([m["model"] for m in model_specs]),
    }])

    run_summary.to_csv(
        table_dir / "075_repeated_validation_run_summary.csv",
        index=False,
    )

    print("\n[OK] 075 repeated internal validation complete")
    print(summary.sort_values("auroc_mean", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
