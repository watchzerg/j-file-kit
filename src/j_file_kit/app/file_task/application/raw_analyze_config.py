"""Raw 纯分析阶段配置：管线阶段使用的路径 + 扩展名归集 DTO。

不含 `inbox_dir`，与 `RawFileOrganizeConfig` 分离是为了让 `analyze_raw_*` 与阶段函数签名保持稳定，
任务组织器负责从任务配置裁剪出分析所需字段。
"""

from pathlib import Path

from pydantic import BaseModel, Field


class RawAnalyzeConfig(BaseModel):
    """Raw 分析阶段配置（不含 `inbox_dir`）。

    由 `RawFileOrganizer` 从任务配置注入各归宿路径与扩展名集合。
    当前 `RawFilePipeline` 阶段 1 使用 `files_misc`；阶段 2 使用 `folders_to_delete`；
    扩展名驱动的分流与其它 `analyze_raw_*` 规则后续迭代填充。
    """

    folders_to_delete: Path | None = Field(
        default=None,
        description="待人工确认的疑似删除目录（Raw 阶段 2.1）",
    )
    folders_video: Path | None = Field(default=None, description="视频目录")
    folders_compressed: Path | None = Field(default=None, description="压缩文件目录")
    folders_pic: Path | None = Field(default=None, description="图片目录")
    folders_audio: Path | None = Field(default=None, description="音频目录")
    folders_misc: Path | None = Field(
        default=None,
        description="无法自动分类的杂项目录",
    )
    files_video_jav: Path | None = Field(default=None, description="JAV 视频文件目录")
    files_video_us: Path | None = Field(default=None, description="US 视频文件目录")
    files_video_vr: Path | None = Field(default=None, description="VR 视频文件目录")
    files_video_movie: Path | None = Field(default=None, description="电影文件目录")
    files_video_misc: Path | None = Field(default=None, description="杂项视频文件目录")
    files_compressed: Path | None = Field(default=None, description="压缩文件目录")
    files_pic: Path | None = Field(default=None, description="图片文件目录")
    files_audio: Path | None = Field(default=None, description="音频文件目录")
    files_misc: Path | None = Field(
        default=None,
        description="无法自动分类的杂项文件目录",
    )

    video_extensions: set[str] = Field(..., description="视频扩展名（带点）")
    image_extensions: set[str] = Field(..., description="图片扩展名（带点）")
    subtitle_extensions: set[str] = Field(..., description="字幕扩展名（带点）")
    archive_extensions: set[str] = Field(..., description="压缩包扩展名（带点）")
    audio_extensions: set[str] = Field(
        ...,
        description="音频扩展名（带点；来自 organizer_defaults.music）",
    )
