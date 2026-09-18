import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from cs_ahf_ml.config import load_config, project_path
from cs_ahf_ml.data import split_columns, drop_high_missing_and_constant

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])
    qc_dir = project_path(cfg, cfg["paths"]["qc_dir"])
    qc_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(raw_path)
    feature_cols, label_col, exclude_cols = split_columns(df, cfg)
    kept_cols, feature_qc = drop_high_missing_and_constant(
        df,
        feature_cols,
        high_missing_threshold=cfg["preprocessing"]["high_missing_threshold"],
        unique_threshold=cfg["preprocessing"]["near_zero_variance_unique_threshold"],
    )

    pd.DataFrame({
        "metric": ["n_rows", "n_columns", "n_events", "event_rate", "n_candidate_features", "n_kept_features"],
        "value": [len(df), df.shape[1], int(df[label_col].sum()), df[label_col].mean(), len(feature_cols), len(kept_cols)]
    }).to_csv(qc_dir / "071_dataset_summary.csv", index=False)

    pd.DataFrame({"excluded_column": exclude_cols}).to_csv(qc_dir / "071_excluded_columns.csv", index=False)
    pd.DataFrame({"kept_feature": kept_cols}).to_csv(qc_dir / "071_kept_features.csv", index=False)
    feature_qc.sort_values(["kept", "missing_pct"], ascending=[True, False]).to_csv(qc_dir / "071_feature_qc.csv", index=False)

    print(f"[OK] rows={len(df)}, events={int(df[label_col].sum())}, event_rate={df[label_col].mean():.4f}")
    print(f"[OK] candidate_features={len(feature_cols)}, kept_features={len(kept_cols)}")
    print(f"[OK] wrote QC outputs to {qc_dir}")

if __name__ == "__main__":
    main()
