"""通用枚举类型

定义跨领域使用的通用枚举类型。领域特定枚举已移至相关模型文件。
"""

from enum import Enum

from j_file_kit.shared.models.task import TaskStatus, TaskType, TriggerType

__all__ = ["FileType", "TaskStatus", "TaskType", "TriggerType"]


class FileType(str, Enum):
    """文件类型枚举"""

    VIDEO = "video"
    IMAGE = "image"
    ARCHIVE = "archive"
    MISC = "misc"
