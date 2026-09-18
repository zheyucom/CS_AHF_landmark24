# -*- coding: utf-8 -*-
"""生成 CS_AHF 分析可复现脚手架 V1.xlsx（4 张表 + 说明与进度）"""
try:
    import openpyxl
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "openpyxl>=3.1.0"])
    import openpyxl

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter


def xl_color(css_hex: str) -> str:
    value = css_hex.removeprefix("#").upper()
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB, got: {css_hex}")
    return "FF" + value


XL_HEAD_BG = xl_color("#4472C4")
XL_HEAD_FG = xl_color("#FFFFFF")
XL_TITLE = xl_color("#1F3864")
XL_EMPH_BG = xl_color("#2F5597")
XL_NOTE_BG = xl_color("#F2F2F2")
XL_NOTE_FG = xl_color("#595959")
XL_BODY_BG = xl_color("#FAFAFA")
XL_BORDER = xl_color("#BFBFBF")
XL_GREEN_BG = xl_color("#C6EFCE")
XL_GREEN_FG = xl_color("#006100")
XL_RED_BG = xl_color("#FFC7CE")
XL_RED_FG = xl_color("#9C0006")
XL_YEL_BG = xl_color("#FFEB9C")
XL_YEL_FG = xl_color("#9C6500")
XL_GRAY_BG = xl_color("#E7E6E6")
XL_GRAY_FG = xl_color("#595959")
XL_BLUE_BG = xl_color("#D9E2F3")
XL_BLUE_FG = xl_color("#1F3864")

THIN = Side(style="thin", color=XL_BORDER)
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FONT = Font(bold=True, color=XL_HEAD_FG, size=10)
TITLE_FONT = Font(bold=True, color=XL_TITLE, size=14)
NOTE_FONT = Font(italic=True, color=XL_NOTE_FG, size=9)
CELL_FONT = Font(size=10)

TITLE_ROW, NOTE_ROW, HEAD_ROW, DATA_ROW = 1, 2, 3, 4
WRAP_TOP = Alignment(wrap_text=True, vertical="top", horizontal="left")
CENTER = Alignment(horizontal="center", vertical="center")


def build_sheet(wb, name, title, note, headers, widths, wrap_cols, tab_color):
    ws = wb.create_sheet(name)
    ncol = len(headers)
    last = get_column_letter(ncol)

    ws.merge_cells(f"A{TITLE_ROW}:{last}{TITLE_ROW}")
    c = ws.cell(row=TITLE_ROW, column=1, value=title)
    c.font = TITLE_FONT
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[TITLE_ROW].height = 24

    ws.merge_cells(f"A{NOTE_ROW}:{last}{NOTE_ROW}")
    c = ws.cell(row=NOTE_ROW, column=1, value=note)
    c.font = NOTE_FONT
    c.fill = PatternFill("solid", start_color=XL_NOTE_BG, end_color=XL_NOTE_BG)
    c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
    ws.row_dimensions[NOTE_ROW].height = 30

    for i, h in enumerate(headers, start=1):
        cell = ws.cell(row=HEAD_ROW, column=i, value=h)
        cell.font = HEAD_FONT
        cell.fill = PatternFill("solid", start_color=XL_HEAD_BG, end_color=XL_HEAD_BG)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BOX
    ws.row_dimensions[HEAD_ROW].height = 32

    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.sheet_properties.tabColor = tab_color
    ws.freeze_panes = f"A{DATA_ROW}"
    return ws, wrap_cols


def write_rows(ws, rows, wrap_cols, start=DATA_ROW, center_cols=()):
    for r, row in enumerate(rows, start=start):
        for i, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=i, value=val)
            cell.font = CELL_FONT
            cell.border = BOX
            cell.alignment = CENTER if i in center_cols else WRAP_TOP
    return start + len(rows) - 1


wb = Workbook()
wb.remove(wb.active)

# ============================== 表A 研究合同 ==============================
A_HEAD = ["序号", "合同字段", "当前值", "状态", "来源 / 依据"]
A_W = [6, 20, 72, 11, 40]
A_ROWS = [
    (1, "合同ID", "CS_AHF-DHF-2026", "已冻结", "RESEARCH_LOGIC_CHAIN_20260916.md"),
    (2, "合同版本", "v1.1（对齐 study_definition_v5.7 + 统计分析计划 v1.0）", "已冻结", "study_definition_v5 / STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md"),
    (3, "研究问题", "在成人首次 index ICU stay 中，针对 T12 前已具有可时间追溯的多域 DHF 操作性表型、且 ICU 最初 12 h 未出现 overt shock proxy 的患者，能否用 [T0,T12) 可获得信息预测 T12-60 h 内治疗升级相关 ICU 血流动力学恶化或 ICU 内死亡？", "已冻结", "study_definition_v5 §1"),
    (4, "分析单位", "每患者 index hospitalization 内第一次 ICU stay", "已冻结", "study_definition_v5 §4"),
    (5, "数据源与版本", "MIMIC-IV v3.1（开发 / 内部验证）；本院床旁心超选择队列（锁模后外部验证）", "已冻结", "v3_reproducibility_manifest.md"),
    (6, "入组表型", "多域 DHF 操作性表型 = HF anchor + 时间合规失代偿佐证 + 同窗紧急管理/治疗证据；echo-supported 层作高特异性验证层，不作主队列硬门槛", "待闸门", "DHF_OPERATIONAL_PHENOTYPE_v20260914.md；受 G2 阻塞"),
    (7, "预测窗口", "[T0, T12)；变量必须 T12 前可获得", "已冻结", "study_definition_v5 §2"),
    (8, "风险窗口", "[T12, min(T60, alive index-ICU discharge))", "已冻结", "统计分析计划 v1.0 §2"),
    (9, "主事件", "treatment-escalation-based ICU hemodynamic deterioration + ICU 内死亡（composite）", "已冻结", "study_definition_v5 §4"),
    (10, "竞争事件", "alive index-ICU discharge", "已冻结", "统计分析计划 v1.0 §2"),
    (11, "行政删失", "T60 仍在 ICU 且尚未发生事件", "已冻结", "统计分析计划 v1.0 §2"),
    (12, "主估计量 / 主模型", "48 h 目标事件 CIF；Fine-Gray 主模型，1 h person-period 作结构补充", "已冻结", "统计分析计划 v1.0 §4.1-§4.2"),
    (13, "样本划分与验证", "外层 5 折（按 event/competing/censor + sepsis 分层）+ 内层 10 折 CV 选 lambda；锁模后本院原样外部预测", "已冻结", "统计分析计划 v1.0 §5"),
    (14, "候选变量与复杂度", "紧凑候选集；最终表型冻结后重算事件数与有效参数上限（EPV 警戒 10.1 仅为审计值）", "待闸门", "统计分析计划 v1.0 §3.3"),
    (15, "样本量与事件数", "待冻结。旧 650/66 与 5,549/452 均为 audit/可行性层，不得作为最终依据", "待闸门", "统计分析计划 v1.0 §8；受 G1/G2/G3 阻塞"),
]
wsA, wrapA = build_sheet(wb, "表A_研究合同",
                         "表A 研究合同（事实层）— 所有步骤协议的唯一上游",
                         "本表是唯一上游。步骤协议引用本表时须写「行号 + 冻结版本」而非自由文本；上游变更时下游可被机械找出。",
                         A_HEAD, A_W, [3, 5], "4472C4")
