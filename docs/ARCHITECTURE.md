# 架构设计文档

## 概述

j-file-kit 采用领域驱动设计（DDD）架构，按业务领域组织代码。每个领域包含完整的领域模型、业务逻辑、API 接口和端口定义，遵循依赖倒置原则。

## 目录结构

```
src/j_file_kit/
├── app/                          # 应用层 - 业务领域
│   ├── app_config/              # 配置 domain
│   │   ├── domain.py            # 配置领域模型
│   │   ├── service/             # 业务逻辑
│   │   ├── api.py               # API 路由
│   │   ├── schemas.py           # 请求/响应模型
│   │   └── ports.py             # 仓储接口
│   ├── task/                    # 任务调度 domain
│   │   ├── ports.py             # TaskRepository 协议
│   │   ├── api.py               # 通用任务 API（列表、查询、取消）
│   │   └── schemas.py           # 请求/响应模型
│   └── file_task/               # 文件任务 domain
│       ├── domain.py            # 领域模型（PathEntryType、FileType、Operation 等）
│       ├── config.py            # 专属配置（JavVideoOrganizeConfig）
│       ├── pipelines/file/      # 处理管道（流程协调）
│       ├── processors/file/     # 处理器实现
│       │   ├── analyzers/       # 分析器
│       │   ├── executors.py     # 执行器
│       │   ├── initializers.py  # 初始化器
│       │   └── finalizers.py    # 终结器
│       ├── service/             # 用例编排（JavVideoOrganizer）
│       ├── api.py               # 文件任务 API（启动任务）
│       ├── schemas.py           # 请求/响应模型
│       └── ports.py             # 仓储接口（FileItemRepository 等）
├── shared/                       # 共享层 - 跨领域通用代码
│   ├── models/                  # 通用模型（预留扩展）
│   ├── interfaces/              # 通用接口（BaseTask、Processor 协议）
│   └── utils/                   # 工具函数（文件 I/O、日志配置、扫描等）
├── infrastructure/               # 基础设施层 - 有状态的 I/O 操作
│   ├── persistence/sqlite/      # 数据库（connection、repositories）
│   ├── config/                  # 配置加载
│   └── task/                    # 任务调度（TaskManager）
└── api/                          # HTTP 接口层
    ├── app.py                   # FastAPI 应用
    └── app_state.py             # 应用状态管理（Composition Root）
```

## 架构分层

### 1. App Layer（应用层）

按业务领域组织，每个 domain 自包含，通过 ports 定义接口，由 infrastructure 实现。

- **app_config**: 配置管理（GlobalConfig、AppConfig、TaskConfig）
- **task**: 任务协议和 API（TaskRepository 协议、通用任务 API）
- **file_task**: 文件处理任务（扫描、分析、执行、统计）

### 2. Shared Layer（共享层）

跨 domain 的通用代码，无业务逻辑，无外部依赖。

