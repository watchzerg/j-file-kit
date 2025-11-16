"""领域枚举类型

定义所有领域相关的枚举类型。
"""

from __future__ import annotations

from enum import Enum


class ProcessorStatus(str, Enum):
    """处理器状态枚举"""

    SUCCESS = "success"
    ERROR = "error"
    SKIP = "skip"
    WARNING = "warning"


class FileType(str, Enum):
    """文件类型枚举"""

    VIDEO = "video"
    IMAGE = "image"
    ARCHIVE = "archive"
    MISC = "misc"


class FileAction(str, Enum):
    """文件动作类型枚举"""

    MOVE_TO_ORGANIZED = "move_to_organized"  # 移动到整理目录（B/ABCD/...）
    MOVE_TO_UNORGANIZED = "move_to_unorganized"  # 移动到无番号目录（C）
    MOVE_TO_ARCHIVE = "move_to_archive"  # 移动到压缩文件目录
    MOVE_TO_MISC = "move_to_misc"  # 移动到其他目录（D）
    DELETE = "delete"  # 删除文件
    SKIP = "skip"  # 跳过处理

    @property
    def description(self) -> str:
        """获取动作的中文描述"""
        descriptions = {
            FileAction.MOVE_TO_ORGANIZED: "整理目录",
            FileAction.MOVE_TO_UNORGANIZED: "无番号目录",
            FileAction.MOVE_TO_ARCHIVE: "压缩文件目录",
            FileAction.MOVE_TO_MISC: "Misc文件目录",
            FileAction.DELETE: "删除",
            FileAction.SKIP: "跳过",
        }
        return descriptions.get(self, self.value)


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型枚举"""

    VIDEO_ORGANIZER = "video_organizer"


class TriggerType(str, Enum):
    """触发类型枚举"""

    MANUAL = "manual"
    AUTO = "auto"
