"""Apply the existing bedside-echo and landmark gates to prioritize source review."""
import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'project_control/internal_validation/20260915_source_review'
OLD=BASE.with_name('20260915_time_gated')


def read(base,name):
    return csv.DictReader((base/name).open(encoding='utf-8-sig',newline=''))


def save(name,rows):
    with (BASE/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    global BASE, OLD
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=Path,default=BASE)
    parser.add_argument('--previous',type=Path,default=OLD)
    parser.add_argument('--review-source',type=Path,default=OLD)
    args=parser.parse_args()
    BASE,OLD=args.base,args.previous
    patients=list(read(BASE,'dhf_phenotype_pre_review.csv'))
    old={r['visit_id']:r for r in read(OLD,'dhf_phenotype_pre_review.csv')}
    timeline={r['visit_id']:r for r in read(BASE,'encounter_icu_time_audit.csv')}
    digests={r['visit_id']:r for r in read(BASE,'case_evidence_digest.csv')} if (BASE/'case_evidence_digest.csv').exists() else {}
    supplement={r['visit_id']:r for r in read(BASE,'AI_semantic_review_11.csv')} if (BASE/'AI_semantic_review_11.csv').exists() else {}
    bedside=defaultdict(list)
    for r in read(BASE,'time_gated_evidence.csv'):
        if r['domain']=='echo_result' and r['assertion']=='available' and re.search('床旁|床边',r['detail']):
            bedside[r['visit_id']].append(r)
        assert not (r['visit_id']=='7039751_3' and r['source_row']=='196750' and 'medrecord' in r['source_file'])
    rows=[];changes=[]
    for p in patients:
        visit=p['visit_id'];t=timeline[visit];has_echo=bool(bedside[visit])
        phenotype=p['phenotype_tier_pre_review'];sem=p['focused_phenotype_semantic_status'];risk=p['focused_riskset_review_status']
        if visit in supplement:
            review=supplement[visit]
            assert review['reviewed_t0']==t['t0_time'], 'Review does not apply to this episode window'
            sem=review['phenotype_semantic_status'];risk=review['riskset_review_status']
        support=phenotype in {'probable_dhf','confirmed_dhf'} or sem in {'dhf_supported','mixed_cardiac_decompensation_supported'}
        observed_failure=p['landmark_presence_status'] in {'died_by_T12','left_index_icu_by_T12'}
        if observed_failure:state='observed_exit_or_death_by_T12'
        elif not has_echo:state='no_available_bedside_echo_in_current_proxy_window'
        elif sem=='dhf_not_supported_after_source_review':state='AI_review_DHF_insufficient'
        elif risk=='exclude_preT12_vaso_lactate_proxy':state='pre12_shock_exclusion_supported_by_proxy'
        elif support and p['landmark_presence_status']=='unknown':state='DHF_candidate_needs_T12_presence_reconstruction'
        elif sem in {'dhf_supported','mixed_cardiac_decompensation_supported'}:state='AI_DHF_supported_needs_riskset_finalization'
        elif sem=='indeterminate_cardiac_attribution':state='AI_review_cardiac_attribution_unresolved'
        elif support:state='priority_DHF_semantic_and_riskset_review'
        elif phenotype=='unknown':state='unknown_HF_anchor_review'
        else:state='rule_negative_requires_sampling_audit'
        rows.append(dict(patient_id=p['patient_id'],visit_id=visit,sex=p['sex'],
            t0_time=t['t0_time'],t0_source=t['t0_source'],landmark_presence_status=p['landmark_presence_status'],
            bedside_echo_report_available=int(has_echo),bedside_echo_source_refs=';'.join(r['source_file']+'#row='+r['source_row'] for r in bedside[visit]),
            automated_phenotype_label=phenotype,automated_label_is_clinical_confirmation=0,
            AI_phenotype_review=sem,AI_riskset_review=risk,worklist_state=state,
            final_analysis_inclusion='not_frozen',source_time_flags=p['time_review_flags']))
        if old[visit]['phenotype_tier_pre_review']!=phenotype:
            changes.append(dict(visit_id=visit,old_rule_label=old[visit]['phenotype_tier_pre_review'],
                revised_rule_label=phenotype,AI_semantic_review=sem,t0_source=t['t0_source']))
    assert len(rows)==len({r['patient_id'] for r in rows})==8385
    save('cohort_disposition_working.csv',rows)
    save('rule_label_changes.csv',changes)
    priority=[]
    for r in rows:
        if r['worklist_state']!='priority_DHF_semantic_and_riskset_review':continue
        d=digests.get(r['visit_id'],{})
        priority.append(r | {k:v for k,v in d.items() if k.endswith('_evidence')})
    save('priority_DHF_review.csv',priority)
    # Preserve the actual reviewed inputs with the derived run.
    review_names=['focused_time_review_22.csv','focused_semantic_review_7.csv','document_quarantine.csv']
    for name in review_names:
        if (args.review_source/name).resolve()!=(BASE/name).resolve():
            shutil.copyfile(args.review_source/name,BASE/name)
    time_reviews=list(read(BASE,'focused_time_review_22.csv'))
    for r in time_reviews:
        if r['apply_time']=='1':assert timeline[r['visit_id']]['t0_time']==r['reviewed_t0']
    qc=dict(denominator=8385,bedside_echo_available_patients=sum(r['bedside_echo_report_available'] for r in rows),
        workflow_counts=dict(Counter(r['worklist_state'] for r in rows)),changed_rule_label_cases=len(changes),
        reviewed_time_overrides_applied=sum(r['apply_time']=='1' for r in time_reviews),
        quarantined_document_absent_from_phenotype='PASS',label_changes=dict(Counter(r['old_rule_label']+' -> '+r['revised_rule_label'] for r in changes)),
        final_cohort_frozen=False,all_8385_or_1024_semantically_reviewed=False,
        supplemental_AI_reviews=len(supplement),run_directory=str(BASE.relative_to(ROOT)) if BASE.is_absolute() else str(BASE),
        input_review_sha256={name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in review_names},
        interpretation='Mutually exclusive operational work queues under current proxy times, not final clinical exclusions; echo gate applies only to local primary cohort; secondary broad cohort remains auditable.')
    (BASE/'worklist_qc.json').write_text(json.dumps(qc,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(qc,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
