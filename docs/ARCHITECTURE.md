# 架构设计文档

## 概述

j-file-kit 采用领域驱动设计（DDD）架构，按业务领域组织代码，每个模块内部分为 domain 层（领域核心）和 application 层（应用编排）。遵循依赖倒置原则，domain 层定义接口（ports），infrastructure 层实现接口。

## 目录结构

```
src/j_file_kit/
├── app/                          # 应用层 - 业务领域模块
│   ├── config/                   # 配置模块
│   │   ├── domain/               # 领域层
│   │   │   ├── models.py         # 配置领域模型（GlobalConfig、TaskConfig、AppConfig）
│   │   │   ├── ports.py          # 仓储接口（AppConfigRepository、ConfigStateManager）
│   │   │   └── exceptions.py     # 配置相关异常
│   │   ├── application/          # 应用层
│   │   │   ├── schemas.py        # 请求/响应 DTO
│   │   │   ├── config_service.py # 配置服务
│   │   │   └── config_validator.py # 验证逻辑
│   │   └── api.py                # HTTP 路由
│   ├── task/                     # 任务调度模块
│   │   ├── domain/               # 领域层
│   │   │   ├── models.py         # 领域模型（TaskStatus、TaskRecord、TaskRunner）
│   │   │   └── ports.py          # 仓储接口（TaskRepository）
│   │   ├── application/          # 应用层
│   │   │   └── schemas.py        # 请求/响应 DTO
│   │   └── api.py                # HTTP 路由（列表、查询、取消）
│   └── file_task/                # 文件任务模块
│       ├── domain/               # 领域层
│       │   ├── models.py         # 领域模型（FileType、SerialId、Operation）
│       │   ├── decisions.py      # 决策模型（MoveDecision、DeleteDecision、SkipDecision）
│       │   └── ports.py          # 仓储接口（FileItemRepository、FileProcessorRepository）
│       ├── application/          # 应用层
│       │   ├── schemas.py        # 请求/响应 DTO
│       │   ├── config.py         # 任务配置（JavVideoOrganizeConfig、AnalyzeConfig）
│       │   ├── analyzer.py       # 分析器（analyze_file）
│       │   ├── executor.py       # 执行器（execute_decision）
│       │   ├── pipeline.py       # 处理管道（FilePipeline）
│       │   ├── jav_video_organizer.py # 具体任务实现
│       │   ├── file_ops.py       # 文件处理工具函数
│       │   └── jav_filename_util.py # JAV 文件名处理函数
│       └── api.py                # HTTP 路由（启动任务）
├── shared/                       # 共享层 - 跨领域通用代码
│   ├── models/                   # 通用模型（预留扩展）
│   ├── interfaces/               # 通用接口（预留扩展）
│   └── utils/                    # 工具函数（文件 I/O、日志配置）
├── infrastructure/               # 基础设施层 - 有状态的 I/O 操作
│   ├── persistence/sqlite/       # 数据库（connection、repositories）
│   │   ├── config/               # 配置仓储实现
│   │   └── task/                 # 任务仓储实现
│   ├── config/                   # 配置加载
│   └── task/                     # 任务调度（TaskManager）
└── api/                          # HTTP 接口层
    ├── app.py                    # FastAPI 应用
    └── app_state.py              # 应用状态管理（Composition Root）
```

### 测试目录约定

```
tests/
├── app/               # 对应 app/ 业务模块
├── infrastructure/    # 对应 infrastructure/
└── shared/            # 对应 shared/
```

测试目录按层级镜像 `src/j_file_kit/`，单元测试放在对应层级下。

## 架构分层

### 1. App Layer（应用层）

按业务领域组织，每个模块包含两个子层：

**Domain 层（领域核心）**：
- 实体（Entities）：业务核心对象
- 值对象（Value Objects）：不可变的业务概念
- 枚举：业务状态和类型定义
- 领域异常：业务相关的异常类型
- 仓储接口（Ports）：定义数据访问接口

**Application 层（应用编排）**：
- 用例服务（Services）：业务逻辑编排
- DTO（Schemas）：请求/响应数据传输对象
- 配置模型：任务配置等
- 管道（Pipeline）：处理流程协调

