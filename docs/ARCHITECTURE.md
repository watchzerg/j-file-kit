# 架构设计文档

## 概述

j-file-kit 采用 DDD 架构，按业务领域组织代码。每个模块内部分为 domain（领域核心）和 application（应用编排）两层。遵循依赖倒置：domain 定义 ports 接口，infrastructure 实现接口。

## 目录结构

```
src/j_file_kit/
├── app/                          # 业务领域模块
│   └── file_task/                # 文件处理任务（状态、调度协议、扫描、分析、执行、配置）
│       ├── api.py                # 任务执行 HTTP 路由
│       ├── config_api.py         # 配置管理 HTTP 路由
│       ├── domain/               # 领域核心
│       │   ├── models.py         # 实体、值对象、枚举、领域异常、TaskConfig、FileTaskRunner
│       │   ├── decisions.py      # Decision 模型（MoveDecision / DeleteDecision / SkipDecision）
│       │   ├── ports.py          # 仓储接口（Protocol）
│       │   └── constants.py      # 任务类型常量（如 task_type）
│       └── application/          # 应用编排
│           ├── schemas.py        # 任务执行 API 请求/响应 DTO
│           ├── config_schemas.py # 配置管理 API 请求/响应 DTO
│           ├── config.py         # 任务配置模型（JavVideoOrganizeConfig、AnalyzeConfig）
│           ├── config_validator.py         # 配置验证（纯函数）
│           ├── file_task_config_service.py # 配置业务逻辑编排
│           ├── jav_video_organizer.py      # JavVideoOrganizer（FileTaskRunner 实现）
│           ├── pipeline.py       # 流程协调（FilePipeline：扫描 → 分析 → 执行）
│           ├── analyzer.py       # 文件分析（analyze_file，返回 Decision）
│           ├── executor.py       # 决策执行（execute_decision）
│           ├── file_ops.py       # 目录扫描工具函数
│           └── jav_filename_util.py        # JAV 文件名解析工具函数
├── shared/utils/                 # 跨领域工具（文件 I/O、日志）
├── infrastructure/               # 有状态 I/O 实现
│   ├── persistence/sqlite/       # SQLite 仓储实现（任务执行记录）
│   ├── persistence/yaml/         # YAML 仓储实现（任务配置）
│   └── file_task/                # FileTaskRunManager 调度器
└── api/                          # FastAPI 应用入口
    ├── app.py                    # 路由注册、生命周期、异常处理
    └── app_state.py              # Composition Root（组装依赖）
```

### 模块内部结构（通用模板）

```
app/<module>/
├── <module_api>.py               # HTTP 路由（可按职责拆分为多个文件）
├── domain/
│   ├── models.py                 # 实体、值对象、枚举、领域异常
│   ├── decisions.py              # Decision 模型（如有分析/执行分离需求）
│   ├── ports.py                  # 仓储接口（Protocol）
│   └── constants.py              # 类型常量（如 task_type）
└── application/
    ├── schemas.py                # 请求/响应 DTO
    ├── config.py                 # 任务配置模型
    ├── config_validator.py       # 配置验证（纯函数）
    └── <feature>_service.py      # 业务逻辑编排（按职责命名）
```

> 说明：领域异常定义在 `models.py` 中（与实体/枚举共存），无需单独的 `exceptions.py`。

### 运行时目录

```
{base_dir}/                       # 默认 .app-data，可通过 J_FILE_KIT_BASE_DIR 覆盖
├── config/task_config.yaml       # 任务配置（YAML）
├── sqlite/j_file_kit.db          # SQLite 数据库（任务执行记录）
└── logs/{run_name}_{run_id}.jsonl  # 任务日志（JSON Lines）
```

**初始化流程**：`lifespan` → 创建目录 → SQLite 连接 → schema 初始化 → YAML 默认配置初始化

## 概念层次

file_task 领域内有两个核心概念层：

- **Task Type（任务类型）**：定义一类任务的行为和配置，由 `task_type` 字符串常量 + `TaskConfig` + `FileTaskRunner` 协议组合表达
- **FileTaskRun（执行实例）**：每次任务执行的记录，包含 `run_id`、`run_name`、状态、统计等

## 依赖规则

```
API Layer  ──────────────────────────────────────────────────────────────
    │                 （路由、异常处理、生命周期）
    ↓
App Layer  ──────────────────────────────────────────────────────────────
    │   ┌──────────────────────────────────────────────┐
    │   │  file_task                                    │
    │   │  （调度协议 + 文件处理业务逻辑 + 配置管理）    │
    │   └──────────────────────────────────────────────┘
    │
    ├───────────────────────┬────────────────────────────
    ↓                       ↓
Shared Layer          Infrastructure Layer
（无业务逻辑工具）      （实现 ports 接口）
```

**依赖方向**：
- `shared/`：无外部依赖
- `app/*/domain`：仅依赖 shared 和其他模块的 domain
- `app/*/application`：依赖 shared 和本模块 domain
- `infrastructure`：依赖 shared 和 app/（实现 ports）
- `api`：作为 Composition Root 组装所有依赖

## 核心设计

### Task 执行模型

| 组件 | 职责 |
|------|------|
| **FileTaskRunner** (Protocol) | 定义"做什么"，业务用例入口；定义在 `domain/models.py` |
| **FileTaskRunManager** | 执行实例调度（创建/执行/取消），并发控制（单实例） |
| **FilePipeline** | 流程协调：扫描 → 分析 → 执行 |
| **Analyzer** | 分析文件，返回 Decision |
| **Executor** | 根据 Decision 执行操作 |