write_rows(wsA, A_ROWS, wrapA, center_cols=(1, 4))

dvA = DataValidation(type="list", formula1='"已冻结,待闸门,已作废"', allow_blank=True)
wsA.add_data_validation(dvA)
dvA.add(f"D{DATA_ROW}:D{DATA_ROW + len(A_ROWS) - 1}")
wsA.conditional_formatting.add(f"D{DATA_ROW}:D{DATA_ROW + len(A_ROWS) - 1}",
    CellIsRule(operator="equal", formula=['"已冻结"'],
               fill=PatternFill("solid", start_color=XL_GREEN_BG, end_color=XL_GREEN_BG),
               font=Font(color=XL_GREEN_FG, size=10)))
wsA.conditional_formatting.add(f"D{DATA_ROW}:D{DATA_ROW + len(A_ROWS) - 1}",
    CellIsRule(operator="equal", formula=['"待闸门"'],
               fill=PatternFill("solid", start_color=XL_YEL_BG, end_color=XL_YEL_BG),
               font=Font(color=XL_YEL_FG, size=10)))
wsA.conditional_formatting.add(f"D{DATA_ROW}:D{DATA_ROW + len(A_ROWS) - 1}",
    CellIsRule(operator="equal", formula=['"已作废"'],
               fill=PatternFill("solid", start_color=XL_GRAY_BG, end_color=XL_GRAY_BG),
               font=Font(color=XL_GRAY_FG, size=10)))
wsA.auto_filter.ref = f"A{HEAD_ROW}:E{DATA_ROW + len(A_ROWS) - 1}"

# ============================== 表B 步骤协议 ==============================
B_HEAD = ["步骤ID", "步骤名", "对应环节", "本步唯一目标", "输入（上游冻结产物）", "执行顺序",
          "必须冻结", "复现约束（本步须落盘的中间产物）", "禁止", "输出（文件名 + schema）",
          "验收对接", "展开程度"]
