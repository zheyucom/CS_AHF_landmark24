# MIMIC 文本数据下载与安装

更新时间：2026-08-28

## 建议先下载什么

当前 AHF 表型验证优先使用 **MIMIC-IV-Note 2.2**，暂时不需要下载完整 MIMIC-CXR 影像。研究只需要住院关联的放射科报告文本，因此先准备以下四个文件：

```text
discharge.csv.gz
radiology.csv.gz
discharge_detail.csv.gz
radiology_detail.csv.gz
```

官方入口：

- [MIMIC-IV-Note 2.2（PhysioNet）](https://physionet.org/content/mimic-iv-note/2.2/)
- [MIMIC-CXR 2.1.0（PhysioNet，可选）](https://physionet.org/content/mimic-cxr/2.1.0/)

下载需要完成 PhysioNet credentialed access、相应数据使用协议和机构要求。请只通过自己的 PhysioNet 账号下载，不要把账号、密码或数据文件发到对话中。

## 浏览器下载步骤

1. 打开 MIMIC-IV-Note 2.2 页面并登录 PhysioNet。
2. 确认页面版本是 `2.2`，进入 `Files` 或数据文件列表。
3. 下载 `note/` 目录中的上述四个 `.csv.gz` 文件，放在同一个本地目录，例如：

```text
/Users/zheyu/Downloads/mimic-iv-note-2.2/note/
```

4. 下载完成后，在终端检查文件是否齐全：

```sh
ls -lh /Users/zheyu/Downloads/mimic-iv-note-2.2/note/*.csv.gz
```

不建议现在下载 MIMIC-CXR 的完整 DICOM/JPEG 影像。它们会显著增加存储和处理成本，而当前研究首先需要的是 radiology report 文本；只有当报告文本验证结果提示需要影像级复核时，再单独规划 CXR。

## 本机加载步骤

先确认 PostgreSQL 可以无交互连接。项目已有 `.pgpass` 时通常不需要输入密码：

```sh
/Library/PostgreSQL/12/bin/psql -X -w -h localhost -U postgres -d mimiciv31 -Atc \
  "select current_database(), current_user"
```

若失败，请先在本机配置 `~/.pgpass`，格式类似：

```text
localhost:5432:mimiciv31:postgres:你的本机数据库密码
```

并设置权限：

```sh
chmod 600 ~/.pgpass
```

然后执行项目安装脚本：

```sh
cd /Users/zheyu/Desktop/CS_AHF_landmark24
scripts/prepare_mimic_note.sh \
  /Users/zheyu/Downloads/mimic-iv-note-2.2/note
```

脚本会检查四个文件、数据库连接和磁盘空间，随后调用本地官方 `create.sql`、`load_gz.sql`、`validate.sql`，最后运行 Note/CXR 源可用性审计。若数据库中已经存在 `mimiciv_note`，脚本默认停止，不会覆盖旧 schema。

## 加载后执行的表型验证

先运行源审计：

```sh
/Library/PostgreSQL/12/bin/psql -X -w -v ON_ERROR_STOP=1 \
  -h localhost -U postgres -d mimiciv31 \
  -f sql_v3_2/audits/100_audit_note_source_availability.sql
```

再运行 pre-T0 放射科证据抽取：

```sh
/Library/PostgreSQL/12/bin/psql -X -w -v ON_ERROR_STOP=1 \
  -h localhost -U postgres -d mimiciv31 \
  -f sql_v3_2/audits/101_create_pre_t0_radiology_ahf_evidence.sql
```

时间边界固定为：

```text
admittime <= radiology.charttime < ICU intime
```

该 SQL 只用于 AHF 表型验证，不改变 `650/66` 队列、结局或预测器。规则标签必须抽样人工复核，不能直接当作影像金标准。

## 预计资源

- 下载：取决于 PhysioNet 网络和权限，不在项目内自动执行。
- PostgreSQL 导入：预计数小时，取决于磁盘、CPU 和数据库配置。
- 额外磁盘：至少预留约 15 GB；导入前以本机 `df -h` 为准。
- 研究前置：Note 文本即可开始影像支持验证；MIMIC-CXR 原始影像、肺超声和完整实时 physician note 不是当前硬性前置条件。

