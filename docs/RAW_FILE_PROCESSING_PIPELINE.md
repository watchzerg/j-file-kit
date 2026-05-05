# Raw 媒体整理处理流程

任务类型：`TASK_TYPE_RAW_FILE_ORGANIZER`（`domain/constants.py`）。

## 编排入口与代码位置

- **`RawFileOrganizer`**：从 `TaskConfig` 解析 **`RawFileOrganizeConfig`**，组装 **`RawAnalyzeConfig`**（扩展名来自 `domain/organizer_defaults.py`），委托 **`RawFilePipeline.run()`**。
- **`RawFilePipeline`**：只处理 **`inbox_dir`（即 `scan_root`）第一层**条目；编排见 [`application/raw_pipeline/pipeline.py`](../src/j_file_kit/app/file_task/application/raw_pipeline/pipeline.py)（`phase1` → `phase2` → `phase3`）。
- 阶段化计数写入 **`FileTaskRunStatistics`**（与 `FileResultRepository.get_statistics` 合并），本期**不写目录明细表**。

配置与路径不变量：[`application/config_common.py`](../src/j_file_kit/app/file_task/application/config_common.py)（**`RAW_MEDIA_ROOT`**）、[`application/raw_task_config.py`](../src/j_file_kit/app/file_task/application/raw_task_config.py)（**`RawFileOrganizeConfig`**）。

---

## 业务逻辑速览（扩展新规则时先看本节）

下列颗粒度与「计划文档」相近：判断**改 phase 几**、**前置条件**、**落盘路径**、**冲突/超长**口径。

### 阶段 1：第一层散落文件 → `files_misc`

**代码**：[`application/raw_pipeline/phase1.py`](../src/j_file_kit/app/file_task/application/raw_pipeline/phase1.py)（`run_phase1`）

- **范围**：仅 **`scan_root` 下一层普通文件**（不递归子目录）。
- **动作**：移入 **`files_misc`**；每条写入 **`file_results`**（与 JAV 管道同一端口）。
- **命名**：`normalize_move_basename`（UTF-8 字节上限 + 为 `-jfk-xxxx` 预留）；落地用 **`executor.execute_decision`**（与 **`move_file_with_conflict_resolution`** 语义一致）。
- **配置**：若存在第一层文件且 **`files_misc`** 未配置 → 报错。
- **dry_run**：不落盘，计数仍按预览累加。

---

### 阶段 2：第一层目录（逐项：2.1 → 2.2 → 2.3 → 2.4）

**代码**：[`application/raw_pipeline/phase2.py`](../src/j_file_kit/app/file_task/application/raw_pipeline/phase2.py)（`run_phase2` → `_phase2_process_one_level1_dir`）

对 inbox **每个第一层子目录**按顺序执行下列子阶段（命中迁出或目录消失则后续子阶段不再对该目录生效）。

#### 2.1：关键字目录 → `folders_to_delete`

- **触发**：目录 basename 命中 **`organizer_defaults.DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS`** 任一子串（NFKC + 大小写无关）。
- **动作**：**整目录**迁入 **`folders_to_delete`**。
- **冲突**：**`file_ops.move_directory_with_conflict_resolution`**（`-jfk-xxxx`）。
- **配置**：若本轮扫描中存在待迁出的关键字目录且 **`folders_to_delete`** 未配置 → 报错。
- **dry_run**：不落盘，计数预览。

#### 2.2：目录内清洗

- **触发**：未命中 2.1 的第一层目录。
- **删除文件**（命中任一即删）：扩展名 ∈ **`DEFAULT_MISC_FILE_DELETE_EXTENSIONS`**；或 stem（规范化匹配）含 **`DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS`**；或 **0 字节**。
- **删空目录**：清洗产生的空子目录自下而上删掉；若第一层目录本身被删空则 **rmdir**（不触碰 `inbox` 上一级）。
- **dry_run**：不删文件、不删目录，计数预览。
- **扩展点**：新「垃圾识别」规则通常加在本子阶段（扩展名 / stem 规则）。

#### 2.3：单链目录折叠（多层单路径 → 单层目录名）

