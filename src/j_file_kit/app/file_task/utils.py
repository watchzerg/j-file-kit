"""文件任务工具函数

提供文件任务domain专用的工具函数，如文件类型判断等。
这些函数是文件domain的业务逻辑，不属于通用工具。
"""

from pathlib import Path

from j_file_kit.app.file_task.domain import FileType


def get_file_type(
    path: Path,
    video_exts: set[str],
    image_exts: set[str],
    archive_exts: set[str],
) -> FileType:
    """根据文件扩展名判断文件类型

    这是文件domain专用的工具函数，用于判断文件类型（视频/图片/压缩/其他）。
    设计意图：将文件类型判断逻辑封装在文件domain中，保持领域模型的完整性。

    Args:
        path: 文件路径
        video_exts: 视频文件扩展名集合
        image_exts: 图片文件扩展名集合
        archive_exts: 压缩文件扩展名集合

    Returns:
        文件类型枚举，无匹配时返回 MISC
    """
    suffix = path.suffix.lower()

    if suffix in video_exts:
        return FileType.VIDEO
    if suffix in image_exts:
        return FileType.IMAGE
    if suffix in archive_exts:
        return FileType.ARCHIVE
    return FileType.MISC
