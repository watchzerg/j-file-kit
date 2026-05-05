"""按扩展名将收件箱文件归入 ``FileType``。

四类扩展名集合由 ``JavAnalyzeConfig`` 提供（管线从 ``organizer_defaults`` 注入）；
均不匹配则为 ``MISC``。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.domain.file_types import FileType


def classify_jav_file(path: Path, config: JavAnalyzeConfig) -> FileType:
    """根据扩展名判断文件类型（视频 / 图片 / 字幕 / 压缩 / 其它）。

    Args:
        path: 文件路径
        config: JAV 分析配置（含四类扩展名集合）

    Returns:
        ``FileType`` 枚举值
    """
    suffix = path.suffix.lower()

    if suffix in config.video_extensions:
        return FileType.VIDEO
    if suffix in config.image_extensions:
        return FileType.IMAGE
    if suffix in config.subtitle_extensions:
        return FileType.SUBTITLE
    if suffix in config.archive_extensions:
        return FileType.ARCHIVE
    return FileType.MISC
