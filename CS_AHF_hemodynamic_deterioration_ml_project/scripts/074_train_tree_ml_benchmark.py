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
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    roc_curve,
    precision_recall_curve,
)
from sklearn.utils.class_weight import compute_sample_weight

from cs_ahf_ml.config import load_config, project_path
from cs_ahf_ml.data import (
    split_columns,
    drop_high_missing_and_constant,
    build_preprocess_frame,
)
from cs_ahf_ml.metrics import binary_metrics, calibration_table


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)


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


def make_model_factory(model_name, random_seed):
    """
    Return a callable that creates an unfitted model.
    """
    if model_name == "random_forest":
        return lambda: RandomForestClassifier(
            n_estimators=600,
            max_depth=5,
            min_samples_leaf=20,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=random_seed,
        )

    if model_name == "hist_gradient_boosting":
        return lambda: HistGradientBoostingClassifier(
            learning_rate=0.03,
            max_iter=300,
            max_leaf_nodes=15,
            min_samples_leaf=30,
            l2_regularization=0.1,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=random_seed,
        )

    if model_name == "lightgbm":
        LGBMClassifier = try_import_lightgbm()
        if LGBMClassifier is None:
            return None

        return lambda: LGBMClassifier(
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

    raise ValueError(f"Unknown model name: {model_name}")


def fit_model(model, X, y, model_name):
    """
    Fit model. Use sample_weight for HistGradientBoosting because it does not
    always support class_weight depending on sklearn version.
    """
    if model_name == "hist_gradient_boosting":
        sample_weight = compute_sample_weight(class_weight="balanced", y=y)
        model.fit(X, y, sample_weight=sample_weight)
    else:
        model.fit(X, y)

    return model


def crossfit_platt_calibration(
    X_train,
    y_train,
    model_name,
    random_seed,
    n_splits=5,
):
    """
    Cross-fitted Platt calibration:
    - OOF predictions are generated only from training data.
    - Calibrator is fitted using OOF predictions.
    """
    skf = StratifiedKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=random_seed,
    )

    oof_prob = np.zeros(len(y_train), dtype=float)

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train), start=1):
        factory = make_model_factory(model_name, random_seed + fold)

        if factory is None:
            raise RuntimeError("LightGBM is not installed.")

        model = factory()

        X_tr = X_train.iloc[tr_idx]
        y_tr = y_train.iloc[tr_idx]
        X_val = X_train.iloc[val_idx]

        model = fit_model(model, X_tr, y_tr, model_name)
        oof_prob[val_idx] = model.predict_proba(X_val)[:, 1]

        print(f"    calibration fold {fold}/{n_splits} complete")

    calibrator = LogisticRegression(
        penalty=None,
        solver="lbfgs",
        max_iter=1000,
    )
    calibrator.fit(logit_clip(oof_prob), y_train)

    return calibrator, oof_prob


def risk_decile_table(y_true, y_prob, model_name):
    df = pd.DataFrame({
        "y": np.asarray(y_true),
        "p": np.asarray(y_prob),
    }).sort_values("p", ascending=False).reset_index(drop=True)

    df["risk_decile"] = pd.qcut(
        df.index + 1,
        q=10,
        labels=[f"D{i}" for i in range(10, 0, -1)]
    )

    out = df.groupby("risk_decile", observed=True).agg(
        n=("y", "size"),
        events=("y", "sum"),
        observed_event_rate=("y", "mean"),
        mean_predicted_risk=("p", "mean"),
        min_predicted_risk=("p", "min"),
        max_predicted_risk=("p", "max"),
    ).reset_index()

    out.insert(0, "model", model_name)
    return out


