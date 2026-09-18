"""Cache existing source records for the 22 time gaps and 3 label discrepancies."""
import csv
import json
from collections import Counter
from pathlib import Path

from advance_internal_dhf_v20260915 import ROOT, DATA, OUT, H, read, time


def main():
    timeline = {r['visit_id']: r for r in read(OUT/'encounter_icu_time_audit.csv')}
    discrepancies = {'11010880_4', '2533820_24', '7039751_3'}
    focus = {v for v, r in timeline.items() if r['t0_source'] == 'structured_proxy'} | discrepancies
    counts = Counter()
    target = OUT/'focused_source_records.jsonl'
    with target.open('w', encoding='utf-8') as handle:
        for pattern, source in [('*/02_rdr_medrecord_list.csv', 'document'), ('*/02_rdr_bedside.csv', 'nursing')]:
            for path in sorted(DATA.glob(pattern)):
                for rowno, r in enumerate(read(path), 2):
                    visit = r['就诊号']
                    if visit not in focus:
                        continue
                    if source == 'nursing' and r['项目名称'] != '备注':
                        continue
                    created = time(r['创建日期'])
                    t0 = time(timeline[visit]['t0_time'])
                    name = r['文书名称'] if source == 'document' else r['项目名称']
                    text = r['文本病历'] if source == 'document' else r['记录值']
                    # Keep the full encounter's narratives for event reconstruction.
                    # Phenotype review must independently enforce availability.
                    obj = dict(visit_id=visit, source=source, source_file=str(path.relative_to(ROOT)),
                               source_row=rowno, name=name, created=r['创建日期'], text=text,
                               in_phenotype_window=bool(created and t0-24*H <= created < t0+12*H))
                    handle.write(json.dumps(obj, ensure_ascii=False)+'\n')
                    counts[source] += 1
    print(json.dumps(dict(cases=len(focus), records=counts, output=str(target)), ensure_ascii=False))


if __name__ == '__main__':
    main()
