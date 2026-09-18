from __future__ import annotations

import re
from pathlib import Path
import numpy as np
import pandas as pd

def get_exclusion_columns(df: pd.DataFrame, cfg: dict) -> list[str]:
    id_cols = cfg["columns"]["id_cols"]
    label_prefixes = cfg["columns"]["label_prefixes"]
    forced_exclude = cfg["columns"]["forced_exclude"]
    exclude = set(id_cols + forced_exclude)

    for col in df.columns:
        if any(col.startswith(prefix) for prefix in label_prefixes):
            exclude.add(col)

    # Safety net: do not allow obvious outcome/follow-up columns into predictors.
    leakage_patterns = [
        r"post12", r"death_12_60", r"complete60", r"followup",
        r"observed_until", r"window60_time", r"landmark12_time",
        r"outcome", r"secondary", r"label_"
    ]
    for col in df.columns:
        low = col.lower()
        if any(re.search(p, low) for p in leakage_patterns):
            exclude.add(col)
    return sorted([c for c in exclude if c in df.columns])

def split_columns(df: pd.DataFrame, cfg: dict) -> tuple[list[str], str, list[str]]:
    label_col = cfg["target"]["label_col"]
    exclude = get_exclusion_columns(df, cfg)
    feature_cols = [c for c in df.columns if c not in exclude]
    feature_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    return feature_cols, label_col, exclude

def drop_high_missing_and_constant(
    df: pd.DataFrame,
    feature_cols: list[str],
    high_missing_threshold: float = 0.80,
    unique_threshold: int = 1,
) -> tuple[list[str], pd.DataFrame]:
    rows = []
    kept = []
    for col in feature_cols:
        miss = df[col].isna().mean()
        nunique = df[col].nunique(dropna=True)
        drop_reason = ""
        if miss > high_missing_threshold:
            drop_reason = f"missing>{high_missing_threshold}"
        elif nunique <= unique_threshold:
            drop_reason = f"nunique<={unique_threshold}"
        else:
            kept.append(col)

        rows.append({
            "column": col,
            "missing_pct": miss * 100,
            "nunique": nunique,
            "kept": col in kept,
            "drop_reason": drop_reason,
        })
    return kept, pd.DataFrame(rows)

def build_preprocess_frame(
    df: pd.DataFrame,
    feature_cols: list[str],
    cfg: dict,
    fit_stats: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    X = df[feature_cols].copy()
    stats = {} if fit_stats is None else fit_stats.copy()

    # For exposure/dose variables where missing means no exposure, fill with zero.
    if cfg["preprocessing"].get("nee_missing_fill_zero", True):
        nee_cols = [c for c in X.columns if c.startswith("nee_") or c.endswith("_0_12h_max")]
        for c in nee_cols:
            if c in X.columns:
                X[c] = X[c].fillna(0)

    if cfg["preprocessing"].get("keep_missing_indicators", True):
        for c in list(X.columns):
            if X[c].isna().any():
                X[f"{c}__missing"] = X[c].isna().astype(int)

    # Winsorize numeric columns. Fit thresholds on training only when fit_stats is None.
    if cfg["preprocessing"]["winsorize"]["enabled"]:
        lq = cfg["preprocessing"]["winsorize"]["lower_q"]
        uq = cfg["preprocessing"]["winsorize"]["upper_q"]
        for c in X.columns:
            if not pd.api.types.is_numeric_dtype(X[c]):
                continue
            key = f"winsor::{c}"
            if fit_stats is None:
                lo, hi = X[c].quantile([lq, uq])
                stats[key] = (float(lo) if pd.notna(lo) else np.nan, float(hi) if pd.notna(hi) else np.nan)
            else:
                lo, hi = stats.get(key, (np.nan, np.nan))
            if pd.notna(lo) and pd.notna(hi):
                X[c] = X[c].clip(lo, hi)

    # Median imputation. Fit medians on training only when fit_stats is None.
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

    return X, stats
