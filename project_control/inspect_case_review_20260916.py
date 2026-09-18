"""Bounded local source viewer for the ongoing AI-assisted case review."""
import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'project_control/internal_validation/20260915_source_review'
CACHE = BASE.with_name('20260916_case_review')


def rows(name):
    with (BASE / name).open(encoding='utf-8-sig', newline='') as f:
        yield from csv.DictReader(f)


def notes():
    with (CACHE / 'source_notes.jsonl').open(encoding='utf-8') as f:
        for line in f:
            yield json.loads(line)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('visits', nargs='+')
    p.add_argument('--mode', choices=['index', 'note', 'evidence', 'events', 'nursing', 'orders'], default='index')
    p.add_argument('--row', type=int, nargs='*')
    p.add_argument('--pattern', default='')
    p.add_argument('--limit', type=int, default=20000)
    a = p.parse_args()
    wanted = set(a.visits)
    for r in rows('cohort_disposition_working.csv'):
        if r['visit_id'] in wanted:
            print(json.dumps(r, ensure_ascii=False))
    output = []
    if a.mode in {'index', 'note'}:
        for r in notes():
            if r['visit_id'] not in wanted or (a.row and r['source_row'] not in a.row):
                continue
            if a.pattern and not re.search(a.pattern, r['name'] + r['text']):
                continue
            if a.mode == 'index':
                r = {k: v for k, v in r.items() if k != 'text'} | {'length': len(r['text'])}
            output.append(json.dumps(r, ensure_ascii=False))
    elif a.mode == 'nursing':
        with (CACHE / 'nursing_remarks.jsonl').open(encoding='utf-8') as f:
            for line in f:
                r = json.loads(line)
                if r['visit_id'] in wanted:
                    output.append(json.dumps(r, ensure_ascii=False))
    else:
        name = {'events': 'icu_event_evidence.csv', 'evidence': 'time_gated_evidence.csv',
                'orders': 'treatment_orders_targeted.csv'}[a.mode]
        for r in rows(name):
            if r['visit_id'] in wanted and (not a.pattern or re.search(a.pattern, json.dumps(r, ensure_ascii=False))):
                output.append(json.dumps(r, ensure_ascii=False))
    text = '\n'.join(output)
    print(text[:a.limit])
    if len(text) > a.limit:
        print(f'OUTPUT TRUNCATED: {len(text)} characters; refine selection.')


if __name__ == '__main__':
    main()