def top_risk_table(y_true, y_prob, model_name, cutoffs=(0.05, 0.10, 0.20, 0.30)):
    df = pd.DataFrame({
        "y": np.asarray(y_true),
        "p": np.asarray(y_prob),
    }).sort_values("p", ascending=False).reset_index(drop=True)

    rows = []
    n_total = len(df)
    n_events_total = int(df["y"].sum())

    for cutoff in cutoffs:
        k = max(1, int(np.ceil(n_total * cutoff)))
        sub = df.iloc[:k]

        rows.append({
            "model": model_name,
            "top_risk_group": f"top_{int(cutoff * 100)}pct",
            "n": k,
            "events": int(sub["y"].sum()),
            "event_rate": sub["y"].mean(),
            "capture_rate_of_all_events": sub["y"].sum() / n_events_total if n_events_total > 0 else np.nan,
            "mean_predicted_risk": sub["p"].mean(),
            "min_predicted_risk": sub["p"].min(),
            "max_predicted_risk": sub["p"].max(),
        })

    return pd.DataFrame(rows)


def decision_curve_table(y_true, y_prob, model_name, thresholds=None):
    if thresholds is None:
        thresholds = np.arange(0.02, 0.41, 0.01)

    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)

    n = len(y_true)
    prevalence = y_true.mean()

    rows = []

    for pt in thresholds:
        pred = y_prob >= pt

        tp = np.sum((pred == 1) & (y_true == 1))
        fp = np.sum((pred == 1) & (y_true == 0))

        nb_model = (tp / n) - (fp / n) * (pt / (1 - pt))
        nb_all = prevalence - (1 - prevalence) * (pt / (1 - pt))

        rows.append({
            "model": model_name,
            "threshold": pt,
            "net_benefit_model": nb_model,
            "net_benefit_all": nb_all,
            "net_benefit_none": 0.0,
        })

    return pd.DataFrame(rows)


def bootstrap_metric_ci(y_true, y_prob, n_bootstrap=500, seed=2026):
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    n = len(y_true)

    rows = []

    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        y_b = y_true[idx]
        p_b = y_prob[idx]

        if len(np.unique(y_b)) < 2:
            continue

        rows.append({
            "auroc": roc_auc_score(y_b, p_b),
            "auprc": average_precision_score(y_b, p_b),
            "brier": brier_score_loss(y_b, p_b),
        })

    boot = pd.DataFrame(rows)

    out = {}
    for metric in ["auroc", "auprc", "brier"]:
        out[f"{metric}_ci_low"] = boot[metric].quantile(0.025)
        out[f"{metric}_ci_high"] = boot[metric].quantile(0.975)

    out["n_bootstrap_valid"] = len(boot)
    return out


