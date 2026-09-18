#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON="$ROOT/.venv/bin/python"
CONFIG="$ROOT/config/config_v3.yaml"
LOG_DIR="$ROOT/../project_control/runs/20260824_v3_init/model_logs"
EVENT_CSV="$ROOT/data/raw_v3/audit_079_event_timing_components_v3.csv"

mkdir -p "$LOG_DIR"
export MPLBACKEND=Agg

run() {
    name=$1
    shift
    echo "Running $name"
    "$PYTHON" "$@" > "$LOG_DIR/$name.log" 2>&1
}

run 071 scripts/071_data_qc.py --config "$CONFIG"
run 072 scripts/072_train_baseline_models.py --config "$CONFIG"
run 072B scripts/072B_train_stable_model_comparison.py --config "$CONFIG"
run 072C scripts/072C_algorithmic_feature_selection.py --config "$CONFIG"
run 072D scripts/072D_threshold_sensitivity_selected_models.py --config "$CONFIG"
run 073 scripts/073_candidate_model_evaluation.py --config "$CONFIG"
run 073B scripts/073B_calibrate_candidate_models.py --config "$CONFIG"
run 074 scripts/074_train_tree_ml_benchmark.py --config "$CONFIG"
run 075 scripts/075_repeated_internal_validation.py --config "$CONFIG"
run 075B scripts/075B_missing_data_sensitivity.py --config "$CONFIG"
run 076 scripts/076_treatment_support_sensitivity.py --config "$CONFIG"
run 077 scripts/077_finalize_model_feature_dictionary.py --config "$CONFIG"
run 077B scripts/077B_export_active_feature_set.py --config "$CONFIG"
run 078 scripts/078_error_analysis_and_label_audit.py --config "$CONFIG" --event-time-csv "$EVENT_CSV"
run 078A scripts/078A_outcome_definition_sensitivity.py --config "$CONFIG" --event-time-csv "$EVENT_CSV"
