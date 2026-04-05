"""文件任务配置模型

定义文件任务相关的配置模型，包括任务配置和分析配置。
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import TaskConfig
from j_file_kit.shared.constants import MEDIA_ROOT


class InboxDeleteRules(BaseModel):
    """收件箱预删除规则（扩展名分类之前，OR 语义）。

    设计意图：在 analyze_file 最先阶段判定是否直接删除，避免误分类后再处理。
    空字符串会在校验时剔除，避免误匹配。
    """

    exact_stems: set[str] = Field(
        default_factory=set,
        description="stem 完全等于其中任一则删除（大小写敏感）",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="stem 包含其中任一则删除（子串，大小写敏感）",
    )
    max_size_bytes: int | None = Field(
        default=None,
        description="若设置则删除体积不超过该值的文件（含 0 表示仅空文件）；None 表示不启用",
    )

    @model_validator(mode="after")
    def drop_empty_strings(self) -> InboxDeleteRules:
        self.exact_stems = {s for s in self.exact_stems if s != ""}
        self.keywords = [k for k in self.keywords if k != ""]
        return self


class SerialIdRule(BaseModel):
    """单条番号长度规则（用于编译 serial_pattern）。

    与 `SerialId` 领域约束对齐：前缀字母数 2–6，数字部分位数 2–5；
    避免正则命中后无法构造 `SerialId`。

    语义：`digits_min`/`digits_max` 为闭区间，表示**十进制数值的有效位数**（与补零展示无关；
    全 ``0`` 数字串按占位长度计）。与 `build_serial_pattern` 截取连续数字后的校验一致。
    """

    prefix_letters: int = Field(
        ...,
        ge=2,
        le=6,
        description="番号字母前缀长度（与 SerialId.prefix 长度范围一致）",
    )
    digits_min: int = Field(
        ...,
        ge=2,
        le=5,
        description="有效数字部分最少位数（含）；十进制数值位数，全 0 串为占位长度",
    )
    digits_max: int = Field(
        ...,
        ge=2,
        le=5,
        description="有效数字部分最多位数（含）；十进制数值位数，全 0 串为占位长度",
    )

    @model_validator(mode="after")
    def digits_range_ordered(self) -> SerialIdRule:
        if self.digits_min > self.digits_max:
            raise ValueError(
                "digits_min 不能大于 digits_max，"
                f"得到 digits_min={self.digits_min}, digits_max={self.digits_max}",
            )
        return self


@dataclass(frozen=True, slots=True)
class SerialPatternSpec:
    """编译后的番号规则包：前缀正则 + 配置规则列表。

    `pattern` 只匹配到「字母前缀 + 可选分隔符」且下一字符为数字的位置，不包含数字段；
    连续数字串在 `jav_filename_util` 中截取，总长不超过与 `SerialId` 对齐的上限，
    再按十进制有效位数（见 `SerialIdRule`）与 `rules` 做语义校验。`rules` 顺序与
    `serial_id_rules` 一致；同一 `prefix_letters` 可有多条规则，命中前缀后**任一**接受即通过。
    """

    pattern: re.Pattern[str]
    rules: tuple[SerialIdRule, ...]


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
    subtitle_extensions: set[str] = Field(..., description="字幕文件扩展名")
    archive_extensions: set[str] = Field(..., description="压缩文件扩展名")
    misc_file_delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Misc文件删除规则配置（keywords, extensions, max_size）",
    )
    video_small_delete_bytes: int | None = Field(
        default=None,
        description="视频体积严格小于该字节数则直接删除（不看文件名）；None 关闭（由 YAML 配置）",
    )
    inbox_delete_rules: InboxDeleteRules = Field(
        default_factory=InboxDeleteRules,
        description="收件箱预删除（扩展名分类前）：完全匹配 stem、关键字、体积上限，OR 语义",
    )
    serial_id_rules: list[SerialIdRule] = Field(
        ...,
        description="番号长度规则列表（OR）；每条为前缀字母数 + 数字位数闭区间，见 SerialIdRule",
    )

    @model_validator(mode="after")
    def validate_serial_id_rules_non_empty(self) -> JavVideoOrganizeConfig:
        if not self.serial_id_rules:
            raise ValueError("serial_id_rules 不能为空")
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
        self.subtitle_extensions = {
            ext if ext.startswith(".") else f".{ext}"
            for ext in self.subtitle_extensions
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
    调用 build_serial_pattern(serial_id_rules) 编译一次后传入，整个 Pipeline 复用。
    """

    # 文件类型扩展名
    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    subtitle_extensions: set[str] = Field(..., description="字幕文件扩展名")
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
    video_small_delete_bytes: int | None = Field(
        default=None,
        description="视频体积严格小于该字节数则直接删除；None 不按体积删（由任务从 JavVideoOrganizeConfig 注入）",
    )
    inbox_delete_rules: InboxDeleteRules = Field(
        default_factory=InboxDeleteRules,
        description="收件箱预删除（扩展名分类前）：完全匹配 stem、关键字、体积上限，OR 语义",
    )

    # 番号规则包（前缀正则 + 规则列表），在任务初始化时编译一次，整个 Pipeline 复用
    serial_pattern: SerialPatternSpec = Field(
        ...,
        description="build_serial_pattern(serial_id_rules) 的编译结果",
    )


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
            "subtitle_extensions": [
                ".srt",
                ".ass",
                ".ssa",
                ".sub",
                ".vtt",
                ".idx",
                ".sup",
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
            "serial_id_rules": [
                {"prefix_letters": 2, "digits_min": 3, "digits_max": 3},
                {"prefix_letters": 3, "digits_min": 2, "digits_max": 3},
                {"prefix_letters": 4, "digits_min": 2, "digits_max": 3},
                {"prefix_letters": 5, "digits_min": 3, "digits_max": 3},
            ],
            "inbox_delete_rules": {
                "exact_stems": [],
                "keywords": ["扫码下载1024安卓APP", "1024手机网址"],
                "max_size_bytes": 0,
            },
            "video_small_delete_bytes": 200 * 1024 * 1024,
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
                    ".nrg",
                    ".iso",
                    ".dmg",
                    ".mdf",
                    ".mds",
                    ".mdx",
                    ".mht",
                    ".dat",
                    ".xltd",
                ],
                "max_size": 1048576,
            },
        },
    )
