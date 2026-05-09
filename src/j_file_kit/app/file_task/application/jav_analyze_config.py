"""JAV 纯分析阶段配置：`analyze_jav_file` 的唯一 DTO。

归宿路径由任务入口根据 ``workspace_root`` 与代码约定的子目录名派生后注入；
分析函数不包含收件箱路径，扫描根由调用方单独传入。
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from j_file_kit.app.file_task.application.config_common import InboxDeleteRules


class JavAnalyzeConfig(BaseModel):
    """`analyze_jav_file(path, config)` 的配置载体（JAV 纯分析阶段，不含收件箱路径）。

    由 `JavVideoOrganizer._create_analyze_config` 组装：四类扩展名、`jav_filename_strip_substrings`、
    ``misc_file_delete_rules.extensions`` 来自 `organizer_defaults` 与 YAML misc 片段合并。
    sorted/unsorted/archive/misc 目录均为 ``workspace_root`` 下的固定子路径。
    """

    # 文件类型扩展名
    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    subtitle_extensions: set[str] = Field(..., description="字幕文件扩展名")
    archive_extensions: set[str] = Field(..., description="压缩文件扩展名")

    # 目标目录（派生自 workspace_root）
    sorted_dir: Path = Field(..., description="已解析番号的媒体归宿根目录")
    unsorted_dir: Path = Field(..., description="无番号视频/字幕归宿目录")
    archive_dir: Path = Field(..., description="压缩包归宿目录")
    misc_dir: Path = Field(..., description="Misc 归宿目录")

    # 删除规则
    misc_file_delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Misc文件删除规则配置（extensions, max_size）",
    )
    video_small_delete_bytes: int | None = Field(
        default=None,
        description="视频体积严格小于该字节数则直接删除；None 不按体积删（由任务注入）",
    )
    inbox_delete_rules: InboxDeleteRules = Field(
        default_factory=InboxDeleteRules,
        description="收件箱预删除（扩展名分类前）：完全匹配 stem、体积上限，OR 语义",
    )

    jav_filename_strip_substrings: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "匹配番号前从文件名中移除的子串（大小写不敏感，各处出现均删除；"
            "成功重构时输出文件名也不含这些子串）。管线注入时使用 `organizer_defaults`"
        ),
    )

    @model_validator(mode="after")
    def drop_empty_jav_filename_strip_tokens_analyze(self) -> JavAnalyzeConfig:
        """剔除空串 token，避免误匹配。"""
        self.jav_filename_strip_substrings = tuple(
            s for s in self.jav_filename_strip_substrings if s != ""
        )
        return self
