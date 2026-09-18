"""Link existing AI report review to full MIMIC candidate evidence, without freezing DHF."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE/'review_linkage_20260915'
RAW = BASE/'dhf_radiology_raw_landmark12_v1_complete.csv'
COMPACT = BASE/'dhf_radiology_report_audit_landmark12_v1.csv'
REVIEW = BASE/'controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_merged_draft_20260914.csv'
PATIENT = BASE/'landmark12_audit_20260904/dhf_multidomain_patient_level_audit_landmark12_20260904.csv'


def read(p):
    return list(csv.DictReader(p.open(encoding='utf-8-sig', newline='')))


def save(name, rows):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def key(r):
    return r['stay_id'],r['note_id']


def yes(r, col):
    return r[col] in {'1','1.0','true','True'}


def main():
    OUT.mkdir(exist_ok=True)
    raw=read(RAW);compact={key(r):r for r in read(COMPACT)}
    reviewed={key(r):r for r in read(REVIEW)};patients=read(PATIENT)
    assert len(raw)==len({key(r) for r in raw})==len(compact)==7828
    assert set(compact)=={key(r) for r in raw}
    assert len(reviewed)==300 and set(reviewed)<=set(compact)
    assert len(patients)==len({r['stay_id'] for r in patients})==5549
    by_stay=defaultdict(list);report_rows=[];availability_disagreements=[]
    for r in raw:
        c=compact[key(r)];a=reviewed.get(key(r),{})
        t12=datetime.fromisoformat(r['landmark12_time'])
        chart=datetime.fromisoformat(r['charttime'])
        assert datetime.fromisoformat(r['window_start'])<=chart<t12
        available=bool(r['storetime'] and datetime.fromisoformat(r['storetime'])<t12)
        # Unknown storetime cannot prove a report was available. Keep the
        # historical flag alongside this strict gate for reproducibility.
        original_available=yes(r,'report_available_by_t12_flag')
        if available!=original_available:
            availability_disagreements.append(dict(stay_id=r['stay_id'],note_id=r['note_id']))
        old=available and c['report_modality'] in {'chest_xray','chest_ct'} and yes(r,'positive_congestion_evidence_flag') and not yes(r,'uncertainty_hit')
        reviewed_definite=bool(a and a['final_report_scope']=='chest_radiology' and a['final_congestion_label']=='definite_congestion')
        effective=available and reviewed_definite if a else old
        if a:
            assert a['final_report_available_by_t12_label'] in {'yes','no','uncertain','indeterminate',''}
            assert ' '.join(a['report_text'].split())==' '.join(r['text'].split()), key(r)
        row=dict(stay_id=r['stay_id'],note_id=r['note_id'],charttime=r['charttime'],storetime=r['storetime'],
                 landmark12_time=r['landmark12_time'],available_by_T12_strict=int(available),
                 original_available_flag=int(original_available),original_modality=c['report_modality'],
                 original_definite_lung_rule=int(old),review_annotation_id=a.get('annotation_id',''),
                 reviewed_scope=a.get('final_report_scope','not_reviewed'),
                 reviewed_congestion=a.get('final_congestion_label','not_reviewed'),
                 reviewed_alternative=a.get('final_alternative_explanation_label','not_reviewed'),
                 reviewed_definite_available=int(available and reviewed_definite),
                 lung_evidence_after_review=int(effective),
                 label_basis='AI_pre_review' if a else 'unreviewed_rule_screen',
                 review_comment=a.get('final_comments',''),final_DHF_inclusion='not_frozen')
        report_rows.append(row);by_stay[r['stay_id']].append(row)
    patient_rows=[]
    for p in patients:
        rr=by_stay[p['stay_id']]
        assert len(rr)==int(p['n_reports_window'])
        n_review=sum(bool(r['review_annotation_id']) for r in rr)
        original=any(r['original_definite_lung_rule'] for r in rr)
        lung=any(r['lung_evidence_after_review'] for r in rr)
        support=p['pre_t0_iv_loop_flag']=='1' or p['pre_t0_ntprobnp_ge300_support_flag']=='1'
        patient_rows.append(dict(stay_id=p['stay_id'],subject_id=p['subject_id'],hadm_id=p['hadm_id'],
            n_reports=len(rr),n_AI_reviewed_reports=n_review,
            all_existing_reports_reviewed=int(bool(rr) and n_review==len(rr)),
            original_definite_lung_screen=int(original),lung_evidence_after_review=int(lung),
            AI_reviewed_definite_lung_available=int(any(r['reviewed_definite_available'] for r in rr)),
            pre_T0_loop_or_NTproBNP_support=int(support),lung_plus_support_candidate=int(lung and support),
            legacy_candidate_outcome=p['final_state'],
            phenotype_status='multidomain_candidate_needs_current_HF_and_management_context' if lung and support else 'needs_other_domains_or_negative_review',
            final_DHF_inclusion='not_frozen'))
    save('report_evidence_7828.csv',report_rows);save('candidate_evidence_5549.csv',patient_rows)
    layers=[]
    for label,predicate in [
        ('all_existing_candidates',lambda r:True),
        ('original_definite_lung_screen',lambda r:r['original_definite_lung_screen']),
        ('lung_screen_after_300_AI_reviews',lambda r:r['lung_evidence_after_review']),
        ('AI_reviewed_definite_lung_available',lambda r:r['AI_reviewed_definite_lung_available']),
        ('lung_plus_preT0_support_candidate',lambda r:r['lung_plus_support_candidate'])]:
        subset=[r for r in patient_rows if predicate(r)];counts=Counter(r['legacy_candidate_outcome'] for r in subset)
        assert sum(counts.values())==len(subset) and set(counts)<={'event','compete','censor'}
        layers.append(dict(evidence_layer=label,n_candidates=len(subset),legacy_events=counts['event'],
            legacy_competing=counts['compete'],legacy_censored=counts['censor'],
            interpretation='evidence_screen_only_not_final_DHF_outcomes'))
    save('evidence_layer_counts.csv',layers)
    qc=dict(report_rows=len(report_rows),review_rows_linked=len(reviewed),candidate_rows=len(patient_rows),
        candidates_with_review=sum(r['n_AI_reviewed_reports']>0 for r in patient_rows),
        reports_with_changed_definite_flag=sum(r['original_definite_lung_rule']!=r['lung_evidence_after_review'] for r in report_rows),
        candidates_with_changed_lung_flag=sum(r['original_definite_lung_screen']!=r['lung_evidence_after_review'] for r in patient_rows),
        reviewed_scope_counts=dict(Counter(r['final_report_scope'] for r in reviewed.values())),
        reviewed_congestion_counts=dict(Counter(r['final_congestion_label'] for r in reviewed.values())),
        availability_disagreement_n=len(availability_disagreements),
        review_raw_text_match='PASS',report_patient_count_match='PASS',
        final_cohort_frozen=False,independent_physician_validation=False,
        selection_warning='300 stratified AI-reviewed reports do not estimate population prevalence or independent accuracy',
        source_sha256={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [RAW,COMPACT,REVIEW,PATIENT]})
    (OUT/'qc.json').write_text(json.dumps(qc,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(qc,ensure_ascii=False,indent=2));print(json.dumps(layers,indent=2))


if __name__=='__main__':main()
