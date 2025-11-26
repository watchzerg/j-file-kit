# 架构设计文档

## 概述

j-file-kit 采用领域驱动设计（DDD）架构，按业务领域组织代码。每个领域（domain）包含完整的领域模型、业务逻辑、API接口和端口定义，遵循依赖倒置原则。

## 目录结构

```
src/j_file_kit/
├── app/                          # 应用层 - 各个domain的目录
│   ├── app_config/              # 配置domain
│   │   ├── domain.py            # 配置领域模型（GlobalConfig、AppConfig、TaskConfig）
│   │   ├── service/             # 配置业务逻辑（合并、验证）
│   │   │   └── config_service.py
│   │   ├── api.py               # 配置API路由
│   │   ├── schemas.py           # HTTP请求/响应模型
│   │   └── ports.py             # 配置仓储接口（AppConfigRepository）
│   └── file_task/               # 文件任务domain
│       ├── domain.py            # 文件任务领域模型（FileType、PathEntryType等）
│       ├── utils.py             # 文件任务工具函数（get_file_type等）
│       ├── config.py            # 文件任务的专属配置模型（JavVideoOrganizeConfig）
│       ├── schemas.py           # HTTP请求/响应模型
│       ├── ports.py             # 文件任务仓储接口（TaskRepository、FileItemRepository等）
│       ├── file_util.py         # 领域工具函数（JAV相关）
│       ├── pipelines/           # 文件处理管道
│       │   └── file/
│       │       ├── pipeline.py  # 流程协调层
│       │       ├── statistics.py
│       │       └── utils.py
│       ├── processors/          # 文件处理器实现
│       │   └── file/
│       │       ├── analyzers/   # 分析器
│       │       ├── executors.py # 执行器
│       │       ├── initializers.py # 初始化器
│       │       └── finalizers.py   # 终结器
│       ├── service/             # 用例，流程编排
│       │   ├── jav_video_organizer.py # 任务用例实现
│       │   └── task_manager.py  # 任务管理器
│       └── api.py               # FastAPI路由
├── shared/                      # 共享代码
│   ├── models/                  # 全局模型
│   │   ├── task.py             # 任务模型（Task、TaskReport）
│   │   ├── results.py          # 处理结果模型（ItemResult、ProcessorResult）
│   │   ├── contexts.py         # 上下文对象（ItemContext）
│   │   ├── enums.py            # 枚举类型（TaskStatus、TaskType、TriggerType）
│   │   └── exceptions.py       # 领域异常
│   ├── interfaces/              # 通用接口
│   │   ├── task.py             # BaseTask协议
│   │   └── processors/         # 处理器协议
│   │       ├── base.py         # 处理器基类
│   │       ├── item.py         # Item级别处理器协议
│   │       ├── task.py         # 任务级别处理器协议
│   │       └── chain.py        # ProcessorChain处理器链
│   └── utils/                   # 通用工具
│       ├── file_utils.py       # 通用文件工具函数
│       └── config_utils.py     # 配置验证工具函数
├── infrastructure/              # 基础设施层
│   ├── filesystem/              # 文件系统操作
│   │   ├── operations.py        # 文件操作封装
│   │   └── scanner.py          # 文件扫描操作
│   ├── persistence/             # 持久化（按领域划分）
│   │   └── sqlite/
│   │       ├── connection.py    # 数据库连接管理
│   │       ├── config/          # 配置仓储实现
│   │       │   └── config_repository.py
│   │       └── task/            # 任务仓储实现
│   │           ├── task_repository.py
│   │           ├── file_item_repository.py
│   │           ├── file_processor_repository.py
│   │           └── task_repository_registry.py
│   ├── config/                  # 配置加载
│   │   └── config.py
│   ├── logging/                 # 日志配置
│   │   └── logging_setup.py
│   └── app_state.py            # 应用状态管理
└── api/                         # HTTP接口层（主应用）
    └── app.py                   # FastAPI应用实例和路由注册
```

## 架构分层

### 1. App Layer (应用层 - Domain组织)

**位置**: `src/j_file_kit/app/`

**职责**:
- 按业务领域组织代码，每个domain包含完整的业务功能
- 定义领域模型、业务逻辑、API接口和端口

**特点**:
- 每个domain是自包含的，包含该领域的所有代码
- 通过ports定义接口，infrastructure层实现这些接口（依赖倒置）
- 可以依赖shared层和infrastructure层

