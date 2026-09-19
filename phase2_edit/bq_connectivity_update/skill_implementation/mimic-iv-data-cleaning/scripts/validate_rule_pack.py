#!/usr/bin/env python3
"""Validate the declarative MIMIC-IV cleaning rule pack.

The validator is intentionally dependency-free and fail-closed. It checks the
shape and governance of rules; it does not claim that a MIMIC table was
successfully queried or that a rule is clinically correct.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
_ALLOWED_STATUSES = {"proposed", "active", "deprecated"}
_REQUIRED_RULE_FIELDS = {
    "rule_id",
    "concept",
    "status",
    "mimic_versions",
    "source_table",
    "allow",
    "quarantine",
    "time_contract",
    "handling",
    "evidence_sources",
    "test_ids",
}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_rule_pack(pack: dict[str, Any]) -> list[str]:
    """Return deterministic validation errors; an empty list means valid."""
    errors: list[str] = []
    if not isinstance(pack, dict):
        return ["rule pack must be a JSON object"]

    if not _VERSION_RE.fullmatch(str(pack.get("schema_version", ""))):
        errors.append("schema_version must use semantic version form X.Y.Z")

    dataset = pack.get("dataset")
    if not isinstance(dataset, dict):
        errors.append("dataset must be an object")
        dataset = {}
    if dataset.get("name") != "MIMIC-IV":
        errors.append("dataset.name must be MIMIC-IV")
    versions = dataset.get("supported_versions")
    if not isinstance(versions, list) or not versions or not all(_is_nonempty_string(v) for v in versions):
        errors.append("dataset.supported_versions must be a non-empty string list")

    governance = pack.get("governance", {})
    if not isinstance(governance, dict):
        errors.append("governance must be an object")
        governance = {}
    if governance.get("active_requires_human_approval") is not True:
        errors.append("governance.active_requires_human_approval must be true")
    statuses = set(governance.get("allowed_statuses", []))
    if statuses and not _ALLOWED_STATUSES.issubset(statuses):
        errors.append("governance.allowed_statuses must include proposed, active, and deprecated")

    rules = pack.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("rules must be a non-empty list")
        return errors

    rule_ids: set[str] = set()
    active_concepts: set[str] = set()
    for index, rule in enumerate(rules):
        prefix = f"rules[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{prefix} must be an object")
            continue

        missing = sorted(_REQUIRED_RULE_FIELDS - set(rule))
        errors.extend(f"{prefix} missing {field}" for field in missing)

        rule_id = rule.get("rule_id")
        if not _is_nonempty_string(rule_id):
            errors.append(f"{prefix}.rule_id must be a non-empty string")
        elif rule_id in rule_ids:
            errors.append(f"duplicate rule_id: {rule_id}")
        else:
            rule_ids.add(rule_id)

        concept = rule.get("concept")
        if not _is_nonempty_string(concept):
            errors.append(f"{prefix}.concept must be a non-empty string")
        status = rule.get("status")
        if status not in _ALLOWED_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(_ALLOWED_STATUSES)}")
        if status == "active" and concept in active_concepts:
            errors.append(f"duplicate active concept: {concept}")
        if status == "active" and _is_nonempty_string(concept):
            active_concepts.add(concept)

        mimic_versions = rule.get("mimic_versions")
        if not isinstance(mimic_versions, list) or not mimic_versions:
            errors.append(f"{prefix}.mimic_versions must be a non-empty list")
        if not _is_nonempty_string(rule.get("source_table")):
            errors.append(f"{prefix}.source_table must be a table name")

        allow = rule.get("allow")
        quarantine = rule.get("quarantine")
        if not isinstance(allow, list) or not allow:
            errors.append(f"{prefix}.allow must be a non-empty list")
            allow = []
        if not isinstance(quarantine, list):
            errors.append(f"{prefix}.quarantine must be a list")
            quarantine = []

        allow_ids: set[int] = set()
        for item_index, entry in enumerate(allow):
            entry_prefix = f"{prefix}.allow[{item_index}]"
            if not isinstance(entry, dict):
                errors.append(f"{entry_prefix} must be an object")
                continue
            itemid = entry.get("itemid")
            if not isinstance(itemid, int) or isinstance(itemid, bool) or itemid <= 0:
                errors.append(f"{entry_prefix}.itemid must be a positive integer")
            elif itemid in allow_ids:
                errors.append(f"duplicate allow itemid {itemid} in {prefix}")
            else:
                allow_ids.add(itemid)
            for field in ("fluid", "category"):
                if not _is_nonempty_string(entry.get(field)):
                    errors.append(f"{entry_prefix}.{field} must be a non-empty string")
            units = entry.get("units")
            if not isinstance(units, list) or not units or not all(_is_nonempty_string(unit) for unit in units):
                errors.append(f"{entry_prefix}.units must be a non-empty string list")

        quarantine_ids: set[int] = set()
        for item_index, entry in enumerate(quarantine):
            entry_prefix = f"{prefix}.quarantine[{item_index}]"
            if not isinstance(entry, dict):
                errors.append(f"{entry_prefix} must be an object")
                continue
            itemid = entry.get("itemid")
            if not isinstance(itemid, int) or isinstance(itemid, bool) or itemid <= 0:
                errors.append(f"{entry_prefix}.itemid must be a positive integer")
            elif itemid in quarantine_ids:
                errors.append(f"duplicate quarantine itemid {itemid} in {prefix}")
            else:
                quarantine_ids.add(itemid)
            if not _is_nonempty_string(entry.get("reason_code")):
                errors.append(f"{entry_prefix}.reason_code must be a non-empty string")

        overlap = sorted(allow_ids & quarantine_ids)
        if overlap:
            errors.append(f"{prefix} allow/quarantine itemid overlap: {overlap}")

        time_contract = rule.get("time_contract")
        if not isinstance(time_contract, dict):
            errors.append(f"{prefix}.time_contract must be an object")
        else:
            expression = re.sub(r"\s+", " ", str(time_contract.get("availability_expression", "")).strip()).upper()
            expected = "GREATEST(CHARTTIME, COALESCE(STORETIME, CHARTTIME))"
            if expression != expected:
                errors.append(f"{prefix}.time_contract.availability_expression must be {expected}")
            if time_contract.get("window_end_operator") != "<":
                errors.append(f"{prefix}.time_contract.window_end_operator must be '<'")
            if time_contract.get("storetime_null_fallback") != "charttime":
                errors.append(f"{prefix}.time_contract.storetime_null_fallback must be charttime")

        handling = rule.get("handling")
        if not isinstance(handling, dict):
            errors.append(f"{prefix}.handling must be an object")
        else:
            for field in ("unknown_unit", "fluid_mismatch", "duplicate_specimen_itemid"):
                if handling.get(field) != "quarantine":
                    errors.append(f"{prefix}.handling.{field} must be quarantine")
            if handling.get("censored_value") != "preserve_raw_boundary":
                errors.append(f"{prefix}.handling.censored_value must preserve_raw_boundary")

        sources = rule.get("evidence_sources")
        if not isinstance(sources, list) or not sources or not all(_is_nonempty_string(source) for source in sources):
            errors.append(f"{prefix}.evidence_sources must be a non-empty string list")
        test_ids = rule.get("test_ids")
        if not isinstance(test_ids, list) or not test_ids or not all(_is_nonempty_string(test_id) for test_id in test_ids):
            errors.append(f"{prefix}.test_ids must be a non-empty string list")

        if status == "active":
            approval = rule.get("approval")
            if not isinstance(approval, dict):
                errors.append(f"{prefix} active rule requires approval record")
            else:
                for field in ("approved_by", "approved_at", "decision"):
                    if not _is_nonempty_string(approval.get(field)):
                        errors.append(f"{prefix}.approval.{field} is required for active rule")
                if approval.get("decision") not in {"approved", "approved_for_skill_use"}:
                    errors.append(f"{prefix}.approval.decision must explicitly approve active rule")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rule_pack", type=Path)
    args = parser.parse_args(argv)
    try:
        pack = json.loads(args.rule_pack.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read rule pack: {exc}", file=sys.stderr)
        return 2
    errors = validate_rule_pack(pack)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: valid rule pack {args.rule_pack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
