#!/usr/bin/env python3
"""
078 Error analysis and label-quality audit.

This script is intentionally analysis-first. It does not search for a better
model. Its main path consumes patient-level risk scores from a previously
chosen model, assigns high/low risk groups, and audits false positives, false
negatives, true positives, and true negatives against outcome components and
pre-landmark clinical signals.

If no patient-level predictions are available, pass --reconstruct-risk-score to
create audit-only cross-fitted elastic-net scores from the current modeling
dataset. That fallback is useful for making the audit runnable in a clean
workspace, but it should not be reported as the final 075/076 model.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "data" / "raw" / "model_070G_modeling_dataset_v1.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "tables" / "078_error_analysis_and_label_audit"

ID_COLS = ["subject_id", "hadm_id", "stay_id"]
TIME_COLS = ["intime", "landmark12_time", "window60_time"]
OUTCOME_COL = "primary_outcome_flag"

PRIMARY_COMPONENT_COLS = [
    "label_support_escalation_flag",
    "label_nee_escalation_flag",
    "label_death_12_60_flag",
]

SECONDARY_COMPONENT_COLS = [
    "label_hd_nee010_flag",
    "label_hd_no_nee_flag",
    "label_mixed_shock_proxy_flag",
    "label_hd_lactate_confirmed_flag",
]

KEY_CONTINUOUS_COLS = [
    "risk_score",
    "age",
    "early_sepsis12_max_sofa_score",
    "ahf_evidence_score_primary_12h",
    "sbp_min",
    "sbp_last",
    "mbp_min",
    "mbp_last",
    "hr_max",
    "hr_delta",
    "shock_index_max",
    "rr_mean",
    "spo2_min",
    "temp_min",
    "lactate_max",
    "lactate_delta",
    "ph_min",
    "baseexcess_min",
    "aniongap_max",
    "creatinine_max",
    "creatinine_delta",
    "bun_max",
    "urineoutput_0_12h_total_ml",
    "gcs_min",
    "nee_0_12h_max",
    "nee_0_12h_last",
    "post12_nee_max",
    "nee_delta_post12_vs_pre12_max",
    "vasoactive_agent_count_0_12h",
    "wbc_max",
    "platelet_min",
    "inr_max",
]

KEY_BINARY_COLS = [
    "high_risk_flag",
    "primary_outcome_flag",
    "label_support_escalation_flag",
    "label_nee_escalation_flag",
    "label_death_12_60_flag",
    "label_hd_nee010_flag",
    "label_hd_no_nee_flag",
    "label_mixed_shock_proxy_flag",
    "label_hd_lactate_confirmed_flag",
    "female",
    "first_unit_ccu_cicu_flag",
    "first_unit_cvicu_flag",
    "iv_loop_rx_early12_flag",
    "ntprobnp_ge300_early12_flag",
    "suspected_infection_before_icu_flag",
    "suspected_infection_icu_0_6h_flag",
    "suspected_infection_icu_6_12h_flag",
    "lactate_available_flag",
    "pre12_support_any_flag",
    "pre12_low_sbp_flag",
    "pre12_low_map_flag",
    "pre12_lactate_ge2_flag",
    "pre12_lactate_ge4_flag",
    "pre12_low_urine_flag",
    "pre12_aki_delta_flag",
    "pre12_acidemia_flag",
    "pre12_shock_proxy_flag",
    "advanced_respiratory_support_0_12h_flag",
    "vasopressor_any_0_12h_flag",
    "inotrope_any_0_12h_flag",
    "norepinephrine_0_12h_flag",
    "epinephrine_0_12h_flag",
    "dopamine_0_12h_flag",
    "phenylephrine_0_12h_flag",
    "vasopressin_0_12h_flag",
    "dobutamine_0_12h_flag",
    "milrinone_0_12h_flag",
    "nee_available_0_12h_flag",
    "nee_pre12_ge_0_5_flag",
    "nee_pre12_ge_1_0_flag",
    "post12_transient_vaso_flag",
]

PATIENT_LIST_COLS = [
    *ID_COLS,
    *TIME_COLS,
    "risk_score",
    "risk_threshold",
    "high_risk_flag",
    "error_group",
    OUTCOME_COL,
    "event_type",
    "event_hour_after_landmark",
    *PRIMARY_COMPONENT_COLS,
    *SECONDARY_COMPONENT_COLS,
    "pre12_shock_proxy_flag",
    "pre12_support_any_flag",
    "pre12_low_sbp_flag",
    "pre12_low_map_flag",
    "pre12_lactate_ge2_flag",
    "pre12_low_urine_flag",
    "pre12_aki_delta_flag",
    "pre12_acidemia_flag",
    "post12_transient_vaso_flag",
    "nee_0_12h_max",
    "nee_0_12h_last",
    "post12_nee_max",
    "nee_delta_post12_vs_pre12_max",
    "sbp_min",
    "mbp_min",
    "hr_max",
    "shock_index_max",
    "lactate_max",
    "ph_min",
    "baseexcess_min",
    "creatinine_max",
    "creatinine_delta",
    "urineoutput_0_12h_total_ml",
    "early_sepsis12_max_sofa_score",
    "suspected_infection_before_icu_flag",
    "suspected_infection_icu_0_6h_flag",
    "suspected_infection_icu_6_12h_flag",
]


@dataclass
class RiskInput:
    frame: pd.DataFrame
    score_col: str
    source: str
    note: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run patient-level error analysis and label-quality audit."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--prediction-csv",
        type=Path,
        default=None,
        help="CSV with patient-level risk scores from the selected model.",
    )
    parser.add_argument(
        "--prediction-col",
        default=None,
        help="Risk/probability column in --prediction-csv. Auto-detected if omitted.",
    )
    parser.add_argument(
        "--event-time-csv",
        type=Path,
        default=None,
        help="Optional CSV with patient-level event timing to merge by stay/hadm/subject id.",
    )
    parser.add_argument(
        "--event-time-col",
        default=None,
        help="Event hour after landmark column in --event-time-csv. Auto-detected if omitted.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--high-risk-top-fraction",
        type=float,
        default=0.20,
        help="Default high-risk group is the top fraction by predicted risk.",
    )
    parser.add_argument(
        "--risk-threshold",
        type=float,
        default=None,
        help="Absolute risk threshold. Overrides --high-risk-top-fraction.",
    )
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument(
        "--reconstruct-risk-score",
        action="store_true",
        help=(
            "If no prediction file is available, create audit-only cross-fitted "
            "elastic-net scores from the modeling dataset."
        ),
    )
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=20260508)
    return parser.parse_args()


def read_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    return pd.read_csv(path)


def normalize_id_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ID_COLS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    return out


def first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    columns_set = set(columns)
    for col in candidates:
        if col in columns_set:
            return col
    return None


def detect_prediction_col(df: pd.DataFrame, requested: str | None = None) -> str:
    if requested:
        if requested not in df.columns:
            raise ValueError(f"Requested prediction column not found: {requested}")
        return requested

    exact_candidates = [
        "risk_score",
        "pred_prob",
        "predicted_probability",
        "prediction_probability",
        "y_pred_proba",
        "y_pred_prob",
        "p_hat",
        "phat",
        "probability",
        "prob_event",
        "event_probability",
        "calibrated_probability",
        "top80_elasticnet_platt",
        "top80_elasticnet_platt_prob",
    ]
    for col in exact_candidates:
        if col in df.columns:
            return col

    fuzzy = []
    for col in df.columns:
        lower = col.lower()
        if "ntprobnp" in lower or lower.endswith("_flag"):
            continue
        looks_like_prob = (
            lower.startswith("pred")
            or lower.startswith("risk")
            or lower.endswith("_prob")
            or lower.endswith("_proba")
            or "probability" in lower
            or "risk_score" in lower
        )
        if looks_like_prob and pd.api.types.is_numeric_dtype(df[col]):
            fuzzy.append(col)

    if len(fuzzy) == 1:
        return fuzzy[0]
    if len(fuzzy) > 1:
        raise ValueError(
            "Multiple possible prediction columns found; pass --prediction-col. "
            f"Candidates: {fuzzy}"
        )
    raise ValueError("Could not auto-detect prediction column.")


def merge_prediction_scores(dataset: pd.DataFrame, risk_input: RiskInput) -> pd.DataFrame:
    pred = normalize_id_types(risk_input.frame)
    data = normalize_id_types(dataset)

    score_col = risk_input.score_col
    if score_col != "risk_score":
        pred = pred.rename(columns={score_col: "risk_score"})
        score_col = "risk_score"
    if "risk_score" not in pred.columns:
        raise ValueError("Prediction data must contain risk_score after normalization.")

    merge_cols = [col for col in ID_COLS if col in data.columns and col in pred.columns]
    if merge_cols:
        pred_cols = merge_cols + ["risk_score"]
        dup = pred.duplicated(merge_cols).sum()
        if dup:
            raise ValueError(
                f"Prediction file has {dup} duplicate rows by keys {merge_cols}."
            )
        merged = data.merge(pred[pred_cols], on=merge_cols, how="left", validate="one_to_one")
    elif len(pred) == len(data):
        merged = data.copy()
        merged["risk_score"] = pred["risk_score"].to_numpy()
    else:
        raise ValueError(
            "Prediction file must share at least one id column "
            f"({ID_COLS}) with dataset, or have exactly the same row count."
        )

    missing = merged["risk_score"].isna().sum()
    if missing:
        raise ValueError(f"Missing risk scores after merge: {missing} rows.")
    return merged


def find_existing_prediction_file(dataset: pd.DataFrame) -> RiskInput | None:
    try:
        col = detect_prediction_col(dataset)
        if col != "ntprobnp_ge300_early12_flag":
            return RiskInput(
                frame=dataset[[*ID_COLS, col]].copy(),
                score_col=col,
                source="dataset",
                note=f"Risk score column detected in dataset: {col}",
            )
    except ValueError:
        pass

    search_roots = [
        ROOT / "outputs" / "model_results",
        ROOT / "outputs" / "tables",
        ROOT / "data",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.csv")):
            if path.name == DEFAULT_DATASET.name:
                continue
            try:
                candidate = pd.read_csv(path, nrows=50)
                col = detect_prediction_col(candidate)
            except Exception:
                continue
            full = pd.read_csv(path)
            return RiskInput(
                frame=full,
                score_col=col,
                source=str(path),
                note=f"Risk score column auto-detected from {path}: {col}",
            )
    return None


def build_crossfit_elasticnet_risk(
    df: pd.DataFrame,
    n_splits: int,
    random_state: int,
) -> RiskInput:
    try:
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import StratifiedKFold
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn is required for --reconstruct-risk-score."
        ) from exc

    if OUTCOME_COL not in df.columns:
        raise ValueError(f"Outcome column not found: {OUTCOME_COL}")

    y = pd.to_numeric(df[OUTCOME_COL], errors="coerce")
    if y.isna().any():
        raise ValueError(f"Outcome has missing/non-numeric values: {y.isna().sum()}")
    y = y.astype(int).to_numpy()

    leakage_prefixes = ("label_",)
    leakage_cols = {OUTCOME_COL, *ID_COLS, *TIME_COLS}
    feature_cols = []
    for col in df.columns:
        if col in leakage_cols:
            continue
        if any(col.startswith(prefix) for prefix in leakage_prefixes):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            feature_cols.append(col)

    if not feature_cols:
        raise ValueError("No numeric non-label features available for score reconstruction.")

    x = df[feature_cols].copy()
    class_counts = np.bincount(y)
    max_splits = int(class_counts[class_counts > 0].min())
    n_splits = max(2, min(n_splits, max_splits))

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    penalty="elasticnet",
                    solver="saga",
                    l1_ratio=0.5,
                    C=0.1,
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    risk = np.full(len(df), np.nan)
    for train_idx, test_idx in cv.split(x, y):
        model.fit(x.iloc[train_idx], y[train_idx])
        risk[test_idx] = model.predict_proba(x.iloc[test_idx])[:, 1]

    out_cols = [col for col in ID_COLS if col in df.columns]
    out = df[out_cols].copy()
    out["risk_score"] = risk
    note = (
        "Audit-only cross-fitted elastic-net risk scores reconstructed because no "
        "saved patient-level predictions were found. These scores are not a "
        "replacement for the selected 075/076 model predictions."
    )
    return RiskInput(frame=out, score_col="risk_score", source="reconstructed_cv", note=note)


def detect_event_time_col(df: pd.DataFrame, requested: str | None = None) -> str | None:
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
    return first_existing(df.columns, candidates)


def merge_event_time(
    dataset: pd.DataFrame,
    event_time_csv: Path | None,
    event_time_col: str | None,
) -> tuple[pd.DataFrame, str]:
    out = dataset.copy()
    detected = detect_event_time_col(
        out,
        event_time_col if event_time_csv is None else None,
    )
    if detected:
        if detected != "event_hour_after_landmark":
            out = out.rename(columns={detected: "event_hour_after_landmark"})
        return out, f"Event time found in dataset column: {detected}"

    if event_time_csv is None:
        out["event_hour_after_landmark"] = np.nan
        return out, "Patient-level event time unavailable in current inputs."

    event_df = normalize_id_types(read_csv(event_time_csv, "event time csv"))
    detected = detect_event_time_col(event_df, event_time_col)
    if detected is None:
        raise ValueError(
            "Could not detect event-time column. Pass --event-time-col explicitly."
        )
    if detected != "event_hour_after_landmark":
        event_df = event_df.rename(columns={detected: "event_hour_after_landmark"})

    data = normalize_id_types(out)
    merge_cols = [col for col in ID_COLS if col in data.columns and col in event_df.columns]
    if not merge_cols:
        raise ValueError("Event-time CSV must share at least one id column with dataset.")
    event_df = event_df[merge_cols + ["event_hour_after_landmark"]].drop_duplicates(merge_cols)
    out = data.merge(event_df, on=merge_cols, how="left", validate="one_to_one")
    return out, f"Event time merged from {event_time_csv} column {detected}."


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def binary_any(df: pd.DataFrame, columns: Iterable[str]) -> pd.Series:
    available = [col for col in columns if col in df.columns]
    if not available:
        return pd.Series(np.nan, index=df.index)
    numeric = df[available].apply(pd.to_numeric, errors="coerce")
    return (numeric.fillna(0) > 0).any(axis=1).astype(int)


def derive_audit_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "sbp_min" in out.columns:
        out["pre12_low_sbp_flag"] = (safe_numeric(out["sbp_min"]) < 90).astype("Int64")
    else:
        out["pre12_low_sbp_flag"] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    if "mbp_min" in out.columns:
        out["pre12_low_map_flag"] = (safe_numeric(out["mbp_min"]) < 65).astype("Int64")
    else:
        out["pre12_low_map_flag"] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    if "lactate_max" in out.columns:
        lactate = safe_numeric(out["lactate_max"])
        out["pre12_lactate_ge2_flag"] = (lactate >= 2).astype("Int64")
        out["pre12_lactate_ge4_flag"] = (lactate >= 4).astype("Int64")
    else:
        out["pre12_lactate_ge2_flag"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
        out["pre12_lactate_ge4_flag"] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    if "urineoutput_0_12h_total_ml" in out.columns:
        urine = safe_numeric(out["urineoutput_0_12h_total_ml"])
        crude_low = urine < 240
    else:
        crude_low = pd.Series(False, index=out.index)
    if "low_urineoutput_0_12h_crude_flag" in out.columns:
        low_uo = (
            safe_numeric(out["low_urineoutput_0_12h_crude_flag"]).fillna(0).astype(int).eq(1)
            | crude_low.fillna(False)
        )
    else:
        low_uo = crude_low.fillna(False)
    out["pre12_low_urine_flag"] = low_uo.astype("Int64")

    if "creatinine_delta" in out.columns:
        out["pre12_aki_delta_flag"] = (
            safe_numeric(out["creatinine_delta"]) >= 0.3
        ).astype("Int64")
    else:
        out["pre12_aki_delta_flag"] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    acidemia_parts = []
    if "ph_min" in out.columns:
        acidemia_parts.append(safe_numeric(out["ph_min"]) < 7.30)
    if "baseexcess_min" in out.columns:
        acidemia_parts.append(safe_numeric(out["baseexcess_min"]) <= -5)
    if acidemia_parts:
        acidemia = pd.concat(acidemia_parts, axis=1).fillna(False).any(axis=1)
        out["pre12_acidemia_flag"] = acidemia.astype("Int64")
    else:
        out["pre12_acidemia_flag"] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    support_cols = [
        "vasopressor_any_0_12h_flag",
        "inotrope_any_0_12h_flag",
        "norepinephrine_0_12h_flag",
        "epinephrine_0_12h_flag",
        "dopamine_0_12h_flag",
        "phenylephrine_0_12h_flag",
        "vasopressin_0_12h_flag",
        "dobutamine_0_12h_flag",
        "milrinone_0_12h_flag",
    ]
    support_any = binary_any(out, support_cols)
    if "nee_0_12h_max" in out.columns:
        nee_max = safe_numeric(out["nee_0_12h_max"])
        support_any = (
            support_any.fillna(0).astype(int).eq(1) | nee_max.fillna(0).gt(0)
        ).astype(int)
        out["nee_pre12_ge_0_5_flag"] = (nee_max >= 0.5).astype("Int64")
        out["nee_pre12_ge_1_0_flag"] = (nee_max >= 1.0).astype("Int64")
    else:
        out["nee_pre12_ge_0_5_flag"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
        out["nee_pre12_ge_1_0_flag"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
    out["pre12_support_any_flag"] = support_any.astype("Int64")

    if "hr_max" in out.columns and "sbp_min" in out.columns:
        hr = safe_numeric(out["hr_max"])
        sbp = safe_numeric(out["sbp_min"])
        out["shock_index_max"] = np.where(sbp > 0, hr / sbp, np.nan)
    else:
        out["shock_index_max"] = np.nan

    hemodynamic_instability = (
        out["pre12_support_any_flag"].fillna(0).astype(int).eq(1)
        | out["pre12_low_sbp_flag"].fillna(0).astype(int).eq(1)
        | out["pre12_low_map_flag"].fillna(0).astype(int).eq(1)
    )
    hypoperfusion = (
        out["pre12_lactate_ge2_flag"].fillna(0).astype(int).eq(1)
        | out["pre12_low_urine_flag"].fillna(0).astype(int).eq(1)
        | out["pre12_aki_delta_flag"].fillna(0).astype(int).eq(1)
        | out["pre12_acidemia_flag"].fillna(0).astype(int).eq(1)
    )
    out["pre12_shock_proxy_flag"] = (hemodynamic_instability & hypoperfusion).astype("Int64")

    post_nee_col = first_existing(
        out.columns,
        [
            "post12_nee_max",
            "nee_12_60h_max",
            "nee_post12_max",
            "post_landmark_nee_max",
        ],
    )
    if post_nee_col:
        if post_nee_col != "post12_nee_max":
            out["post12_nee_max"] = safe_numeric(out[post_nee_col])
        pre_nee = safe_numeric(out.get("nee_0_12h_max", pd.Series(np.nan, index=out.index))).fillna(0)
        out["nee_delta_post12_vs_pre12_max"] = safe_numeric(out["post12_nee_max"]).fillna(0) - pre_nee
    else:
        out["post12_nee_max"] = np.nan
        out["nee_delta_post12_vs_pre12_max"] = np.nan

    duration_col = first_existing(
        out.columns,
        [
            "post12_vaso_duration_hours",
            "post12_vasoactive_duration_hours",
            "vaso_12_60h_duration_hours",
            "post_landmark_vaso_duration_hours",
        ],
    )
    if duration_col:
        duration = safe_numeric(out[duration_col])
        out["post12_transient_vaso_flag"] = (
            duration.gt(0) & duration.le(2)
        ).astype("Int64")
    else:
        out["post12_transient_vaso_flag"] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    return out


def derive_event_type(df: pd.DataFrame) -> pd.Series:
    outcome = safe_numeric(df.get(OUTCOME_COL, pd.Series(0, index=df.index))).fillna(0).astype(int)
    support = safe_numeric(df.get("label_support_escalation_flag", pd.Series(0, index=df.index))).fillna(0).astype(int)
    nee = safe_numeric(df.get("label_nee_escalation_flag", pd.Series(0, index=df.index))).fillna(0).astype(int)
    death = safe_numeric(df.get("label_death_12_60_flag", pd.Series(0, index=df.index))).fillna(0).astype(int)
    lactate_confirmed = safe_numeric(
        df.get("label_hd_lactate_confirmed_flag", pd.Series(0, index=df.index))
    ).fillna(0).astype(int)
    mixed = safe_numeric(
        df.get("label_mixed_shock_proxy_flag", pd.Series(0, index=df.index))
    ).fillna(0).astype(int)

    event_type = pd.Series("no_primary_outcome", index=df.index, dtype="object")
    event_type[(outcome == 1) & (support == 1) & (nee == 0) & (death == 0)] = "support_escalation_only"
    event_type[(outcome == 1) & (support == 0) & (nee == 1) & (death == 0)] = "nee_escalation_only"
    event_type[(outcome == 1) & (support == 1) & (nee == 1) & (death == 0)] = "support_plus_nee"
    event_type[(outcome == 1) & (support == 0) & (nee == 0) & (death == 1)] = "death_only"
    event_type[(outcome == 1) & (support == 1) & (nee == 0) & (death == 1)] = "support_plus_death"
    event_type[(outcome == 1) & (support == 0) & (nee == 1) & (death == 1)] = "nee_plus_death"
    event_type[(outcome == 1) & (support == 1) & (nee == 1) & (death == 1)] = "support_plus_nee_plus_death"
    event_type[(outcome == 1) & (support == 0) & (nee == 0) & (death == 0) & (lactate_confirmed == 1)] = "lactate_confirmed_only"
    event_type[(outcome == 1) & (support == 0) & (nee == 0) & (death == 0) & (mixed == 1)] = "mixed_shock_proxy_only"
    event_type[(outcome == 1) & (support == 0) & (nee == 0) & (death == 0) & (lactate_confirmed == 0) & (mixed == 0)] = "primary_without_core_component"
    return event_type


def assign_error_groups(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    out = df.copy()
    out["risk_threshold"] = threshold
    out["high_risk_flag"] = (safe_numeric(out["risk_score"]) >= threshold).astype(int)
    y = safe_numeric(out[OUTCOME_COL]).fillna(0).astype(int)
    high = out["high_risk_flag"].eq(1)
    out["error_group"] = np.select(
        [
            high & y.eq(1),
            high & y.eq(0),
            ~high & y.eq(1),
            ~high & y.eq(0),
        ],
        [
            "true_positive",
            "false_positive",
            "false_negative",
            "true_negative",
        ],
        default="unclassified",
    )
    return out


def pct(numer: float, denom: float) -> float:
    if denom == 0 or pd.isna(denom):
        return np.nan
    return 100.0 * numer / denom


def summarize_confusion(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = len(df)
    events = safe_numeric(df[OUTCOME_COL]).fillna(0).astype(int).sum()
    for group, sub in df.groupby("error_group", dropna=False):
        n = len(sub)
        n_events = safe_numeric(sub[OUTCOME_COL]).fillna(0).astype(int).sum()
        rows.append(
            {
                "error_group": group,
                "n": n,
                "pct_total": pct(n, total),
                "n_events": n_events,
                "event_rate": pct(n_events, n),
                "mean_risk": safe_numeric(sub["risk_score"]).mean(),
                "median_risk": safe_numeric(sub["risk_score"]).median(),
            }
        )
    order = ["true_positive", "false_positive", "false_negative", "true_negative"]
    out = pd.DataFrame(rows)
    out["order"] = out["error_group"].map({g: i for i, g in enumerate(order)}).fillna(99)
    out = out.sort_values(["order", "error_group"]).drop(columns="order")
    out.attrs["events"] = events
    return out


def summarize_event_types(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group, group_df in df.groupby("error_group", dropna=False):
        denom = len(group_df)
        counts = group_df["event_type"].value_counts(dropna=False)
        for event_type, n in counts.items():
            rows.append(
                {
                    "error_group": group,
                    "event_type": event_type,
                    "n": int(n),
                    "pct_within_group": pct(n, denom),
                }
            )
    return pd.DataFrame(rows).sort_values(["error_group", "n"], ascending=[True, False])


def summarize_components(df: pd.DataFrame) -> pd.DataFrame:
    cols = [col for col in [*PRIMARY_COMPONENT_COLS, *SECONDARY_COMPONENT_COLS] if col in df.columns]
    rows = []
    for group, group_df in df.groupby("error_group", dropna=False):
        denom = len(group_df)
        for col in cols:
            values = safe_numeric(group_df[col])
            n_nonmissing = values.notna().sum()
            n_positive = values.fillna(0).astype(int).sum()
            rows.append(
                {
                    "error_group": group,
                    "component": col,
                    "n_group": denom,
                    "n_nonmissing": n_nonmissing,
                    "n_positive": int(n_positive),
                    "pct_group_positive": pct(n_positive, denom),
                    "pct_nonmissing_positive": pct(n_positive, n_nonmissing),
                }
            )
    return pd.DataFrame(rows)


def summarize_continuous(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = []
    cols = [col for col in columns if col in df.columns]
    for group, group_df in df.groupby("error_group", dropna=False):
        for col in cols:
            values = safe_numeric(group_df[col])
            rows.append(
                {
                    "error_group": group,
                    "variable": col,
                    "n": int(values.notna().sum()),
                    "missing": int(values.isna().sum()),
                    "missing_pct": pct(values.isna().sum(), len(values)),
                    "mean": values.mean(),
                    "sd": values.std(),
                    "median": values.median(),
                    "q1": values.quantile(0.25),
                    "q3": values.quantile(0.75),
                    "min": values.min(),
                    "max": values.max(),
                }
            )
    return pd.DataFrame(rows)


def summarize_binary(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = []
    cols = [col for col in columns if col in df.columns]
    for group, group_df in df.groupby("error_group", dropna=False):
        denom = len(group_df)
        for col in cols:
            values = safe_numeric(group_df[col])
            n_nonmissing = values.notna().sum()
            n_positive = values.fillna(0).astype(int).sum()
            rows.append(
                {
                    "error_group": group,
                    "variable": col,
                    "n_group": denom,
                    "n_nonmissing": int(n_nonmissing),
                    "n_positive": int(n_positive),
                    "pct_group_positive": pct(n_positive, denom),
                    "pct_nonmissing_positive": pct(n_positive, n_nonmissing),
                    "missing_pct": pct(values.isna().sum(), denom),
                }
            )
    return pd.DataFrame(rows)


def summarize_event_time(df: pd.DataFrame) -> pd.DataFrame:
    if "event_hour_after_landmark" not in df.columns:
        return pd.DataFrame(
            [{"error_group": "all", "event_time_bin": "not_available", "n": len(df), "pct": 100.0}]
        )
    event_df = df[df[OUTCOME_COL].fillna(0).astype(int).eq(1)].copy()
    event_hours = safe_numeric(event_df["event_hour_after_landmark"])
    if event_hours.notna().sum() == 0:
        return pd.DataFrame(
            [
                {
                    "error_group": group,
                    "event_time_bin": "not_available",
                    "n": len(sub),
                    "pct_within_events_in_group": np.nan,
                }
                for group, sub in event_df.groupby("error_group", dropna=False)
            ]
        )
    bins = [-np.inf, 0, 2, 6, 12, 24, 36, 48, 60, 72, np.inf]
    labels = [
        "before_or_at_landmark",
        "00_0_2h_after_landmark",
        "01_2_6h_after_landmark",
        "02_6_12h_after_landmark",
        "03_12_24h_after_landmark",
        "04_24_36h_after_landmark",
        "05_36_48h_after_landmark",
        "06_48_60h_after_landmark",
        "07_60_72h_after_landmark",
        "08_after_72h",
    ]
    event_df["event_time_bin"] = pd.cut(event_hours, bins=bins, labels=labels, right=True)
    rows = []
    for group, sub in event_df.groupby("error_group", dropna=False):
        denom = len(sub)
        for bin_name, n in sub["event_time_bin"].value_counts(dropna=False).items():
            rows.append(
                {
                    "error_group": group,
                    "event_time_bin": str(bin_name),
                    "n": int(n),
                    "pct_within_events_in_group": pct(n, denom),
                }
            )
    return pd.DataFrame(rows).sort_values(["error_group", "event_time_bin"])


def summarize_risk_deciles(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    try:
        out["risk_decile"] = pd.qcut(
            safe_numeric(out["risk_score"]),
            q=10,
            labels=[f"D{i}" for i in range(1, 11)],
            duplicates="drop",
        )
    except ValueError:
        out["risk_decile"] = "not_available"
    rows = []
    for decile, sub in out.groupby("risk_decile", dropna=False, observed=False):
        n = len(sub)
        n_events = safe_numeric(sub[OUTCOME_COL]).fillna(0).astype(int).sum()
        rows.append(
            {
                "risk_decile": str(decile),
                "n": n,
                "n_events": int(n_events),
                "event_rate": pct(n_events, n),
                "risk_min": safe_numeric(sub["risk_score"]).min(),
                "risk_median": safe_numeric(sub["risk_score"]).median(),
                "risk_max": safe_numeric(sub["risk_score"]).max(),
            }
        )
    return pd.DataFrame(rows)


def select_existing(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    existing = [col for col in cols if col in df.columns]
    return df[existing].copy()


def top_error_lists(df: pd.DataFrame, top_n: int) -> dict[str, pd.DataFrame]:
    patient_cols = [col for col in PATIENT_LIST_COLS if col in df.columns]
    return {
        "top_false_positives": select_existing(
            df[df["error_group"].eq("false_positive")]
            .sort_values("risk_score", ascending=False)
            .head(top_n),
            patient_cols,
        ),
        "top_false_negatives_extreme_low_risk": select_existing(
            df[df["error_group"].eq("false_negative")]
            .sort_values("risk_score", ascending=True)
            .head(top_n),
            patient_cols,
        ),
        "top_false_negatives_near_threshold": select_existing(
            df[df["error_group"].eq("false_negative")]
            .sort_values("risk_score", ascending=False)
            .head(top_n),
            patient_cols,
        ),
    }


def label_noise_candidates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = df.copy()
    zero = pd.Series(0, index=out.index)
    outcome = safe_numeric(out.get(OUTCOME_COL, zero)).fillna(0).astype(int)
    support = safe_numeric(out.get("label_support_escalation_flag", zero)).fillna(0).astype(int)
    nee = safe_numeric(out.get("label_nee_escalation_flag", zero)).fillna(0).astype(int)
    death = safe_numeric(out.get("label_death_12_60_flag", zero)).fillna(0).astype(int)
    lactate_confirmed = safe_numeric(out.get("label_hd_lactate_confirmed_flag", zero)).fillna(0).astype(int)
    mixed = safe_numeric(out.get("label_mixed_shock_proxy_flag", zero)).fillna(0).astype(int)
    pre_shock = safe_numeric(out.get("pre12_shock_proxy_flag", zero)).fillna(0).astype(int)
    nee_max = safe_numeric(out.get("nee_0_12h_max", pd.Series(np.nan, index=out.index)))
    event_hour = safe_numeric(out.get("event_hour_after_landmark", pd.Series(np.nan, index=out.index)))

    flags = pd.DataFrame(index=out.index)
    flags["fp_severe_pre12_no_outcome"] = (
        out["error_group"].eq("false_positive") & pre_shock.eq(1)
    )
    flags["fp_pre12_nee_ge_0_5_no_outcome"] = (
        out["error_group"].eq("false_positive") & nee_max.ge(0.5).fillna(False)
    )
    flags["fn_death_only"] = (
        out["error_group"].eq("false_negative")
        & death.eq(1)
        & support.eq(0)
        & nee.eq(0)
    )
    flags["fn_support_or_nee_event_low_risk"] = (
        out["error_group"].eq("false_negative") & (support.eq(1) | nee.eq(1))
    )
    flags["fn_no_pre12_shock_signal"] = (
        out["error_group"].eq("false_negative") & pre_shock.eq(0)
    )
    flags["fn_very_early_event"] = (
        out["error_group"].eq("false_negative") & event_hour.le(2).fillna(False)
    )
    flags["primary_positive_without_core_component"] = (
        outcome.eq(1) & support.eq(0) & nee.eq(0) & death.eq(0) & lactate_confirmed.eq(0) & mixed.eq(0)
    )
    flags["primary_negative_with_core_component"] = (
        outcome.eq(0) & (support.eq(1) | nee.eq(1) | death.eq(1))
    )
    flags["death_circulatory_unclear_structural_proxy"] = (
        death.eq(1) & support.eq(0) & nee.eq(0) & lactate_confirmed.eq(0)
    )
    flags["pre12_nee_extreme_ge_1_0"] = nee_max.ge(1.0).fillna(False)
    flags["pre12_nee_extreme_ge_3_0"] = nee_max.ge(3.0).fillna(False)

    out["label_noise_flag_count"] = flags.sum(axis=1)
    for col in flags.columns:
        out[col] = flags[col].astype(int)

    candidate_cols = [
        *[col for col in PATIENT_LIST_COLS if col in out.columns],
        "label_noise_flag_count",
        *flags.columns.tolist(),
    ]
    candidates = (
        out[out["label_noise_flag_count"].gt(0)]
        .sort_values(["label_noise_flag_count", "risk_score"], ascending=[False, False])
    )

    summary_rows = []
    for flag in flags.columns:
        total_n = int(flags[flag].sum())
        row = {"audit_flag": flag, "n": total_n, "pct_total": pct(total_n, len(flags))}
        for group in ["false_positive", "false_negative", "true_positive", "true_negative"]:
            group_mask = out["error_group"].eq(group)
            row[f"n_{group}"] = int((flags[flag] & group_mask).sum())
            row[f"pct_{group}"] = pct((flags[flag] & group_mask).sum(), group_mask.sum())
        summary_rows.append(row)

    return select_existing(candidates, candidate_cols), pd.DataFrame(summary_rows)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def read_overall_event_time_sql_result() -> pd.DataFrame | None:
    for base in [ROOT, ROOT.parent]:
        path = base / "sql_results" / "061F_QC1_event_time_since_landmark.csv"
        if path.exists():
            return pd.read_csv(path)
        path = base / "sql_results" / "060B_QC1_event_time_since_landmark.csv"
        if path.exists():
            return pd.read_csv(path)
    return None


def format_metric(value: float, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{value:.{digits}f}"


def to_markdown_safe(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return "_No rows._"
    try:
        return df.head(max_rows).to_markdown(index=False)
    except ImportError:
        return "```\n" + df.head(max_rows).to_string(index=False) + "\n```"


def build_report(
    df: pd.DataFrame,
    args: argparse.Namespace,
    risk_input: RiskInput,
    event_time_note: str,
    outputs: dict[str, Path],
    confusion: pd.DataFrame,
    event_types: pd.DataFrame,
    component_summary: pd.DataFrame,
    binary_summary: pd.DataFrame,
    label_noise_summary: pd.DataFrame,
) -> str:
    total = len(df)
    n_events = int(safe_numeric(df[OUTCOME_COL]).fillna(0).astype(int).sum())
    threshold = float(df["risk_threshold"].iloc[0])

    fp_n = int((df["error_group"] == "false_positive").sum())
    fn_n = int((df["error_group"] == "false_negative").sum())
    tp_n = int((df["error_group"] == "true_positive").sum())
    tn_n = int((df["error_group"] == "true_negative").sum())

    missing_post12 = "post12_nee_max" not in df.columns or df["post12_nee_max"].notna().sum() == 0
    missing_event_time = df["event_hour_after_landmark"].notna().sum() == 0
    transient_available = (
        "post12_transient_vaso_flag" in df.columns
        and df["post12_transient_vaso_flag"].notna().sum() > 0
    )

    fp_pre_shock = binary_summary[
        (binary_summary["error_group"] == "false_positive")
        & (binary_summary["variable"] == "pre12_shock_proxy_flag")
    ]
    fn_death = binary_summary[
        (binary_summary["error_group"] == "false_negative")
        & (binary_summary["variable"] == "label_death_12_60_flag")
    ]
    fp_pre_shock_pct = (
        float(fp_pre_shock["pct_group_positive"].iloc[0]) if not fp_pre_shock.empty else np.nan
    )
    fn_death_pct = (
        float(fn_death["pct_group_positive"].iloc[0]) if not fn_death.empty else np.nan
    )

    notes = []
    if risk_input.source == "reconstructed_cv":
        notes.append(
            "- Risk scores were reconstructed only for this audit because no saved patient-level predictions were present. Replace them with the formal 075/076 model predictions before using FP/FN lists in a manuscript."
        )
    if missing_event_time:
        notes.append(
            "- Patient-level outcome event time is not present in the current modeling dataset, so event-time-by-error-group tables are placeholders. Merge an event-time CSV to complete this audit item."
        )
    if missing_post12:
        notes.append(
            "- Patient-level post12 NEE maximum/duration is not present, so NEE upgrade magnitude and transient vasopressor audit rely only on outcome component flags."
        )
    if not transient_available:
        notes.append(
            "- Transient post12 vasopressor exposure cannot be identified without patient-level post-landmark medication duration."
        )

    component_view = component_summary.pivot_table(
        index="component",
        columns="error_group",
        values="pct_group_positive",
        aggfunc="first",
    ).reset_index()

    fp_event_type = event_types[event_types["error_group"] == "false_positive"]
    fn_event_type = event_types[event_types["error_group"] == "false_negative"]
    noise_top = label_noise_summary.sort_values("n", ascending=False)

    text = [
        "# 078 Error Analysis and Label Audit",
        "",
        "## Inputs",
        "",
        f"- Dataset: `{args.dataset}`",
        f"- Risk source: `{risk_input.source}`",
        f"- Risk note: {risk_input.note}",
        f"- High-risk threshold: {format_metric(threshold, 6)}",
        f"- High-risk rule: top {format_metric(args.high_risk_top_fraction * 100, 1)}% unless --risk-threshold was supplied",
        f"- Event-time note: {event_time_note}",
        "",
        "## Cohort and Confusion Groups",
        "",
        f"- N = {total}; events = {n_events} ({format_metric(pct(n_events, total), 2)}%).",
        f"- TP = {tp_n}, FP = {fp_n}, FN = {fn_n}, TN = {tn_n}.",
        f"- FP with pre12 shock proxy: {format_metric(fp_pre_shock_pct, 1)}% of false positives.",
        f"- FN with death component: {format_metric(fn_death_pct, 1)}% of false negatives.",
        "",
        to_markdown_safe(confusion),
        "",
        "## Outcome Components by Error Group",
        "",
        to_markdown_safe(component_view, max_rows=20),
        "",
        "## Event Type Composition",
        "",
        "### False Positives",
        "",
        to_markdown_safe(fp_event_type, max_rows=20),
        "",
        "### False Negatives",
        "",
        to_markdown_safe(fn_event_type, max_rows=20),
        "",
        "## Label-Noise / Outcome-Component Review Flags",
        "",
        to_markdown_safe(noise_top, max_rows=20),
        "",
        "## Interpretation Checklist",
        "",
        "- If many false positives have severe pre12 shock proxy but no primary outcome, review whether the outcome is too narrow or whether competing risks/discharge/death censoring are masking clinically severe cases.",
        "- If false negatives are enriched for death-only or very early events, review sudden death, arrhythmia/procedure/surgery/infection-source variables, and whether death is circulatory.",
        "- If false negatives are enriched for support or NEE escalation but lack pre12 signal, prioritize post-landmark medication cleaning and high-value features such as echo/LVEF, BNP/NT-proBNP, troponin, fluid balance, diuretic response, hypotension burden, shock index, lactate clearance, SOFA components, and infection source.",
        "- If FP/FN patterns are heterogeneous across event types and severity variables, consider prespecified subgroup analyses before promoting a more complex model.",
        "",
        "## Data Gaps Found by This Run",
        "",
        *(notes if notes else ["- No major audit input gaps detected."]),
        "",
        "## Output Files",
        "",
        *[f"- `{name}`: `{path}`" for name, path in outputs.items()],
        "",
    ]
    return "\n".join(text)


def run() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dataset = normalize_id_types(read_csv(args.dataset, "modeling dataset"))
    if OUTCOME_COL not in dataset.columns:
        raise ValueError(f"Outcome column not found in dataset: {OUTCOME_COL}")

    if args.prediction_csv:
        pred = read_csv(args.prediction_csv, "prediction csv")
        pred_col = detect_prediction_col(pred, args.prediction_col)
        risk_input = RiskInput(
            frame=pred,
            score_col=pred_col,
            source=str(args.prediction_csv),
            note=f"Risk score column from supplied prediction CSV: {pred_col}",
        )
    else:
        risk_input = find_existing_prediction_file(dataset)
        if risk_input is None and args.reconstruct_risk_score:
            risk_input = build_crossfit_elasticnet_risk(
                dataset,
                n_splits=args.n_splits,
                random_state=args.random_state,
            )
        elif risk_input is None:
            raise ValueError(
                "No patient-level prediction file/column was found. Pass "
                "--prediction-csv and --prediction-col from the selected 075/076 model, "
                "or pass --reconstruct-risk-score for audit-only fallback scores."
            )

    merged = merge_prediction_scores(dataset, risk_input)
    merged, event_time_note = merge_event_time(
        merged,
        event_time_csv=args.event_time_csv,
        event_time_col=args.event_time_col,
    )

    if args.risk_threshold is not None:
        threshold = args.risk_threshold
    else:
        if not (0 < args.high_risk_top_fraction < 1):
            raise ValueError("--high-risk-top-fraction must be between 0 and 1.")
        threshold = float(
            safe_numeric(merged["risk_score"]).quantile(1.0 - args.high_risk_top_fraction)
        )
        if math.isnan(threshold):
            raise ValueError("Could not compute high-risk threshold from risk_score.")

    audited = derive_audit_flags(merged)
    audited["event_type"] = derive_event_type(audited)
    audited = assign_error_groups(audited, threshold)

    confusion = summarize_confusion(audited)
    event_types = summarize_event_types(audited)
    component_summary = summarize_components(audited)
    continuous_summary = summarize_continuous(audited, KEY_CONTINUOUS_COLS)
    binary_summary = summarize_binary(audited, KEY_BINARY_COLS)
    event_time_summary = summarize_event_time(audited)
    risk_deciles = summarize_risk_deciles(audited)
    label_candidates, label_noise_summary = label_noise_candidates(audited)

    patient_cols = [col for col in PATIENT_LIST_COLS if col in audited.columns]
    patient_list = select_existing(
        audited.sort_values(["error_group", "risk_score"], ascending=[True, False]),
        patient_cols,
    )

    outputs: dict[str, Path] = {}
    outputs["patient_list_all"] = args.output_dir / "078_patient_list_all_with_error_group.csv"
    write_csv(patient_list, outputs["patient_list_all"])

    for group in ["false_positive", "false_negative", "true_positive", "true_negative"]:
        path = args.output_dir / f"078_patient_list_{group}.csv"
        write_csv(select_existing(audited[audited["error_group"].eq(group)], patient_cols), path)
        outputs[f"patient_list_{group}"] = path

    top_lists = top_error_lists(audited, args.top_n)
    for name, frame in top_lists.items():
        path = args.output_dir / f"078_{name}.csv"
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
        path = args.output_dir / f"078_{name}.csv"
        write_csv(frame, path)
        outputs[name] = path

    overall_event_time = read_overall_event_time_sql_result()
    if overall_event_time is not None:
        path = args.output_dir / "078_overall_event_time_from_sql_qc.csv"
        write_csv(overall_event_time, path)
        outputs["overall_event_time_from_sql_qc"] = path

    if risk_input.source == "reconstructed_cv":
        risk_path = args.output_dir / "078_reconstructed_cv_risk_scores.csv"
        write_csv(risk_input.frame, risk_path)
        outputs["reconstructed_cv_risk_scores"] = risk_path

    metadata = {
        "dataset": str(args.dataset),
        "n_rows": int(len(audited)),
        "n_events": int(safe_numeric(audited[OUTCOME_COL]).fillna(0).astype(int).sum()),
        "risk_source": risk_input.source,
        "risk_note": risk_input.note,
        "risk_threshold": threshold,
        "high_risk_top_fraction": args.high_risk_top_fraction,
        "risk_threshold_supplied": args.risk_threshold is not None,
        "event_time_note": event_time_note,
        "output_dir": str(args.output_dir),
        "columns_missing_for_post12_nee": bool(audited["post12_nee_max"].isna().all()),
        "columns_missing_for_event_time": bool(audited["event_hour_after_landmark"].isna().all()),
    }
    meta_path = args.output_dir / "078_run_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    outputs["run_metadata"] = meta_path

    report = build_report(
        audited,
        args,
        risk_input,
        event_time_note,
        outputs,
        confusion,
        event_types,
        component_summary,
        binary_summary,
        label_noise_summary,
    )
    report_path = args.output_dir / "078_error_analysis_and_label_audit_report.md"
    report_path.write_text(report, encoding="utf-8")
    outputs["report"] = report_path

    print(f"078 audit complete. Output directory: {args.output_dir}")
    print(f"Report: {report_path}")
    print(f"Risk source: {risk_input.source}")
    print(f"High-risk threshold: {threshold:.6f}")
    return 0


def main() -> None:
    try:
        raise SystemExit(run())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
