# 架构设计文档

## 概述

j-file-kit 采用分层架构设计，遵循领域驱动设计（DDD）原则，将代码分为数据模型层、接口层、服务层、基础设施层和API层。

## 架构分层

### 1. Models Layer (数据模型层)

**位置**: `src/j_file_kit/models/`

**职责**:
- 定义业务领域模型和核心概念
- 定义数据结构和状态模型

**特点**:
- 无外部依赖（仅标准库和Pydantic）
- 纯数据模型，不涉及I/O操作
- 可独立测试

**主要模块**:
- `results.py`: 处理结果模型（ItemResult、FileItemResult、ProcessorResult）
  - `ItemResult`: Item处理结果基类，支持未来扩展不同类型的item（文件、爬虫数据等）
  - `FileItemResult`: 文件类型的item处理结果，继承ItemResult
- `task.py`: 任务模型（Task、TaskReport）
  - `Task`: 任务实例模型，存储在数据库中
  - `TaskReport`: 任务执行报告，仅用于内部日志记录，不作为返回值
- `config.py`: 配置数据模型（GlobalConfig、AppConfig、TaskConfig、JavVideoOrganizeConfig）
  - `GlobalConfig`: 全局配置模型，定义目录路径等全局设置
  - `AppConfig`: 应用级配置模型，包含全局配置和任务配置列表（配置聚合根）
  - `TaskConfig`: 任务配置模型，定义单个任务的配置
  - `JavVideoOrganizeConfig`: JAV视频文件整理任务特定配置模型
  - `create_default_global_config()`: 创建默认全局配置（单一数据源，被 AppConfigRepository 使用）
  - `create_default_task_configs()`: 创建默认任务配置（单一数据源，被 AppConfigRepository 使用）
- `value_objects.py`: 值对象（SerialId、FileInfo、DirectoryInfo）
- `contexts.py`: 上下文对象（ItemContext、FileContext）
- `enums.py`: 枚举类型（TaskStatus、TaskType、FileType、ProcessorStatus等）
- `exceptions.py`: 领域异常

### 2. Interfaces Layer (接口层)

**位置**: `src/j_file_kit/interfaces/`

**职责**:
- 定义所有协议和抽象接口
- 定义处理器协议（Processor、Analyzer、Executor、Initializer、Finalizer）
- 定义任务协议（BaseTask）

**特点**:
- 依赖models层（使用数据模型）
- 使用 Python 3.14+ 延迟注解（`from __future__ import annotations`）处理类型提示
- 通过架构设计避免循环依赖
- 只包含协议定义，不包含具体实现

**主要模块**:
- `processors/`: 处理器协议定义
  - `base.py`: 处理器基类定义（ItemProcessor、TaskProcessor）
  - `item.py`: Item级别处理器协议（Analyzer、Executor）
  - `task.py`: 任务级别处理器协议（Initializer、Finalizer）
  - `chain.py`: ProcessorChain处理器链（处理器执行层）
- `task.py`: BaseTask抽象基类协议（业务用例层）

### 3. Services Layer (服务层)

**位置**: `src/j_file_kit/services/`

**职责**:
- 编排领域对象，实现业务用例
- 协调多个领域对象的交互
- 管理业务流程
- 包含具体处理器实现和用例实现

**特点**:
- 依赖models层和interfaces层
- 可以依赖infrastructure层（服务层可以访问基础设施）
- 包含业务编排逻辑和具体实现

**主要模块**:
- `pipeline/file/`: 文件处理管道实现（流程协调层），包含 pipeline.py、statistics.py、utils.py，协调文件扫描、处理器链执行和结果汇总，主要处理文件，目录清理是辅助功能
- `tasks/file/`: 文件处理领域的任务用例实现（业务用例层），包含 jav_video_organizer.py
- `processors/file/`: 文件处理相关的处理器实现，包含 analyzers/、executors.py、initializers.py、finalizers.py
- `task_manager.py`: 任务管理器，管理任务的执行、状态跟踪和取消
- `config_service.py`: 配置服务，管理应用配置

**领域组织**:
- services 层按领域组织，文件相关实现位于 `file/` 子目录下
- pipeline、processors、tasks 三个模块保持结构一致性，都采用相同的领域组织方式
- 为未来添加 crawler 领域做准备

### Task、Pipeline、ProcessorChain 职责分工

- **Task (BaseTask)**: 业务用例层，定义"做什么"
  - 定义业务用例，组合处理器，创建并配置 Pipeline
  - 通过 `create_pipeline()` 方法组装 Pipeline
  - 通过 `run()` 方法执行任务

- **Pipeline (FilePipeline)**: 流程协调层，定义"怎么做流程"
  - 协调处理流程（扫描 → 处理 → 汇总）
  - 管理任务生命周期（初始化 → 处理 → 终结）
  - 封装统计信息管理和结果持久化
  - 主要处理文件，目录清理是辅助功能

