#!/usr/bin/env python3
"""Build versioned five-table internal DHF workbench from existing exports.

The outputs are auditable preparation layers. Text keyword hits and order
intervals are evidence/代理字段, never clinical gold-standard labels.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "DHF_SRR"
MASTER = ROOT / "project_control/internal_validation/20260912/icu_stay_master_20260912.csv"
OUT = ROOT / "project_control/internal_validation/20260914_workbench"
OUT.mkdir(parents=True, exist_ok=True)

EXCLUDED = {"9204020"}
DATE_RE = re.compile(r"(?:19|20)\d{2}[-/.年]\s*\d{1,2}[-/.月]\s*\d{1,2}(?:日|号)?(?:\s+|T)\d{1,2}:\d{2}(?::\d{2})?")
PATTERNS = {
    "hf_anchor": re.compile(r"急性心衰|急性心力衰竭|心力衰竭|心功能不全|心源性休克|心肌病|严重瓣膜", re.I),
    "congestion": re.compile(r"肺水肿|肺充血|肺淤血|湿啰音|端坐呼吸|呼吸困难|颈静脉怒张|外周水肿|低氧恶化", re.I),
    "management": re.compile(r"利尿|呋塞米|托拉塞米|无创通气|呼吸机|升压|正性肌力|硝酸甘油|扩血管|液体管理", re.I),
    "alternative": re.compile(r"肺炎|ARDS|误吸|脓毒症|感染|肺出血|创伤|术后|肾功能不全", re.I),
}

def parse_dt(v: str | None) -> dt.datetime | None:
    if not v: return None
    s = str(v).strip().replace("年", "-").replace("月", "-").replace("日", "").replace("号", "")
    s = s.replace("/", "-").replace(".", "-").replace("T", " ")
    s = re.sub(r"\s+", " ", s).strip()
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try: return dt.datetime.strptime(s, f)
        except ValueError: pass
    return None

def fmt(x: dt.datetime | None) -> str: return x.strftime("%Y-%m-%d %H:%M:%S") if x else ""

def read(path: Path):
    with path.open(encoding="utf-8-sig", newline="", errors="replace") as f:
        yield from csv.DictReader(f)

def write(name: str, rows: list[dict]):
    path = OUT / name
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    return path

def main():
    master = [r for r in read(MASTER) if r.get("patient_id") not in EXCLUDED and r.get("index_adult_icu_flag") == "1"]
    keys = {(r["patient_id"], r["visit_id"]): r for r in master}

    # 1 encounter_icu
    encounter = []
    for r in master:
        encounter.append({
            "patient_id": r["patient_id"], "sex": r["sex"], "visit_id": r["visit_id"],
            "episode_id": f"{r['visit_id']}_index", "index_flag": 1,
            "age_at_encounter": r["age_at_encounter"], "date_of_birth": r["date_of_birth"],
            "encounter_date": r["encounter_date"], "admit_time": r["encounter_date"],
            "icu_intime": r["t0_candidate"], "icu_intime_source": r["t0_candidate_source"],
            "icu_outtime_proxy": r["icu_out_time_first"], "icu_outtime_source": "icu_document_out_time" if r["icu_out_time_first"] else "missing",
            "transfer_time_proxy": r["icu_transfer_time_first"], "structured_discharge_time": r["structured_discharge_time"],
            "encounter_status": r["encounter_status"], "time_qc_status": r["time_qc_status"],
            "multiple_icu_document_flag": int(int(r.get("icu_doc_in_count", 0) or 0) > 1 or int(r.get("icu_doc_transfer_count", 0) or 0) > 1),
            "outcome_status": "needs_document_outcome_parse",
        })

    # 2 document evidence, retaining only bounded snippets and aggregate flags.
    docs = []
    doc_paths = sorted(DATA.glob("*/02_rdr_medrecord_list.csv"))
    for path in doc_paths:
        for r in read(path):
            key = (r.get("患者ID", ""), r.get("就诊号", ""))
            if key not in keys: continue
            text = re.sub(r"[\r\n\t ]+", " ", r.get("文本病历", "") or "")
            name = r.get("文书名称", "") or ""
            hits = {k: int(p.search(text) is not None) for k, p in PATTERNS.items()}
            relevant = name in {"入ICU记录", "出ICU记录", "ICU转病房记录", "查房记录(SOAP)", "查房记录(简单)", "普通病程录", "首次病程录（新版）", "会诊结果", "出院记录", "死亡记录"} or any(hits.values())
            if not relevant: continue
            docs.append({
                "patient_id": key[0], "sex": r.get("性别", ""), "visit_id": key[1],
                "document_id": r.get("文档编号", ""), "document_name": name,
                "document_created_time": r.get("创建日期", ""), "department": r.get("就诊科室", ""),
                "nonempty_text_flag": int(bool(text)), "hf_anchor_hit": hits["hf_anchor"],
                "congestion_hit": hits["congestion"], "management_hit": hits["management"],
                "alternative_hit": hits["alternative"], "evidence_basis": "document_text_keyword_recall",
            })

    # 3 diagnostic evidence (exams + labs), preserving report-time semantics.
    diagnostics = []
    for path in sorted(DATA.glob("*/02_rdr_exam_master_report.csv")):
        for r in read(path):
            key = (r.get("患者ID", ""), r.get("就诊号", ""))
            if key not in keys: continue
            text = f"{r.get('检查结论','')} {r.get('检查所见','')}"
            diagnostics.append({
                "patient_id": key[0], "sex": r.get("性别", ""), "visit_id": key[1], "evidence_type": "exam",
                "report_time_proxy": r.get("检查[报告]日期", ""), "verification_time": r.get("审核日期", ""),
                "test_name": r.get("项目名称", ""), "test_type": r.get("检查类型", ""),
                "result_value": "", "result_text": text[:1000], "abnormal_flag_raw": r.get("是否异常", ""),
                "evidence_basis": "report_time_proxy",
            })
    for path in sorted(DATA.glob("*/02_rdr_lab_test_data.csv")):
        for r in read(path):
            key = (r.get("患者ID", ""), r.get("就诊号", ""))
            if key not in keys: continue
            diagnostics.append({
                "patient_id": key[0], "sex": r.get("性别", ""), "visit_id": key[1], "evidence_type": "lab",
                "report_time_proxy": r.get("检验[报告]日期", ""), "verification_time": "",
                "test_name": r.get("检验指标", ""), "test_type": r.get("检验类型", ""),
                "result_value": r.get("检验结果数值", "") or r.get("检验结果值", ""), "result_text": r.get("结果备注", ""),
                "abnormal_flag_raw": r.get("异常标志", ""), "evidence_basis": "result_time_proxy",
            })

    # 4 treatment orders as interval proxies.
    treatments = []
    for path in sorted(DATA.glob("*/02_rdr_orders.csv")):
        for r in read(path):
            key = (r.get("患者ID", ""), r.get("就诊号", ""))
            if key not in keys: continue
            name = r.get("药品名称", "") or ""
            treatments.append({
                "patient_id": key[0], "sex": r.get("性别", ""), "visit_id": key[1], "order_id": r.get("医嘱序号", ""),
                "medication_name": name, "route": r.get("给药途径", ""), "dose": r.get("剂量", ""), "dose_unit": r.get("剂量单位", ""),
                "order_start_time": r.get("开嘱时间", ""), "order_stop_time": r.get("停嘱时间", ""),
                "duration": r.get("用药时长", ""), "order_status": r.get("医嘱状态", ""),
                "long_term_flag": r.get("是否长期医嘱", ""), "exposure_basis": "order_interval_proxy",
            })

    # 5 phenotype screen: aggregate only; no time-window claim until document time parsing is expanded.
    by_key = defaultdict(lambda: Counter())
    for d in docs:
        c = by_key[(d["patient_id"], d["visit_id"])]
        for k in ("hf_anchor_hit", "congestion_hit", "management_hit", "alternative_hit"):
            c[k] += int(d[k])
    phenotype = []
    for r in master:
        c = by_key[(r["patient_id"], r["visit_id"])]
        a, b, m, alt = c["hf_anchor_hit"] > 0, c["congestion_hit"] > 0, c["management_hit"] > 0, c["alternative_hit"] > 0
        phenotype.append({
            "patient_id": r["patient_id"], "sex": r["sex"], "visit_id": r["visit_id"], "episode_id": f"{r['visit_id']}_index",
            "adult_index_flag": 1, "t0_candidate": r["t0_candidate"], "t0_source": r["t0_candidate_source"],
            "hf_anchor_document_hit": int(a), "congestion_document_hit": int(b), "management_document_hit": int(m),
            "alternative_explanation_hit": int(alt), "document_hf_hit_count": c["hf_anchor_hit"],
            "document_congestion_hit_count": c["congestion_hit"], "document_management_hit_count": c["management_hit"],
            "dhf_recall_screen_status": "candidate_recall_only" if a and b else "not_supported_by_document_recall",
            "final_dhf_tier": "pending_time_gated_review", "label_basis": "document_recall_without_T0_T12_gate",
        })

    paths = [write("encounter_icu.csv", encounter), write("icu_note_evidence.csv", docs), write("diagnostic_evidence.csv", diagnostics), write("treatment_order_proxy.csv", treatments), write("dhf_phenotype_screen.csv", phenotype)]
    summary = {
        "generated_at": "2026-09-14", "adult_index_rows": len(master), "excluded_patient": "9204020",
        "rows": {p.name: sum(1 for _ in read(p)) for p in paths},
        "phenotype_screen": Counter(r["dhf_recall_screen_status"] for r in phenotype),
        "time_policy": "T0/T12 not yet applied to every evidence row; report/result dates and order intervals retain proxy basis",
        "raw_data_modified": False,
    }
    (OUT / "workbench_qc.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=dict), encoding="utf-8")
    (ROOT / "project_control/task_reports/TASK_REPORT_2026-09-14_WORKBENCH_BUILD.md").write_text(
        "# 任务报告：院内 DHF 五张工作表构建（2026-09-14）\n\n"
        f"- 成人 index ICU 主表：{len(master):,} 行；已排除 9204020。\n"
        f"- 文书证据表：{len(docs):,} 行；检查检验表：{len(diagnostics):,} 行；医嘱代理表：{len(treatments):,} 行。\n"
        f"- DHF 文书高召回表型筛查：{sum(r['dhf_recall_screen_status']=='candidate_recall_only' for r in phenotype):,} 行进入候选排序层。\n"
        "- 当前标签仍为 `candidate_recall_only`/`pending_time_gated_review`，因为文书创建时间与报告时间不能自动替代全部 T0/T12 事件时间；原始来源和代理证据等级均已保留。\n\n"
        "## 输出\n\n" + "\n".join(f"- `{p.relative_to(ROOT)}`" for p in paths) + "\n- `project_control/internal_validation/20260914_workbench/workbench_qc.json`\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=dict))

if __name__ == "__main__": main()
