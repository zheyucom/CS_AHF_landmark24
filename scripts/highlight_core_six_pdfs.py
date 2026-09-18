#!/usr/bin/env python3
"""Create non-destructive, field-highlighted copies of the core literature set."""

from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "literature_review" / "导师交付_核心文献高光PDF_可编辑"

COLORS = {
    "population_time": (1.0, 0.90, 0.20),
    "endpoint": (1.0, 0.35, 0.35),
    "model_validation": (0.35, 0.65, 1.0),
    "result": (0.35, 0.85, 0.45),
    "limitation": (0.75, 0.45, 0.90),
    "direct_use": (1.0, 0.60, 0.20),
}

RULES = {
    "00_Metra_2023_WHF临床共识_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/EUZINEQY/viewtext.pdf",
        "population_time": ["worsening heart failure", "hospitalized", "outpatient"],
        "endpoint": ["worsening signs and symptoms", "intensification of treatment", "escalation of therapy"],
        "model_validation": ["consensus statement", "definition"],
        "result": ["mortality", "hospitalization"],
        "limitation": ["limitations", "lack of"],
        "direct_use": ["treatment intensification", "clinical deterioration"],
    },
    "01_DeVore_2014_WHF结局与预后_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/SRLF57EW/DeVore 等 - 2014 - In‐Hospital Worsening Heart Failure and Associations With Mortality, Readmission, and Healthcare Uti.pdf",
        "population_time": ["patients hospitalized with acute heart failure", "at least 12 hours after hospital presentation", "65 years and older"],
        "endpoint": ["need for escalation of therapy", "initiated inotropic medications or an intravenous vasodilator more than 12 hours", "transferred to the intensive care unit"],
        "model_validation": ["retrospective, observational study", "sensitivity analyses"],
        "result": ["63 727 patients", "11% developed worsening heart failure", "adjusted hazards of 30-day mortality were 2.56", "19.0% at 30 days and 50.1% at 1 year"],
        "limitation": ["limited by the variables collected", "residual measured or unmeasured confounding", "may not be generalizable"],
        "direct_use": ["Prevention and treatment of in-hospital worsening heart failure represents an important goal"],
    },
    "02_DeVore_2016_ADHERE风险模型_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/HP5WM4PU/DeVore 等 - 2016 - Development and validation of a risk model for in-hospital worsening heart failure from the Acute De.pdf",
        "population_time": ["patients hospitalized with acute heart failure", "within 12 hours of hospital presentation", "more than 12 hours after hospital presentation"],
        "endpoint": ["persistent or worsening signs or symptoms requiring an escalation of therapy", "In-hospital worsening heart failure"],
        "model_validation": ["logistic regression with robust standard errors", "66% random derivation sample", "remaining 34%", "calibration and discrimination"],
        "result": ["23,696 patients", "15.4% and 15.6%", "c statistic, 0.74", "validation sample (c statistic, 0.72)", "increased troponin and creatinine"],
        "limitation": ["Our analysis has limitations", "may not be generalizable", "did not have data on all potential predictors"],
        "direct_use": ["identify those at increased risk for in-hospital worsening heart failure"],
    },
    "03_Rahman_2022_AHF到CS早期预测_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/CGNVH9S5/Rahman 等 - 2022 - Using Machine Learning for Early Prediction of Cardiogenic Shock in Patients With Acute Heart Failur.pdf",
        "population_time": ["patients with acute heart failure", "12 hours", "24 hours"],
        "endpoint": ["cardiogenic shock", "onset of CS", "vasopressor"],
        "model_validation": ["machine learning", "cross-validation", "random forest", "gradient boosting"],
        "result": ["area under the receiver operating characteristic curve", "sensitivity", "specificity", "hours before"],
        "limitation": ["limitations", "single-center", "retrospective"],
        "direct_use": ["false-positive", "true-positive", "early prediction"],
    },
    "04_Chang_2022_CS早期预测_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/MY94PZFZ/Chang 等 - 2022 - Early Prediction of Cardiogenic Shock Using Machine Learning.pdf",
        "population_time": ["adult patients", "MIMIC-III", "intensive care unit"],
        "endpoint": ["cardiogenic shock", "shock index", "vasopressor"],
        "model_validation": ["machine learning", "cross-validation", "XGBoost", "random forest"],
        "result": ["AUROC", "AUC", "accuracy", "sensitivity"],
        "limitation": ["limitations", "single-center", "retrospective"],
        "direct_use": ["early prediction", "before the onset"],
    },
    "05_Zhang_2024_HF合并Sepsis死亡预测_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/BNMSDQMS/Zhang 等 - 2024 - Survival prediction for heart failure complicated by sepsis based on machine learning methods.pdf",
        "population_time": ["patients with heart failure and sepsis", "ICU stays less than 1 day", "under 18 years old"],
        "endpoint": ["28-day all-cause mortality", "28-day in-hospital mortality"],
        "model_validation": ["eICU-CRD", "MIMIC-IV", "external validation", "10-fold cross-validation", "Logistic Regression"],
        "result": ["6819 patients", "3891 cases", "2928 cases", "AUC of 0.746", "AUC of 0.699", "Brier score of 0.169"],
        "limitation": ["limitations", "retrospective", "missing"],
        "direct_use": ["mortality among patients with heart failure and sepsis", "norepinephrine", "phenylephrine"],
    },
    "06_Gao_2026_CVICU血流动力学恶化_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/AKNCTVSE/Gao 等 - 2026 - Machine learning-based early warning system for hemodynamic deterioration in cardiovascular ICU pati.pdf",
        "population_time": ["adult patients aged 18 years or older", "ICU length of stay of at least 24 h", "first 24 h of ICU admission", "subsequent ICU stay"],
        "endpoint": ["strict composite outcome", "hemodynamic instability", "tissue hypoperfusion", "confirmed cardiac etiology"],
        "model_validation": ["bidirectional cross-validation", "strictly held-out external validation set", "without any retraining or parameter tuning", "10-fold stratified cross-validation"],
        "result": ["46,007 admissions", "50,949 admissions", "AUROC of 0.841", "AUROC of 0.852", "SOFA (AUROC 0.681)", "APACHE II (AUROC 0.747)"],
        "limitation": ["limitations", "retrospective", "missing more than 50%"],
        "direct_use": ["feature set to avoid mathematical redundancy", "prevent data leakage", "risk stratification system"],
    },
    "07_Beer_2024_AHF心脏恶化到CS_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/4XSPY6Z3/Beer 等 - 2024 - Prediction of cardiac worsening through to cardiogenic shock in patients with acute heart failure.pdf",
        "population_time": ["acute heart failure", "CYCLE", "admission"],
        "endpoint": ["worsening heart failure", "cardiogenic shock", "SCAI"],
        "model_validation": ["logistic regression", "multivariable"],
        "result": ["223 patients", "96", "18 patients", "NT-proBNP", "creatinine"],
        "limitation": ["limitations", "single-centre", "small sample"],
        "direct_use": ["tricuspid regurgitation", "pro-adrenomedullin", "renal function"],
    },
    "08_Hu_2024_动态CS外部验证_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/L8WRQD4A/Hu 等 - 2024 - Development and external validation of a dynamic risk score for early prediction of cardiogenic shoc.pdf",
        "population_time": ["acute decompensated heart failure", "myocardial infarction", "hourly"],
        "endpoint": ["cardiogenic shock", "mixed shock", "new-onset"],
        "model_validation": ["external validation", "MIMIC-III", "NYU", "pretraining"],
        "result": ["AUROC", "AUPRC", "37 h", "1,500", "131"],
        "limitation": ["limitations", "small", "single-center"],
        "direct_use": ["dynamic risk score", "transfer", "measurement frequency"],
    },
    "09_Essay_2020_ICU新发AHF动态预测_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/L97SD5UF/Essay 等 - 2020 - Decompensation in Critical Care Early Prediction of Acute Heart Failure Onset.pdf",
        "population_time": ["intensive care unit", "acute heart failure", "tele-ICU"],
        "endpoint": ["decompensation", "onset of AHF"],
        "model_validation": ["random forest", "cross-validation", "machine learning"],
        "result": ["AUROC", "0.9503", "200 minutes", "26,534", "96,350"],
        "limitation": ["limitations", "retrospective"],
        "direct_use": ["vital signs", "observation window", "early prediction"],
    },
    "10_Greene_2023_WHF术语框架_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/CXB7REH4/Greene 等 - 2023 - Worsening Heart Failure Nomenclature, Epidemiology, and Future Directions.pdf",
        "population_time": ["worsening heart failure", "hospitalized", "ambulatory"],
        "endpoint": ["intensification of therapy", "hospitalization", "urgent visit"],
        "model_validation": ["nomenclature", "definition"],
        "result": ["mortality", "readmission", "risk"],
        "limitation": ["limitations", "heterogeneity"],
        "direct_use": ["trajectory", "continuum", "treatment intensification"],
    },
    "11_Collins_2024_TRIPOD_AI报告规范_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/FIV3J6L7/Collins 等 - 2024 - TRIPOD+AI statement updated guidance for reporting clinical prediction models that use regression o.pdf",
        "population_time": ["target population", "eligibility criteria", "study setting"],
        "endpoint": ["outcome", "time horizon"],
        "model_validation": ["external validation", "calibration", "discrimination", "missing data", "sample size"],
        "result": ["27-item", "checklist"],
        "limitation": ["limitations", "applicability"],
        "direct_use": ["transparent reporting", "protocol", "data sharing"],
    },
    "12_Moons_2025_PROBAST_AI偏倚工具_高光.pdf": {
        "src": "/Users/zheyu/Zotero/storage/ECELTRZM/Moons 等 - 2025 - PROBAST+AI an updated quality, risk of bias, and applicability assessment tool for prediction model.pdf",
        "population_time": ["participants", "target population"],
        "endpoint": ["outcome", "predictors"],
        "model_validation": ["risk of bias", "applicability", "analysis", "calibration", "external validation"],
        "result": ["PROBAST+AI", "signalling questions"],
        "limitation": ["limitations", "high risk of bias"],
        "direct_use": ["model development", "model evaluation", "quality assessment"],
    },
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    for output_name, config in RULES.items():
        if not Path(config["src"]).exists():
            summary.append((output_name, {"missing_source": 1}, 0))
            continue
        doc = fitz.open(config["src"])
        counts = {field: 0 for field in COLORS}
        phrase_counts = {}
        seen = set()
        for page in doc:
            for field, color in COLORS.items():
                for phrase in config.get(field, []):
                    phrase_key = (field, phrase)
                    for rect in page.search_for(phrase):
                        if counts[field] >= 12 or phrase_counts.get(phrase_key, 0) >= 4:
                            break
                        key = (page.number, round(rect.x0, 1), round(rect.y0, 1), field)
                        if key in seen:
                            continue
                        seen.add(key)
                        annot = page.add_highlight_annot(rect)
                        annot.set_colors(stroke=color)
                        annot.set_info(content=f"字段：{field}; 关键词：{phrase}")
                        annot.update(opacity=0.42)
                        counts[field] += 1
                        phrase_counts[phrase_key] = phrase_counts.get(phrase_key, 0) + 1
        target = OUT / output_name
        if target.exists():
            target.unlink()
        doc.save(target, garbage=4, deflate=True)
        doc.close()
        summary.append((output_name, counts, sum(counts.values())))

    for name, counts, total in summary:
        detail = ", ".join(f"{k}={v}" for k, v in counts.items())
        print(f"{name}\ttotal={total}\t{detail}")


if __name__ == "__main__":
    main()
