from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
)

def binary_metrics(y_true, y_prob, threshold=0.5) -> dict:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    return {
        "n": int(len(y_true)),
        "events": int(y_true.sum()),
        "event_rate": float(y_true.mean()),
        "auroc": float(roc_auc_score(y_true, y_prob)),
        "auprc": float(average_precision_score(y_true, y_prob)),
        "brier": float(brier_score_loss(y_true, y_prob)),
        "threshold": threshold,
        "sensitivity": float(tp / (tp + fn)) if (tp + fn) else np.nan,
        "specificity": float(tn / (tn + fp)) if (tn + fp) else np.nan,
        "ppv": float(tp / (tp + fp)) if (tp + fp) else np.nan,
        "npv": float(tn / (tn + fn)) if (tn + fn) else np.nan,
    }

def calibration_table(y_true, y_prob, n_bins=10) -> pd.DataFrame:
    df = pd.DataFrame({"y": y_true, "p": y_prob})
    df["bin"] = pd.qcut(df["p"], q=n_bins, duplicates="drop")
    out = df.groupby("bin", observed=True).agg(
        n=("y", "size"),
        mean_pred=("p", "mean"),
        obs_rate=("y", "mean"),
        events=("y", "sum"),
    ).reset_index()
    return out