**执行流程**：
```
API 请求 → FileTaskRunManager.start_run() → 后台线程执行
    → FileTaskRunner.run() → FilePipeline 协调
        → scan → analyze (Decision) → execute → 持久化
    → 更新执行实例状态
```

### Decision 模式

分离"分析"和"执行"，支持 dry_run 预览：
- `MoveDecision`：移动文件
- `DeleteDecision`：删除文件
- `SkipDecision`：跳过

### 配置管理

- **TaskConfig**：按 task_type 区分的任务配置，定义在 `domain/models.py`，包含 `type`、`enabled`、`config`（dict）字段
- **JavVideoOrganizeConfig**：具体任务配置 Pydantic 模型，定义在 `application/config.py`，通过 `TaskConfig.get_config()` 反序列化得到
- **FileTaskConfigService**：配置读取、合并、验证、保存的业务逻辑，定义在 `application/file_task_config_service.py`
- 配置存储在 YAML 文件中（`{base_dir}/config/task_config.yaml`），支持通过 HTTP API 读取和修改
- 配置无内存缓存，每次读取直接读 YAML 文件（任务启动非高频，无需缓存）

### 依赖注入策略

| 类型 | 方式 | 原因 |
|------|------|------|
| 数据库 | ports 注入 | 可替换、需事务测试 |
| 文件系统 | 直接依赖 shared/utils | API 稳定、临时目录可测 |
| 日志 | 直接依赖 shared/utils | API 稳定、loguru 原生支持 |

### Repository 参数化

Repository 方法接收 `run_id` 参数（而非构造时绑定），支持单例复用：
```python
file_result_repository.save_result(run_id=123, result=...)
```

## 数据存储

| 存储 | 用途 |
|------|------|
| `config/task_config.yaml` | 任务配置（YAML，按 task_type 区分） |
| `sqlite/file_task_runs` 表 | 执行实例（状态、统计） |
| `sqlite/file_results` 表 | 文件处理结果（决策 + 执行） |

## 扩展指南

### 添加新任务类型

1. 在 `app/file_task/application/` 创建任务类，实现 `FileTaskRunner` 协议
2. 定义任务类型常量（`domain/constants.py`）
3. 定义配置模型（`application/config.py`）和验证器（`application/config_validator.py`）
4. 在 `application/config.py` 中添加默认配置创建函数
5. 在路由文件中注册端点，组装依赖

### 添加新 Domain

1. 创建 `app/<domain>/domain/`（models、ports）
2. 创建 `app/<domain>/application/`（schemas、services）
3. 创建路由文件（`<domain>_api.py` 或 `api.py`）
4. 在 `infrastructure/persistence/` 中实现仓储（SQLite 或 YAML）
5. 在 `api/app.py` 注册路由

## 关键决策

1. **Feature-First**：按业务功能划分模块
2. **存储分离**：YAML 存配置、SQLite 存运行数据，各取所长
3. **FileTaskRunner 协议**：解耦调度与具体任务，定义在 `domain/models.py`
4. **Decision 模式**：分析/执行分离，支持预览
5. **单实例部署**：FileTaskRunManager 的单执行实例约束基于此假设

## 测试策略

### 目录结构

```
tests/
├── conftest.py                               # 全局 fixtures
├── shared/utils/                             # 镜像 src/shared/utils/
├── app/
│   └── file_task/
│       ├── conftest.py                       # mock 仓储、示例 TaskConfig
│       ├── domain/                           # 镜像 src/.../domain/
│       └── application/
│           ├── conftest.py                   # 临时 YAML 文件、配置对象构造器
│           └── ...
└── infrastructure/
    ├── conftest.py                           # 真实文件系统临时目录、SQLite 连接
    ├── file_task/                            # 镜像 src/infrastructure/file_task/
    └── persistence/yaml/                     # 镜像 src/infrastructure/persistence/yaml/
```

### 核心原则

- **镜像源码结构**：`tests/` 目录结构与 `src/j_file_kit/` 完全对应，按模块导航测试文件
- **Marker 分层，而非目录分层**：用 `pytestmark = pytest.mark.unit / integration` 区分类型，而非 `tests/unit/` + `tests/integration/` 双目录；同一模块的单元与集成测试可共存于同一文件
- **`conftest.py` 分层放置**：利用 pytest fixture 继承机制，在每个有公共 fixtures 需求的目录放置 `conftest.py`，子目录自动继承父级 fixtures

### 测试类型划分

| 标记 | 适用场景 | 典型示例 |
|------|----------|----------|
| `unit` | 纯函数、Pydantic 模型验证、无 I/O 的 domain/application 逻辑 | `test_jav_filename_util.py`、`test_config_validator.py` |
| `integration` | 涉及真实文件系统（YAML/SQLite）或外部 I/O | `test_file_task_config_repository.py`、`test_file_task_run_manager.py` |
| `slow` | 端到端 pipeline、大量文件操作 | 完整 `FilePipeline` 流程测试 |

### conftest.py 分层职责

| 层级 | 放置内容 |
|------|----------|
| `tests/conftest.py` | 全局通用 fixtures（如扩展 `tmp_path`） |
| `tests/app/file_task/conftest.py` | mock 仓储实现、示例 `TaskConfig` 构造器 |
| `tests/app/file_task/application/conftest.py` | 临时 YAML 配置文件路径、具体任务配置对象 |
| `tests/infrastructure/conftest.py` | 真实临时数据目录、SQLite 连接、YAML 仓储实例 |
