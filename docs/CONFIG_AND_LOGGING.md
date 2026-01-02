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
| `global_config` | 全局目录配置 | 单行表，存储 inbox_dir, sorted_dir, unsorted_dir 等目录路径 |
| `task_configs` | 任务配置 | name, type, enabled, config(JSON)，支持 WebUI 动态修改 |

**加载流程**：
1. `SQLiteConnectionManager` 创建表结构
2. `AppConfigRepository._ensure_default_config()` 初始化默认配置
3. `load_config_from_db()` 加载到内存 `AppConfig` 对象

---

## 日志架构

### 1. 业务操作日志（SQLite）

用于 WebUI 查询、排序、过滤：

| 表 | 用途 |
|---|---|
| `tasks` | 任务实例记录（task_name, status, start_time, end_time, statistics） |
| `file_items` | 文件处理结果（path, file_type, serial_id, success, error_message, duration_ms） |
| `file_operations` | 文件操作历史（MOVE/DELETE/RENAME 的 source_path, target_path, timestamp） |

### 2. 系统/调试日志（Loguru）

| 类型 | 位置 | 说明 |
|---|---|---|
| 全局日志 | 控制台 | `setup_logging()` 配置标准库桥接，当前未添加文件 handler |
| 任务日志 | `{log_dir}/{task_name}_{task_id}.jsonl` | `configure_task_logger()` 为每个任务创建独立 JSON Lines 文件 |

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

