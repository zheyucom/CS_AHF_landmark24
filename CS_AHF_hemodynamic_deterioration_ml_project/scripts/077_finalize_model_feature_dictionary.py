import argparse
from pathlib import Path
import sys
import warnings
import joblib
import re

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
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


def strip_missing_suffix(feature):
    if feature.endswith("__missing"):
        return feature.replace("__missing", "")
    return feature


def infer_aggregation(feature):
    base = strip_missing_suffix(feature)

    suffix_map = {
        "_min": "minimum",
        "_max": "maximum",
        "_mean": "mean",
        "_last": "last",
        "_first": "first",
        "_delta": "change/delta",
        "_flag": "binary flag",
        "_count": "count",
        "_total": "total",
        "_total_ml": "total volume",
        "_rate": "rate",
        "_available_flag": "availability flag",
    }

    if feature.endswith("__missing"):
        return "missing indicator"

    for suffix, label in suffix_map.items():
        if base.endswith(suffix):
            return label

    return "raw/derived value"


def infer_time_window(feature):
    f = strip_missing_suffix(feature)

    if "0_12h" in f or "early12" in f:
        return "ICU admission 0-12 h"
    if "early_sepsis12" in f:
        return "ICU admission 0-12 h"
    if "first_day" in f:
        return "first ICU day"
    if f.startswith("charlson_"):
        return "pre-existing comorbidity"
    if f.startswith("hf_icd") or f.startswith("acute_hf_icd"):
        return "hospital diagnosis evidence"
    if f.startswith("first_unit_"):
        return "ICU admission metadata"
    if "before_icu" in f:
        return "before ICU admission"
    if "icu_6_12h" in f:
        return "ICU 6-12 h"
    return "ICU admission 0-12 h or baseline"


def infer_module(feature):
    f = strip_missing_suffix(feature)

    # Demographics / admission
    if f in {"age", "female", "male"}:
        return "Demographics"

    if f.startswith("first_unit_"):
        return "ICU unit / care process"

    # AHF evidence / diagnosis
    if (
        f.startswith("hf_icd")
        or f.startswith("acute_hf_icd")
        or f.startswith("ahf_evidence")
        or f.startswith("iv_loop")
        or f.startswith("ntprobnp")
    ):
        return "AHF evidence / diagnosis"

    # Sepsis and severity
    if (
        f.startswith("early_sepsis12")
        or f.startswith("sepsis")
        or f.startswith("sirs")
        or f.startswith("sofa")
        or f.startswith("sapsii")
        or f.startswith("apsiii")
        or f.startswith("oasis")
        or f.startswith("lods")
    ):
        return "Sepsis / illness severity"

    if f.startswith("suspected_infection"):
        return "Infection timing / care process"

    # Comorbidities
    if f.startswith("charlson"):
        return "Comorbidities"

    # Vital signs
    vital_prefixes = (
        "sbp_", "dbp_", "mbp_", "hr_", "rr_", "spo2_", "temp_",
        "heart_rate_", "resp_rate_"
    )
    if f.startswith(vital_prefixes):
        return "Vital signs"

    # Perfusion / blood gas / acid-base
    bg_prefixes = (
        "lactate_", "ph_", "baseexcess_", "bicarbonate_", "aniongap_",
        "po2_", "pco2_", "pao2fio2_", "fio2_"
    )
    if f.startswith(bg_prefixes):
        return "Perfusion / blood gas / acid-base"

    # Chemistry / kidney / electrolytes
    chemistry_prefixes = (
        "creatinine_", "bun_", "urea_", "sodium_", "potassium_",
        "chloride_", "calcium_", "magnesium_", "phosphate_", "glucose_",
        "albumin_", "bilirubin_", "ast_", "alt_", "alkalinephosphatase_"
    )
    if f.startswith(chemistry_prefixes):
        return "Chemistry / renal / electrolytes"

    # CBC / hematology
    cbc_prefixes = (
        "wbc_", "hemoglobin_", "hematocrit_", "platelet_", "rdw_",
        "mch_", "mchc_", "mcv_"
    )
    if f.startswith(cbc_prefixes):
        return "Complete blood count"

    # Coagulation
    coag_prefixes = (
        "inr_", "pt_", "ptt_", "fibrinogen_", "d_dimer_", "ddimer_"
    )
    if f.startswith(coag_prefixes):
        return "Coagulation"

    # Urine / kidney support
    if f.startswith("urine") or f.startswith("low_urineoutput"):
        return "Urine output / renal perfusion"

    # Neurologic
    if f.startswith("gcs_"):
        return "Neurologic status"

    # Respiratory support
    if (
        f.startswith("ventilation")
        or f.startswith("oxygen")
        or f.startswith("ventilator")
        or f.startswith("invasive_vent")
        or f.startswith("noninvasive_vent")
    ):
        return "Respiratory support"

    # Circulatory support
    vaso_prefixes = (
        "nee_", "norepinephrine_", "epinephrine_", "dopamine_",
        "phenylephrine_", "vasopressin_", "dobutamine_", "milrinone_",
        "vasopressor_", "inotrope_", "vasoactive_agent_", "vaso_records_"
    )
    if f.startswith(vaso_prefixes):
        return "Vasoactive / inotropic support"

    return "Other"


