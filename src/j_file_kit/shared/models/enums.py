"""通用枚举类型

定义跨领域使用的通用枚举类型。

设计意图：
- PathEntryType：用于区分文件系统路径项类型（文件/目录），是通用的文件系统概念
"""

from enum import Enum


class PathEntryType(str, Enum):
    """路径项类型枚举

    区分路径项是文件还是文件夹。
    这是通用的文件系统概念，用于文件扫描和遍历操作。
    """

    FILE = "file"
    DIRECTORY = "directory"
