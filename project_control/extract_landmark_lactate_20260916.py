"""Extract report-time lactate evidence and auditable pre-landmark order proxies."""
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from advance_internal_dhf_v20260915 import ROOT, DATA, read, time, H

BASE = ROOT / 'project_control/internal_validation/20260916_semantic_corrected'
LAB_DIRS = {'DHF--女_检验记录20260911200112252', 'DHF--男_检验记录20260911203919626'}
LAC = re.compile(r'乳酸(?!脱氢)|\bLAC\b|\blactate\b', re.I)


def save(name, rows, fields=None):
    with (BASE / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def order_window(r, t0):
    """ONCE is a point proxy; only documented infusions may bridge T0."""
    start, stop = time(r['start_time']), time(r['stop_time'])
    if r['valid_order_flag'] != '1' or not start or start >= t0 + 12*H:
        return 'outside_or_invalid'
    if not re.search(r'静脉|静推|静滴|IV', r['route'], re.I):
        return 'route_not_IV'
    once = r['frequency'].strip().upper() in {'ONCE', 'ST', 'STAT'}
    pump = bool(re.search(r'泵|持续', r['route'])) and not once
    if t0 <= start:
        return 'IV_infusion_started_pre12' if pump else 'IV_point_order_pre12'
    if stop and stop > t0 and pump:
        return 'IV_infusion_interval_overlaps_pre12'
    if (not stop or stop > t0) and not once:
        return 'preT0_order_continuation_uncertain'
    return 'outside_or_invalid'


def main():
    timeline = {r['visit_id']: r for r in read(BASE / 'encounter_icu_time_audit.csv')}
    limits = {v: time(r['t0_time']) for v, r in timeline.items()}
    values = defaultdict(list)
    rows, bnp = [], []
    qc = Counter()
    for path in sorted(DATA.glob('*/02_rdr_lab_test_data.csv')):
        if path.parent.name not in LAB_DIRS:
            continue
        for n, r in enumerate(read(path), 2):
            qc['raw_lab_rows_scanned'] += 1
            v = r['就诊号']
            if v not in limits:
                continue
            analyte = r['检验指标']
            is_lac = bool(LAC.search(analyte))
            is_bnp = bool(re.search(r'BNP', analyte, re.I))
            if not (is_lac or is_bnp):
                continue
            reported = time(r['检验[报告]日期'])
            t0 = limits[v]
            if not reported or not t0 - 24*H <= reported < t0 + 60*H:
                continue
            raw = r['检验结果值'].strip()
            numeric_text = r['检验结果数值'].strip()
            exact = bool(re.fullmatch(r'[+]?(?:\d+(?:\.\d*)?|\.\d+)', raw))
            try:
                number = float(raw) if exact else None
            except ValueError:
                number = None
            valid = number is not None and math.isfinite(number) and number >= 0
            window = 'preT0' if reported < t0 else 'pre12' if reported < t0+12*H else 'post12'
            obj = dict(patient_id=r['患者ID'], visit_id=v, analyte=analyte,
                       raw_result=raw, exported_numeric=numeric_text,
                       exact_numeric=number if valid else '', unit='not_exported',
                       report_time=r['检验[报告]日期'], window=window,
                       t0_time=timeline[v]['t0_time'], source_file=str(path.relative_to(ROOT)),
                       source_row=n, time_basis='report_time_not_sampling_time')
            (rows if is_lac else bnp).append(obj)
            if is_lac and valid and window == 'pre12':
                values[v].append(obj)
        print('scanned', path.parent.name, flush=True)
    fields = ['patient_id','visit_id','analyte','raw_result','exported_numeric','exact_numeric',
              'unit','report_time','window','t0_time','source_file','source_row','time_basis']
    save('lactate_report_evidence.csv', rows, fields)
    save('bnp_general_lab_evidence.csv', bnp, fields)
    orders = defaultdict(list)
    for r in read(BASE / 'treatment_orders_targeted.csv'):
        if r['drug_group'] != 'vasoactive':
            continue
        state = order_window(r, limits[r['visit_id']])
        if state not in {'outside_or_invalid', 'route_not_IV'}:
            orders[r['visit_id']].append(r | {'pre12_order_class': state})
    order_rows = [r for rs in orders.values() for r in rs]
    save('pre12_vaso_order_evidence.csv', order_rows)
    summary = []
    for v, t in timeline.items():
        vs, os = values[v], orders[v]
        maximum = max((r['exact_numeric'] for r in vs), default=None)
        inf = [r for r in os if r['pre12_order_class'].startswith('IV_infusion')]
        point = [r for r in os if r['pre12_order_class'] == 'IV_point_order_pre12']
        if maximum is None:
            state = 'unknown_no_exact_pre12_lactate'
        elif maximum >= 2 and inf:
            state = 'high_lactate_numeric_and_IV_infusion_proxy_review_units_indication'
        elif maximum >= 2 and point:
            state = 'high_lactate_numeric_and_IV_point_order_review_indication'
        elif maximum >= 2:
            state = 'high_lactate_numeric_no_definite_IV_order_proxy'
        else:
            state = 'observed_lactate_numeric_below_2_units_unverified'
        summary.append(dict(patient_id=t['patient_id'], visit_id=v, t0_time=t['t0_time'],
                            pre12_lactate_reports=len(vs), max_pre12_lactate_numeric=maximum if maximum is not None else '',
                            lactate_units='not_exported_not_assumed', IV_infusion_order_proxies=len(inf),
                            IV_point_order_proxies=len(point), continuation_uncertain_orders=len(os)-len(inf)-len(point),
                            risk_proxy_work_state=state,
                            lactate_refs=';'.join(r['source_file']+'#row='+str(r['source_row']) for r in vs),
                            order_refs=';'.join(r['source_file']+'#row='+str(r['source_row']) for r in os),
                            final_riskset_eligibility='not_frozen'))
    save('pre12_shock_proxy_working.csv', summary)
    result = dict(qc, patients=len(summary), lactate_evidence_rows=len(rows),
                  bnp_evidence_rows=len(bnp), patients_with_pre12_exact_lactate=sum(int(r['pre12_lactate_reports']) > 0 for r in summary),
                  states=dict(Counter(r['risk_proxy_work_state'] for r in summary)),
                  unit_verified=False, final_riskset_frozen=False, raw_modified=False)
    (BASE/'lactate_qc.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
