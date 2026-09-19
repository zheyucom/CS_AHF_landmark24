#!/usr/bin/env python3
"""Statically audit MIMIC-IV SQL and exercise synthetic lab row contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_RULE_PACK = Path(__file__).resolve().parents[1] / "references" / "mimic-iv-lab-rules.json"


def _finding(code: str, severity: str, message: str, action: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message, "action": action}


def _strip_sql_comments(sql: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\r\n]*", " ", without_blocks)


def audit_sql(sql: str, rule_pack: dict[str, Any]) -> list[dict[str, str]]:
    """Return deterministic static findings without executing or rewriting SQL."""
    normalized = re.sub(r"\s+", " ", _strip_sql_comments(sql).lower()).strip()
    findings: list[dict[str, str]] = []
    uses_labevents = bool(re.search(r"\b(?:from|join)\s+(?:[\w`]+\.)?labevents\b", normalized))
    uses_fuzzy_label = bool(
        re.search(r"(?:regexp_contains|regexp_like|like)\s*\([^)]*(?:label|fluid|category)", normalized)
        or re.search(r"(?:label|fluid|category)[^;]{0,100}\blike\b", normalized)
    )

    if uses_labevents and uses_fuzzy_label:
        findings.append(
            _finding(
                "MIMIC001",
                "error",
                "名称或元数据模糊匹配被用于实验室纳入。",
                "名称正则只能发现候选；正式特征必须使用已批准的精确 itemid 合同。",
            )
        )

    quarantine_ids: dict[int, str] = {}
    allowed_ids: set[int] = set()
    for rule in rule_pack.get("rules", []):
        if rule.get("status") != "active":
            continue
        allowed_ids.update(entry["itemid"] for entry in rule.get("allow", []) if isinstance(entry.get("itemid"), int))
        for entry in rule.get("quarantine", []):
            if isinstance(entry.get("itemid"), int):
                quarantine_ids[entry["itemid"]] = entry.get("reason_code", "quarantined_itemid")

    referenced_ids = {int(value) for value in re.findall(r"(?<![\w.])(\d{5})(?!\w)", normalized)}
    blocked = sorted(referenced_ids & set(quarantine_ids))
    has_explicit_quarantine = all(
        token in normalized
        for token in ("known_quarantine", "quarantine_reason", "approved_contract")
    )
    has_quarantine_contract = (
        "lab_quarantine_item_v1" in normalized
        and "known_quarantine_reason" in normalized
        and "quarantine_reason" in normalized
    )
    if uses_labevents and blocked and not (has_explicit_quarantine or has_quarantine_contract):
        findings.append(
            _finding(
                "MIMIC002",
                "error",
                f"查询包含已隔离的实验室 itemid：{blocked}。",
                "从特征纳入集合移除这些 itemid，并在 quarantine 中按 reason code 汇总。",
            )
        )

    availability_pattern = re.compile(
        r"greatest\s*\(\s*(?:\w+\.)?charttime\s*,\s*coalesce\s*\(\s*(?:\w+\.)?storetime\s*,\s*(?:\w+\.)?charttime\s*\)\s*\)"
    )
    if uses_labevents and "charttime" in normalized and not availability_pattern.search(normalized):
        findings.append(
            _finding(
                "MIMIC003",
                "error",
                "实验室时间窗没有使用结果最早可用时间。",
                "使用 GREATEST(charttime, COALESCE(storetime, charttime)) 与 landmark 比较，并保留原时间字段。",
            )
        )

    if uses_labevents and not re.search(r"\bvalueuom\b|\bunitname\b", normalized):
        findings.append(
            _finding(
                "MIMIC004",
                "warning",
                "查询未见单位字段或单位合同。",
                "保留 valueuom，并按规则包 allowlist 验证；未知单位进入 quarantine。",
            )
        )

    if re.search(r"coalesce\s*\(\s*(?:\w+\.)?(?:valuenum|value)\s*,\s*0(?:\.0+)?\s*\)", normalized):
        findings.append(
            _finding(
                "MIMIC005",
                "error",
                "实验室缺失值被补为 0。",
                "保留缺失状态；区分未测、连接失败、超窗和 derived 漏失。",
            )
        )

    if uses_labevents and "specimen_id" not in normalized:
        findings.append(
            _finding(
                "MIMIC006",
                "warning",
                "查询未保留 specimen_id，无法可靠检查同一标本重复。",
                "保留 specimen_id，并在聚合前审计 specimen_id × itemid 重复。",
            )
        )

    has_derived = bool(re.search(r"\bmimiciv_derived(?:\.|\b)", normalized))
    has_lab_contract = bool(re.search(r"\b(?:lab_eligible_v1|lab_event_classified_v1)\b", normalized))
    if uses_labevents and not has_derived:
        findings.append(
            _finding(
                "MIMIC007",
                "warning",
                "当前 SQL 未展示 raw↔derived 双向覆盖对账。",
                "核心变量另行输出 raw-only、derived-only 和 both；不要把 derived 当作无条件真值。",
            )
        )
    if has_derived and not uses_labevents and not has_lab_contract and re.search(r"\b(?:from|join)\b", normalized):
        findings.append(
            _finding(
                "MIMIC009",
                "error",
                "查询把 mimiciv_derived 作为唯一实验室来源。",
                "derived 只能用于双向覆盖对账；正式 raw 特征必须从批准的 raw 表读取。",
            )
        )

    if uses_labevents and uses_fuzzy_label and not (referenced_ids & allowed_ids):
        findings.append(
            _finding(
                "MIMIC008",
                "error",
                "模糊候选查询未包含任何已批准的精确 itemid。",
                "先登记 sourced/fixture-tested 规则并经人工批准，再用于正式特征。",
            )
        )

    return findings


def _parse_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _match_rule(rule_pack: dict[str, Any], concept: str) -> dict[str, Any]:
    matches = [
        rule
        for rule in rule_pack.get("rules", [])
        if rule.get("concept", "").casefold() == concept.casefold() and rule.get("status") == "active"
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one active rule for concept {concept!r}, found {len(matches)}")
    return matches[0]


def _quarantine(row: dict[str, Any], reason_code: str) -> dict[str, Any]:
    return {"row": dict(row), "reason_code": reason_code}


_NUMERIC_BOUNDARY = re.compile(r"^\s*(<=|>=|<|>)\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*$")
_INTERVAL_VALUE = re.compile(
    r"^\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)\s*(?:-|to)\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)\s*$",
    re.IGNORECASE,
)


def classify_lab_rows(
    rows: Iterable[dict[str, Any]],
    concept: str,
    landmark: datetime,
    rule_pack: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Classify synthetic/authorized rows without silently changing raw values."""
    rule = _match_rule(rule_pack, concept)
    allow_by_itemid = {entry["itemid"]: entry for entry in rule["allow"]}
    blocked_by_itemid = {entry["itemid"]: entry["reason_code"] for entry in rule.get("quarantine", [])}
    accepted: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any]] = set()

    for original in rows:
        row = dict(original)
        itemid = row.get("itemid")
        contract = allow_by_itemid.get(itemid)
        if contract is None:
            quarantine.append(_quarantine(row, blocked_by_itemid.get(itemid, "unregistered_itemid")))
            continue

        if row.get("specimen_id") in (None, ""):
            quarantine.append(_quarantine(row, "missing_specimen_id"))
            continue
        if str(row.get("fluid", "")).casefold() != contract["fluid"].casefold():
            quarantine.append(_quarantine(row, "fluid_mismatch"))
            continue
        if str(row.get("category", "")).casefold() != contract["category"].casefold():
            quarantine.append(_quarantine(row, "category_mismatch"))
            continue
        allowed_units = {unit.casefold() for unit in contract["units"]}
        if str(row.get("valueuom", "")).casefold() not in allowed_units:
            quarantine.append(_quarantine(row, "unknown_unit"))
            continue

        charttime = _parse_time(row.get("charttime"))
        storetime = _parse_time(row.get("storetime"))
        if charttime is None:
            quarantine.append(_quarantine(row, "missing_charttime"))
            continue
        if storetime is not None and storetime < charttime:
            quarantine.append(_quarantine(row, "storetime_before_charttime"))
            continue
        availability_time = max(charttime, storetime or charttime)
        if availability_time >= landmark:
            quarantine.append(_quarantine(row, "available_after_landmark"))
            continue

        raw_value = row.get("value")
        if raw_value in (None, ""):
            quarantine.append(_quarantine(row, "missing_value"))
            continue
        censor_match = _NUMERIC_BOUNDARY.match(str(raw_value))
        if _INTERVAL_VALUE.match(str(raw_value)):
            quarantine.append(_quarantine(row, "interval_value"))
            continue

        key = (row.get("specimen_id"), itemid)
        if key in seen:
            quarantine.append(_quarantine(row, "duplicate_specimen_itemid"))
            continue
        seen.add(key)

        accepted_row = dict(row)
        accepted_row["availability_time"] = availability_time.isoformat()
        accepted_row["raw_value"] = raw_value
        accepted_row["censor_type"] = censor_match.group(1) if censor_match else None
        accepted_row["raw_boundary"] = censor_match.group(2) if censor_match else None
        accepted.append(accepted_row)

    return {"accepted": accepted, "quarantine": quarantine}


def reconcile_keys(raw_keys: Iterable[Any], derived_keys: Iterable[Any]) -> dict[str, list[Any]]:
    raw = set(raw_keys)
    derived = set(derived_keys)
    sort_key = lambda value: str(value)
    return {
        "raw_only": sorted(raw - derived, key=sort_key),
        "derived_only": sorted(derived - raw, key=sort_key),
        "both": sorted(raw & derived, key=sort_key),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql_file", type=Path)
    parser.add_argument("--rule-pack", type=Path, default=DEFAULT_RULE_PACK)
    parser.add_argument("--json", dest="json_output", type=Path)
    args = parser.parse_args(argv)

    try:
        sql = args.sql_file.read_text(encoding="utf-8")
        rule_pack = json.loads(args.rule_pack.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read input: {exc}", file=sys.stderr)
        return 2

    findings = audit_sql(sql, rule_pack)
    if args.json_output:
        args.json_output.write_text(json.dumps(findings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if findings:
        for item in findings:
            print(f"[{item['severity'].upper()}] {item['code']}: {item['message']}")
            print(f"  ACTION: {item['action']}")
    else:
        print("OK: no static findings")
    return 1 if any(item["severity"] == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
