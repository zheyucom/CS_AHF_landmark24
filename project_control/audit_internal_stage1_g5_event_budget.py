#!/usr/bin/env python3
"""Apply the pre-specified Study-1 G5 event-budget gate.

This script does not fit any association or prediction model.  It translates
the G4 endpoint counts into the maximum permitted effective degrees of freedom
and stops analyses that are either underpowered or not formally frozen.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "project_control"
RUN_ID = "20260924_internal_stage1_g5_event_budget"
OUT = CONTROL / "runs" / RUN_ID
G4_QC = CONTROL / "runs/20260924_internal_stage1_g4_outcomes/qc.json"
G4_FLOW = CONTROL / "runs/20260924_internal_stage1_g4_outcomes/outcome_flow_counts.csv"
SAP = CONTROL / "STATISTICAL_ANALYSIS_PLAN_INTERNAL_DHF_STUDY1_V1.md"


def effective_df_cap(events: int):
    return min(10, max(0, int(events) // 15))


def assess_endpoint(*, endpoint, events, endpoint_frozen, minimum_adjusted_df=3):
    cap = effective_df_cap(events)
    if not endpoint_frozen:
        allowed = False
        scope = "endpoint_not_frozen_no_formal_model"
    elif cap < minimum_adjusted_df:
        allowed = False
        scope = "descriptive_and_pre_specified_crude_only"
    else:
        allowed = True
        scope = "adjusted_association_within_df_cap"
    return {
        "endpoint": endpoint,
        "events": int(events),
        "endpoint_frozen": bool(endpoint_frozen),
        "events_per_effective_df": 15,
        "effective_df_cap": cap,
        "minimum_adjusted_df": int(minimum_adjusted_df),
        "adjusted_multivariable_allowed": allowed,
        "analysis_scope": scope,
    }


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    qc = json.loads(G4_QC.read_text(encoding="utf-8"))
    endpoints = [
        {
            **assess_endpoint(
                endpoint="strict_T12_hospital_death",
                events=qc["strict_T12_hospital_death_n"],
                endpoint_frozen=qc["hospital_disposition_frozen_for_G5_event_budget"],
            ),
            "population_role": "current_authorized_primary_association_population",
            "formal_use": "primary_endpoint_event_budget",
        },
        {
            **assess_endpoint(
                endpoint="overall_phenotype_hospital_death_context_only",
                events=qc["main_hospital_death_n"],
                endpoint_frozen=qc["hospital_disposition_frozen_for_G5_event_budget"],
            ),
            "population_role": "overall_burden_population_not_current_association_population",
            "formal_use": "context_only_requires_protocol_amendment_before_model",
        },
        {
            **assess_endpoint(
                endpoint="short_execution_level_composite",
                events=qc["short_target_event_proxy_n"],
                endpoint_frozen=qc["short_execution_level_outcome_frozen"],
            ),
            "population_role": "strict_T12_short_window",
            "formal_use": "blocked_execution_level_endpoint_not_available",
        },
    ]
    write_csv(
        OUT / "event_budget_v1.csv",
        endpoints,
        [
            "endpoint", "events", "endpoint_frozen", "events_per_effective_df", "effective_df_cap",
            "minimum_adjusted_df", "adjusted_multivariable_allowed", "analysis_scope",
            "population_role", "formal_use",
        ],
    )

    primary = endpoints[0]
    decision = {
        "run_id": RUN_ID,
        "status": "STOP_ADJUSTED_T12_DEATH_MODEL_DF_LT_3",
        "strict_T12_deaths": primary["events"],
        "strict_T12_effective_df_cap": primary["effective_df_cap"],
        "adjusted_multivariable_death_association_allowed": primary["adjusted_multivariable_allowed"],
        "permitted_without_protocol_change": [
            "descriptive hospital-death burden",
            "pre-specified one-factor crude associations with multiplicity and uncertainty disclosed",
            "phenotype, care-pathway, missingness, and outcome-observability analyses",
        ],
        "not_permitted_without_protocol_change": [
            "adjusted multivariable T12 hospital-death association model",
            "stepwise or univariable-P-value predictor selection",
            "formal model using the local 48-hour composite as if eMAR-confirmed",
            "switching to the 773-person overall cohort after viewing results without an explicit protocol amendment",
        ],
        "decision_required_before_G7": (
            "retain the approved T12 design as descriptive/crude-only, or prospectively amend the association question "
            "to an overall T0 cohort using baseline-only factors; do not choose based on which model looks better"
        ),
        "models_run": False,
        "raw_data_modified": False,
    }
    (OUT / "gate_decision.json").write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")
    snapshot = {
        "run_id": RUN_ID,
        "generated_at": datetime.now().astimezone().isoformat(),
        "inputs": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in (G4_QC, G4_FLOW, SAP)
        ],
    }
    (OUT / "input_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "run_id": RUN_ID,
        "status": decision["status"],
        "strict_T12_deaths": primary["events"],
        "strict_T12_effective_df_cap": primary["effective_df_cap"],
        "models_run": False,
        "out": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
