#!/usr/bin/env python3
"""Mechanical completion checks for the Phase 2 literature artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


REQUIRED_CANDIDATE_COLUMNS = {
    "record_id", "title", "authors", "year", "journal", "language",
    "study_design", "population", "outcome", "time_anchor", "doi", "pmid",
    "pmcid", "arxiv_id", "landing_url", "source_databases", "retrieved_at",
    "screening_status", "exclusion_reason", "evidence_stream",
    "relevance_score", "quality_grade", "verification_status", "core25_flag",
    "fulltext40_flag", "first15_flag", "legacy_seed_flag",
}


def truthy(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.dir
    errors: list[str] = []
    warnings: list[str] = []

    required = [
        "candidate_table.csv",
        "source_manifest.jsonl",
        "download_log.csv",
        "quality_report.md",
    ]
    for name in required:
        if not (base / name).is_file():
            errors.append(f"missing_required_file:{name}")

    with (base / "candidate_table.csv").open(encoding="utf-8-sig", newline="") as handle:
        candidates = list(csv.DictReader(handle))
    missing_columns = REQUIRED_CANDIDATE_COLUMNS - set(candidates[0])
    if missing_columns:
        errors.append(f"candidate_missing_columns:{sorted(missing_columns)}")
    if len(candidates) != 100:
        errors.append(f"candidate_count:{len(candidates)}")
    if len({row["record_id"] for row in candidates}) != 100:
        errors.append("candidate_record_id_not_unique")
    if len({row["doi"].lower() for row in candidates}) != 100:
        errors.append("candidate_doi_not_unique")
    flags = {
        name: {row["record_id"] for row in candidates if truthy(row[name])}
        for name in ("fulltext40_flag", "core25_flag", "first15_flag")
    }
    for name, expected in (
        ("fulltext40_flag", 40),
        ("core25_flag", 25),
        ("first15_flag", 15),
    ):
        if len(flags[name]) != expected:
            errors.append(f"{name}_count:{len(flags[name])}")
    if not flags["first15_flag"] <= flags["core25_flag"] <= flags["fulltext40_flag"]:
        errors.append("flag_sets_not_nested")
    for row in candidates:
        if truthy(row["core25_flag"]) and (
            not row["doi"].strip()
            or not row["landing_url"].strip()
            or row["verification_status"].strip().lower() == "unverified"
        ):
            errors.append(f"core_source_unstable:{row['record_id']}")

    source_events = []
    with (base / "source_manifest.jsonl").open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            try:
                source_events.append(json.loads(line))
            except json.JSONDecodeError as error:
                errors.append(f"source_manifest_invalid_json_line:{number}:{error}")
    fulltext_events = [
        event
        for event in source_events
        if event.get("event_type") == "fulltext_access"
        and event.get("query_id") == "PHASE2_FULLTEXT40"
    ]
    if len(fulltext_events) != 40:
        errors.append(f"fulltext_access_event_count:{len(fulltext_events)}")
    if any(event.get("si_requested") is not False for event in fulltext_events):
        errors.append("fulltext_event_si_not_false")

    with (base / "download_log.csv").open(encoding="utf-8-sig", newline="") as handle:
        downloads = list(csv.DictReader(handle))
    if len(downloads) != 40:
        errors.append(f"download_log_count:{len(downloads)}")
    if {row["record_id"] for row in downloads} != flags["fulltext40_flag"]:
        errors.append("download_log_not_equal_fulltext40")
    status_counts: dict[str, int] = {}
    verified_paths = []
    for row in downloads:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        if row["status"] == "verified_main_pdf":
            required_fields = (
                "local_path", "mime", "bytes", "page_count", "sha256",
                "oa_authorization_evidence_url", "license_or_evidence",
            )
            for field in required_fields:
                if not row[field].strip():
                    errors.append(f"download_missing_{field}:{row['record_id']}")
            path = Path(row["local_path"])
            verified_paths.append(path)
            if not path.is_file():
                errors.append(f"download_missing_file:{row['record_id']}")
                continue
            if path.read_bytes()[:5] != b"%PDF-":
                errors.append(f"download_bad_pdf_signature:{row['record_id']}")
            if path.stat().st_size != int(row["bytes"]):
                errors.append(f"download_bytes_mismatch:{row['record_id']}")
            if file_sha256(path) != row["sha256"]:
                errors.append(f"download_sha256_mismatch:{row['record_id']}")
            if row["mime"] != "application/pdf":
                errors.append(f"download_mime_mismatch:{row['record_id']}")
            if re.search(r"(?:^|[-_.])(supp|mmc\\d*|s\\d{3}|wt\\d+|ww\\d+)(?:[-_.]|$)", path.name, re.I):
                errors.append(f"supplement_like_pdf_name:{row['record_id']}:{path.name}")
        else:
            if any(row[field].strip() for field in ("local_path", "mime", "bytes", "page_count", "sha256")):
                errors.append(f"failed_download_has_file_metadata:{row['record_id']}")
            if not row["failure_or_manual_action"].strip():
                errors.append(f"failed_download_missing_action:{row['record_id']}")
    if status_counts != {
        "verified_main_pdf": 21,
        "manual_authorized_retrieval_required": 11,
        "no_authorized_pdf_found": 8,
    }:
        errors.append(f"unexpected_download_status_counts:{status_counts}")
    all_pdf_paths = list((base / "fulltext_downloads").glob("**/*.pdf"))
    if len(all_pdf_paths) != len(verified_paths):
        errors.append(
            f"unexpected_pdf_count_on_disk:{len(all_pdf_paths)}_vs_verified:{len(verified_paths)}"
        )

    verification = json.loads((base / "fulltext_verification.json").read_text(encoding="utf-8"))
    if verification.get("downloaded_pdf_count") != 21:
        errors.append("verification_downloaded_count_not_21")
    if verification.get("verified_main_pdf_count") != 21:
        errors.append("verification_verified_count_not_21")
    if verification.get("manual_review_required_count") != 0:
        errors.append("verification_manual_review_not_zero")

    status = json.loads((base / "phase2_status.json").read_text(encoding="utf-8"))
    if status.get("status") != "waiting_review":
        errors.append(f"phase2_status_not_waiting_review:{status.get('status')}")
    if status.get("si_choice") != "no":
        errors.append(f"phase2_si_choice_not_no:{status.get('si_choice')}")
    if status.get("phase3_zotero_touched") is not False:
        errors.append("phase3_zotero_touched_not_false")
    if status.get("phase4_obsidian_touched") is not False:
        errors.append("phase4_obsidian_touched_not_false")

    quality = (base / "quality_report.md").read_text(encoding="utf-8")
    for marker in (
        "user_reported_legacy_articles_imported=true",
        "verified=false",
        "SI_choice=no",
        "status=Waiting review",
    ):
        if marker not in quality:
            errors.append(f"quality_report_missing_marker:{marker}")

    prohibited = [
        path
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in {".sqlite", ".caj", ".zip", ".tar", ".gz"}
    ]
    if prohibited:
        errors.append(f"prohibited_phase2_files:{[str(path) for path in prohibited]}")

    report = {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "candidate_count": len(candidates),
        "fulltext40_count": len(flags["fulltext40_flag"]),
        "core25_count": len(flags["core25_flag"]),
        "first15_count": len(flags["first15_flag"]),
        "source_manifest_jsonl_count": len(source_events),
        "fulltext_access_event_count": len(fulltext_events),
        "download_log_count": len(downloads),
        "download_status_counts": status_counts,
        "pdf_count_on_disk": len(all_pdf_paths),
        "verified_pdf_count": len(verified_paths),
        "si_downloaded": 0,
        "zotero_touched": False,
        "obsidian_touched": False,
        "patient_level_data_touched": False,
    }
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out.read_text(encoding="utf-8"))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
