# CS_AHF 周二研究进展周报

周报日期：2026-09-15
覆盖周期：2026-09-09 至 2026-09-15
下次组会：2026-09-16

## 一句话结论

本周完成MIMIC主窗口7,828/7,828放射科报告的完整导出核验，以及院内8,385名成人候选的全量时间门控和复核工作清单；研究已从“数据可用性确认”进入“双库DHF临床复核与终点重建”，尚不能报告最终DHF人数、事件数或模型性能。

## 本周完成

| 完成项 | 证据路径 | 是否可写入论文最终结果 |
|---|---|---|
| MIMIC主窗口完整报告导出及行数/键/stay对账 | `project_control/bigquery/dhf_radiology_raw_landmark12_v1_complete.csv`；`project_control/bigquery/landmark12_audit_20260904/` | 完整性QC可写；表型比例待冻结 |
| 新主窗口300条临床标注包和60条独立盲法包 | `project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/README.md` | 标注流程可写；标签尚待临床确认 |
| 院内全量episode/T0/T12门控、原文复核及互斥工作状态 | `project_control/internal_validation/20260915_source_review/` | 数据处理QC可写；表型和风险集待冻结 |
| 22例时间疑点、7例语义疑点和隔离文书审计 | `focused_time_review_22.csv`、`focused_semantic_review_7.csv`、`document_quarantine.csv` | 审计过程可写；不构成全量临床验证 |
| DHF操作性表型、论文14阶段合同和方法初稿 | `DHF_OPERATIONAL_PHENOTYPE_v20260914.md`、`PAPER_WORKFLOW_20260915.md`、`PROPOSAL_METHODS_DRAFT_20260915.md` | 方法合同可写；最终数字待冻结 |

## 当前阶段

- 阶段：阶段3-5，队列、时间清洗与表型预审。
- 本周状态：主窗口报告库和院内原始多域工作台已可审计；尚未完成临床金标准、同口径终点或正式验证。
- 下一阶段入口条件：冻结双库DHF operational phenotype和T12风险集，重建event/competing/censor后按最终事件数限制低维模型。

## 关键数字及证据路径

| 指标 | 数值 | 证据路径与解释 |
|---|---:|---|
| MIMIC主窗口完整放射科报告 | 7,828/7,828 | `dhf_radiology_raw_landmark12_v1_complete.csv`；通过行数、键唯一性和stay-level对账 |
| 有主窗口报告的MIMIC stay | 3,886 | `controlled_annotation_20260904_landmark12_complete_v2/README.md`；数据可用性，不是DHF人数 |
| 新主窗口临床复核样本 | round 1 300；round 2 60 | 同一README；round 1和独立round 2均待临床人工最终确认 |
| 院内成人index ICU候选分母 | 8,385（女2,842，男5,543） | `internal_validation/20260915_source_review/qc.json`；不是最终DHF人数或全院成人ICU分母 |
| 院内时间门控证据/目标医嘱 | 284,049 / 20,025 | 同一QC；时间窗和键一致性通过，文书创建/报告时间仍为可用时间代理 |
| 院内优先复核工作量 | 285语义/风险集；102 T12；40 HF锚点；2,115阴性抽样 | `worklist_qc.json`；互斥工作队列，不是最终排除流图 |
| 院内规则支持候选 | 892（891 probable + 1旧技术标签） | `qc.json`；非临床确认DHF，旧技术名`confirmed_dhf`不代表确认 |
| MIMIC现有候选证据层 | 5,549候选；肺充血筛查层675 | `bigquery/review_linkage_20260915/evidence_layer_counts.csv`；675不是DHF |

旧`2,424/334`、旧`outputs/`、`outputs_v2/`及旧模型性能仅为历史探索。旧pre-T0 300条审核仅作历史/规则语义验证，不能代替新主窗口标注包；需继续清理可能误导的旧文档。

## 阻塞问题与预计投入

