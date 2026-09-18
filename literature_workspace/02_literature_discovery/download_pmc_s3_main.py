#!/usr/bin/env python3
"""Retry main-article PDFs from the official PMC OA S3 dataset.

This helper is intentionally restricted to rows already selected in
download_log.csv. It requires --no-si and only accepts the canonical
<PMCID>.<version>.pdf object, never other PDFs in the article prefix.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


S3_ROOT = "https://pmc-oa-opendata.s3.amazonaws.com"
S3_NAMESPACE = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}


def canonical_main_pdf(pmcid: str) -> str:
    query = urllib.parse.urlencode({"list-type": "2", "prefix": f"{pmcid}."})
    with urllib.request.urlopen(f"{S3_ROOT}/?{query}", timeout=30) as response:
        root = ET.fromstring(response.read())
    keys = [node.text or "" for node in root.findall(".//s3:Key", S3_NAMESPACE)]
    candidates: list[tuple[int, str]] = []
    pattern = re.compile(
        rf"^{re.escape(pmcid)}\.(\d+)/{re.escape(pmcid)}\.\1\.pdf$",
        re.IGNORECASE,
    )
    for key in keys:
        match = pattern.match(key)
        if match:
            candidates.append((int(match.group(1)), key))
    if not candidates:
        return ""
    return f"{S3_ROOT}/{max(candidates)[1]}"


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
    no_main_pdf = 0
    for row in rows:
        pmcid = row.get("pmcid", "").strip()
        if not pmcid:
            continue
        pdf_url = canonical_main_pdf(pmcid)
        if not pdf_url:
            no_main_pdf += 1
            print(f"[{row['record_id']}] {pmcid}: no canonical main PDF in PMC OA S3")
            continue
        attempted += 1
        record_out = args.out / "by_record" / row["record_id"]
        command = [
            str(args.node),
            str(args.downloader),
            "--pdf-url",
            pdf_url,
            "--title",
            row["title"],
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
        print(f"[{row['record_id']}] {pmcid}: {status}")
        if completed.returncode and completed.stderr:
            print(completed.stderr.strip()[:500])

    print(
        json.dumps(
            {
                "pmcid_rows": sum(bool(row.get("pmcid", "").strip()) for row in rows),
                "attempted": attempted,
                "downloaded": downloaded,
                "no_canonical_main_pdf": no_main_pdf,
                "si_requested": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
