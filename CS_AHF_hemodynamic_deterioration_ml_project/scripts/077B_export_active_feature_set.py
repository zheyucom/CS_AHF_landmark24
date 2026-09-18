import argparse
from pathlib import Path
import sys
import warnings
import joblib

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

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


def make_model(seed):
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

        model = make_model(seed + fold)
        model.fit(X_tr, y_tr)

        oof_prob[val_idx] = model.predict_proba(X_val)[:, 1]

    calibrator = LogisticRegression(
        penalty=None,
        solver="lbfgs",
        max_iter=1000,
    )
    calibrator.fit(logit_clip(oof_prob), y_train)

    return calibrator


def binary_metrics(y_true, y_prob):
    return {
        "auroc": roc_auc_score(y_true, y_prob),
        "auprc": average_precision_score(y_true, y_prob),
        "brier": brier_score_loss(y_true, y_prob),
        "event_rate": float(np.mean(y_true)),
    }


def top_risk_table(y_true, y_prob, model_name, cutoffs=(0.05, 0.10, 0.20, 0.30)):
    df = pd.DataFrame({
        "y": np.asarray(y_true),
        "p": np.asarray(y_prob),
    }).sort_values("p", ascending=False).reset_index(drop=True)

    n_total = len(df)
    n_events_total = int(df["y"].sum())

    rows = []

    for cutoff in cutoffs:
        k = max(1, int(np.ceil(n_total * cutoff)))
        sub = df.iloc[:k]

        rows.append({
            "model": model_name,
            "top_risk_group": f"top_{int(cutoff * 100)}pct",
            "n": k,
            "events": int(sub["y"].sum()),
            "event_rate": float(sub["y"].mean()),
            "capture_rate": float(sub["y"].sum() / n_events_total) if n_events_total > 0 else np.nan,
            "mean_predicted_risk": float(sub["p"].mean()),
            "min_predicted_risk": float(sub["p"].min()),
            "max_predicted_risk": float(sub["p"].max()),
        })

    return pd.DataFrame(rows)