B_W = [8, 18, 18, 38, 34, 50, 42, 42, 32, 32, 14, 10]
B_ROWS = [
    ("S01", "数据字典与单位冻结", "G1 闸门 / 阶段6前置",
     "为每个候选变量定义来源字段、单位、生理合理范围、缺失语义与编码规则，成为后续解析与插补的唯一依据",
     "各库原始表 schema；FEATURE_FREEZE_V33.md；INTERNAL_HOSPITAL_FIELD_SEMANTICS_CONFIRMATION_CHECKLIST_V1",
     "① 按域列出全部候选变量；② 逐变量登记 来源表.字段/单位/取值时间/重复值汇总口径/生理范围/缺失语义；③ 逐项标 unit_status(confirmed|unknown|not_exported)；④ 输出并冻结版本号",
     "变量名单与顺序；依赖的源表 schema 版本；单位状态；生理范围阈值；缺失语义三分（结构性缺失 / 未测量 / 不适用）",
     "数据字典文件 + 版本号 + SHA-256；单位确认回执；变量-源表映射的机械校验输出",
     "在无字典依据时执行「结构性缺失填 0」；单位未确认时做跨库阈值比较；凭推测填写单位",
     "data_dictionary/data_dictionary_v1.csv + unit_status_report.csv",
     "C01-1 C01-2 C01-3", "骨架"),
    ("S02", "候选分母与唯一键", "阶段1",
     "建立 patient/hadm/stay 唯一非空键与成人边界，形成可追溯的候选分母",
     "MIMIC-IV 原始表；本院 8,385 行提取结果",
     "① 合并男女表并去重；② 校验 subject_id/hadm_id/stay_id 唯一且非空；③ 按年龄阈值与首次 ICU 规则筛成人；④ 输出候选分母与逐条排除计数",
     "唯一键定义；成人年龄阈值；首次 vs 全部 ICU stay 规则；数据快照时间",
     "候选分母 CSV；唯一性校验日志；逐条排除计数；源表行数快照",
     "把「心超选择后的分母」称为全院 ICU 总体；用旧派生表反向修改本轮计数",
     "cohort_denominator.csv + uniqueness_check.log",
     "C02-1 C02-2", "骨架"),
    ("S03", "截断值与检验值解析", "G1 闸门 / 清洗缺口 B-D",
     "把检验结果字符串统一解析为「值 + 边界语义 + 单位状态」，使任一结果都能回答「是否高于/低于某阈值」，且不把低于检出限当精确值、不把截断当缺失",
     "S01 数据字典；各库检验明细表（只读）；本院 NT-proBNP 截断实测（女 3.5%=857/24,705、男 4.4%=2,181/50,149，形态 >25000/<20/<20.00，「检验结果数值」列为空）",
     "① 枚举全部非数值形态（>x、<x、>=x、<=x、区间 a-b、空、溶血、未测、中文单位后缀）；② 实现单一函数 parse_lab_value() 返回 {lower,upper,censored_side,unit_status,raw_text}；③ 阈值判定仅当整个区间完全位于阈值一侧（>25000 可判 >5000 成立；<3 不得判低于 2）；④ 三个既有脚本改用该函数并删除各自解析分支；⑤ 对截断组做三种处理敏感性对比（log1p(边界) 保守代理 + 指示器 / 单独分箱 / 排除-仅诊断），三者方向一致才可报告；⑥ 报告截断值的比例、分布、按性别与病区分布",
     "阈值判定语义（区间完全一侧）；parse_lab_value 的返回结构与版本号；三种敏感性处理定义；是否把 censored 值计入缺失率；单位/assay 未确认前 unit_status=unknown 且阈值结论不用于正式排除",
     "parse_lab_value 源码 SHA-256 与版本号；全形态单元测试集及运行日志；逐变量解析前后对照表（行数与唯一值数）；截断比例审计表与三种敏感性结果表；三脚本改造前后解析差异统计",
     "把 <0.01 当成 0.01；把截断当缺失直接进 MICE；单位未确认时做跨库阈值比较；未经单测即替换三脚本解析逻辑",
     "parse_lab_value.py + test_parse_lab_value.py + lab_parse_audit.csv + truncation_audit.csv",
     "C03-1 C03-2 C03-3 C03-4 C03-5", "完整"),
    ("S04", "ICU 时间轴与 index episode", "阶段2",
     "定 T0、index ICU episode、再入 ICU 关系与每条证据的时间可见性",
     "入/出 ICU、转科、护理记录、SOAP、报告、医嘱",
     "① 直接事件时间（入/出 ICU）优先，护理/SOAP 次之；② 处理转科方向（呼吸与危重症医学科 != ICU）；③ 处理复制日期与时间可见性；④ 生成 episode 候选与冲突裁决记录",
     "T0 来源优先级；转科方向判定规则；后见信息识别规则；时间粒度（分钟/小时）",
     "encounter_icu_time_audit.csv；icu_event_evidence.csv；icu_episode_candidates.csv；冲突裁决记录",
     "把再入 ICU 资料拼入首段；用 T12 后信息判定 T0；把空白模板计为证据",
     "icu_episode_candidates.csv + t0_evidence.csv",
     "C04-1 C04-2", "骨架"),
    ("S05", "DHF 表型判定（语义规则）", "阶段3 / G2 闸门",
     "按冻结词典输出 A/B/C 域证据与五状态断言，形成 patient-level 表型分级",
     "[T0-24h,T12) 文书/心超/影像/BNP/管理证据；DHF_SEMANTIC_RULE_DICTIONARY_V1.md；DHF_OPERATIONAL_PHENOTYPE_v20260914.md",
     "① 按词典识别 affirmed/negated/uncertain/hypothetical/historical；② 应用排除清单（作废、病危/病重通知、麻醉前访视单、空白模板）；③ 逐例输出 A/B/C 域与替代解释；④ 分级 confirmed_/probable_/not_supported/unknown",
     "词典文件版本与 SHA-256；A/B/C 域定义；四层分级规则；替代解释清单；证据时间窗",
     "逐例证据原文行号；词典命中记录；11 项回归测试扩展至全词典后的日志；raw agreement 与 Cohen's kappa（须独立标注者）",
     "单用 CXR / 单用 BNP / 单用利尿剂 / 最终 ICD 确诊 DHF；用同一规则重复运行冒充验证；把「不能排除心衰」当阴性",
     "time_gated_evidence.csv + dhf_phenotype_pre_review.csv",
     "C05-1 C05-2 C05-3", "骨架"),
    ("S06", "表型抽样验证与 kappa", "G2 闸门",
     "由独立第二标注者盲法复核分层随机样本，量化表型可靠性",
     "S05 输出；待标注队列；既有 45/300 例审核结果",
     "① 预设分层随机抽样框（60-100 例）；② 第二位标注者独立盲法标注；③ 计算 raw agreement + Cohen's kappa + 95% CI；④ 分歧按预设规则裁决并记录",
     "抽样框与抽样方法；样本量；盲法流程；分歧裁决规则；kappa 目标值",
     "phenotype_validation.csv；抽样框文件；两位标注者原始记录；裁决记录",
     "用同一标注者的重复标注充当独立 kappa；事后调整抽样以改善一致率；把 AI 预审核当独立临床参照",
     "phenotype_validation.csv + kappa_report.md",
     "C06-1 C06-2 C06-3", "骨架"),
    ("S07", "landmark 风险集与资格", "阶段4",
     "确定 T12 时仍在 index ICU 且存活、且不存在 pre-T12 overt shock proxy 的风险集",
     "S04 时间轴；S05 表型；T12 前支持治疗与乳酸",
     "① 排除 T12 前死亡或离开 index ICU 者；② 应用 pre-12h overt shock 代理排除（血管活性药 + 乳酸 max >=2，见 061C/061D）；③ 记录观察完整性与既有严重状态；④ 输出在险集",
     "T12 判定口径；overt shock 代理定义；既有支持状态识别规则；观察完整性判据",
     "在险集 ID 列表；逐例排除理由；与 SQL 规则的对照说明",
     "把 IABP/ECMO 单独当排除标志；把旧文「pre-T0」泛称当实际代码窗口；把已离开/已死亡者留在风险集",
     "landmark12_riskset.csv + exclusion_reasons.csv",
     "C07-1 C07-2", "骨架"),
    ("S08", "三态结局构建", "阶段5 / G3 闸门",
     "构建互斥且有序的三态结局（目标事件 / 竞争事件 / 行政删失）与患者级事件时间",
     "S07 在险集；T12 后支持/护理/文书时间序列；死亡时间；ICU 转出时间",
     "① 判定 T12 后相对 pre-T12 基线的支持升级或 NEE 持续升高（连续 >=30 min）；② 把 ICU 内死亡定位到 index ICU 段；③ 定义 alive ICU discharge 为竞争事件、T60 仍在 ICU 未事件为行政删失；④ 各组成分开记录，未知不当无事件",
     "支持升级与持续性判定规则；NEE 换算规则（不得从总剂量推导泵速）；死亡归段规则；删失时间定义",
     "outcomes_frozen.csv；患者级首次事件时间；组成分解表；三态互斥校验输出",
     "从医嘱总剂量推导泵速或 NEE；把未知当无事件；把 mixed-physiology 主结局称为纯 CS；用 final ICD 反推事件",
     "outcomes_frozen.csv + event_components.csv",
     "C08-1 C08-2", "骨架"),
    ("S09", "医嘱代理验证", "G3 闸门 / 决定3",
     "验证「有效医嘱」作为治疗暴露代理的效度与偏差方向",
     "S08 结局构件；医嘱区间；护理记录与 SOAP 中实际给药",
     "① 抽 30-50 例逐例比对医嘱区间与实际给药；② 报一致率与偏差方向；③ 对 T12±2 h 边界附近支持用药人工复核；④ 报告医嘱时间粒度",
     "抽样与比对规程；一致性定义；边界复核范围；粒度报告格式",
     "proxy_validation.csv；逐例比对记录；边界复核清单；两库首次升级时间分布",
     "在无代理验证证据时把医嘱直接当真实暴露；只报一致率不报偏差方向；忽略 T12 边界的方向性高估",
     "proxy_validation.csv + boundary_review.csv",
     "C09-1 C09-2 C09-3", "骨架"),
    ("S10", "无泄漏特征重建", "阶段6",
     "重建仅使用 [T0,T12) 可得信息的特征集，并机械核验不存在后见变量",
     "S01 数据字典；FEATURE_FREEZE_V33.md 黑白名单；冻结 MIMIC 队列",
     "① 按字典生成候选特征；② 机械扫描 T12 后字段与结局派生列；③ 核验黑名单列全部不在设计矩阵；④ 重估有效参数数与每折事件数",
     "特征清单与列顺序；时间窗定义；聚合口径；黑名单；复杂度上限",
     "设计矩阵列名清单；黑名单核验输出；特征-源字段映射；列顺序文件",
     "按单因素 P 值或外部性能筛选变量；纳入结局派生列、资格变量或支持治疗聚合列",
     "final_feature_manifest.csv + leakage_scan.log",
     "C10-1 C10-2", "骨架"),
    ("S11", "缺失处理与训练折内预处理", "SAP §4.5-§6",
     "在训练折内完成插补、缺失指示、标准化与编码，输出可复用的预处理管线",
     "S10 设计矩阵；S03 解析结果",
     "① 逐变量缺失率与模式审计；② 决定删除/合并为域特征/保留缺失指示（不得看性能后定）；③ 训练折内拟合插补与标准化参数；④ 保存每折转换参数",
     "缺失机制假设；插补方法与完成数据集数；缺失指示定义；标准化方法；异常值规则",
     "每折预处理参数字典；缺失率审计表；插补模型对象；逐折应用日志",
     "全数据预处理后再交叉验证；因改变插补与拆分的先后顺序而使验证集参与拟合",
     "preprocess_params/ + missingness_audit.csv",
     "C11-1 C11-2", "骨架"),
    ("S12", "主模型 Fine-Gray 嵌套验证", "阶段8-9 / SAP §5",
     "在锁定的表型、候选变量与三态结局上，用严格嵌套验证得到无偏的 48 h 目标事件 CIF 及其区分度、校准与净获益的 OOF 估计；本步不选模型、不调变量，只估计",
     "表A 冻结行；S10 无泄漏设计矩阵（列顺序已锁定）；S11 训练折内预处理管线；S08 三态结局",
     "① 外层 5 折，按 event/competing/censor + sepsis 分层，折索引一次生成后落盘不变；② 每训练折内独立完成 插补 -> 缺失指示 -> 中心化/标准化 -> 变量选择 -> 内层 10 折 CV 选 lambda -> 拟合，测试折只生成 OOF 风险；③ 主估计量 = 48 h 目标事件 CIF，报 subdistribution HR + 95% CI、CIF 曲线、个体风险排序；④ 报 competing-risk 适用 AUC（CIF 口径）、IPCW Brier、校准截距/斜率、校准图、风险富集、DCA 净获益，每项注明估计口径；⑤ bootstrap 或重复外层折估计不确定性与选择稳定性；⑥ 全数据按已锁定规则拟合最终模型，仅用于系数与部署文件",
     "外层折数与分层变量；折索引文件 SHA-256；内层折数；lambda 选择规则（min 或 1se，事前择一）；惩罚类型与 alpha（预设 elastic net alpha=0.5）；变量顺序；参照组；CIF 口径与 IPCW 权重构造；bootstrap 次数；随机种子",
     "患者级外层折映射表；每折预处理参数（插补矩阵、标准化中心/尺度、缺失指示定义）；每折 lambda 序列与最终 lambda；设计矩阵列名；模型对象；逐患者 OOF 风险；最终模型系数与协方差；sessionInfo() 与包版本；每折 event/competing/censor 计数",
     "任何折外插补或折外调参；用普通 Logistic AUC 冒充 CIF AUC；看到测试折表现后改 lambda 规则；用 apparent performance 作为报告性能；训练集 SHAP 排名后回头删变量",
     "final_validation/internal/：oof_risk.csv、fold_map.csv、preprocess_params/、perf_table.csv、calibration_plot.png、dca_plot.csv、final_model/coef.csv",
     "C12-1 C12-2 C12-3 C12-4 C12-5", "完整"),
    ("S13", "person-period 结构补充", "阶段8 / SAP §4.2",
     "以 1 h 离散时间多状态结构检验 Fine-Gray 时间聚合结论的稳健性",
     "S12 锁定的在险集、结局与特征",
     "① 将风险窗口拆为 1 h 区间；② 拟合离散时间多项 hazard；③ 与 Fine-Gray 的方向与风险排序对照；④ 展示风险随时间变化",
     "区间长度；区间起点对齐规则；状态转移定义；与主模型一致的折与特征集",
     "person-period 数据集构造脚本；逐区间事件计数；与主模型的对照表",
     "把它当作第二个可自由调参的主模型；用其性能高低替代主模型结论",
     "person_period_dataset.csv + structure_agreement.csv",
     "C13-1", "骨架"),
    ("S14", "表型/删失/缺失敏感性 + 院内外部验证", "阶段10-11",
     "在锁模后按预设分支完成敏感性与本院原样外部预测",
     "锁定模型对象；锁定预处理参数；本院最终队列与同口径结局",
     "① 执行预设敏感性分支（表型层级、BNP-only、最近24h、PE/替代诊断、缺失/删失、持续时长、事件组成）；② 本院按锁定特征顺序/预处理参数/系数原样预测；③ 报告校准漂移与 case-mix 差异；④ 再校准单独报告",
     "敏感性分支清单；外部验证字段映射；再校准方法；报告重心（校准优先于判别）；结论表述边界",
     "sensitivity_matrix.csv；外部逐患者预测；字段映射表；选择链与心超完成/可用/异常支持率",
     "按院内结果改变量/阈值/系数；把代理结局冒充等价验证；事后新增敏感性分支挑显著",
     "sensitivity_matrix.csv + external_predictions.csv",
     "C14-1 C14-2 C14-3", "骨架"),
    ("S15", "报告与 AI 使用披露", "阶段13-14",
     "按 TRIPOD+AI 逐项定位输出，完成 PROBAST+AI 偏倚审计与 AI 使用披露",
     "全部 run 工件；表D 登记；QC 日志",
     "① TRIPOD+AI 27 项逐条定位到稿件位置；② PROBAST+AI 开发/评价逐问作答并留理由与证据锚点；③ 完成 AI 使用披露（model / prompt 版本 / 时间戳 / 原始输出 / 引用行号）；④ 统一版本、数据可用性、引用核验",
     "报告清单版本；审计作答规则；AI 披露字段；全文数值来源 run_id",
     "报告清单定位表；偏倚审计表；AI 判读留痕表；图表与数值的 run 追溯",
     "用自评替代独立审查；把低风险判断当作临床效用证明；引用越界；外传患者明细",
     "submission/reporting_checklists/ + ai_review_audit 表",
     "C15-1 C15-2 C15-3", "骨架"),
]
wsB, wrapB = build_sheet(wb, "表B_步骤协议",
                         "表B 步骤协议（协议层）— 每步 9 字段，逐行 = 逐步骤",
                         "粒度约定：本项目为「1 个分析步骤 = 1 个步骤级协议」，不是「1 篇论文 = 1 个 prompt」。S03/S12 为完整样例，其余为可直接补全的骨架。",
                         B_HEAD, B_W, [4, 5, 6, 7, 8, 9, 10], "70AD47")
