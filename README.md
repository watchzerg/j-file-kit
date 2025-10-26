# j-file-kit

基于 Python 的文件管理工具，支持自定义规则的文件操作。

## 项目概述

j-file-kit 是一个灵活的文件管理工具，专为处理大量文件而设计。它使用管道/过滤器架构，支持文件分类、重命名、移动等操作，特别适合视频文件整理等场景。

### 核心特性

- **管道/过滤器架构**：Scanner → Analyzer → Executor → Finalizer
- **自定义规则扩展**：支持 Python 代码编写自定义处理规则
- **流式处理**：边扫描边执行，支持百万级文件处理
- **错误容错**：跳过失败项，继续处理，最后生成完整报告
- **事务日志**：记录所有操作，支持手动回滚
- **配置驱动**：YAML 配置文件，支持多任务管理

## 核心架构

### 管道/过滤器模式

```
Scanner → [Analyzer₁ → Analyzer₂ → Executor₁ → Executor₂ → ...] → Finalizers → Report
         └────────────── ProcessingContext 贯穿传递 ──────────────┘
```

- **Scanner**: 遍历文件目录，生成 `FileInfo` 流
- **Analyzer**: 分析文件，填充 `ProcessingContext`（如分类、番号提取）
- **Executor**: 根据 Context 执行操作（如重命名、移动）
- **Finalizer**: 全局后处理（如清理空目录）
- **Pipeline**: 协调流程，支持短路机制

### 数据模型

- `FileInfo`: 文件基础信息（路径、扩展名）
- `ProcessingContext`: 处理上下文（携带分析结果和中间状态）
- `ProcessorResult`: 单个处理器的处理结果
- `TaskResult`: 单个文件的完整处理结果
- `TaskReport`: 任务汇总报告

## 典型使用场景

### 视频文件整理

对指定目录进行视频/图片文件的番号提取和整理：

1. **分类处理**：
   - 视频/图片文件 → 进入番号提取流程
   - 非视频/图片文件 → 移动到 `todo-non-vidpic/` 目录

2. **番号提取与重命名**：
   - 番号格式：`[A-Za-z]{2,5}-\d+`（如 `ABCDE-0001`）
   - 提取番号到文件名开头，原位置替换为 `-serialId-`
   - 重名处理：追加后缀 `-Dup1234`（4位随机数）

3. **后续分类**：
   - 有番号的文件：保持在当前目录
   - 无番号的文件：移动到 `todo-vidpic/` 目录

4. **清理空目录**：处理完成后删除所有空目录

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv 安装依赖
uv sync
```

### 2. 配置任务

复制配置文件模板：

```bash
cp configs/task_config.yaml.example configs/task_config.yaml
```

编辑 `configs/task_config.yaml`：

```yaml
# 全局配置
global:
  scan_root: /path/to/your/files
  log_dir: ./logs
  report_dir: ./reports
  
# 任务列表
tasks:
  - name: video_file_organizer
    type: file_organize
    enabled: true
    config:
      todo_non_vidpic_dir: /path/to/todo-non-vidpic
      todo_vidpic_dir: /path/to/todo-vidpic
      video_extensions: [.mp4, .avi, .mkv, .mov]
      image_extensions: [.jpg, .jpeg, .png, .webp]
      serial_id_pattern: "[A-Za-z]{2,5}-\\d+"
```

### 3. 运行任务

```python
from jfk.core.pipeline import Pipeline
from jfk.core.config import load_config

# 加载配置
config = load_config("configs/task_config.yaml")

# 创建管道
pipeline = Pipeline(config)

# 执行任务
pipeline.run()
```

## 扩展开发

### 自定义规则

在 `jfk/rules/` 目录下编写 Python 模块：

```python
from jfk.core.models import ProcessingContext, ProcessorResult
from jfk.core.processor import Analyzer

class MyCustomRule(Analyzer):
    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        # 自定义分析逻辑
        if ctx.file_info.path.suffix == '.custom':
            ctx.custom_flag = True
        return ProcessorResult(status='success')
```

### 注册规则

```python
from jfk.rules.my_custom_rule import MyCustomRule

pipeline = Pipeline(config)
pipeline.add_analyzer(MyCustomRule())
pipeline.run()
```

## 项目结构

```
j-file-kit/
├── jfk/                          # 主包
│   ├── core/                     # 核心抽象
│   │   ├── models.py            # 数据模型
│   │   ├── config.py            # 配置模型
│   │   ├── scanner.py           # 文件扫描器
│   │   ├── pipeline.py          # 管道协调器
│   │   └── processor.py         # Processor 协议
│   ├── processors/              # 内置处理器
│   │   ├── analyzers.py         # 分析器
│   │   ├── executors.py         # 执行器
│   │   └── finalizers.py        # 终结器
│   ├── rules/                   # 用户扩展点
│   └── utils/                   # 工具函数
├── configs/                     # 配置文件
├── tests/                       # 测试
├── examples/                    # 使用示例
├── logs/                        # 日志输出
└── reports/                    # 报告输出
```

## 开发指南

### 测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=jfk --cov-report=html
```

### 代码质量

```bash
# 代码格式化
ruff format

# 代码检查
ruff check

# 类型检查
mypy jfk/
```

## 未来规划

- **Web UI**：基于 FastAPI 的 HTTP 接口
- **数据库持久化**：PostgreSQL 支持，断点续扫
- **Docker 部署**：支持 Unraid 系统部署
- **更多处理器**：支持更多文件操作类型

## 许可证

MIT License
