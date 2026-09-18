"""Cache source notes for current phenotype and landmark review worklists."""
import json
import re
import argparse
from collections import Counter
from pathlib import Path

from advance_internal_dhf_v20260915 import ROOT, DATA, read, time, H, blank_icu_template

DEFAULT_BASE=ROOT/'project_control/internal_validation/20260916_semantic_corrected'
DEFAULT_OUT=ROOT/'project_control/internal_validation/20260916_case_review'


def main():
    parser=argparse.ArgumentParser(description='Cache source notes for the current semantic-corrected worklist.')
    parser.add_argument('--base', type=Path, default=DEFAULT_BASE,
                        help='run directory containing cohort_disposition_working.csv')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT,
                        help='cache output directory')
    args=parser.parse_args()
    BASE=args.base if args.base.is_absolute() else ROOT/args.base
    OUT=args.out if args.out.is_absolute() else ROOT/args.out
    OUT.mkdir(exist_ok=True)
    wanted={'priority_DHF_semantic_and_riskset_review','DHF_candidate_needs_T12_presence_reconstruction','unknown_HF_anchor_review'}
    cases={r['visit_id']:r for r in read(BASE/'cohort_disposition_working.csv') if r['worklist_state'] in wanted}
    counts=Counter()
    with (OUT/'source_notes.jsonl').open('w',encoding='utf-8') as f:
        for path in sorted(DATA.glob('*/02_rdr_medrecord_list.csv')):
            for n,r in enumerate(read(path),2):
                visit=r['就诊号']
                if visit not in cases:continue
                t0=time(cases[visit]['t0_time']);created=time(r['创建日期']);name=r['文书名称']
                event_doc=bool(re.search('入ICU|出ICU|ICU转|转入记录|转出记录|死亡记录|出院记录',name,re.I))
                near=bool(created and t0-24*H<=created<t0+72*H)
                if not near and not event_doc:continue
                obj=dict(visit_id=visit,source_file=str(path.relative_to(ROOT)),source_row=n,name=name,
                    created=r['创建日期'],text=r['文本病历'],in_phenotype_window=bool(created and t0-24*H<=created<t0+12*H),
                    blank_template=blank_icu_template(name,r['文本病历']))
                f.write(json.dumps(obj,ensure_ascii=False)+'\n');counts['notes']+=1
            print('cached',path.parent.name,flush=True)
    with (OUT/'nursing_remarks.jsonl').open('w',encoding='utf-8') as f:
        for path in sorted(DATA.glob('*/02_rdr_bedside.csv')):
            for n,r in enumerate(read(path),2):
                visit=r['就诊号']
                if visit not in cases or r['项目名称']!='备注':continue
                created=time(r['创建日期']);t0=time(cases[visit]['t0_time'])
                if not created or not t0-6*H<=created<t0+72*H:continue
                f.write(json.dumps(dict(visit_id=visit,source_file=str(path.relative_to(ROOT)),source_row=n,
                    created=r['创建日期'],text=r['记录值']),ensure_ascii=False)+'\n');counts['nursing_remarks']+=1
    qc=dict(cases=len(cases),worklists=dict(Counter(r['worklist_state'] for r in cases.values())),records=dict(counts),
        scope='all event documents plus notes created T0-24h to T0+72h; source availability still independently adjudicated',raw_modified=False)
    (OUT/'source_cache_qc.json').write_text(json.dumps(qc,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(qc,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
