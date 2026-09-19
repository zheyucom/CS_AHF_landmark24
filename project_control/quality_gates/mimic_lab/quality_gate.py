#!/usr/bin/env python3
"""Fail-closed static quality gate for project SQL authority and MIMIC labs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any


AUTHORITY_STATUSES = {"ACTIVE", "AUDIT_ONLY", "LEGACY_BLOCKED", "SUPERSEDED"}
ANALYSIS_ROLES = {"main", "sensitivity", "audit", "historical"}
ARTIFACT_KINDS = {
    "cohort",
    "phenotype",
    "outcome",
    "feature",
    "audit",
    "export",
    "modeling",
    "tool",
    "report",
    "config",
}
ENGINES = {"postgres", "bigquery", "python", "r", "shell", "notebook", "config"}
REQUIRED_MANIFEST_FIELDS = {
    "path",
    "artifact_kind",
    "authority_status",
    "analysis_role",
    "engine",
    "replacement_path",
    "allow_final_run",
    "rationale",
    "reviewed_on",
}
FORMAL_LAB_KINDS = {"cohort", "phenotype", "outcome", "feature", "modeling"}


def finding(
    code: str,
    path: str,
    message: str,
    severity: str = "error",
    blocks_final_run: bool = True,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "blocks_final_run": blocks_final_run,
        "path": path,
        "message": message,
    }


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def validate_manifest_rows(
    rows: Iterable[Mapping[str, Any]], tracked_sql: set[str]
) -> list[dict[str, Any]]:
    """Validate one-and-only-one fail-closed authority row per tracked SQL file."""
    materialized = [dict(row) for row in rows]
    paths = [str(row.get("path", "")).strip() for row in materialized]
    findings: list[dict[str, Any]] = []

    for path in sorted(tracked_sql - set(paths)):
        findings.append(
            finding(
                "MANIFEST_UNREGISTERED",
                path,
                "Git 跟踪 SQL 未登记到 PIPELINE_AUTHORITY_MANIFEST.csv。",
            )
        )
    for path in sorted(set(paths) - tracked_sql - {""}):
        findings.append(
            finding(
                "MANIFEST_NOT_TRACKED",
                path,
                "清单路径不是 Git 跟踪 SQL，不能作为正式工件。",
            )
        )
    for path, count in sorted(Counter(paths).items()):
        if path and count != 1:
            findings.append(
                finding(
                    "MANIFEST_DUPLICATE",
                    path,
                    f"同一 SQL 在权威清单中登记 {count} 次；必须恰好一次。",
                )
            )

    for row in materialized:
        path = str(row.get("path", "")).strip() or "<missing-path>"
        missing_columns = REQUIRED_MANIFEST_FIELDS - set(row)
        empty_required = {
            field
            for field in (REQUIRED_MANIFEST_FIELDS - {"replacement_path"})
            if not str(row.get(field, "")).strip()
        }
        if missing_columns or empty_required:
            fields = sorted(missing_columns | empty_required)
            findings.append(
                finding(
                    "MANIFEST_REQUIRED_FIELD",
                    path,
                    f"权威清单缺少必填字段：{fields}。",
                )
            )

        status = str(row.get("authority_status", "")).strip()
        role = str(row.get("analysis_role", "")).strip()
        kind = str(row.get("artifact_kind", "")).strip()
        engine = str(row.get("engine", "")).strip()
        allow_value = str(row.get("allow_final_run", "")).strip().lower()
        allow_final = _truthy(allow_value)

        if status not in AUTHORITY_STATUSES:
            findings.append(
                finding("MANIFEST_BAD_STATUS", path, f"未知 authority_status：{status!r}。")
            )
        if role not in ANALYSIS_ROLES:
            findings.append(finding("MANIFEST_BAD_ROLE", path, f"未知 analysis_role：{role!r}。"))
        if kind not in ARTIFACT_KINDS:
            findings.append(finding("MANIFEST_BAD_KIND", path, f"未知 artifact_kind：{kind!r}。"))
        if engine not in ENGINES:
            findings.append(finding("MANIFEST_BAD_ENGINE", path, f"未知 engine：{engine!r}。"))

        if allow_value not in {"true", "false"}:
            findings.append(
                finding(
                    "MANIFEST_BAD_BOOLEAN",
                    path,
                    "allow_final_run 只能是 true 或 false。",
                )
            )

        if allow_final and status != "ACTIVE":
            findings.append(
                finding(
                    "MANIFEST_FINAL_RUN_STATUS",
                    path,
                    "只有 ACTIVE 工件可以设置 allow_final_run=true。",
                )
            )
        if status == "ACTIVE" and not allow_final:
            findings.append(
                finding(
                    "MANIFEST_ACTIVE_NOT_FINAL",
                    path,
                    "ACTIVE 工件必须明确设置 allow_final_run=true；否则应保持 blocked。",
                )
            )
        if status == "ACTIVE" and role not in {"main", "sensitivity"}:
            findings.append(
                finding(
                    "MANIFEST_ACTIVE_ROLE",
                    path,
                    "ACTIVE 工件只能属于 main 或 sensitivity。",
                )
            )
        if status == "AUDIT_ONLY" and role != "audit":
            findings.append(
                finding(
                    "MANIFEST_AUDIT_ROLE",
                    path,
                    "AUDIT_ONLY 工件必须标为 audit。",
                )
            )
        if status in {"LEGACY_BLOCKED", "SUPERSEDED"} and role != "historical":
            findings.append(
                finding(
                    "MANIFEST_HISTORICAL_ROLE",
                    path,
                    f"{status} 工件必须标为 historical。",
                )
            )
        if status == "SUPERSEDED" and not str(row.get("replacement_path", "")).strip():
            findings.append(
                finding(
                    "MANIFEST_REPLACEMENT_MISSING",
                    path,
                    "SUPERSEDED 工件必须登记 replacement_path。",
                )
            )
        replacement = str(row.get("replacement_path", "")).strip()
        if status == "SUPERSEDED" and replacement and (
            replacement not in tracked_sql or replacement == path
        ):
            findings.append(
                finding(
                    "MANIFEST_BAD_REPLACEMENT",
                    path,
                    "SUPERSEDED replacement_path 必须指向另一个 Git 跟踪 SQL。",
                )
            )
    return findings


def validate_execution_plan(
    requested_paths: Sequence[str], rows: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Reject arbitrary, historical, audit-only, or superseded SQL from a final plan."""
    by_path = {str(row.get("path", "")).strip(): row for row in rows}
    findings: list[dict[str, Any]] = []
    for path in requested_paths:
        row = by_path.get(path)
        if row is None:
            findings.append(
                finding(
                    "PLAN_UNREGISTERED_ARTIFACT",
                    path,
                    "执行计划包含未登记 SQL。",
                )
            )
        elif row.get("authority_status") != "ACTIVE" or not _truthy(
            row.get("allow_final_run")
        ):
            findings.append(
                finding(
                    "PLAN_BLOCKED_ARTIFACT",
                    path,
                    "执行计划包含不允许进入正式运行的工件。",
                )
            )
    return findings


