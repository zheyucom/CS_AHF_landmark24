#!/usr/bin/env python3
"""
078A outcome/cohort definition sensitivity.

Goal: compare whether model performance and stability improve when the outcome
definition is made cleaner, the cohort removes baseline shock-like patients, or
the prediction window is shortened. This script keeps the modeling approach
fixed: top80 compact features + fixed elastic-net + Platt calibration.

Window-specific outcomes require patient-level event time after the 12 h
landmark. If --event-time-csv is not provided and the raw dataset has no such
column, the 12-36 h and 12-48 h rows are reported as unavailable instead of
being approximated from aggregate QC tables.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.append(str(PROJECT_ROOT / "src"))

from cs_ahf_ml import error_audit as audit
from cs_ahf_ml.config import load_config, project_path
from cs_ahf_ml.data import (
    build_preprocess_frame,
    drop_high_missing_and_constant,
    split_columns,
)


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


ID_COLS = ["subject_id", "hadm_id", "stay_id"]


def logit_clip(p, eps=1e-6):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p)).reshape(-1, 1)


def apply_platt(prob, calibrator):
    return calibrator.predict_proba(logit_clip(prob))[:, 1]


def make_elasticnet_fixed(seed):
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
    n_events = int(np.sum(y_train))
    n_nonevents = int(len(y_train) - n_events)
    n_splits = max(2, min(n_splits, n_events, n_nonevents))

    skf = StratifiedKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=seed,
    )
    oof_prob = np.zeros(len(y_train), dtype=float)

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train), start=1):
        model = make_elasticnet_fixed(seed + fold)
        model.fit(X_train.iloc[tr_idx], y_train.iloc[tr_idx])
        oof_prob[val_idx] = model.predict_proba(X_train.iloc[val_idx])[:, 1]

    calibrator = LogisticRegression(penalty=None, solver="lbfgs", max_iter=1000)
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
    df = pd.DataFrame({"y": np.asarray(y_true), "p": np.asarray(y_prob)})
    df = df.sort_values("p", ascending=False).reset_index(drop=True)
    n_total = len(df)
    n_events_total = int(df["y"].sum())

    rows = []
    for cutoff in cutoffs:
        k = max(1, int(np.ceil(n_total * cutoff)))
        sub = df.iloc[:k]
        rows.append({
            "top_risk_group": f"top_{int(cutoff * 100)}pct",
            "n": k,
            "events": int(sub["y"].sum()),
            "event_rate": float(sub["y"].mean()),
            "capture_rate": (
                float(sub["y"].sum() / n_events_total) if n_events_total > 0 else np.nan
            ),
            "mean_predicted_risk": float(sub["p"].mean()),
        })
    return rows


def load_feature_set(feature_sets_long, feature_set_name, processed_columns):
    sub = feature_sets_long[feature_sets_long["feature_set"] == feature_set_name]
    features = sub.sort_values("rank_in_feature_set")["feature"].tolist()
    return [f for f in features if f in processed_columns]


def detect_event_time_col(df, requested=None):
    if requested:
        if requested not in df.columns:
            raise ValueError(f"Requested event-time column not found: {requested}")
        return requested
    candidates = [
        "primary_event_hour_after_landmark",
        "event_hour_after_landmark",
        "hour_after_landmark",
        "event_time_hour",
        "event_hour",
        "event_time_since_landmark_hour",
        "hours_after_landmark",
        "time_to_event_hour",
    ]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def merge_event_time(df, event_time_csv, event_time_col):
    out = df.copy()
    detected = detect_event_time_col(
        out,
        event_time_col if event_time_csv is None else None,
    )
    if detected:
        if detected != "event_hour_after_landmark":
            out["event_hour_after_landmark"] = pd.to_numeric(out[detected], errors="coerce")
        else:
            out["event_hour_after_landmark"] = pd.to_numeric(out[detected], errors="coerce")
        return out, f"event time from raw dataset column {detected}"

    if event_time_csv is None:
        out["event_hour_after_landmark"] = np.nan
        return out, "patient-level event time unavailable"

    event_path = Path(event_time_csv)
    if not event_path.is_absolute():
        event_path = PROJECT_ROOT / event_time_csv
    event_df = pd.read_csv(event_path)
    detected = detect_event_time_col(event_df, event_time_col)
    if detected is None:
        raise ValueError("Could not detect event time column; pass --event-time-col.")
    if detected != "event_hour_after_landmark":
        event_df = event_df.rename(columns={detected: "event_hour_after_landmark"})

    merge_cols = [c for c in ID_COLS if c in out.columns and c in event_df.columns]
    if not merge_cols:
        raise ValueError("Event-time CSV needs at least one id column shared with raw dataset.")
    for col in merge_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
        event_df[col] = pd.to_numeric(event_df[col], errors="coerce").astype("Int64")
    event_df = event_df[merge_cols + ["event_hour_after_landmark"]].drop_duplicates(merge_cols)
    out = out.merge(event_df, on=merge_cols, how="left", validate="one_to_one")
    out["event_hour_after_landmark"] = pd.to_numeric(
        out["event_hour_after_landmark"], errors="coerce"
    )
    return out, f"event time merged from {event_path}"


def require_columns(df, columns, variant_name):
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{variant_name} missing columns: {missing}")


def derive_outcome_variants(df):
    require_columns(
        df,
        [
            "primary_outcome_flag",
            "label_support_escalation_flag",
            "label_nee_escalation_flag",
            "label_death_12_60_flag",
            "label_hd_nee010_flag",
            "label_hd_no_nee_flag",
            "pre12_shock_proxy_flag",
        ],
        "078A",
    )

    primary = df["primary_outcome_flag"].astype(int)
    strict_no_nee_only = df["label_hd_no_nee_flag"].astype(int)
    nee010 = df["label_hd_nee010_flag"].astype(int)
    no_pre12_shock = df["pre12_shock_proxy_flag"].fillna(0).astype(int).eq(0)
    has_event_time = df["event_hour_after_landmark"].notna()

    variants = [
        {
            "variant": "01_original_primary_12_60",
            "family": "baseline",
            "status": "available",
            "cohort_mask": pd.Series(True, index=df.index),
            "outcome": primary,
            "definition": "current primary_outcome_flag, 12-60 h",
        },
        {
            "variant": "02_original_exclude_pre12_shock_proxy",
            "family": "cohort",
            "status": "available",
            "cohort_mask": no_pre12_shock,
            "outcome": primary,
            "definition": "primary_outcome_flag after excluding pre12 shock proxy",
        },
        {
            "variant": "03_nee010_substitute_12_60",
            "family": "outcome",
            "status": "available",
            "cohort_mask": pd.Series(True, index=df.index),
            "outcome": nee010,
            "definition": "label_hd_nee010_flag; proxy for NEE >=0.10 replacing >=0.05",
        },
        {
            "variant": "04_strict_no_nee_only_12_60",
            "family": "outcome",
            "status": "available",
            "cohort_mask": pd.Series(True, index=df.index),
            "outcome": strict_no_nee_only,
            "definition": "label_hd_no_nee_flag; NEE-only events removed",
        },
        {
            "variant": "05_strict_no_nee_only_exclude_pre12_shock_proxy",
            "family": "outcome+cohort",
            "status": "available",
            "cohort_mask": no_pre12_shock,
            "outcome": strict_no_nee_only,
            "definition": "strict no-NEE-only outcome after excluding pre12 shock proxy",
        },
    ]

    window_specs = [
        ("06_original_primary_12_36", primary, 24.0, "primary_outcome_flag within 0-24 h after 12 h landmark"),
        ("07_original_primary_12_48", primary, 36.0, "primary_outcome_flag within 0-36 h after 12 h landmark"),
        (
            "08_strict_no_nee_only_12_36",
            strict_no_nee_only,
            24.0,
            "strict no-NEE-only outcome within 0-24 h after 12 h landmark",
        ),
        (
            "09_strict_no_nee_only_12_48",
            strict_no_nee_only,
            36.0,
            "strict no-NEE-only outcome within 0-36 h after 12 h landmark",
        ),
    ]

    for name, base_outcome, hour_limit, definition in window_specs:
        if has_event_time.any():
            hour = pd.to_numeric(df["event_hour_after_landmark"], errors="coerce")
            window_outcome = (base_outcome.eq(1) & hour.le(hour_limit)).astype(int)
            status = "available"
        else:
            window_outcome = pd.Series(pd.NA, index=df.index)
            status = "unavailable_event_time_missing"
        variants.append({
            "variant": name,
            "family": "window",
            "status": status,
            "cohort_mask": pd.Series(True, index=df.index),
            "outcome": window_outcome,
            "definition": definition,
        })

    return variants


def summarize_variant_counts(df, variants):
    primary = df["primary_outcome_flag"].astype(int)
    rows = []
    for spec in variants:
        mask = spec["cohort_mask"].fillna(False)
        n = int(mask.sum())
        if spec["status"] != "available":
            rows.append({
                "variant": spec["variant"],
                "family": spec["family"],
                "status": spec["status"],
                "definition": spec["definition"],
                "n": n,
                "events": np.nan,
                "event_rate": np.nan,
                "original_events_within_cohort": int(primary[mask].sum()) if n else 0,
                "events_removed_vs_original": np.nan,
                "events_added_vs_original": np.nan,
                "cohort_excluded_n": int((~mask).sum()),
            })
            continue
        y = spec["outcome"].astype(int)
        events = int(y[mask].sum())
        original_events = int(primary[mask].sum())
        removed = int(((primary.eq(1)) & (y.eq(0)) & mask).sum())
        added = int(((primary.eq(0)) & (y.eq(1)) & mask).sum())
        rows.append({
            "variant": spec["variant"],
            "family": spec["family"],
            "status": spec["status"],
            "definition": spec["definition"],
            "n": n,
            "events": events,
            "event_rate": events / n if n else np.nan,
            "original_events_within_cohort": original_events,
            "events_removed_vs_original": removed,
            "events_added_vs_original": added,
            "cohort_excluded_n": int((~mask).sum()),
        })
    return pd.DataFrame(rows)


def fit_evaluate_variant(
    df_variant,
    y,
    all_raw_features,
    feature_sets_long,
    feature_set_name,
    cfg,
    seed,
    test_size,
    calibration_folds,
):
    train_idx, test_idx = train_test_split(
        np.arange(len(df_variant)),
        test_size=test_size,
        random_state=seed,
        stratify=y,
    )

    train_df = df_variant.iloc[train_idx].reset_index(drop=True)
    test_df = df_variant.iloc[test_idx].reset_index(drop=True)
    y_train = y.iloc[train_idx].reset_index(drop=True).astype(int)
    y_test = y.iloc[test_idx].reset_index(drop=True).astype(int)

    kept_raw_features, _ = drop_high_missing_and_constant(
        train_df,
        all_raw_features,
        high_missing_threshold=cfg["preprocessing"]["high_missing_threshold"],
        unique_threshold=cfg["preprocessing"]["near_zero_variance_unique_threshold"],
    )

    X_train_all, prep_stats = build_preprocess_frame(train_df, kept_raw_features, cfg, fit_stats=None)
    X_test_all, _ = build_preprocess_frame(test_df, kept_raw_features, cfg, fit_stats=prep_stats)
    X_test_all = X_test_all.reindex(columns=X_train_all.columns, fill_value=0)

    features = load_feature_set(feature_sets_long, feature_set_name, list(X_train_all.columns))
    if not features:
        raise RuntimeError(f"No usable features for {feature_set_name}")

    X_train = X_train_all[features].copy()
    X_test = X_test_all[features].copy()

    calibrator = crossfit_platt_calibrator(
        X_train,
        y_train,
        seed=seed,
        n_splits=calibration_folds,
    )
    model = make_elasticnet_fixed(seed)
    model.fit(X_train, y_train)

    p_train = apply_platt(model.predict_proba(X_train)[:, 1], calibrator)
    p_test = apply_platt(model.predict_proba(X_test)[:, 1], calibrator)

    train_metrics = compute_metrics(y_train, p_train)
    test_metrics = compute_metrics(y_test, p_test)
    return {
        "n_train": len(train_df),
        "n_test": len(test_df),
        "n_features": len(features),
        "n_events_train": int(y_train.sum()),
        "n_events_test": int(y_test.sum()),
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
        "top_rows": top_risk_metrics(y_test, p_test),
        "model": model,
        "calibrator": calibrator,
        "features": features,
        "prep_stats": prep_stats,
    }


def plot_metric_boxplot(metrics_df, metric, fig_path):
    test_df = metrics_df[metrics_df["split"] == "test"].copy()
    variants = list(test_df["variant"].unique())
    data = [test_df.loc[test_df["variant"] == v, metric].dropna().values for v in variants]

    plt.figure(figsize=(12, 5))
    plt.boxplot(data, tick_labels=variants, showmeans=True)
    plt.xticks(rotation=35, ha="right")
    plt.ylabel(metric)
    plt.title(f"078A outcome definition sensitivity: {metric}")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=240)
    plt.close()


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def safe_markdown(df, max_rows=20):
    if df.empty:
        return "_No rows._"
    try:
        return df.head(max_rows).to_markdown(index=False)
    except ImportError:
        return "```\n" + df.head(max_rows).to_string(index=False) + "\n```"


def build_report(counts, summary, top_summary, run_summary, output_paths, event_time_note):
    available = counts[counts["status"].eq("available")].copy()
    unavailable = counts[~counts["status"].eq("available")].copy()

    summary_sorted = summary.sort_values("auroc_mean", ascending=False).copy()
    top20 = top_summary[top_summary["top_risk_group"].eq("top_20pct")].copy()
    top20 = top20.sort_values("event_rate_mean", ascending=False)

    lines = [
        "# 078A Outcome Definition Sensitivity",
        "",
        "## Event-Time Input",
        "",
        f"- {event_time_note}",
        "",
        "## Outcome/Cohort Event Counts",
        "",
        safe_markdown(counts, max_rows=30),
        "",
        "## Repeated Validation Summary",
        "",
        safe_markdown(summary_sorted, max_rows=30),
        "",
        "## Top 20% Risk Group Summary",
        "",
        safe_markdown(top20, max_rows=30),
        "",
        "## Unavailable Window Analyses",
        "",
        safe_markdown(unavailable[["variant", "status", "definition"]], max_rows=20),
        "",
        "## Interpretation",
        "",
        "- If stricter outcomes improve AUROC/AUPRC and reduce variability, outcome noise and small treatment-dose fluctuations are likely limiting performance.",
        "- If excluding pre12 shock-like patients improves stability, the current cohort contains baseline shock-like cases that blur incident deterioration.",
        "- If 12-36 h or 12-48 h windows improve after event-time export, the 12-60 h horizon is probably too long for 0-12 h predictors.",
        "- If all variants stay near the same performance, prioritize new high-value features rather than further outcome narrowing.",
        "",
        "## Output Files",
        "",
        *[f"- `{name}`: `{path}`" for name, path in output_paths.items()],
        "",
    ]
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--feature_set", default="top80_compact")
    parser.add_argument("--n_repeats", type=int, default=30)
    parser.add_argument("--test_size", type=float, default=None)
    parser.add_argument("--calibration_folds", type=int, default=3)
    parser.add_argument("--event-time-csv", default=None)
    parser.add_argument("--event-time-col", default=None)
    parser.add_argument("--min_events", type=int, default=30)
    parser.add_argument("--save_last_models", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    cfg = load_config(args.config)

    table_dir = project_path(cfg, cfg["paths"]["table_dir"])
    fig_dir = project_path(cfg, cfg["paths"]["figure_dir"])
    model_dir = project_path(cfg, cfg["paths"]["model_dir"])
    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])
    feature_sets_path = table_dir / "072D_feature_sets_long.csv"

    output_dir = table_dir / "078A_outcome_definition_sensitivity"
    output_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    if not feature_sets_path.exists():
        raise FileNotFoundError("072D_feature_sets_long.csv not found. Please run 072D first.")

    feature_sets_long = pd.read_csv(feature_sets_path)
    df_raw = pd.read_csv(raw_path)
    all_raw_features, label_col, _ = split_columns(df_raw, cfg)
    df, event_time_note = merge_event_time(df_raw, args.event_time_csv, args.event_time_col)
    df = audit.derive_audit_flags(df)
    test_size = args.test_size if args.test_size is not None else cfg["preprocessing"]["test_size"]

    variants = derive_outcome_variants(df)
    counts = summarize_variant_counts(df, variants)

    metric_rows = []
    top_rows = []
    run_rows = []
    last_model_records = []

    for spec in variants:
        if spec["status"] != "available":
            continue

        mask = spec["cohort_mask"].fillna(False)
        df_variant = df.loc[mask].reset_index(drop=True)
        y = spec["outcome"].loc[mask].reset_index(drop=True).astype(int)

        n_events = int(y.sum())
        n_nonevents = int(len(y) - n_events)
        if n_events < args.min_events or n_nonevents < args.min_events:
            run_rows.append({
                "variant": spec["variant"],
                "status": "skipped_low_event_count",
                "n": len(y),
                "events": n_events,
                "nonevents": n_nonevents,
            })
            continue

        for repeat in range(args.n_repeats):
            seed = cfg["random_seed"] + repeat
            result = fit_evaluate_variant(
                df_variant=df_variant,
                y=y,
                all_raw_features=all_raw_features,
                feature_sets_long=feature_sets_long,
                feature_set_name=args.feature_set,
                cfg=cfg,
                seed=seed,
                test_size=test_size,
                calibration_folds=args.calibration_folds,
            )

            for split, metrics in [
                ("train", result["train_metrics"]),
                ("test", result["test_metrics"]),
            ]:
                metric_rows.append({
                    "variant": spec["variant"],
                    "family": spec["family"],
                    "repeat": repeat + 1,
                    "seed": seed,
                    "split": split,
                    "n_train": result["n_train"],
                    "n_test": result["n_test"],
                    "n_features": result["n_features"],
                    "n_events_train": result["n_events_train"],
                    "n_events_test": result["n_events_test"],
                    **metrics,
                })

            for row in result["top_rows"]:
                row.update({
                    "variant": spec["variant"],
                    "family": spec["family"],
                    "repeat": repeat + 1,
                    "seed": seed,
                })
                top_rows.append(row)

            if args.save_last_models and repeat == args.n_repeats - 1:
                model_path = model_dir / f"078A_last_repeat_{spec['variant']}.joblib"
                joblib.dump({
                    "model": result["model"],
                    "calibrator": result["calibrator"],
                    "features": result["features"],
                    "prep_stats": result["prep_stats"],
                    "variant": spec,
                    "config": cfg,
                    "seed": seed,
                }, model_path)
                last_model_records.append({"variant": spec["variant"], "model_path": str(model_path)})

        run_rows.append({
            "variant": spec["variant"],
            "status": "completed",
            "n": len(y),
            "events": n_events,
            "nonevents": n_nonevents,
        })

    metrics_df = pd.DataFrame(metric_rows)
    top_df = pd.DataFrame(top_rows)
    run_df = pd.DataFrame(run_rows)

    if metrics_df.empty:
        raise RuntimeError("No outcome variants were evaluated.")

    test_metrics = metrics_df[metrics_df["split"].eq("test")].copy()
    summary = test_metrics.groupby(["variant", "family"]).agg(
        n_repeats=("repeat", "count"),
        n_features_mean=("n_features", "mean"),
        n_test_mean=("n_test", "mean"),
        n_events_test_mean=("n_events_test", "mean"),
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

    baseline = summary[summary["variant"].eq("01_original_primary_12_60")]
    if not baseline.empty:
        base = baseline.iloc[0]
        summary["delta_auroc_vs_original"] = summary["auroc_mean"] - base["auroc_mean"]
        summary["delta_auprc_vs_original"] = summary["auprc_mean"] - base["auprc_mean"]
        summary["delta_brier_vs_original"] = summary["brier_mean"] - base["brier_mean"]

    top_summary = top_df.groupby(["variant", "family", "top_risk_group"]).agg(
        n_repeats=("repeat", "count"),
        event_rate_mean=("event_rate", "mean"),
        event_rate_sd=("event_rate", "std"),
        capture_rate_mean=("capture_rate", "mean"),
        capture_rate_sd=("capture_rate", "std"),
        mean_predicted_risk_mean=("mean_predicted_risk", "mean"),
    ).reset_index()

    output_paths = {}
    outputs = {
        "variant_event_counts": counts,
        "metrics_long": metrics_df,
        "summary": summary,
        "top_risk_long": top_df,
        "top_risk_summary": top_summary,
        "run_status": run_df,
    }
    for name, frame in outputs.items():
        path = output_dir / f"078A_{name}.csv"
        write_csv(frame, path)
        output_paths[name] = path

    if last_model_records:
        path = output_dir / "078A_saved_last_models.csv"
        write_csv(pd.DataFrame(last_model_records), path)
        output_paths["saved_last_models"] = path

    for metric in ["auroc", "auprc", "brier"]:
        path = fig_dir / f"078A_outcome_definition_sensitivity_{metric}.png"
        plot_metric_boxplot(metrics_df, metric, path)
        output_paths[f"figure_{metric}"] = path

    run_summary = {
        "n_rows_raw": int(len(df)),
        "feature_set": args.feature_set,
        "n_repeats": args.n_repeats,
        "test_size": test_size,
        "calibration_folds": args.calibration_folds,
        "min_events": args.min_events,
        "event_time_note": event_time_note,
        "available_variants": int(counts["status"].eq("available").sum()),
        "evaluated_variants": int(run_df["status"].eq("completed").sum()) if not run_df.empty else 0,
    }
    meta_path = output_dir / "078A_run_summary.json"
    meta_path.write_text(json.dumps(run_summary, indent=2), encoding="utf-8")
    output_paths["run_summary_json"] = meta_path

    report = build_report(counts, summary, top_summary, run_summary, output_paths, event_time_note)
    report_path = output_dir / "078A_outcome_definition_sensitivity_report.md"
    report_path.write_text(report, encoding="utf-8")
    output_paths["report"] = report_path

    print("[OK] 078A outcome definition sensitivity complete")
    print(f"Output directory: {output_dir}")
    print(f"Report: {report_path}")
    print(summary.sort_values("auroc_mean", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
