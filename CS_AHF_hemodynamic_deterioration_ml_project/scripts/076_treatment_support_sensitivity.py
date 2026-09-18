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
from cs_ahf_ml.data import (
    split_columns,
    drop_high_missing_and_constant,
    build_preprocess_frame,
)


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=ConvergenceWarning)


def logit_clip(p, eps=1e-6):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p)).reshape(-1, 1)


def apply_platt(prob, calibrator):
    return calibrator.predict_proba(logit_clip(prob))[:, 1]


def normalize_feature_name(col):
    """
    Remove generated missing suffix so that treatment-support variables and their
    missing indicators are handled together.
    """
    if col.endswith("__missing"):
        return col.replace("__missing", "")
    return col


def is_nee_feature(col):
    base = normalize_feature_name(col)
    return base.startswith("nee_")


def is_individual_vaso_inotrope_feature(col):
    base = normalize_feature_name(col)

    prefixes = (
        "norepinephrine_",
        "epinephrine_",
        "dopamine_",
        "phenylephrine_",
        "vasopressin_",
        "dobutamine_",
        "milrinone_",
    )

    return base.startswith(prefixes)


def is_vaso_inotrope_summary_feature(col):
    base = normalize_feature_name(col)

    exact_or_prefixes = (
        "vaso_records_",
        "vasoactive_agent_count_",
        "vasopressor_any_",
        "inotrope_any_",
        "nee_available_",
    )

    return base.startswith(exact_or_prefixes)


def is_any_vaso_inotrope_nee_feature(col):
    return (
        is_nee_feature(col)
        or is_individual_vaso_inotrope_feature(col)
        or is_vaso_inotrope_summary_feature(col)
    )


def is_dose_like_feature(col):
    """
    Dose/intensity variables are closest to the outcome component involving
    NEE increase or support escalation.
    """
    base = normalize_feature_name(col)

    if base.startswith("nee_"):
        return True

    if is_individual_vaso_inotrope_feature(base):
        dose_suffixes = (
            "_max",
            "_min",
            "_mean",
            "_last",
        )
        return base.endswith(dose_suffixes)

    if base.startswith("vasoactive_agent_count_"):
        return True

    return False


def is_individual_agent_flag(col):
    base = normalize_feature_name(col)

    if not is_individual_vaso_inotrope_feature(base):
        return False

    return base.endswith("_flag")


def is_broad_exposure_flag(col):
    base = normalize_feature_name(col)
    return base in {
        "vasopressor_any_0_12h_flag",
        "inotrope_any_0_12h_flag",
    }


def filter_features_by_strategy(features, strategy):
    """
    Sensitivity strategies:

    current_top80:
      Original top80 compact feature set.

    no_nee:
      Remove NEE variables only.

    no_dose_keep_exposure:
      Remove NEE and dose/intensity variables, but keep agent exposure flags.

    broad_exposure_only:
      Keep only broad vasopressor_any / inotrope_any flags and remove all
      individual agent flags, doses, NEE, records, and agent count.

    no_vaso_inotrope_nee:
      Remove all early vasoactive/inotrope/NEE variables.
    """
    out = []

    for f in features:
        remove = False

        if strategy == "current_top80":
            remove = False

        elif strategy == "no_nee":
            remove = is_nee_feature(f)

        elif strategy == "no_dose_keep_exposure":
            remove = is_dose_like_feature(f)

        elif strategy == "broad_exposure_only":
            if is_any_vaso_inotrope_nee_feature(f) and not is_broad_exposure_flag(f):
                remove = True

        elif strategy == "no_vaso_inotrope_nee":
            remove = is_any_vaso_inotrope_nee_feature(f)

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        if not remove:
            out.append(f)

    return out


