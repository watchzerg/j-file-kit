"""文件任务配置模型（YAML `TaskConfig.config` 与各任务强类型配置的桥梁）。

- `JavVideoOrganizeConfig`：JAV 整理任务在存储/API 层的完整配置（含 `inbox_dir` 与路径校验）。
- `AnalyzeConfig`：从上述配置派生、仅供给 `analyze_file` 的输入 DTO（不包含 `inbox_dir`）。
- `create_default_jav_video_organizer_task_config`：首次初始化 `task_config.yaml` 时使用。
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import TaskConfig
from j_file_kit.shared.constants import MEDIA_ROOT


class InboxDeleteRules(BaseModel):
    """收件箱预删除规则：在 `analyze_file` 里先于扩展名分类求值，命中则直接 `DeleteDecision`（条件 OR）。

    用于删掉广告壳、过小占位文件等；空 token 在 `drop_empty_strings` 中剔除。
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


class JavVideoOrganizeConfig(BaseModel):
    """JAV 收件箱整理任务的强类型配置（对应 YAML 里某 `task_type` 的 `config` 字典）。

    在代码中的位置：`TaskConfig.get_config(JavVideoOrganizeConfig)` → 供 `JavVideoOrganizer` 读取；
    `inbox_dir` 作为 `FilePipeline` 的扫描根；其余字段经 `_create_analyze_config` 映射为 `AnalyzeConfig`。

    不变量：凡非 None 的目录字段必须为 `MEDIA_ROOT` 子目录（见 `validate_dir_paths_under_media_root`）。
    首次安装的站标去噪默认值只出现在 `create_default_jav_video_organizer_task_config`，不在本模型写死。
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
    jav_filename_strip_substrings: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "匹配番号前从文件名中移除的子串（大小写不敏感，各处出现均删除；"
            "成功重构时输出文件名也不含这些子串）。未配置或空列表则不启用；空串在校验时剔除"
        ),
    )

    @model_validator(mode="after")
    def drop_empty_jav_filename_strip_tokens(self) -> JavVideoOrganizeConfig:
        self.jav_filename_strip_substrings = tuple(
            s for s in self.jav_filename_strip_substrings if s != ""
        )
        return self

    @model_validator(mode="after")
    def validate_extensions(self) -> JavVideoOrganizeConfig:
        """将四类扩展名统一规范为前导 `.`，与扫描/分类逻辑一致。"""
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
    """`analyze_file(path, config)` 的唯一配置载体（纯分析阶段，不含收件箱路径）。

    由 `JavVideoOrganizeConfig` 字段子集构造：输出目录、扩展名分类、各类删除/去噪规则。
    番号前缀等解析规则固定在 `jav_filename_util`，不经 YAML 覆盖。
    `jav_filename_strip_substrings` 须与任务配置保持一致；空元组表示不做站标去噪。
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

    jav_filename_strip_substrings: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "匹配番号前从文件名中移除的子串（大小写不敏感，各处出现均删除；"
            "成功重构时输出文件名也不含这些子串）。未配置或空列表则不启用；须与 JavVideoOrganizeConfig 一致"
        ),
    )

    @model_validator(mode="after")
    def drop_empty_jav_filename_strip_tokens_analyze(self) -> AnalyzeConfig:
        """剔除空串 token，避免误匹配；与 `JavVideoOrganizeConfig` 侧校验语义一致。"""
        self.jav_filename_strip_substrings = tuple(
            s for s in self.jav_filename_strip_substrings if s != ""
        )
        return self


def create_default_jav_video_organizer_task_config() -> TaskConfig:
    """生成「一份可写入 YAML」的 jav_video_organizer 默认 `TaskConfig`。

    调用方：应用 lifespan 中若配置文件缺失，则以此初始化磁盘上的 `task_config.yaml`。
    返回的 `config` 字典含容器友好路径（如 `/media/inbox`）及首字母装机的站标去噪列表；
    用户可在 YAML 中覆盖；Pydantic 模型层不把这些默认值写死在 `JavVideoOrganizeConfig` 字段里。
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
            "jav_filename_strip_substrings": [
                "BBS-2048",
                "BIG-2048",
                "CHD-1080",
                "DHD-1080",
                "FUN-2048",
                "HJD-2048",
                "PP-168",
                "RH-2048",
                "XHD-1080",
                "CCTV-12306",
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
