"""领域模型包

定义文件处理过程中的所有数据结构和状态。
包含领域实体、值对象和领域异常。
"""

from .contexts import FileContext, ItemContext
from .enums import (
    FileAction,
    FileType,
    ProcessorStatus,
    TaskStatus,
    TaskType,
    TriggerType,
)
from .exceptions import (
    TaskAlreadyRunningError,
    TaskCancelledError,
    TaskError,
    TaskNotFoundError,
)
from .results import FileItemResult, ItemResult, ProcessorResult
from .task import Task, TaskReport
from .value_objects import DirectoryInfo, FileInfo, SerialId

__all__ = [
    # 枚举
    "ProcessorStatus",
    "FileType",
    "FileAction",
    "TaskStatus",
    "TaskType",
    "TriggerType",
    # 值对象
    "SerialId",
    "FileInfo",
    "DirectoryInfo",
    # 上下文
    "ItemContext",
    "FileContext",
    # 结果
    "ProcessorResult",
    "ItemResult",
    "FileItemResult",
    # 任务
    "Task",
    "TaskReport",
    # 异常
    "TaskError",
    "TaskNotFoundError",
    "TaskAlreadyRunningError",
    "TaskCancelledError",
]
