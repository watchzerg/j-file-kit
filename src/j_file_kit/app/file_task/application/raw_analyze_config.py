"""Raw 纯分析阶段配置：管线阶段使用的路径 + 扩展名归集 DTO。

归宿路径均从 ``workspace_root`` 与代码约定子目录派生，由 ``RawFileOrganizer`` 注入；
不含收件箱路径字段，扫描根由管线上下文单独持有。
"""

from pathlib import Path

from pydantic import BaseModel, Field


class RawAnalyzeConfig(BaseModel):
    """Raw 分析阶段配置（不含收件箱路径）。

    `RawFilePipeline` 阶段 1 使用 ``files_misc``；阶段 2 使用 ``folders_to_delete`` 及分类归宿；
    阶段 3 将 ``files_misc`` 第一层按规则迁入各 ``files_*`` / ``files_video_*``。
    """

    folders_to_delete: Path = Field(
        ..., description="阶段 2.1：关键字目录迁入（人工确认删除）"
    )
    folders_video: Path = Field(..., description="视频目录")
    folders_compressed: Path = Field(..., description="压缩文件目录")
    folders_pic: Path = Field(..., description="图片目录")
    folders_audio: Path = Field(..., description="音频目录")
    folders_misc: Path = Field(..., description="无法自动分类的目录级杂项")
    files_to_delete: Path = Field(..., description="阶段 3.0 junk stem 迁入目录")
    files_video_jav: Path = Field(..., description="JAV 视频文件目录")
    files_video_us: Path = Field(..., description="US 视频文件目录")
    files_video_jav_vr: Path = Field(..., description="JAV VR 视频文件目录")
    files_video_us_vr: Path = Field(..., description="US VR 视频文件目录")
    files_video_movie: Path = Field(..., description="电影文件目录")
    files_video_misc: Path = Field(..., description="杂项视频文件目录")
    files_compressed: Path = Field(..., description="压缩文件目录")
    files_pic: Path = Field(..., description="图片文件目录")
    files_audio: Path = Field(..., description="音频文件目录")
    files_misc: Path = Field(..., description="无法自动分类的文件级杂项")

    video_extensions: set[str] = Field(..., description="视频扩展名（带点）")
    image_extensions: set[str] = Field(..., description="图片扩展名（带点）")
    subtitle_extensions: set[str] = Field(..., description="字幕扩展名（带点）")
    archive_extensions: set[str] = Field(..., description="压缩包扩展名（带点）")
    audio_extensions: set[str] = Field(
        ...,
        description="音频扩展名（带点；来自 organizer_defaults.music）",
    )
