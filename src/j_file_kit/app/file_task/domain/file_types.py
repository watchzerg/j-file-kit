"""文件任务领域：路径项与按扩展名划分的文件类型枚举

用于目录扫描（PathEntryType）、JAV/Raw 管线中的扩展名分类与决策（FileType）。
应用层 analyzer、executor、pipeline 与 domain decisions 依赖本模块。
"""

from enum import StrEnum


class PathEntryType(StrEnum):
    """路径项类型枚举

    区分路径项是文件还是文件夹，用于目录扫描和遍历操作。
    """

    FILE = "file"
    DIRECTORY = "directory"


class FileType(StrEnum):
    """文件类型枚举

    用于区分不同类型的文件（视频、图片、字幕、压缩包、其他）。
    这是文件 domain 的核心概念，用于文件分类和处理决策。

    UNCLASSIFIED：尚未按扩展名分类时的占位（例如收件箱预删除命中后返回的 DeleteDecision），
    与扩展名归入的 MISC 区分。
    """

    VIDEO = "video"
    IMAGE = "image"
    SUBTITLE = "subtitle"
    ARCHIVE = "archive"
    MISC = "misc"
    UNCLASSIFIED = "unclassified"
