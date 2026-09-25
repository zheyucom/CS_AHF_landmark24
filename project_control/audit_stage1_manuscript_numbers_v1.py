#!/usr/bin/env python3
"""Check that key Stage 1 numbers in the manuscript match frozen outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript/study1_internal_dhf/MANUSCRIPT_DRAFT_V0_1_20260924.md"
OUT = ROOT / "project_control/runs/20260925_internal_stage1_treatment_proxy/manuscript_number_audit_v1.json"

EXPECTED = {
    "cohort_773": "773",
    "death_62": "62",
    "t12_risk_558": "558",
    "proxy_events_81": "81",
    "competing_150": "150",
    "administrative_273": "273",
    "unknown_54": "54",
    "text_total_766": "766/773",
    "text_clinical_733": "733/773",
    "text_dose_686": "686",
    "text_unambiguous_dose_672": "672",
    "text_rate_199": "199",
    "text_unambiguous_rate_125": "125",
}


def main() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    checks = {name: value in text for name, value in EXPECTED.items()}
    # Ensure the manuscript explicitly disclaims eMAR confirmation.
    checks["proxy_disclaimer_present"] = "不是 eMAR 确认的实际给药发生率" in text and "医嘱区间" in text
    result = {
        "pass": all(checks.values()),
        "checks": checks,
        "expected": EXPECTED,
        "manuscript": str(MANUSCRIPT.relative_to(ROOT)),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
