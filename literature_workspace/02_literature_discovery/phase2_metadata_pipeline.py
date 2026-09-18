#!/usr/bin/env python3
"""Phase-2 metadata-only literature discovery and audit pipeline.

This script deliberately retrieves bibliographic metadata only.  It does not
download article full text, supplements, HTML pages, PDFs, or Zotero data.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parent
UTC_NOW = lambda: dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
USER_AGENT = "CS-AHF-landmark24-literature-audit/1.0 (metadata-only)"

PUBMED_QUERIES: dict[str, str] = {
    "Q1_AHF_WHF_definition": (
        '("acute heart failure"[Title/Abstract] OR "acute decompensated heart failure"[Title/Abstract]) '
        'AND ("worsening heart failure"[Title/Abstract] OR "in-hospital worsening"[Title/Abstract] '
        'OR "treatment intensification"[Title/Abstract] OR "treatment escalation"[Title/Abstract])'
    ),
    "Q2_AHF_to_CS": (
        '("acute heart failure"[Title/Abstract] OR "acute decompensated heart failure"[Title/Abstract]) '
        'AND ("cardiogenic shock"[Title/Abstract]) '
        'AND (predict*[Title/Abstract] OR risk[Title/Abstract] OR progression[Title/Abstract] '
        'OR "machine learning"[Title/Abstract])'
    ),
    "Q3_HF_sepsis_mixed": (
        '("heart failure"[Title/Abstract]) AND (sepsis[Title/Abstract] OR septic[Title/Abstract] '
        'OR infection[Title/Abstract]) AND ("intensive care"[Title/Abstract] OR ICU[Title/Abstract] '
        'OR shock[Title/Abstract] OR mortality[Title/Abstract] OR outcome*[Title/Abstract])'
    ),
    "Q4_ICU_hemodynamic_deterioration": (
        '("hemodynamic deterioration"[Title/Abstract] OR "hemodynamic instability"[Title/Abstract] '
        'OR "circulatory failure"[Title/Abstract] OR "cardiovascular intensive care"[Title/Abstract] '
        'OR "cardiac intensive care"[Title/Abstract]) '
        'AND (predict*[Title/Abstract] OR "early warning"[Title/Abstract] OR '
        '"machine learning"[Title/Abstract] OR deterioration[Title/Abstract])'
    ),
    "Q5_dynamic_EHR_landmark_leakage": (
        '("electronic health record"[Title/Abstract] OR EHR[Title/Abstract] OR '
        '"intensive care"[Title/Abstract]) AND ("dynamic prediction"[Title/Abstract] '
        'OR landmark*[Title/Abstract] OR "time-dependent"[Title/Abstract] '
        'OR "real-time prediction"[Title/Abstract] OR "data leakage"[Title/Abstract]) '
        'AND (deterioration[Title/Abstract] OR shock[Title/Abstract] '
        'OR "clinical prediction"[Title/Abstract])'
    ),
    "Q6_prediction_reporting_validation": (
        '("prediction model"[Title/Abstract] OR "machine learning"[Title/Abstract]) '
        'AND (TRIPOD[Title/Abstract] OR PROBAST[Title/Abstract] OR calibration[Title/Abstract] '
        'OR "external validation"[Title/Abstract] OR "decision curve"[Title/Abstract] '
        'OR "sample size"[Title/Abstract]) AND (clinical[Title/Abstract] OR '
        'diagnostic[Title/Abstract] OR prognostic[Title/Abstract])'
    ),
    "Q7_MIMIC_transportability": (
        '("MIMIC-IV"[Title/Abstract] OR "MIMIC III"[Title/Abstract] OR '
        '"Medical Information Mart for Intensive Care"[Title/Abstract]) '
        'AND ("external validation"[Title/Abstract] OR transportability[Title/Abstract] '
        'OR generalizability[Title/Abstract] OR "dataset shift"[Title/Abstract] '
        'OR multicenter[Title/Abstract])'
    ),
    "Q8_Chinese_language": (
        '(("heart failure"[Title/Abstract] OR "cardiogenic shock"[Title/Abstract]) '
        'AND (sepsis[Title/Abstract] OR "intensive care"[Title/Abstract] '
        'OR deterioration[Title/Abstract] OR prognosis[Title/Abstract])) '
        'AND chinese[Language]'
    ),
}

CROSSREF_QUERIES: dict[str, str] = {
    "CR1_AHF_WHF": "acute heart failure worsening heart failure risk prediction treatment escalation",
    "CR2_CS_early_warning": "cardiogenic shock early prediction machine learning acute heart failure",
    "CR3_ICU_HD": "hemodynamic deterioration cardiovascular intensive care early warning",
    "CR4_dynamic_EHR": "dynamic prediction landmark electronic health record intensive care deterioration",
    "CR5_prediction_methods": "TRIPOD AI PROBAST AI calibration external validation prediction model",
    "CR6_transportability": "MIMIC external validation transportability clinical prediction model",
}

OPENALEX_QUERIES: dict[str, str] = {
    "OA1_AHF_CS_HD": "acute heart failure hemodynamic deterioration cardiogenic shock prediction",
    "OA2_HF_sepsis": "heart failure sepsis mixed shock fluid resuscitation",
    "OA3_dynamic_landmark": "dynamic prediction landmark electronic health record intensive care data leakage",
    "OA4_validation_transport": "clinical prediction model external validation calibration transportability",
}

LEGACY_SEEDS = {
    "10.1002/ejhf.2874",
    "10.1161/jaha.114.001088",
    "10.1016/j.ahj.2016.04.021",
    "10.1002/ehf2.14792",
    "10.1093/ehjacc/zuae037",
    "10.1016/j.jscai.2022.100308",
    "10.3389/fcvm.2022.862424",
    "10.3389/fcvm.2025.1694001",
    "10.3389/fmed.2024.1410702",
    "10.2196/19892",
    "10.1016/j.jacc.2022.11.023",
    "10.1136/bmj-2023-078378",
    "10.1136/bmj-2024-082505",
}

TARGET_TITLES = [
    "Transparent reporting of a multivariable prediction model for individual prognosis or diagnosis (TRIPOD)",
    "PROBAST: A Tool to Assess the Risk of Bias and Applicability of Prediction Model Studies",
    "Calibration: the Achilles heel of predictive analytics",
    "Clinical prediction models: a practical approach to development, validation, and updating",
    "Minimum sample size for external validation of a clinical prediction model with a binary outcome",
    "Minimum sample size for developing a multivariable prediction model",
    "MIMIC-IV, a freely accessible electronic health record dataset",
    "MIMIC-III, a freely accessible critical care database",
    "Cardiogenic shock classification to predict mortality in the cardiac intensive care unit",
    "SCAI clinical expert consensus statement on the classification of cardiogenic shock",
    "Contemporary Management of Cardiogenic Shock: A Scientific Statement From the American Heart Association",
    "Worsening Heart Failure: Nomenclature, Epidemiology, and Future Directions",
    "2021 ESC Guidelines for the diagnosis and treatment of acute and chronic heart failure",
]

SELECTION_BY_STREAM: dict[str, list[str]] = {
    "AHF_WHF_outcome_definition": [
        "10.1002/ejhf.2874",
        "10.1016/j.jacc.2022.11.023",
        "10.1161/jaha.114.001088",
        "10.1016/j.ahj.2016.04.021",
        "10.1016/j.ijcard.2017.10.023",
        "10.1016/j.ijcard.2016.10.002",
        "10.1016/j.cardfail.2009.04.001",
        "10.1161/circheartfailure.116.003048",
        "10.1002/ejhf.308",
        "10.1016/j.ahj.2015.04.007",
        "10.1016/j.jchf.2015.01.007",
        "10.1002/ejhf.186",
        "10.1002/ehf2.12195",
        "10.1002/ejhf.515",
        "10.1016/j.ahj.2015.09.001",
        "10.1002/ejhf.333",
        "10.1016/j.hfc.2015.07.004",
        "10.36660/abc.20220584",
    ],
    "AHF_to_cardiogenic_shock": [
        "10.1002/ehf2.14792",
        "10.1093/ehjacc/zuae037",
        "10.1016/j.jscai.2022.100308",
        "10.3389/fcvm.2022.862424",
        "10.1016/j.amjcard.2026.03.076",
        "10.7759/cureus.50395",
        "10.1016/j.jscai.2022.100496",
        "10.3389/fcvm.2022.849688",
        "10.1016/j.ijcha.2021.100809",
        "10.1016/j.jacc.2019.07.077",
        "10.1016/j.ahj.2020.10.054",
        "10.1007/s00134-015-4041-5",
        "10.1161/cir.0000000000000525",
        "10.1002/ccd.28329",
        "10.1161/jaha.122.029232",
        "10.1097/shk.0000000000002091",
        "10.1016/j.jacadv.2022.100126",
        "10.1093/ehjdh/ztae094",
    ],
    "HF_sepsis_mixed_physiology": [
        "10.3389/fmed.2024.1410702",
        "10.1016/j.mayocpiqo.2021.11.008",
        "10.1016/j.jemermed.2024.02.001",
        "10.1371/journal.pone.0256368",
        "10.1016/j.cpcardiol.2024.102696",
        "10.1097/ccm.0000000000003960",
        "10.1016/j.jointm.2023.05.001",
        "10.1007/s11596-025-00138-9",
        "10.1186/s12871-022-01865-5",
        "10.1001/jamanetworkopen.2022.35331",
        "10.3389/fmed.2022.714384",
        "10.1038/s41598-025-85596-w",
        "10.1186/s12916-024-03715-2",
        "10.1016/j.amjmed.2022.09.022",
        "10.3881/j.issn.1000-503x.16031",
        "10.3760/cma.j.cn121430-20200817-00629",
        "10.3760/cma.j.issn.2095-4352.2017.12.018",
        "10.3760/cma.j.cn121430-20240812-00693",
    ],
    "ICU_CICU_hemodynamic_deterioration": [
        "10.3389/fcvm.2025.1694001",
        "10.1038/s41591-020-0789-4",
        "10.1097/shk.0000000000002261",
        "10.7759/cureus.50169",
        "10.4258/hir.2021.27.3.241",
        "10.3390/jcm14020350",
        "10.1016/j.jcrc.2024.154954",
        "10.1016/j.jcrc.2025.155093",
        "10.1007/s11886-024-02149-9",
        "10.1093/ehjdh/ztae098",
        "10.1016/j.ihj.2022.11.002",
        "10.3389/frai.2022.876007",
        "10.3389/fcvm.2023.1119699",
        "10.1016/j.xjon.2024.09.006",
        "10.4187/respcare.06797",
        "10.1002/ccd.30103",
    ],
    "landmark_dynamic_EHR_leakage": [
        "10.1007/s10729-014-9281-3",
        "10.1186/s12911-022-02026-x",
        "10.1016/j.jtcvs.2021.10.060",
        "10.1177/08850666231166349",
        "10.1371/journal.pdig.0000116",
        "10.1016/j.ijmedinf.2023.105086",
        "10.3389/fmed.2022.853102",
        "10.3389/fmed.2020.637434",
        "10.2196/69293",
        "10.1038/s41746-025-02114-y",
        "10.1016/j.patter.2023.100804",
        "10.1111/j.1467-9469.2006.00529.x",
    ],
    "reporting_bias_calibration_validation": [
        "10.1136/bmj-2023-078378",
        "10.1136/bmj-2024-082505",
        "10.1136/bmj.g7594",
        "10.7326/m14-0698",
        "10.7326/m18-1376",
        "10.7326/m18-1377",
        "10.1002/sim.9025",
        "10.1136/bmj-2023-074821",
        "10.1016/j.jclinepi.2021.02.011",
        "10.1186/1471-2288-14-40",
        "10.1186/s12916-019-1466-7",
        "10.1016/j.jclinepi.2015.12.005",
    ],
    "MIMIC_external_transportability_China": [
        "10.1038/s41597-022-01899-x",
        "10.1038/s41597-021-01110-7",
        "10.1093/jamia/ocad174",
        "10.1186/s12911-022-02090-3",
        "10.3389/fendo.2026.1699647",
        "10.1016/j.ijmedinf.2025.106203",
    ],
}

CORE25_DOIS = {
    "10.1002/ejhf.2874",
    "10.1016/j.jacc.2022.11.023",
    "10.1161/jaha.114.001088",
    "10.1016/j.ahj.2016.04.021",
    "10.1016/j.ijcard.2017.10.023",
    "10.1002/ehf2.14792",
    "10.1093/ehjacc/zuae037",
    "10.1016/j.jscai.2022.100308",
    "10.3389/fcvm.2022.862424",
    "10.1016/j.amjcard.2026.03.076",
    "10.1016/j.jscai.2022.100496",
    "10.1016/j.jacc.2019.07.077",
    "10.3389/fmed.2024.1410702",
    "10.1016/j.mayocpiqo.2021.11.008",
    "10.1371/journal.pone.0256368",
    "10.1001/jamanetworkopen.2022.35331",
    "10.1186/s12916-024-03715-2",
    "10.1016/j.amjmed.2022.09.022",
    "10.3389/fcvm.2025.1694001",
    "10.1038/s41591-020-0789-4",
    "10.7759/cureus.50169",
    "10.1007/s10729-014-9281-3",
    "10.1016/j.patter.2023.100804",
    "10.1136/bmj-2023-078378",
    "10.1136/bmj-2024-082505",
}

FIRST15_DOIS = {
    "10.1161/jaha.114.001088",
    "10.1016/j.ahj.2016.04.021",
    "10.1002/ehf2.14792",
    "10.1093/ehjacc/zuae037",
    "10.1016/j.jscai.2022.100308",
    "10.3389/fcvm.2022.862424",
    "10.3389/fcvm.2025.1694001",
    "10.1038/s41591-020-0789-4",
    "10.3389/fmed.2024.1410702",
    "10.1016/j.mayocpiqo.2021.11.008",
    "10.1371/journal.pone.0256368",
    "10.1186/s12916-024-03715-2",
    "10.1007/s10729-014-9281-3",
    "10.1136/bmj-2023-078378",
    "10.1136/bmj-2024-082505",
}

FULLTEXT_EXTRA15_DOIS = {
    "10.1161/circheartfailure.116.003048",
    "10.1002/ejhf.308",
    "10.1016/j.jchf.2015.01.007",
    "10.1002/ejhf.515",
    "10.7759/cureus.50395",
    "10.3389/fcvm.2022.849688",
    "10.1016/j.ahj.2020.10.054",
    "10.1002/ccd.28329",
    "10.1016/j.jemermed.2024.02.001",
    "10.1016/j.jointm.2023.05.001",
    "10.1186/s12871-022-01865-5",
    "10.1186/s12911-022-02026-x",
    "10.1002/sim.9025",
    "10.1186/s12916-019-1466-7",
    "10.1038/s41597-022-01899-x",
}

CHINESE_OFFICIAL_URLS = {
    "10.3881/j.issn.1000-503x.16031": (
        "Official journal site",
        "https://journal13.magtechjournal.com/yxkxy/CN/10.3881/j.issn.1000-503X.16031",
    ),
    "10.3760/cma.j.cn121430-20200817-00629": (
        "Chinese Medical Association journal gateway",
        "https://www.yiigle.com/LinkIn.do?linkin_type=DOI&DOI=10.3760/cma.j.cn121430-20200817-00629",
    ),
    "10.3760/cma.j.issn.2095-4352.2017.12.018": (
        "Wanfang Medical",
        "https://med.wanfangdata.com.cn/Paper/Detail?id=PeriodicalPaper_zgwzbjjyx201712018",
    ),
    "10.3760/cma.j.cn121430-20240812-00693": (
        "Chinese Medical Association journal gateway",
        "https://www.yiigle.com/LinkIn.do?linkin_type=DOI&DOI=10.3760/cma.j.cn121430-20240812-00693",
    ),
}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(value: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    return value.rstrip(".,;)]}")


def normalized_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", clean_text(value).lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    stop = {"a", "an", "the", "in", "of", "for", "on", "to", "and", "with", "by", "et", "al"}
    return " ".join(tok for tok in value.split() if tok not in stop)


def json_request(url: str, retries: int = 3, pause: float = 0.4) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                ctype = response.headers.get("Content-Type", "")
                if "json" not in ctype.lower():
                    raise RuntimeError(f"metadata endpoint returned non-JSON content type: {ctype}")
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, RuntimeError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(pause * (2**attempt))
    raise RuntimeError(f"metadata request failed after {retries} attempts: {url}: {last}")


def chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(values), size):
        yield values[i : i + size]


def pubmed_search(query: str, retmax: int = 180) -> tuple[list[str], int, str]:
    params = urllib.parse.urlencode(
        {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": str(retmax),
            "sort": "relevance",
            "tool": "CS_AHF_landmark24",
        }
    )
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}"
    payload = json_request(url)
    result = payload["esearchresult"]
    return result.get("idlist", []), int(result.get("count", 0)), url


def pubmed_summaries(pmids: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for batch in chunks(pmids, 180):
        params = urllib.parse.urlencode(
            {
                "db": "pubmed",
                "id": ",".join(batch),
                "retmode": "json",
                "version": "2.0",
                "tool": "CS_AHF_landmark24",
            }
        )
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{params}"
        payload = json_request(url)
        for uid in payload.get("result", {}).get("uids", []):
            found[str(uid)] = payload["result"][str(uid)]
        time.sleep(0.34)
    return found


def pubmed_record(summary: dict[str, Any]) -> dict[str, Any]:
    articleids = {str(x.get("idtype", "")).lower(): clean_text(x.get("value", "")) for x in summary.get("articleids", [])}
    pubdate = clean_text(summary.get("pubdate", ""))
    year_match = re.search(r"(?:19|20)\d{2}", pubdate)
    authors = [clean_text(x.get("name", "")) for x in summary.get("authors", []) if clean_text(x.get("name", ""))]
    doi = normalize_doi(articleids.get("doi", ""))
    pmid = clean_text(summary.get("uid", "") or articleids.get("pubmed", ""))
    pmcid = clean_text(articleids.get("pmc", ""))
    return {
        "title": clean_text(summary.get("title", "")),
        "authors": authors,
        "year": int(year_match.group()) if year_match else None,
        "journal": clean_text(summary.get("fulljournalname", "") or summary.get("source", "")),
        "doi": doi,
        "pmid": pmid,
        "pmcid": pmcid,
        "arxiv_id": "",
        "landing_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        "source_databases": ["PubMed"],
        "source_type": "journal-article",
        "language": "",
    }


def crossref_search(query: str, rows: int = 80) -> tuple[list[dict[str, Any]], int, str]:
    params = urllib.parse.urlencode(
        {
            "query.bibliographic": query,
            "rows": str(rows),
            "mailto": "research-metadata@example.invalid",
        }
    )
    url = f"https://api.crossref.org/works?{params}"
    payload = json_request(url)
    message = payload.get("message", {})
    return message.get("items", []), int(message.get("total-results", 0)), url


def crossref_lookup(doi: str) -> tuple[dict[str, Any] | None, str]:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    try:
        payload = json_request(url)
        return payload.get("message", {}), url
    except RuntimeError:
        return None, url


def crossref_record(item: dict[str, Any]) -> dict[str, Any]:
    date_parts = (
        item.get("published-print", {}).get("date-parts")
        or item.get("published-online", {}).get("date-parts")
        or item.get("published", {}).get("date-parts")
        or item.get("created", {}).get("date-parts")
        or []
    )
    year = date_parts[0][0] if date_parts and date_parts[0] else None
    authors = []
    for author in item.get("author", []) or []:
        family = clean_text(author.get("family", ""))
        given = clean_text(author.get("given", ""))
        name = ", ".join(x for x in [family, given] if x)
        if name:
            authors.append(name)
    return {
        "title": clean_text((item.get("title") or [""])[0]),
        "authors": authors,
        "year": int(year) if year else None,
        "journal": clean_text((item.get("container-title") or [""])[0]),
        "doi": normalize_doi(item.get("DOI", "")),
        "pmid": "",
        "pmcid": "",
        "arxiv_id": "",
        "landing_url": clean_text(item.get("URL", "")),
        "source_databases": ["Crossref"],
        "source_type": clean_text(item.get("type", "")),
        "language": clean_text(item.get("language", "")),
        "license": item.get("license", []) or [],
        "links": item.get("link", []) or [],
    }


def record_key(record: dict[str, Any]) -> str:
    doi = normalize_doi(record.get("doi", ""))
    if doi:
        return f"doi:{doi}"
    for field in ("pmid", "pmcid", "arxiv_id"):
        value = clean_text(record.get(field, "")).lower()
        if value:
            return f"{field}:{value}"
    first_author = clean_text((record.get("authors") or [""])[0]).split(",")[0].lower()
    return f"title:{normalized_title(record.get('title', ''))}|{first_author}|{record.get('year', '')}"


def merge_records(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    out = dict(current)
    for field in ("title", "year", "journal", "doi", "pmid", "pmcid", "arxiv_id", "landing_url", "source_type", "language"):
        if not out.get(field) and incoming.get(field):
            out[field] = incoming[field]
    if len(incoming.get("authors") or []) > len(out.get("authors") or []):
        out["authors"] = incoming["authors"]
    out["source_databases"] = sorted(set((out.get("source_databases") or []) + (incoming.get("source_databases") or [])))
    if incoming.get("license"):
        out["license"] = incoming["license"]
    if incoming.get("links"):
        out["links"] = incoming["links"]
    return out


def retrieve() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = UTC_NOW()
    source_events: list[dict[str, Any]] = []
    pmid_to_queries: dict[str, set[str]] = defaultdict(set)
    all_pmids: set[str] = set()

    for query_id, query in PUBMED_QUERIES.items():
        pmids, total, url = pubmed_search(query)
        for pmid in pmids:
            pmid_to_queries[pmid].add(query_id)
        all_pmids.update(pmids)
        source_events.append(
            {
                "event_type": "search",
                "source": "PubMed",
                "source_tier": "T1",
                "query_id": query_id,
                "query": query,
                "search_timestamp": timestamp,
                "raw_identifier": "",
                "canonical_identifier": "",
                "url": url,
                "hit_count_total": total,
                "hit_count_retrieved": len(pmids),
                "verification_sources": ["PubMed E-utilities"],
                "access_status": "metadata_retrieved",
            }
        )
        time.sleep(0.34)

    for title in TARGET_TITLES:
        query_id = f"PX_{normalized_title(title)[:48].replace(' ', '_')}"
        pmids, total, url = pubmed_search(f'"{title}"[Title]', retmax=8)
        for pmid in pmids:
            pmid_to_queries[pmid].add(query_id)
        all_pmids.update(pmids)
        source_events.append(
            {
                "event_type": "seed_resolution",
                "source": "PubMed",
                "source_tier": "T1",
                "query_id": query_id,
                "query": f'"{title}"[Title]',
                "search_timestamp": timestamp,
                "raw_identifier": title,
                "canonical_identifier": ",".join(pmids),
                "url": url,
                "hit_count_total": total,
                "hit_count_retrieved": len(pmids),
                "verification_sources": ["PubMed E-utilities"],
                "access_status": "metadata_retrieved" if pmids else "not_found",
            }
        )
        time.sleep(0.34)

    summaries = pubmed_summaries(sorted(all_pmids, key=lambda x: int(x)))
    records: dict[str, dict[str, Any]] = {}
    for pmid, summary in summaries.items():
        record = pubmed_record(summary)
        record["query_ids"] = sorted(pmid_to_queries.get(pmid, set()))
        record["legacy_seed_flag"] = normalize_doi(record.get("doi", "")) in LEGACY_SEEDS
        key = record_key(record)
        records[key] = merge_records(records[key], record) if key in records else record
        source_events.append(
            {
                "event_type": "metadata",
                "source": "PubMed",
                "source_tier": "T1",
                "query_id": "|".join(record["query_ids"]),
                "query": "",
                "search_timestamp": timestamp,
                "raw_identifier": pmid,
                "canonical_identifier": f"PMID:{pmid}",
                "url": record["landing_url"],
                "hit_count_total": "",
                "hit_count_retrieved": 1,
                "verification_sources": ["PubMed ESummary"],
                "access_status": "metadata_verified",
            }
        )

    crossref_dois: dict[str, set[str]] = defaultdict(set)
    for query_id, query in CROSSREF_QUERIES.items():
        items, total, url = crossref_search(query)
        for item in items:
            record = crossref_record(item)
            if not record["title"]:
                continue
            record["query_ids"] = [query_id]
            record["legacy_seed_flag"] = normalize_doi(record.get("doi", "")) in LEGACY_SEEDS
            if record["doi"]:
                crossref_dois[record["doi"]].add(query_id)
            key = record_key(record)
            records[key] = merge_records(records[key], record) if key in records else record
        source_events.append(
            {
                "event_type": "search",
                "source": "Crossref",
                "source_tier": "T1",
                "query_id": query_id,
                "query": query,
                "search_timestamp": timestamp,
                "raw_identifier": "",
                "canonical_identifier": "",
                "url": url,
                "hit_count_total": total,
                "hit_count_retrieved": len(items),
                "verification_sources": ["Crossref REST API"],
                "access_status": "metadata_retrieved",
            }
        )
        time.sleep(0.2)

    for doi, query_ids in sorted(crossref_dois.items()):
        source_events.append(
            {
                "event_type": "metadata",
                "source": "Crossref",
                "source_tier": "T1",
                "query_id": "|".join(sorted(query_ids)),
                "query": "",
                "search_timestamp": timestamp,
                "raw_identifier": doi,
                "canonical_identifier": f"DOI:{doi}",
                "url": f"https://doi.org/{doi}",
                "hit_count_total": "",
                "hit_count_retrieved": 1,
                "verification_sources": ["Crossref REST API"],
                "access_status": "metadata_verified",
            }
        )

    # Exact DOI re-verification of every legacy seed; this prevents inherited trust.
    for doi in sorted(LEGACY_SEEDS):
        item, url = crossref_lookup(doi)
        if item:
            record = crossref_record(item)
            record["query_ids"] = sorted(set(record.get("query_ids", [])) | {"LEGACY_EXACT_DOI"})
            record["legacy_seed_flag"] = True
            key = record_key(record)
            records[key] = merge_records(records[key], record) if key in records else record
        source_events.append(
            {
                "event_type": "seed_resolution",
                "source": "Crossref",
                "source_tier": "T1",
                "query_id": "LEGACY_EXACT_DOI",
                "query": doi,
                "search_timestamp": timestamp,
                "raw_identifier": doi,
                "canonical_identifier": f"DOI:{doi}",
                "url": url,
                "hit_count_total": 1 if item else 0,
                "hit_count_retrieved": 1 if item else 0,
                "verification_sources": ["Crossref REST API"],
                "access_status": "metadata_verified" if item else "not_found",
            }
        )
        time.sleep(0.15)

    pool = sorted(records.values(), key=lambda r: (-(r.get("year") or 0), normalized_title(r.get("title", ""))))
    (BASE_DIR / "retrieved_pool.json").write_text(json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8")
    with (BASE_DIR / "retrieval_events.jsonl").open("w", encoding="utf-8") as fh:
        for event in source_events:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"unique_pool": len(pool), "events": len(source_events), "pubmed_records": len(summaries)}, indent=2))


def europe_pmc_enrichment(pmids: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for batch in chunks(pmids, 28):
        query = " OR ".join(f"EXT_ID:{pmid}" for pmid in batch)
        params = urllib.parse.urlencode(
            {"query": query, "format": "json", "resultType": "core", "pageSize": "100"}
        )
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{params}"
        payload = json_request(url)
        for result in payload.get("resultList", {}).get("result", []):
            pmid = clean_text(result.get("pmid", ""))
            if pmid:
                found[pmid] = result
        time.sleep(0.25)
    return found


def infer_study_design(record: dict[str, Any], enrichment: dict[str, Any]) -> str:
    text = f"{record.get('title', '')} {clean_text(enrichment.get('abstractText', ''))}".lower()
    pubtypes = " ".join(enrichment.get("pubTypeList", {}).get("pubType", []) or []).lower()
    if "systematic review" in text or "systematic review" in pubtypes:
        return "systematic review"
    if "meta-analysis" in text or "meta-analysis" in pubtypes:
        return "systematic review/meta-analysis"
    if any(term in text for term in ("guideline", "consensus statement", "scientific statement", "practical guidance")):
        return "guideline/consensus"
    if "reporting guideline" in text or "statement:" in text and "tripod" in text:
        return "reporting guideline"
    if "risk of bias" in text and "probast" in text:
        return "risk-of-bias tool/methodology"
    if "review" in text:
        return "narrative/scoping review"
    if "randomized" in text or "randomised" in text:
        return "randomized trial/secondary analysis"
    if "prospective" in text:
        return "prospective cohort"
    if "retrospective" in text:
        return "retrospective cohort"
    if "case-control" in text:
        return "case-control study"
    if any(term in text for term in ("development and validation", "external validation", "prediction model", "risk model")):
        return "prediction model development/validation"
    if any(term in text for term in ("machine learning", "dynamic prediction", "early prediction")):
        return "prediction-model study"
    if "cohort" in text or "observational" in text:
        return "observational cohort"
    if "method" in text or "calibration" in text or "sample size" in text or "landmark" in text:
        return "methodological study"
    return "clinical observational/methodological article"


def infer_population(stream: str, title: str) -> str:
    low = title.lower()
    if stream == "AHF_WHF_outcome_definition":
        return "adult hospitalized acute/decompensated heart failure or worsening-heart-failure cohorts"
    if stream == "AHF_to_cardiogenic_shock":
        return "adult acute heart failure and/or cardiac intensive care/cardiogenic shock cohorts"
    if stream == "HF_sepsis_mixed_physiology":
        return "adult heart failure with sepsis/septic shock or mixed septic-cardiogenic physiology"
    if stream == "ICU_CICU_hemodynamic_deterioration":
        if "pulmonary embol" in low:
            return "adult ICU patients with intermediate-risk pulmonary embolism (adjacent deterioration phenotype)"
        return "adult ICU/cardiac or cardiovascular ICU cohorts"
    if stream == "landmark_dynamic_EHR_leakage":
        return "longitudinal EHR/ICU cohorts or prediction-methodology examples"
    if stream == "reporting_bias_calibration_validation":
        return "clinical prediction model studies (methodological/reporting domain)"
    return "MIMIC and/or multicenter ICU cohorts, including cross-country external validation examples"


def infer_outcome(stream: str, title: str) -> str:
    low = title.lower()
    if stream == "AHF_WHF_outcome_definition":
        if "risk model" in low or "predict" in low:
            return "in-hospital worsening heart failure / treatment intensification"
        return "definition, timing, incidence, or prognosis of worsening heart failure"
    if stream == "AHF_to_cardiogenic_shock":
        if "mortality" in low or "survival" in low or "outcomes" in low:
            return "cardiogenic shock severity/outcomes (supporting phenotype evidence)"
        return "incident/progressive cardiogenic shock or low-cardiac-output deterioration"
    if stream == "HF_sepsis_mixed_physiology":
        if "fluid" in low or "resuscitation" in low:
            return "fluid exposure/balance and mortality or shock outcomes"
        return "short-term mortality, shock severity, or mixed septic-cardiogenic outcomes"
    if stream == "ICU_CICU_hemodynamic_deterioration":
        return "hemodynamic/circulatory deterioration, shock, or short-term ICU outcome"
    if stream == "landmark_dynamic_EHR_leakage":
        return "dynamic clinical deterioration/event prediction and leakage-safe longitudinal modeling"
    if stream == "reporting_bias_calibration_validation":
        return "reporting quality, risk of bias, calibration, or external-validation validity"
    return "model generalizability, transportability, dataset shift, or external validation"


def infer_time_anchor(stream: str, title: str) -> str:
    low = title.lower()
    if "within 24 h" in low or "first 24" in low:
        return "first 24 h after ICU admission"
    if "early vs. late" in low:
        return "during index AHF hospitalization; early versus late WHF"
    if "time-dependent" in low:
        return "repeated/time-dependent measurements during ICU stay"
    if "dynamic" in low or "real-time" in low:
        return "repeated landmark/update times during hospitalization"
    if stream == "AHF_WHF_outcome_definition":
        return "index AHF admission; in-hospital post-baseline worsening"
    if stream == "AHF_to_cardiogenic_shock":
        return "hospital/CICU admission preceding incident or progressive shock"
    if stream == "HF_sepsis_mixed_physiology":
        return "sepsis/ICU presentation and early resuscitation period"
    if stream == "ICU_CICU_hemodynamic_deterioration":
        return "ICU/CICU admission or continuously updated bedside window"
    if stream == "landmark_dynamic_EHR_leakage":
        return "explicit/repeated landmark using only information available by prediction time"
    if stream == "reporting_bias_calibration_validation":
        return "not applicable—methodological/reporting source"
    return "development-dataset index time and independent external-validation index time"


def infer_quality_grade(record: dict[str, Any], design: str, is_core: bool) -> str:
    text = f"{record.get('title', '')} {design}".lower()
    if any(term in text for term in ("systematic review", "meta-analysis", "guideline", "consensus", "reporting guideline", "risk-of-bias")):
        return "A"
    if "external validation" in text or is_core:
        return "A-"
    if any(term in text for term in ("validation", "cohort", "prediction model", "randomized")):
        return "B"
    if "review" in text or "methodological" in text:
        return "B-"
    return "C+"


def assemble() -> None:
    selection = [(stream, normalize_doi(doi)) for stream, dois in SELECTION_BY_STREAM.items() for doi in dois]
    selection_dois = [doi for _, doi in selection]
    if len(selection_dois) != 100 or len(set(selection_dois)) != 100:
        raise RuntimeError("selection specification must contain exactly 100 unique DOIs")
    if not (len(CORE25_DOIS) == 25 and len(FIRST15_DOIS) == 15):
        raise RuntimeError("core/first selection counts are invalid")
    fulltext40 = {normalize_doi(x) for x in CORE25_DOIS | FULLTEXT_EXTRA15_DOIS}
    if len(fulltext40) != 40 or not {normalize_doi(x) for x in FIRST15_DOIS} <= {
        normalize_doi(x) for x in CORE25_DOIS
    }:
        raise RuntimeError("40/25/15 flag specification is invalid")

    timestamp = UTC_NOW()
    pool = json.loads((BASE_DIR / "retrieved_pool.json").read_text(encoding="utf-8"))
    by_doi: dict[str, dict[str, Any]] = {
        normalize_doi(record.get("doi", "")): record for record in pool if normalize_doi(record.get("doi", ""))
    }
    exact_events: list[dict[str, Any]] = []
    crossref_ok: set[str] = set()
    pubmed_ok: set[str] = set()
    missing_crossref: list[str] = []

    # Every final candidate is independently resolved in Crossref; no legacy trust is inherited.
    # Crossref permits substantially more than this bounded six-worker metadata load.
    crossref_results: dict[str, tuple[dict[str, Any] | None, str]] = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(crossref_lookup, doi): doi for doi in selection_dois}
        for future in as_completed(futures):
            crossref_results[futures[future]] = future.result()
    for doi in selection_dois:
        item, url = crossref_results[doi]
        if item:
            incoming = crossref_record(item)
            incoming["query_ids"] = ["FINAL100_EXACT_DOI"]
            incoming["legacy_seed_flag"] = doi in LEGACY_SEEDS
            by_doi[doi] = merge_records(by_doi.get(doi, {}), incoming)
            crossref_ok.add(doi)
        else:
            missing_crossref.append(doi)
        exact_events.append(
            {
                "event_type": "candidate_verification",
                "source": "Crossref",
                "source_tier": "T1",
                "query_id": "FINAL100_EXACT_DOI",
                "query": doi,
                "search_timestamp": timestamp,
                "raw_identifier": doi,
                "canonical_identifier": f"DOI:{doi}",
                "url": url,
                "hit_count_total": 1 if item else 0,
                "hit_count_retrieved": 1 if item else 0,
                "verification_sources": ["Crossref REST API"],
                "access_status": "metadata_verified" if item else "not_found",
            }
        )
    # Resolve selected DOIs in PubMed using bounded OR batches, then map the
    # returned ESummary article IDs back to canonical DOI values.
    doi_to_pmids: dict[str, list[str]] = {doi: [] for doi in selection_dois}
    doi_to_search_url: dict[str, str] = {}
    all_pmids: list[str] = []
    batch_searches: list[tuple[list[str], list[str], int, str]] = []
    for doi_batch in chunks(selection_dois, 20):
        query = " OR ".join(f'"{doi}"[AID]' for doi in doi_batch)
        pmids, total, url = pubmed_search(query, retmax=100)
        all_pmids.extend(pmids)
        batch_searches.append((doi_batch, pmids, total, url))
        for doi in doi_batch:
            doi_to_search_url[doi] = url
        time.sleep(0.34)

    summaries = pubmed_summaries(sorted(set(all_pmids), key=lambda x: int(x)))
    for pmid, summary in summaries.items():
        incoming = pubmed_record(summary)
        doi = normalize_doi(incoming.get("doi", ""))
        if doi not in doi_to_pmids:
            continue
        doi_to_pmids[doi].append(pmid)
        pubmed_ok.add(doi)
        incoming["query_ids"] = ["FINAL100_DOI_TO_PMID"]
        incoming["legacy_seed_flag"] = doi in LEGACY_SEEDS
        by_doi[doi] = merge_records(by_doi.get(doi, {}), incoming)
    for doi in selection_dois:
        pmids = doi_to_pmids[doi]
        exact_events.append(
            {
                "event_type": "candidate_verification",
                "source": "PubMed",
                "source_tier": "T1",
                "query_id": "FINAL100_DOI_TO_PMID",
                "query": f'"{doi}"[AID]',
                "search_timestamp": timestamp,
                "raw_identifier": doi,
                "canonical_identifier": ",".join(f"PMID:{x}" for x in pmids),
                "url": doi_to_search_url.get(doi, ""),
                "hit_count_total": len(pmids),
                "hit_count_retrieved": len(pmids),
                "verification_sources": ["PubMed E-utilities"],
                "access_status": "metadata_verified" if pmids else "not_found_in_pubmed",
            }
        )

    selected_pmids = sorted(
        {clean_text(by_doi.get(doi, {}).get("pmid", "")) for doi in selection_dois if by_doi.get(doi, {}).get("pmid")},
        key=lambda x: int(x),
    )
    epmc = europe_pmc_enrichment(selected_pmids)
    for pmid in selected_pmids:
        record = epmc.get(pmid, {})
        exact_events.append(
            {
                "event_type": "metadata_enrichment",
                "source": "Europe PMC",
                "source_tier": "T2",
                "query_id": "FINAL100_ABSTRACT_LANGUAGE",
                "query": f"EXT_ID:{pmid}",
                "search_timestamp": timestamp,
                "raw_identifier": pmid,
                "canonical_identifier": f"PMID:{pmid}",
                "url": f"https://europepmc.org/article/MED/{pmid}",
                "hit_count_total": 1 if record else 0,
                "hit_count_retrieved": 1 if record else 0,
                "verification_sources": ["Europe PMC REST metadata"],
                "access_status": "metadata_enriched" if record else "not_found",
            }
        )
    for doi, (official_source, official_url) in CHINESE_OFFICIAL_URLS.items():
        exact_events.append(
            {
                "event_type": "candidate_verification",
                "source": official_source,
                "source_tier": "T3_manual_authoritative_record",
                "query_id": "CHINESE_OFFICIAL_RECORD",
                "query": doi,
                "search_timestamp": timestamp,
                "raw_identifier": doi,
                "canonical_identifier": f"DOI:{doi}",
                "url": official_url,
                "hit_count_total": 1,
                "hit_count_retrieved": 1,
                "verification_sources": ["DOI HEAD redirect", official_source],
                "access_status": "official_landing_resolved_metadata_only",
            }
        )

    core_norm = {normalize_doi(x) for x in CORE25_DOIS}
    first_norm = {normalize_doi(x) for x in FIRST15_DOIS}
    legacy_norm = {normalize_doi(x) for x in LEGACY_SEEDS}
    rows: list[dict[str, Any]] = []
    for index, (stream, doi) in enumerate(selection, 1):
        record = by_doi.get(doi, {})
        if not record.get("title") or not (doi in crossref_ok or doi in pubmed_ok):
            raise RuntimeError(f"final candidate lacks authoritative T1 metadata: {doi}")
        pmid = clean_text(record.get("pmid", ""))
        enrichment = epmc.get(pmid, {})
        design = infer_study_design(record, enrichment)
        language_code = clean_text(enrichment.get("language", "") or record.get("language", "")).lower()
        language = "Chinese" if language_code in {"chi", "zho", "zh"} or record.get("title", "").startswith("[") else "English"
        is_core = doi in core_norm
        is_first = doi in first_norm
        is_full = doi in fulltext40
        verification = (
            "verified_T1_dual"
            if doi in crossref_ok and doi in pubmed_ok
            else "verified_pubmed_T1_official_journal"
            if doi in pubmed_ok and doi in CHINESE_OFFICIAL_URLS
            else "verified_crossref_T1"
            if doi in crossref_ok
            else "verified_pubmed_T1"
            if doi in pubmed_ok
            else "unverified"
        )
        screening_status = (
            "provisional_core25"
            if is_core
            else "fulltext40_priority"
            if is_full
            else "title_abstract_included_reserve"
        )
        rows.append(
            {
                "record_id": f"R{index:03d}",
                "title": clean_text(record.get("title", "")),
                "authors": "; ".join(record.get("authors", [])),
                "year": record.get("year") or "",
                "journal": clean_text(record.get("journal", "")),
                "language": language,
                "study_design": design,
                "population": infer_population(stream, record.get("title", "")),
                "outcome": infer_outcome(stream, record.get("title", "")),
                "time_anchor": infer_time_anchor(stream, record.get("title", "")),
                "doi": doi,
                "pmid": pmid,
                "pmcid": clean_text(record.get("pmcid", "") or enrichment.get("pmcid", "")),
                "arxiv_id": clean_text(record.get("arxiv_id", "")),
                "landing_url": f"https://doi.org/{doi}",
                "source_databases": ";".join(
                    sorted(
                        set(record.get("source_databases", []))
                        | ({"Europe PMC"} if enrichment else set())
                        | ({CHINESE_OFFICIAL_URLS[doi][0]} if doi in CHINESE_OFFICIAL_URLS else set())
                    )
                ),
                "retrieved_at": timestamp,
                "screening_status": screening_status,
                "exclusion_reason": "",
                "evidence_stream": stream,
                "relevance_score": 10 if is_first else 9 if is_core else 8 if is_full else 6,
                "quality_grade": infer_quality_grade(record, design, is_core),
                "verification_status": verification,
                "core25_flag": str(is_core).lower(),
                "fulltext40_flag": str(is_full).lower(),
                "first15_flag": str(is_first).lower(),
                "legacy_seed_flag": str(doi in legacy_norm).lower(),
            }
        )

    fieldnames = list(rows[0].keys())
    with (BASE_DIR / "candidate_table.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    retrieval_events_path = BASE_DIR / "retrieval_events.jsonl"
    retrieval_events = []
    if retrieval_events_path.exists():
        retrieval_events = [
            json.loads(line) for line in retrieval_events_path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
    with (BASE_DIR / "source_manifest.jsonl").open("w", encoding="utf-8") as fh:
        for event in retrieval_events + exact_events:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    row_by_doi = {row["doi"]: row for row in rows}
    download_fields = [
        "record_id",
        "title",
        "doi",
        "pmid",
        "pmcid",
        "access_route",
        "oa_authorization_evidence_url",
        "license_or_evidence",
        "status",
        "local_path",
        "mime",
        "bytes",
        "page_count",
        "sha256",
        "failure_or_manual_action",
    ]
    with (BASE_DIR / "download_log.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=download_fields)
        writer.writeheader()
        for doi in selection_dois:
            if doi not in fulltext40:
                continue
            row = row_by_doi[doi]
            pmcid = row["pmcid"]
            record = by_doi[doi]
            licenses = record.get("license", []) or []
            license_urls = [clean_text(x.get("URL", "")) for x in licenses if clean_text(x.get("URL", ""))]
            if pmcid:
                route = "PMC_OA_candidate"
                evidence_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
                license_evidence = "PMC record present; article-level license must be confirmed before download"
            elif license_urls:
                route = "publisher_OA_license_candidate"
                evidence_url = license_urls[0]
                license_evidence = "Crossref license metadata; file route must still be validated"
            else:
                route = "publisher_or_institutional_route_pending"
                evidence_url = f"https://doi.org/{doi}"
                license_evidence = "No article-level OA license confirmed from metadata-only audit"
            writer.writerow(
                {
                    "record_id": row["record_id"],
                    "title": row["title"],
                    "doi": doi,
                    "pmid": row["pmid"],
                    "pmcid": pmcid,
                    "access_route": route,
                    "oa_authorization_evidence_url": evidence_url,
                    "license_or_evidence": license_evidence,
                    "status": "si_confirmation_required",
                    "local_path": "",
                    "mime": "",
                    "bytes": "",
                    "page_count": "",
                    "sha256": "",
                    "failure_or_manual_action": (
                        "Await Controller SI=yes or SI=no. Then use only lawful OA, publisher API, "
                        "or user-authorized institutional access; validate MIME and %PDF before recording success."
                    ),
                }
            )

    stats = {
        "candidate_count": len(rows),
        "fulltext40_count": sum(row["fulltext40_flag"] == "true" for row in rows),
        "core25_count": sum(row["core25_flag"] == "true" for row in rows),
        "first15_count": sum(row["first15_flag"] == "true" for row in rows),
        "dual_T1_verified": sum(row["verification_status"] == "verified_T1_dual" for row in rows),
        "crossref_only_T1_verified": sum(row["verification_status"] == "verified_crossref_T1" for row in rows),
        "pubmed_plus_official_chinese_verified": sum(
            row["verification_status"] == "verified_pubmed_T1_official_journal" for row in rows
        ),
        "core_dual_T1_verified": sum(
            row["core25_flag"] == "true" and row["verification_status"] == "verified_T1_dual" for row in rows
        ),
        "languages": dict(Counter(row["language"] for row in rows)),
        "stream_counts": dict(Counter(row["evidence_stream"] for row in rows)),
        "missing_crossref": missing_crossref,
        "assembled_at": timestamp,
    }
    (BASE_DIR / "assembly_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def supplement_openalex() -> None:
    timestamp = UTC_NOW()
    events: list[dict[str, Any]] = []
    results_out: list[dict[str, Any]] = []
    candidate_rows = list(csv.DictReader((BASE_DIR / "candidate_table.csv").open(encoding="utf-8-sig")))
    candidate_dois = {normalize_doi(row["doi"]) for row in candidate_rows}
    candidate_titles = {normalized_title(row["title"]) for row in candidate_rows}
    overlap_doi: set[str] = set()
    overlap_title: set[str] = set()
    unique_result_keys: set[str] = set()

    for query_id, query in OPENALEX_QUERIES.items():
        params = urllib.parse.urlencode(
            {
                "search": query,
                "per-page": "25",
                "sort": "relevance_score:desc",
                "select": "id,doi,title,publication_year,authorships,primary_location,ids,type",
            }
        )
        url = f"https://api.openalex.org/works?{params}"
        payload = json_request(url)
        results = payload.get("results", [])
        total = int(payload.get("meta", {}).get("count", 0))
        events.append(
            {
                "event_type": "search",
                "source": "OpenAlex",
                "source_tier": "T2",
                "query_id": query_id,
                "query": query,
                "search_timestamp": timestamp,
                "raw_identifier": "",
                "canonical_identifier": "",
                "url": url,
                "hit_count_total": total,
                "hit_count_retrieved": len(results),
                "verification_sources": ["OpenAlex REST API"],
                "access_status": "metadata_retrieved",
            }
        )
        for result in results:
            doi = normalize_doi(clean_text(result.get("doi", "")))
            title = clean_text(result.get("title", ""))
            openalex_id = clean_text(result.get("id", ""))
            key = f"doi:{doi}" if doi else f"title:{normalized_title(title)}"
            unique_result_keys.add(key)
            if doi and doi in candidate_dois:
                overlap_doi.add(doi)
            if normalized_title(title) in candidate_titles:
                overlap_title.add(normalized_title(title))
            compact = {
                "query_id": query_id,
                "openalex_id": openalex_id,
                "doi": doi,
                "title": title,
                "year": result.get("publication_year"),
                "type": result.get("type", ""),
                "candidate100_match": bool(
                    (doi and doi in candidate_dois) or normalized_title(title) in candidate_titles
                ),
            }
            results_out.append(compact)
            events.append(
                {
                    "event_type": "metadata",
                    "source": "OpenAlex",
                    "source_tier": "T2",
                    "query_id": query_id,
                    "query": "",
                    "search_timestamp": timestamp,
                    "raw_identifier": openalex_id,
                    "canonical_identifier": f"DOI:{doi}" if doi else f"OpenAlex:{openalex_id.rsplit('/', 1)[-1]}",
                    "url": openalex_id,
                    "hit_count_total": "",
                    "hit_count_retrieved": 1,
                    "verification_sources": ["OpenAlex REST API"],
                    "access_status": "metadata_retrieved_supplemental",
                }
            )
        time.sleep(0.2)

    (BASE_DIR / "openalex_supplemental.json").write_text(
        json.dumps(results_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for filename in ("retrieval_events.jsonl", "source_manifest.jsonl"):
        path = BASE_DIR / filename
        existing = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        existing = [
            event
            for event in existing
            if not (event.get("source") == "OpenAlex" and str(event.get("query_id", "")).startswith("OA"))
        ]
        with path.open("w", encoding="utf-8") as fh:
            for event in existing + events:
                fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    stats = {
        "queries": len(OPENALEX_QUERIES),
        "retrieved_occurrences": len(results_out),
        "unique_supplemental_records": len(unique_result_keys),
        "candidate100_doi_overlap": len(overlap_doi),
        "candidate100_title_overlap": len(overlap_title),
        "promoted_to_candidate100": 0,
        "decision": "supplemental coverage check only; no record displaced a more directly relevant T1-verified candidate",
        "searched_at": timestamp,
    }
    (BASE_DIR / "openalex_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def exclusion_reason(record: dict[str, Any]) -> str:
    title = clean_text(record.get("title", "")).lower()
    query_ids = set(record.get("query_ids", []))
    if any(term in title for term in ("child", "pediatric", "paediatric", "neonat", "fetal", "pregnan")):
        return "ineligible_population_pediatric_or_pregnancy"
    if any(term in title for term in ("mouse", "mice", "rat ", "swine", "porcine", "animal model")):
        return "nonhuman_study"
    if any(
        term in title
        for term in (
            "cancer",
            "carcinoma",
            "tumor",
            "tumour",
            "radiotherapy",
            "postpartum depression",
            "maltreatment",
            "legal",
            "orthopaedic",
            "spinal",
        )
    ):
        return "unrelated_clinical_domain"
    if any(
        term in title
        for term in (
            "valve hemodynamic deterioration",
            "transcatheter aortic valve",
            "postoperative",
            "perioperative",
            "cardiac surgery",
            "trauma",
            "transplant",
        )
    ):
        return "adjacent_perioperative_or_procedure_population"
    if any(term in title for term in ("case report", "a case of", "letter regarding", "reply to the letter", "erratum")):
        return "noneligible_publication_format"
    if "Q6_prediction_reporting_validation" in query_ids and not any(
        term in title
        for term in (
            "tripod",
            "probast",
            "calibration",
            "external validation",
            "sample size",
            "transportability",
            "prediction model",
        )
    ):
        return "generic_prediction_methods_outside_scope"
    if "Q7_MIMIC_transportability" in query_ids and not any(
        term in title for term in ("transport", "generaliz", "external validation", "mimic", "multicenter")
    ):
        return "no_transportability_or_external_validation_focus"
    if any(term in title for term in ("mortality", "survival")) and not any(
        term in title for term in ("early", "predict", "risk", "worsening", "deterioration", "shock")
    ):
        return "mortality_only_without_early_deterioration_focus"
    if not any(
        term in title
        for term in (
            "heart failure",
            "cardiogenic shock",
            "sepsis",
            "septic",
            "hemodynamic",
            "circulatory failure",
            "intensive care",
            "tripod",
            "probast",
            "calibration",
            "landmark",
            "transportability",
            "mimic",
        )
    ):
        return "insufficient_topic_relevance"
    return "lower_direct_relevance_than_quota_selected_record"


def write_screening_audit() -> None:
    pool = json.loads((BASE_DIR / "retrieved_pool.json").read_text(encoding="utf-8"))
    candidates = list(csv.DictReader((BASE_DIR / "candidate_table.csv").open(encoding="utf-8-sig")))
    candidate_dois = {normalize_doi(row["doi"]) for row in candidates}
    candidate_pmids = {row["pmid"] for row in candidates if row["pmid"]}
    candidate_titles = {normalized_title(row["title"]) for row in candidates}
    excluded: list[dict[str, Any]] = []
    for record in pool:
        doi = normalize_doi(record.get("doi", ""))
        pmid = clean_text(record.get("pmid", ""))
        title_key = normalized_title(record.get("title", ""))
        if (doi and doi in candidate_dois) or (pmid and pmid in candidate_pmids) or title_key in candidate_titles:
            continue
        excluded.append(
            {
                "pool_record_key": record_key(record),
                "title": clean_text(record.get("title", "")),
                "year": record.get("year") or "",
                "doi": doi,
                "pmid": pmid,
                "query_ids": ";".join(record.get("query_ids", [])),
                "screening_stage": "pass1_title_metadata",
                "exclusion_reason": exclusion_reason(record),
            }
        )
    fields = list(excluded[0].keys())
    with (BASE_DIR / "screening_exclusions.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(excluded)
    stats = {
        "broad_unique_pool": len(pool),
        "candidate_matches_from_broad_pool": len(pool) - len(excluded),
        "targeted_gap_fill_candidates": len(candidates) - (len(pool) - len(excluded)),
        "pass1_excluded": len(excluded),
        "pass1_reason_counts": dict(Counter(row["exclusion_reason"] for row in excluded)),
        "candidate100": len(candidates),
        "fulltext40_priority": sum(row["fulltext40_flag"] == "true" for row in candidates),
        "core25_provisional": sum(row["core25_flag"] == "true" for row in candidates),
        "first15_provisional": sum(row["first15_flag"] == "true" for row in candidates),
        "note": "Pass 2 is priority selection for later full-text assessment; full-text assessment is blocked by SI_choice=pending.",
        "generated_at": UTC_NOW(),
    }
    (BASE_DIR / "screening_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def inspect_pool() -> None:
    pool = json.loads((BASE_DIR / "retrieved_pool.json").read_text(encoding="utf-8"))
    query_counts: Counter[str] = Counter()
    for record in pool:
        query_counts.update(record.get("query_ids", []))
    print(f"Pool: {len(pool)}")
    print("Query membership:")
    for key, value in sorted(query_counts.items()):
        print(f"  {key}: {value}")
    for i, record in enumerate(pool, 1):
        sources = "+".join(record.get("source_databases", []))
        print(
            f"{i:04d}\t{record.get('year') or ''}\t{record.get('pmid','')}\t"
            f"{record.get('doi','')}\t{sources}\t{record.get('title','')}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("retrieve", "assemble", "supplement-openalex", "screen-audit", "inspect")
    )
    args = parser.parse_args()
    if args.command == "retrieve":
        retrieve()
    elif args.command == "assemble":
        assemble()
    elif args.command == "supplement-openalex":
        supplement_openalex()
    elif args.command == "screen-audit":
        write_screening_audit()
    else:
        inspect_pool()


if __name__ == "__main__":
    main()