def _strip_sql_comments(sql: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\r\n]*", " ", without_blocks)


def _normalized_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", _strip_sql_comments(sql).lower()).strip()


def _contract_itemids(contract: Mapping[str, Any]) -> tuple[set[int], dict[int, str]]:
    allowed: set[int] = set()
    quarantined: dict[int, str] = {}
    for rule in contract.get("rules", []):
        if rule.get("status") != "active":
            continue
        for entry in rule.get("allow", []):
            if isinstance(entry.get("itemid"), int):
                allowed.add(entry["itemid"])
        for entry in rule.get("quarantine", []):
            if isinstance(entry.get("itemid"), int):
                quarantined[entry["itemid"]] = str(
                    entry.get("reason_code", "quarantined_itemid")
                )
    return allowed, quarantined


def _explicit_itemids(normalized_sql: str) -> set[int]:
    """Extract numeric IDs only where SQL syntax explicitly assigns them to itemid."""
    values = {
        int(value)
        for value in re.findall(
            r"\b(?:\w+\.)?itemid\s*=\s*(\d{4,6})\b", normalized_sql
        )
    }
    values.update(
        int(value)
        for value in re.findall(
            r"\b(\d{4,6})\s+as\s+itemid\b", normalized_sql
        )
    )
    for body in re.findall(
        r"\b(?:\w+\.)?itemid\s+in\s*\(([^)]*)\)", normalized_sql
    ):
        values.update(int(value) for value in re.findall(r"\b\d{4,6}\b", body))
    for body in re.findall(
        r"\bunnest\s*\(\s*\[([^]]*)\]\s*\)\s+(?:as\s+)?itemid\b",
        normalized_sql,
    ):
        values.update(int(value) for value in re.findall(r"\b\d{4,6}\b", body))
    return values