write_rows(wsB, B_ROWS, wrapB, center_cols=(1, 12))

dvB = DataValidation(type="list", formula1='"完整,骨架,待展开"', allow_blank=True)
wsB.add_data_validation(dvB)
dvB.add(f"L{DATA_ROW}:L{DATA_ROW + len(B_ROWS) - 1}")
for txt, bg, fg in (("完整", XL_GREEN_BG, XL_GREEN_FG), ("骨架", XL_YEL_BG, XL_YEL_FG),
                    ("待展开", XL_RED_BG, XL_RED_FG)):
    wsB.conditional_formatting.add(f"L{DATA_ROW}:L{DATA_ROW + len(B_ROWS) - 1}",
        CellIsRule(operator="equal", formula=[f'"{txt}"'],
                   fill=PatternFill("solid", start_color=bg, end_color=bg),
                   font=Font(color=fg, size=10)))
wsB.auto_filter.ref = f"A{HEAD_ROW}:L{DATA_ROW + len(B_ROWS) - 1}"

# ============================== 表C 验收标准 ==============================
C_HEAD = ["验收ID", "绑定步骤", "验收项", "口径 / 公式", "达标条件（预设，不得事后放宽）",
          "证据载体（文件/列/图）", "封存状态", "填写时间", "实测值", "偏差解释"]
