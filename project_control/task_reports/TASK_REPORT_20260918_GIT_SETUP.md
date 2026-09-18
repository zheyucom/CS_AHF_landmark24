# 任务报告：本机 Git 初始化与安全边界配置

日期：2026-09-18

## 1. 用户问题与本轮范围

用户询问是否需要下载 `.git`，以及能否由 DHF 在本机项目中完成下载和配置。

## 2. 已验证事实

- `.git` 不是单独下载的软件或文件；已有远程仓库时应使用 `git clone`，现有未建仓目录应使用 `git init`。
- 本机已安装 Apple Git 2.50.1，无需安装 Git。
- 本机正式项目 `/Users/zheyu/Desktop/CS_AHF_landmark24` 原先不是 Git 仓库，也没有根目录 `.gitignore`。
- 项目约含 7.3GB `project_control/` 数据，其中最大单文件约 6.2GB；另有患者级证据表、虚拟环境、模型产物和 BigQuery 导出，不能直接纳入版本库。
- 本机未配置全局 Git `user.name`、`user.email`、凭证助手或 Git 托管命令行工具；当前也没有已确认的远程仓库地址。

## 3. 已执行配置

- 在本机项目根目录执行 `git init -b main`；
- 配置仓库级：`core.autocrlf=input`、`core.filemode=false`、`fetch.prune=true`、`pull.ff=only`；
- 建立根目录 `.gitignore`，排除原始/患者级数据、运行产物、模型文件、虚拟环境、缓存、日志、密钥、BigQuery 导出、Office/PDF 二进制文件和本地插件；
- 保留研究 Markdown、代码、SQL、配置、模板、变量字典及任务报告用于版本控制；
- 验证 6.2GB 证据表、BigQuery CSV、`.venv` 和 Obsidian 插件二进制均被忽略。

应用忽略规则后，待纳入版本控制的文件约 672 个、总计约 5.9MB；最大候选文件小于 0.5MB，未将大体量原始数据加入 Git。

## 4. 尚未完成

- 未创建初始提交：提交者姓名和邮箱尚未确认；
- 未配置 `origin`：远程仓库 URL 尚未提供；
- 未推送：本机尚无可用远程地址和认证配置。

## 5. 下一步

用户提供或选择 GitHub/GitLab/Gitee/其他 Git 服务的空仓库 URL，并确认提交者姓名和邮箱后，完成仓库级身份、初始提交、远程绑定、首次推送及本地/远程 SHA 核对。

