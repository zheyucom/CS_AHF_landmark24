#!/usr/bin/env python3
"""Extract auditable Gate-3 DHF evidence for the 45-case priority queue.

This is a review aid, not a diagnostic classifier. It restricts documents,
diagnoses, labs and orders to the pre-T12 window and keeps short source
snippets so a clinician can adjudicate without rereading the full export.
"""
from pathlib import Path
import glob, re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "project_control/internal_validation/20260912"
INFILE = BASE / "internal_gate3_semantic_priority_queue_20260913.csv"
OUTFILE = BASE / "internal_gate3_semantic_evidence_20260914.csv"


def read_many(pattern):
    frames=[]
    for f in glob.glob(str(ROOT/pattern)):
        try:
            d=pd.read_csv(f,dtype=str,encoding="utf-8-sig",low_memory=False)
            d["_source_file"]=f
            frames.append(d)
        except Exception:
            pass
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()


def dt(s): return pd.to_datetime(s,errors="coerce")

def snippets(text, patterns, limit=3):
    text=re.sub(r"\s+"," ",str(text or "")); out=[]
    for p in patterns:
        for m in re.finditer(p,text,re.I):
            out.append(text[max(0,m.start()-90):min(len(text),m.end()+150)])
            if len(out)>=limit: return out
    return out


def main():
    q=pd.read_csv(INFILE,dtype=str,encoding="utf-8-sig").fillna("")
    docs=read_many("DHF_SRR/*全部文书*/02_rdr_medrecord_list.csv")
    dx=read_many("DHF_SRR/*诊断信息*/02_rdr_diagnosis.csv")
    labs=read_many("DHF_SRR/*检验记录*/02_rdr_lab_test_data.csv")
    meds=read_many("DHF_SRR/*用药记录*/02_rdr_orders.csv")
    for d in (docs,dx,labs,meds):
        if not d.empty:
            d["_pid"]=d.get("患者ID","").astype(str); d["_visit"]=d.get("就诊号","").astype(str)
    if not docs.empty: docs["_time"]=dt(docs.get("创建日期",pd.Series(dtype=str)))
    if not dx.empty: dx["_time"]=dt(dx.get("诊断时间",pd.Series(dtype=str)))
    if not labs.empty: labs["_time"]=dt(labs.get("检验[报告]日期",pd.Series(dtype=str)))
    if not meds.empty: meds["_start"]=dt(meds.get("开嘱时间",pd.Series(dtype=str))); meds["_stop"]=dt(meds.get("停嘱时间",pd.Series(dtype=str)))
    rows=[]
    for _,r in q.iterrows():
        pid,visit=str(r.patient_id),str(r.visit_id); t0=dt(r.t0_time_final); t12=t0+pd.Timedelta(hours=12)
        lo=t0-pd.Timedelta(hours=24)
        dd=docs[(docs._pid==pid)&(docs._visit==visit)] if not docs.empty else docs
        scoped=dd[(dd._time>=lo)&(dd._time<t12)] if not dd.empty else dd
        text=" ".join((str(x.get("文书名称",""))+" "+str(x.get("文本病历",""))) for _,x in scoped.iterrows())
        dxx=dx[(dx._pid==pid)&(dx._visit==visit)&(dx._time>=lo)&(dx._time<t12)] if not dx.empty else dx
        lxx=labs[(labs._pid==pid)&(labs._visit==visit)&(labs._time>=lo)&(labs._time<t12)] if not labs.empty else labs
        mxx=meds[(meds._pid==pid)&(meds._visit==visit)&(meds._start<t12)&((meds._stop.isna())|(meds._stop>=lo))] if not meds.empty else meds
        dx_names="；".join(sorted(set(str(x) for x in dxx.get("诊断名称",[]) if str(x).strip())))[:1200]
        bnp=lxx[lxx.get("检验指标","").astype(str).str.contains("BNP|NT.proBNP|脑钠肽",case=False,regex=True)] if not lxx.empty else lxx
        bnp_vals="；".join((str(x.get("检验指标",""))+"="+str(x.get("检验结果值",x.get("检验结果数值","")))+" @ "+str(x.get("检验[报告]日期",""))) for _,x in bnp.iterrows())[:1000]
        loop=mxx[mxx.get("药品名称","").astype(str).str.contains("呋塞米|托拉塞米|布美他尼|利尿",case=False,regex=True)] if not mxx.empty else mxx
        loop_orders="；".join((str(x.get("药品名称",""))+" "+str(x.get("剂量",""))+str(x.get("剂量单位",""))+" "+str(x.get("给药途径",""))+" ["+str(x.get("开嘱时间",""))+"~"+str(x.get("停嘱时间",""))+"]") for _,x in loop.iterrows())[:1600]
        evidence_patterns=[r"肺水肿|肺淤血|肺充血|容量超负荷|端坐呼吸|夜间阵发性呼吸困难|颈静脉怒张|双下肢.{0,8}水肿|下肢.{0,8}水肿",r"呼吸困难|胸闷气急|湿啰音|低氧|氧合",r"心衰|心力衰竭|心功能不全|心源性休克"]
        alt_patterns=[r"肺炎|感染|脓毒症|ARDS|急性呼吸窘迫|气胸|肺栓塞|出血|术后|创伤|COPD|哮喘"]
        rows.append({**r.to_dict(),"pre_t12_document_count":len(scoped),"pre_t12_document_evidence":" || ".join(snippets(text,evidence_patterns,4)),"alternative_explanation_evidence":" || ".join(snippets(text,alt_patterns,4)),"pre_t12_diagnoses":dx_names,"pre_t12_bnp":bnp_vals,"pre_t12_loop_orders":loop_orders,"pre_t12_document_names":"；".join(sorted(set(str(x.get('文书名称','')) for _,x in scoped.iterrows())))})
    pd.DataFrame(rows).to_csv(OUTFILE,index=False,encoding="utf-8-sig")
    print(f"wrote {OUTFILE} rows {len(rows)}")

if __name__=='__main__': main()
