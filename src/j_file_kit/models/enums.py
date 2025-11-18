"""通用枚举类型

定义跨领域使用的通用枚举类型。领域特定枚举已移至相关模型文件。
"""

from __future__ import annotations

from enum import Enum


class FileType(str, Enum):
    """文件类型枚举"""

    VIDEO = "video"
    IMAGE = "image"
    ARCHIVE = "archive"
    MISC = "misc"
