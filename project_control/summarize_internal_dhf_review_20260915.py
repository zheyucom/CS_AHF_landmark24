"""Create compact case evidence packets and validate the completed local run."""
import csv
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from advance_internal_dhf_v20260915 import H, time

BASE=Path(__file__).resolve().parent/'internal_validation/20260915_time_gated'


def read(name):
    with (BASE/name).open(encoding='utf-8-sig',newline='') as f:
        yield from csv.DictReader(f)


def main():
    patients=list(read('dhf_phenotype_pre_review.csv'))
    timelines={r['visit_id']:r for r in read('encounter_icu_time_audit.csv')}
    assert len(patients)==len(timelines)==8385
    assert len({r['patient_id'] for r in patients})==8385
    assert not any(r['patient_id']=='9204020' for r in patients)
    for r in timelines.values():
        assert time(r['t12_time'])-time(r['t0_time'])==12*H
        if r['index_icu_outtime']:
            assert time(r['index_icu_outtime'])>time(r['t0_time'])
    assert all(r['final_analysis_inclusion']=='not_frozen' for r in patients)
    selected={r['visit_id']:r for r in patients if r['phenotype_tier_pre_review'] in {'confirmed_dhf','probable_dhf','unknown'} or r['prior_semantic_review']=='retain_candidate'}
    snippets=defaultdict(lambda:defaultdict(list))
    accepted={'affirmed','uncertain','order_proxy','measured'}
    evidence_count=0
    for r in read('time_gated_evidence.csv'):
        evidence_count+=1
        t=time(r['available_time_proxy']);t0=time(timelines[r['visit_id']]['t0_time'])
        # Ongoing order starts can precede the window; all clinical note/lab/
        # exam availability proxies must lie inside the declared interval.
        if r['source']!='order_interval_proxy':assert t0-24*H<=t<t0+12*H
        if r['visit_id'] not in selected or r['assertion'] not in accepted:continue
        group=r['domain']
        dest=snippets[r['visit_id']][group]
        if len(dest)<3:
            dest.append(f"{r['assertion']} | {r['available_time_proxy']} | {r['excerpt'][:260]} | {r['source_file']}#row={r['source_row']}")
    rows=[]
    for visit,r in selected.items():
        t=timelines[visit]
        row={k:r[k] for k in ['patient_id','sex','visit_id','phenotype_tier_pre_review','decision_reason','prior_semantic_review','prior_semantic_reason','time_review_flags','landmark_presence_status']}
        row.update(t0_time=t['t0_time'],t0_source=t['t0_source'],icu_out_time=t['index_icu_outtime'],
                   disposition='agent_pre_review_queue_not_new_user_questionnaire')
        for domain in ['hf','congestion','symptom','management','iv_loop','echo_abnormal','natriuretic_peptide','alternative']:
            row[domain+'_evidence']='\n'.join(snippets[visit][domain])
        rows.append(row)
    with (BASE/'case_evidence_digest.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    report=dict(patient_unique_key_check='PASS',adult_exclusion_check='PASS',t12_offset_check='PASS',
                exit_order_check='PASS',availability_window_check='PASS',final_labels_not_fabricated='PASS',
                evidence_rows_checked=evidence_count,case_digest_rows=len(rows),
                bnp_available_patients=sum(r['bnp_status']=='measured_unit_not_exported' for r in patients),
                prior_AI_sample_comparison={str(k):v for k,v in Counter((r['prior_semantic_review'],r['phenotype_tier_pre_review']) for r in patients if r['prior_semantic_review']!='not_sampled').items()},
                comparison_is_independent_validation=False)
    (BASE/'validation_qc.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=Path,default=BASE)
    BASE=parser.parse_args().base.resolve()
    main()