- **ProcessorChain**: 处理器执行层，定义"怎么执行处理器"
  - 管理处理器的注册和执行顺序
  - 区分 initializers、analyzers、executors、finalizers
  - 处理单个 item 的执行逻辑

- `processors/file/`: 文件处理相关的具体处理器实现
  - `analyzers/`: 分析器实现（FileClassifier、FileSerialIdExtractor、FileActionDecider等）
  - `executors.py`: 执行器实现（UnifiedFileExecutor、EmptyDirectoryExecutor）
  - `initializers.py`: 初始化器实现（TaskStatusInitializer、TaskConfigValidatorInitializer、TaskResourceInitializer等）
  - `finalizers.py`: 终结器实现（TaskStatisticsFinalizer）

### 4. Infrastructure Layer (基础设施层)

**位置**: `src/j_file_kit/infrastructure/`

**职责**:
- 提供I/O操作（文件系统、数据库、网络等）
- 配置管理
- 日志记录
- 应用状态管理

**特点**:
- 依赖models层（实现持久化等）
- 可替换实现（如文件系统操作可替换为云存储）

**主要模块**:
- `filesystem/`: 文件系统操作
  - `operations.py`: 文件操作封装
    - `move_file()`: 基础文件移动
    - `move_file_with_conflict_resolution()`: 带冲突解决的文件移动（自动生成唯一路径）
    - `delete_file()`: 删除文件
    - `create_directory()`: 创建目录
    - `delete_directory()`: 删除目录
    - `path_exists()`, `is_file()`, `is_directory()`: 路径检查
    - 其他文件操作函数
  - `scanner.py`: 文件扫描操作（scan_directory_files）
- `persistence/`: 持久化
  - `sqlite/`: SQLite数据库实现
    - `connection.py`: 数据库连接管理和表结构定义（SQLiteConnectionManager）
    - `config_repository.py`: 应用配置仓储（AppConfigRepository），管理全局配置和任务配置
    - `task_repository.py`: 任务仓储（TaskRepository），管理任务实例
    - `file_item_repository.py`: 文件处理结果仓储（FileItemRepository），管理文件处理结果
    - `file_processor_repository.py`: 文件处理操作仓储（FileProcessorRepository），记录文件操作历史
  - 数据库表结构设计：
    - `global_config` 表：单行表，存储全局配置（scan_root）
    - `task_configs` 表：存储任务配置（name, type, enabled, config JSON）
    - `tasks` 表：存储任务实例（task_id, task_name, status, statistics JSON等）
    - `file_items` 表：使用具体字段存储文件信息（path, stem, file_type, serial_id等），专门存储文件处理结果，提升查询性能和索引效率
    - `file_operations` 表：使用具体字段存储文件操作信息（source_path, target_path, file_type, serial_id等），只记录文件操作，不记录目录操作
- `config/`: 配置加载
  - `config.py`: 配置加载函数
    - `load_config_from_db()`: 从SQLite数据库加载配置
    - 注意：配置模型和默认配置创建函数定义在 models/config.py 中
- `logging/`: 日志
  - `logger.py`: 结构化日志记录器（JSON Lines格式）
- `app_state.py`: 应用状态管理（AppState）
  - 管理全局状态：配置、任务管理器、数据库连接
  - 从环境变量 `J_FILE_KIT_BASE_DIR` 读取基础目录（默认 `.app-data`）
  - 固定目录结构：`{base_dir}/sqlite/j_file_kit.db`、`{base_dir}/logs/`

### 5. API Layer (HTTP接口层)

**位置**: `src/j_file_kit/api/`

**职责**:
- HTTP接口适配
- 请求/响应模型转换
- 异常处理

**特点**:
- 依赖services层、interfaces层和infrastructure层
- 使用FastAPI框架

**主要模块**:
- `app.py`: FastAPI应用实例和异常处理器
- `routes.py`: 任务管理API路由
- `config_routes.py`: 配置管理API路由
- `models.py`: API请求/响应模型

### 6. Utils (工具层)

**位置**: `src/j_file_kit/utils/`

**职责**:
- 提供纯工具函数（无业务逻辑）
- 无I/O操作

**主要模块**:
- `file_utils.py`: 通用文件工具函数（纯函数，无I/O操作，无业务逻辑）
  - `get_file_type()`: 判断文件类型
  - `generate_alternative_filename()`: 生成候选文件名路径，用于处理路径冲突（使用 `-jfk-xxxx` 后缀格式）
- `jav_utils.py`: JAV 领域工具函数
  - `generate_jav_filename()`: 根据番号生成新文件名
  - `generate_sorted_dir()`: 生成整理目录路径
  - `trim_separators()`: 去除字符串前后的分隔符
