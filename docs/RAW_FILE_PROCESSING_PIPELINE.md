# Raw 媒体整理管线

任务：`TASK_TYPE_RAW_FILE_ORGANIZER`。入口 **`RawFileOrganizer`** → **`RawFilePipeline.run()`**（[`pipeline.py`](../src/j_file_kit/app/file_task/application/raw_pipeline/pipeline.py)）。仅处理 **`scan_root`（inbox）第一层**：散落文件、第一层子目录；**不递归 inbox 下的多级散落文件**（阶段 1）。计数写入 **`FileTaskRunStatistics`**；与代码冲突时**以源码为准**。

---

## 总览

```mermaid
flowchart LR
  subgraph p1 [阶段1]
    F[第一层文件] --> M[files_misc]
  end
  subgraph p2 [阶段2 每层目录]
    D[inbox 子目录] --> A[2.1 关键字整目录]
    A -->|否| B[2.2 递归清洗]
    B --> C[2.3 单链折叠]
    C --> E[2.4 拆解或整目录归档]
  end
  subgraph p3 [阶段3]
    M2[files_misc 第一层] --> J[3.0 junk→files_to_delete]
    J --> R[3.x 按扩展名分流]
  end
  p1 --> p2
  p2 --> p3
```

---

## 共享口径（各阶段一致）

| 项 | 说明 |
|----|------|
| **junk 关键字** | [`organizer_defaults.DEFAULT_RAW_JUNK_KEYWORDS`](../src/j_file_kit/app/file_task/domain/organizer_defaults.py)；目录名 / stem 均经同一套规范化（NFKC、大小写无关等，见 `raw_pipeline/keywords`）。 |
| **移动命名** | **`normalize_move_basename`** + **`move_file_with_conflict_resolution`**（`-jfk-xxxx`）；目录整块迁移用 **`move_directory_with_conflict_resolution`**。 |
| **dry_run** | 不写盘；计数与日志仍按「将要发生的动作」累加（细粒度见各阶段源码）。 |
| **取消** | `cancellation_event` 置位后：阶段 1 逐文件、阶段 2 目录边界与 2.2 扫描迭代等处退出（[`pipeline.py`](../src/j_file_kit/app/file_task/application/raw_pipeline/pipeline.py)）。 |

---

## 产品常量（Raw 相关摘录）

| 符号 | 用途 |
|------|------|
| `DEFAULT_RAW_JUNK_KEYWORDS` | 2.1 目录 basename；2.2 / 3.0 文件 stem 子串匹配。 |
| `DEFAULT_MISC_FILE_DELETE_EXTENSIONS` | 2.2 命中即删（**无体积上限**）。 |
| `DEFAULT_RAW_PHASE22_JUNK_DELETE_MAX_BYTES` | **仅 2.2**：stem 命中 junk 时还须 **`st_size` 严格小于**该值（默认 **100MiB**）。 |
| 媒体扩展名集合 | `DEFAULT_*_EXTENSIONS` → 注入 **`RawAnalyzeConfig`**，供 2.4 / 3 分流判定。 |

---

## 阶段简表

| 阶段 | 范围 | 动作摘要 | 必填配置（触发时） |
|------|------|----------|----------------------|
| **1** | inbox 下一层**文件** | 迁入 `files_misc`，写 `file_results` | 有待移文件时 `files_misc` |
| **2.1** | 各第一层**目录** basename | 含 junk 关键字则**整目录**→ `folders_to_delete` | 有待迁目录时 `folders_to_delete` |
| **2.2** | 未迁走的目录**整棵子树** | 删垃圾文件、自下而上删空目录；规则见下节 | — |
| **2.3** | 仍存在的第一层目录 | 多层单链折叠为一层目录名（超长合并名有截断策略） | — |
| **2.4** | 仍存在的第一层目录 | 小目录拆解→`files_misc`；否则按树内类型 **整目录**→ `folders_*` | 有待分类目录时 `files_misc` + 各 `folders_pic` / `audio` / `compressed` / `video` / `misc`（[`phase2_preflight.py`](../src/j_file_kit/app/file_task/application/raw_pipeline/phase2_preflight.py)） |
| **3.0** | `files_misc` **下一层文件** | stem 含 junk → **`files_to_delete`**（无体积条件） | 有待迁出 junk 文件时 `files_to_delete` |
| **3.x** | 同上剩余队列 | zip/jpg/mp3…→ `files_compressed` / `files_pic` / `files_audio`；**视频扩展名暂留** `files_misc`；其余未知扩展名留驻 | 有待分流类型时对应 `files_*` |

**编排**：[`phase2.py`](../src/j_file_kit/app/file_task/application/raw_pipeline/phase2.py)（`phase2_delete_move` / `clean` / `collapse` / `classify`）。

---

## 2.2 删除规则（递归目录内文件）

命中 **任一** 则删除：`misc` 扩展名 **或** stem 含 junk 且 **体积 < `DEFAULT_RAW_PHASE22_JUNK_DELETE_MAX_BYTES`** **或** 0 字节文件。then 删产生的空目录（第一层目录删空则 `rmdir`）。

**对照 3.0**：2.2 在「第一层子目录以内」递归；3.0 只在 **`files_misc` 单层**，junk 命中即迁入 `files_to_delete`，**无** 100MiB 门槛。

---

## 2.4 拆分一句话

- **小目录**（仅文件、无子目录、≤5 个文件、类型为单一媒体类或「单一类+图片」）：文件进 **`files_misc`**（命名规则见源码）。
- **否则**：按整棵树扩展名画像迁到某一 **`folders_*`**；unknown 扩展名等混合类型 → **`folders_misc`**。

---

## 阶段 3 计数（近似）

- **`phase3_deleted_junk_misc`**：3.0 迁入 `files_to_delete`（含 dry_run）。
- **`phase3_seen_files_misc`**：3.0 之后参与分流的文件数。
- **`phase3_deferred_files_misc`**：未成功分流（视频占位、未知扩展、失败）。

近似：`3.0 前 misc 第一层文件数 ≈ phase3_seen_files_misc + phase3_deleted_junk_misc`。

完整字段语义：**[`domain/task_run.py`](../src/j_file_kit/app/file_task/domain/task_run.py)**。架构总览：**[ARCHITECTURE.md](./ARCHITECTURE.md)**。