- **触发**：2.2 后目录仍存在；从第一层起点向下，连续满足「**仅有单子目录、当前层无文件**」，直到遇到文件、分叉或停止。
- **动作**：链上各层目录名用 **`_`** 合并为新目录名；合并名 UTF-8 **≤255 字节**；超长时对长度 **≥10 字符**的段按比例截断，**短段不截断**；预算仍不足则 **跳过折叠**（不中断 run）。
- **落地顺序**：链末端内容先入 staging → **`move_directory_with_conflict_resolution`** 整块迁至合并名（冲突 `-jfk-xxxx`）→ **成功后再**删旧链空目录。
- **失败/取消**：非空 staging 不静默删除；尽量改名为 **`raw-chain-quarantine-run{run_id}-*`**。
- **dry_run**：不改盘，折叠成功计数仍预览。
- **扩展点**：合并名算法 / 折叠条件变更 → 本子阶段。

#### 2.4：目录拆分与归档

**输入**：2.2 + 2.3 之后的当前第一层目录路径。

**小目录拆解**分支触发条件（需**同时**满足）：

- **单层级**：目录下**只有文件、无子目录**。
- **类型**：集合为「**单一类型（图片 / 视频 / 音频 / 压缩）**」或「**单一类型 + 图片**」（类型按 **`RawAnalyzeConfig`** 中扩展名集合判定）。
- **数量**：直接子文件数 **≤ 5**。

**小目录拆解后**：

- 各文件移入 **`files_misc`**。
- **`stem == 目录名`**：保持原名；否则 **`{dir}_{stem}{suffix}`**；允许仅靠后缀区分不同文件。
- **命名 / 冲突**：**`normalize_move_basename`** + **`move_file_with_conflict_resolution`**（与阶段 1 超长与 `-jfk-xxxx` 口径一致）。
- 拆解完成后删除空目录。

**未知扩展名**（相对上述四类媒体扩展名集合）：在**拆解判定**中 **一票否决**，走 **整目录迁移**分支。

**整目录迁移**（拆解未命中或其它情况：含子目录、文件数>5、类型组合不满足等）：

- **画像**：按目录树内 **全部文件**（递归）的扩展名归类；字幕走字幕扩展名集合，否则为 **unknown**。
- **规则**：
  - 仅图片 → **`folders_pic`**
  - 仅音频（**可含图片**）→ **`folders_audio`**
  - 仅压缩（**可含图片**）→ **`folders_compressed`**
  - 仅视频（**可含图片**）→ **`folders_video`**
  - **其它混合**（含 unknown、字幕与其它组合等）→ **`folders_misc`**
- **冲突**：**`move_directory_with_conflict_resolution`**（`-jfk-xxxx`）。
- **配置**：若 inbox 存在任一 **非关键字**第一层目录，须同时配置 **`files_misc`** 与各 **`folders_pic` / `folders_audio` / `folders_compressed` / `folders_video` / `folders_misc`**（与是否配置 **`folders_to_delete`** 独立）。
- **dry_run**：不落盘，拆解 / 整目录迁移计数预览。
- **扩展点**：新归宿桶或新拆解条件 → 本子阶段；新媒体类型通常先扩 **`organizer_defaults`** + **`RawAnalyzeConfig`** 注入，再在 2.4 判定中使用。

---

### 阶段 3（占位）：`files_misc` 第一层计数

**代码**：[`application/raw_pipeline/phase3.py`](../src/j_file_kit/app/file_task/application/raw_pipeline/phase3.py)

- 统计 **`files_misc` 下第一层文件数**；分流到各 **`files_*`** **非本期**。

---

## 取消（`cancellation_event`）

置位后在下列间隙检测并结束后续阶段：

- **阶段 1**：每个第一层文件之间。
- **阶段 2**：每个第一层目录开始前；**2.2** 目录扫描迭代中；**2.3** 折叠迁移子项时；**2.4** 拆解时每个文件之间。

---

## 统计字段（run 级）

除聚合字段 `total_items` / `success_*` 等外，`FileTaskRunStatistics` 含 **`phase1_*` / `phase2_*` / `phase3_*`**，语义见领域模型 [`domain/task_run.py`](../src/j_file_kit/app/file_task/domain/task_run.py)。

总体架构见 [ARCHITECTURE.md](./ARCHITECTURE.md)。若与代码冲突，**以源码为准**。
