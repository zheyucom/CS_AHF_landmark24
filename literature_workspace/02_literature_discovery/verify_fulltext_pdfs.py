#!/usr/bin/env python3
"""Independently verify downloaded main-article PDFs against Phase 2 metadata."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

from pypdf import PdfReader


STOPWORDS = {
    "about", "after", "among", "and", "article", "based", "between", "clinical",
    "during", "early", "for", "from", "heart", "intensive", "methods", "of",
    "patients", "prediction", "study", "the", "through", "to", "using", "with",
}


def normalized_tokens(value: str) -> set[str]:
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return {
        token
        for token in re.findall(r"[a-z0-9]+", folded.lower())
        if len(token) >= 4 and token not in STOPWORDS
    }


def normalize_doi(value: str) -> str:
    return re.sub(r"\s+", "", value.lower()).rstrip(".,;)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_text(reader: PdfReader, pages: int = 5) -> str:
    chunks = []
    for page in reader.pages[:pages]:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--csv-out", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    results = []
    for row in rows:
        pdfs = sorted((args.downloads / "by_record" / row["record_id"] / "PDFs").glob("*.pdf"))
        if not pdfs:
            continue
        path = pdfs[0]
        signature = path.read_bytes()[:5] == b"%PDF-"
        mime = subprocess.run(
            ["file", "--brief", "--mime-type", str(path)],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        errors = []
        page_count = 0
        text = ""
        try:
            reader = PdfReader(str(path))
            page_count = len(reader.pages)
            text = extract_text(reader)
        except Exception as error:
            errors.append(f"pdf_parse_error:{type(error).__name__}:{error}")

        target_tokens = normalized_tokens(row["title"])
        observed_tokens = normalized_tokens(text)
        title_overlap = (
            len(target_tokens & observed_tokens) / len(target_tokens)
            if target_tokens
            else 0.0
        )
        doi_match = normalize_doi(row["doi"]) in normalize_doi(text)
        content_match = doi_match or title_overlap >= 0.55
        passed = (
            signature
            and mime == "application/pdf"
            and page_count > 0
            and bool(text.strip())
            and content_match
            and len(pdfs) == 1
        )
        if len(pdfs) != 1:
            errors.append(f"unexpected_pdf_count:{len(pdfs)}")
        if not signature:
            errors.append("missing_pdf_signature")
        if mime != "application/pdf":
            errors.append(f"unexpected_mime:{mime}")
        if not page_count:
            errors.append("zero_pages")
        if not text.strip():
            errors.append("no_extractable_text")
        if not content_match:
            errors.append("title_and_doi_mismatch")

        results.append(
            {
                "record_id": row["record_id"],
                "title": row["title"],
                "doi": row["doi"],
                "local_path": str(path.resolve()),
                "pdf_signature_valid": signature,
                "mime": mime,
                "bytes": path.stat().st_size,
                "page_count": page_count,
                "sha256": sha256(path),
                "extracted_chars_first5": len(text),
                "title_token_overlap": round(title_overlap, 4),
                "doi_match": doi_match,
                "verification_status": "verified_main_pdf" if passed else "manual_review_required",
                "errors": ";".join(errors),
            }
        )

    args.csv_out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(results[0].keys()) if results else []
    with args.csv_out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    args.json_out.write_text(
        json.dumps(
            {
                "downloaded_pdf_count": len(results),
                "verified_main_pdf_count": sum(
                    result["verification_status"] == "verified_main_pdf"
                    for result in results
                ),
                "manual_review_required_count": sum(
                    result["verification_status"] != "verified_main_pdf"
                    for result in results
                ),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(args.json_out.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
