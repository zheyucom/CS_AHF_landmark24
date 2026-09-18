#!/usr/bin/env python3
"""Conservative machine-assisted pre-review for the 50 internal Gate-3 stays.

Raw DHF_SRR exports are read-only. Every semantic assignment is either supported
by a time-bounded source row or retained as uncertain/unknown for clinician review.
"""
from __future__ import annotations
import csv, glob, re
from pathlib import Path
from datetime import timedelta
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "project_control/internal_validation/20260912"
INFILE = BASE / "internal_gate3_manual_review_50_20260913.csv"
OUTFILE = BASE / "internal_gate3_manual_review_50_20260913_reviewed.csv"
NEEDFILE = BASE / "internal_gate3_manual_review_50_20260913_need_user_check.csv"

# User-adjudicated corrections from the 2026-09-13 clinical review. These are
# explicit episode-level facts, not model predictions.
MANUAL = {
    "G3-001": {"validity": "valid", "comment": "用户确认：心脏骤停后危重状态，EF 15%及心室活动明显减弱保留为有效报告"},
    "G3-005": {"t0": "2025-08-15 10:15:00", "source": "icu_document_event_time", "comment": "用户核对：入院/出ICU文书均记录本次EICU入院时间2025-08-15 10:15"},
    "G3-015": {"t0": "2025-01-07 12:45:00", "source": "icu_document_event_time", "comment": "用户核对：首次病程录、病案首页及转入记录支持本次ICU入院时间2025-01-07 12:45"},
    "G3-029": {"t0": "2025-04-26 12:20:00", "source": "icu_document_event_time", "comment": "用户核对：首次病程录、ICU转病房记录支持本次ICU入院时间2025-04-26 12:20"},
    "G3-043": {"t0": "2022-01-08 09:35:00", "source": "icu_document_event_time", "hf": "no", "decomp": "no", "mgmt": "no", "tier": "not_supported", "discrepancy": "同一次就诊存在多段ICU：首段2022-01-08 09:35入ICU，2022-01-09转消化内科/后转普外科；2022-01-12手术后再入ICU（17:35）。本研究index采用首段ICU；患者无DHF。", "comment": "用户核对：多次ICU事件已按首段index处理，2022-01-12为再入ICU且无DHF"},
    "G3-050": {"t0": "2025-06-03 22:15:00", "source": "icu_document_event_time", "comment": "用户核对：首次病程录、出ICU记录及病案首页支持本次ICU入院时间2025-06-03 22:15"},
}


def read_many(pattern, usecols=None):
    frames=[]
    for f in glob.glob(str(ROOT / pattern)):
        try:
            d=pd.read_csv(f,dtype=str,usecols=usecols,encoding="utf-8-sig",low_memory=False)
            d["_source_file"]=f
            frames.append(d)
        except Exception:
            pass
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()


def dt(x):
    return pd.to_datetime(x,errors="coerce")

DATE_RE = re.compile(r"(?:20\d{2}[年/-]\d{1,2}[月/-]\d{1,2}(?:日)?|\d{4}\.\d{1,2}\.\d{1,2})(?:[ T日]\s*)?\d{1,2}[:：]\d{2}(?::\d{2})?")

def extract_dates_near(text, terms):
    text=str(text or "")
    out=[]
    for m in re.finditer("|".join(map(re.escape,terms)),text,re.I):
        lo=max(0,m.start()-100); hi=min(len(text),m.end()+120)
        chunk=text[lo:hi]
        for dm in DATE_RE.finditer(chunk):
            s=dm.group(0).replace("年","-").replace("月","-").replace("日"," ").replace("/","-").replace(".","-").replace("：",":")
            t=pd.to_datetime(s,errors="coerce")
            if pd.notna(t): out.append((t,m.group(0),chunk[:180].replace("\\n"," ")))
    # unique by timestamp
    seen=set(); ans=[]
    for x in out:
        k=str(x[0])
        if k not in seen: seen.add(k); ans.append(x)
    return ans