def make_elasticnet_fixed(seed):
    """
    Fixed elastic-net setting used in repeated validation.
    C=0.02 approximates the stable value selected earlier.
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
    plt.title(f"076 treatment-support sensitivity: {metric}")
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
        "current_top80",
        "no_nee",
        "no_dose_keep_exposure",
        "broad_exposure_only",
        "no_vaso_inotrope_nee",
    ]

    metric_rows = []
    top_rows = []
    split_rows = []
    feature_rows = []

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

        top80_features = load_feature_set(
            feature_sets_long,
            "top80_compact",
            processed_columns,
        )

        for strategy in strategies:
            selected_features = filter_features_by_strategy(
                top80_features,
                strategy,
            )

            selected_features = [f for f in selected_features if f in processed_columns]

            if len(selected_features) < 5:
                print(f"  [SKIP] {strategy}: only {len(selected_features)} features available")
                continue

            X_train = X_train_all[selected_features].copy()
            X_test = X_test_all[selected_features].copy()

            print(f"  [RUN] {strategy}: {len(selected_features)} features")

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
                "strategy": strategy,
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
                "strategy": strategy,
                "split": "test",
                "n_train": len(train_df),
                "n_test": len(test_df),
                "n_features": len(selected_features),
                "n_events_train": int(y_train.sum()),
                "n_events_test": int(y_test.sum()),
                **test_metrics,
            })

            for rank, f in enumerate(selected_features, start=1):
                feature_rows.append({
                    "repeat": r + 1,
                    "seed": seed,
                    "strategy": strategy,
                    "rank": rank,
                    "feature": f,
                    "is_vaso_inotrope_nee": is_any_vaso_inotrope_nee_feature(f),
                    "is_nee": is_nee_feature(f),
                    "is_dose_like": is_dose_like_feature(f),
                    "is_individual_agent_flag": is_individual_agent_flag(f),
                    "is_broad_exposure_flag": is_broad_exposure_flag(f),
                })

            for row in top_risk_metrics(y_test, p_test):
                row.update({
                    "repeat": r + 1,
                    "seed": seed,
                    "strategy": strategy,
                })
                top_rows.append(row)

            if r == args.n_repeats - 1:
                joblib.dump(
                    {
                        "model": model,
                        "calibrator": calibrator,
                        "features": selected_features,
                        "prep_stats": prep_stats,
                        "strategy": strategy,
                        "config": cfg,
                        "seed": seed,
                    },
                    model_dir / f"076_last_repeat_{strategy}.joblib",
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
    feature_df = pd.DataFrame(feature_rows)

    metrics_df.to_csv(
        table_dir / "076_treatment_support_sensitivity_metrics_long.csv",
        index=False,
    )

    top_df.to_csv(
        table_dir / "076_treatment_support_sensitivity_top_risk_long.csv",
        index=False,
    )

    split_df.to_csv(
        table_dir / "076_treatment_support_sensitivity_splits.csv",
        index=False,
    )

    feature_df.to_csv(
        table_dir / "076_treatment_support_sensitivity_features_long.csv",
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
        table_dir / "076_treatment_support_sensitivity_summary.csv",
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
        table_dir / "076_treatment_support_sensitivity_top_risk_summary.csv",
        index=False,
    )

    plot_metric_boxplot(
        test_metrics,
        "auroc",
        fig_dir / "076_treatment_support_sensitivity_auroc_boxplot.png",
    )

    plot_metric_boxplot(
        test_metrics,
        "auprc",
        fig_dir / "076_treatment_support_sensitivity_auprc_boxplot.png",
    )

    plot_metric_boxplot(
        test_metrics,
        "brier",
        fig_dir / "076_treatment_support_sensitivity_brier_boxplot.png",
    )

    top20 = top_df[top_df["top_risk_group"] == "top_20pct"].copy()
    top20 = top20.rename(columns={"event_rate": "top20_event_rate"})

    plot_metric_boxplot(
        top20,
        "top20_event_rate",
        fig_dir / "076_treatment_support_sensitivity_top20_event_rate_boxplot.png",
    )

    run_summary = pd.DataFrame([{
        "n_rows": len(df),
        "n_repeats": args.n_repeats,
        "test_size": test_size,
        "calibration_folds": args.calibration_folds,
        "base_feature_set": "top80_compact",
        "model": "fixed_elasticnet_platt",
        "strategies": ",".join(strategies),
    }])

    run_summary.to_csv(
        table_dir / "076_treatment_support_sensitivity_run_summary.csv",
        index=False,
    )

    print("\n[OK] 076 treatment-support sensitivity complete")
    print(summary.sort_values("auroc_mean", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