def is_portability_sensitive(feature):
    f = strip_missing_suffix(feature)
    sensitive_prefixes = (
        "first_unit_",
        "hf_icd_",
        "acute_hf_icd",
        "ahf_evidence",
        "iv_loop",
        "ntprobnp",
        "suspected_infection_",
    )
    return f.startswith(sensitive_prefixes)


def is_treatment_support(feature):
    f = strip_missing_suffix(feature)
    prefixes = (
        "nee_", "norepinephrine_", "epinephrine_", "dopamine_",
        "phenylephrine_", "vasopressin_", "dobutamine_", "milrinone_",
        "vasopressor_", "inotrope_", "vasoactive_agent_", "vaso_records_"
    )
    return f.startswith(prefixes)


def is_outcome_proximal(feature):
    return is_treatment_support(feature)


def infer_external_priority(feature):
    if is_treatment_support(feature):
        return "high - clinically important, but outcome-proximal"
    if is_portability_sensitive(feature):
        return "medium/low - check external database consistency"
    module = infer_module(feature)
    if module in {
        "Vital signs",
        "Perfusion / blood gas / acid-base",
        "Chemistry / renal / electrolytes",
        "Complete blood count",
        "Urine output / renal perfusion",
        "Sepsis / illness severity",
        "Comorbidities",
        "Demographics",
    }:
        return "high"
    return "medium"


def infer_external_source_hint(feature):
    module = infer_module(feature)

    mapping = {
        "Demographics": "ADT / admission registry",
        "ICU unit / care process": "ICU admission table / department metadata",
        "AHF evidence / diagnosis": "diagnosis codes, medication orders, BNP/NT-proBNP labs",
        "Sepsis / illness severity": "derived from vitals/labs/vasopressors/ventilation/renal data",
        "Infection timing / care process": "antibiotic and culture timestamps",
        "Comorbidities": "diagnosis history / discharge diagnosis codes",
        "Vital signs": "ICU flowsheet / vital sign charting",
        "Perfusion / blood gas / acid-base": "blood gas and chemistry laboratory tables",
        "Chemistry / renal / electrolytes": "chemistry laboratory tables",
        "Complete blood count": "hematology laboratory tables",
        "Coagulation": "coagulation laboratory tables",
        "Urine output / renal perfusion": "ICU intake/output records",
        "Neurologic status": "nursing neurological assessment / GCS charting",
        "Respiratory support": "ventilator flowsheet / oxygen therapy records",
        "Vasoactive / inotropic support": "medication infusion records",
    }

    return mapping.get(module, "to be determined")


