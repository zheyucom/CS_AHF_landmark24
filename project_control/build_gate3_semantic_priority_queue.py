#!/usr/bin/env python3
"""Create a focused clinician queue from the 50-case Gate-3 pre-review.

The queue contains only cases where DHF semantic evidence is uncertain,
missing, or requires confirmation of an alternative explanation. T0 and ICU
episode facts already adjudicated by the user are retained as context but are
not re-requested.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "project_control/internal_validation/20260912"
INFILE = BASE / "internal_gate3_manual_review_50_20260913_reviewed.csv"
OUTFILE = BASE / "internal_gate3_semantic_priority_queue_20260913.csv"


def main() -> None:
    df = pd.read_csv(INFILE, dtype=str, encoding="utf-8-sig").fillna("")
    uncertain = (
        df["hf_anchor_support_final"].isin(["unknown", "uncertain"])
        | df["decompensation_domain_final"].isin(["unknown", "uncertain"])
        | df["management_evidence_final"].isin(["unknown", "uncertain"])
        | df["dhf_tier_final"].isin(["unknown", "echo_supported_draft"])
    )
    q = df.loc[uncertain].copy()
    def reason(row):
        parts = []
        if row.hf_anchor_support_final in ("unknown", "uncertain"):
            parts.append(f"HF锚点={row.hf_anchor_support_final}")
        if row.decompensation_domain_final in ("unknown", "uncertain"):
            parts.append(f"失代偿={row.decompensation_domain_final}")
        if row.management_evidence_final in ("unknown", "uncertain"):
            parts.append(f"管理强化={row.management_evidence_final}")
        if row.dhf_tier_final in ("unknown", "echo_supported_draft"):
            parts.append(f"综合层级={row.dhf_tier_final}")
        return "；".join(parts)
    q["priority_reason"] = q.apply(reason, axis=1)
    q["review_focus"] = q.apply(
        lambda r: "核对T12前文书/SOAP/检验/影像中的明确充血或失代偿证据，排除感染、出血、术后等替代解释；确认管理强化是否实际发生",
        axis=1,
    )
    cols = [
        "review_id", "patient_id", "sex", "visit_id", "t0_time_final",
        "t0_source_final", "report_time", "finding", "conclusion",
        "echo_report_validity", "echo_abnormal_domains",
        "hf_anchor_support_final", "decompensation_domain_final",
        "management_evidence_final", "dhf_tier_final", "outcome_status_final",
        "priority_reason", "review_focus", "review_comments",
    ]
    q[cols].sort_values(["dhf_tier_final", "review_id"]).to_csv(
        OUTFILE, index=False, encoding="utf-8-sig"
    )
    print(f"wrote {OUTFILE} rows {len(q)}")


if __name__ == "__main__":
    main()
