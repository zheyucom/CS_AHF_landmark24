#!/usr/bin/env python3
"""Finalize Phase 2 download outcomes and append idempotent access events."""

from __future__ import annotations

import argparse
import csv
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


def openalex_assessment(doi: str) -> dict:
    work_id = urllib.parse.quote(f"https://doi.org/{doi}", safe=":/")
    request = urllib.request.Request(
        f"https://api.openalex.org/works/{work_id}",
        headers={"User-Agent": "Phase2LiteratureAudit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return {
        "open_access": payload.get("open_access") or {},
        "location": payload.get("best_oa_location") or {},
    }


def pmc_license(pmcid: str) -> str:
    if not pmcid:
        return ""
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Phase2LiteratureAudit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())
    record = root.find(".//record")
    return record.attrib.get("license", "") if record is not None else ""


def record_manifest(downloads: Path, record_id: str) -> dict:
    path = downloads / "by_record" / record_id / "manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def first_result(manifest: dict) -> dict:
    return (manifest.get("results") or [{}])[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--download-events", type=Path, required=True)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    verification_payload = json.loads(args.verification.read_text(encoding="utf-8"))
    verified = {
        result["record_id"]: result
        for result in verification_payload.get("results", [])
        if result.get("verification_status") == "verified_main_pdf"
    }
    initial_batch = json.loads(
        (args.downloads / "manifest.json").read_text(encoding="utf-8")
    )
    initial_by_doi = {
        result.get("doi", "").lower(): result
        for result in initial_batch.get("results", [])
    }

    events = []
    finalized = []
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for row in rows:
        record_id = row["record_id"]
        doi = row["doi"].lower()
        try:
            assessment = openalex_assessment(doi)
        except Exception:
            assessment = {"open_access": {}, "location": {}}
        oa = assessment["open_access"]
        location = assessment["location"]
        try:
            license_name = pmc_license(row.get("pmcid", "").strip())
        except Exception:
            license_name = ""
        manifest = record_manifest(args.downloads, record_id)
        result = first_result(manifest)
        initial = initial_by_doi.get(doi, {})

        if record_id in verified:
            check = verified[record_id]
            source_pdf = result.get("source") or manifest.get("request", {}).get("pdf_url", "")
            if "pmc-oa-opendata.s3.amazonaws.com" in source_pdf:
                row["access_route"] = "PMC_OA_S3_main_pdf"
                row["oa_authorization_evidence_url"] = (
                    f"https://pmc.ncbi.nlm.nih.gov/articles/{row['pmcid']}/"
                )
                evidence = (
                    f"PMC OA dataset canonical main PDF; article license={license_name or 'recorded by PMC'}; "
                    f"source_pdf={source_pdf}; SI=no"
                )
                source_name = "PMC OA S3"
                verification_sources = [
                    "PMC article record",
                    "PMC OA Web Service",
                    "PMC OA S3",
                    "local PDF verification",
                ]
            else:
                row["access_route"] = "publisher_OA_main_pdf"
                row["oa_authorization_evidence_url"] = (
                    location.get("landing_page_url")
                    or manifest.get("request", {}).get("source_url", "")
                    or f"https://doi.org/{doi}"
                )
                evidence = (
                    f"Publisher/repository OA main PDF; OpenAlex oa_status={oa.get('oa_status')}; "
                    f"license={location.get('license') or 'publicly readable/unspecified'}; "
                    f"source_pdf={source_pdf}; SI=no"
                )
                source_name = "Publisher/repository OA"
                verification_sources = [
                    "OpenAlex OA location",
                    "publisher/repository PDF",
                    "local PDF verification",
                ]
            row["license_or_evidence"] = evidence
            row["status"] = "verified_main_pdf"
            row["local_path"] = check["local_path"]
            row["mime"] = check["mime"]
            row["bytes"] = str(check["bytes"])
            row["page_count"] = str(check["page_count"])
            row["sha256"] = check["sha256"]
            row["failure_or_manual_action"] = ""
            event_url = source_pdf
        else:
            is_oa = bool(oa.get("is_oa"))
            if is_oa:
                row["status"] = "manual_authorized_retrieval_required"
                row["access_route"] = "OA_path_unresolved_or_fetch_blocked"
                row["oa_authorization_evidence_url"] = (
                    location.get("landing_page_url")
                    or (
                        f"https://pmc.ncbi.nlm.nih.gov/articles/{row['pmcid']}/"
                        if row.get("pmcid", "").strip()
                        else f"https://doi.org/{doi}"
                    )
                )
                row["license_or_evidence"] = (
                    f"OpenAlex oa_status={oa.get('oa_status')}; "
                    f"license={location.get('license') or license_name or 'unspecified'}; SI=no"
                )
                detail = result.get("err") or initial.get("err") or ""
                row["failure_or_manual_action"] = (
                    "OA/full-text landing evidence exists, but no verified main PDF was obtained "
                    f"(automated status={result.get('status') or initial.get('status') or 'no_main_pdf_url'}"
                    f"{'; detail=' + detail if detail else ''}). "
                    "Use only manual authorized retrieval; Phase 2 did not inspect Zotero. No SI downloaded."
                )
                source_name = "OpenAlex/PMC/publisher OA assessment"
                verification_sources = ["OpenAlex OA location", "PMC/Crossref access attempt"]
            else:
                row["status"] = "no_authorized_pdf_found"
                row["access_route"] = "OA_only_search_exhausted"
                row["oa_authorization_evidence_url"] = f"https://doi.org/{doi}"
                row["license_or_evidence"] = (
                    f"OpenAlex oa_status={oa.get('oa_status') or 'unknown'}; "
                    "no authorized OA main PDF identified; SI=no"
                )
                row["failure_or_manual_action"] = (
                    "No authorized OA main PDF was identified in the audited routes. "
                    "If the user has authorized access or a Zotero attachment, Phase 3 may reconcile it read-only; "
                    "Phase 2 did not inspect Zotero. No paywall bypass and no SI download."
                )
                source_name = "OA-only route assessment"
                verification_sources = ["OpenAlex OA status", "Crossref/PMC access attempt"]
            row["local_path"] = ""
            row["mime"] = ""
            row["bytes"] = ""
            row["page_count"] = ""
            row["sha256"] = ""
            event_url = row["oa_authorization_evidence_url"]

        events.append(
            {
                "access_status": row["status"],
                "canonical_identifier": f"DOI:{doi}",
                "event_type": "fulltext_access",
                "query": doi,
                "query_id": "PHASE2_FULLTEXT40",
                "raw_identifier": result.get("source") or event_url,
                "search_timestamp": timestamp,
                "source": source_name,
                "source_tier": "lawful_fulltext_route",
                "url": event_url,
                "verification_sources": verification_sources,
                "si_requested": False,
            }
        )
        finalized.append(row)

    with args.input.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(finalized[0].keys()))
        writer.writeheader()
        writer.writerows(finalized)

    args.download_events.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )
    retained = []
    with args.source_manifest.open(encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            if not (
                event.get("event_type") == "fulltext_access"
                and event.get("query_id") == "PHASE2_FULLTEXT40"
            ):
                retained.append(event)
    retained.extend(events)
    args.source_manifest.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in retained),
        encoding="utf-8",
    )

    counts = {}
    for row in finalized:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print(json.dumps({"rows": len(finalized), "status_counts": counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
