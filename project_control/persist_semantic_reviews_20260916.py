"""Validate and export the explicitly source-read AI decisions, never gold labels."""
import csv
import json
from collections import Counter
from pathlib import Path

from advance_internal_dhf_v20260915 import ROOT, read, time, H

BASE = ROOT/'project_control/internal_validation/20260916_semantic_corrected'
CACHE = BASE.with_name('20260916_case_review')


def main():
    decisions = json.loads((CACHE/'AI_decisions_11.json').read_text())
    timeline = {r['visit_id']: r for r in read(BASE/'encounter_icu_time_audit.csv')}
    with (CACHE/'source_notes.jsonl').open() as f:
        notes = {(r['visit_id'], r['source_row']): r for r in map(json.loads, f)}
    evidence = {}
    for r in read(BASE/'time_gated_evidence.csv'):
        if r['domain'] == 'echo_result':
            evidence[r['visit_id'], int(r['source_row'])] = r
    orders = {(r['visit_id'], int(r['source_row'])): r for r in read(BASE/'treatment_orders_targeted.csv')}
    risks = {r['visit_id']: r for r in read(BASE/'pre12_shock_proxy_working.csv')} if (BASE/'pre12_shock_proxy_working.csv').exists() else {}
    rows = []
    for d in decisions:
        v = d['visit_id']; t0 = time(d['reviewed_t0'])
        assert d['reviewed_t0'] == timeline[v]['t0_time'], 'Changed T0 requires renewed source review'
        refs = []; availability = []
        for n in d['note_rows']:
            note = notes[v, n]
            assert t0-24*H <= time(note['created']) < t0+12*H, (v, n)
            refs.append(note['source_file']+'#row='+str(n))
            availability.append(str(n)+'@'+note['created'])
        for n in d['echo_rows']:
            e = evidence[v, n]
            refs.append(e['source_file']+'#row='+str(n))
        for n in d['order_rows']:
            e = orders[v, n]
            refs.append(e['source_file']+'#row='+str(n))
        r = {k: val for k, val in d.items() if not k.endswith('_rows')}
        r.update(riskset_review_status='exclude_dhf_insufficient' if d['phenotype_semantic_status']=='dhf_not_supported_after_source_review' else 'pending_pre12_proxy_and_source_reconciliation',
                 risk_proxy_work_state=risks.get(v, {}).get('risk_proxy_work_state', 'pending_extraction'),
                 max_pre12_lactate_numeric=risks.get(v, {}).get('max_pre12_lactate_numeric', ''),
                 source_refs=';'.join(refs), note_creation_time_proxies=';'.join(availability),
                 review_scope='full_selected_notes_plus_report_order_crosscheck_not_all_encounter_documents',
                 reviewer_type='AI_pre_review_not_independent_physician', review_date='2026-09-16',
                 final_analysis_inclusion='not_frozen')
        rows.append(r)
    with (BASE/'AI_semantic_review_11.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    qc=dict(reviewed_cases=len(rows), status_counts=dict(Counter(r['phenotype_semantic_status'] for r in rows)),
            source_note_references=sum(len(d['note_rows']) for d in decisions),
            all_review_t0_match=True, all_note_creation_proxies_within_window=True,
            source_references_resolved=True, independent_clinical_gold_standard=False,
            final_cohort_frozen=False)
    (BASE/'AI_review_qc.json').write_text(json.dumps(qc,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(qc,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
