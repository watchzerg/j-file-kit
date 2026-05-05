# Raw 媒体整理处理流程

任务类型：`TASK_TYPE_RAW_FILE_ORGANIZER`（`domain/constants.py`）。

## 编排入口

- **`RawFileOrganizer`**：从 `TaskConfig` 解析 **`RawFileOrganizeConfig`**，组装 **`RawAnalyzeConfig`**（扩展名来自 `domain/organizer_defaults.py`），委托 **`RawFilePipeline.run()`**。
- **`RawFilePipeline`**：只遍历 **`inbox_dir`（即 `scan_root`）第一层**条目，按三阶段编排；阶段化计数写入返回的 **`FileTaskRunStatistics`**（与 `FileResultRepository.get_statistics` 合并），本期**不写目录明细表**。

配置与路径不变量见 [`application/config.py`](../src/j_file_kit/app/file_task/application/config.py) 中的 **`RAW_MEDIA_ROOT`**（`/media/raw_workspace`）及 **`RawFileOrganizeConfig`** 各字段（与业务目录名一致的 `folders_*` / `files_*`）。

## 三阶段（当前行为）

1. **阶段 1**：将 inbox **第一层文件**移动到 **`files_misc`**（`RawAnalyzeConfig.files_misc`）。移动前做文件名规范化（含 UTF-8 字节上限与 `-jfk-xxxx` 冲突后缀预留），冲突消解与 **`executor.execute_decision`** / **`move_file_with_conflict_resolution`** 一致；每条结果写入 **`file_results`**（与 JAV 管道相同端口）。
2. **阶段 2（占位）**：仅枚举 inbox **第一层目录**并计数；目录内分析、整目录移动、空目录清理等**非本期**。
3. **阶段 3（占位）**：统计 **`files_misc` 下第一层文件**数（分流至各 `files_*` **非本期**）。

取消：`cancellation_event` 置位后，在阶段 1 条目之间检测并提前结束（后续阶段不执行）。

## 统计字段（run 级）

除聚合字段 `total_items` / `success_*` 等外，`FileTaskRunStatistics` 含 **`phase1_*` / `phase2_*` / `phase3_*`**，语义见领域模型注释。

总体架构见 [ARCHITECTURE.md](./ARCHITECTURE.md)。若与代码冲突，**以源码为准**。
