"""文件任务配置模型

定义文件任务相关的配置模型，包括任务配置和分析配置。
"""

import re
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, model_validator

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import TaskConfig
from j_file_kit.shared.constants import MEDIA_ROOT


class JavVideoOrganizeConfig(BaseModel):
    """JAV视频文件整理任务配置

    包含目录路径和文件处理规则的完整配置，各任务类型独立管理自身配置。
    所有目录字段（非 None）必须是 MEDIA_ROOT 的子目录。
    """

    inbox_dir: Path | None = Field(default=None, description="待处理目录")
    sorted_dir: Path | None = Field(default=None, description="已整理目录（有番号）")
    unsorted_dir: Path | None = Field(default=None, description="未整理目录（无番号）")
    archive_dir: Path | None = Field(default=None, description="归档目录")
    misc_dir: Path | None = Field(default=None, description="杂项目录")

    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    archive_extensions: set[str] = Field(..., description="压缩文件扩展名")
    misc_file_delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Misc文件删除规则配置（keywords, extensions, max_size）",
    )
    serial_id_combinations: Annotated[
        list[tuple[int, int]],
        BeforeValidator(
            lambda v: [tuple(item) for item in v] if isinstance(v, list) else v,
        ),
    ] = Field(
        default=[(3, 3), (4, 3), (5, 3), (6, 3), (3, 4)],
        description="番号字母数+数字数的合法组合列表，每个元素为 (字母数, 数字数)",
    )

    @model_validator(mode="after")
    def validate_serial_id_combinations(self) -> JavVideoOrganizeConfig:
        """验证 serial_id_combinations 非空且每个元素均为正整数对"""
        if not self.serial_id_combinations:
            raise ValueError("serial_id_combinations 不能为空")
        for n_letters, n_digits in self.serial_id_combinations:
            if n_letters <= 0 or n_digits <= 0:
                raise ValueError(
                    "serial_id_combinations 中每个组合的字母数和数字数必须为正整数，"
                    f"得到 ({n_letters}, {n_digits})",
                )
        return self

    @model_validator(mode="after")
    def validate_extensions(self) -> JavVideoOrganizeConfig:
        """规范化扩展名格式（确保以点号开头）"""
        self.video_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in self.video_extensions
        }
        self.image_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in self.image_extensions
        }
        self.archive_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in self.archive_extensions
        }
        return self

    @model_validator(mode="after")
    def validate_dir_paths_under_media_root(self) -> JavVideoOrganizeConfig:
        """所有非 None 目录路径必须是 MEDIA_ROOT 的子目录。

        作为模型不变量在构造时强制校验，覆盖配置加载和 API 更新两个场景。
        测试可通过 monkeypatch 覆盖模块级 MEDIA_ROOT 变量。
        """
        media_root = MEDIA_ROOT.resolve(strict=False)
        errors = []
        for field_name in (
            "inbox_dir",
            "sorted_dir",
            "unsorted_dir",
            "archive_dir",
            "misc_dir",
        ):
            dir_path: Path | None = getattr(self, field_name)
            if (
                dir_path is not None
                and media_root not in dir_path.resolve(strict=False).parents
            ):
                errors.append(f"{field_name}（{dir_path}）必须是 {media_root} 的子目录")
        if errors:
            raise ValueError(
                "目录路径不符合 MEDIA_ROOT 约束：\n"
                + "\n".join(f"  - {e}" for e in errors),
            )
        return self


class AnalyzeConfig(BaseModel):
    """分析配置

    包含分析文件所需的所有配置信息。
    serial_pattern 由 JavVideoOrganizer._create_analyze_config 在任务初始化时
    调用 build_serial_pattern(serial_id_combinations) 编译一次后传入，整个 Pipeline 复用。
    """

    # 文件类型扩展名
    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    archive_extensions: set[str] = Field(..., description="压缩文件扩展名")

    # 目标目录
    sorted_dir: Path | None = Field(
        default=None,
        description="整理后的视频图片存储目录",
    )
    unsorted_dir: Path | None = Field(
        default=None,
        description="无番号视频图片存储目录",
    )
    archive_dir: Path | None = Field(default=None, description="压缩文件存储目录")
    misc_dir: Path | None = Field(default=None, description="Misc文件存储目录")

    # 删除规则
    misc_file_delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Misc文件删除规则配置（keywords, extensions, max_size）",
    )

    # 预编译的番号正则，在任务初始化时编译一次，整个 Pipeline 复用
    serial_pattern: re.Pattern[str] = Field(..., description="预编译的番号正则")


def create_default_jav_video_organizer_task_config() -> TaskConfig:
    """创建 jav_video_organizer 默认任务配置。

    Returns:
        默认任务配置对象
    """
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": "/media/inbox",
            "sorted_dir": "/media/sorted",
            "unsorted_dir": "/media/unsorted",
            "archive_dir": "/media/archive",
            "misc_dir": "/media/misc",
            "video_extensions": [
                ".mp4",
                ".avi",
                ".mkv",
                ".mov",
                ".wmv",
                ".flv",
                ".webm",
                ".rmvb",
                ".rm",
                ".mpg",
                ".mpeg",
                ".m4v",
                ".ts",
                ".m2ts",
                ".vob",
                ".divx",
            ],
            "image_extensions": [
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".bmp",
                ".gif",
                ".tiff",
            ],
            "archive_extensions": [
                ".zip",
                ".rar",
                ".7z",
                ".tar",
                ".gz",
                ".bz2",
                ".xz",
            ],
            "serial_id_combinations": [[3, 2], [3, 3], [4, 2], [4, 3]],
            "misc_file_delete_rules": {
                "keywords": ["sample", "preview", "temp"],
                "extensions": [
                    ".tmp",
                    ".temp",
                    ".bak",
                    ".old",
                    ".url",
                    ".lnk",
                    ".mhtml",
                    ".html",
                    ".htm",
                    ".nfo",
                    ".chm",
                    ".txt",
                    ".xml",
                    ".exe",
                    ".scr",
                    ".md",
                    ".sfv",
                    ".pdf",
                    ".doc",
                    ".docs",
                    ".bat",
                    ".cmd",
                    ".pif",
                    ".js",
                    ".vbs",
                    ".log",
                    ".website",
                    ".desktop",
                    ".webloc",
                    ".ds_store",
                    ".torrent",
                    ".rtf",
                    ".ini",
                    ".cfg",
                    ".db",
                    ".nzb",
                    ".!ut",
                    ".part",
                    ".crdownload",
                    ".aria2",
                    ".ydl",
                    ".apk",
                    ".!qb",
                ],
                "max_size": 1048576,
            },
        },
    )
