# 架构设计文档

## 概述

DDD 风格，按业务领域组织代码。每个模块内部分为 `domain`（领域核心）和 `application`（应用编排）两层。依赖倒置：domain 定义 ports 接口，infrastructure 实现接口。

## 目录结构

```
src/j_file_kit/
├── main.py                       # CLI 入口（uvicorn 启动）
├── api/
│   ├── app.py                    # 路由注册、生命周期、异常处理
│   └── app_state.py              # Composition Root（组装依赖）
├── app/
│   ├── file_task/                # 文件处理任务领域
│   │   ├── api.py                # 任务执行 HTTP 路由
│   │   ├── config_api.py         # 配置管理 HTTP 路由
│   │   ├── domain/
│   │   │   ├── models.py         # 实体、枚举、领域异常、TaskConfig、FileTaskRunner Protocol
│   │   │   ├── decisions.py      # Decision 模型（MoveDecision / DeleteDecision / SkipDecision）
│   │   │   ├── ports.py          # 仓储接口（Protocol）
│   │   │   └── constants.py      # task_type 常量
│   │   └── application/
│   │       ├── schemas.py        # 任务执行 API DTO
│   │       ├── config_schemas.py # 配置管理 API DTO
│   │       ├── config.py         # JavVideoOrganizeConfig、AnalyzeConfig（Pydantic）
│   │       ├── config_validator.py         # 配置验证纯函数
│   │       ├── file_task_config_service.py # 配置读取/合并/验证/保存
│   │       ├── jav_video_organizer.py      # JavVideoOrganizer（FileTaskRunner 实现）
│   │       ├── pipeline.py       # FilePipeline：扫描 → 分析 → 执行
│   │       ├── analyzer.py       # analyze_file，返回 Decision
│   │       ├── executor.py       # execute_decision，执行文件操作
│   │       ├── file_ops.py       # 目录扫描工具函数
│   │       └── jav_filename_util.py  # JAV 文件名解析
│   └── media_browser/            # 媒体目录浏览领域
│       ├── api.py                # 目录懒加载枚举 HTTP 路由
│       └── schemas.py            # 响应 DTO
├── shared/
│   ├── constants.py              # 系统级常量（MEDIA_ROOT = /media）
│   └── utils/                    # 跨领域工具（文件 I/O、日志）
└── infrastructure/
    ├── file_task/
    │   └── file_task_run_manager.py  # 执行实例调度（并发控制）
    └── persistence/
        ├── sqlite/               # SQLite 仓储（任务执行记录、文件处理结果）
        │   ├── connection.py
        │   ├── schema.py
        │   └── file_task/        # FileTaskRun / FileResult 仓储实现
        └── yaml/                 # YAML 仓储（任务配置）
            ├── file_task_config_repository.py
            └── default_file_task_config_initializer.py
```

### 运行时目录

```
{J_FILE_KIT_BASE_DIR}/            # 默认 /data（容器内），可通过环境变量覆盖
├── config/task_config.yaml       # 任务配置（YAML）
├── sqlite/j_file_kit.db          # 任务执行记录 + 文件处理结果
└── logs/{run_name}_{run_id}.jsonl
```

**启动流程**：`lifespan` → `/media` 挂载检查（production）→ 创建 `sqlite/`、`logs/`、`config/` 子目录 → SQLite 连接 + schema 初始化 → YAML 默认配置初始化 → 读取配置触发模型校验

## 依赖规则

```
api/          Composition Root，组装所有依赖，无业务逻辑
  ↓
app/          业务逻辑（domain + application），不感知 infrastructure
  ↓
shared/       无业务逻辑工具，无外部依赖

infrastructure/   依赖 app/ 的 ports 接口，实现 I/O
```

- `shared/`：无外部依赖
- `app/*/domain`：仅依赖 shared
- `app/*/application`：依赖 shared + 本模块 domain
- `infrastructure`：依赖 shared + app/（实现 ports）
- `api`：依赖全部，作为 Composition Root

## 核心设计

### Task 执行模型

| 组件 | 职责 |
|------|------|
| **FileTaskRunner** (Protocol) | 定义"做什么"，业务用例入口；定义在 `domain/models.py` |
| **FileTaskRunManager** | 执行实例调度、并发控制（同一 task_type 单实例） |
| **FilePipeline** | 流程协调：扫描 → 分析 → 执行 → 持久化 |
| **Analyzer** | 分析文件，返回 Decision（纯函数） |
| **Executor** | 根据 Decision 执行文件操作，目标目录自动 `mkdir -p` |

```
API → FileTaskRunManager.start_run() → 后台线程
    → FileTaskRunner.run() → FilePipeline
        → scan → analyze（Decision）→ execute → 持久化结果
```

### Decision 模式

分离"分析"和"执行"，支持 `dry_run` 预览：`MoveDecision` / `DeleteDecision` / `SkipDecision`

### 配置管理

- **TaskConfig**（`domain/models.py`）：按 `task_type` 区分，含 `type`、`enabled`、`config`（dict）
- **JavVideoOrganizeConfig**（`application/config.py`）：具体配置 Pydantic 模型，通过 `TaskConfig.get_config()` 反序列化
- 存储在 YAML 文件，无内存缓存（任务启动非高频）
- **路径约束**：`model_validator` 强制所有目录路径必须是 `MEDIA_ROOT`（`/media`）子目录，构造时自动触发；目录是否存在仅在 API 更新时额外校验（`check_dirs_exist`）

### 依赖注入

| 类型 | 方式 |
|------|------|
| 数据库 | ports 注入（可替换、易测试） |
| 文件系统 | 直接调用 `shared/utils` |
| 日志 | 直接调用 `shared/utils` |

Repository 方法接收 `run_id` 参数而非构造时绑定，支持单例复用。

## 数据存储

| 存储 | 用途 |
|------|------|
| `config/task_config.yaml` | 任务配置，按 task_type 区分 |
| `sqlite/file_task_runs` | 执行实例（run_id、状态、统计） |
| `sqlite/file_results` | 文件处理结果（决策类型 + 执行结果） |

## 测试策略

`tests/` 目录结构镜像 `src/j_file_kit/`，按模块导航。

| 标记 | 适用场景 |
|------|----------|
| `unit` | 纯函数、Pydantic 模型验证、无 I/O 的 domain/application 逻辑 |
| `integration` | 涉及真实文件系统（YAML/SQLite）或 HTTP 层 |
| `e2e` | 完整 Docker 容器端到端流程 |

`conftest.py` 分层放置，子目录自动继承父级 fixtures。同一模块的单元与集成测试可共存于同一文件，用 marker 区分而非目录区分。

## 扩展指南

### 添加新任务类型

1. `domain/constants.py` 添加 `task_type` 常量
2. `application/config.py` 定义配置 Pydantic 模型 + 默认配置创建函数
3. `application/config_validator.py` 添加验证逻辑
4. `application/` 创建任务类，实现 `FileTaskRunner` 协议
5. 在路由文件注册端点，在 `app_state.py` 组装依赖

### 添加新 Domain

1. `app/<domain>/domain/`（models、ports）
2. `app/<domain>/application/`（schemas、services）
3. 路由文件 + `infrastructure/persistence/` 仓储实现
4. `api/app.py` 注册路由，`api/app_state.py` 组装依赖
