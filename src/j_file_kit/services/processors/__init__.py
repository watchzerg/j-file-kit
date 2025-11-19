"""处理器实现

包含文件处理相关的具体处理器实现。
这些处理器位于服务层，可以依赖infrastructure层。
"""

from .analyzers import (
    FileActionDecider,
    FileClassifier,
    FileSerialIdExtractor,
    MiscFileDeleteAnalyzer,
    MiscFileSizeAnalyzer,
)
from .executors import FileEmptyDirectoryExecutor, UnifiedFileExecutor
from .finalizers import FileTaskStatisticsFinalizer
from .initializers import (
    FileConfigValidatorInitializer,
    FileResourceInitializer,
    FileTaskStatusInitializer,
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
    "FileEmptyDirectoryExecutor",
    # Initializers
    "FileTaskStatusInitializer",
    "FileConfigValidatorInitializer",
    "FileResourceInitializer",
    # Finalizers
    "FileTaskStatisticsFinalizer",
]
