"""数据模型包

定义文件处理过程中的所有数据结构和状态。
包含领域实体、值对象和领域异常。
"""

from .contexts import ItemContext, PathItemContext
from .enums import (
    FileType,
    OperationType,
    PathItemAction,
    PathItemType,
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
from .operations import Operation
from .results import FileItemResult, ItemResult, ProcessorResult
from .task import Task, TaskReport
from .value_objects import PathItemInfo, SerialId

__all__ = [
    # 枚举
    "ProcessorStatus",
    "FileType",
    "PathItemType",
    "PathItemAction",
    "TaskStatus",
    "TaskType",
    "TriggerType",
    "OperationType",
    # 值对象
    "SerialId",
    "PathItemInfo",
    # 上下文
    "ItemContext",
    "PathItemContext",
    # 结果
    "ProcessorResult",
    "ItemResult",
    "FileItemResult",
    # 任务
    "Task",
    "TaskReport",
    # 操作
    "Operation",
    # 异常
    "TaskError",
    "TaskNotFoundError",
    "TaskAlreadyRunningError",
    "TaskCancelledError",
]
