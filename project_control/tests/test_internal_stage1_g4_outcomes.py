#!/usr/bin/env python3
"""Tests for the internal DHF Study-1 G4 outcome contract."""

from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control" / "build_internal_stage1_g4_outcomes.py"


def load_module():
    spec = importlib.util.spec_from_file_location("g4_outcomes_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("G4 outcome script cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def order(
    medication: str,
    route: str,
    start: str,
    stop: str,
    *,
    valid: str = "1",
):
    return {
        "medication": medication,
        "route": route,
        "start_time": start,
        "stop_time": stop,
        "valid_order_flag": valid,
        "status": "医嘱停止",
        "source_file": "orders.csv",
        "source_row": "2",
        "order_id": "O1",
    }


def tube(name: str, site: str, start: str, stop: str):
    return {
        "引流管名称": name,
        "部位": site,
        "置管日期": start,
        "拔管日期": stop,
        "生命周期状态": "3",
        "当前状态": "1",
        "source_file": "tube.csv",
        "source_row": "2",
    }


class InternalStage1G4OutcomeTests(unittest.TestCase):
    def test_vasoactive_whitelist_excludes_broad_legacy_matches(self) -> None:
        g4 = load_module()
        self.assertEqual("norepinephrine", g4.map_vasoactive_class("重酒石酸去甲肾上腺素针"))
        self.assertEqual("epinephrine", g4.map_vasoactive_class("肾上腺素针"))
        self.assertEqual("phenylephrine", g4.map_vasoactive_class("去氧肾上腺素针"))
        self.assertEqual("dobutamine", g4.map_vasoactive_class("多巴酚丁胺针"))
        self.assertIsNone(g4.map_vasoactive_class("异丙肾上腺素针"))
        self.assertIsNone(g4.map_vasoactive_class("左西孟旦针"))
        self.assertIsNone(g4.map_vasoactive_class("垂体后叶素针"))

    def test_only_explicit_pump_route_is_continuous_proxy(self) -> None:
        g4 = load_module()
        self.assertEqual("continuous_pump", g4.classify_order_route("静脉注射(泵)"))
        self.assertEqual("continuous_pump", g4.classify_order_route("静脉滴注(泵)"))
        self.assertEqual("ambiguous_iv_drip", g4.classify_order_route("静脉滴注"))
        self.assertEqual("point_or_non_iv", g4.classify_order_route("静脉注射"))
        self.assertEqual("point_or_non_iv", g4.classify_order_route("肌注"))

    def test_new_post_t12_class_for_at_least_60_minutes_is_proxy_event(self) -> None:
        g4 = load_module()
        result = g4.classify_order_proxy_episode(
            [order("去甲肾上腺素针", "静脉注射(泵)", "2026-01-01 13:00:00", "2026-01-01 15:00:00")],
            stamp("2026-01-01 12:00:00"),
            stamp("2026-01-03 12:00:00"),
        )
        self.assertEqual("proxy_event", result["status"])
        self.assertEqual("norepinephrine", result["event_drug_class"])
        self.assertEqual("2026-01-01 13:00:00", result["event_time"])

    def test_same_class_after_t12_with_t12_baseline_is_unknown_intensification(self) -> None:
        g4 = load_module()
        rows = [
            order("去甲肾上腺素针", "静脉注射(泵)", "2026-01-01 10:00:00", "2026-01-01 14:00:00"),
            order("去甲肾上腺素针", "静脉注射(泵)", "2026-01-01 14:10:00", "2026-01-01 16:00:00"),
        ]
        result = g4.classify_order_proxy_episode(
            rows,
            stamp("2026-01-01 12:00:00"),
            stamp("2026-01-03 12:00:00"),
        )
        self.assertEqual("unknown", result["status"])
        self.assertIn("same_class_baseline_intensity_unknown", result["unknown_reasons"])

    def test_missing_stop_or_nonpump_drip_is_unknown_not_negative(self) -> None:
        g4 = load_module()
        rows = [
            order("多巴胺针", "静脉注射(泵)", "2026-01-01 13:00:00", ""),
            order("米力农针", "静脉滴注", "2026-01-01 14:00:00", "2026-01-01 18:00:00"),
        ]
        result = g4.classify_order_proxy_episode(
            rows,
            stamp("2026-01-01 12:00:00"),
            stamp("2026-01-03 12:00:00"),
        )
        self.assertEqual("unknown", result["status"])
        self.assertIn("missing_stop_time", result["unknown_reasons"])
        self.assertIn("ambiguous_iv_drip_route", result["unknown_reasons"])

    def test_iabp_or_paired_ecmo_tubes_support_mcs_proxy_event(self) -> None:
        g4 = load_module()
        t12 = stamp("2026-01-01 12:00:00")
        end = stamp("2026-01-03 12:00:00")
        iabp = g4.classify_mcs_episode(
            [tube("IABP管", "右腹股沟", "2026-01-01 13:00:00", "2026-01-02 12:00:00")],
            t12,
            end,
        )
        self.assertEqual("proxy_event", iabp["status"])
        ecmo = g4.classify_mcs_episode(
            [
                tube("ECMO", "右腹股沟", "2026-01-01 13:00:00", "2026-01-03 00:00:00"),
                tube("ECMO", "左腹股沟", "2026-01-01 14:00:00", "2026-01-03 00:00:00"),
            ],
            t12,
            end,
        )
        self.assertEqual("proxy_event", ecmo["status"])
        self.assertEqual("ECMO_paired_tube_proxy", ecmo["event_component"])

    def test_single_ecmo_tube_is_unknown(self) -> None:
        g4 = load_module()
        result = g4.classify_mcs_episode(
            [tube("ECMO", "右腹股沟", "2026-01-01 13:00:00", "2026-01-02 12:00:00")],
            stamp("2026-01-01 12:00:00"),
            stamp("2026-01-03 12:00:00"),
        )
        self.assertEqual("unknown", result["status"])
        self.assertIn("single_ecmo_tube_without_paired_cannula", result["unknown_reasons"])

    def test_structured_homepage_is_authoritative_for_hospital_disposition(self) -> None:
        g4 = load_module()
        death = g4.classify_hospital_disposition("治疗结果 : 死亡", "2026-01-10 00:00:00")
        alive = g4.classify_hospital_disposition("治疗结果 : 好转", "2026-01-10 00:00:00")
        missing = g4.classify_hospital_disposition("", "")
        self.assertEqual("hospital_death", death["status"])
        self.assertEqual("alive_hospital_discharge", alive["status"])
        self.assertEqual("outcome_unknown", missing["status"])

    def test_homepage_alive_category_updates_are_not_death_endpoint_conflicts(self) -> None:
        g4 = load_module()
        self.assertFalse(g4.has_binary_disposition_conflict({"治疗结果 :", "治疗结果 : 未愈"}))
        self.assertFalse(g4.has_binary_disposition_conflict({"治疗结果 : 好转", "治疗结果 : 未愈"}))
        self.assertTrue(g4.has_binary_disposition_conflict({"治疗结果 : 死亡", "治疗结果 : 好转"}))

    def test_short_outcome_prioritizes_death_then_mcs_then_order(self) -> None:
        g4 = load_module()
        result = g4.classify_short_outcome(
            t12=stamp("2026-01-01 12:00:00"),
            t60=stamp("2026-01-03 12:00:00"),
            icu_outtime=stamp("2026-01-03 12:00:00"),
            icu_death_time=stamp("2026-01-01 13:00:00"),
            order_result={"status": "proxy_event", "event_time": "2026-01-01 13:00:00", "event_component": "order_proxy"},
            mcs_result={"status": "proxy_event", "event_time": "2026-01-01 13:00:00", "event_component": "IABP_tube_proxy"},
        )
        self.assertEqual("target_event", result["final_status"])
        self.assertEqual("ICU_death", result["event_component"])
        self.assertEqual("2026-01-01 13:00:00", result["event_time"])

    def test_unresolved_upgrade_before_exit_is_outcome_unknown(self) -> None:
        g4 = load_module()
        result = g4.classify_short_outcome(
            t12=stamp("2026-01-01 12:00:00"),
            t60=stamp("2026-01-03 12:00:00"),
            icu_outtime=stamp("2026-01-02 12:00:00"),
            icu_death_time=None,
            order_result={"status": "unknown", "unknown_time": "2026-01-01 14:00:00", "unknown_reasons": "missing_stop_time"},
            mcs_result={"status": "none"},
        )
        self.assertEqual("outcome_unknown", result["final_status"])
        self.assertEqual("missing_stop_time", result["unknown_reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
