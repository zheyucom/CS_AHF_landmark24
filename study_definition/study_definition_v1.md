```markdown
# Study Definition v1

## 研究问题

在成人首次 ICU 入科、且入 ICU 早期表现为急性心力衰竭优势临床综合征但尚未发生显性心源性休克的患者中，基于入 ICU 后 0–24 h 可获得的信息，预测 24–72 h 内新发显性心源性休克的风险。

## Index time

ICU intime。

## Landmark time

ICU 入科后 24 h。

所有进入模型的预测变量必须来自 ICU intime 至 ICU intime + 24 h 之间。

## Prediction window

ICU 入科后 24–72 h。

## 主队列

成人患者；
首次 ICU stay；
入 ICU 早期存在 AHF-present-at-ICU-admission 证据；
0–24 h 内未发生 overt cardiogenic shock；
在 24 h landmark 时仍处于可观察风险集中。

## 主结局

24–72 h 内新发 overt cardiogenic shock。

结局定义应尽量对齐 SCAI C/D/E 的结构化 proxy，包括：
1. 低血压或升压/强心药支持；
2. 低灌注证据，例如乳酸升高、少尿、肌酐上升、代谢性酸中毒；
3. 心源性或 AHF-dominant 背景；
4. 排除明显非心源性休克主导情况。

## 主要分析设计

24 h landmark prediction。

主分析使用 24–72 h 风险窗。

可采用 person-period 格式，将 24–72 h 拆分为：
- 24–48 h；
- 48–72 h。

每个患者最多贡献两行。

## complete72 子集

complete72 仅作为敏感性分析，不作为主分析人群。

原因：
complete72 是基于未来是否完整观察到 72 h 的信息构造，可能引入选择偏倚。

## 主要模型

主模型优先使用：
- penalized logistic regression；
- pooled logistic regression；
- bootstrap 或 repeated cross-validation 内部验证。

复杂机器学习模型仅作为 benchmark，不作为首选主模型。

## 数据安全

MIMIC 原始数据、note 文本和任何可能包含敏感信息的派生数据不得上传至非授权环境。
所有分析在本地合规环境完成。

## Feature extraction principle

For variables covered by official MIMIC-IV concepts, the study will preferentially use official MIMIC-code definitions or adapt them to the prespecified study time window.

Official definitions will be used for:
- vital signs;
- Glasgow Coma Scale;
- urine output;
- common laboratory variables;
- selected vasoactive/inotrope medications when available.

For variables not fully covered by official MIMIC-code, study-specific definitions will be created using:
- explicit itemid whitelist;
- fluid/source restriction;
- unit harmonization;
- physiologic range checks;
- clear time-window restriction;
- version-controlled data dictionary.

Label-based fuzzy extraction will not be used as the primary extraction strategy.
官方能覆盖的，用官方；官方不能覆盖的，自己写白名单；不能再用模糊 label 搜索当主方法
```

