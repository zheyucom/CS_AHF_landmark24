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
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    roc_curve,
    precision_recall_curve,
)
from sklearn.exceptions import ConvergenceWarning

from cs_ahf_ml.config import load_config, project_path
from cs_ahf_ml.data import (
    split_columns,
    drop_high_missing_and_constant,
    build_preprocess_frame,
)
from cs_ahf_ml.metrics import binary_metrics, calibration_table


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)


def logit_clip(p, eps=1e-6):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p)).reshape(-1, 1)


def make_elasticnet_model(cfg):
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


def make_unweighted_elasticnet_model(cfg):
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
            class_weight=None,
            n_jobs=-1,
            random_state=cfg["random_seed"],
        )),
    ])


def crossfit_platt_calibrator(X_train, y_train, cfg, base_weighted=True, n_splits=5):
    """
    Fit Platt calibration model using out-of-fold predictions from training data only.
    Then later fit final base model on full training set.
    """
    skf = StratifiedKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=cfg["random_seed"],
    )

    oof_prob = np.zeros(len(y_train))

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train), start=1):
        X_tr = X_train.iloc[tr_idx]
        y_tr = y_train.iloc[tr_idx]
        X_val = X_train.iloc[val_idx]

        base_model = make_elasticnet_model(cfg) if base_weighted else make_unweighted_elasticnet_model(cfg)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ConvergenceWarning)
            base_model.fit(X_tr, y_tr)

        oof_prob[val_idx] = base_model.predict_proba(X_val)[:, 1]
        print(f"    calibration fold {fold}/{n_splits} complete")

    calibrator = LogisticRegression(
        penalty=None,
        solver="lbfgs",
        max_iter=1000,
    )
    calibrator.fit(logit_clip(oof_prob), y_train)

    return calibrator, oof_prob


def apply_calibrator(prob, calibrator):
    return calibrator.predict_proba(logit_clip(prob))[:, 1]


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
    plt.title("073B Calibration after Platt scaling")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(fig_dir / "073B_calibrated_models_calibration.png", dpi=240)
    plt.close()

    pd.concat(all_cal, ignore_index=True).to_csv(
        table_dir / "073B_calibrated_models_calibration_table.csv",
        index=False,
    )


def plot_roc_pr(all_predictions, fig_dir):
    plt.figure(figsize=(6, 5))
    for item in all_predictions:
        fpr, tpr, _ = roc_curve(item["y_test"], item["p_test"])
        auc = roc_auc_score(item["y_test"], item["p_test"])
        plt.plot(fpr, tpr, label=f"{item['model']} AUROC={auc:.3f}")

    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("073B Calibrated Models ROC")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(fig_dir / "073B_calibrated_models_roc.png", dpi=240)
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
    plt.title("073B Calibrated Models PR Curve")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(fig_dir / "073B_calibrated_models_pr.png", dpi=240)
    plt.close()


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
    plt.plot(first["threshold"], first["net_benefit_all"], linestyle="--", label="Treat all")
    plt.plot(first["threshold"], first["net_benefit_none"], linestyle="--", label="Treat none")

    plt.xlabel("Risk threshold")
    plt.ylabel("Net benefit")
    plt.title("073B Decision Curve after calibration")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(fig_dir / "073B_calibrated_models_decision_curve.png", dpi=240)
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--calibration_folds", type=int, default=5)
    args = parser.parse_args()

    cfg = load_config(args.config)

    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])

    model_dir = project_path(cfg, cfg["paths"]["model_dir"])
    fig_dir = project_path(cfg, cfg["paths"]["figure_dir"])
    table_dir = project_path(cfg, cfg["paths"]["table_dir"])
    feature_sets_path = table_dir / "072D_feature_sets_long.csv"

    for d in [model_dir, fig_dir, table_dir]:
        d.mkdir(parents=True, exist_ok=True)

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

    candidate_feature_sets = {}

    for fs in [
        "top50_compact",
        "top80_compact",
        "portable_top50_compact",
    ]:
        sub = feature_sets_long[feature_sets_long["feature_set"] == fs]
        features = sub.sort_values("rank_in_feature_set")["feature"].tolist()
        features = [f for f in features if f in processed_columns]
        candidate_feature_sets[fs] = features

    all_predictions = []
    metrics_rows = []
    decile_rows = []
    top_rows = []
    dca_rows = []

    for fs_name, features in candidate_feature_sets.items():
        for weighted in [True, False]:
            weight_name = "weighted" if weighted else "unweighted"
            model_name = f"{fs_name}_{weight_name}_platt"

            print(f"[RUN] {model_name}: {len(features)} features")

            X_train = X_train_all[features].copy()
            X_test = X_test_all[features].copy()

            calibrator, oof_prob = crossfit_platt_calibrator(
                X_train,
                y_train,
                cfg,
                base_weighted=weighted,
                n_splits=args.calibration_folds,
            )

            base_model = make_elasticnet_model(cfg) if weighted else make_unweighted_elasticnet_model(cfg)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=ConvergenceWarning)
                base_model.fit(X_train, y_train)

            p_train_raw = base_model.predict_proba(X_train)[:, 1]
            p_test_raw = base_model.predict_proba(X_test)[:, 1]

            p_train_cal = apply_calibrator(p_train_raw, calibrator)
            p_test_cal = apply_calibrator(p_test_raw, calibrator)

            metrics_rows.append({
                "model": model_name,
                "split": "train_calibrated",
                "n_features": len(features),
                **binary_metrics(y_train, p_train_cal),
            })

            metrics_rows.append({
                "model": model_name,
                "split": "test_calibrated",
                "n_features": len(features),
                **binary_metrics(y_test, p_test_cal),
            })

            all_predictions.append({
                "model": model_name,
                "y_test": y_test,
                "p_test": p_test_cal,
            })

            decile_rows.append(
                risk_decile_table(y_test, p_test_cal, model_name)
            )

            top_rows.append(
                top_risk_table(y_test, p_test_cal, model_name)
            )

            dca_rows.append(
                decision_curve_table(y_test, p_test_cal, model_name)
            )

            joblib.dump(
                {
                    "base_model": base_model,
                    "calibrator": calibrator,
                    "features": features,
                    "prep_stats": prep_stats,
                    "weighted": weighted,
                    "config": cfg,
                },
                model_dir / f"073B_{model_name}.joblib",
            )

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(
        table_dir / "073B_calibrated_model_metrics.csv",
        index=False,
    )

    pd.concat(decile_rows, ignore_index=True).to_csv(
        table_dir / "073B_calibrated_model_risk_deciles.csv",
        index=False,
    )

    pd.concat(top_rows, ignore_index=True).to_csv(
        table_dir / "073B_calibrated_model_top_risk_groups.csv",
        index=False,
    )

    dca_df = pd.concat(dca_rows, ignore_index=True)
    dca_df.to_csv(
        table_dir / "073B_calibrated_model_decision_curve.csv",
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
        "candidate_feature_sets": ",".join(candidate_feature_sets.keys()),
        "calibration_method": "crossfit_platt_scaling",
        "calibration_folds": args.calibration_folds,
    }])

    run_summary.to_csv(
        table_dir / "073B_run_summary.csv",
        index=False,
    )

    print("[OK] 073B calibration complete")
    print(metrics_df[metrics_df["split"] == "test_calibrated"].sort_values(
        ["brier", "auroc"],
        ascending=[True, False],
    ).to_string(index=False))


if __name__ == "__main__":
    main()
    