def plot_roc_pr(all_predictions, fig_dir):
    plt.figure(figsize=(6, 5))

    for item in all_predictions:
        fpr, tpr, _ = roc_curve(item["y_test"], item["p_test"])
        auc = roc_auc_score(item["y_test"], item["p_test"])
        plt.plot(fpr, tpr, label=f"{item['model']} AUROC={auc:.3f}")

    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("074 Tree ML Benchmark ROC")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(fig_dir / "074_tree_benchmark_roc.png", dpi=240)
    plt.close()

    plt.figure(figsize=(6, 5))

    for item in all_predictions:
        precision, recall, _ = precision_recall_curve(item["y_test"], item["p_test"])
        ap = average_precision_score(item["y_test"], item["p_test"])
        plt.plot(recall, precision, label=f"{item['model']} AUPRC={ap:.3f}")

    baseline = np.mean(all_predictions[0]["y_test"])
    plt.axhline(baseline, linestyle="--", label=f"baseline={baseline:.3f}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("074 Tree ML Benchmark PR Curve")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(fig_dir / "074_tree_benchmark_pr.png", dpi=240)
    plt.close()


def plot_calibration(all_predictions, fig_dir, table_dir):
    plt.figure(figsize=(6, 5))
    all_cal = []

    for item in all_predictions:
        cal = calibration_table(item["y_test"], item["p_test"], n_bins=10)
        cal.insert(0, "model", item["model"])
        all_cal.append(cal)

        plt.plot(
            cal["mean_pred"],
            cal["obs_rate"],
            marker="o",
            label=item["model"],
        )

    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.xlabel("Mean predicted risk")
    plt.ylabel("Observed event rate")
    plt.title("074 Tree ML Benchmark Calibration")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(fig_dir / "074_tree_benchmark_calibration.png", dpi=240)
    plt.close()

    pd.concat(all_cal, ignore_index=True).to_csv(
        table_dir / "074_tree_benchmark_calibration_table.csv",
        index=False,
    )


def plot_decision_curve(dca_df, fig_dir):
    plt.figure(figsize=(7, 5))

    for model in dca_df["model"].unique():
        sub = dca_df[dca_df["model"] == model]
        plt.plot(
            sub["threshold"],
            sub["net_benefit_model"],
            label=model,
        )

    first = dca_df[dca_df["model"] == dca_df["model"].iloc[0]]

    plt.plot(
        first["threshold"],
        first["net_benefit_all"],
        linestyle="--",
        label="Treat all",
    )
    plt.plot(
        first["threshold"],
        first["net_benefit_none"],
        linestyle="--",
        label="Treat none",
    )

    plt.xlabel("Risk threshold")
    plt.ylabel("Net benefit")
    plt.title("074 Tree ML Benchmark Decision Curve")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(fig_dir / "074_tree_benchmark_decision_curve.png", dpi=240)
    plt.close()


def load_feature_sets(feature_sets_long, processed_columns):
    feature_sets = {}

    for fs in [
        "top50_compact",
        "top80_compact",
        "portable_top50_compact",
    ]:
        sub = feature_sets_long[feature_sets_long["feature_set"] == fs]
        features = sub.sort_values("rank_in_feature_set")["feature"].tolist()
        features = [f for f in features if f in processed_columns]
        feature_sets[fs] = features

    return feature_sets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--calibration_folds", type=int, default=5)
    parser.add_argument("--n_bootstrap_ci", type=int, default=500)
    parser.add_argument(
        "--include_lightgbm",
        action="store_true",
        help="Run LightGBM if installed.",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])
    table_dir = project_path(cfg, cfg["paths"]["table_dir"])
    feature_sets_path = table_dir / "072D_feature_sets_long.csv"

    model_dir = project_path(cfg, cfg["paths"]["model_dir"])
    fig_dir = project_path(cfg, cfg["paths"]["figure_dir"])

    for d in [model_dir, fig_dir, table_dir]:
        d.mkdir(parents=True, exist_ok=True)

    if not feature_sets_path.exists():
        raise FileNotFoundError(
            f"{feature_sets_path} not found. Please run 072D first."
        )

    df = pd.read_csv(raw_path)
    feature_sets_long = pd.read_csv(feature_sets_path)

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

    feature_sets = load_feature_sets(feature_sets_long, processed_columns)

    model_names = [
        "random_forest",
        "hist_gradient_boosting",
    ]

    if args.include_lightgbm:
        if try_import_lightgbm() is not None:
            model_names.append("lightgbm")
        else:
            print("[WARN] lightgbm is not installed. Skipping LightGBM.")

    all_predictions = []
    metrics_rows = []
    decile_rows = []
    top_rows = []
    dca_rows = []
    feature_importance_rows = []
    model_summary_rows = []

    for fs_name, features in feature_sets.items():
        X_train = X_train_all[features].copy()
        X_test = X_test_all[features].copy()

        for model_name in model_names:
            run_name = f"{fs_name}_{model_name}_platt"
            print(f"[RUN] {run_name}: {len(features)} features")

            calibrator, oof_prob = crossfit_platt_calibration(
                X_train=X_train,
                y_train=y_train,
                model_name=model_name,
                random_seed=cfg["random_seed"],
                n_splits=args.calibration_folds,
            )

            factory = make_model_factory(model_name, cfg["random_seed"])
            model = factory()

            model = fit_model(model, X_train, y_train, model_name)

            p_train_raw = model.predict_proba(X_train)[:, 1]
            p_test_raw = model.predict_proba(X_test)[:, 1]

            p_train_cal = apply_platt(p_train_raw, calibrator)
            p_test_cal = apply_platt(p_test_raw, calibrator)

            train_metrics = {
                "model": run_name,
                "feature_set": fs_name,
                "model_type": model_name,
                "split": "train_calibrated",
                "n_features": len(features),
                **binary_metrics(y_train, p_train_cal),
            }

            test_metrics = {
                "model": run_name,
                "feature_set": fs_name,
                "model_type": model_name,
                "split": "test_calibrated",
                "n_features": len(features),
                **binary_metrics(y_test, p_test_cal),
            }

            ci = bootstrap_metric_ci(
                y_test,
                p_test_cal,
                n_bootstrap=args.n_bootstrap_ci,
                seed=cfg["random_seed"],
            )
            test_metrics.update(ci)

            metrics_rows.append(train_metrics)
            metrics_rows.append(test_metrics)

            all_predictions.append({
                "model": run_name,
                "y_test": y_test,
                "p_test": p_test_cal,
            })

            decile_rows.append(
                risk_decile_table(y_test, p_test_cal, run_name)
            )

            top_rows.append(
                top_risk_table(y_test, p_test_cal, run_name)
            )

            dca_rows.append(
                decision_curve_table(y_test, p_test_cal, run_name)
            )

            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
                for f, imp in zip(features, importances):
                    feature_importance_rows.append({
                        "model": run_name,
                        "feature": f,
                        "importance": imp,
                    })

            model_summary_rows.append({
                "model": run_name,
                "feature_set": fs_name,
                "model_type": model_name,
                "n_features": len(features),
            })

            joblib.dump(
                {
                    "model": model,
                    "calibrator": calibrator,
                    "features": features,
                    "prep_stats": prep_stats,
                    "config": cfg,
                },
                model_dir / f"074_{run_name}.joblib",
            )

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(
        table_dir / "074_tree_benchmark_metrics.csv",
        index=False,
    )

    pd.DataFrame(model_summary_rows).to_csv(
        table_dir / "074_tree_benchmark_model_summary.csv",
        index=False,
    )

    if feature_importance_rows:
        pd.DataFrame(feature_importance_rows).sort_values(
            ["model", "importance"],
            ascending=[True, False],
        ).to_csv(
            table_dir / "074_tree_benchmark_feature_importance.csv",
            index=False,
        )

    pd.concat(decile_rows, ignore_index=True).to_csv(
        table_dir / "074_tree_benchmark_risk_deciles.csv",
        index=False,
    )

    pd.concat(top_rows, ignore_index=True).to_csv(
        table_dir / "074_tree_benchmark_top_risk_groups.csv",
        index=False,
    )

    dca_df = pd.concat(dca_rows, ignore_index=True)
    dca_df.to_csv(
        table_dir / "074_tree_benchmark_decision_curve.csv",
        index=False,
    )

    plot_roc_pr(all_predictions, fig_dir)
    plot_calibration(all_predictions, fig_dir, table_dir)
    plot_decision_curve(dca_df, fig_dir)

    run_summary = pd.DataFrame([{
        "n_rows": len(df),
        "n_train": len(train_df),
        "n_test": len(test_df),
        "n_events_train": int(y_train.sum()),
        "n_events_test": int(y_test.sum()),
        "feature_sets": ",".join(feature_sets.keys()),
        "model_names": ",".join(model_names),
        "calibration_method": "crossfit_platt_scaling",
        "calibration_folds": args.calibration_folds,
        "n_bootstrap_ci": args.n_bootstrap_ci,
    }])

    run_summary.to_csv(
        table_dir / "074_tree_benchmark_run_summary.csv",
        index=False,
    )

    print("[OK] 074 tree ML benchmark complete")
    print(metrics_df[metrics_df["split"] == "test_calibrated"].sort_values(
        ["auroc", "auprc"],
        ascending=False,
    ).to_string(index=False))


if __name__ == "__main__":
    main()
