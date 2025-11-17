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


class PathItemType(str, Enum):
    """路径项类型枚举

    区分路径项是文件还是文件夹，这是第一层分类。
    """

    FILE = "file"
    DIRECTORY = "directory"


class PathItemAction(str, Enum):
    """路径项动作类型枚举

    统一处理文件和文件夹的操作枚举，支持文件和文件夹的各种操作。
    """

    MOVE_TO_ORGANIZED = "move_to_organized"  # 移动到整理目录（B/ABCD/...）
    MOVE_TO_UNORGANIZED = "move_to_unorganized"  # 移动到无番号目录（C）
    MOVE_TO_ARCHIVE = "move_to_archive"  # 移动到压缩文件目录
    MOVE_TO_MISC = "move_to_misc"  # 移动到其他目录（D）
    DELETE = "delete"  # 删除文件
    DELETE_DIRECTORY = "delete_directory"  # 删除目录
    SKIP = "skip"  # 跳过处理

    @property
    def description(self) -> str:
        """获取动作的中文描述"""
        descriptions = {
            PathItemAction.MOVE_TO_ORGANIZED: "整理目录",
            PathItemAction.MOVE_TO_UNORGANIZED: "无番号目录",
            PathItemAction.MOVE_TO_ARCHIVE: "压缩文件目录",
            PathItemAction.MOVE_TO_MISC: "Misc文件目录",
            PathItemAction.DELETE: "删除",
            PathItemAction.DELETE_DIRECTORY: "删除目录",
            PathItemAction.SKIP: "跳过",
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


class OperationType(str, Enum):
    """操作类型枚举"""

    RENAME = "rename"
    MOVE = "move"
    DELETE = "delete"
    CREATE_DIR = "create_dir"
    DELETE_DIR = "delete_dir"