C_W = [10, 9, 20, 36, 42, 28, 11, 13, 22, 32]
C_ROWS = [
    ("C01-1", "S01", "数据字典覆盖率", "候选变量中被登记 来源表.字段 / 单位 / 取值时间 的比例", "100%，无空字段", "data_dictionary_v1.csv", "未封存", None, None, None),
    ("C01-2", "S01", "单位状态已确认", "unit_status 取值分布", "每项为 confirmed，或明确 not_exported 并记录处理方式", "unit_status_report.csv", "未封存", None, None, None),
    ("C01-3", "S01", "生理范围阈值已定义", "每个连续变量的 lower / upper 与越界处置规则", "全部定义；越界规则可机械执行", "data_dictionary_v1.csv", "未封存", None, None, None),
    ("C02-1", "S02", "唯一键", "主队列内 subject_id / hadm_id / stay_id 唯一且非空", "重复数 = 0，空值数 = 0", "uniqueness_check.log", "未封存", None, None, None),
    ("C02-2", "S02", "成人边界已报告", "年龄阈值与排除计数", "阈值与逐条排除计数均可追溯", "cohort_denominator.csv", "未封存", None, None, None),
    ("C03-1", "S03", "解析覆盖率", "非数值形态中被成功分类的比例", "100%，无 unparsed 残留", "lab_parse_audit.csv", "未封存", None, None, None),
    ("C03-2", "S03", "三脚本一致性", "同一行数据在三脚本下的「有效值」计数差异", "差异 = 0", "解析差异报告", "未封存", None, None, None),
    ("C03-3", "S03", "截断比例已报告", "按性别 x 变量的截断比例与形态分布", "全部变量已报告；形态分类齐全", "truncation_audit.csv", "未封存", None, None, None),
    ("C03-4", "S03", "敏感性方向一致", "log1p 代理 / 分箱 / 排除 三种处理的效应方向", "三者方向一致；不一致时不给正式阈值结论", "截断值敏感性表", "未封存", None, None, None),
    ("C03-5", "S03", "单元测试通过", "全形态用例（>x / <x / 区间 / 空 / 溶血 / 未测 / 中文单位）", "100% 通过", "test_parse_lab_value.py 日志", "未封存", None, None, None),
    ("C04-1", "S04", "T0 可追溯", "每位患者 T0 的来源唯一且可追溯；再入 ICU 不混窗", "100% 有唯一 T0 与来源标注", "t0_evidence.csv", "未封存", None, None, None),
    ("C04-2", "S04", "时间可见性", "每条证据时间戳来源已标注；后见信息未参与资格判定", "机械扫描：后见信息参与判定次数 = 0", "encounter_icu_time_audit.csv", "未封存", None, None, None),
    ("C05-1", "S05", "语义回归测试", "扩展至全词典的用例通过率", "100% 通过（含否定不跨小句、复合否定、不能排除->uncertain）", "测试日志", "未封存", None, None, None),
    ("C05-2", "S05", "规则已外置", "判定逻辑是否引用外部冻结词典文件", "代码内无内联词表；词典文件带版本号与 SHA-256", "phenotype_rulebook_v1.yaml", "未封存", None, None, None),
    ("C05-3", "S05", "五状态断言完整", "affirmed / negated / uncertain / hypothetical / historical 覆盖情况", "五态均有测试用例；「不能排除」判为 uncertain 非阴性", "测试日志", "未封存", None, None, None),
    ("C06-1", "S06", "独立 kappa", "raw agreement + Cohen's kappa + 95% CI", "已报告，且明确标注为独立第二标注者", "phenotype_validation.csv", "未封存", None, None, None),
    ("C06-2", "S06", "抽样设计已写明", "抽样方法（优先抽样 / 分层随机）与抽样框", "明确为分层随机并附抽样框与权重；不外推总体比例", "抽样框文件", "未封存", None, None, None),
    ("C06-3", "S06", "分歧裁决规则已预设", "分歧裁决规则是否在标注前写定", "规则预先写入协议并带时间戳", "协议文件", "未封存", None, None, None),
    ("C07-1", "S07", "在险集正确", "T12 前死亡/离开者已排除；overt shock 代理与代码一致", "排除数可追溯；代理定义与 061C/061D 一致（血管活性药 + 乳酸 max >=2）", "landmark12_riskset.csv", "未封存", None, None, None),
    ("C07-2", "S07", "排除理由齐全", "逐例排除理由可追溯", "100% 有理由；无「其他/未知」笼统分类", "exclusion_reasons.csv", "未封存", None, None, None),
    ("C08-1", "S08", "三态互斥有序", "每 stay 是否恰属一态", "重叠数 = 0；未知不记为无事件", "outcomes_frozen.csv 校验输出", "未封存", None, None, None),
    ("C08-2", "S08", "事件时间可追溯", "患者级首次事件时间与主标签一一对应", "mismatch = 0", "event_components.csv", "未封存", None, None, None),
    ("C09-1", "S09", "医嘱代理一致性", "30-50 例逐例一致率 + 偏差方向", "已报告一致率，且偏差方向明确（非仅报一致率）", "proxy_validation.csv", "未封存", None, None, None),
    ("C09-2", "S09", "T12 边界复核", "T12±2 h 边界附近支持用药的人工复核结果", "已复核并量化方向性偏差", "boundary_review.csv", "未封存", None, None, None),
    ("C09-3", "S09", "时间粒度已报告", "医嘱时间粒度及其与「连续 >=30 min」判定的可实现性", "两者已对照说明", "proxy_validation.csv", "未封存", None, None, None),
    ("C10-1", "S10", "无结局后信息", "label / event_time / death / follow-up 列与 T12 后字段进入设计矩阵的次数", "0 次（机械扫描输出）", "leakage_scan.log", "未封存", None, None, None),
    ("C10-2", "S10", "黑名单核验", "FEATURE_FREEZE_V33 黑名单列在设计矩阵中的出现情况", "出现次数 = 0", "leakage_scan.log", "未封存", None, None, None),
    ("C11-1", "S11", "折内预处理", "插补/标准化/编码参数是否逐折保存且折间不共享", "逐折参数齐全；跨折共享次数 = 0", "preprocess_params/", "未封存", None, None, None),
    ("C11-2", "S11", "缺失机制已报告", "逐变量缺失率与模式；截断值的归属", "缺失率与模式已输出；截断值不计为缺失", "missingness_audit.csv", "未封存", None, None, None),
    ("C12-1", "S12", "无折外泄漏", "折外插补 / 调参 / 变量选择的次数", "0 次（审计脚本输出）", "审计脚本输出", "未封存", None, None, None),
    ("C12-2", "S12", "指标口径匹配", "每个性能数字是否标注估计口径", "100% 标注；未混列 Logistic AUC 与 CIF AUC", "perf_table.csv", "未封存", None, None, None),
    ("C12-3", "S12", "每折事件数", "每折 event / competing / censor 计数与最小值", "已报告最小值与各折分布", "fold_map.csv", "未封存", None, None, None),
    ("C12-4", "S12", "校准", "校准截距 / 斜率 + 校准图", "两者均报告", "calibration_plot.png", "未封存", None, None, None),
    ("C12-5", "S12", "不确定性", "bootstrap 或重复外层折给出的区间", "主性能指标均带 95% CI", "perf_table.csv", "未封存", None, None, None),
    ("C13-1", "S13", "结构稳健性", "person-period 与 Fine-Gray 的方向与风险排序一致性", "方向与排序一致；不一致时已给出解释", "structure_agreement.csv", "未封存", None, None, None),
    ("C14-1", "S14", "敏感性预设", "所有敏感性分支的定义时间", "全部在锁模前定义；事后新增数 = 0", "sensitivity_matrix.csv", "未封存", None, None, None),
    ("C14-2", "S14", "外部验证锁模", "外部预测是否使用锁定的特征顺序 / 预处理参数 / 系数", "未按院内结果改动；改动次数 = 0", "external_predictions.csv", "未封存", None, None, None),
    ("C14-3", "S14", "选择链完整", "全院成人 ICU -> 心超选择分母 -> 多域 DHF 各级人数与排除原因", "全链完整报告，含心超完成率/可用率/异常支持率", "选择链流程图", "未封存", None, None, None),
    ("C15-1", "S15", "TRIPOD+AI 定位", "27 项逐条定位到稿件位置", "100% 定位；未覆盖项如实标注", "reporting_checklists/", "未封存", None, None, None),
    ("C15-2", "S15", "AI 使用披露", "model / prompt 版本 / 时间戳 / 原始输出 / 引用行号", "五要素齐全；AI 与临床参照分离已声明", "ai_review_audit 表", "未封存", None, None, None),
    ("C15-3", "S15", "数值同一 run", "全文数值的来源 run_id", "全部出自同一 run_id 且可追溯至表D", "表D 登记", "未封存", None, None, None),
]
wsC, wrapC = build_sheet(wb, "表C_验收标准",
                         "表C 验收标准（答案侧）— 达标条件必须先于结果填写并封存",
                         "统一执行规则第 7 条：达标条件须在看见最终性能前填写并记录时间戳；解封后不得放宽条件，只允许如实报告偏差并解释。",
                         C_HEAD, C_W, [3, 4, 5, 6, 9, 10], "ED7D31")