def infer_unit_hint(feature):
    f = strip_missing_suffix(feature)

    # Binary indicators should be handled before prefix-based unit rules.
    if f.endswith("_flag") or feature.endswith("__missing"):
        return "binary 0/1"

    if f.startswith(("sbp_", "dbp_", "mbp_")):
        return "mmHg"
    if f.startswith("hr_"):
        return "beats/min"
    if f.startswith("rr_"):
        return "breaths/min"
    if f.startswith("spo2_"):
        return "%"
    if f.startswith("temp_"):
        return "degree Celsius"
    if f.startswith("lactate_"):
        return "mmol/L"
    if f.startswith("ph_"):
        return "unitless"
    if f.startswith("aniongap_"):
        return "mEq/L or mmol/L"
    if f.startswith("bicarbonate_"):
        return "mEq/L or mmol/L"
    if f.startswith("creatinine_"):
        return "mg/dL"
    if f.startswith("bun_"):
        return "mg/dL"
    if f.startswith(("sodium_", "potassium_", "chloride_")):
        return "mmol/L"
    if f.startswith("wbc_"):
        return "K/uL or 10^9/L; verify local unit"
    if f.startswith("platelet_"):
        return "K/uL or 10^9/L; verify local unit"
    if f.startswith(("hemoglobin_", "rdw_")):
        return "verify local laboratory unit"
    if f.startswith("inr_"):
        return "unitless"
    if f.startswith("urine") or f.startswith("low_urineoutput"):
        return "mL or mL/kg/h depending on variable"
    if f.startswith("nee_"):
        return "ug/kg/min norepinephrine-equivalent dose"

    return "verify"


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


def load_feature_set(feature_sets_long, feature_set_name, processed_columns):
    sub = feature_sets_long[feature_sets_long["feature_set"] == feature_set_name]
    features = sub.sort_values("rank_in_feature_set")["feature"].tolist()
    features = [f for f in features if f in processed_columns]
    return features


