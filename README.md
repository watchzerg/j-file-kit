# j-file-kit

[![Python](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Pydantic](https://img.shields.io/badge/pydantic-2.10+-green.svg)](https://pydantic.dev/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

基于 Python 的现代化文件管理工具，采用管道/过滤器架构设计，支持自定义规则的文件操作。专为处理大量文件而设计，特别适合视频文件整理、媒体库管理等场景。

## ✨ 核心特性

- **🏗️ 管道/过滤器架构**：Scanner → Analyzer → Executor → Finalizer，模块化设计
- **🔧 自定义规则扩展**：支持 Python 代码编写自定义处理规则
- **⚡ 流式处理**：边扫描边执行，支持百万级文件处理
- **🛡️ 错误容错**：跳过失败项，继续处理，最后生成完整报告
- **📝 事务日志**：记录所有操作，支持手动回滚
- **⚙️ 配置驱动**：YAML 配置文件，支持多任务管理
- **🎯 类型安全**：基于 Pydantic v2，端到端类型检查
- **📊 丰富报告**：详细的处理报告和统计信息

## 🚀 快速开始

### 📦 环境要求

- Python 3.14+
- uv (推荐) 或 pip

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd j-file-kit

# 使用 uv 安装（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 2. 创建配置文件

创建 `config.yaml` 文件：

```yaml
# 全局配置
global:
  scan_root: ./scan                              # 扫描根目录（修改为你的文件目录）
  log_dir: ./logs                                # 日志目录
  db_path: ./data/j_file_kit.db                  # 数据库文件路径

# 任务列表
tasks:
  - name: jav_video_organizer
    type: file_organize
    enabled: true
    config:
      # 目标目录配置
      organized_dir: ./organized                 # 整理后的视频图片存储目录（有番号）
      unorganized_dir: ./unorganized            # 无番号视频图片存储目录
      archive_dir: ./archives                    # 压缩文件存储目录
      misc_dir: ./misc                           # Misc文件存储目录
      
      # 文件类型配置
      video_extensions: [.mp4, .avi, .mkv, .mov, .wmv, .flv, .webm]
      image_extensions: [.jpg, .jpeg, .png, .webp, .bmp, .gif, .tiff]
      archive_extensions: [.zip, .rar, .7z, .tar, .gz, .bz2, .xz]
      
      # 删除规则配置（用于Misc文件）
      misc_file_delete_rules:
        keywords: [rarbg, sample, preview, temp]  # 文件名包含这些关键字的文件将被删除
        extensions: [.tmp, .temp, .bak, .old]    # 这些扩展名的文件将被删除
        max_size: 1048576                        # 小于等于此大小的文件将被删除（字节）
```

### 3. 运行任务

#### 方式一：使用HTTP API

```bash
# 启动HTTP服务
uv run python -m j_file_kit.main

# 或使用uvicorn直接运行
uvicorn j_file_kit.api.app:app --reload
```

然后通过HTTP API调用：

```bash
# 启动任务
curl -X POST http://localhost:8000/api/tasks/jav_video_organizer/start \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# 查看任务状态
curl http://localhost:8000/api/tasks/{task_id}

# 列出所有任务
curl http://localhost:8000/api/tasks
```

#### 方式二：使用内置的视频文件整理任务

```python
from j_file_kit.infrastructure.config.config import load_config
from j_file_kit.infrastructure.app_state import AppState
from j_file_kit.services.jav_video_organizer import JavVideoOrganizer

# 创建应用状态（会自动加载配置）
app_state = AppState()

# 创建任务实例
task = JavVideoOrganizer(app_state.config, app_state.log_dir)

# 启动任务（通过任务管理器）
task_id = app_state.task_manager.start_task(task, dry_run=True)

# 查看任务状态
task_model = app_state.task_manager.get_task(task_id)
print(f"任务状态: {task_model.status}")
```

#### 方式三：使用管道 API（高级用法）

```python
from j_file_kit.services.pipeline import PathEntryPipeline
from j_file_kit.infrastructure.config.config import load_config
from j_file_kit.infrastructure.persistence import OperationRepository, SQLiteConnectionManager
from j_file_kit.domain.processors.analyzers import FileClassifier, SerialIdExtractor

# 加载配置
config = load_config("config.yaml")

# 创建数据库连接和操作记录仓储
sqlite_conn = SQLiteConnectionManager(config.global_.db_path)
operation_repository = OperationRepository(sqlite_conn, task_id=1)  # task_id 需要从任务管理获取

# 创建管道
pipeline = PathEntryPipeline(config, "jav_video_organizer", operation_repository)

# 添加处理器
pipeline.add_analyzer(FileClassifier({".mp4", ".avi"}, {".jpg", ".png"}))
pipeline.add_analyzer(SerialIdExtractor())
pipeline.add_executor(pipeline.create_unified_executor())

# 执行任务（预览模式）
preview_report = pipeline.run(dry_run=True)
print(f"预览完成: {preview_report.total_items} 个item将被处理")

# 实际执行
report = pipeline.run()
print(f"任务完成: {report.success_rate:.2%} 成功率")
```

## 📋 番号规则说明

### 🎯 内置番号格式

j-file-kit 使用固定的内置番号正则表达式：
`(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\d{2,5})(?![0-9])`

### 📏 规则详情
- **字母部分**：2-5个英文字母（大小写都可以）
- **分隔符**：可选，支持 `-`、`_` 或无分隔符
- **数字部分**：2-5个数字
- **边界条件**：
  - 番号前面不能紧挨着字母
  - 番号后面不能紧挨着数字
- **输出格式**：统一标准化为 `字母-数字` 格式（大写字母）

## 🔧 扩展开发

### 自定义分析器

```python
from __future__ import annotations

from j_file_kit.domain.models import ProcessingContext, ProcessorResult
from j_file_kit.domain.processor import Analyzer

class CustomAnalyzer(Analyzer):
    """自定义分析器示例"""
    
    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """处理文件分析逻辑"""
        # 自定义分析逻辑
        if ctx.file_info.suffix == '.custom':
            ctx.custom_data["processed"] = True
            
        return ProcessorResult.success(
            f"Custom analyzer applied to {ctx.file_info.name}"
        )
```

### 自定义执行器

```python
from __future__ import annotations

from j_file_kit.domain.models import ProcessingContext, ProcessorResult
from j_file_kit.domain.processor import Executor

class CustomExecutor(Executor):
    """自定义执行器示例"""
    
    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """执行文件操作"""
        try:
            # 自定义操作逻辑
            if ctx.custom_data.get("processed"):
                # 执行自定义操作
                pass
                
            return ProcessorResult.success(
                f"Custom operation completed for {ctx.file_info.name}"
            )
        except Exception as e:
            return ProcessorResult.error(f"Custom operation failed: {str(e)}")
```

## 📐 架构设计

项目采用分层架构设计，遵循领域驱动设计（DDD）原则。详细架构说明请参考 [架构设计文档](docs/ARCHITECTURE.md)。

### 核心分层

- **domain/**: 领域层 - 业务模型、协议定义和处理器实现
- **services/**: 服务层 - 业务编排和流程协调
- **infrastructure/**: 基础设施层 - I/O操作、持久化、配置管理
- **api/**: HTTP接口层 - RESTful API适配
- **tasks/**: 应用层 - 具体任务实现
- **utils/**: 工具函数 - 纯函数工具

## 📁 项目结构

```
j-file-kit/
├── 📦 src/
│   └── j_file_kit/              # 主包
│       ├── 🏗️ domain/           # 领域层（业务模型和协议）
│       │   ├── models.py        # 领域模型
│       │   ├── processor.py     # Processor 协议定义
│       │   ├── task.py          # 任务抽象基类
│       │   └── processors/      # 处理器实现
│       │       ├── analyzers.py # 分析器
│       │       ├── executors.py # 执行器
│       │       └── finalizers.py # 终结器
│       ├── ⚙️ services/          # 服务层（业务编排）
│       │   ├── pipeline.py      # 管道协调器
│       │   ├── task_manager.py  # 任务管理器
│       │   └── scanner.py       # 文件扫描服务
│       ├── 🔧 infrastructure/   # 基础设施层（I/O和外部依赖）
│       │   ├── filesystem/      # 文件系统操作
│       │   │   ├── operations.py # 文件操作封装
│       │   │   └── scanner.py   # 文件扫描操作
│       │   ├── persistence/     # 持久化
│       │   │   ├── db.py        # 数据库管理
│       │   │   └── transaction_log.py # 事务日志
│       │   ├── config/          # 配置管理
│       │   │   └── config.py    # 配置模型和加载器
│       │   ├── logging/         # 日志
│       │   │   └── logger.py    # 结构化日志
│       │   └── app_state.py     # 应用状态管理
│       ├── 🌐 api/              # HTTP接口层
│       │   ├── app.py           # FastAPI应用
│       │   ├── routes.py        # API路由
│       │   └── models.py        # API请求/响应模型
│       ├── 📋 tasks/            # 应用层（具体任务实现）
│       │   └── jav_video_organizer.py # JAV视频文件整理任务
│       ├── 🛠️ utils/            # 工具函数
│       │   ├── file_utils.py    # 文件工具函数
│       │   ├── regex_patterns.py # 正则表达式模式
│       │   └── filename_generation.py # 文件名生成
│       └── main.py              # 主入口文件
├── 🧪 tests/                    # 测试套件
├── 📊 configs/                 # 配置文件目录
├── 📋 pyproject.toml           # 项目配置
└── 🔒 uv.lock                  # 依赖锁定文件
```

## 🛠️ 开发指南

### 🧪 测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 生成覆盖率报告
pytest --cov=j_file_kit --cov-report=html
```

### 🔍 代码质量

```bash
# 代码格式化
ruff format

# 代码检查
ruff check

# 类型检查
mypy src/j_file_kit/

# 运行所有检查
ruff check && mypy src/j_file_kit/ && pytest
```

### 📦 依赖管理

```bash
# 添加新依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name

# 更新依赖
uv lock --upgrade

# 同步环境
uv sync
```

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 贡献规范

- 遵循项目的代码风格和类型注解要求
- 添加适当的测试覆盖
- 更新相关文档
- 确保所有测试通过