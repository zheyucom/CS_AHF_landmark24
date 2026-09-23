#!/usr/bin/env python3
"""Build the internal DHF Study-1 G4 outcome audit.

The structured inpatient homepage is authoritative for terminal hospital
disposition.  The 48-hour ICU deterioration outcome is reconstructed in a
separate proxy layer because the local export has order intervals and tube
records, but no eMAR, pump rate, NEE, or administration-level record.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "project_control"
RUN_ID = "20260924_internal_stage1_g4_outcomes"
OUT = CONTROL / "runs" / RUN_ID

G3 = CONTROL / "runs/20260924_internal_stage1_g3_phenotype/dhf_abc_evidence_ledger_v1.csv"
G2 = CONTROL / "runs/20260924_internal_stage1_g2_chronology/episode_chronology_reconciled.csv"
TARGETED_ORDERS = CONTROL / "internal_validation/20260916_semantic_corrected/treatment_orders_targeted.csv"
SAP = CONTROL / "STATISTICAL_ANALYSIS_PLAN_INTERNAL_DHF_STUDY1_V1.md"
PHENOTYPE_CONTRACT = CONTROL / "INTERNAL_DHF_PHENOTYPE_CONTRACT_V1.md"
ORDER_PROXY_SPEC = CONTROL / "ORDER_PROXY_CLASSIFICATION_SPEC_V1.md"

MIN_PROXY_DURATION = timedelta(minutes=60)
MAX_MERGE_GAP = timedelta(minutes=15)


def read_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def iter_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        yield from csv.DictReader(handle)


def write_csv(path: Path, rows, fields=None):
    rows = list(rows)
    if not rows and not fields:
        raise ValueError(f"cannot infer fields for empty output: {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_dt(value):
    if isinstance(value, datetime):
        return value
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def fmt_dt(value):
    value = parse_dt(value)
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def is_true(value):
    return str(value).strip().lower() in {"1", "true", "yes"}


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_ref(row):
    path = row.get("source_file", "")
    number = row.get("source_row", "")
    return f"{path}#row={number}" if path else ""


def map_vasoactive_class(medication: str):
    """Map only the frozen seven-class MIMIC-aligned whitelist."""
    name = str(medication or "")
    if "异丙肾上腺素" in name or "左西孟旦" in name or "垂体后叶" in name:
        return None
    if "去甲肾上腺素" in name:
        return "norepinephrine"
    if "去氧肾上腺素" in name:
        return "phenylephrine"
    if "肾上腺素" in name:
        return "epinephrine"
    if "多巴酚丁胺" in name:
        return "dobutamine"
    if "多巴胺" in name:
        return "dopamine"
    if "米力农" in name:
        return "milrinone"
    if "血管加压素" in name or ("加压素" in name and "垂体后叶" not in name):
        return "vasopressin"
    return None


def classify_order_route(route: str):
    route = str(route or "").strip()
    if "静脉" in route and "泵" in route:
        return "continuous_pump"
    if route == "静脉滴注":
        return "ambiguous_iv_drip"
    return "point_or_non_iv"


def merge_intervals(intervals):
    intervals = sorted((start, stop) for start, stop in intervals if start and stop and stop > start)
    merged = []
    for start, stop in intervals:
        if merged and start <= merged[-1][1] + MAX_MERGE_GAP:
            merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
        else:
            merged.append((start, stop))
    return merged


def classify_order_proxy_episode(order_rows, t12, observation_end):
    t12 = parse_dt(t12)
    observation_end = parse_dt(observation_end)
    if not t12 or not observation_end or observation_end <= t12:
        return {
            "status": "unknown",
            "unknown_time": fmt_dt(t12),
            "unknown_reasons": ["invalid_observation_window"],
            "atomic_rows": [],
        }

    baseline_classes = set()
    post_intervals = defaultdict(list)
    unknown_items = []
    atomic_rows = []

    for row in order_rows:
        drug_class = map_vasoactive_class(row.get("medication", ""))
        route_class = classify_order_route(row.get("route", ""))
        start = parse_dt(row.get("start_time", ""))
        stop = parse_dt(row.get("stop_time", ""))
        valid = is_true(row.get("valid_order_flag", "1"))
        baseline_flag = False
        post_flag = False
        candidate_status = "outside_contract"

        if not valid:
            candidate_status = "invalid_or_cancelled_order"
        elif not drug_class:
            candidate_status = "not_in_frozen_whitelist"
        elif not start:
            candidate_status = "missing_start_time_unknown"
            unknown_items.append((t12, "missing_start_time", drug_class))
        else:
            baseline_flag = bool(
                route_class == "continuous_pump"
                and start < t12
                and (stop is None or stop > t12)
            )
            if baseline_flag:
                baseline_classes.add(drug_class)
                candidate_status = "active_order_proxy_at_T12"

            post_flag = t12 <= start < observation_end
            if post_flag and route_class == "continuous_pump":
                if stop is None:
                    candidate_status = "post_T12_missing_stop_unknown"
                    unknown_items.append((start, "missing_stop_time", drug_class))
                elif stop <= start:
                    candidate_status = "nonpositive_interval_unknown"
                    unknown_items.append((start, "nonpositive_order_interval", drug_class))
                else:
                    candidate_status = "post_T12_continuous_order_interval"
                    post_intervals[drug_class].append((start, min(stop, observation_end)))
            elif post_flag and route_class == "ambiguous_iv_drip":
                candidate_status = "post_T12_ambiguous_iv_drip_unknown"
                unknown_items.append((start, "ambiguous_iv_drip_route", drug_class))
            elif post_flag:
                candidate_status = "post_T12_point_or_non_iv_not_continuous"

        atomic_rows.append({
            "order_id": row.get("order_id", ""),
            "medication": row.get("medication", ""),
            "drug_class": drug_class or "not_whitelisted",
            "route": row.get("route", ""),
            "route_class": route_class,
            "status": row.get("status", ""),
            "start_time": fmt_dt(start),
            "stop_time": fmt_dt(stop),
            "valid_order_flag": int(valid),
            "baseline_at_T12_flag": int(baseline_flag),
            "post_T12_before_observation_end_flag": int(post_flag),
            "candidate_status": candidate_status,
            "source_ref": source_ref(row),
        })

    event_items = []
    for drug_class, intervals in post_intervals.items():
        for start, stop in merge_intervals(intervals):
            if stop - start < MIN_PROXY_DURATION:
                continue
            if drug_class in baseline_classes:
                unknown_items.append((start, "same_class_baseline_intensity_unknown", drug_class))
            else:
                event_items.append((start, drug_class))

    event_items.sort(key=lambda item: (item[0], item[1]))
    unknown_items.sort(key=lambda item: (item[0], item[1], item[2]))
    result = {
        "status": "none",
        "event_time": "",
        "event_component": "",
        "event_drug_class": "",
        "baseline_drug_classes": sorted(baseline_classes),
        "unknown_time": fmt_dt(unknown_items[0][0]) if unknown_items else "",
        "unknown_reasons": sorted({item[1] for item in unknown_items}),
        "earlier_unknown_before_confirmed_event_flag": 0,
        "atomic_rows": atomic_rows,
    }
    if event_items:
        result.update({
            "status": "proxy_event",
            "event_time": fmt_dt(event_items[0][0]),
            "event_component": "vasoactive_or_inotrope_new_class_order_proxy",
            "event_drug_class": event_items[0][1],
            "earlier_unknown_before_confirmed_event_flag": int(
                bool(unknown_items and unknown_items[0][0] < event_items[0][0])
            ),
        })
    elif unknown_items:
        result["status"] = "unknown"
    return result


def mcs_device_class(name: str):
    name = str(name or "")
    if re.search(r"IABP|主动脉.*球囊", name, re.I):
        return "IABP"
    if re.search(r"Impella", name, re.I):
        return "Impella"
    if re.search(r"ECMO|体外膜肺|叶克膜", name, re.I):
        return "ECMO"
    return None


def intervals_overlap(a_start, a_stop, b_start, b_stop, observation_end):
    a_stop = a_stop or observation_end
    b_stop = b_stop or observation_end
    return max(a_start, b_start) < min(a_stop, b_stop)


def classify_mcs_episode(tube_rows, t12, observation_end):
    t12 = parse_dt(t12)
    observation_end = parse_dt(observation_end)
    atomic_rows = []
    relevant = []
    unknown_items = []
    if not t12 or not observation_end or observation_end <= t12:
        return {
            "status": "unknown",
            "unknown_time": fmt_dt(t12),
            "unknown_reasons": ["invalid_observation_window"],
            "atomic_rows": [],
        }

    for row in tube_rows:
        device = mcs_device_class(row.get("引流管名称", ""))
        if not device:
            continue
        start = parse_dt(row.get("置管日期", ""))
        stop = parse_dt(row.get("拔管日期", ""))
        status = "outside_outcome_window"
        if not start:
            status = "missing_placement_time_unknown"
            unknown_items.append((t12, "missing_mcs_placement_time", device))
        elif start < observation_end and (stop is None or stop > t12):
            status = "MCS_record_overlaps_outcome_window"
            relevant.append((device, start, stop, row.get("部位", ""), row))
        atomic_rows.append({
            "device_class": device,
            "device_name": row.get("引流管名称", ""),
            "site": row.get("部位", ""),
            "placement_time": fmt_dt(start),
            "removal_time": fmt_dt(stop),
            "lifecycle_status": row.get("生命周期状态", ""),
            "current_status": row.get("当前状态", ""),
            "candidate_status": status,
            "source_ref": source_ref(row),
        })

    event_items = []
    for device, start, _stop, _site, _row in relevant:
        if device in {"IABP", "Impella"} and t12 <= start < observation_end:
            event_items.append((start, f"{device}_tube_proxy"))

    ecmo = [item for item in relevant if item[0] == "ECMO"]
    paired_indexes = set()
    for i, left in enumerate(ecmo):
        for j in range(i + 1, len(ecmo)):
            right = ecmo[j]
            distinct_site = bool(left[3] and right[3] and left[3] != right[3])
            if not distinct_site:
                continue
            if intervals_overlap(left[1], left[2], right[1], right[2], observation_end):
                pair_time = max(left[1], right[1])
                if t12 <= pair_time < observation_end:
                    event_items.append((pair_time, "ECMO_paired_tube_proxy"))
                    paired_indexes.update({i, j})

    for i, item in enumerate(ecmo):
        if i not in paired_indexes and t12 <= item[1] < observation_end:
            unknown_items.append((item[1], "single_ecmo_tube_without_paired_cannula", "ECMO"))

    event_items.sort(key=lambda item: (item[0], item[1]))
    unknown_items.sort(key=lambda item: (item[0], item[1]))
    result = {
        "status": "none",
        "event_time": "",
        "event_component": "",
        "unknown_time": fmt_dt(unknown_items[0][0]) if unknown_items else "",
        "unknown_reasons": sorted({item[1] for item in unknown_items}),
        "atomic_rows": atomic_rows,
    }
    if event_items:
        result.update({
            "status": "proxy_event",
            "event_time": fmt_dt(event_items[0][0]),
            "event_component": event_items[0][1],
        })
    elif unknown_items:
        result["status"] = "unknown"
    return result


def classify_hospital_disposition(disposition: str, discharge_date: str):
    disposition = str(disposition or "").strip()
    discharge_date = str(discharge_date or "").strip()
    if "死亡" in disposition:
        return {"status": "hospital_death", "reason": "structured_homepage_death"}
    if discharge_date and any(label in disposition for label in ("好转", "治愈", "未愈", "其他")):
        reason = "structured_homepage_non_death_discharge"
        if "其他" in disposition:
            reason = "structured_homepage_other_non_death_discharge"
        return {"status": "alive_hospital_discharge", "reason": reason}
    return {"status": "outcome_unknown", "reason": "missing_or_unmapped_structured_disposition"}


def has_binary_disposition_conflict(outcomes):
    """Detect death/non-death disagreement, ignoring updates among alive labels."""
    binary = set()
    for outcome in outcomes:
        outcome = str(outcome or "")
        if "死亡" in outcome:
            binary.add("death")
        elif any(label in outcome for label in ("好转", "治愈", "未愈", "其他")):
            binary.add("alive")
    return binary == {"death", "alive"}


def result_unknown_item(result):
    if result.get("status") != "unknown":
        return None
    when = parse_dt(result.get("unknown_time", ""))
    reasons = result.get("unknown_reasons", [])
    if isinstance(reasons, str):
        reason = reasons
    else:
        reason = "|".join(reasons)
    return when, reason


def classify_short_outcome(
    *,
    t12,
    t60,
    icu_outtime,
    icu_death_time,
    order_result,
    mcs_result,
):
    t12 = parse_dt(t12)
    t60 = parse_dt(t60)
    out = parse_dt(icu_outtime)
    death = parse_dt(icu_death_time)
    if not t12 or not t60 or not out or out <= t12:
        return {
            "final_status": "outcome_unknown",
            "event_time": "",
            "event_component": "",
            "unknown_reason": "invalid_or_missing_T12_T60_ICU_outtime",
        }
    observation_end = min(t60, out)
    candidates = []
    if death and t12 <= death < t60 and death <= out:
        candidates.append((death, 0, "ICU_death"))
    for result, priority in ((mcs_result, 1), (order_result, 2)):
        event_time = parse_dt(result.get("event_time", ""))
        if result.get("status") == "proxy_event" and event_time and t12 <= event_time < observation_end:
            candidates.append((event_time, priority, result.get("event_component", "proxy_event")))

    if candidates:
        event_time, _priority, component = min(candidates, key=lambda item: (item[0], item[1]))
        return {
            "final_status": "target_event",
            "event_time": fmt_dt(event_time),
            "event_component": component,
            "unknown_reason": "",
        }

    unknown_items = [item for item in (result_unknown_item(order_result), result_unknown_item(mcs_result)) if item]
    unknown_items = [item for item in unknown_items if item[0] and t12 <= item[0] < observation_end]
    if unknown_items:
        unknown_time, reason = min(unknown_items, key=lambda item: item[0])
        return {
            "final_status": "outcome_unknown",
            "event_time": fmt_dt(unknown_time),
            "event_component": "",
            "unknown_reason": reason,
        }

    if out < t60:
        return {
            "final_status": "competing_event",
            "event_time": fmt_dt(out),
            "event_component": "alive_index_ICU_exit",
            "unknown_reason": "",
        }
    return {
        "final_status": "administrative_censor",
        "event_time": fmt_dt(t60),
        "event_component": "T60_no_observed_proxy_event",
        "unknown_reason": "",
    }


def load_homepage_rows(target_visit_ids):
    by_visit = defaultdict(list)
    files = sorted(ROOT.glob("DHF_SRR/*/02_rdr_emr_inp_homepage.csv"))
    for path in files:
        for row_number, row in enumerate(iter_csv(path), 2):
            visit_id = row.get("就诊号", "")
            if visit_id not in target_visit_ids:
                continue
            row = dict(row)
            row["source_file"] = str(path.relative_to(ROOT))
            row["source_row"] = row_number
            by_visit[visit_id].append(row)

    selected = {}
    conflicts = {}
    raw_version_changes = {}
    for visit_id, rows in by_visit.items():
        outcomes = {row.get("转归情况", "").strip() for row in rows if row.get("转归情况", "").strip()}
        if has_binary_disposition_conflict(outcomes):
            conflicts[visit_id] = sorted(outcomes)
        if len(outcomes) > 1:
            raw_version_changes[visit_id] = sorted(outcomes)
        selected[visit_id] = max(rows, key=lambda row: parse_dt(row.get("更新时间", "")) or datetime.min)
    return selected, conflicts, raw_version_changes, files


def load_tube_rows(target_visit_ids):
    by_visit = defaultdict(list)
    coverage = set()
    files = sorted(ROOT.glob("DHF_SRR/*/02_rdr_tube.csv"))
    for path in files:
        for row_number, row in enumerate(iter_csv(path), 2):
            visit_id = row.get("就诊号", "")
            if visit_id not in target_visit_ids:
                continue
            coverage.add(visit_id)
            row = dict(row)
            row["source_file"] = str(path.relative_to(ROOT))
            row["source_row"] = row_number
            by_visit[visit_id].append(row)
    return by_visit, coverage, files


def audit_raw_order_coverage(target_visit_ids):
    coverage = set()
    files = sorted(ROOT.glob("DHF_SRR/*/02_rdr_orders.csv"))
    for path in files:
        for row in iter_csv(path):
            visit_id = row.get("就诊号", "")
            if visit_id in target_visit_ids:
                coverage.add(visit_id)
    return coverage, files


def build_outputs():
    OUT.mkdir(parents=True, exist_ok=True)
    g3_rows = read_csv(G3)
    chronology = {row["visit_id"]: row for row in read_csv(G2)}
    if len(g3_rows) != 8385 or len(chronology) != 8385:
        raise ValueError("G3 and G2 must each contain the locked 8,385-row source frame")

    main_rows = [row for row in g3_rows if is_true(row.get("main_rule_supported_flag"))]
    strict_rows = [row for row in g3_rows if is_true(row.get("main_strict_t12_riskset_flag"))]
    main_ids = {row["visit_id"] for row in main_rows}
    strict_ids = {row["visit_id"] for row in strict_rows}
    if len(main_ids) != 773 or len(strict_ids) != 558:
        raise ValueError(f"unexpected locked G3 sizes: main={len(main_ids)} strict={len(strict_ids)}")

    homepage, homepage_conflicts, homepage_raw_changes, homepage_files = load_homepage_rows(main_ids)
    if set(homepage) != main_ids:
        raise ValueError(f"structured homepage missing for {len(main_ids - set(homepage))} main phenotype visits")

    orders_by_visit = defaultdict(list)
    for row in read_csv(TARGETED_ORDERS):
        if row.get("visit_id") in strict_ids and row.get("drug_group") == "vasoactive":
            orders_by_visit[row["visit_id"]].append(row)

    tube_by_visit, tube_coverage, tube_files = load_tube_rows(strict_ids)
    raw_order_coverage, raw_order_files = audit_raw_order_coverage(strict_ids)

    hospital_ledger = []
    for row in sorted(main_rows, key=lambda item: item["visit_id"]):
        visit_id = row["visit_id"]
        home = homepage[visit_id]
        timeline = chronology[visit_id]
        outcome = classify_hospital_disposition(home.get("转归情况", ""), home.get("出院日期", ""))
        exact_death = timeline.get("hospital_death_time", "") if outcome["status"] == "hospital_death" else ""
        hospital_ledger.append({
            "patient_id": row.get("patient_id", ""),
            "visit_id": visit_id,
            "algorithmic_phenotype_label": row.get("algorithmic_label_v1", ""),
            "strict_T12_riskset_flag": row.get("main_strict_t12_riskset_flag", "0"),
            "t0_time": timeline.get("t0_time", ""),
            "t12_time": timeline.get("t12_time", ""),
            "structured_admit_date": home.get("入院日期", ""),
            "structured_discharge_date": home.get("出院日期", ""),
            "structured_disposition_raw": home.get("转归情况", ""),
            "hospital_outcome_status": outcome["status"],
            "hospital_outcome_reason": outcome["reason"],
            "exact_death_time_if_available": exact_death,
            "death_time_exact_flag": int(bool(exact_death)),
            "index_icu_outtime": timeline.get("index_icu_outtime", ""),
            "death_after_index_icu_exit_flag": int(bool(
                exact_death
                and parse_dt(timeline.get("index_icu_outtime", ""))
                and parse_dt(exact_death) > parse_dt(timeline.get("index_icu_outtime", ""))
            )),
            "calendar_2024_incomplete_flag": row.get("calendar_2024_incomplete_flag", "0"),
            "homepage_source_ref": source_ref(home),
            "homepage_duplicate_conflict_flag": int(visit_id in homepage_conflicts),
            "homepage_raw_version_change_flag": int(visit_id in homepage_raw_changes),
            "interpretation": "structured terminal hospital disposition; not a prediction-model label",
        })

    short_ledger = []
    order_atomic = []
    mcs_atomic = []
    for row in sorted(strict_rows, key=lambda item: item["visit_id"]):
        visit_id = row["visit_id"]
        timeline = chronology[visit_id]
        t12 = parse_dt(timeline.get("t12_time", ""))
        t60 = parse_dt(timeline.get("t60_time", ""))
        out = parse_dt(timeline.get("index_icu_outtime", ""))
        observation_end = min(t60, out) if t60 and out else None

        order_result = classify_order_proxy_episode(orders_by_visit.get(visit_id, []), t12, observation_end)
        mcs_result = classify_mcs_episode(tube_by_visit.get(visit_id, []), t12, observation_end)
        home = homepage[visit_id]
        hospital_outcome = classify_hospital_disposition(home.get("转归情况", ""), home.get("出院日期", ""))
        exact_death = timeline.get("hospital_death_time", "") if hospital_outcome["status"] == "hospital_death" else ""
        short = classify_short_outcome(
            t12=t12,
            t60=t60,
            icu_outtime=out,
            icu_death_time=exact_death,
            order_result=order_result,
            mcs_result=mcs_result,
        )

        for atomic in order_result.get("atomic_rows", []):
            order_atomic.append({"patient_id": row.get("patient_id", ""), "visit_id": visit_id, **atomic})
        for atomic in mcs_result.get("atomic_rows", []):
            mcs_atomic.append({"patient_id": row.get("patient_id", ""), "visit_id": visit_id, **atomic})

        short_ledger.append({
            "patient_id": row.get("patient_id", ""),
            "visit_id": visit_id,
            "t12_time": fmt_dt(t12),
            "t60_time": fmt_dt(t60),
            "index_icu_outtime": fmt_dt(out),
            "observation_end": fmt_dt(observation_end),
            "hospital_outcome_status": hospital_outcome["status"],
            "hospital_death_time": exact_death,
            "icu_death_in_window_flag": int(short["event_component"] == "ICU_death"),
            "order_proxy_status": order_result.get("status", "none"),
            "order_proxy_event_time": order_result.get("event_time", ""),
            "order_proxy_event_drug_class": order_result.get("event_drug_class", ""),
            "order_proxy_baseline_classes": "|".join(order_result.get("baseline_drug_classes", [])),
            "order_proxy_unknown_reasons": "|".join(order_result.get("unknown_reasons", [])),
            "order_proxy_earlier_unknown_flag": order_result.get("earlier_unknown_before_confirmed_event_flag", 0),
            "mcs_proxy_status": mcs_result.get("status", "none"),
            "mcs_proxy_event_time": mcs_result.get("event_time", ""),
            "mcs_proxy_event_component": mcs_result.get("event_component", ""),
            "mcs_proxy_unknown_reasons": "|".join(mcs_result.get("unknown_reasons", [])),
            "short_outcome_status": short["final_status"],
            "short_outcome_time": short["event_time"],
            "short_outcome_component": short["event_component"],
            "short_outcome_unknown_reason": short["unknown_reason"],
            "raw_order_source_present_flag": int(visit_id in raw_order_coverage),
            "raw_tube_source_present_flag": int(visit_id in tube_coverage),
            "calendar_2024_incomplete_flag": row.get("calendar_2024_incomplete_flag", "0"),
            "interpretation": "48-hour local order/tube proxy layer; not eMAR-confirmed execution",
        })

    write_csv(OUT / "hospital_disposition_ledger_v1.csv", hospital_ledger)
    write_csv(OUT / "t12_short_outcome_proxy_ledger_v1.csv", short_ledger)
    write_csv(
        OUT / "vasoactive_order_proxy_atomic_v1.csv",
        order_atomic,
        [
            "patient_id", "visit_id", "order_id", "medication", "drug_class", "route", "route_class",
            "status", "start_time", "stop_time", "valid_order_flag", "baseline_at_T12_flag",
            "post_T12_before_observation_end_flag", "candidate_status", "source_ref",
        ],
    )
    write_csv(
        OUT / "mcs_tube_proxy_atomic_v1.csv",
        mcs_atomic,
        [
            "patient_id", "visit_id", "device_class", "device_name", "site", "placement_time",
            "removal_time", "lifecycle_status", "current_status", "candidate_status", "source_ref",
        ],
    )

    hospital_counts = Counter(row["hospital_outcome_status"] for row in hospital_ledger)
    strict_hospital_counts = Counter(
        row["hospital_outcome_status"] for row in hospital_ledger if is_true(row["strict_T12_riskset_flag"])
    )
    short_counts = Counter(row["short_outcome_status"] for row in short_ledger)
    component_counts = Counter(
        row["short_outcome_component"] or "none" for row in short_ledger
        if row["short_outcome_status"] == "target_event"
    )
    flow_rows = []
    for domain, counts in (
        ("main_phenotype_hospital_disposition", hospital_counts),
        ("strict_T12_hospital_disposition", strict_hospital_counts),
        ("strict_T12_short_proxy_outcome", short_counts),
        ("strict_T12_target_component", component_counts),
    ):
        for status, count in sorted(counts.items()):
            flow_rows.append({"domain": domain, "status": status, "n": count})
    write_csv(OUT / "outcome_flow_counts.csv", flow_rows, ["domain", "status", "n"])

    observability = [
        {"domain": "main_phenotype", "measure": "algorithmic_rule_supported_n", "n": len(main_rows), "interpretation": "clinical calibration pending"},
        {"domain": "hospital_disposition", "measure": "structured_homepage_covered_n", "n": len(homepage), "interpretation": "all main phenotype visits"},
        {"domain": "hospital_disposition", "measure": "structured_homepage_binary_conflict_n", "n": len(homepage_conflicts), "interpretation": "death versus non-death conflicts fail QC"},
        {"domain": "hospital_disposition", "measure": "structured_homepage_raw_version_change_n", "n": len(homepage_raw_changes), "interpretation": "blank/alive-category updates retained; latest row selected"},
        {"domain": "strict_T12", "measure": "strict_riskset_n", "n": len(strict_rows), "interpretation": "direct ICU presence layer"},
        {"domain": "strict_T12", "measure": "raw_order_source_covered_n", "n": len(raw_order_coverage), "interpretation": "coverage does not equal eMAR execution"},
        {"domain": "strict_T12", "measure": "raw_tube_source_covered_n", "n": len(tube_coverage), "interpretation": "zero-row visits remain source-covered"},
        {"domain": "short_outcome", "measure": "eMAR_available_n", "n": 0, "interpretation": "order proxy only"},
        {"domain": "short_outcome", "measure": "pump_rate_or_NEE_available_n", "n": 0, "interpretation": "same-class intensification cannot be resolved"},
        {"domain": "short_outcome", "measure": "ICU_death_in_T12_T60_n", "n": sum(row["icu_death_in_window_flag"] for row in short_ledger), "interpretation": "exact death before index ICU exit"},
    ]
    write_csv(OUT / "outcome_observability_summary.csv", observability, ["domain", "measure", "n", "interpretation"])

    snapshot_paths = [G3, G2, TARGETED_ORDERS, SAP, PHENOTYPE_CONTRACT, ORDER_PROXY_SPEC, *homepage_files, *tube_files]
    snapshot = {
        "run_id": RUN_ID,
        "generated_at": datetime.now().astimezone().isoformat(),
        "inputs": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in snapshot_paths
        ],
        "coverage_only_inputs": [
            {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size}
            for path in raw_order_files
        ],
    }
    (OUT / "input_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    qc = {
        "run_id": RUN_ID,
        "status": "PASS_PRIMARY_HOSPITAL_DISPOSITION_SHORT_OUTCOME_PROXY_ONLY",
        "main_algorithmic_phenotype_n": len(main_rows),
        "strict_T12_riskset_n": len(strict_rows),
        "main_hospital_death_n": hospital_counts.get("hospital_death", 0),
        "main_alive_hospital_discharge_n": hospital_counts.get("alive_hospital_discharge", 0),
        "main_hospital_outcome_unknown_n": hospital_counts.get("outcome_unknown", 0),
        "strict_T12_hospital_death_n": strict_hospital_counts.get("hospital_death", 0),
        "strict_T12_alive_hospital_discharge_n": strict_hospital_counts.get("alive_hospital_discharge", 0),
        "strict_T12_hospital_outcome_unknown_n": strict_hospital_counts.get("outcome_unknown", 0),
        "structured_homepage_conflict_n": len(homepage_conflicts),
        "structured_homepage_raw_version_change_n": len(homepage_raw_changes),
        "raw_order_source_coverage_n": len(raw_order_coverage),
        "raw_tube_source_coverage_n": len(tube_coverage),
        "short_target_event_proxy_n": short_counts.get("target_event", 0),
        "short_competing_event_n": short_counts.get("competing_event", 0),
        "short_administrative_censor_n": short_counts.get("administrative_censor", 0),
        "short_outcome_unknown_n": short_counts.get("outcome_unknown", 0),
        "short_ICU_death_n": component_counts.get("ICU_death", 0),
        "short_order_proxy_event_n": component_counts.get("vasoactive_or_inotrope_new_class_order_proxy", 0),
        "short_IABP_proxy_event_n": component_counts.get("IABP_tube_proxy", 0),
        "short_ECMO_paired_proxy_event_n": component_counts.get("ECMO_paired_tube_proxy", 0),
        "eMAR_available": False,
        "pump_rate_or_NEE_available": False,
        "hospital_disposition_frozen_for_G5_event_budget": True,
        "short_execution_level_outcome_frozen": False,
        "short_order_tube_proxy_layer_frozen": True,
        "clinical_phenotype_calibration_completed": False,
        "model_run": False,
        "raw_data_modified": False,
        "next_gate": "G5_event_budget_for_hospital_death; short composite remains proxy sensitivity until execution-level data are available",
    }
    if len(hospital_ledger) != 773 or len(short_ledger) != 558:
        raise ValueError("outcome ledgers do not preserve locked cohort sizes")
    if sum(short_counts.values()) != 558:
        raise ValueError("short outcome states do not sum to strict T12 risk set")
    if len(raw_order_coverage) != 558 or len(tube_coverage) != 558:
        raise ValueError("strict T12 source coverage is incomplete")
    if homepage_conflicts or hospital_counts.get("outcome_unknown", 0):
        raise ValueError("structured hospital disposition is not fully resolved")
    (OUT / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    return qc


def main():
    qc = build_outputs()
    print(json.dumps({
        "run_id": RUN_ID,
        "status": qc["status"],
        "main_algorithmic_phenotype_n": qc["main_algorithmic_phenotype_n"],
        "strict_T12_riskset_n": qc["strict_T12_riskset_n"],
        "strict_T12_hospital_death_n": qc["strict_T12_hospital_death_n"],
        "short_target_event_proxy_n": qc["short_target_event_proxy_n"],
        "short_outcome_unknown_n": qc["short_outcome_unknown_n"],
        "out": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
