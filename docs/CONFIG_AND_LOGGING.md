# 配置与日志架构

## 数据目录

应用启动时自动创建数据目录（不存在则创建）：

```
{base_dir}/                    # 默认 .app-data，可通过 J_FILE_KIT_BASE_DIR 环境变量覆盖
├── sqlite/
│   └── j_file_kit.db          # SQLite 数据库（配置 + 业务数据 + 操作日志）
└── logs/
    └── {task_name}_{task_id}.jsonl  # 任务级别日志（JSON Lines 格式）
```

初始化入口：`AppState.__init__()` → 创建目录 + SQLite 连接 + 默认配置

---

## 配置架构

**存储位置**：SQLite 数据库

| 表 | 用途 | 说明 |
|---|---|---|
| `global_config` | 全局目录配置 | 单行表，存储 inbox_dir, sorted_dir, unsorted_dir, archive_dir, misc_dir, starred_dir |
| `task_configs` | 任务配置 | name, type, enabled, config(JSON)，支持 WebUI 动态修改 |

**加载流程**：
1. `SQLiteConnectionManager` 创建表结构
2. `AppConfigRepositoryImpl._ensure_default_config()` 初始化默认配置
3. `load_app_config_from_db()` 加载到内存 `AppConfig` 对象

---

## 日志架构

### 1. 业务操作日志（SQLite）

用于 WebUI 查询、排序、过滤：

| 表 | 用途 |
|---|---|
| `tasks` | 任务实例记录（task_name, task_type, trigger_type, status, start_time, end_time, error_message, statistics） |
| `file_items` | 文件处理结果（path, stem, file_type, serial_id, success, has_errors, has_warnings, was_skipped, error_message, total_duration_ms, processor_count, context_data, processor_results, created_at） |
| `file_operations` | 文件操作历史（operation, source_path, target_path, timestamp, file_item_id, file_type, serial_id） |

`file_operations.operation` 受枚举约束，仅允许 `move` / `delete` / `rename`。

### 2. 系统/调试日志（Loguru）

| 类型 | 位置 | 格式 | 说明 |
|---|---|---|---|
| 全局日志 | stderr（控制台） | 环境感知 | `setup_logging()` 配置，INFO 级别，拦截第三方库日志 |
| 任务日志 | `{log_dir}/{task_name}_{task_id}.jsonl` | JSON Lines | `configure_task_logger()` 为每个任务创建独立文件 |

**环境配置**：

控制台日志格式通过 `J_FILE_KIT_ENV` 环境变量控制：

- `development`（默认）：彩色文本格式，便于人类阅读和调试
  ```
  2024-01-15 10:30:45 | INFO     | pipeline:_start_task:155 - 开始任务: jav_video_organizer
  ```

- `production`：JSON 格式，便于日志收集系统解析
  ```json
  {"text": "开始任务: jav_video_organizer", "record": {"time": {...}, "level": "INFO", ...}}
  ```

**设计原则**：
- 所有业务代码直接使用 `from loguru import logger`
- 第三方库（uvicorn、fastapi 等）通过 `InterceptHandler` 桥接到 loguru
- 控制台输出环境感知：开发易读，生产机器友好
- 任务日志文件与任务生命周期绑定，任务结束后自动移除 handler
- 生产环境关闭 `diagnose`，避免敏感信息泄漏

---

## 关键代码位置

| 功能 | 文件 |
|---|---|
| 数据目录初始化 | `api/app_state.py` |
| SQLite 表结构 | `infrastructure/persistence/sqlite/connection.py` |
| 配置仓储 | `infrastructure/persistence/sqlite/config/config_repository.py` |
| 日志配置 | `shared/utils/logging.py` |
| 文件处理结果 | `infrastructure/persistence/sqlite/task/file_item_repository.py` |
| 文件操作记录 | `infrastructure/persistence/sqlite/task/file_processor_repository.py` |

