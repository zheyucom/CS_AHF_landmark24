"""Persist source-grounded AI case review separately from automated labels."""
import csv
import json
from collections import Counter, defaultdict

from advance_internal_dhf_v20260915 import OUT, DATA, read


TIME_DECISIONS = {
    '10271725_18': ('', 'unresolved', 1611, '出ICU入院栏为空；首次病程19:12与大病史20:06均未明确等同ICU到达时间。'),
    '10726076_3': ('2025-01-06 01:25:00', 'contextual_admission', 246935, '首次病程临床科室为重症医学科且正文明确急诊异物取出后转ICU；入院字段可作上下文支持的分钟级时间，非直接到达记录。'),
    '1692135_10': ('', 'unresolved', 64021, '出ICU及转科文书入院年份2021与本次2022住院冲突；不能仅凭推测更改年份和时刻。'),
    '1723933_37': ('2021-01-21 21:05:00', 'contextual_admission', 65442, '本次首次病程重症医学科入院21:05与大病史一致；旧入ICU文书叙述上次脑出血不能覆盖本次气道出血就诊。'),
    '1813317_337': ('', 'unresolved', 31141, '明确收住EICU但仅有入院19:10和入病房19:00，出ICU入院栏为空；保留时点不确定。'),
    '1926193_28': ('2021-02-09 23:30:00', 'contextual_admission', 69882, '重症医学科首次病程及大病史入院同为23:30；明确急诊CPR后收住ICU；创建23:13早于该时刻，保留文书时间冲突。'),
    '2001052_4': ('', 'unresolved', 72340, '2月4日转监护室是外院既往过程；本院首次病程入院18:30属急诊医学科，次日00:31普通病程记入监护室后情况，不能冒充到达时刻。'),
    '2314812_30': ('2023-05-04 07:30:00', 'contextual_admission', 78656, '首次病程入院07:30、ICU003床号、大病史07:30及PCI术后转ICU叙述一致；上下文支持，非直接入ICU时间栏。'),
    '2339213_33': ('', 'unresolved', 79617, '出ICU入院时间为0001-01-01占位值；入ICU时间栏为空；护理仅出入量，不能用首条记录代替到达。'),
    '2355023_9': ('', 'unresolved', 260311, '2月8日入ICU文书关键栏为空，与2月4日首次住院存在间隔，不能把住院时间直接当ICU时间。'),
    '2591142_5': ('2023-03-06 16:30:00', 'explicit_retrospective_transfer', 42448, '重症SOAP明确2023-03-06 16:30转至我科继续监护，多份SOAP复述一致；用正文事件时间。'),
    '2822361_29': ('2025-07-11 11:26:00', 'contextual_admission', 46052, '重症医学科首次病程入院11:26且正文门诊后收入ICU；大病史入病房12:00不同，保留上下文级精度。'),
    '2838574_7': ('2023-01-16 18:05:00', 'corroborated_discharge_admission', 494711, '出ICU入院18:05与首次病程及ICU转病房入院18:05一致；出ICU文书创建2022年为冲突元数据，正文不能据此整体丢弃。'),
    '3641644_32': ('2022-07-18 18:45:00', 'contextual_admission', 56119, '重症医学科首次病程、大病史及转出记录入院同为18:45，急诊处理后转ICU；转出10:16与转入病房17:17另保留冲突。'),
    '3644045_110': ('', 'unresolved', 113951, '首次病程入院14:50为肝病感染内科，入病房15:00，入ICU记录关键字段空白；未查到直接时刻。'),
    '4318302_5': ('', 'unresolved', 68178, '首次病程消化内科入院15:55且拟入ICU行ERCP；空白入ICU文书不能证实实际到达时刻。'),
    '5811402_5': ('', 'date_only', 93014, '病房转ICU文书明确2022-03-11入ICU，但没有钟点；不自动补00:00或以神经内科入院11:25替代。'),
    '5999058_9': ('', 'unresolved', 189681, '重症首次病程入院16:00和大病史18:45冲突；入ICU记录为空，当前不足以挑定分钟时刻。'),
    '6686520_3': ('', 'unresolved', 197801, '入ICU记录核心字段空白；14:55为肝病感染内科入院字段，不能单独确认ICU到达。'),
    '6835516_3': ('', 'unresolved', 119045, '首次病程消化内科入院07:00与大病史07:05；可定位当天重症过程，尚缺直接ICU到达时刻。'),
    '9188374_2': ('', 'unresolved', 333175, '15:17首次入内分泌科，随后低氧转ICU；21:39是入ICU文书创建时间，时间栏空白，不能当实际到达。'),
    '9196107_3': ('', 'unresolved', 335324, '入ICU文书关键字段空白，呼吸内科入院13:12与入病房15:49不一致；维持时间不确定。'),
}