def explicit_icu_times(text):
    """Extract only dates syntactically attached to an ICU admission event."""
    text = str(text or "")
    pats = [
        r"入ICU时间\s*[:：]\s*([0-9]{4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}(?:日)?\s*[0-9]{1,2}[:：][0-9]{2}(?::[0-9]{2})?)",
        r"患者于\s*([0-9]{4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}(?:日)?\s*[0-9]{1,2}[:：][0-9]{2}(?::[0-9]{2})?).{0,30}(?:入|转入)ICU",
        r"(?:于|在)\s*([0-9]{4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}(?:日)?\s*[0-9]{1,2}[:：][0-9]{2}(?::[0-9]{2})?).{0,15}(?:进入|入住)ICU",
    ]
    vals=[]
    for p in pats:
        for m in re.finditer(p,text,re.I):
            s=m.group(1).replace("年","-").replace("月","-").replace("日"," ").replace("/","-").replace(".","-").replace("：",":")
            t=pd.to_datetime(s,errors="coerce")
            if pd.notna(t): vals.append(t)
    return sorted(set(vals))


def non_template_hit(text, positive_terms):
    text=str(text or "")
    neg = re.search(r"(?:否认|无|未见|未发现|排除|不支持|没有).{0,18}(?:心衰|心力衰竭|肺水肿|肺淤血|肺充血)",text)
    risk = re.search(r"(?:可能出现|可能发生|风险|告知|知情|并发症|评分|排除).{0,30}(?:心衰|心力衰竭|休克|死亡|肺水肿)",text)
    pos = any(re.search(t,text,re.I) for t in positive_terms)
    return bool(pos and not neg and not risk)

def contextual_status(text, yes_terms, uncertain_terms=()):
    """Classify local sentence windows, avoiding global template contamination."""
    text = str(text or "")
    yes = False; maybe = False
    for pat in yes_terms:
        for m in re.finditer(pat, text, re.I):
            w = text[max(0, m.start()-70):min(len(text), m.end()+90)]
            if re.search(r"否认|无|未见|未发现|排除|不支持|没有|可能出现|可能发生|风险|告知|知情|并发症|评分", w):
                continue
            yes = True
    for pat in uncertain_terms:
        for m in re.finditer(pat, text, re.I):
            w = text[max(0, m.start()-70):min(len(text), m.end()+90)]
            if not re.search(r"否认|无|未见|排除", w):
                maybe = True
    return "yes" if yes else ("uncertain" if maybe else "unknown")


