# Raw 媒体整理处理流程

任务类型：`TASK_TYPE_RAW_FILE_ORGANIZER`（`domain/constants.py`）。

## 编排入口

- **`RawFileOrganizer`**：从 `TaskConfig` 解析 **`RawFileOrganizeConfig`**，组装 **`RawAnalyzeConfig`**（扩展名来自 `domain/organizer_defaults.py`），委托 **`RawFilePipeline.run()`**。
- **`RawFilePipeline`**：只遍历 **`inbox_dir`（即 `scan_root`）第一层**条目，按三阶段编排；阶段化计数写入返回的 **`FileTaskRunStatistics`**（与 `FileResultRepository.get_statistics` 合并），本期**不写目录明细表**。

配置与路径不变量见 [`application/config_common.py`](../src/j_file_kit/app/file_task/application/config_common.py) 中的 **`RAW_MEDIA_ROOT`**（`/media/raw_workspace`）、[`application/raw_task_config.py`](../src/j_file_kit/app/file_task/application/raw_task_config.py) 的 **`RawFileOrganizeConfig`** 各字段（与业务目录名一致的 `folders_*` / `files_*`）。

## 三阶段（当前行为）

1. **阶段 1**：将 inbox **第一层文件**移动到 **`files_misc`**（`RawAnalyzeConfig.files_misc`）。移动前做文件名规范化（含 UTF-8 字节上限与 `-jfk-xxxx` 冲突后缀预留），冲突消解与 **`executor.execute_decision`** / **`move_file_with_conflict_resolution`** 一致；每条结果写入 **`file_results`**（与 JAV 管道相同端口）。
2. **阶段 2**：对 inbox **第一层目录**逐项处理。**2.1** 若目录名命中 `organizer_defaults.DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS`
   任一子串（NFKC + 大小写无关），整目录迁入 **`folders_to_delete`**；目录 basename 冲突与文件一致，
   使用 **`file_ops.move_directory_with_conflict_resolution`**（`-jfk-xxxx`）。
   **2.2** 未命中关键字则自底向上清洗：扩展名落入 **`DEFAULT_MISC_FILE_DELETE_EXTENSIONS`**、或 **stem**
   含 **`DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS`**、或体积为 **0** 的文件删除；并删除因此产生的空子目录，
   至多删空当前的「第一层目录」本身（不触碰 `inbox` 上一级）。**dry_run** 下不改动磁盘，
   但阶段化计数仍会按预览累加。**2.3** 从第一层起点向下，将连续「仅单子目录且无文件」的链折叠为单层目录名
   （各层目录名以 `_` 合并；合并名 UTF-8 总长 **≤255 字节**，超长时对长度 **≥10 字符** 的段按比例截断，短段不截断；
   预算仍不足则跳过该目录折叠且不中断 run）。链末端内容迁入 staging 目录后，**先**将 staging 整块迁至合并名（冲突时用 **`-jfk-xxxx`**），**成功后再**删除旧链目录；失败或取消时不对非空 staging 做静默删除，非空则尽量改名为 **`raw-chain-quarantine-run{run_id}-*`** 便于人工核对。
   **2.4** 若在折叠后目录仍存在，仅占位打点并记日志「待分类」（策略非本期）。
3. **阶段 3（占位）**：统计 **`files_misc` 下第一层文件**数（分流至各 `files_*` **非本期**）。

取消：`cancellation_event` 置位后，在阶段 **1（每个第一层文件之间）**
与阶段 **2（每个第一层目录开始前、2.2 目录内扫描迭代中、2.3 折叠迁移子项时）**检测并提前结束（后续阶段不执行）。

## 统计字段（run 级）

除聚合字段 `total_items` / `success_*` 等外，`FileTaskRunStatistics` 含 **`phase1_*` / `phase2_*` / `phase3_*`**，语义见领域模型注释。

总体架构见 [ARCHITECTURE.md](./ARCHITECTURE.md)。若与代码冲突，**以源码为准**。