def evaluate_feature_set(
    model_name,
    features,
    X_train_all,
    X_test_all,
    y_train,
    y_test,
    seed,
    calibration_folds,
):
    X_train = X_train_all[features].copy()
    X_test = X_test_all[features].copy()

    calibrator = crossfit_platt_calibrator(
        X_train,
        y_train,
        seed=seed,
        n_splits=calibration_folds,
    )

    model = make_model(seed)
    model.fit(X_train, y_train)

    p_train_raw = model.predict_proba(X_train)[:, 1]
    p_test_raw = model.predict_proba(X_test)[:, 1]

    p_train = apply_platt(p_train_raw, calibrator)
    p_test = apply_platt(p_test_raw, calibrator)

    rows = [
        {
            "model": model_name,
            "split": "train",
            "n_features": len(features),
            **binary_metrics(y_train, p_train),
        },
        {
            "model": model_name,
            "split": "test",
            "n_features": len(features),
            **binary_metrics(y_test, p_test),
        },
    ]

    coef = model.named_steps["clf"].coef_.ravel()

    coef_df = pd.DataFrame({
        "model": model_name,
        "model_feature": features,
        "standardized_coef_refit": coef,
        "abs_standardized_coef_refit": np.abs(coef),
        "direction_refit": np.where(
            coef > 0,
            "higher value -> higher predicted risk",
            np.where(coef < 0, "higher value -> lower predicted risk", "zero"),
        ),
    }).sort_values("abs_standardized_coef_refit", ascending=False)

    top_df = top_risk_table(y_test, p_test, model_name)

    return model, calibrator, pd.DataFrame(rows), coef_df, top_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--coef_threshold", type=float, default=1e-8)
    parser.add_argument("--calibration_folds", type=int, default=3)
    args = parser.parse_args()

    cfg = load_config(args.config)

    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])

    table_dir = project_path(cfg, cfg["paths"]["table_dir"])
    model_dir = project_path(cfg, cfg["paths"]["model_dir"])

    for d in [table_dir, model_dir]:
        d.mkdir(parents=True, exist_ok=True)

    feature_dict_path = table_dir / "077_final_model_feature_dictionary.csv"
    coef_path = table_dir / "077_final_model_coefficients.csv"
    mapping_path = table_dir / "077_external_validation_variable_mapping_template.csv"

    if not feature_dict_path.exists():
        raise FileNotFoundError("077_final_model_feature_dictionary.csv not found. Run 077 first.")
    if not coef_path.exists():
        raise FileNotFoundError("077_final_model_coefficients.csv not found. Run 077 first.")
    if not mapping_path.exists():
        raise FileNotFoundError("077_external_validation_variable_mapping_template.csv not found. Run 077 first.")

    feature_dict = pd.read_csv(feature_dict_path)
    coef_077 = pd.read_csv(coef_path)
    mapping = pd.read_csv(mapping_path)

    all_features = feature_dict.sort_values("feature_rank_in_top80")["model_feature"].tolist()

    active_coef = coef_077[
        coef_077["abs_standardized_coef"] > args.coef_threshold
    ].copy()

    zero_coef = coef_077[
        coef_077["abs_standardized_coef"] <= args.coef_threshold
    ].copy()

    active_features = active_coef["model_feature"].tolist()

    active_feature_dict = feature_dict[
        feature_dict["model_feature"].isin(active_features)
    ].copy()

    active_feature_dict["active_feature_rank"] = active_feature_dict["model_feature"].map(
        {f: i + 1 for i, f in enumerate(active_features)}
    )

    active_feature_dict = active_feature_dict.sort_values("active_feature_rank")

    active_mapping = mapping[
        mapping["model_feature"].isin(active_features)
    ].copy()

    active_mapping["active_feature_rank"] = active_mapping["model_feature"].map(
        {f: i + 1 for i, f in enumerate(active_features)}
    )

    active_mapping = active_mapping.sort_values("active_feature_rank")

    active_feature_dict.to_csv(
        table_dir / "077B_active_feature_dictionary.csv",
        index=False,
    )

    active_coef.to_csv(
        table_dir / "077B_active_feature_coefficients_from_077.csv",
        index=False,
    )

    zero_coef.to_csv(
        table_dir / "077B_zero_coefficient_features_from_077.csv",
        index=False,
    )

    active_mapping.to_csv(
        table_dir / "077B_active_external_validation_mapping_template.csv",
        index=False,
    )

    active_module_summary = active_feature_dict.groupby("module").agg(
        n_active_features=("model_feature", "count"),
        n_treatment_support=("is_treatment_support_feature", "sum"),
        n_portability_sensitive=("is_portability_sensitive_feature", "sum"),
        n_missing_indicators=("is_missing_indicator", "sum"),
        n_available_flags=("is_available_flag", "sum"),
    ).reset_index().sort_values("n_active_features", ascending=False)

    active_module_summary.to_csv(
        table_dir / "077B_active_feature_modules_summary.csv",
        index=False,
    )

    # Same-split check for the selected set and its non-zero subset.
    df = pd.read_csv(raw_path)
    all_raw_features, label_col, exclude_cols = split_columns(df, cfg)
    y_all = df[label_col].astype(int)

    train_idx, test_idx = train_test_split(
        np.arange(len(df)),
        test_size=cfg["preprocessing"]["test_size"],
        random_state=cfg["random_seed"],
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

    all_features_present = [f for f in all_features if f in X_train_all.columns]
    active_features_present = [f for f in active_features if f in X_train_all.columns]

    model_all, cal_all, metrics_all, coef_all_refit, top_all = evaluate_feature_set(
        model_name=f"top80_all_{len(all_features_present)}_features_refit",
        features=all_features_present,
        X_train_all=X_train_all,
        X_test_all=X_test_all,
        y_train=y_train,
        y_test=y_test,
        seed=cfg["random_seed"],
        calibration_folds=args.calibration_folds,
    )

    model_active, cal_active, metrics_active, coef_active_refit, top_active = evaluate_feature_set(
        model_name=f"active_{len(active_features_present)}_features_refit",
        features=active_features_present,
        X_train_all=X_train_all,
        X_test_all=X_test_all,
        y_train=y_train,
        y_test=y_test,
        seed=cfg["random_seed"],
        calibration_folds=args.calibration_folds,
    )

    metrics_df = pd.concat([metrics_all, metrics_active], ignore_index=True)
    coef_refit_df = pd.concat([coef_all_refit, coef_active_refit], ignore_index=True)
    top_df = pd.concat([top_all, top_active], ignore_index=True)

    metrics_df.to_csv(
        table_dir / "077B_active_feature_model_metrics.csv",
        index=False,
    )

    coef_refit_df.to_csv(
        table_dir / "077B_active_feature_refit_coefficients.csv",
        index=False,
    )

    top_df.to_csv(
        table_dir / "077B_active_feature_top_risk_groups.csv",
        index=False,
    )

    summary = pd.DataFrame([{
        "n_total_top80_compact_features": len(all_features),
        "n_active_nonzero_features": len(active_features),
        "n_zero_coefficient_features": len(zero_coef),
        "coef_threshold": args.coef_threshold,
        "calibration_folds": args.calibration_folds,
        "note": "Active features are defined as non-zero standardized coefficients from the 077 fixed train/test split model. Refit performance is a same-split check, not repeated validation.",
    }])

    summary.to_csv(
        table_dir / "077B_active_feature_summary.csv",
        index=False,
    )

    joblib.dump(
        {
            "model": model_active,
            "calibrator": cal_active,
            "features": active_features_present,
            "prep_stats": prep_stats,
            "config": cfg,
        },
        model_dir / f"077B_active_{len(active_features_present)}_feature_elasticnet_platt.joblib",
    )

    print("[OK] 077B active feature export complete")
    print(f"[OK] all features: {len(all_features)}")
    print(f"[OK] active features: {len(active_features)}")
    print(f"[OK] zero coefficient features: {len(zero_coef)}")
    print("[OK] performance check:")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
    