LAST_C = write_rows(wsC, C_ROWS, wrapC, center_cols=(1, 2, 7, 8))

dvC = DataValidation(type="list", formula1='"未封存,已封存,已解封"', allow_blank=True)
wsC.add_data_validation(dvC)
dvC.add(f"G{DATA_ROW}:G{LAST_C}")
for txt, bg, fg in (("未封存", XL_RED_BG, XL_RED_FG), ("已封存", XL_GREEN_BG, XL_GREEN_FG),
                    ("已解封", XL_YEL_BG, XL_YEL_FG)):
    wsC.conditional_formatting.add(f"G{DATA_ROW}:G{LAST_C}",
        CellIsRule(operator="equal", formula=[f'"{txt}"'],
                   fill=PatternFill("solid", start_color=bg, end_color=bg),
                   font=Font(color=fg, size=10)))
wsC.auto_filter.ref = f"A{HEAD_ROW}:J{LAST_C}"
for r in range(DATA_ROW, LAST_C + 1):
    for col in ("H", "I"):
        wsC[f"{col}{r}"].number_format = "@"

# ============================== 表D 冻结配置登记 ==============================
D_HEAD = ["run_id", "步骤ID", "脚本路径", "脚本 SHA-256", "数据版本（schema / snapshot）", "随机种子",
          "折索引文件", "折索引 SHA-256", "关键参数（JSON）", "包与版本（sessionInfo）",
          "输出工件", "工件 SHA-256", "开始时间", "结束时间", "操作者", "与前一 run 的差异及解释"]
