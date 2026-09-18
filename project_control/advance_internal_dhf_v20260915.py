#!/usr/bin/env python3
"""Local, streaming episode reconstruction and time-gated DHF evidence audit.

Outputs are rule-assisted pre-review, never independent clinical adjudication.
Raw exports and previous versions are immutable inputs.
"""
from __future__ import annotations

import csv
import argparse
import datetime as dt
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'DHF_SRR'
BASE = ROOT / 'project_control/internal_validation/20260912'
OUT = ROOT / 'project_control/internal_validation/20260915_time_gated'
REVIEW = OUT
H = dt.timedelta(hours=1)
STAMP = r'(?:19|20)\d{2}[-/.年]\s*\d{1,2}[-/.月]\s*\d{1,2}(?:日|号)?\s*[ T]?\s*\d{1,2}[:：]\d{2}(?::\d{2})?'
ICU = re.compile(r'ICU|监护室|(?<!危)重症医学', re.I)
LABELS = {
    'icu_in': re.compile(r'(?:入\s*ICU\s*(?:时间|日期))\s*[:：]?\s*('+STAMP+')', re.I),
    'icu_out': re.compile(r'出\s*ICU\s*(?:日期|时间)\s*[:：]?\s*('+STAMP+')', re.I),
    'death': re.compile(r'死亡(?:日期|时间)\s*[:：]?\s*('+STAMP+')'),
    'hospital_out': re.compile(r'出院(?:日期|时间)\s*[:：]?\s*('+STAMP+')'),
}
TRANSFER = re.compile(r'(?:患者\s*于|转科日期[:：]?)\s*('+STAMP+r')\s*由(.{1,100}?)(?:转入|转至|转往|转)(.{1,80}?)(?=接科情况|转入情况|主诉|[。；\n]|$)', re.I)
ADMIT = re.compile(r'入院时间\s*[:：]?\s*('+STAMP+')')
NURSE_IN = re.compile(r'(?:患者)?由.{0,35}?(?:进入|转入|送入|入)(?:我科)?(?:监护室|ICU)', re.I)
NURSE_OUT = re.compile(r'(?:转入|转至|转往)(.{1,45}?)(?=[，,。；]|$)')
NURSE_PLAN = re.compile(r'拟|计划|待转|准备|建议|考虑转')
RETRO = re.compile(r'出ICU|转病房|转出记录|死亡|出院|谈话|告知|同意|须知|评分|评估表|知情|病[危重]通知|作废|麻醉前访视')
DOMAINS = {
    'hf': re.compile(r'心力衰竭|心衰|心功能不全|心源性休克|心肌病|心肌炎|心功能[ⅠⅡⅢⅣIV1-4-]{1,5}级', re.I),
    'congestion': re.compile(r'肺水肿|肺淤血|肺充血|端坐呼吸|(?:无法|不能|难以)平卧|夜间阵发性呼吸困难|湿[啰罗]音|颈静脉怒张|(?:双)?下肢.{0,6}水肿|全身.{0,10}(?:凹陷性)?(?:浮肿|水肿)|容量超负荷'),
    'symptom': re.compile(r'呼吸困难|胸闷气急|气促|低氧血症|低灌注'),
    'management': re.compile(r'(?:予|给予|加用|加强|强化|增加|调整|静推|静滴|泵入).{0,18}(?:利尿|呋塞米|托拉塞米|硝酸甘油|无创通气|强心)|(?:利尿|呋塞米|托拉塞米).{0,12}(?:治疗|静推|静滴|泵入)'),
    'alternative': re.compile(r'肺炎|ARDS|脓毒症|感染性休克|肺栓塞|失血性休克|肺挫伤|误吸|创伤|术后|肾功能不全|尿毒症', re.I),
}
NEG = re.compile(r'(?:否认|未见|未闻及|未及|未发现|不支持|无明显|无|没有|排除)(?:(?!但|伴|存在).){0,12}$')
RISK = re.compile(r'可能出现|可能发生|防止|预防|风险|并发症|警惕|告知|必要时|如出现|避免|伴或不伴|典型表现|通常表现|常见表现')
UNCERTAIN = re.compile(r'考虑|可能|疑似|待排|不能排除|不除外|[?？]')
HISTORY = re.compile(r'既往|家族史|父亲|母亲|多年前')
LOOP = re.compile(r'呋塞米|托拉塞米|布美他尼|依他尼酸')
VASO = re.compile(r'去甲肾上腺素|肾上腺素|多巴胺|多巴酚丁胺|米力农|左西孟旦|血管加压素|垂体后叶|去氧肾上腺素')


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        yield from csv.DictReader(handle)