def scan_sql(
    path: str,
    sql: str,
    manifest_row: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return deterministic static findings without executing or rewriting SQL."""
    normalized = _normalized_sql(sql)
    status = str(manifest_row.get("authority_status", ""))
    role = str(manifest_row.get("analysis_role", ""))
    kind = str(manifest_row.get("artifact_kind", ""))
    formal = status != "AUDIT_ONLY" and kind in FORMAL_LAB_KINDS
    hard = status == "ACTIVE"
    severity = "error" if hard else "warning"
    results: list[dict[str, Any]] = []

    def add(code: str, message: str) -> None:
        results.append(finding(code, path, message, severity, hard))

    uses_raw = bool(re.search(r"\blabevents\b", normalized))
    uses_derived = bool(
        re.search(
            r"\bmimiciv_(?:\d+_\d+_)?derived\."
            r"(?:bg|chemistry|coagulation|complete_blood_count|blood_differential|"
            r"enzyme|first_day_lab)\b",
            normalized,
        )
    )

    if formal and uses_derived:
        add(
            "LAB_DERIVED_FORMAL_SOURCE",
            "正式队列、表型、结局或特征不得直接由 derived 实验室表生成。",
        )

    if uses_raw or uses_derived:
        silent_range = re.search(
            r"case\s+when\s+([a-z_][\w.]*)\s+between\b[^;]{0,160}"
            r"\bthen\s+\1(?:\s*::\s*[a-z_][a-z_ ]*)?\s+else\s+null\s+end",
            normalized,
        )
        if silent_range:
            add(
                "LAB_SILENT_RANGE_NULL",
                "范围外实验室值被 CASE ... ELSE NULL 静默删除；必须保留原值、标志和原因。",
            )

    if not uses_raw:
        return results

    fuzzy_metadata = bool(
        re.search(
            r"(?:label|fluid|category)[^;]{0,120}(?:\blike\b|regexp_(?:contains|like))",
            normalized,
        )
        or re.search(
            r"(?:\blike\b|regexp_(?:contains|like))[^;]{0,120}(?:label|fluid|category)",
            normalized,
        )
    )
    if fuzzy_metadata:
        add(
            "LAB_FUZZY_METADATA_SELECTION",
            "名称或元数据模糊匹配不能用于正式实验室纳入。",
        )

    availability_expression = (
        r"greatest\s*\(\s*(?:\w+\.)?charttime\s*,\s*coalesce\s*\(\s*"
        r"(?:\w+\.)?storetime\s*,\s*(?:\w+\.)?charttime\s*\)\s*\)"
    )
    availability = re.search(availability_expression, normalized)
    if not availability:
        add(
            "LAB_AVAILABILITY_MISSING",
            "raw 实验室查询缺少 GREATEST(charttime, COALESCE(storetime, charttime)) 可用时间。",
        )
    landmark_gate = re.search(
        rf"(?:availability_time|{availability_expression})\s*(?:<|>=)\s*"
        r"(?:\w+\.)?(?:t12|landmark\w*)\b",
        normalized,
    )
    if not landmark_gate:
        add(
            "LAB_LANDMARK_GATE_MISSING",
            "raw 实验室查询未把 availability_time 与登记的 landmark/T12 比较。",
        )

    if "valueuom" not in normalized or not any(
        token in normalized for token in ("allowed_unit", "allowed_units", "unknown_unit")
    ):
        add("LAB_UNIT_CONTRACT_MISSING", "raw 实验室查询缺少单位 allowlist 与未知单位分流。")
    if "fluid" not in normalized or not any(
        token in normalized for token in ("expected_fluid", "fluid_mismatch", "lc.fluid")
    ):
        add("LAB_FLUID_CONTRACT_MISSING", "raw 实验室查询缺少精确 fluid 合同。")
    if "category" not in normalized or not any(
        token in normalized
        for token in ("expected_category", "category_mismatch", "lc.category")
    ):
        add("LAB_CATEGORY_CONTRACT_MISSING", "raw 实验室查询缺少精确 category 合同。")
    if "specimen_id" not in normalized or not any(
        token in normalized
        for token in ("duplicate_specimen", "specimen_itemid_count", "partition by le.specimen_id")
    ):
        add(
            "LAB_SPECIMEN_CONTRACT_MISSING",
            "raw 实验室查询缺少 specimen_id × itemid 聚合前重复隔离。",
        )

    if re.search(
        r"coalesce\s*\(\s*(?:\w+\.)?(?:valuenum|value)\s*,\s*0(?:\.0+)?\s*\)",
        normalized,
    ):
        add("LAB_MISSING_TO_ZERO", "实验室缺失值不得补零。")

    allowed_ids, quarantined_ids = _contract_itemids(contract)
    referenced_ids = _explicit_itemids(normalized)
    explicit_quarantine = all(
        token in normalized for token in ("known_quarantine", "quarantine_reason")
    )
    wrong_fluid = sorted(referenced_ids & set(quarantined_ids))
    if wrong_fluid and not explicit_quarantine:
        add(
            "LAB_WRONG_FLUID_ITEMID",
            f"查询引用已隔离的错误体液 itemid：{wrong_fluid}。",
        )
    unknown_ids = sorted(referenced_ids - allowed_ids - set(quarantined_ids))
    if unknown_ids:
        add(
            "LAB_UNREGISTERED_ITEMID",
            f"查询引用未登记的实验室 itemid：{unknown_ids}。",
        )
    return results


def _normalize_identifier(value: str) -> str:
    return value.strip().strip("`\"").rstrip(";,)").lower()


def _created_tables(sql: str) -> set[str]:
    normalized = _normalized_sql(sql)
    return {
        _normalize_identifier(value)
        for value in re.findall(
            r"\bcreate\s+(?:or\s+replace\s+)?(?:temp(?:orary)?\s+)?table\s+"
            r"(?:if\s+not\s+exists\s+)?([`\"\w.$-]+)",
            normalized,
        )
    }


def _referenced_tables(sql: str) -> set[str]:
    normalized = _normalized_sql(sql)
    return {
        _normalize_identifier(value)
        for value in re.findall(r"\b(?:from|join)\s+([`\"\w.$-]+)", normalized)
    }


def scan_blocked_dependencies(
    sql_by_path: Mapping[str, str], rows: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Reject ACTIVE SQL that consumes tables produced only by non-final artifacts."""
    by_path = {str(row.get("path", "")): dict(row) for row in rows}
    producers: dict[str, set[str]] = defaultdict(set)
    for path, sql in sql_by_path.items():
        for table in _created_tables(sql):
            producers[table].add(path)

    findings: list[dict[str, Any]] = []
    for path, sql in sql_by_path.items():
        consumer = by_path.get(path, {})
        if consumer.get("authority_status") != "ACTIVE":
            continue
        for table in sorted(_referenced_tables(sql) & producers.keys()):
            table_producers = producers[table]
            statuses = {
                by_path.get(producer, {}).get("authority_status")
                for producer in table_producers
            }
            if statuses and statuses.issubset({"LEGACY_BLOCKED", "SUPERSEDED"}):
                findings.append(
                    finding(
                        "DEPENDENCY_BLOCKED_TABLE",
                        path,
                        f"ACTIVE SQL 读取仅由 blocked/superseded 工件生成的表 {table}；"
                        f"生产者：{sorted(table_producers)}。",
                    )
                )
            elif statuses and statuses == {"AUDIT_ONLY"}:
                findings.append(
                    finding(
                        "DEPENDENCY_AUDIT_ONLY_TABLE",
                        path,
                        f"ACTIVE SQL 读取仅供审计的表 {table}。",
                    )
                )
    return findings


def _infer_artifact_kind(path: str) -> str:
    name = Path(path).name.lower()
    if any(token in name for token in ("audit", "qc", "compare", "inventory", "discovery")):
        return "audit"
    if any(token in name for token in ("export", "query")):
        return "export"
    if any(token in name for token in ("outcome", "label", "event_timing", "censor")):
        return "outcome"
    if any(token in name for token in ("cohort", "riskset", "adult_first_icu")):
        return "cohort"
    if any(token in name for token in ("phenotype", "evidence", "ahf_strict", "hf_icd")):
        return "phenotype"
    if any(
        token in name
        for token in ("feature", "predictor", "labs_", "vital", "support", "echo_screen")
    ):
        return "feature"
    if any(token in name for token in ("modeling", "dataset", "person_period", "input")):
        return "modeling"
    if any(token in name for token in ("setup", "schema_and_manifest")):
        return "config"
    return "tool"


def initial_manifest_row(path: str) -> dict[str, str]:
    """Create a conservative, per-file Phase-A row; nothing is promoted to ACTIVE."""
    normalized = path.replace("\\", "/")
    replacement = ""
    if normalized == "project_control/MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql":
        status = "SUPERSEDED"
        role = "historical"
        replacement = "project_control/MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql"
        rationale = "V1 审计已由包含语义、单位、可用时间和体液隔离的 V2 明确替代。"
    elif (
        normalized.startswith("project_control/")
        or normalized.startswith("sql_v3_2/audits/")
        or normalized.startswith("sql_v4_2/audits/")
    ):
        status = "AUDIT_ONLY"
        role = "audit"
        rationale = "阶段 A 仅允许质量控制、候选发现或聚合审计，不得生成正式队列、特征或结局。"
    else:
        status = "LEGACY_BLOCKED"
        role = "historical"
        if normalized.startswith("sql_v3_2/"):
            rationale = "当前主线候选；阶段 B 完成 raw 实验室合同层和传递依赖审计前禁止正式执行。"
        elif normalized.startswith("sql_v4_2/"):
            rationale = "预设敏感性候选；通过与主线相同的实验室质量门前禁止正式执行。"
        else:
            rationale = "历史 SQL 原件保留用于追溯；未通过当前权威与实验室合同，正式运行 fail-closed。"

    engine = "bigquery" if normalized.startswith("project_control/") else "postgres"
    return {
        "path": normalized,
        "artifact_kind": _infer_artifact_kind(normalized),
        "authority_status": status,
        "analysis_role": role,
        "engine": engine,
        "replacement_path": replacement,
        "allow_final_run": "false",
        "rationale": rationale,
        "reviewed_on": "2026-09-19",
    }


def git_tracked_sql(project_root: Path) -> set[str]:
    completed = subprocess.run(
        ["git", "-C", str(project_root), "ls-files", "-z", "--", "*.sql"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed: {message}")
    return {
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    }


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_initial_manifest(path: Path, tracked_sql: set[str]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite authority manifest: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "path",
        "artifact_kind",
        "authority_status",
        "analysis_role",
        "engine",
        "replacement_path",
        "allow_final_run",
        "rationale",
        "reviewed_on",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(initial_manifest_row(item) for item in sorted(tracked_sql))


def audit_repository(
    project_root: Path,
    rows: Iterable[Mapping[str, Any]],
    contract: Mapping[str, Any],
    tracked_sql: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Audit every tracked SQL while only ACTIVE findings can block final execution."""
    materialized = [dict(row) for row in rows]
    tracked = tracked_sql if tracked_sql is not None else git_tracked_sql(project_root)
    results = validate_manifest_rows(materialized, tracked)
    by_path = {row.get("path", ""): row for row in materialized}
    sql_by_path: dict[str, str] = {}

    for path in sorted(tracked):
        sql_path = project_root / path
        try:
            sql = sql_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            results.append(
                finding(
                    "SQL_READ_FAILED",
                    path,
                    f"SQL 无法读取：{exc}",
                )
            )
            continue
        sql_by_path[path] = sql
        row = by_path.get(path)
        if row is None:
            continue
        results.extend(scan_sql(path, sql, row, contract))

    results.extend(scan_blocked_dependencies(sql_by_path, materialized))
    for item in results:
        row = by_path.get(item.get("path", ""), {})
        item.setdefault("authority_status", str(row.get("authority_status", "UNREGISTERED")))
        item.setdefault("analysis_role", str(row.get("analysis_role", "unknown")))
    return sorted(results, key=lambda item: (item["path"], item["code"], item["message"]))


def write_findings_csv(path: Path, findings: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "path",
        "authority_status",
        "analysis_role",
        "code",
        "severity",
        "blocks_final_run",
        "message",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(findings)


def write_summary(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    tracked_sql: set[str],
    findings: Sequence[Mapping[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    statuses = Counter(str(row.get("authority_status", "")) for row in rows)
    codes = Counter(str(item.get("code", "")) for item in findings)
    blockers = sum(bool(item.get("blocks_final_run")) for item in findings)
    lines = [
        "# MIMIC 实验室 SQL 静态质量门扫描摘要",
        "",
        f"扫描日期：{date.today().isoformat()}",
        "",
        "## 结论",
        "",
        f"- Git 跟踪 SQL：{len(tracked_sql)} 个。",
        f"- 权威清单行：{len(rows)} 行。",
        f"- 阻断正式运行的问题：{blockers} 个。",
        f"- 历史/审计风险记录：{len(findings) - blockers} 个（不代表已修复）。",
        "- 本扫描仅为静态检查；未连接数据库、未读取患者级数据。",
        "",
        "## 权威状态",
        "",
    ]
    lines.extend(f"- `{status}`：{count}" for status, count in sorted(statuses.items()))
    lines.extend(["", "## 发现代码", ""])
    if codes:
        lines.extend(f"- `{code}`：{count}" for code, count in sorted(codes.items()))
    else:
        lines.append("- 无静态发现。")
    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "`LEGACY_BLOCKED`/`SUPERSEDED` 中的发现进入问题账本但不修改历史原件；"
            "任何 ACTIVE 工件一旦出现同类问题或依赖这些产物，质量门将硬失败。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap-manifest")
    bootstrap.add_argument("--project-root", type=Path, required=True)
    bootstrap.add_argument("--output", type=Path, required=True)

    check = subparsers.add_parser("check")
    check.add_argument("--project-root", type=Path, required=True)
    check.add_argument("--manifest", type=Path, required=True)
    check.add_argument("--contract", type=Path, required=True)
    check.add_argument("--report-csv", type=Path, required=True)
    check.add_argument("--summary-md", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        project_root = args.project_root.resolve()
        tracked = git_tracked_sql(project_root)
        if args.command == "bootstrap-manifest":
            write_initial_manifest(args.output, tracked)
            print(f"WROTE {len(tracked)} rows: {args.output}")
            return 0

        rows = read_manifest(args.manifest)
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        findings = audit_repository(project_root, rows, contract, tracked)
        write_findings_csv(args.report_csv, findings)
        write_summary(args.summary_md, rows, tracked, findings)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    blockers = [item for item in findings if item["blocks_final_run"]]
    print(
        f"SQL={len(tracked)} MANIFEST={len(rows)} "
        f"FINDINGS={len(findings)} BLOCKERS={len(blockers)}"
    )
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
