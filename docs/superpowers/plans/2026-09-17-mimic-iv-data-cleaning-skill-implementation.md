# MIMIC-IV 数据清洗 Skill 实施计划

日期：2026-09-17

## 目标

创建并安装 `mimic-iv-data-cleaning`，让 Codex 在 MIMIC-IV 实验室提取、清洗、特征构建或 SQL 审查时，主动检查精确 itemid、标本/类别/单位、结果可用时间、重复、删失值、缺失值补零和 raw/derived 覆盖，不接触或内置患者级数据。

## 实施顺序

1. 使用 Skill Creator 官方 `init_skill.py` 初始化目录和 `agents/openai.yaml`。
2. 先编写 `scripts/test_fixtures.py`，覆盖规则包验证、BUN 标本污染、乳酸双向对账、T12 后 storetime、比较符号、未知单位、重复 specimen 与缺失补零。
3. 运行测试并确认因功能缺失而失败。
4. 实现 `validate_rule_pack.py` 和 `audit_mimic_sql.py`，仅做到测试要求的最小行为。
5. 建立实验室规则包、规则 schema、工作流和来源记录；临床规则仅在有来源、回归测试及人工批准记录后激活。
6. 补齐精简的 `SKILL.md`，明确失败边界、引用文件读取条件和四项审计输出。
7. 运行合成测试、危险/合规 SQL CLI 测试、规则验证、语法编译和 Skill Creator `quick_validate.py`。
8. 用不携带预期答案的原始任务做前向测试，确认能够主动指出错误标本与结果可用时间风险。
9. 将通过验证的目录复制到本机 `~/.codex/skills/mimic-iv-data-cleaning`，再从本机运行同一套验证并确认 Codex 可发现目录。
10. 将可分享副本和验证报告保存到项目 `deliverables/mimic-iv-data-cleaning/`，不包含患者级数据、密钥或本机绝对路径。

## 验收命令

```bash
python3 scripts/test_fixtures.py
python3 scripts/validate_rule_pack.py references/mimic-iv-lab-rules.json
python3 -m py_compile scripts/*.py
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" .
```

危险 SQL 必须产生硬失败，合规 SQL 必须没有硬失败；数据库不可用时只能输出 `not_run`，不得声称完成患者级审计。