**主要Domain**:

#### app_config (配置domain)

**位置**: `app/app_config/`

**职责**: 管理应用配置

**主要模块**:
- `domain.py`: 配置领域模型
  - `GlobalConfig`: 全局配置模型（目录路径等）
  - `AppConfig`: 应用级配置聚合根
  - `TaskConfig`: 任务配置模型
  - `create_default_global_config()`: 创建默认全局配置
  - `create_default_task_configs()`: 创建默认任务配置
- `service/config_service.py`: 配置业务逻辑（合并、验证、保存）
- `api.py`: 配置管理API路由（GET、PATCH）
- `schemas.py`: HTTP请求/响应模型（UpdateConfigRequest等）
- `ports.py`: 配置仓储接口（AppConfigRepository Protocol）

#### file_task (文件任务domain)

**位置**: `app/file_task/`

**职责**: 文件处理任务相关的所有功能

**主要模块**:
- `domain.py`: 文件任务领域模型（包含文件domain专用的所有领域模型）
  - `FileType`: 文件类型枚举（VIDEO、IMAGE、ARCHIVE、MISC）
  - `PathEntryType`、`PathEntryAction`、`PathEntryInfo`: 路径项相关模型
  - `PathEntryContext`: 路径项处理上下文
  - `FileItemResult`: 文件处理结果
  - `OperationType`、`Operation`: 文件操作相关模型
  - `SerialId`: 番号值对象
- `config.py`: 文件任务专属配置模型（JavVideoOrganizeConfig）
- `utils.py`: 文件任务工具函数（如 `get_file_type()`）
- `schemas.py`: HTTP请求/响应模型（StartTaskRequest、TaskStatusResponse等）
- `ports.py`: 文件任务仓储接口
  - `TaskRepository`: 任务仓储协议
  - `FileItemRepository`: 文件处理结果仓储协议
  - `FileProcessorRepository`: 文件处理操作仓储协议
  - `TaskRepositoryRegistry`: 任务仓储注册表协议
- `file_util.py`: 领域工具函数（JAV相关：番号提取、文件名生成等）
- `pipelines/file/`: 文件处理管道实现（流程协调层）
  - `pipeline.py`: FilePipeline，协调文件扫描、处理器链执行和结果汇总
  - `statistics.py`: 统计信息跟踪
  - `utils.py`: 管道工具函数
- `processors/file/`: 文件处理相关的处理器实现
  - `analyzers/`: 分析器实现（FileClassifier、FileSerialIdExtractor、FileActionDecider等）
  - `executors.py`: 执行器实现（UnifiedFileExecutor、EmptyDirectoryExecutor）
  - `initializers.py`: 初始化器实现（TaskStatusInitializer、TaskConfigValidatorInitializer、TaskResourceInitializer等）
  - `finalizers.py`: 终结器实现（TaskStatisticsFinalizer）
- `service/`: 用例，流程编排
  - `jav_video_organizer.py`: JAV视频文件整理任务用例实现
  - `task_manager.py`: 任务管理器，管理任务的执行、状态跟踪和取消
- `api.py`: 文件任务管理API路由（启动、查询、取消任务等）

### 2. Shared Layer (共享层)

**位置**: `src/j_file_kit/shared/`

**职责**:
- 提供跨domain的共享代码
- 包含通用模型、接口和工具函数

**特点**:
- 无业务逻辑，只包含通用概念
- 无外部依赖（仅标准库和Pydantic）
- 可被所有domain使用

**主要模块**:

#### shared/models (全局模型)

**位置**: `shared/models/`

**职责**: 定义跨domain的通用数据模型

**主要模块**:
- `task.py`: 任务模型（Task、TaskReport）
- `results.py`: 处理结果模型（ItemResult、ProcessorResult）
- `contexts.py`: 上下文对象（ItemContext）
- `enums.py`: 枚举类型（TaskStatus、TaskType、TriggerType）
- `exceptions.py`: 领域异常

**注意**: 文件domain专用的类型已迁移到 `app/file_task/domain.py`，包括：
- `FileType`、`PathEntryType`、`PathEntryAction`、`PathEntryInfo`
- `PathEntryContext`、`FileItemResult`
- `OperationType`、`Operation`
- `SerialId`

#### shared/interfaces (通用接口)

**位置**: `shared/interfaces/`

**职责**: 定义跨domain的通用协议和抽象接口

