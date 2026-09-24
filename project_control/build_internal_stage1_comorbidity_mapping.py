#!/usr/bin/env python3
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / 'project_control'
OUT = CONTROL / 'runs' / '20260924_internal_stage1_g7_comorbidity_mapping'
OUT.mkdir(parents=True, exist_ok=True)

G2 = CONTROL / 'runs/20260924_internal_stage1_g2_chronology/episode_chronology_reconciled.csv'
G3 = CONTROL / 'runs/20260924_internal_stage1_g3_phenotype/dhf_abc_evidence_ledger_v1.csv'
DIAGNOSIS_FILES = [
    ROOT / 'DHF_SRR/DHF--男_诊断信息20260911203952612/02_rdr_diagnosis.csv',
    ROOT / 'DHF_SRR/DHF--女_诊断信息20260911211222860/02_rdr_diagnosis.csv',
]
HISTORY_FILES = [
    ROOT / 'DHF_SRR/DHF--男_入院病史20260911204028934/02_rdr_admit_info.csv',
    ROOT / 'DHF_SRR/DHF--女_入院病史20260911200821856/02_rdr_admit_info.csv',
]

DOMAIN_RULES = {
    'hypertension': ['高血压'],
    'diabetes': ['糖尿病'],
    'ischemic_heart_disease': ['冠心病', '冠状动脉粥样硬化性心脏病', '缺血性心脏病', '心肌梗死', '心肌缺血'],
    'chronic_kidney_disease': ['慢性肾', '肾功能不全', '慢性肾衰', '尿毒症', '终末期肾'],
    'atrial_fibrillation_or_arrhythmia': ['房颤', '心房颤动', '心律失常'],
    'chronic_obstructive_lung_disease': ['慢性阻塞性肺', '慢阻肺', 'COPD', '肺气肿', '慢性支气管炎'],
    'prior_stroke_or_cerebrovascular_disease': ['脑梗', '脑出血', '脑卒中', '卒中', '脑血管病', '短暂性脑缺血', 'TIA'],
    'chronic_liver_disease': ['肝硬化', '慢性肝', '肝功能不全', '慢性肝炎'],
}
NEGATIONS = ['否认', '无', '未见', '没有', '未发现', '不伴', '排除', '否定', '未诉']

def read_csv(path):
    with path.open('r', encoding='utf-8-sig', newline='', errors='replace') as f:
        return list(csv.DictReader(f))

def valid_time(value):
    value = (value or '').strip()
    return value or None

def is_pre_t0(event_time, t0):
    event_time = valid_time(event_time)
    t0 = valid_time(t0)
    return bool(event_time and t0 and event_time <= t0)

def find_hits(text, terms):
    text = text or ''
    hits = []
    for term in terms:
        for match in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            start, end = match.span()
            context = text[max(0, start - 10):min(len(text), end + 12)]
            neg = any(negation in context for negation in NEGATIONS)
            hits.append({'term': term, 'negated': neg, 'context': context[:180]})
    return hits

def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