D_W = [16, 8, 34, 42, 24, 11, 26, 42, 38, 32, 34, 42, 17, 17, 10, 36]
D_ROWS = [
    ("RUN-0000-SAMPLE", "S12", "analysis_r/090_finegray_baseline_v33.R",
     "（示例）<sha256>", "study_ahf_v3 @ <snapshot 时间>", 20260916,
     "folds/outer5_seed20260916.csv", "（示例）<sha256>",
     '{"outer_folds":5,"inner_folds":10,"lambda_rule":"1se","alpha":0.5,"bootstrap":500}',
     "R 4.6.1; survival 3.x; cmprsk 2.x; riskRegression 2.x; glmnet 4.x",
     "final_validation/internal/oof_risk.csv", "（示例）<sha256>",
     "2026-09-16 20:15", "2026-09-16 20:41", "zheyu",
     "示例行（格式示范）。首次真实登记前请删除或替换。"),
]
wsD, wrapD = build_sheet(wb, "表D_冻结配置登记",
                         "表D 冻结配置登记 — 把「必须冻结」从指令变成可追溯数据",
                         "追加式台账：每次运行逐步追加一行，永不覆盖。这是对标 Excel 的缺口补齐件——该表自身也没有种子/超参/包版本的取值列。",
                         D_HEAD, D_W, [3, 5, 7, 9, 10, 11, 16], "7030A0")
LAST_D = write_rows(wsD, D_ROWS, wrapD, center_cols=(2, 6, 13, 14, 15))
wsD.auto_filter.ref = f"A{HEAD_ROW}:P{LAST_D}"
for r in range(DATA_ROW, LAST_D + 1):
    wsD[f"F{r}"].number_format = "0"

