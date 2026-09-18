# 院内数据源级别提数清单 v1

## 你真正需要做什么

先不要逐个寻找 MIMIC 的衍生变量，也不要在院内平台里手工计算模型字段。你只需要按数据源导出原始表，保留连接键、时间、原始值、单位和记录语义。

## 最小执行步骤

1. 打开 `hospital_source_level_data_request_checklist_v1.xlsx`。
2. 先看 `01_提数总清单`，按 `priority` 从“必须-第一批”开始。
3. 只填写黄色列：
   - `local_database_table_or_view_to_fill`
   - `local_extraction_sql_or_path_to_fill`
   - `completion_status_to_fill`
   - `notes_or_blockers_to_fill`
4. 按 `recommended_output_name` 导出对应 CSV 或数据库视图。
5. 每张关键表先导出 20-50 行脱敏样例，发回做审计。
6. 样例通过后再导出全量。

## 为什么这样做

当前模型变量多数是从原始长表衍生而来。例如 `map_lt65_record_prop` 不需要院内有同名字段，只需要原始 MAP 记录和时间；`nee_0_12h_last` 不需要同名字段，只需要升压药/强心药实际执行记录、剂量、单位、体重和起止时间。

## 后续我会做什么

拿到样例或全量原始表后，我会做：

1. 连接键审计：各表能否连到 ICU stay。
2. 时间窗审计：能否生成 ICU 0-12h 特征和 12-60h 结局。
3. 单位/编码审计：检验、药物、心超字段是否可统一。
4. 缺失率审计：哪些变量可用于当前外部验证。
5. 衍生变量生成：从原始长表生成 MIMIC 对应字段。
6. 外部验证判断：直接验证当前模型，还是先做删减版/重训版。