- `regex_patterns.py`: 正则表达式模式

## 依赖关系

```
┌─────────────┐
│     API     │  HTTP接口层
└──────┬──────┘
       │
       ├──→ ┌─────────────┐
       │    │  services/  │  服务层（业务编排+用例实现+处理器实现）
       │    └──────┬──────┘
       │           │
       │           ├──→ ┌──────────────┐
       │           │    │  interfaces/ │  接口层（协议定义）
       │           │    └──────┬──────┘
       │           │           │
       │           └───────────┼───────────┐
       │                       │           │
       │                       ↓           ↓
       │              ┌──────────────┐  ┌─────────────┐
       │              │    models/   │  │infrastructure│  基础设施层
       │              └──────────────┘  └─────────────┘
       │
       └──→ ┌─────────────┐
            │   utils/    │  工具层
            └─────────────┘
```

### 依赖规则

1. **models/**: 无外部依赖（仅标准库、Pydantic）
2. **interfaces/**: 依赖models/（使用数据模型），使用 Python 3.14+ 延迟注解处理类型提示，通过架构设计避免循环依赖
3. **services/**: 依赖models/、interfaces/、utils/、infrastructure/
4. **api/**: 依赖services/、interfaces/、infrastructure/
5. **utils/**: 依赖models/（使用数据模型），无业务逻辑，纯工具函数
6. **infrastructure/**: 依赖models/（实现持久化等）

## 设计原则

### 1. 单一职责原则
每个模块、类、函数都有明确的单一职责。

### 2. 依赖倒置原则
- 接口层定义抽象，基础设施层和服务层实现具体细节
- 服务层依赖接口抽象，不依赖具体实现

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
- 纯函数 `utils/file_utils.py::generate_alternative_filename()` 负责生成候选文件名（无I/O操作）
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
3. `AppConfigRepository` 检查配置表，如果为空则创建默认配置
4. `load_config_from_db()` 从数据库加载配置到内存
5. HTTP API 更新配置时，使用 `AppConfigRepository` 更新数据库，然后调用 `AppState.reload_config()` 重新加载

## 数据流

### 任务执行流程

```
1. API接收请求
   ↓
2. tasks/创建任务实例
   ↓
3. services/task_manager启动任务（在后台线程执行）
   ↓
4. services/pipeline协调执行（流程协调层）
   - Pipeline 通过 ProcessorChain 执行处理器
   ├── initializers: 前置处理（状态更新、配置验证、资源初始化）
   │   - 在非预览模式下执行，失败会阻止任务继续
   ↓
5. infrastructure/filesystem/scanner扫描文件
   ↓
6. services/processors/处理item（文件等）
   - ProcessorChain 管理处理器的执行顺序
   ├── analyzers: 分析item（分类、提取番号等）
   ├── executors: 执行操作（使用infrastructure/filesystem）
   │   - 使用 move_file_with_conflict_resolution() 处理路径冲突
   ↓
7. 结果保存到数据库
   ├── file_items: 保存文件处理结果
   ├── file_operations: 记录文件操作历史
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

1. 在 `services/processors/` 中创建新的处理器类
2. 继承 `interfaces/processors/` 中相应的基类（Analyzer 或 Executor）
3. 实现 `process()` 方法
4. 在任务中组合使用

#### 任务级别处理器（Initializer/Finalizer）

1. 在 `services/processors/` 中创建新的处理器类
2. 继承 `interfaces/processors/` 中相应的基类（Initializer 或 Finalizer）
3. 实现 `initialize()` 或 `finalize()` 方法
4. 在任务的 `create_pipeline()` 方法中添加（Task 通过此方法创建并配置 Pipeline）：
   - Initializer: 使用 `pipeline.add_initializer()`
   - Finalizer: 使用 `pipeline.add_finalizer()`

**注意**:
- Initializer 在任务开始执行前运行，失败会阻止任务继续执行
- Finalizer 在任务完成后运行，失败不应影响任务完成状态
- 处理器位于services层，可以依赖infrastructure层

### 添加新的任务类型

1. 在 `services/` 中创建新的任务类
2. 继承 `interfaces/task.py` 中的 `BaseTask`
3. 实现 `run()` 方法
4. 在 `api/routes.py` 中注册任务实例获取逻辑

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

### 4. 仓储模式

- **实现**: 使用仓储模式封装数据库操作
- **仓储**: `AppConfigRepository`、`TaskRepository`、`FileItemRepository`、`FileProcessorRepository`
- **优势**: 统一数据访问接口，便于测试和替换实现

### 5. JSON 字段设计

- **设计**: 数据库表使用 JSON 字段存储灵活数据
- **优势**: 支持不同任务类型的特定数据结构，便于扩展
- **表**: `file_items`（使用具体字段）、`file_operations`（使用具体字段）、`tasks.statistics`、`task_configs.config`

