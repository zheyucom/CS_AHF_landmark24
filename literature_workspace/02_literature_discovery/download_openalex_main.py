#!/usr/bin/env python3
"""Retry selected main PDFs using OpenAlex article-level OA locations.

The script requires --no-si, skips rows that already have a successful
record-level downloader manifest, and rejects non-PDF-looking URLs.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


def existing_success(record_out: Path) -> bool:
    manifest = record_out / "manifest.json"
    if not manifest.exists():
        return False
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return any(
        result.get("status") == "open_access_downloaded"
        for result in payload.get("results", [])
    )


def pdf_like(url: str) -> bool:
    value = url.lower()
    return (
        value.endswith(".pdf")
        or "/pdf/" in value
        or "/pdfdirect/" in value
        or "/counter/pdf/" in value
        or value.endswith("/pdf")
        or "type=printable" in value
    )


def openalex_location(doi: str) -> dict:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-si", action="store_true", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--node", type=Path, required=True)
    parser.add_argument("--downloader", type=Path, required=True)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    attempted = 0
    downloaded = 0
    skipped_existing = 0
    skipped_no_pdf = 0
    for row in rows:
        record_out = args.out / "by_record" / row["record_id"]
        if existing_success(record_out):
            skipped_existing += 1
            continue
        assessment = openalex_location(row["doi"])
        oa = assessment["open_access"]
        location = assessment["location"]
        pdf_url = str(location.get("pdf_url") or "")
        if not oa.get("is_oa") or not pdf_like(pdf_url):
            skipped_no_pdf += 1
            print(
                f"[{row['record_id']}] no eligible OA main-PDF URL "
                f"(status={oa.get('oa_status')}, url={pdf_url or '-'})"
            )
            continue

        attempted += 1
        command = [
            str(args.node),
            str(args.downloader),
            "--pdf-url",
            pdf_url,
            "--title",
            row["title"],
            "--source-url",
            str(location.get("landing_page_url") or ""),
            "--no-si",
            "--out",
            str(record_out),
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        status = "subprocess_failed"
        if completed.stdout.strip():
            try:
                payload = json.loads(completed.stdout)
                result = (payload.get("results") or [{}])[0]
                status = result.get("status", status)
            except json.JSONDecodeError:
                status = "invalid_downloader_output"
        if status == "open_access_downloaded":
            downloaded += 1
        print(
            f"[{row['record_id']}] {status}; "
            f"oa_status={oa.get('oa_status')}; license={location.get('license') or ''}"
        )
        if completed.returncode and completed.stderr:
            print(completed.stderr.strip()[:500])

    print(
        json.dumps(
            {
                "attempted": attempted,
                "downloaded": downloaded,
                "skipped_existing": skipped_existing,
                "skipped_no_eligible_pdf_url": skipped_no_pdf,
                "si_requested": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