**各模块职责**：
- **config**: 配置管理（GlobalConfig、AppConfig、TaskConfig）
- **task**: 任务协议和 API（TaskRepository 协议、通用任务 API）
- **file_task**: 文件处理任务（扫描、分析、执行、统计）

### 2. Shared Layer（共享层）

跨 domain 的通用代码，无业务逻辑，无外部依赖。

- **models/**: 预留扩展（当前为空）
- **utils/**: 工具函数（文件 I/O、日志配置等稳定的跨切面功能）

### 3. Infrastructure Layer（基础设施层）

提供有状态的 I/O 操作，实现 domain 定义的 ports 接口，以及任务调度基础设施。

- **persistence/sqlite/**: SQLite 仓储实现
- **config/**: 配置加载（load_app_config_from_db）
- **task/**: 任务调度（TaskManager）

### 4. API Layer（HTTP 接口层）

FastAPI 应用，路由注册，异常处理，生命周期管理。

- **app.py**: FastAPI 应用入口
- **app_state.py**: 应用状态管理（Composition Root），负责组装所有依赖

## 依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                           API Layer                              │
│              (路由注册、异常处理、生命周期管理)                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                          App Layer                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    各业务模块                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │   │
│  │  │   config    │  │    task     │←─│    file_task    │   │   │
│  │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────────┐ │   │   │
│  │  │ │ domain  │ │  │ │ domain  │ │  │ │   domain    │ │   │   │
│  │  │ ├─────────┤ │  │ ├─────────┤ │  │ ├─────────────┤ │   │   │
│  │  │ │ app层   │ │  │ │ app层   │ │  │ │ application │ │   │   │
│  │  │ └─────────┘ │  │ └─────────┘ │  │ └─────────────┘ │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ↓                                      ↓
┌───────────────────────┐              ┌───────────────────────┐
│    Shared Layer       │              │  Infrastructure Layer │
│  (无业务逻辑的工具)     │              │  (实现 ports 接口)     │
└───────────────────────┘              └───────────────────────┘
```

**依赖规则**：
- shared/: 无外部依赖（纯工具函数）
- app/*/domain: 仅依赖 shared/ 和其他模块的 domain 层
- app/*/application: 依赖 shared/ 和本模块的 domain 层
- infrastructure: 依赖 shared/ 和 app/（ports、domain models），实现 domain 的 ports
- api: 依赖 app/、infrastructure/、shared/（作为 Composition Root 组装所有依赖）

### 模块间依赖

- **file_task** 依赖 **task**：file_task.application 使用 task.domain.models.TaskRunner 和 task.domain.ports.TaskRepository
- **file_task** 依赖 **config**：file_task.application 使用 config.domain.models.AppConfig 读取全局配置（目录路径）和任务配置（文件扩展名、删除规则等）
- **task** 不依赖 **file_task**：task 模块保持通用，不包含文件任务专属类型
- **config** 不依赖其他业务模块：config 模块作为基础配置模块，保持独立

### 依赖策略

根据 I/O 操作的特性采用不同的依赖方式：

| 类型 | 依赖方式 | 位置 | 原因 |
|------|----------|------|------|
| **数据库操作** | 通过 ports 注入 | infrastructure/ | 可能迁移数据库、需要事务测试、连接管理复杂 |
| **文件系统操作** | 直接依赖 | shared/utils/ | API 稳定、用临时目录即可测试、无状态管理 |
| **日志操作** | 直接依赖 | shared/utils/ | API 稳定、loguru 原生支持测试捕获、无状态管理 |

业务相关的文件操作（如带 `-jfk-` 后缀的冲突处理）应放在对应模块的 `application/file_ops.py` 中。

## 核心概念

### Task、Pipeline 职责分工

| 组件 | 层次 | 职责 |
|------|------|------|
| **TaskRunner** | 业务用例层 | 定义"做什么"，配置 Pipeline |
| **Pipeline** | 流程协调层 | 定义"怎么做流程"，协调扫描→分析→执行与统计 |
| **Analyzer** | 分析层 | 分析文件，返回 Decision |
| **Executor** | 执行层 | 根据 Decision 执行操作 |

任务状态由 **TaskManager** 统一更新，Pipeline 只负责流程协调、统计与日志。

### TaskManager 职责

TaskManager 是全局任务调度器，位于 `infrastructure/task/`（任务调度基础设施）：
- 管理任务的生命周期（创建、执行、取消）
- 控制并发（当前只允许一个任务运行）
- 通过 TaskRunner 协议与具体任务实现解耦

**部署约束**：
- 本项目以单实例 Web 服务方式部署
- TaskManager 的“单任务运行”约束基于单实例假设

### Decision 模式

文件处理使用 Decision 模式，分离"分析"和"执行"：
- **MoveDecision**: 移动文件到目标目录
- **DeleteDecision**: 删除文件
- **SkipDecision**: 跳过不处理

## 数据存储

### SQLite 表结构

| 表 | 用途 |
|---|---|
| `global_config` | 全局配置（单行，scan_root） |
| `task_configs` | 任务配置（name、type、enabled、config JSON） |
| `tasks` | 任务实例（状态、时间、统计） |
| `file_items` | 文件处理结果 |
| `file_operations` | 文件操作历史 |

### 配置加载流程

1. FastAPI `lifespan` 创建 `SQLiteConnectionManager`
2. `SQLiteSchemaInitializer` 初始化表结构
3. `AppState` 组装依赖并创建 `AppConfigRepositoryImpl`
4. `load_app_config_from_db()` 加载配置到内存

## 任务执行流程

```
API 请求 → 创建任务实例（注入 repositories）→ TaskManager 启动（后台线程）
    ↓
Pipeline 协调执行
    ├── 扫描文件（scan_directory_items）
    ├── 分析文件（analyze_file → Decision）
    ├── 执行决策（execute_decision）
    ├── 结果持久化
    └── 任务完成
    ↓
任务完成，状态更新到数据库
```

## 扩展指南

### 添加新任务类型

1. 在对应模块的 `application/` 创建任务类（如 `app/file_task/application/new_task.py`）
2. 实现 `TaskRunner` 协议
3. 构造函数接收所需的 repositories（通过 API 层注入）
4. 实现 `run(task_id, dry_run, cancellation_event)` 方法
5. 在对应的 `api.py` 中注册启动端点，组装依赖

### 添加新 Domain

1. 在 `app/` 下创建目录（如 `app/new_domain/`）
2. 创建 domain 层：
   - `domain/models.py`：领域模型
   - `domain/ports.py`：仓储接口
3. 创建 application 层：
   - `application/schemas.py`：DTO
   - `application/services.py`：业务服务
4. 创建 `api.py`：HTTP 路由
5. 在 `infrastructure/persistence/sqlite/` 创建仓储实现
6. 在 `api/app.py` 注册路由

### 模块内部结构模板

```
app/new_domain/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── models.py       # 实体、值对象、枚举、异常
│   └── ports.py        # 仓储接口
├── application/
│   ├── __init__.py
│   ├── schemas.py      # DTO
│   └── services.py     # 用例服务
└── api.py              # HTTP 路由
```

## 关键设计决策

1. **Feature-First 模块组织**: 按业务功能划分模块，每个模块内部分 domain 和 application 层
2. **SQLite 存储配置**: 统一数据存储，便于管理和备份
3. **路径冲突处理**: "先尝试后生成"模式，使用 `-jfk-xxxx` 后缀
4. **仓储模式**: domain 定义 ports，infrastructure 实现，实现依赖倒置
5. **JSON 字段**: 灵活存储不同任务类型的特定数据
6. **任务调度分离**: TaskManager 独立于具体任务类型，通过 TaskRunner 协议解耦
7. **Decision 模式**: 分离分析和执行，支持 dry_run 预览
8. **Repository 参数化设计**: FileItemRepository/FileProcessorRepository 方法接收 task_id 参数而非构造时绑定，支持单例复用，简化依赖注入
