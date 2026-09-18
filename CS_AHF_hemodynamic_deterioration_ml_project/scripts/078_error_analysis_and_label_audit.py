#!/usr/bin/env python3
"""
078 patient-level error analysis and label-quality audit.

Default behavior scores the fixed 077 final top80 elastic-net + Platt model on
the reproduced fixed test split, then audits false positives, false negatives,
true positives, and true negatives. No new model is trained in the default path.

Reusable audit table/report functions live in src/cs_ahf_ml/error_audit.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.append(str(PROJECT_ROOT / "src"))

from cs_ahf_ml import error_audit as audit
from cs_ahf_ml.config import load_config, project_path
from cs_ahf_ml.data import build_preprocess_frame, split_columns

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)


def logit_clip(p, eps=1e-6):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p)).reshape(-1, 1)


def apply_platt(prob, calibrator):
    return calibrator.predict_proba(logit_clip(prob))[:, 1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument(
        "--model-joblib",
        default=None,
        help="Saved final-model bundle used for scoring when --prediction-csv is not supplied.",
    )
    parser.add_argument(
        "--analysis-split",
        choices=["test", "train", "all"],
        default="test",
        help="Which fixed 077 split to audit. Default is held-out test.",
    )
    parser.add_argument(
        "--prediction-csv",
        default=None,
        help="Optional patient-level prediction CSV. If supplied, model scoring is skipped.",
    )
    parser.add_argument("--prediction-col", default=None)
    parser.add_argument("--event-time-csv", default=None)
    parser.add_argument("--event-time-col", default=None)
    parser.add_argument(
        "--high-risk-top-fraction",
        type=float,
        default=0.20,
        help="High risk is the top fraction by predicted risk unless --risk-threshold is supplied.",
    )
    parser.add_argument("--risk-threshold", type=float, default=None)
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument(
        "--output-dir",
        default=None,
    )
    return parser.parse_args()


def fixed_split_indices(df: pd.DataFrame, cfg: dict) -> tuple[np.ndarray, np.ndarray]:
    label_col = cfg["target"]["label_col"]
    y_all = df[label_col].astype(int)
    return train_test_split(
        np.arange(len(df)),
        test_size=cfg["preprocessing"]["test_size"],
        random_state=cfg["random_seed"],
        stratify=y_all,
    )


def select_analysis_rows(df: pd.DataFrame, cfg: dict, split_name: str) -> pd.DataFrame:
    if split_name == "all":
        out = df.copy()
        out["analysis_split"] = "all"
        out["source_row_index"] = np.arange(len(out))
        return out

    train_idx, test_idx = fixed_split_indices(df, cfg)
    idx = train_idx if split_name == "train" else test_idx
    out = df.iloc[idx].copy()
    out["analysis_split"] = split_name
    out["source_row_index"] = idx
    return out.reset_index(drop=True)


def score_saved_model(df_full: pd.DataFrame, df_score: pd.DataFrame, cfg: dict, model_path: Path) -> pd.DataFrame:
    if not model_path.exists():
        raise FileNotFoundError(f"Model bundle not found: {model_path}")

    bundle = joblib.load(model_path)
    model = bundle["model"]
    calibrator = bundle["calibrator"]
    features = bundle["features"]
    prep_stats = bundle["prep_stats"]

    all_raw_features, label_col, _ = split_columns(df_full, cfg)
    X_all, _ = build_preprocess_frame(
        df_score,
        all_raw_features,
        cfg,
        fit_stats=prep_stats,
    )
    X = X_all.reindex(columns=features, fill_value=0)
    p_raw = model.predict_proba(X)[:, 1]
    p = apply_platt(p_raw, calibrator)

    pred_cols = [c for c in ["subject_id", "hadm_id", "stay_id", "analysis_split", "source_row_index"] if c in df_score.columns]
    pred = df_score[pred_cols].copy()
    pred["risk_score"] = p
    pred["risk_score_raw_uncalibrated"] = p_raw
    pred["model_source"] = model_path.name
    return pred


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def run() -> int:
    args = parse_args()

    cfg = load_config(args.config)
    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])
    model_path = (
        project_path(cfg, args.model_joblib)
        if args.model_joblib
        else project_path(cfg, cfg["paths"]["model_dir"])
        / "077_final_top80_elasticnet_platt_train_split.joblib"
    )
    output_dir = (
        project_path(cfg, args.output_dir)
        if args.output_dir
        else project_path(cfg, cfg["paths"]["table_dir"])
        / "078_error_analysis_and_label_audit"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    df_full = pd.read_csv(raw_path)
    df_score = select_analysis_rows(df_full, cfg, args.analysis_split)

    if args.prediction_csv:
        pred_path = Path(args.prediction_csv)
        if not pred_path.is_absolute():
            pred_path = project_path(cfg, args.prediction_csv)
        pred_df = pd.read_csv(pred_path)
        pred_col = audit.detect_prediction_col(pred_df, args.prediction_col)
        risk_input = audit.RiskInput(
            frame=pred_df,
            score_col=pred_col,
            source=str(pred_path),
            note=f"Risk score column from supplied prediction CSV: {pred_col}",
        )
    else:
        pred_df = score_saved_model(df_full, df_score, cfg, model_path)
        pred_path = output_dir / f"078_{args.analysis_split}_split_final_model_predictions.csv"
        write_csv(pred_df, pred_path)
        risk_input = audit.RiskInput(
            frame=pred_df,
            score_col="risk_score",
            source=str(model_path),
            note=(
                f"Scored saved 077 final top80 elastic-net Platt model on "
                f"fixed {args.analysis_split} split; no model was trained."
            ),
        )

    event_time_csv = None
    if args.event_time_csv:
        event_time_csv = Path(args.event_time_csv)
        if not event_time_csv.is_absolute():
            event_time_csv = project_path(cfg, args.event_time_csv)

    merged = audit.merge_prediction_scores(df_score, risk_input)
    merged, event_time_note = audit.merge_event_time(
        merged,
        event_time_csv=event_time_csv,
        event_time_col=args.event_time_col,
    )

    if args.risk_threshold is not None:
        threshold = args.risk_threshold
    else:
        if not (0 < args.high_risk_top_fraction < 1):
            raise ValueError("--high-risk-top-fraction must be between 0 and 1.")
        threshold = float(
            audit.safe_numeric(merged["risk_score"]).quantile(1.0 - args.high_risk_top_fraction)
        )

    audited = audit.derive_audit_flags(merged)
    audited["event_type"] = audit.derive_event_type(audited)
    audited = audit.assign_error_groups(audited, threshold)

    confusion = audit.summarize_confusion(audited)
    event_types = audit.summarize_event_types(audited)
    component_summary = audit.summarize_components(audited)
    continuous_summary = audit.summarize_continuous(audited, audit.KEY_CONTINUOUS_COLS)
    binary_summary = audit.summarize_binary(audited, audit.KEY_BINARY_COLS)
    event_time_summary = audit.summarize_event_time(audited)
    risk_deciles = audit.summarize_risk_deciles(audited)
    label_candidates, label_noise_summary = audit.label_noise_candidates(audited)

    patient_cols = [col for col in audit.PATIENT_LIST_COLS if col in audited.columns]
    if "analysis_split" in audited.columns:
        patient_cols = [*patient_cols, "analysis_split", "source_row_index"]
    patient_list = audit.select_existing(
        audited.sort_values(["error_group", "risk_score"], ascending=[True, False]),
        patient_cols,
    )

    outputs: dict[str, Path] = {}
    outputs["model_predictions"] = pred_path
    outputs["patient_list_all"] = output_dir / "078_patient_list_all_with_error_group.csv"
    write_csv(patient_list, outputs["patient_list_all"])

    for group in ["false_positive", "false_negative", "true_positive", "true_negative"]:
        path = output_dir / f"078_patient_list_{group}.csv"
        write_csv(audit.select_existing(audited[audited["error_group"].eq(group)], patient_cols), path)
        outputs[f"patient_list_{group}"] = path

    for name, frame in audit.top_error_lists(audited, args.top_n).items():
        path = output_dir / f"078_{name}.csv"
        write_csv(frame, path)
        outputs[name] = path

    table_outputs = {
        "confusion_summary": confusion,
        "event_type_by_error_group": event_types,
        "outcome_components_by_error_group": component_summary,
        "pre12_key_continuous_by_error_group": continuous_summary,
        "pre12_key_binary_by_error_group": binary_summary,
        "event_time_by_error_group": event_time_summary,
        "risk_deciles": risk_deciles,
        "label_noise_candidates": label_candidates,
        "label_noise_summary": label_noise_summary,
    }

    for name, frame in table_outputs.items():
        path = output_dir / f"078_{name}.csv"
        write_csv(frame, path)
        outputs[name] = path

    overall_event_time = audit.read_overall_event_time_sql_result()
    if overall_event_time is not None:
        path = output_dir / "078_overall_event_time_from_sql_qc.csv"
        write_csv(overall_event_time, path)
        outputs["overall_event_time_from_sql_qc"] = path

    metadata = {
        "dataset": str(raw_path),
        "model_joblib": str(model_path) if not args.prediction_csv else None,
        "analysis_split": args.analysis_split,
        "n_rows": int(len(audited)),
        "n_events": int(audit.safe_numeric(audited[audit.OUTCOME_COL]).fillna(0).astype(int).sum()),
        "risk_source": risk_input.source,
        "risk_note": risk_input.note,
        "risk_threshold": threshold,
        "high_risk_top_fraction": args.high_risk_top_fraction,
        "event_time_note": event_time_note,
        "output_dir": str(output_dir),
        "columns_missing_for_post12_nee": bool(audited["post12_nee_max"].isna().all()),
        "columns_missing_for_event_time": bool(audited["event_hour_after_landmark"].isna().all()),
    }
    meta_path = output_dir / "078_run_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    outputs["run_metadata"] = meta_path

    report_args = SimpleNamespace(
        dataset=raw_path,
        output_dir=output_dir,
        high_risk_top_fraction=args.high_risk_top_fraction,
        risk_threshold=args.risk_threshold,
    )
    report = audit.build_report(
        audited,
        report_args,
        risk_input,
        event_time_note,
        outputs,
        confusion,
        event_types,
        component_summary,
        binary_summary,
        label_noise_summary,
    )
    report_path = output_dir / "078_error_analysis_and_label_audit_report.md"
    report_path.write_text(report, encoding="utf-8")

    print("[OK] 078 error analysis and label audit complete")
    print(f"Analysis split: {args.analysis_split}")
    print(f"Output directory: {output_dir}")
    print(f"Report: {report_path}")
    print(confusion.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
