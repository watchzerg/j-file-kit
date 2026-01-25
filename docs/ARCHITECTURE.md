# 架构设计文档

## 概述

j-file-kit 采用 DDD 架构，按业务领域组织代码。每个模块内部分为 domain（领域核心）和 application（应用编排）两层。遵循依赖倒置：domain 定义 ports 接口，infrastructure 实现接口。

## 目录结构

```
src/j_file_kit/
├── app/                          # 业务领域模块
│   ├── global_config/            # 全局配置（业务目录路径）
│   ├── task_config/              # 任务配置基础设施（模型、接口）
│   ├── task/                     # 任务调度协议（TaskRunner、TaskRepository）
│   └── file_task/                # 文件处理任务（扫描、分析、执行）
├── shared/utils/                 # 跨领域工具（文件 I/O、日志）
├── infrastructure/               # 有状态 I/O 实现
│   ├── persistence/sqlite/       # SQLite 仓储实现
│   ├── config/                   # ConfigManager 实现
│   └── task/                     # TaskManager 调度器
└── api/                          # FastAPI 应用入口
    ├── app.py                    # 路由注册、生命周期
    └── app_state.py              # Composition Root（组装依赖）
```

### 模块内部结构

```
app/<module>/
├── domain/
│   ├── models.py                 # 实体、值对象、枚举
│   ├── ports.py                  # 仓储接口（Protocol）
│   ├── exceptions.py             # 领域异常
│   └── constants.py              # 类型常量（如 task_type）
└── application/
    ├── schemas.py                # 请求/响应 DTO
    ├── services.py               # 业务逻辑编排
    └── config.py                 # 任务配置模型
```

### 运行时目录

```
{base_dir}/                       # 默认 .app-data，可通过 J_FILE_KIT_BASE_DIR 覆盖
├── sqlite/j_file_kit.db          # SQLite 数据库
└── logs/{task_name}_{task_id}.jsonl  # 任务日志（JSON Lines）
```

**初始化流程**：`lifespan` → 创建目录 → SQLite 连接 → schema 初始化 → 默认配置初始化

## 依赖规则

```
API Layer  ──────────────────────────────────────────────────────────────
    │                 （路由、异常处理、生命周期）
    ↓
App Layer  ──────────────────────────────────────────────────────────────
    │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │   │global_config│  │    task     │←─│  file_task  │
    │   │task_config  │  │  (protocol) │  │  (concrete) │
    │   └─────────────┘  └─────────────┘  └─────────────┘
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

**模块间依赖**：
- `file_task` → `task`（使用 TaskRunner 协议）
- `file_task` → `global_config`/`task_config`（读取配置）
- `global_config` ↔ `task_config`（相互独立）

## 核心设计

### Task 执行模型

| 组件 | 职责 |
|------|------|
| **TaskRunner** (Protocol) | 定义"做什么"，业务用例入口 |
| **TaskManager** | 任务调度（创建/执行/取消），并发控制（单任务） |
| **Pipeline** | 流程协调：扫描 → 分析 → 执行 |
| **Analyzer** | 分析文件，返回 Decision |
| **Executor** | 根据 Decision 执行操作 |

**执行流程**：
```
API 请求 → TaskManager.start_task() → 后台线程执行
    → TaskRunner.run() → Pipeline 协调
        → scan → analyze (Decision) → execute → 持久化
    → 更新任务状态
```

### Decision 模式

分离"分析"和"执行"，支持 dry_run 预览：
- `MoveDecision`：移动文件
- `DeleteDecision`：删除文件
- `SkipDecision`：跳过

### 配置管理

- **GlobalConfig**：应用级配置（业务目录路径）
- **TaskConfig**：按 task_type 区分的任务配置（JSON 存储）
- **ConfigManager**：启动时加载全局配置，任务配置按需懒加载并缓存

### 依赖注入策略

| 类型 | 方式 | 原因 |
|------|------|------|
| 数据库 | ports 注入 | 可替换、需事务测试 |
| 文件系统 | 直接依赖 shared/utils | API 稳定、临时目录可测 |
| 日志 | 直接依赖 shared/utils | API 稳定、loguru 原生支持 |

### Repository 参数化

Repository 方法接收 `task_id` 参数（而非构造时绑定），支持单例复用：
```python
file_item_repository.save_file_item(task_id=123, item=...)
```

## 数据存储

| 表 | 用途 |
|---|---|
| `config_global` | 全局配置 |
| `config_task` | 任务配置（按 type 区分） |
| `tasks` | 任务实例（状态、统计） |
| `file_items` | 文件处理结果 |
| `file_operations` | 文件操作历史 |

## 扩展指南

### 添加新任务类型

1. 在 `app/file_task/application/` 创建任务类，实现 `TaskRunner` 协议
2. 定义任务类型常量（`domain/constants.py`）
3. 定义配置 schema（`application/config_schemas.py`）
4. 在 `api.py` 注册端点，组装依赖

### 添加新 Domain

1. 创建 `app/<domain>/domain/`（models、ports）
2. 创建 `app/<domain>/application/`（schemas、services）
3. 创建 `api.py` 路由
4. 在 `infrastructure/persistence/sqlite/` 实现仓储
5. 在 `api/app.py` 注册路由

## 关键决策

1. **Feature-First**：按业务功能划分模块
2. **SQLite 统一存储**：便于管理和备份
3. **TaskRunner 协议**：解耦调度与具体任务
4. **Decision 模式**：分析/执行分离，支持预览
5. **单实例部署**：TaskManager 的单任务约束基于此假设