def time(value):
    s = (value or '').strip().replace('年','-').replace('月','-').replace('日',' ').replace('号',' ').replace('：',':').replace('/','-').replace('.','-')
    if not re.search(r'\d:\d{2}', s):
        return None
    s = re.sub(r'\s+', ' ', s.replace('T',' ')).strip()
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                return dt.datetime.strptime(s, fmt)
            except ValueError:
                pass
    return None


def stamp(t):
    return t.isoformat(sep=' ') if t else ''


def clean(text):
    return re.sub(r'\s+', ' ', text or '')


def entry_evidence(all_ins, outs):
    """Retain earlier admission fields when an exit corroborates a prior ICU stay."""
    explicit = [e for e in all_ins if e['source'] != 'icu_discharge_note_admission_field']
    if not explicit:
        return sorted(all_ins, key=lambda e: e['event_time'])
    first = min(time(e['event_time']) for e in explicit)
    prior = [e for e in all_ins if e['source'] == 'icu_discharge_note_admission_field'
             and any(time(e['event_time']) < time(o['event_time']) < first for o in outs)]
    return sorted(explicit + prior, key=lambda e: e['event_time'])


def write(name, rows, fields=None):
    rows = list(rows)
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as handle:
        w = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def key(r):
    return r.get('患者ID', ''), r.get('就诊号', '')


def blank_icu_template(name, text):
    if name != '入ICU记录':
        return False
    labels = ['入ICU时间', '入ICU原因', '入ICU前诊治经过', '既往史', '入科查体', '辅助检查', '入ICU诊断', '转入ICU后诊疗计划']
    pattern = r'\s*'.join(re.escape(label) + r'\s*[:：]\s*' for label in labels)
    return bool(re.search(pattern, text))