SEMANTIC_DECISIONS = {
    '11010880_4': ('dhf_supported', 'baseline_shock_requires_rule_mapping', [36684],
        '本次进展性胸闷、睡眠无法平卧，明确心衰/心源性休克；当日心超EF40%，静脉呋塞米医嘱。漏识别无法平卧导致旧规则漏纳。',
        '入院前CPR、临时起搏和多巴胺支持；不能由总剂量得出NEE阈值。表型保留，风险集资格单独审计。'),
    '2533820_24': ('mixed_cardiac_decompensation_supported', 'baseline_mechanical_support_requires_eligibility_mapping', [494185, 494248],
        '创伤失血为起因，但T12前SOAP明确心源性休克、急性心肌梗死和心超收缩功能下降；不能继续标无HF锚点。',
        '10:43已VA-ECMO及双升压药，发生于T12=13:10前；既有061C主规则是前12h血管活性药且乳酸>=2，并非机械支持单独排除。入院乳酸1.5，须核对其余同窗乳酸和已发生结局条件，暂不自动排除。'),
    '7039751_3': ('dhf_not_supported_after_source_review', 'exclude_dhf_insufficient', [196750, 196741, 196737, 196789],
        'HF诊断来自疑似复制段：同一文书67岁左侧支架/室速消融与72岁右侧取栓的本次病程矛盾；当日心超EF60%、仅左房大和轻度反流。',
        '剔除该文书用于表型后，BNP升高和房颤不能单独确诊失代偿；无独立充血及心衰管理证据，予排除草案。不是认定患者从无慢性心衰。'),
    '1723933_37': ('dhf_supported', 'eligibility_pending', [65442],
        '首次病程明确急性心力衰竭、全身中高度凹陷性浮肿、心界扩大和当日心超左室收缩功能减低；有IV呋塞米及NT-proBNP结果。',
        '肺部感染/气道出血并存，不能仅因替代诊断提及而否定心衰。旧规则未覆盖全身浮肿且未利用文书心超，补入语义支持队列。'),
    '2822361_29': ('dhf_supported', 'eligibility_pending', [46052, 46060],
        '本次气急加重、双下肢水肿/湿啰音、明确HF NYHA III及IV呋塞米；心超右房大、三尖瓣反流及肺高压支持，EF60%不排除右心/HFpEF谱系。',
        'COPD/支扩并存；不指定HFpEF亚型。空白入ICU模板中的升压/CRRT措辞不计实际执行；T0为上下文支持时间，尚需T12观察链。'),
    '1813317_337': ('uncertain_cardiac_contribution', 'eligibility_pending', [31141],
        '首次病程列HF且记BNP2128pg/mL，胸闷气急与湿啰音可支持；高碳酸血症、肺性脑病及感染亦可解释呼吸恶化。',
        'NIV不能自动归因为HF管理；本窗尚缺明确心源充血和HF强化治疗。保留不确定，未上报为最终阳性或阴性。'),
    '2314812_30': ('dhf_supported', 'exclude_preT12_vaso_lactate_proxy', [78631, 78637, 78656],
        '急性心梗、心源性休克、湿啰音及心超EF40%，血管活性支持；有独立急性心功能失代偿证据。',
        '入ICU早期文书乳酸4.1mmol/L并用多巴胺/去甲肾上腺素，支持061C前12h血管活性药且乳酸>=2的排除草案；仍为文书/医嘱时间代理。IABP已用，ECMO建议被拒绝，不能把建议算执行。'),
}


def save(name, rows):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    records=defaultdict(dict)
    for line in (OUT/'focused_source_records.jsonl').open():
        r=json.loads(line);records[r['visit_id']][r['source_row']]=r
    nursing_counts=defaultdict(Counter)
    for p in DATA.glob('*/02_rdr_bedside.csv'):
        for r in read(p):
            if r['就诊号'] in TIME_DECISIONS:
                nursing_counts[r['就诊号']]['nonempty_rows']+=bool(r['项目名称'])
                nursing_counts[r['就诊号']]['remark_rows']+=r['项目名称']=='备注'
    timing=[]
    for visit,(t,status,line,reason) in TIME_DECISIONS.items():
        src=records[visit][line]
        timing.append(dict(visit_id=visit,reviewed_t0=t,time_review_status=status,apply_time=int(bool(t)),
                           source_file=src['source_file'],source_row=line,evidence_reason=reason,
                           nursing_nonempty_rows=nursing_counts[visit]['nonempty_rows'],
                           nursing_remark_rows=nursing_counts[visit]['remark_rows'],reviewer_type='AI_source_review'))
    save('focused_time_review_22.csv',timing)
    semantic=[]
    for visit,(phenotype,risk,lines,reason,boundary) in SEMANTIC_DECISIONS.items():
        src=[records[visit][line] for line in lines]
        semantic.append(dict(visit_id=visit,phenotype_semantic_status=phenotype,riskset_review_status=risk,
                             hf_decompensation_reason=reason,eligibility_or_uncertainty=boundary,
                             source_refs=';'.join(f"{r['source_file']}#row={r['source_row']}" for r in src),
                             review_scope='full_selected_admission_and_SOAP_plus_report_order_crosscheck',
                             reviewer_type='AI_pre_review_not_independent_physician',final_analysis_inclusion='not_frozen'))
    save('focused_semantic_review_7.csv',semantic)
    bad=records['7039751_3'][196750]
    save('document_quarantine.csv',[dict(visit_id=bad['visit_id'],source_file=bad['source_file'],
        source_row=bad['source_row'],reason='inconsistent_age_procedure_laterality_and_unrelated_HF_diagnosis_block',
        use='exclude_phenotype_only_keep_raw_for_audit')])
    print(json.dumps(dict(time_cases=len(timing),time_status_counts=Counter(r['time_review_status'] for r in timing),
        semantic_cases=len(semantic),phenotype_counts=Counter(r['phenotype_semantic_status'] for r in semantic),
        source_quarantine_rows=1),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
