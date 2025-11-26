"""通用枚举类型

定义跨领域使用的通用枚举类型。领域特定枚举已移至相关模型文件。
"""

from j_file_kit.shared.models.task import TaskStatus, TaskType, TriggerType

__all__ = ["TaskStatus", "TaskType", "TriggerType"]