def assertions(text, domain):
    for sentence in re.split(r'[。；;\n]', text):
        for m in DOMAINS[domain].finditer(sentence):
            # Negation is local to the current clause, not the entire note.
            prefix = re.split(r'[，,：:]', sentence[:m.start()])[-1][-35:]
            context = sentence[max(0,m.start()-45):m.end()+40]
            if RISK.search(context):
                status = 'hypothetical'
            elif re.search(r'不能排除|不除外|未排除', prefix):
                status = 'uncertain'
            elif NEG.search(prefix) or re.search(r'无(?!法平卧)|未见|未及|不明显',m.group()):
                status = 'negated'
            elif UNCERTAIN.search(prefix + sentence[m.end():m.end()+6]):
                status = 'uncertain'
            elif HISTORY.search(prefix):
                status = 'historical'
            else:
                status = 'affirmed'
            yield status, m.group(), clean(context)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    masters = [r for r in read(BASE/'icu_stay_master_20260912.csv') if r['index_adult_icu_flag']=='1' and r['patient_id']!='9204020']
    master = {(r['patient_id'],r['visit_id']):r for r in masters}
    assert len(master)==len(masters)==8385 and len({r['patient_id'] for r in masters})==8385
    qc = Counter()
    events = defaultdict(list)
    event_rows = []

    def add(k, typ, t, source, name, created, path, rowno, excerpt, priority):
        if not t:
            return
        m = master[k]
        admission, discharge = time(m['encounter_date']), time(m['structured_discharge_time'])
        reason = ''
        if admission and t < admission-24*H:
            reason = 'before_encounter_boundary'
        elif discharge and t > discharge+24*H:
            reason = 'after_hospital_discharge_boundary'
        elif created and t > created+48*H:
            reason = 'event_over_48h_after_document_creation'
        e = dict(patient_id=k[0],visit_id=k[1],event_type=typ,event_time=stamp(t),source=source,
                 document_name=name,record_created_time=stamp(created),source_file=str(path.relative_to(ROOT)),
                 source_row=rowno,excerpt=excerpt,priority=priority,rejection_reason=reason)
        event_rows.append(e)
        qc['event_'+typ]+=1
        if not reason:
            events[k].append(e)
        else:
            qc['rejected_'+reason]+=1

    for path in sorted(DATA.glob('*/02_rdr_bedside.csv')):
        for i,r in enumerate(read(path),2):
            k=key(r)
            if k not in master or r['项目名称']!='备注':
                continue
            text=r['记录值']; created=time(r['创建日期'])
            match=NURSE_IN.search(text)
            if match and not NURSE_PLAN.search(text[max(0,match.start()-10):match.start()]):
                add(k,'icu_in',created,'nursing_entry_record_time','护理备注',created,path,i,match.group(),0)
            if not NURSE_PLAN.search(text):
                for m in NURSE_OUT.finditer(text):
                    target=m.group(1)
                    if not ICU.search(target) and re.search(r'病房|内科|外科|病区',target):
                        add(k,'icu_out',created,'nursing_transfer_record_time','护理备注',created,path,i,m.group(),0)
        print('nursing completed',path.parent.name,flush=True)

    for path in sorted(DATA.glob('*/02_rdr_medrecord_list.csv')):
        for i,r in enumerate(read(path),2):
            k=key(r)
            if k not in master:
                continue
            name=r['文书名称']; text=r['文本病历']; created=time(r['创建日期'])
            if not re.search(r'ICU|转入记录|转出记录|死亡记录|出院记录',name,re.I):
                continue
            for typ,pat in LABELS.items():
                if typ=='death' and '死亡记录' not in name: continue
                if typ=='hospital_out' and '出院记录' not in name: continue
                for m in pat.finditer(text):
                    add(k,typ,time(m.group(1)),'explicit_document_event',name,created,path,i,m.group(),1 if typ=='icu_in' else 3)
            # User-confirmed semantics: the admission field in 出ICU记录 is
            # an ICU entry candidate; explicit ICU/nursing evidence ranks first.
            if name=='出ICU记录':
                m=ADMIT.search(text)
                if m: add(k,'icu_in',time(m.group(1)),'icu_discharge_note_admission_field',name,created,path,i,m.group(),2)
            for m in TRANSFER.finditer(text):
                src,dst=m.group(2),m.group(3)
                a,b=bool(ICU.search(src)),bool(ICU.search(dst))
                typ='icu_out' if a and not b else 'icu_in' if b and not a else 'icu_to_icu' if a and b else 'ward_transfer'
                add(k,typ,time(m.group(1)),'directional_document_transfer',name,created,path,i,m.group(),1)
        print('event documents completed',path.parent.name,flush=True)

    manual={}
    selected={'G3-005','G3-015','G3-029','G3-043','G3-050'}
    for r in read(BASE/'internal_gate3_manual_review_50_20260913_reviewed.csv'):
        if r['review_id'] in selected:
            manual[(r['patient_id'],r['visit_id'])]=r

    focused_time = {r['visit_id']: r for r in read(REVIEW/'focused_time_review_22.csv')} if (REVIEW/'focused_time_review_22.csv').exists() else {}
    focused_semantic = {r['visit_id']: r for r in read(REVIEW/'focused_semantic_review_7.csv')} if (REVIEW/'focused_semantic_review_7.csv').exists() else {}
    quarantine = {(r['source_file'], int(r['source_row'])) for r in read(REVIEW/'document_quarantine.csv')} if (REVIEW/'document_quarantine.csv').exists() else set()
    for k in master:
        review = focused_time.get(k[1], {})
        if review.get('apply_time') == '1':
            add(k, 'icu_in', time(review['reviewed_t0']), 'AI_review_' + review['time_review_status'],
                'source_crosschecked_event', None, ROOT/review['source_file'], int(review['source_row']), review['evidence_reason'], -1)

    encounters=[]; intervals=[]; by_key={}
    for k,m in master.items():
        ee=events[k]; all_ins=[e for e in ee if e['event_type']=='icu_in']
        explicit_ins=[e for e in all_ins if e['source']!='icu_discharge_note_admission_field']
        outs=sorted([e for e in ee if e['event_type']=='icu_out'],key=lambda e:e['event_time'])
        ins=entry_evidence(all_ins, outs)
        # Admission-field discrepancies within six hours describe the same
        # entry cluster unless an explicit exit separates the timestamps.
        clusters=[]
        for e in ins:
            t=time(e['event_time'])
            if clusters and t-time(clusters[-1][0]['event_time'])<=6*H and not any(time(clusters[-1][-1]['event_time'])<time(x['event_time'])<t for x in outs):
                clusters[-1].append(e)
            else:
                clusters.append([e])
        chosen=[]
        for c in clusters:
            chosen.append(min(c,key=lambda e:(e['priority'],e['event_time'])))
        source='structured_proxy'; t0=time(m['t0_candidate']); excerpt=''; flags=[]
        if chosen:
            t0=time(chosen[0]['event_time']);source=chosen[0]['source'];excerpt=chosen[0]['excerpt']
        if explicit_ins and source=='icu_discharge_note_admission_field':
            flags.append('earlier_episode_recovered_by_admission_and_exit')
        if k in manual:
            t0=time(manual[k]['t0_time_final']);source='user_confirmed_document_time';excerpt=manual[k].get('t0_discrepancy_note','')
        if len(chosen)>1:
            for a,b in zip(chosen,chosen[1:]):
                if not any(time(a['event_time'])<time(o['event_time'])<time(b['event_time']) for o in outs):
                    flags.append('repeat_entry_without_intervening_exit')
        old=time(m['t0_candidate'])
        delta=(t0-old).total_seconds()/3600 if t0 and old else None
        if delta is not None and abs(delta)>6: flags.append('t0_changed_over_6h')
        if source=='structured_proxy':flags.append('no_explicit_icu_entry')
        focused = focused_time.get(k[1], {})
        if focused.get('time_review_status') == 'contextual_admission':
            flags.append('contextual_time_not_direct_arrival')
        if focused:
            flags.append('source_time_review_' + focused['time_review_status'])
        if explicit_ins and any(abs(time(x['event_time'])-t0)>6*H for x in all_ins if x['source']=='icu_discharge_note_admission_field'):
            flags.append('discharge_note_admission_field_disagrees')
        if not t0:flags.append('missing_t0')
        next_in=min((time(x['event_time']) for x in chosen if t0 and time(x['event_time'])>t0+6*H),default=None)
        out_candidates=[x for x in outs if t0 and time(x['event_time'])>t0 and (not next_in or time(x['event_time'])<next_in)]
        actual=[x for x in out_candidates if x['priority']<=1]
        out=min(actual or out_candidates,key=lambda x:x['event_time'],default=None)
        outtime=time(out['event_time']) if out else None
        if outtime and any(abs(time(x['event_time'])-outtime)>6*H for x in out_candidates):flags.append('exit_times_differ_over_6h')
        death=min((time(x['event_time']) for x in ee if x['event_type']=='death' and t0 and time(x['event_time'])>=t0),default=None)
        hospital_out=min((time(x['event_time']) for x in ee if x['event_type']=='hospital_out' and t0 and time(x['event_time'])>=t0),default=None)
        t12=t0+12*H if t0 else None
        eligible='unknown'
        if t12:
            if outtime and outtime<=t12:eligible='left_index_icu_by_T12'
            elif death and death<=t12:eligible='died_by_T12'
            elif outtime or (death and not next_in):eligible='present_at_T12_by_document_timeline'
        er=dict(patient_id=k[0],sex=m['sex'],visit_id=k[1],episode_id=k[1]+'_index',
                old_t0=m['t0_candidate'],t0_time=stamp(t0),t0_source=source,t0_excerpt=excerpt,
                focused_time_review_status=focused.get('time_review_status', 'not_in_focused_batch'),
                focused_time_review_reason=focused.get('evidence_reason', ''),
                t0_change_hours='' if delta is None else round(delta,4),t12_time=stamp(t12),t60_time=stamp(t0+60*H) if t0 else '',
                entry_clusters=len(clusters),readmission_with_exit_flag=int(any(time(a['event_time'])<time(o['event_time'])<time(b['event_time']) for a,b in zip(chosen,chosen[1:]) for o in outs)),
                index_icu_outtime=stamp(outtime),icu_out_source=out['source'] if out else '',
                hospital_death_time=stamp(death),hospital_discharge_time=stamp(hospital_out),
                landmark_presence_status=eligible,time_review_flags=';'.join(sorted(set(flags))))
        encounters.append(er);by_key[k]=er
        for num,e in enumerate(chosen,1):
            entry=time(e['event_time']); following=time(chosen[num]['event_time']) if num<len(chosen) else None
            exit_=min((time(x['event_time']) for x in outs if time(x['event_time'])>entry and (not following or time(x['event_time'])<following)),default=None)
            intervals.append(dict(patient_id=k[0],visit_id=k[1],episode_number_candidate=num,entry_time=stamp(entry),entry_source=e['source'],exit_time_candidate=stamp(exit_),status='reconstructed_candidate_requires_conflict_audit'))
    write('icu_event_evidence.csv',event_rows)
    write('encounter_icu_time_audit.csv',encounters)
    write('icu_episode_candidates.csv',intervals)
    print('time audit completed',len(encounters),'episodes',len(intervals),flush=True)

    evidence=[]; seen=set(); domain_counts=defaultdict(Counter)
    def emit(k,domain,status,excerpt,path,rowno,available,source,extra=''):
        ident=(k,domain,status,excerpt,stamp(available),extra)
        if ident in seen:return
        seen.add(ident);domain_counts[k][domain+'_'+status]+=1
        evidence.append(dict(patient_id=k[0],visit_id=k[1],domain=domain,assertion=status,available_time_proxy=stamp(available),
                             source=source,source_file=str(path.relative_to(ROOT)),source_row=rowno,excerpt=excerpt,detail=extra))
    def window(k,t):
        t0=time(by_key[k]['t0_time'])
        return bool(t and t0 and t0-24*H<=t<t0+12*H)

    for path in sorted(DATA.glob('*/02_rdr_medrecord_list.csv')):
        for i,r in enumerate(read(path),2):
            k=key(r)
            if k not in master:continue
            created=time(r['创建日期'])
            if not window(k,created):continue
            name=r['文书名称']
            if (str(path.relative_to(ROOT)), i) in quarantine:
                qc['quarantined_phenotype_documents'] += 1
                continue
            if blank_icu_template(name, r['文本病历']):
                qc['excluded_blank_icu_templates'] += 1
                continue
            if RETRO.search(name):qc['excluded_retrospective_or_template_documents']+=1;continue
            domain_counts[k]['in_window_documents']+=1
            clinical_text=re.sub(r'鉴别诊断\s*[:：].*?(?=诊疗计划|诊疗措施|诊疗方案|$)','',r['文本病历'],flags=re.S)
            for domain in DOMAINS:
                for status,term,excerpt in assertions(clinical_text,domain):
                    emit(k,domain,status,excerpt,path,i,created,'document_creation_proxy',name)
        print('time-gated notes completed',path.parent.name,flush=True)

    # Full report text, including independent longitudinal exports. Exact
    # duplicate reports are collapsed; previous-visit rows are separate history.
    patient_keys={k[0]:k for k in master}
    for path in sorted(DATA.glob('*/02_rdr_exam_master_report.csv')):
        for i,r in enumerate(read(path),2):
            k=patient_keys.get(r.get('患者ID'))
            if not k:continue
            reported=time(r['检查[报告]日期'])
            if not window(k,reported):continue
            if key(r)!=k:
                if reported>=time(by_key[k]['t0_time']):
                    qc['cross_visit_exam_after_T0_excluded']+=1
                    continue
                qc['cross_visit_exam_pre_T0_retained']+=1
            name=r['项目名称'];typ=r['检查类型'];text=r['检查结论']+' '+r['检查所见']
            if key(r)!=k:name+='; prior_visit='+r['就诊号']
            echo=bool(re.search(r'心超|心脏超声|超声心动|心脏彩|左心功能|经食[管道].*超声',name+' '+typ))
            chest=bool(re.search(r'胸部|胸片|肺部|肺动脉CTA|胸腔',name,re.I))
            if echo:
                emit(k,'echo_result','available' if text.strip() else 'missing',clean(text),path,i,reported,'report_time_proxy',name)
                # Bare right-heart/valve mentions and minor regurgitation are
                # not abnormal findings. EF >=50 does not rule out HFpEF.
                abnormal=re.search(r'(?:LVEF|EF|射血分数)\s*[:：=]?\s*(?:[1-4]\d)(?:\.\d+)?\s*%|(?:左室|右室).{0,10}(?:收缩功能|壁运动|壁活动).{0,6}(?:减低|降低|减弱)|(?:中度|重度).{0,10}(?:反流|返流|狭窄)|(?:反流|返流|狭窄).{0,8}(?:中度|重度)|(?:左心|右心|全心|左房|右房|左室|右室).{0,6}(?:增大|扩大)|左室舒张功能.{0,6}(?:减退|降低)',text,re.I)
                if abnormal:emit(k,'echo_abnormal','affirmed',abnormal.group(),path,i,reported,'report_time_proxy',name)
            if chest:
                emit(k,'chest_result','available',clean(text),path,i,reported,'report_time_proxy',name)
                for domain in ('congestion','alternative'):
                    for status,term,excerpt in assertions(text,domain):emit(k,domain,status,excerpt,path,i,reported,'report_time_proxy',name)
        print('time-gated exams completed',path.parent.name,flush=True)

    orders=[]; order_seen=set()
    for path in sorted(DATA.glob('*/02_rdr_orders.csv')):
        for i,r in enumerate(read(path),2):
            k=key(r)
            if k not in master:continue
            name=r['药品名称'];kind='iv_loop' if LOOP.search(name) else 'vasoactive' if VASO.search(name) else ''
            if not kind:continue
            start,stop=time(r['开嘱时间']),time(r['停嘱时间']);t0=time(by_key[k]['t0_time'])
            if not t0 or not start or start>=t0+60*H or (stop and stop<t0-24*H):continue
            status=r['医嘱状态'];route=r['给药途径'];valid=not bool(re.search(r'作废|废除|撤销|取消|未执行',status))
            if kind=='iv_loop' and not re.search(r'静脉|静推|静滴|泵|IV',route,re.I):valid=False
            if stop and stop<start:valid=False
            identity=(k,r['医嘱序号'],name,stamp(start),stamp(stop),route,r['剂量'])
            if identity in order_seen:continue
            order_seen.add(identity)
            pre=valid and (window(k,start) or bool(stop and start<t0-24*H<stop))
            if pre:emit(k,kind,'order_proxy',name,path,i,start,'order_interval_proxy',route+';'+status)
            orders.append(dict(patient_id=k[0],visit_id=k[1],order_id=r['医嘱序号'],drug_group=kind,medication=name,
                               route=route,dose=r['剂量'],dose_unit=r['剂量单位'],frequency=r['频次'],status=status,
                               start_time=stamp(start),stop_time=stamp(stop),valid_order_flag=int(valid),pre_T12_proxy_flag=int(pre),
                               stop_missing_flag=int(not stop),source_file=str(path.relative_to(ROOT)),source_row=i,
                               execution_basis='order_proxy_not_pump_rate_or_individual_administration'))
        print('time-gated orders completed',path.parent.name,flush=True)

    # These two exports were profiled as the dedicated longitudinal BNP/
    # troponin tables. General all-analyte exports remain available for later
    # physiological-feature reconstruction and are not redundantly rescanned.
    targeted_lab_folders={'DHF--女_检验记录20260911201403540','DHF--男_检验记录20260911204412869'}
    for path in sorted(DATA.glob('*/02_rdr_lab_test_data.csv')):
        if path.parent.name not in targeted_lab_folders:
            qc['general_lab_files_deferred']+=1
            continue
        for i,r in enumerate(read(path),2):
            k=patient_keys.get(r.get('患者ID'))
            if not k or not re.search(r'BNP',r['检验指标'],re.I):continue
            reported=time(r['检验[报告]日期'])
            if not window(k,reported):continue
            if key(r)!=k:
                if reported>=time(by_key[k]['t0_time']):
                    qc['cross_visit_bnp_after_T0_excluded']+=1
                    continue
                qc['cross_visit_bnp_pre_T0_retained']+=1
            value=r['检验结果值'] or r['检验结果数值']
            emit(k,'natriuretic_peptide','measured',r['检验指标']+'='+value,path,i,reported,'result_report_time_proxy','unit_not_exported;no_numeric_rule_in_assigned;source_visit='+r['就诊号'])
        print('targeted BNP completed',path.parent.name,flush=True)

    semantic={(r['patient_id'],r['visit_id']):r for r in read(BASE/'internal_gate3_semantic_evidence_20260914_adjudicated.csv')}
    tiers=[]
    for k,m in master.items():
        c=domain_counts[k];er=by_key[k];a=c['hf_affirmed']>0;b=c['congestion_affirmed']>0
        manage=c['management_affirmed']>0 or c['iv_loop_order_proxy']>0
        echo=c['echo_abnormal_affirmed']>0;alt=c['alternative_affirmed']>0
        # These tiers deliberately remain pre-review, with clinical calibration
        # and final analytical inclusion represented as separate fields.
        if not er['t0_time'] or not c['in_window_documents']:tier='unknown';reason='no_time_bounded_clinical_text'
        elif a and b and echo and manage and not alt and not er['time_review_flags']:
            tier='confirmed_dhf';reason='multidomain_rule_support_requires_semantic_confirmation'
        elif a and (b or c['symptom_affirmed']) and (echo or manage):tier='probable_dhf';reason='support_present_alternative_or_time_or_domain_gap'
        elif not a and c['hf_uncertain']:tier='unknown';reason='uncertain_hf_anchor'
        else:tier='not_supported';reason='insufficient_current_multidomain_evidence_not_proof_of_absence'
        prior=semantic.get(k,{})
        focused=focused_semantic.get(k[1],{})
        if k in manual and manual[k]['review_id']=='G3-043':tier='not_supported';reason='user_confirmed_no_DHF'
        tiers.append(dict(patient_id=k[0],sex=m['sex'],visit_id=k[1],t0_time=er['t0_time'],
                          phenotype_tier_pre_review=tier,decision_reason=reason,label_basis='local_rules_AI_pre_review_not_clinical_gold_standard',
                          final_analysis_inclusion='not_frozen',hf_anchor_affirmed=int(a),congestion_affirmed=int(b),
                          focused_phenotype_semantic_status=focused.get('phenotype_semantic_status','not_in_focused_batch'),
                          focused_riskset_review_status=focused.get('riskset_review_status','not_in_focused_batch'),
                          focused_source_refs=focused.get('source_refs',''),
                          symptom_affirmed=int(c['symptom_affirmed']>0),management_proxy=int(manage),echo_result_available=int(c['echo_result_available']>0),
                          echo_abnormal_rule_support=int(echo),alternative_mentioned=int(alt),in_window_documents=c['in_window_documents'],
                          time_review_flags=er['time_review_flags'],landmark_presence_status=er['landmark_presence_status'],
                          prior_semantic_review=prior.get('codex_adjudication_status','not_sampled'),
                          prior_semantic_reason=prior.get('codex_adjudication_reason',''),
                          bnp_status='measured_unit_not_exported' if c['natriuretic_peptide_measured'] else 'not_observed_in_targeted_export_window'))
    write('time_gated_evidence.csv',evidence)
    write('treatment_orders_targeted.csv',orders)
    write('dhf_phenotype_pre_review.csv',tiers)
    summary=dict(version='20260915',adult_selected_echo_candidate_denominator=len(master),
                 time_source_counts=dict(Counter(r['t0_source'] for r in encounters)),
                 t0_changed=sum(abs(float(r['t0_change_hours'] or 0))>0 for r in encounters),
                 focused_time_cases=len(focused_time),focused_semantic_cases=len(focused_semantic),
                 time_flags=dict(Counter(f for r in encounters for f in r['time_review_flags'].split(';') if f)),
                 repeat_icu_with_intervening_exit=sum(r['readmission_with_exit_flag'] for r in encounters),
                 landmark_presence_counts=dict(Counter(r['landmark_presence_status'] for r in encounters)),
                 phenotype_pre_review_counts=dict(Counter(r['phenotype_tier_pre_review'] for r in tiers)),
                 echo_report_available=sum(r['echo_result_available'] for r in tiers),echo_abnormal_rule_support=sum(r['echo_abnormal_rule_support'] for r in tiers),
                 counts=dict(qc),output_rows={'events':len(event_rows),'episode_candidates':len(intervals),'time_gated_evidence':len(evidence),'targeted_orders':len(orders)},
                 raw_data_modified=False,final_cohort_frozen=False,clinical_gold_standard=False,
                 limitations=['Index encounter inherited from prior candidate master; full patient episode selection still needs chronology audit.',
                              'Creation timestamps are availability proxies, not immutable signing timestamps.',
                              'BNP values retained without numerical rule-in because units are not exported; nursing physiology pending.',
                              'No NEE or clinical outcome inferred from medication amount.',
                              'No final event/competing/censor counts until full endpoint components and observation are reconstructed.'])
    summary['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUT/'qc.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--review-dir', type=Path, default=REVIEW)
    args = parser.parse_args()
    OUT, REVIEW = args.out.resolve(), args.review_dir.resolve()
    main()