- **models/**: 预留扩展（当前为空）
- **interfaces/**: BaseTask 协议、Processor 基类
- **utils/**: 工具函数（文件 I/O、日志配置等稳定的跨切面功能）

### 3. Infrastructure Layer（基础设施层）

提供有状态的 I/O 操作，实现 domain 定义的 ports 接口，以及任务调度基础设施。

- **persistence/sqlite/**: SQLite 仓储实现
- **config/**: 配置加载（load_config_from_db）
- **task/**: 任务调度（TaskManager）

### 4. API Layer（HTTP 接口层）

FastAPI 应用，路由注册，异常处理，生命周期管理。

- **app.py**: FastAPI 应用入口
- **app_state.py**: 应用状态管理（Composition Root），负责组装所有依赖

## 依赖关系

```
┌─────────────┐
│     API     │  → 路由注册、异常处理
└──────┬──────┘
       │
       ↓
┌─────────────┐
│     App     │  → 业务领域（定义 ports、domain models、异常）
│             │
│ ┌─────────┐ │
│ │  task   │←┼──── file_task 依赖 task
│ └─────────┘ │
│ ┌─────────┐ │
│ │file_task│ │
│ └─────────┘ │
└──────┬──────┘
       │
       ├──────────────────┐
       ↓                  ↓
┌─────────────┐    ┌──────────────┐
│   Shared    │    │Infrastructure│  → 实现 ports（依赖 app/）
└─────────────┘    └──────────────┘
```

**依赖规则**：
- shared/models: 无外部依赖（预留扩展）
- shared/interfaces: 依赖 shared/models
- shared/utils: 无外部依赖（纯文件 I/O 工具）
- app/task: 依赖 shared/
- app/file_task: 依赖 shared/ 和 app/task
- infrastructure: 依赖 shared/ 和 app/（ports、domain models），实现 domain 的 ports
- api: 依赖 app/、infrastructure/、shared/（作为 Composition Root 组装所有依赖）

### 依赖策略

根据 I/O 操作的特性采用不同的依赖方式：

| 类型 | 依赖方式 | 位置 | 原因 |
|------|----------|------|------|
| **数据库操作** | 通过 ports 注入 | infrastructure/ | 可能迁移数据库、需要事务测试、连接管理复杂 |
| **文件系统操作** | 直接依赖 | shared/utils/ | API 稳定、用临时目录即可测试、无状态管理 |
| **日志操作** | 直接依赖 | shared/utils/ | API 稳定、loguru 原生支持测试捕获、无状态管理 |

业务相关的文件操作（如带 `-jfk-` 后缀的冲突处理）应放在对应 domain 的 utils.py 中。

## 核心概念

### Task、Pipeline、ProcessorChain 职责分工

| 组件 | 层次 | 职责 |
|------|------|------|
| **Task** | 业务用例层 | 定义"做什么"，组合处理器，创建 Pipeline |
| **Pipeline** | 流程协调层 | 定义"怎么做流程"，协调扫描→处理→汇总 |
| **ProcessorChain** | 处理器执行层 | 定义"怎么执行处理器"，管理执行顺序 |

### TaskManager 职责

TaskManager 是全局任务调度器，位于 `infrastructure/task/`（任务调度基础设施）：
- 管理任务的生命周期（创建、执行、取消）
- 控制并发（当前只允许一个任务运行）
- 通过 BaseTask 协议与具体任务实现解耦
- 协调运行时依赖组装（创建 TaskRepositoryRegistry）

### 处理器类型

| 类型 | 级别 | 职责 |
|------|------|------|
| **Initializer** | 任务级 | 前置处理（状态、配置验证、资源初始化） |
| **Analyzer** | Item 级 | 分析（分类、提取番号、决定动作） |
| **Executor** | Item 级 | 执行操作（移动、删除文件） |
| **Finalizer** | 任务级 | 后处理（统计信息更新） |

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

1. `AppState.__init__()` 创建 `SQLiteConnectionManager`
2. 连接管理器自动创建表结构
3. `AppConfigRepository` 检查并创建默认配置
4. `load_config_from_db()` 加载配置到内存

## 任务执行流程

```
API 请求 → 创建任务实例 → TaskManager 启动（后台线程）
    ↓
Pipeline 协调执行
    ├── Initializers（前置处理）
    ├── Scanner（扫描文件）
    ├── ProcessorChain（Analyzers → Executors）
    ├── 结果持久化
    └── Finalizers（后处理）
    ↓
任务完成，状态更新到数据库
```

## 扩展指南

### 添加新处理器

1. 在 `app/file_task/processors/file/` 创建处理器类
2. 继承 `shared/interfaces/processors/` 中的基类
3. 实现 `process()`（Item 级）或 `initialize()`/`finalize()`（任务级）
4. 在 `jav_video_organizer.py` 的 `create_pipeline()` 中注册

### 添加新任务类型

1. 在对应 domain 的 `service/` 创建任务类（如 `app/file_task/service/`）
2. 实现 `shared/interfaces/task.py::BaseTask` 协议
3. 实现 `run()` 方法
4. 在对应的 `api.py` 中注册启动端点

### 添加新 Domain

1. 在 `app/` 下创建目录（如 `app/new_domain/`）
2. 创建：`domain.py`、`ports.py`、`schemas.py`、`service/`、`api.py`
3. 在 `infrastructure/persistence/sqlite/` 创建仓储实现
4. 在 `api/app.py` 注册路由

## 关键设计决策

1. **SQLite 存储配置**: 统一数据存储，便于管理和备份
2. **路径冲突处理**: "先尝试后生成"模式，使用 `-jfk-xxxx` 后缀
3. **仓储模式**: domain 定义 ports，infrastructure 实现，实现依赖倒置
4. **JSON 字段**: 灵活存储不同任务类型的特定数据
5. **任务调度分离**: TaskManager 独立于具体任务类型，通过 BaseTask 协议解耦