# ============================== 说明与进度 ==============================
wsX = wb.create_sheet("说明与进度")
wsX.merge_cells("A1:F1")
wsX["A1"] = "CS_AHF 分析可复现脚手架 V1 — 使用说明与进度"
wsX["A1"].font = TITLE_FONT
wsX.row_dimensions[1].height = 24
wsX.merge_cells("A2:F2")
wsX["A2"] = "配套文档：project_control/ANALYSIS_REPRODUCIBILITY_SCAFFOLD_V1.md。本工作簿不含任何未冻结的数值。"
wsX["A2"].font = NOTE_FONT
wsX["A2"].fill = PatternFill("solid", start_color=XL_NOTE_BG, end_color=XL_NOTE_BG)
wsX["A2"].alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
wsX.row_dimensions[2].height = 30

wsX["A4"] = "四张表的分工"
wsX["A4"].font = Font(bold=True, color=XL_TITLE, size=12)
X_HEAD = ["表", "作用", "填写者", "什么时候填", "关键约束"]
X_ROWS = [
    ("表A 研究合同", "所有步骤协议的唯一上游；把研究方案字段化", "研究者（与导师确认）",
     "已有，随方案修订更新", "步骤协议引用本表须写「行号 + 冻结版本」，不写自由文本"),
    ("表B 步骤协议", "把「主要动作」散文展开成可执行的步骤级协议", "研究者 + AI 协同",
     "执行该步之前完成展开", "每步 9 字段；「必须冻结」「复现约束」两栏不得留空"),
    ("表C 验收标准", "验收侧；把定性「通过条件」落成可核对条件", "研究者",
     "看见结果之前先封存达标条件", "解封后不得放宽条件，只允许如实报告偏差"),
    ("表D 冻结配置登记", "把「必须冻结」变成可追溯数据；补 Excel 自身缺口", "每次运行的操作者",
     "每次运行后立即追加，永不覆盖", "一行 = 一次运行的一个步骤；SHA-256 与种子必填"),
]
for i, h in enumerate(X_HEAD, start=1):
    cell = wsX.cell(row=5, column=i, value=h)
    cell.font = HEAD_FONT
    cell.fill = PatternFill("solid", start_color=XL_HEAD_BG, end_color=XL_HEAD_BG)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BOX
for r, row in enumerate(X_ROWS, start=6):
    for i, val in enumerate(row, start=1):
        cell = wsX.cell(row=r, column=i, value=val)
        cell.font = CELL_FONT
        cell.border = BOX
        cell.alignment = WRAP_TOP
for col, w in zip("ABCDE", [16, 34, 20, 24, 44]):
    wsX.column_dimensions[col].width = w

wsX["A12"] = "进度基线（建表时快照，2026-09-16）"
wsX["A12"].font = Font(bold=True, color=XL_TITLE, size=12)
Y_HEAD = ["指标", "建表基线", "范围 / 更新方式"]
for i, h in enumerate(Y_HEAD, start=1):
    cell = wsX.cell(row=13, column=i, value=h)
    cell.font = HEAD_FONT
    cell.fill = PatternFill("solid", start_color=XL_EMPH_BG, end_color=XL_EMPH_BG)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = BOX

_n_frozen_A = sum(1 for r in A_ROWS if r[3] == "已冻结")
_n_gate_A = sum(1 for r in A_ROWS if r[3] == "待闸门")
_n_full_B = sum(1 for r in B_ROWS if r[11] == "完整")
Y_ROWS = [
    ("合同字段总数", len(A_ROWS), "表A 已登记字段"),
    ("合同已冻结项", _n_frozen_A, "表A 状态 = 已冻结"),
    ("合同待闸门项", _n_gate_A, "表A 状态 = 待闸门（受 G1 / G2 / G3 阻塞）"),
    ("步骤协议总数", len(B_ROWS), "表B 步骤数"),
    ("步骤协议已完整展开", _n_full_B, "表B 展开程度 = 完整（S03 / S12）"),
    ("验收项总数", len(C_ROWS), "表C 验收项数"),
    ("验收已封存", 0, "表C 封存状态 = 已封存（须先于结果填写）"),
    ("验收已解封", 0, "表C 封存状态 = 已解封"),
    ("冻结登记条数", len(D_ROWS), "表D 登记行数（当前 1 行为示例，首次真实登记前删除）"),
]
for r, (name, baseline, scope) in enumerate(Y_ROWS, start=14):
    wsX.cell(row=r, column=1, value=name).font = CELL_FONT
    wsX.cell(row=r, column=2, value=baseline).font = CELL_FONT
    wsX.cell(row=r, column=3, value=scope).font = CELL_FONT
    wsX.cell(row=r, column=2).alignment = CENTER
    for i in range(1, 4):
        wsX.cell(row=r, column=i).border = BOX
        if i != 2:
            wsX.cell(row=r, column=i).alignment = WRAP_TOP
for col, w in zip("ABCD", [24, 12, 46, 4]):
    wsX.column_dimensions[col].width = w
wsX.merge_cells("A25:C25")
wsX["A25"] = "如需自动计数：可在 D 列加入 COUNTIF / COUNTA 公式（如 =COUNTIF('表C_验收标准'!G4:G44,\"已封存\")）；本工作簿刻意不含公式，以避免在任何预览器中显示空值或错误值。"
wsX["A25"].font = NOTE_FONT
wsX["A25"].alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
wsX.row_dimensions[25].height = 30
wsX.sheet_properties.tabColor = xl_color("#AFABAB")

wb.properties.title = "CS_AHF 分析可复现脚手架 V1"
OUT = "/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/CS_AHF_分析可复现脚手架_V1.xlsx"
wb.save(OUT)
print("saved:", OUT)
print("sheets:", wb.sheetnames)
