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
  scan_roots:                                    # 扫描根目录列表
    - /path/to/your/files                       # 修改为你的文件目录
  log_dir: ./logs                               # 日志目录
  report_dir: ./reports                         # 报告目录

# 任务列表
tasks:
  - name: video_file_organizer
    type: file_organize
    enabled: true
    config:
      # 目标目录配置
      todo_non_vidpic_dir: /path/to/todo-non-vidpic  # 非视频图片文件目录
      todo_vidpic_dir: /path/to/todo-vidpic          # 无番号视频图片文件目录
      
      # 文件类型配置
      video_extensions: [.mp4, .avi, .mkv, .mov, .wmv, .flv, .webm]
      image_extensions: [.jpg, .jpeg, .png, .webp, .bmp, .gif, .tiff]
      
      # 可选配置
      dry_run: false
      backup: false
      max_file_size: 1073741824
      min_file_size: 1048576
```

### 3. 运行任务

#### 方式一：使用内置的视频文件整理器

```python
from j_file_kit.rules.video_organizer import VideoFileOrganizer

# 创建整理器
organizer = VideoFileOrganizer("config.yaml")

# 预览模式（推荐先运行）
preview_report = organizer.run_dry()
print(f"预览模式将处理 {preview_report.total_files} 个文件")

# 实际执行
report = organizer.run()
print(f"处理完成: 成功 {report.success_files}, 失败 {report.error_files}")
```

#### 方式二：使用管道 API

```python
from j_file_kit.core.pipeline import Pipeline
from j_file_kit.core.config import load_config
from j_file_kit.processors.analyzers import FileClassifier, SerialIdExtractor
from j_file_kit.processors.executors import FileRenamer, FileMover
from j_file_kit.processors.finalizers import ReportGenerator

# 加载配置
config = load_config("config.yaml")

# 创建管道
pipeline = Pipeline(config)

# 添加处理器
pipeline.add_analyzer(FileClassifier({".mp4", ".avi"}, {".jpg", ".png"}))
pipeline.add_analyzer(SerialIdExtractor())
pipeline.add_executor(FileRenamer(pipeline.transaction_log))
pipeline.add_executor(FileMover("/path/to/todo_vidpic", pipeline.transaction_log))
pipeline.add_finalizer(ReportGenerator("./reports", pipeline.report))

# 执行任务
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

from j_file_kit.core.models import ProcessingContext, ProcessorResult
from j_file_kit.core.processor import Analyzer

class CustomAnalyzer(Analyzer):
    """自定义分析器示例"""
    
    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """处理文件分析逻辑"""
        # 自定义分析逻辑
        if ctx.file_info.suffix == '.custom':
            ctx.custom_flag = True
            ctx.custom_data = {"processed": True}
            
        return ProcessorResult(
            status='success',
            message=f"Custom analyzer applied to {ctx.file_info.name}"
        )
```

### 自定义执行器

```python
from j_file_kit.core.models import ProcessingContext, ProcessorResult
from j_file_kit.core.processor import Executor

class CustomExecutor(Executor):
    """自定义执行器示例"""
    
    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """执行文件操作"""
        try:
            # 自定义操作逻辑
            if ctx.custom_flag:
                # 执行自定义操作
                pass
                
            return ProcessorResult(
                status='success',
                message=f"Custom operation completed for {ctx.file_info.name}"
            )
        except Exception as e:
            return ProcessorResult.error(f"Custom operation failed: {str(e)}")
```

## 📁 项目结构

```
j-file-kit/
├── 📦 src/
│   └── j_file_kit/              # 主包
│       ├── 🏗️ core/             # 核心抽象层
│       │   ├── models.py        # 数据模型
│       │   ├── config.py        # 配置模型和加载器
│       │   ├── scanner.py       # 文件扫描器
│       │   ├── pipeline.py      # 管道协调器
│       │   └── processor.py     # Processor 协议定义
│       ├── ⚙️ processors/       # 内置处理器
│       │   ├── analyzers.py     # 分析器
│       │   ├── executors.py     # 执行器
│       │   └── finalizers.py    # 终结器
│       ├── 🔧 rules/            # 用户扩展点和内置规则
│       │   └── video_organizer.py # 视频文件整理器
│       └── 🛠️ utils/            # 工具函数
├── 🧪 tests/                    # 测试套件
├── 📊 logs/                    # 日志输出目录
├── 📈 reports/                 # 报告输出目录
├── 📄 main.py                  # 主入口文件
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