| 问题 | 为什么卡住 | 下一动作 | 主动工时 | 计算/等待 | 风险 |
|---|---|---|---:|---:|---|
| 新主窗口300条标注未临床确认 | 当前为分层抽样和Codex草案，不是临床金标准 | 完成round 1；需要正式一致性时，第二位标注者独立完成60条 | 5-10 h临床复核；60条1-2 h | 临床排期 | 高 |
| 双库DHF表型未冻结 | 单项影像、BNP、心超流程或规则标签都不足以确诊DHF | 逐例整合HF anchor、失代偿、管理和替代解释 | 12-20 h | 低 | 高 |
| 院内T12风险集/终点未闭环 | ICU时间、报告时间和医嘱存在代理边界；缺执行级升级轨迹 | 重建event、alive ICU discharge和观察完整性；eMAR到位后做敏感性 | 6-12 h | 数据补提数天至数周 | 高 |
| MIMIC Echo strict draft仅6例 | 不能以极小严格层硬性限定开发队列 | 冻结多域主表型；院内保留echo-supported严格验证层 | 6-12 h | 低 | 高 |
| 最终模型未重跑 | 事件数和最终可用预测器尚未锁定 | 低维参数冻结后运行嵌套MICE m=20、Fine-Gray、person-period和敏感性 | 8-16 h | 数小时至过夜 | 中 |

## 下周计划

1. 推进新主窗口300条临床标注，并决定是否启动独立60条双盲复核和kappa。
2. 处理院内285例优先队列、102例T12观察链、40例HF锚点，并抽样核查规则阴性病例。
3. 冻结MIMIC和院内共同的A/B/C多域DHF operational phenotype，输出可审计`cohort_freeze.csv`。
4. 重建T12后治疗升级、ICU内死亡、alive ICU discharge和行政随访状态；医嘱区间仅作为预设代理敏感性。
5. 按最终事件数重估低维参数上限，运行嵌套MICE m=20、Fine-Gray主模型、1 h person-period补充模型及预设敏感性分析。

## 需要导师决策

1. 是否要求第二位临床标注者对新主窗口60条进行独立盲法复核，以形成正式kappa。
2. 是否确认MIMIC多域DHF operational phenotype为开发队列主定义，并明确Echo strict draft 6例不作硬门槛；院内echo-supported层作为严格外部验证层。
3. 若执行级eMAR无法及时取得，是否接受医嘱区间代理的限制性实施方案，并在执行级数据可得后预设敏感性复核。

## 周三组会3-5分钟中文口头稿

老师好，本周主要完成两件事。第一，MIMIC主窗口的放射科报告已经从GCS完整导出，7,828条报告通过行数、键唯一性和stay-level对账，确认不是以前网页下载缺270条的下界数据。基于这个完整窗口，我们重新生成了300条临床复核包和60条独立盲法复核包。这里需要强调：旧pre-T0的300条只保留作历史规则语义验证，新包才对应现在的`[T0-24小时,T12)`主窗口；目前新包仍等待临床人工确认，因此不能报告最终影像PPV、DHF人数或任何最终模型性能。

第二，院内数据已经完成8,385名成人候选的全量时间门控和复核工作台。当前有284,049条可追溯证据和20,025条目标医嘱，285例进入优先语义和风险集复核，另有102例需要补T12观察链、40例需核HF锚点。规则支持的892例只是候选，绝不能写成临床确认DHF。院内外部验证仍有终点问题：当前医嘱可以构建暴露区间，但不是逐次执行级eMAR，因此治疗升级的主定义需要和可用时间、竞争出ICU一起重建。

方法上，主estimand不变：T12后到T60或活着离开index ICU前的治疗升级型ICU血流动力学恶化，Fine-Gray为主模型，alive ICU discharge是竞争事件，1小时person-period是补充。MIMIC Echo严格层目前只有6例，不能硬性要求开发队列都满足；应先冻结多域DHF表型，院内保留echo-supported严格验证层。

这周需要老师帮助决定三点：新300条是否安排第二位临床标注者独立复核60条以获得正式kappa；是否确认多域DHF作为MIMIC开发主定义；以及若eMAR暂不可得，是否先按医嘱区间代理实施并预设执行级数据到位后的敏感性分析。

## 更新动作

- [x] 已同步`project_control/RESEARCH_DASHBOARD.md`
- [x] 已追加当天自动化任务报告
- [x] 已将旧队列、旧模型和旧pre-T0标注明确降级为历史/初步材料