def main():
    g2 = read_csv(G2)
    g3 = read_csv(G3)
    main_g3 = [r for r in g3 if r.get('main_rule_supported_flag') == '1']
    g2_by_visit = {r.get('visit_id', ''): r for r in g2}
    main = {}
    for r in main_g3:
        visit_id = r.get('visit_id', '')
        if visit_id not in g2_by_visit:
            raise SystemExit('missing chronology row: ' + visit_id)
        c = g2_by_visit[visit_id]
        main[visit_id] = {'patient_id': r.get('patient_id', ''), 'sex': r.get('sex', ''), 'visit_id': visit_id, 't0_time': c.get('t0_time', '')}
    if len(main) != 773:
        raise SystemExit(f'expected 773 main episodes, got {len(main)}')

    evidence = []
    diagnosis_record_available = set()
    history_record_available = set()
    for path in DIAGNOSIS_FILES:
        for row in read_csv(path):
            visit_id = row.get('就诊号', '')
            if visit_id not in main or not is_pre_t0(row.get('诊断时间'), main[visit_id]['t0_time']):
                continue
            diagnosis_record_available.add(visit_id)
            for domain, terms in DOMAIN_RULES.items():
                for hit in find_hits(row.get('诊断名称', ''), terms):
                    evidence.append({
                        'patient_id': main[visit_id]['patient_id'], 'sex': main[visit_id]['sex'], 'visit_id': visit_id,
                        't0_time': main[visit_id]['t0_time'], 'domain': domain, 'source_type': 'pre_T0_diagnosis',
                        'source_time': row.get('诊断时间', ''), 'evidence_status': 'negative' if hit['negated'] else 'present',
                        'matched_term': hit['term'], 'context_excerpt': hit['context'],
                    })

    history_text_keys = ['主诉', '现病史', '婚育史', '饮酒史', '过敏史', '吸烟史', '用药史']
    for path in HISTORY_FILES:
        for row in read_csv(path):
            visit_id = row.get('就诊号', '')
            if visit_id not in main or not is_pre_t0(row.get('创建日期'), main[visit_id]['t0_time']):
                continue
            history_record_available.add(visit_id)
            text = ' '.join((row.get(k, '') or '') for k in history_text_keys)
            for domain, terms in DOMAIN_RULES.items():
                for hit in find_hits(text, terms):
                    evidence.append({
                        'patient_id': main[visit_id]['patient_id'], 'sex': main[visit_id]['sex'], 'visit_id': visit_id,
                        't0_time': main[visit_id]['t0_time'], 'domain': domain, 'source_type': 'pre_T0_admission_history',
                        'source_time': row.get('创建日期', ''), 'evidence_status': 'negative' if hit['negated'] else 'present',
                        'matched_term': hit['term'], 'context_excerpt': hit['context'],
                    })

    write_csv(OUT / 'comorbidity_evidence_ledger_v1.csv', evidence, [
        'patient_id','sex','visit_id','t0_time','domain','source_type','source_time',
        'evidence_status','matched_term','context_excerpt'
    ])

    summary_rows = []
    status_counts = {}
    by_visit_domain = {}
    for ev in evidence:
        by_visit_domain.setdefault((ev['visit_id'], ev['domain']), []).append(ev)
    for visit_id, base in sorted(main.items()):
        row = dict(base)
        row['pre_T0_diagnosis_record_available'] = '1' if visit_id in diagnosis_record_available else '0'
        row['pre_T0_admission_history_record_available'] = '1' if visit_id in history_record_available else '0'
        for domain in DOMAIN_RULES:
            ev = by_visit_domain.get((visit_id, domain), [])
            positive = any(e['evidence_status'] == 'present' for e in ev)
            negative = any(e['evidence_status'] == 'negative' for e in ev)
            status = 'conflict' if positive and negative else 'present' if positive else 'negative' if negative else 'unknown'
            row[domain + '_status'] = status
            row[domain + '_source_count'] = str(len(ev))
            row[domain + '_source_types'] = '|'.join(sorted(set(e['source_type'] for e in ev)))
            status_counts.setdefault(domain, Counter())[status] += 1
        summary_rows.append(row)

    summary_fields = ['patient_id','sex','visit_id','t0_time','pre_T0_diagnosis_record_available','pre_T0_admission_history_record_available']
    for domain in DOMAIN_RULES:
        summary_fields += [domain + '_status', domain + '_source_count', domain + '_source_types']
    write_csv(OUT / 'comorbidity_episode_summary_v1.csv', summary_rows, summary_fields)

    audit = {
        'run_id': '20260924_internal_stage1_g7_comorbidity_mapping',
        'status': 'PASS_WITH_UNKNOWN_SEMANTICS',
        'main_episode_n': len(main),
        'pre_T0_diagnosis_record_available_n': len(diagnosis_record_available),
        'pre_T0_admission_history_record_available_n': len(history_record_available),
        'evidence_row_n': len(evidence),
        'domain_status_counts': {domain: dict(counter) for domain, counter in status_counts.items()},
        'unknown_is_not_negative': True,
        'post_T0_records_used': False,
        'outcome_fields_used': False,
        'mapping_is_clinical_gold_standard': False,
        'mapping_note': 'Keyword-assisted source mapping for candidate-factor audit; clinical review and final factor contract remain pending.',
        'domain_rules': DOMAIN_RULES,
        'negation_patterns': NEGATIONS,
    }
    (OUT / 'comorbidity_mapping_audit_v1.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': audit['status'], 'main_episode_n': len(main), 'pre_T0_diagnosis_record_available_n': len(diagnosis_record_available), 'pre_T0_admission_history_record_available_n': len(history_record_available), 'evidence_row_n': len(evidence), 'out': str(OUT)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
