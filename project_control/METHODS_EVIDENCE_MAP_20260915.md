# 方法与文献对应表

更新：2026-09-15。下列 9 条 DOI 的标题、首位作者、刊物与出版年已通过 Crossref 实时元数据核对；此项不等于阅读全文核验。当前采用中文本地规则和 AI 辅助预审核，没有运行或验证第三方中文临床 NLP 模型，也没有向外部服务发送患者资料。

| 编号 | 文献 | 对应步骤与支持内容 | 不能据此宣称 |
|---|---|---|---|
| R1 | Bozkurt et al. Universal definition and classification of heart failure. *European Journal of Heart Failure*. 2021. [DOI](https://doi.org/10.1002/ejhf.2115) | HF 由症状/体征、心脏结构/功能异常及利钠肽/客观充血证据综合判断 | 本项目的具体 A+B+C 自动规则已获临床验证 |
| R2 | McDonagh et al. 2021 ESC Guidelines for the diagnosis and treatment of acute and chronic heart failure. *European Heart Journal*. 2021. [DOI](https://doi.org/10.1093/eurheartj/ehab368) | 心超、利钠肽及临床检查互补；治疗证据须结合心衰临床场景 | 任何利尿剂或轻度瓣膜反流都能确诊 DHF；该文支持“2026 已全面更名” |
| R3 | Benchimol et al. The RECORD Statement. *PLOS Medicine*. 2015. [DOI](https://doi.org/10.1371/journal.pmed.1001885) | 报告常规医疗数据来源、选人算法、数据链接、清洗及验证，直接支持当前五表和原文证据追溯工作 | 文献规定必须恰好拆成五张表；五表是本项目工程实现 |
| R4 | Chapman et al. A Simple Algorithm for Identifying Negated Findings and Diseases in Discharge Summaries. *Journal of Biomedical Informatics*. 2001. [DOI](https://doi.org/10.1006/jbin.2001.1029) | 借鉴局部否定范围，避免“无肺水肿”命中阳性；本项目另标不确定、既往和风险告知 | 英文 NegEx 的性能可以直接迁移到中文病历；当前正则就是经过验证的 NegEx 实现 |
| R5 | Irvin et al. CheXpert: A Large Chest Radiograph Dataset with Uncertainty Labels and Expert Comparison. *Proceedings of the AAAI Conference on Artificial Intelligence*. 2019. [DOI](https://doi.org/10.1609/aaai.v33i01.3301590) | 借鉴阳性、阴性、不确定的报告标签和专家比较思想 | CheXpert 是 DHF 诊断标准，或其胸片规则已验证中文 CT/心超。旧文档的 Radiology: AI 引用错误 |
| R6 | Fine and Gray. A Proportional Hazards Model for the Subdistribution of a Competing Risk. *JASA*. 1999. [DOI](https://doi.org/10.1080/01621459.1999.10474144) | 对当前定义下的恶化/死亡复合事件累积发生风险建模，活着离开 index ICU 为竞争事件 | 文献本身规定本项目的 T12/T60、NEE 阈值或 30 min 持续时间；这些是预设操作性选择 |
| R7 | Collins et al. TRIPOD+AI statement. *BMJ*. 2024. [DOI](https://doi.org/10.1136/bmj-2023-078378) | 从研究问题、参与者、预测器、结局到开发与外部验证的透明报告；适用于回归及机器学习 | 填好清单就证明模型性能好或具备临床效用 |
| R8 | Moons et al. PROBAST+AI. *BMJ*. 2025. [DOI](https://doi.org/10.1136/bmj-2024-082505) | 审查质量、偏倚与适用性，重点关注选择偏倚、时间泄露和结局测量差异 | 当前无独立人工金标准仍可自评所有域为低风险。旧文档的 2023 年错误 |
| R9 | Riley et al. Calculating the sample size required for developing a clinical prediction model. *BMJ*. 2020;368:m441. [DOI](https://doi.org/10.1136/bmj.m441) | 最终队列和事件数明确后评估候选参数复杂度，不直接套用固定 EPV=10 | 该文提供竞争风险模型的一键专用样本量公式；仍需与当前估计目标适配。旧文档的 2019 年错误 |

## 当前步骤的临床意义

当前问题是“到底谁符合研究入组条件”，因此先重建 ICU 段，再找 T12 前可见的 HF、失代偿和管理证据。譬如 1 月 8 日入 ICU、1 月 9 日出 ICU、1 月 12 日再次入 ICU 的同一次住院，不能把 1 月 12 日的心超或用药拼到首段 ICU 的前 12 小时。这一做法减少错纳、时间泄露和把已转出患者仍算作 ICU 风险集的错误。

当前 8,385 人只是已导出且做过床旁心超的成人候选分母；原始提取已有心超选择条件，不能据此计算全院所有成人 ICU 患者接受心超的比例。院内心超严格层与 MIMIC 多域开发层的差异需报告为可迁移性/适用性边界。

## 预设规则与临床审核

护理明确入监护室记录时间、正文明确入 ICU 时间、出 ICU 文书的入院字段都保留。出现冲突时优先直接事件记录；泛称“入病房”不自动认作入 ICU。SOAP 的计划转出不等于实际转出。后写文书可用于回顾重建事件时间，但不能把其后见信息输入 T12 预测器。

AI 预审核可以完成证据抽取和初步分层，不能冒充独立医师审核。既有 45 例和 300 条预审核继续使用；只有剩余临床不确定项才集中交用户处理。若论文报告 PPV、敏感度或评阅者一致性，须使用独立参照审核和正确抽样设计，不能用同一规则自我复核。

## 本轮动作与依据

| 实际动作 | 临床/方法目的 | 依据及边界 |
|---|---|---|
| 查22例全文，回填8例时间并保留14例代理 | 使病例属于正确ICU段和前12h窗口；上下文推定6例另标 | R3、R7、R8支持可追溯测量；来源优先级来自用户确认与本项目规则，不是指南规定 |
| 增加“无法平卧”和全身水肿、剔除36份空白模板、隔离1份矛盾文书的表型用途 | 减少症状漏检及模板/复制内容误纳 | R1/R2支持临床证据组合；R3/R4支持数据清洗与否定识别；8项回归测试不等同临床验证 |
| 把7例DHF语义和预测资格分别记录 | DHF成立不代表前12h无已存在休克 | R7/R8支持明确参与者与预测时点；乳酸>=2+血管活性药是既有061C项目规则，不是HF指南诊断标准 |
| 用同窗床旁心超、T12状态确定285例优先复核顺序 | 优先处理可能进主队列者，保留阴性抽样防漏 | R3/R8支持选择流程透明；285是工作清单，不是基于文献推导的最终样本量 |
| 将300条MIMIC审核回连7,828份报告和5,549候选 | 审核修正实际进入患者筛查，同时保留未审核标签来源 | R3/R5支持链接与不确定标签；混合AI/规则层不代表独立金标准，也不能估计全体阳性率 |

上述9篇文献的题录核验已完成，但尚未把每个操作细节逐条核到全文页码。开题可据此交代方法来源，投稿前仍需原文精读核准具体引用语句。
