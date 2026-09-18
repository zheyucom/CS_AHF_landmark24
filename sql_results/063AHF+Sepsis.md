| 结局                                        | n / N      | 事件率 |
| ------------------------------------------- | ---------- | ------ |
| current mixed shock proxy                   | 233 / 6301 | 3.70%  |
| new support initiation                      | 331 / 6301 | 5.25%  |
| agent count increase                        | 447 / 6301 | 7.09%  |
| hemodynamic deterioration broad             | 536 / 6301 | 8.51%  |
| hemodynamic deterioration lactate-confirmed | 176 / 6301 | 2.79%  |
| mixed shock proxy or death                  | 328 / 6301 | 5.21%  |

如果做 **总体 ICU AHF 人群**，最合理的主结局候选是：

```
hemodynamic deterioration broad
536 / 6301 = 8.51%
```

这比原 strict mixed shock proxy 的 3.70% 更可做。

| 结局                                        | n / N      | 事件率 |
| ------------------------------------------- | ---------- | ------ |
| current mixed shock proxy                   | 133 / 2424 | 5.49%  |
| new support initiation                      | 163 / 2424 | 6.72%  |
| agent count increase                        | 240 / 2424 | 9.90%  |
| hemodynamic deterioration broad             | 282 / 2424 | 11.63% |
| hemodynamic deterioration lactate-confirmed | 98 / 2424  | 4.04%  |
| mixed shock proxy or death                  | 178 / 2424 | 7.34%  |

如果把主队列定为 **AHF + early sepsis12**，主结局用：

```
hemodynamic deterioration broad
```

那么事件率是：

```
282 / 2424 = 11.63%
```

而是写：

> **Early prediction of hemodynamic deterioration among ICU patients with acute heart failure and early sepsis: an interpretable machine learning study based on MIMIC-IV**

中文：

> **急性心力衰竭合并早期脓毒症 ICU 患者未来 48 h 血流动力学恶化风险预测模型研究：基于 MIMIC-IV 的可解释机器学习研究**

主分析：

```
人群：AHF + early sepsis12
landmark：ICU 入科 12 h
预测变量：0–12 h
结局窗口：12–60 h
主结局：hemodynamic deterioration broad
```

目前主结局事件率：

```
11.63%
```

严格 mixed shock proxy 保留为关键次要结局：

```
current mixed shock proxy：5.49%
mixed shock proxy or death：7.34%
```



——————加入NEE

| 结局                             | n / N      | 事件率 |
| -------------------------------- | ---------- | ------ |
| 原 hd broad                      | 536 / 6301 | 8.51%  |
| 加 NEE ≥0.05 后 hd broad         | 605 / 6301 | 9.60%  |
| 加 NEE ≥0.10 后 hd broad         | 580 / 6301 | 9.20%  |
| NEE conservative escalation 本身 | 132 / 6301 | 2.09%  |

| 结局                             | n / N      | 事件率     |
| -------------------------------- | ---------- | ---------- |
| 原 hd broad                      | 282 / 2424 | 11.63%     |
| 加 NEE ≥0.05 后 hd broad         | 334 / 2424 | **13.78%** |
| 加 NEE ≥0.10 后 hd broad         | 315 / 2424 | 13.00%     |
| NEE conservative escalation 本身 | 102 / 2424 | 4.21%      |

| 结局                     | n / N      | 事件率 |
| ------------------------ | ---------- | ------ |
| 原 hd broad              | 254 / 3877 | 6.55%  |
| 加 NEE ≥0.05 后 hd broad | 271 / 3877 | 6.99%  |

overall AHF12:
pre12 NEE 有记录：929 / 6301 = 14.74%
post12 NEE 有记录：934 / 6301 = 14.82%
pre12 NEE max median ≈ 0.100
post12 NEE max median ≈ 0.120

| 组成                                     | n    | 比例   |
| ---------------------------------------- | ---- | ------ |
| 无事件                                   | 2090 | 86.22% |
| 支持新启用/种类增加，无 NEE 升级，无死亡 | 181  | 7.47%  |
| 仅 NEE 升级                              | 52   | 2.15%  |
| 支持升级 + NEE 升级                      | 44   | 1.82%  |
| 仅死亡                                   | 42   | 1.73%  |
| 支持升级 + 死亡                          | 9    | 0.37%  |
| 支持升级 + NEE 升级 + 死亡               | 6    | 0.25%  |

——

我建议主结局正式定义为：

## Primary outcome

```
12–60 h hemodynamic deterioration
```

在 ICU 入科 12 h landmark 后未来 48 h 内出现以下任一：

```
1. 新启用 vasoactive / inotrope support；
2. vasoactive / inotrope 药物种类增加；
3. norepinephrine-equivalent dose 较 0–12 h 最大值增加 ≥0.05 μg/kg/min；
4. 12–60 h 内死亡。
```

对应 SQL flag：

```
hd_deterioration_broad_nee005_flag
```

事件率：

```
AHF + early sepsis12: 334 / 2424 = 13.78%
```

| 敏感性结局               | flag                                         | 事件率 |
| ------------------------ | -------------------------------------------- | ------ |
| 更严格 NEE 阈值          | `hd_deterioration_broad_nee010_flag`         | 13.00% |
| 不含 NEE                 | `hd_deterioration_broad_flag`                | 11.63% |
| strict mixed shock proxy | `current_mixed_shock_proxy_flag`             | 5.49%  |
| lactate-confirmed HD     | `hd_deterioration_lac_confirmed_nee005_flag` | 4.33%  |

### 064

| 项目                               | 结果               |
| ---------------------------------- | ------------------ |
| 主分析人数                         | 2424               |
| subject / hadm / stay              | 2424 / 2424 / 2424 |
| 主结局事件数                       | 334                |
| 主结局事件率                       | 13.78%             |
| NEE ≥0.10 敏感性结局               | 315，13.00%        |
| 不含 NEE 的 HD deterioration       | 282，11.63%        |
| strict mixed shock proxy           | 133，5.49%         |
| lactate-confirmed HD deterioration | 105，4.33%         |
| 12–60 h 死亡                       | 57，2.35%          |

| 组成                       | n    | pct    |
| -------------------------- | ---- | ------ |
| 无事件                     | 2090 | 86.22% |
| 支持新启用 / 药物种类增加  | 181  | 7.47%  |
| 仅 NEE 升级                | 52   | 2.15%  |
| 支持升级 + NEE 升级        | 44   | 1.82%  |
| 仅死亡                     | 42   | 1.73%  |
| 支持升级 + 死亡            | 9    | 0.37%  |
| 支持升级 + NEE 升级 + 死亡 | 6    | 0.25%  |

| complete60        | n    | 主事件率 | 支持升级率 | NEE 升级率 | 死亡率 |
| ----------------- | ---- | -------- | ---------- | ---------- | ------ |
| 未完整观察到 60 h | 1023 | 6.06%    | 1.96%      | 0.78%      | 5.08%  |
| 完整观察到 60 h   | 1401 | 19.41%   | 15.70%     | 6.71%      | 0.36%  |

这说明 **ICU 60 h 前转出/观察中断仍然存在选择性**。但这不是当前流程的错误。主分析仍保留全部 2424 例；后续需要做：

```
1. complete60 子集敏感性分析；
2. 12–36 h / 36–60 h person-period 分析；
3. 或在论文中报告观察时间差异和删失情况。
```

现阶段不建议为了提高完整随访比例而只分析 complete60，因为那会引入选择偏倚