**主要模块**:
- `task.py`: BaseTask协议（业务用例层）
- `processors/`: 处理器协议定义
  - `base.py`: 处理器基类定义（ItemProcessor、TaskProcessor）
  - `item.py`: Item级别处理器协议（Analyzer、Executor）
  - `task.py`: 任务级别处理器协议（Initializer、Finalizer）
  - `chain.py`: ProcessorChain处理器链（处理器执行层）

#### shared/utils (通用工具)

**位置**: `shared/utils/`

**职责**: 提供纯工具函数（无业务逻辑，无I/O操作）

**主要模块**:
- `file_utils.py`: 通用文件工具函数
  - `get_file_type()`: 判断文件类型
  - `generate_alternative_filename()`: 生成候选文件名路径，用于处理路径冲突
- `config_utils.py`: 配置验证工具函数
  - `validate_global_config()`: 验证全局配置

### 3. Infrastructure Layer (基础设施层)

**位置**: `src/j_file_kit/infrastructure/`

**职责**:
- 提供I/O操作（文件系统、数据库、网络等）
- 配置管理
- 日志记录
- 应用状态管理
- 实现domain定义的ports接口

**特点**:
- 依赖shared层（使用共享模型）
- 实现domain定义的ports接口（依赖倒置）
- 可替换实现（如文件系统操作可替换为云存储）

**主要模块**:
- `filesystem/`: 文件系统操作
  - `operations.py`: 文件操作封装（move_file、delete_file等）
  - `scanner.py`: 文件扫描操作（scan_directory_files）
- `persistence/`: 持久化（按领域划分）
  - `sqlite/`: SQLite数据库实现
    - `connection.py`: 数据库连接管理和表结构定义
    - `config/config_repository.py`: 配置仓储实现（实现AppConfigRepository）
    - `task/`: 任务仓储实现
      - `task_repository.py`: 任务仓储实现（实现TaskRepository）
      - `file_item_repository.py`: 文件处理结果仓储实现（实现FileItemRepository）
      - `file_processor_repository.py`: 文件处理操作仓储实现（实现FileProcessorRepository）
      - `task_repository_registry.py`: 任务仓储注册表实现（实现TaskRepositoryRegistry）
- `config/config.py`: 配置加载函数（load_config_from_db）
- `logging/logging_setup.py`: 结构化日志记录器配置
- `app_state.py`: 应用状态管理（AppState），管理全局状态

### 4. API Layer (HTTP接口层)

**位置**: `src/j_file_kit/api/`

**职责**:
- FastAPI应用实例和路由注册
- 异常处理
- 应用生命周期管理

**主要模块**:
- `app.py`: FastAPI应用实例，注册各个domain的路由，定义异常处理器

### Task、Pipeline、ProcessorChain 职责分工

- **Task (BaseTask)**: 业务用例层，定义"做什么"
  - 定义业务用例，组合处理器，创建并配置 Pipeline
  - 通过 `create_pipeline()` 方法组装 Pipeline
  - 通过 `run()` 方法执行任务
  - 位置：`app/file_task/service/jav_video_organizer.py`

- **Pipeline (FilePipeline)**: 流程协调层，定义"怎么做流程"
  - 协调处理流程（扫描 → 处理 → 汇总）
  - 管理任务生命周期（初始化 → 处理 → 终结）
  - 封装统计信息管理和结果持久化
  - 主要处理文件，目录清理是辅助功能
  - 位置：`app/file_task/pipelines/file/pipeline.py`

- **ProcessorChain**: 处理器执行层，定义"怎么执行处理器"
  - 管理处理器的注册和执行顺序
  - 区分 initializers、analyzers、executors、finalizers
  - 处理单个 item 的执行逻辑
  - 位置：`shared/interfaces/processors/chain.py`

- `processors/file/`: 文件处理相关的具体处理器实现
  - `analyzers/`: 分析器实现（FileClassifier、FileSerialIdExtractor、FileActionDecider等）
  - `executors.py`: 执行器实现（UnifiedFileExecutor、EmptyDirectoryExecutor）
  - `initializers.py`: 初始化器实现（TaskStatusInitializer、TaskConfigValidatorInitializer、TaskResourceInitializer等）
  - `finalizers.py`: 终结器实现（TaskStatisticsFinalizer）
  - 位置：`app/file_task/processors/file/`

## 依赖关系

