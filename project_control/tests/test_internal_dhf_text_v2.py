"""Tests for the V2 current-HF text semantic bridge.

The bridge may promote a tentative HF mention only when a nearby,
current-context HF judgment is linked to HF-directed treatment.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control" / "build_internal_stage1_g3_text_v2.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dhf_text_v2_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("V2 text script cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TextSemanticV2Tests(unittest.TestCase):
    def test_same_sentence_tentative_hf_plus_loop_treatment_promotes(self):
        mod = load_module()
        results = mod.analyze_hf_text("目前考虑急性心衰，予静脉呋塞米利尿治疗。")
        self.assertTrue(any(r["status"] == "affirmed_with_treatment_support" for r in results))

    def test_adjacent_sentence_tentative_hf_plus_treatment_promotes(self):
        mod = load_module()
        results = mod.analyze_hf_text("目前考虑心功能不全。予托拉塞米静脉利尿。")
        self.assertTrue(any(r["status"] == "affirmed_with_treatment_support" for r in results))

    def test_tentative_hf_without_specific_treatment_stays_uncertain(self):
        mod = load_module()
        results = mod.analyze_hf_text("考虑心衰可能，建议进一步完善心超检查。")
        self.assertTrue(any(r["status"] == "uncertain" for r in results))
        self.assertFalse(any(r["status"] == "affirmed_with_treatment_support" for r in results))

    def test_differential_diagnosis_is_not_promoted(self):
        mod = load_module()
        results = mod.analyze_hf_text("鉴别诊断：心衰；目前实际按肺炎予抗感染治疗。")
        self.assertFalse(any(r["status"] == "affirmed_with_treatment_support" for r in results))

    def test_risk_warning_is_not_promoted(self):
        mod = load_module()
        results = mod.analyze_hf_text("警惕发生心衰，必要时予利尿治疗。")
        self.assertFalse(any(r["status"] == "affirmed_with_treatment_support" for r in results))

    def test_historical_hf_is_not_promoted(self):
        mod = load_module()
        results = mod.analyze_hf_text("既往心衰，目前予抗感染治疗。")
        self.assertFalse(any(r["status"] == "affirmed_with_treatment_support" for r in results))

    def test_same_paragraph_far_link_is_review_only(self):
        mod = load_module()
        results = mod.analyze_hf_text("目前考虑心衰。完善检查。调整呼吸支持。随后予呋塞米利尿。")
        self.assertTrue(any(r["status"] == "probable_current_hf" for r in results))
        self.assertFalse(any(r["status"] == "affirmed_with_treatment_support" for r in results))

    def test_antibiotic_does_not_support_hf(self):
        mod = load_module()
        results = mod.analyze_hf_text("目前考虑心衰，予头孢抗感染治疗。")
        self.assertFalse(any(r["status"] == "affirmed_with_treatment_support" for r in results))


    def test_low_probability_hf_is_not_promoted(self):
        mod = load_module()
        results = mod.analyze_hf_text("心源性休克可能性小；暂予多巴胺维持血压。")
        self.assertFalse(any(r["status"] == "affirmed_with_treatment_support" for r in results))

    def test_conditional_treatment_is_not_promoted(self):
        mod = load_module()
        results = mod.analyze_hf_text("BNP偏高提示心衰可能。建议注意出入量平衡，必要时利尿强心。")
        self.assertFalse(any(r["status"] == "affirmed_with_treatment_support" for r in results))

    def test_question_mark_hf_is_not_promoted(self):
        mod = load_module()
        results = mod.analyze_hf_text("心功能不全？建议继续利尿治疗。")
        self.assertFalse(any(r["status"] == "affirmed_with_treatment_support" for r in results))

if __name__ == "__main__":
    unittest.main(verbosity=2)