def main():
    base=pd.read_csv(INFILE,dtype=str,encoding="utf-8-sig").fillna("")
    docs=read_many("DHF_SRR/*全部文书*/02_rdr_medrecord_list.csv")
    exams=read_many("DHF_SRR/*检查记录*/02_rdr_exam_master_report.csv")
    meds=read_many("DHF_SRR/*用药记录*/02_rdr_orders.csv")
    diagnoses=read_many("DHF_SRR/*诊断信息*/02_rdr_diagnosis.csv")
    for d in (docs,exams,meds,diagnoses):
        if not d.empty:
            d["_visit"]=d.get("就诊号","").astype(str)
            d["_pid"]=d.get("患者ID","").astype(str)
    docs["_time"]=dt(docs.get("创建日期",pd.Series(dtype=str)))
    meds["_start"]=dt(meds.get("开嘱时间",pd.Series(dtype=str))); meds["_stop"]=dt(meds.get("停嘱时间",pd.Series(dtype=str)))
    diagnoses["_time"]=dt(diagnoses.get("诊断时间",pd.Series(dtype=str)))
    outputs=[]
    for _,r in base.iterrows():
        pid=str(r.patient_id); visit=str(r.visit_id); t0=dt(r.t0_candidate)
        manual = MANUAL.get(str(r.review_id), {})
        if manual.get("t0"): t0 = dt(manual["t0"])
        t12=t0+timedelta(hours=12) if pd.notna(t0) else pd.NaT
        comments=[]
        dd=docs[(docs._pid==pid)&(docs._visit==visit)] if not docs.empty else pd.DataFrame()
        ee=exams[(exams._pid==pid)&(exams._visit==visit)] if not exams.empty else pd.DataFrame()
        mm=meds[(meds._pid==pid)&(meds._visit==visit)] if not meds.empty else pd.DataFrame()
        dx=diagnoses[(diagnoses._pid==pid)&(diagnoses._visit==visit)] if not diagnoses.empty else pd.DataFrame()
        # T0 evidence: explicit event time in ICU transfer/admission records, otherwise proxy.
        icu_hits=[]
        if not dd.empty:
            for _,x in dd.iterrows():
                name=str(x.get("文书名称","")); text=str(x.get("文本病历",""))
                if re.search(r"入ICU|入监护室|转入ICU|转入重症|由.*(?:ICU|监护室|重症医学科).*(?:转入|进入)",name+text,re.I):
                    for hit_time in explicit_icu_times(text):
                        icu_hits.append((hit_time,name,x.get("创建日期","")))
        t0_final=t0; t0_source="structured_proxy_uncertain"; discrepancy=""
        if icu_hits:
            icu_hits=sorted(icu_hits,key=lambda z:z[0])
            near=[h for h in icu_hits if pd.notna(t0) and abs(h[0]-t0)<=timedelta(hours=24)]
            if len(icu_hits)==1 and abs(icu_hits[0][0]-t0)<=timedelta(hours=6):
                t0_final=icu_hits[0][0]; t0_source="icu_document_event_time"
            elif len(near)==1 and abs(near[0][0]-t0)<=timedelta(hours=6):
                t0_final=near[0][0]; t0_source="icu_document_event_time"
            else:
                t0_source="uncertain_conflict"; discrepancy="candidate=%s; explicit ICU text=%s"%(r.t0_candidate, ", ".join(str(x[0]) for x in icu_hits[:4]))
                comments.append("T0冲突："+discrepancy)
        else:
            comments.append("未检出带明确时间的入ICU/转ICU文本，暂用结构化入区代理")
        if manual.get("source"):
            t0_source = manual["source"]
            discrepancy = manual.get("discrepancy", "")
            comments = [manual["comment"]]
        # Echo facts from selected report row.
        finding=str(r.finding); conclusion=str(r.conclusion); echo_text=finding+" "+conclusion
        completed="yes" if echo_text.strip() else "uncertain"
        result="yes" if finding.strip() or conclusion.strip() else "no"
        # A limited view (for example, pulmonary artery not visualised) can still
        # yield a valid conclusion. Reserve uninterpretable for explicit failure
        # to assess a key result or absent report conclusion.
        validity="uninterpretable" if re.search(r"无法评估|无法测量|各瓣膜口血流无法评估",echo_text) else ("valid" if result=="yes" else "uncertain")
        if manual.get("validity"): validity = manual["validity"]
        domains=[]
        if re.search(r"EF\s*[:：]?\s*(?:1[0-9]|2[0-9]|3[0-9]|4[0-9])%?|射血分数.{0,5}(?:降低|减低)|左室壁活动.{0,8}(?:减弱|消失)",echo_text,re.I): domains.append("LV_systolic")
        if re.search(r"舒张|左房.{0,8}(?:增大|扩大)|室间隔.{0,8}(?:增厚|厚)",echo_text): domains.append("diastolic_filling")
        if re.search(r"右室|肺动脉压|肺高压|三尖瓣反流速度",echo_text): domains.append("RV_PH")
        if re.search(r"瓣膜.{0,12}(?:中度|重度|狭窄|关闭不全)|主动脉瓣.{0,12}(?:狭窄|反流)",echo_text): domains.append("valve")
        if re.search(r"心包.{0,12}(?:积液|增厚|压塞)",echo_text): domains.append("pericardium")
        if not domains and re.search(r"轻度.*反流|少量反流|退行性变",echo_text): domains.append("valve_minor")
        abnormal="yes" if domains and not (len(domains)==1 and domains[0]=="valve_minor") else ("no" if re.search(r"未见明显异常|各结构正常|未见异常",conclusion) and not domains else "uncertain")
        # Time bounded clinical text and diagnoses.
        lo=t0-timedelta(hours=24) if pd.notna(t0) else pd.NaT
        scoped=dd[(dd._time>=lo)&(dd._time<t12)] if (not dd.empty and pd.notna(lo)) else dd.iloc[0:0]
        text_blob=" ".join((str(x.get("文书名称",""))+" "+str(x.get("文本病历",""))) for _,x in scoped.iterrows())
        hf_diag=bool(not dx.empty and dx[(dx._time>=lo)&(dx._time<t12)]["诊断名称"].astype(str).str.contains("心衰|心力衰竭",regex=True).any()) if pd.notna(lo) else False
        hf_ctx = contextual_status(text_blob,
            [r"急性心力衰竭", r"急性心衰", r"心功能不全", r"心功能[ⅡⅢIV1-4]{1,4}级", r"心源性休克"],
            [r"心衰可能", r"考虑.{0,12}心衰", r"合并.{0,12}心衰"])
        hf = "yes" if hf_diag else hf_ctx
        if hf == "unknown" and re.search(r"(?:否认|无|未见).{0,10}(?:心衰|心力衰竭|心功能不全)", text_blob): hf = "no"
        decomp = contextual_status(text_blob,
            [r"肺水肿", r"肺淤血", r"肺充血", r"端坐呼吸", r"容量超负荷", r"双下肢.{0,8}水肿", r"下肢.{0,8}水肿"],
            [r"呼吸困难", r"胸闷气急", r"BNP.{0,15}(?:升高|高)"])
        if decomp == "unknown" and re.search(r"(?:无|未见|否认).{0,12}(?:肺水肿|肺淤血|呼吸困难|下肢水肿)", text_blob): decomp = "no"
        loop=mm[mm.apply(lambda x: bool(re.search(r"呋塞米|托拉塞米|布美他尼|利尿", str(x.get("药品名称", "")))), axis=1)] if not mm.empty else mm
        loop_window=loop[(loop._start<t12)&((loop._stop.isna())|(loop._stop>=lo))] if not loop.empty and pd.notna(lo) else loop.iloc[0:0]
        mgmt="yes" if (len(loop_window)>0 and (re.search(r"予以|加用|继续|加强|利尿",text_blob) or len(loop_window)>0)) else ("uncertain" if len(loop_window)>0 else "unknown")
        tier="multidomain_draft" if hf=="yes" and decomp=="yes" and mgmt=="yes" and abnormal=="yes" else ("echo_supported_draft" if hf=="yes" and abnormal=="yes" else ("not_supported" if hf=="no" else "unknown"))
        if manual.get("hf"): hf = manual["hf"]
        if manual.get("decomp"): decomp = manual["decomp"]
        if manual.get("mgmt"): mgmt = manual["mgmt"]
        if manual.get("tier"): tier = manual["tier"]
        if hf == "uncertain": comments.append("T12前未找到可排除模板/否定语境的明确心衰锚点，待临床核对")
        elif hf == "yes": comments.append("T12前文书/诊断含明确心衰或心功能不全锚点，需核对是否为本次失代偿")
        if decomp == "uncertain": comments.append("T12前失代偿域未形成可审计阳性证据，待核对症状/体征/影像/BNP")
        elif decomp == "yes": comments.append("T12前文书含局部失代偿表现，需核对替代解释和发生时间")
        if mgmt in ("unknown", "uncertain"): comments.append("治疗强化仅能由医嘱区间部分代理，未作为执行级结局")
        if abnormal == "uncertain": comments.append("心超异常域无法安全归类，需核对原报告")
        # Preserve every user-adjudicated note in the audit trail, including
        # semantic corrections that do not change the T0 source.
        if manual.get("comment") and manual["comment"] not in comments: comments.insert(0, manual["comment"])
        # ICU out/major outcome documents.
        out_hits=[]; death=False; auto=False; discharge=False; transfer=False
        if not dd.empty:
            for _,x in dd.iterrows():
                name=str(x.get("文书名称","")); text=str(x.get("文本病历","")); both=name+text
                m_out=re.search(r"患者于\s*([0-9]{4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}(?:日)?\s*[0-9]{1,2}[:：][0-9]{2}(?::[0-9]{2})?).{0,50}(?:由.+?)?(?:转入|离开)",text,re.I)
                if m_out:
                    s=m_out.group(1).replace("年","-").replace("月","-").replace("日"," ").replace("/","-").replace(".","-").replace("：",":")
                    tt=pd.to_datetime(s,errors="coerce")
                    if pd.notna(tt): out_hits.append((tt,name))
                if re.search(r"死亡记录|死亡证明|患者死亡|临床死亡",name+text) and not re.search(r"风险|可能.*死亡|告知",text): death=True
                if re.search(r"自动出院|放弃治疗|要求出院",both): auto=True
                if re.search(r"出院记录|出院小结",name) and re.search(r"出院日期\s*[:：]?\s*20\d{2}",text): discharge=True
                if m_out and re.search(r"转入|离开",m_out.group(0)): transfer=True
        icu_out=""; icu_out_source=""; outcome="unknown"
        if out_hits:
            h=min(out_hits,key=lambda z:z[0]); icu_out=str(h[0]); icu_out_source="document_event_time"; comments.append("ICU出科证据：%s %s"%(h[1],h[0]))
        if death: outcome="death_in_icu" if not out_hits else "death_after_icu"
        elif auto: outcome="automatic_discharge"
        elif discharge: outcome="hospital_discharge"
        elif transfer: outcome="alive_transfer"
        # Keep execution-level event fields blank unless an explicit event time can be established.
        outputs.append({**r.to_dict(),"reviewer_id":"codex_pre_review_20260913","t0_time_final":str(t0_final) if pd.notna(t0_final) else "","t0_source_final":t0_source,"t0_discrepancy_reason":discrepancy,"echo_completed_final":completed,"echo_result_available_final":result,"echo_abnormal_support_final":abnormal,"echo_abnormal_domains":";".join(domains),"echo_report_time_semantics":"report_time","echo_report_validity":validity,"hf_anchor_support_final":hf,"decompensation_domain_final":decomp,"management_evidence_final":mgmt,"dhf_tier_final":tier,"icu_out_time_final":icu_out,"icu_out_source_final":icu_out_source,"outcome_status_final":outcome,"event_time_final":"","event_component_final":"","competing_time_final":"","censor_time_final":"","review_comments":"；".join(comments)})
    out=pd.DataFrame(outputs)
    out.to_csv(OUTFILE,index=False,encoding="utf-8-sig")
    need = out[
        out.t0_source_final.isin(["structured_proxy_uncertain", "uncertain_conflict"])
        | (out.echo_report_validity == "uninterpretable")
    ].copy()
    need["user_check_reason"] = need.apply(
        lambda x: "T0候选与明确ICU文本时间冲突" if x.t0_source_final == "uncertain_conflict"
        else ("缺少明确入ICU/转ICU事件时间，需核对护理或转入文书" if x.t0_source_final == "structured_proxy_uncertain" else "心超报告存在无法评估/关键结果不可测描述，需核对原报告"), axis=1)
    need.to_csv(NEEDFILE,index=False,encoding="utf-8-sig")
    print("wrote",OUTFILE,"rows",len(out),"need_user_check",len(need),"file",NEEDFILE)
    print(out[["review_id","t0_source_final","echo_abnormal_support_final","hf_anchor_support_final","decompensation_domain_final","management_evidence_final","dhf_tier_final","outcome_status_final"]].to_string(index=False))

if __name__=="__main__": main()