```
┌─────────────┐
│     API     │  HTTP接口层（路由注册）
└──────┬──────┘
       │
       ├──→ ┌─────────────┐
       │    │    app/      │  应用层（Domain组织）
       │    │  ┌────────┐  │
       │    │  │app_config│ │  配置domain
       │    │  │file_task │ │  文件任务domain
       │    │  └────────┘  │
       │    └──────┬───────┘
       │           │
       │           ├──→ ┌──────────────┐
       │           │    │   shared/    │  共享层
       │           │    │  ┌────────┐  │
       │           │    │  │models  │  │  全局模型
       │           │    │  │interfaces│ │  通用接口
       │           │    │  │utils    │  │  通用工具
       │           │    │  └────────┘  │
       │           │    └──────┬───────┘
       │           │           │
       │           └───────────┼───────────┐
       │                       │           │
       │                       ↓           ↓
       │              ┌──────────────┐  ┌─────────────┐
       │              │   shared/    │  │infrastructure│  基础设施层
       │              │   models/    │  │（实现ports）│
       │              └──────────────┘  └─────────────┘
```

### 依赖规则

1. **shared/models/**: 无外部依赖（仅标准库、Pydantic），纯数据模型
2. **shared/interfaces/**: 依赖shared/models/（使用数据模型），使用TYPE_CHECKING避免循环依赖
3. **shared/utils/**: 依赖shared/models/（使用数据模型），无业务逻辑，纯工具函数
4. **app/{domain}/**: 依赖shared/、infrastructure/，可以依赖其他domain（通过shared层）
   - domain定义ports接口（Protocol）
   - service实现业务逻辑
   - api提供HTTP接口
5. **infrastructure/**: 依赖shared/models/，实现domain定义的ports接口（依赖倒置）
6. **api/**: 依赖app/（各个domain的api）、infrastructure/

## 设计原则

### 1. 单一职责原则
每个模块、类、函数都有明确的单一职责。

### 2. 依赖倒置原则
- domain定义ports接口（Protocol），infrastructure层实现这些接口
- domain依赖接口抽象，不依赖具体实现
- 通过依赖倒置实现domain与infrastructure的解耦

### 3. 分层隔离
- 各层之间通过明确的接口交互
- 避免跨层直接调用

### 4. 避免过度设计
- 只实现当前需要的功能
- 不预留不必要的扩展性
- 保持代码简洁

## 文件系统操作封装

所有文件系统I/O操作都封装在 `infrastructure/filesystem/` 中：

- **operations.py**: 提供基础文件操作函数
  - `move_file()`: 基础文件移动（直接移动，不处理冲突）
  - `move_file_with_conflict_resolution()`: 带冲突解决的文件移动
    - 先尝试直接移动，如果目标路径已存在，自动生成唯一路径并重试
    - 使用 `generate_alternative_filename()` 生成候选文件名（格式：`{原始stem}-jfk-{4个随机字符}{suffix}`）
    - 始终基于原始目标路径生成，避免路径越来越长
    - 最多重试10次
  - `delete_file()`: 删除文件
  - `create_directory()`: 创建目录
  - `delete_directory()`: 删除目录
  - `is_directory_empty()`: 检查目录是否为空
  - `read_text_file()`, `write_text_file()`, `append_text_file()`: 文本文件操作
  - `path_exists()`, `is_file()`, `is_directory()`: 路径检查

- **scanner.py**: 提供文件扫描操作
  - `scan_directory_files()`: 扫描目录下的所有文件

**路径冲突处理机制**:
- 纯函数 `shared/utils/file_utils.py::generate_alternative_filename()` 负责生成候选文件名（无I/O操作）
- `infrastructure/filesystem/operations.py::move_file_with_conflict_resolution()` 负责实际移动和重试逻辑
- 使用 `-jfk-xxxx` 后缀格式，避免与原始文件名冲突
- 如果输入路径已带后缀，会提取原始路径并基于原始路径生成新候选路径

这样设计的好处：
1. 统一文件操作接口
2. 职责分离：路径生成（纯函数）与文件操作（I/O）分离
3. 便于测试（可mock文件系统操作）
4. 便于未来扩展（如支持云存储）

## 配置管理

### 配置存储

配置系统使用 SQLite 数据库存储，不再使用 YAML 文件：

- **环境变量**: `J_FILE_KIT_BASE_DIR`（默认 `.app-data`）确定基础目录
- **固定目录结构**:
  - `{base_dir}/sqlite/j_file_kit.db`: 数据库文件
  - `{base_dir}/logs/`: 日志目录

### 数据库表结构

- **global_config**: 单行表，存储全局配置
  - `id`: 固定为 1（CHECK约束）
  - `scan_root`: TEXT字段，存储扫描根目录（单个路径字符串，空字符串表示未设置）
  - `updated_at`: 更新时间

- **task_configs**: 存储任务配置
  - `name`: 任务名称（主键）
  - `type`: 任务类型（file_organize、db_update等）
  - `enabled`: 是否启用
  - `config`: JSON对象，存储任务特定配置
  - `updated_at`: 更新时间

- **tasks**: 存储任务实例
  - `task_id`: 任务ID（主键）
  - `task_name`, `task_type`, `trigger_type`, `status`: 任务基本信息
  - `start_time`, `end_time`, `error_message`: 执行信息
  - `statistics`: JSON字段，存储统计信息（total_items、success_items等）

- **file_items**: 存储文件处理结果
  - `id`: 自增主键
  - `task_id`: 关联任务ID
  - `path`, `stem`: 文件路径和文件名（不含扩展名）
  - `file_type`: 文件类型（video/image/archive/misc），可为 NULL
  - `serial_id`: 番号，可为 NULL
  - `success`, `has_errors`, `has_warnings`, `was_skipped`: 处理状态
  - `error_message`, `total_duration_ms`, `processor_count`: 处理详情
  - `context_data`, `processor_results`: JSON字段，存储上下文和处理结果

- **file_operations**: 存储文件操作记录
  - `id`: 操作ID（主键）
  - `task_id`: 关联任务ID
  - `file_item_id`: 关联文件项ID（可选）
  - `timestamp`, `operation`: 操作时间和类型（只包含文件操作：MOVE、DELETE、RENAME）
  - `source_path`, `target_path`: 源路径和目标路径（展开为独立字段）
  - `file_type`, `serial_id`: 文件类型和番号（冗余字段，避免JOIN）

### 配置加载流程

1. 应用启动时，`AppState.__init__()` 创建 `SQLiteConnectionManager`
2. 连接管理器自动创建表结构（如果不存在）
3. `AppConfigRepository`（实现）检查配置表，如果为空则创建默认配置
4. `load_config_from_db()` 从数据库加载配置到内存
5. HTTP API 更新配置时，使用 `AppConfigRepository` 更新数据库，然后调用 `AppState.reload_config()` 重新加载

**注意**：
- 配置模型定义在 `app/app_config/domain.py`
- 配置仓储接口定义在 `app/app_config/ports.py`
- 配置仓储实现位于 `infrastructure/persistence/sqlite/config/config_repository.py`

## 数据流

### 任务执行流程

```
1. API接收请求（app/file_task/api.py）
   ↓
2. 创建任务实例（app/file_task/service/jav_video_organizer.py）
   ↓
3. task_manager启动任务（app/file_task/service/task_manager.py，在后台线程执行）
   ↓
4. pipeline协调执行（app/file_task/pipelines/file/pipeline.py，流程协调层）
   - Pipeline 通过 ProcessorChain 执行处理器
   ├── initializers: 前置处理（状态更新、配置验证、资源初始化）
   │   - 在非预览模式下执行，失败会阻止任务继续
   ↓
5. infrastructure/filesystem/scanner扫描文件
   ↓
6. processors处理item（app/file_task/processors/file/，文件等）
   - ProcessorChain 管理处理器的执行顺序
   ├── analyzers: 分析item（分类、提取番号等）
   ├── executors: 执行操作（使用infrastructure/filesystem）
   │   - 使用 move_file_with_conflict_resolution() 处理路径冲突
   ↓
7. 结果保存到数据库
   ├── file_items: 保存文件处理结果（infrastructure/persistence/sqlite/task/file_item_repository.py）
   ├── file_operations: 记录文件操作历史（infrastructure/persistence/sqlite/task/file_processor_repository.py）
   ↓
8. finalizers: 后处理（统计信息更新等）
   ├── 更新任务统计信息到数据库
   ├── 更新 TaskReport（仅用于日志记录）
   ↓
9. 任务完成，状态更新到数据库
```

### 数据查询流程

- API 查询任务状态时，从数据库的 `tasks` 表读取任务信息
- 统计信息（如 total_items）从 `file_items` 表通过 `FileItemRepository.get_statistics()` 查询
- `TaskReport` 仅用于 Pipeline 内部日志记录，不作为返回值

## 扩展指南

### 添加新的处理器

#### Item 级别处理器（Analyzer/Executor）

1. 在 `app/file_task/processors/file/` 中创建新的处理器类
2. 继承 `shared/interfaces/processors/` 中相应的基类（Analyzer 或 Executor）
3. 实现 `process()` 方法
4. 在任务中组合使用（在 `app/file_task/service/jav_video_organizer.py` 的 `create_pipeline()` 方法中）

#### 任务级别处理器（Initializer/Finalizer）

1. 在 `app/file_task/processors/file/` 中创建新的处理器类
2. 继承 `shared/interfaces/processors/` 中相应的基类（Initializer 或 Finalizer）
3. 实现 `initialize()` 或 `finalize()` 方法
4. 在任务的 `create_pipeline()` 方法中添加（Task 通过此方法创建并配置 Pipeline）：
   - Initializer: 使用 `pipeline.add_initializer()`
   - Finalizer: 使用 `pipeline.add_finalizer()`

**注意**:
- Initializer 在任务开始执行前运行，失败会阻止任务继续执行
- Finalizer 在任务完成后运行，失败不应影响任务完成状态
- 处理器位于domain层，可以依赖infrastructure层

### 添加新的任务类型

1. 在 `app/file_task/service/` 中创建新的任务类
2. 继承 `shared/interfaces/task.py` 中的 `BaseTask`
3. 实现 `run()` 方法
4. 在 `app/file_task/api.py` 中注册任务实例获取逻辑

### 添加新的Domain

1. 在 `app/` 目录下创建新的domain目录（如 `app/crawler_task/`）
2. 创建domain的基本结构：
   - `domain.py`: 领域模型
   - `config.py`: 领域专属配置（如果需要）
   - `schemas.py`: HTTP请求/响应模型
   - `ports.py`: 仓储接口定义
   - `service/`: 业务逻辑和用例实现
   - `api.py`: API路由
3. 在 `infrastructure/persistence/sqlite/` 下创建对应的仓储实现目录
4. 在 `api/app.py` 中注册新domain的路由

### 替换文件系统实现

如果需要支持其他文件系统（如云存储），只需：
1. 在 `infrastructure/filesystem/` 中创建新的实现
2. 保持接口一致
3. 通过依赖注入使用新实现

## 关键设计决策

### 1. 配置系统迁移到 SQLite

- **原因**: 统一数据存储，便于管理和查询
- **实现**: 使用 `AppConfigRepository` 管理配置，支持事务更新
- **优势**: 配置与任务数据统一存储，便于备份和迁移

### 2. 路径冲突处理机制

- **设计**: "先尝试后生成"模式，减少不必要的 I/O 检查
- **实现**: 
  - `generate_alternative_filename()`: 纯函数，生成候选文件名（无I/O）
  - `move_file_with_conflict_resolution()`: 实际移动和重试逻辑
- **后缀格式**: `-jfk-xxxx`（4个小写字母或数字），避免与原始文件名冲突
- **路径提取**: 如果输入路径已带后缀，提取原始路径并基于原始路径生成

### 3. TaskReport 仅用于内部日志

- **设计**: `TaskReport` 不再作为 `BaseTask.run()` 的返回值
- **原因**: 统一使用数据库中的 `statistics` JSON 字段作为单一数据源
- **使用**: Pipeline 内部使用 `TaskReport` 进行日志记录，数据持久化到数据库

### 4. 仓储模式（依赖倒置）

- **实现**: 使用仓储模式封装数据库操作，遵循依赖倒置原则
- **接口定义**: domain定义ports（Protocol），如 `app/app_config/ports.py`、`app/file_task/ports.py`
- **接口实现**: infrastructure实现这些接口，如 `infrastructure/persistence/sqlite/config/config_repository.py`、`infrastructure/persistence/sqlite/task/`
- **仓储**: `AppConfigRepository`、`TaskRepository`、`FileItemRepository`、`FileProcessorRepository`
- **优势**: 统一数据访问接口，便于测试和替换实现，domain不依赖具体实现

### 5. JSON 字段设计

- **设计**: 数据库表使用 JSON 字段存储灵活数据
- **优势**: 支持不同任务类型的特定数据结构，便于扩展
- **表**: `file_items`（使用具体字段）、`file_operations`（使用具体字段）、`tasks.statistics`、`task_configs.config`

