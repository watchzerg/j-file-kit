"""文件处理相关的处理器实现

包含文件处理任务使用的所有处理器：分析器、执行器、初始化器、终结器。
这些处理器位于服务层，可以依赖infrastructure层。
"""

from .analyzers import (
    FileActionDecider,
    FileClassifier,
    FileSerialIdExtractor,
    MiscFileDeleteAnalyzer,
    MiscFileSizeAnalyzer,
)
from .executors import EmptyDirectoryExecutor, UnifiedFileExecutor
from .finalizers import TaskStatisticsFinalizer
from .initializers import (
    TaskConfigValidatorInitializer,
    TaskResourceInitializer,
    TaskStatusInitializer,
)

__all__ = [
    # Analyzers
    "FileClassifier",
    "FileSerialIdExtractor",
    "MiscFileSizeAnalyzer",
    "MiscFileDeleteAnalyzer",
    "FileActionDecider",
    # Executors
    "UnifiedFileExecutor",
    "EmptyDirectoryExecutor",
    # Initializers
    "TaskStatusInitializer",
    "TaskConfigValidatorInitializer",
    "TaskResourceInitializer",
    # Finalizers
    "TaskStatisticsFinalizer",
]