def build_feature_dictionary(features):
    rows = []

    for rank, f in enumerate(features, start=1):
        base = strip_missing_suffix(f)

        rows.append({
            "feature_rank_in_top80": rank,
            "model_feature": f,
            "base_feature": base,
            "module": infer_module(f),
            "aggregation_or_feature_type": infer_aggregation(f),
            "time_window": infer_time_window(f),
            "is_missing_indicator": f.endswith("__missing"),
            "is_available_flag": f.endswith("_available_flag"),
            "is_treatment_support_feature": is_treatment_support(f),
            "is_outcome_proximal_feature": is_outcome_proximal(f),
            "is_portability_sensitive_feature": is_portability_sensitive(f),
            "external_validation_priority": infer_external_priority(f),
            "external_data_source_hint": infer_external_source_hint(f),
            "unit_hint": infer_unit_hint(f),
            "recommended_external_action": "",
            "local_variable_name": "",
            "local_unit": "",
            "local_extraction_rule": "",
            "local_availability": "",
            "notes": "",
        })

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--feature_set", default="top80_compact")
    parser.add_argument("--calibration_folds", type=int, default=3)
    args = parser.parse_args()

    cfg = load_config(args.config)

    table_dir = project_path(cfg, cfg["paths"]["table_dir"])
    model_dir = project_path(cfg, cfg["paths"]["model_dir"])
    raw_path = project_path(cfg, cfg["paths"]["raw_dataset"])
    feature_sets_path = table_dir / "072D_feature_sets_long.csv"

    for d in [table_dir, model_dir]:
        d.mkdir(parents=True, exist_ok=True)

    if not feature_sets_path.exists():
        raise FileNotFoundError("072D_feature_sets_long.csv not found. Please run 072D first.")

    df = pd.read_csv(raw_path)
    feature_sets_long = pd.read_csv(feature_sets_path)

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
    processed_columns = list(X_train_all.columns)

    selected_features = load_feature_set(
        feature_sets_long,
        args.feature_set,
        processed_columns,
    )

    if len(selected_features) == 0:
        raise RuntimeError(f"No features found for feature set: {args.feature_set}")

    X_train = X_train_all[selected_features].copy()
    X_test = X_test_all[selected_features].copy()

    model = make_model(cfg["random_seed"])
    model.fit(X_train, y_train)

    calibrator = crossfit_platt_calibrator(
        X_train,
        y_train,
        seed=cfg["random_seed"],
        n_splits=args.calibration_folds,
    )

    coef = model.named_steps["clf"].coef_.ravel()

    coef_df = pd.DataFrame({
        "model_feature": selected_features,
        "standardized_coef": coef,
        "abs_standardized_coef": np.abs(coef),
        "direction": np.where(coef > 0, "higher value -> higher predicted risk",
                              np.where(coef < 0, "higher value -> lower predicted risk", "zero")),
    })

    coef_df = coef_df.sort_values(
        "abs_standardized_coef",
        ascending=False,
    ).reset_index(drop=True)

    coef_df.insert(0, "coef_rank", np.arange(1, len(coef_df) + 1))

    feature_dict = build_feature_dictionary(selected_features)

    feature_dict = feature_dict.merge(
        coef_df[[
            "coef_rank",
            "model_feature",
            "standardized_coef",
            "abs_standardized_coef",
            "direction",
        ]],
        on="model_feature",
        how="left",
    )

    feature_dict = feature_dict.sort_values("feature_rank_in_top80").reset_index(drop=True)

    feature_dict.to_csv(
        table_dir / "077_final_model_feature_dictionary.csv",
        index=False,
    )

    coef_df = coef_df.merge(
        feature_dict[[
            "model_feature",
            "base_feature",
            "module",
            "aggregation_or_feature_type",
            "time_window",
            "is_treatment_support_feature",
            "is_portability_sensitive_feature",
            "external_validation_priority",
            "unit_hint",
        ]],
        on="model_feature",
        how="left",
    )

    coef_df.to_csv(
        table_dir / "077_final_model_coefficients.csv",
        index=False,
    )

    module_summary = feature_dict.groupby("module").agg(
        n_features=("model_feature", "count"),
        n_treatment_support=("is_treatment_support_feature", "sum"),
        n_portability_sensitive=("is_portability_sensitive_feature", "sum"),
        n_missing_indicators=("is_missing_indicator", "sum"),
        n_available_flags=("is_available_flag", "sum"),
    ).reset_index().sort_values("n_features", ascending=False)

    module_summary.to_csv(
        table_dir / "077_final_model_modules_summary.csv",
        index=False,
    )

    external_mapping = feature_dict[[
        "feature_rank_in_top80",
        "model_feature",
        "base_feature",
        "module",
        "aggregation_or_feature_type",
        "time_window",
        "external_validation_priority",
        "external_data_source_hint",
        "unit_hint",
        "is_treatment_support_feature",
        "is_outcome_proximal_feature",
        "is_portability_sensitive_feature",
        "recommended_external_action",
        "local_variable_name",
        "local_unit",
        "local_extraction_rule",
        "local_availability",
        "notes",
    ]].copy()

    external_mapping.to_csv(
        table_dir / "077_external_validation_variable_mapping_template.csv",
        index=False,
    )

    model_summary = pd.DataFrame([{
        "feature_set": args.feature_set,
        "n_total_rows": len(df),
        "n_train": len(train_df),
        "n_test": len(test_df),
        "n_events_total": int(df[label_col].sum()),
        "n_events_train": int(y_train.sum()),
        "n_events_test": int(y_test.sum()),
        "n_selected_features": len(selected_features),
        "base_model": "elasticnet logistic regression",
        "base_model_C": 0.02,
        "base_model_l1_ratio": 0.5,
        "class_weight": "balanced",
        "calibration": "cross-fitted Platt scaling",
        "calibration_folds": args.calibration_folds,
        "note": "Coefficients are standardized coefficients from the base elastic-net model before Platt calibration. They are for relative importance and direction, not causal interpretation.",
    }])

    model_summary.to_csv(
        table_dir / "077_final_model_summary.csv",
        index=False,
    )

    joblib.dump(
        {
            "model": model,
            "calibrator": calibrator,
            "features": selected_features,
            "prep_stats": prep_stats,
            "config": cfg,
            "feature_dictionary": feature_dict,
        },
        model_dir / "077_final_top80_elasticnet_platt_train_split.joblib",
    )

    print("[OK] 077 final model feature dictionary complete")
    print(f"[OK] selected features: {len(selected_features)}")
    print("[OK] wrote:")
    print(f"  {table_dir / '077_final_model_feature_dictionary.csv'}")
    print(f"  {table_dir / '077_final_model_coefficients.csv'}")
    print(f"  {table_dir / '077_final_model_modules_summary.csv'}")
    print(f"  {table_dir / '077_external_validation_variable_mapping_template.csv'}")
    print(f"  {table_dir / '077_final_model_summary.csv'}")


if __name__ == "__main__":
    main()
