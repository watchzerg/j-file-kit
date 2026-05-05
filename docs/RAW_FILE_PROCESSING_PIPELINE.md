# Raw 媒体整理处理流程（占位说明）

任务类型：`TASK_TYPE_RAW_FILE_ORGANIZER`（`domain/constants.py`）。

## 本期范围

- **`RawFileOrganizer`**：从 `TaskConfig` 解析 **`RawFileOrganizeConfig`**，组装 **`RawAnalyzeConfig`**（扩展名来自 `domain/organizer_defaults.py`），委托 **`RawFilePipeline.run()`**。
- **`RawFilePipeline`**：**不扫描、不分析、不落库**；`run` 直接返回空的 **`FileTaskRunStatistics`**（全零字段）。

配置与路径不变量见 [`application/config.py`](../src/j_file_kit/app/file_task/application/config.py) 中的 **`RAW_MEDIA_ROOT`**（`/media/raw_workspace`）及 **`RawFileOrganizeConfig`** 各字段（与业务目录名一致的 `folders_*` / `files_*`）。

## 后续（非本期）

- 仅遍历 **`inbox` 下第一层**文件与目录；命中后 **整目录移动** 等规则将实现在 **`RawFilePipeline`**（与 JAV 的 **`FilePipeline`** 解耦）。

总体架构见 [ARCHITECTURE.md](./ARCHITECTURE.md)。若与代码冲突，**以源码为准**。
