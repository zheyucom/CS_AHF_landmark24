# 任务报告：胸部 CT 纳入肺部证据域与影像标注范围修订

日期：2026-09-05 Asia/Shanghai  
阶段：阶段 3，DHF 表型验证与冻结准备

## 本次完成

1. 明确胸部 CT/CTA 纳入 DHF 相关肺部证据域。胸片和胸部 CT 均可记录肺水肿、肺间质改变、肺血管充血、胸腔积液以及 PE、右心负荷、肺炎/ARDS 等并存或替代解释。
2. 将影像人工复核改为“先确认报告范围和 modality，再判断肺充血”：胸部影像允许判读；非胸部报告固定为 `indeterminate`，不进入肺充血 PPV 分母；混合/不清报告保留待人工确认。
3. 更新标注模板、中文快速指南、主窗口标注包 README、草标脚本和合并 QC 脚本，新增 `final_report_scope`、`final_modality`。
4. 合并脚本新增一致性约束：非胸部不能填 `no_congestion`；胸部范围不能配 `non_chest` modality；scope 与 modality 必须成对提供。旧标注包仍可在没有新字段时回写，但输出新字段为空，避免破坏历史结果。
5. 新主窗口 300 条草标已重新生成：300 行、28 列、`review_status=pending_human_review` 全部保留。当前草分类为胸部 211、非胸部 63、混合/不清 14、可能胸部 12；后两类需人工确认后才能成为最终胸部 scope。
6. 新增 `DHF_SUBTYPE_ANALYSIS_PLAN_V1.md`：HFrEF/HFmrEF/HFpEF-compatible 和左/右/双心受累作为预设描述/异质性分析，不立即拆分主模型；亚型缺失不作数值插补。

## 方法边界

- 胸部 CT 可以帮助识别肺水肿与 PE、肺炎、ARDS 等并存或替代诊断，但“做过 CT”不能证明 DHF；CT 未做也不能视为 CT 阴性。
- 胸片与胸部 CT 不要求每位患者同时完成。主肺部证据使用 CXR OR CT；CXR AND CT 仅作敏感性分析，以避免 CT 的临床选择性造成严重选择偏倚。
- 影像证据仍不能单独确诊 DHF。最终 DHF 表型需结合 HF anchor、心超结构/功能证据或经验证的临床失代偿证据，以及治疗/管理强化证据。
- 心超仍是院内严格 `echo-supported DHF` 层的必要心脏证据；胸部 CT 不能替代心超。MIMIC 主开发端仍不能把 Echo 设为硬门槛，因为窗口内可用 Echo 覆盖不足。

## 验证

- 草标重新生成：300 行成功。
- `make_dhf_annotation_draft.py`、`merge_dhf_annotation_review.py` 语法检查通过。
- QC fixture 合并：300 行成功；非胸部 63 条全部为 `indeterminate`；scope/modality 约束通过。
- 临床最终完成表尚未生成，因为 `final_*` 字段仍待人工复核；不能把 Codex 草标当作人工金标准。

## 下一步

1. 临床复核新主窗口 300 条：先填 `final_report_scope` 和 `final_modality`，再填充血、替代解释和 comments。
2. 胸部 CT 报告特别记录 PE/右心负荷、肺炎/ARDS 和肺水肿是否并存；不因并存诊断自动排除 DHF。
3. 如需正式 Cohen's kappa，由第二位临床人员独立盲法复核 60 条；旧的同标注者复制不能用于独立一致性。
4. 完成临床复核后重新计算胸部影像规则 PPV，并分别报告 CXR-only、CT-supported、CXR OR CT、CXR AND CT 和 Echo-supported 层的事件数与检查选择性。
5. 表型冻结后再按事件数决定低维模型、MICE 和 Fine-Gray 重跑；本轮不提前重跑最终模型。
