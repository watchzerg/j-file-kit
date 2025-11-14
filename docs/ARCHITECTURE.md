# 架构设计文档

## 概述

j-file-kit 采用分层架构设计，遵循领域驱动设计（DDD）原则，将代码分为领域层、服务层、基础设施层和接口层。

## 架构分层

### 1. Domain Layer (领域层)

**位置**: `src/j_file_kit/domain/`

**职责**:
- 定义业务领域模型和核心概念
- 定义处理器协议（Processor、Analyzer、Executor、Finalizer）
- 实现处理器具体逻辑（processors/）

**特点**:
- 无外部依赖（仅标准库和Pydantic）
- 纯业务逻辑，不涉及I/O操作
- 可独立测试

**主要模块**:
- `models.py`: 领域模型（ProcessingContext、TaskReport、SerialId等）
- `processor.py`: Processor协议定义和ProcessorChain
- `task.py`: BaseTask抽象基类
- `processors/`: 处理器实现
  - `analyzers.py`: 分析器（FileClassifier、SerialIdExtractor等）
  - `executors.py`: 执行器（UnifiedFileExecutor）
  - `finalizers.py`: 终结器（ReportGenerator）

### 2. Services Layer (服务层)

**位置**: `src/j_file_kit/services/`

**职责**:
- 编排领域对象，实现业务用例
- 协调多个领域对象的交互
- 管理业务流程

**特点**:
- 依赖domain层
- 不直接依赖infrastructure层（通过依赖注入）
- 包含业务编排逻辑

**主要模块**:
- `pipeline.py`: 管道协调器，协调文件扫描、处理器链执行和结果汇总
- `task_manager.py`: 任务管理器，管理任务的执行、状态跟踪和取消
- `scanner.py`: 文件扫描服务，提供文件目录扫描功能

### 3. Infrastructure Layer (基础设施层)

**位置**: `src/j_file_kit/infrastructure/`

**职责**:
- 提供I/O操作（文件系统、数据库、网络等）
- 配置管理
- 日志记录
- 应用状态管理

**特点**:
- 依赖domain层（实现持久化等）
- 可替换实现（如文件系统操作可替换为云存储）

**主要模块**:
- `filesystem/`: 文件系统操作
  - `operations.py`: 文件操作封装（move_file、delete_file、create_directory等）
  - `scanner.py`: 文件扫描操作（scan_directory_files）
- `persistence/`: 持久化
  - `db.py`: 数据库管理器（SQLite）
  - `transaction_log.py`: 事务日志记录器
- `config/`: 配置管理
  - `config.py`: 配置模型和加载器（YAML）
- `logging/`: 日志
  - `logger.py`: 结构化日志记录器（JSON Lines格式）
- `app_state.py`: 应用状态管理

### 4. API Layer (接口层)

**位置**: `src/j_file_kit/api/`

**职责**:
- HTTP接口适配
- 请求/响应模型转换
- 异常处理

**特点**:
- 依赖services层和infrastructure层
- 使用FastAPI框架

**主要模块**:
- `app.py`: FastAPI应用实例和异常处理器
- `routes.py`: 任务管理API路由
- `config_routes.py`: 配置管理API路由
- `models.py`: API请求/响应模型

### 5. Application Layer (应用层)

**位置**: `src/j_file_kit/tasks/`

**职责**:
- 实现具体的业务用例
- 组合使用processors实现完整任务流程

**特点**:
- 依赖domain层、services层和infrastructure层
- 负责组装和编排

**主要模块**:
- `video_organizer.py`: 视频文件整理任务实现

### 6. Utils (工具层)

**位置**: `src/j_file_kit/utils/`

**职责**:
- 提供纯工具函数（无业务逻辑）
- 无I/O操作

**主要模块**:
- `file_utils.py`: 文件工具函数（路径计算、类型判断等）
- `regex_patterns.py`: 正则表达式模式
- `filename_generation.py`: 文件名生成

## 依赖关系

```
┌─────────────┐
│     API     │  HTTP接口层
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   tasks/    │  应用层（用例实现）
└──────┬──────┘
       │
       ├──→ ┌─────────────┐
       │    │  services/  │  服务层（业务编排）
       │    └──────┬──────┘
       │           │
       │           ↓
       │    ┌─────────────┐
       │    │   domain/   │  领域层（业务模型+协议）
       │    └──────┬──────┘
       │           │
       └───────────┼───────────┐
                   │           │
                   ↓           ↓
         ┌─────────────────┐  ┌─────────────┐
         │ domain/         │  │infrastructure│  基础设施层
         │ processors/     │  └─────────────┘
         └─────────────────┘
```

### 依赖规则

1. **domain/**: 无外部依赖（仅标准库、Pydantic）
2. **domain/processors/**: 依赖domain/，可依赖utils/，通过依赖注入使用infrastructure/
3. **services/**: 依赖domain/，不直接依赖infrastructure/（通过依赖注入）
4. **tasks/**: 依赖domain/、domain/processors/、services/、infrastructure/
5. **api/**: 依赖services/、tasks/、infrastructure/
6. **utils/**: 无业务逻辑，纯工具函数

## 设计原则

### 1. 单一职责原则
每个模块、类、函数都有明确的单一职责。

### 2. 依赖倒置原则
- 领域层定义抽象，基础设施层实现具体细节
- 服务层依赖领域抽象，不依赖具体实现

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
  - `move_file()`: 移动文件
  - `delete_file()`: 删除文件
  - `create_directory()`: 创建目录
  - `read_text_file()`: 读取文本文件
  - `write_text_file()`: 写入文本文件
  - `append_text_file()`: 追加文本
  - `path_exists()`: 检查路径是否存在
  - `is_file()`: 检查是否为文件
  - `is_directory()`: 检查是否为目录

- **scanner.py**: 提供文件扫描操作
  - `scan_directory_files()`: 扫描目录下的所有文件

这样设计的好处：
1. 统一文件操作接口
2. 便于测试（可mock文件系统操作）
3. 便于未来扩展（如支持云存储）

## 数据流

### 任务执行流程

```
1. API接收请求
   ↓
2. tasks/创建任务实例
   ↓
3. services/task_manager启动任务
   ↓
4. services/pipeline协调执行
   ↓
5. services/scanner扫描文件
   ↓
6. domain/processors/处理文件
   ├── analyzers: 分析文件
   ├── executors: 执行操作（使用infrastructure/filesystem）
   └── finalizers: 后处理
   ↓
7. 生成报告并返回
```

## 扩展指南

### 添加新的处理器

1. 在 `domain/processors/` 中创建新的处理器类
2. 继承相应的基类（Analyzer/Executor/Finalizer）
3. 实现 `process()` 方法
4. 在任务中组合使用

### 添加新的任务类型

1. 在 `tasks/` 中创建新的任务类
2. 继承 `domain/task.py` 中的 `BaseTask`
3. 实现 `run()` 方法
4. 在 `api/routes.py` 中注册任务实例获取逻辑

### 替换文件系统实现

如果需要支持其他文件系统（如云存储），只需：
1. 在 `infrastructure/filesystem/` 中创建新的实现
2. 保持接口一致
3. 通过依赖注入使用新实现

