"""文件任务配置模型（YAML `TaskConfig.config` 与各任务强类型配置的桥梁）。

- `JavVideoOrganizeConfig`：JAV 整理任务在存储/API 层的完整配置（含 `inbox_dir` 与路径校验）。
- `JavAnalyzeConfig`：从上述配置派生、仅供给 `analyze_jav_file` 的输入 DTO（不包含 `inbox_dir`）。
- `RawFileOrganizeConfig` / `RawAnalyzeConfig`：raw 收件箱整理任务的任务侧与分析侧配置。
- `create_default_*_task_config`：首次初始化 `task_config.yaml` 时使用。
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from j_file_kit.app.file_task.domain.constants import (
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
)
from j_file_kit.app.file_task.domain.models import TaskConfig
from j_file_kit.shared.constants import MEDIA_ROOT

# JAV 整理任务的媒体子根目录；测试可 monkeypatch 此模块变量
JAV_MEDIA_ROOT = MEDIA_ROOT / "jav_workspace"

# Raw 整理任务的媒体子根目录；测试可 monkeypatch 此模块变量
RAW_MEDIA_ROOT = MEDIA_ROOT / "raw_workspace"


class InboxDeleteRules(BaseModel):
    """收件箱预删除规则：在 `analyze_jav_file` 里先于扩展名分类求值，命中则直接 `DeleteDecision`（条件 OR）。

    用于删掉广告壳、过小占位文件等；空 token 在 `drop_empty_strings` 中剔除。
    """

    exact_stems: set[str] = Field(
        default_factory=set,
        description="stem 完全等于其中任一则删除（大小写敏感）",
    )
    max_size_bytes: int | None = Field(
        default=None,
        description="若设置则删除体积不超过该值的文件（含 0 表示仅空文件）；None 表示不启用",
    )

    @model_validator(mode="after")
    def drop_empty_strings(self) -> InboxDeleteRules:
        self.exact_stems = {s for s in self.exact_stems if s != ""}
        return self


class JavVideoOrganizeConfig(BaseModel):
    """JAV 收件箱整理任务的强类型配置（对应 YAML 里某 `task_type` 的 `config` 字典）。

    在代码中的位置：`TaskConfig.get_config(JavVideoOrganizeConfig)` → 供 `JavVideoOrganizer` 读取；
    `inbox_dir` 作为 `FilePipeline` 的扫描根；其余字段经 `_create_analyze_config` 映射为 `JavAnalyzeConfig`。

    四类媒体扩展名、Misc 删除扩展名及站标去噪子串**不在本模型字段中**，由 `organizer_defaults`
    在 `JavVideoOrganizer._create_analyze_config` 中注入 `JavAnalyzeConfig`；`misc_file_delete_rules` 在存储层仅含 max_size（见剔除校验器）。

    不变量：凡非 None 的目录字段必须为 `JAV_MEDIA_ROOT`（`/media/jav_workspace`）子目录（见 `validate_dir_paths_under_media_root`）。
    """

    inbox_dir: Path | None = Field(default=None, description="待处理目录")
    sorted_dir: Path | None = Field(default=None, description="已整理目录（有番号）")
    unsorted_dir: Path | None = Field(default=None, description="未整理目录（无番号）")
    archive_dir: Path | None = Field(default=None, description="归档目录")
    misc_dir: Path | None = Field(default=None, description="杂项目录")

    misc_file_delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Misc 删除可调部分：max_size（扩展名列表由代码常量注入）",
    )
    video_small_delete_bytes: int | None = Field(
        default=None,
        description="视频体积严格小于该字节数则直接删除（不看文件名）；None 关闭（由 YAML 配置）",
    )
    inbox_delete_rules: InboxDeleteRules = Field(
        default_factory=InboxDeleteRules,
        description="收件箱预删除（扩展名分类前）：完全匹配 stem、体积上限，OR 语义",
    )

    @model_validator(mode="after")
    def strip_misc_extensions_from_yaml(self) -> JavVideoOrganizeConfig:
        """Misc 删除规则以 `organizer_defaults` 常量为准；剔除 YAML 中的非可调键，避免写回配置。"""
        if not self.misc_file_delete_rules:
            return self
        rules = dict(self.misc_file_delete_rules)
        rules.pop("extensions", None)
        rules.pop("keywords", None)
        self.misc_file_delete_rules = rules
        return self

    @model_validator(mode="after")
    def validate_dir_paths_under_media_root(self) -> JavVideoOrganizeConfig:
        """所有非 None 目录路径必须是 JAV_MEDIA_ROOT（/media/jav_workspace）的子目录。

        作为模型不变量在构造时强制校验，覆盖配置加载和 API 更新两个场景。
        测试可通过 monkeypatch 覆盖模块级 JAV_MEDIA_ROOT 变量。
        """
        jav_media_root = JAV_MEDIA_ROOT.resolve(strict=False)
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
                and jav_media_root not in dir_path.resolve(strict=False).parents
            ):
                errors.append(
                    f"{field_name}（{dir_path}）必须是 {jav_media_root} 的子目录",
                )
        if errors:
            raise ValueError(
                "目录路径不符合 JAV_MEDIA_ROOT 约束：\n"
                + "\n".join(f"  - {e}" for e in errors),
            )
        return self


class JavAnalyzeConfig(BaseModel):
    """`analyze_jav_file(path, config)` 的唯一配置载体（JAV 纯分析阶段，不含收件箱路径）。

    由 `JavVideoOrganizer._create_analyze_config` 组装：输出目录与收件箱预删等来自任务配置；
    四类扩展名、`jav_filename_strip_substrings`、`misc_file_delete_rules.extensions` 来自 `organizer_defaults`
    与 YAML misc 片段合并。番号前缀等解析规则固定在 `jav_filename_util`，不经 YAML 覆盖。
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
        description="Misc文件删除规则配置（extensions, max_size）",
    )
    video_small_delete_bytes: int | None = Field(
        default=None,
        description="视频体积严格小于该字节数则直接删除；None 不按体积删（由任务从 JavVideoOrganizeConfig 注入）",
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


RAW_FILE_ORGANIZE_PATH_FIELD_NAMES: tuple[str, ...] = (
    "inbox_dir",
    "folders_to_delete",
    "folders_video_huge",
    "folders_video_complex",
    "folders_video_movie",
    "folders_video_vr",
    "folders_compressed",
    "folders_pic",
    "folders_audio",
    "folders_misc",
    "files_video_jav",
    "files_video_us",
    "files_video_vr",
    "files_movie",
    "files_video_misc",
    "files_compressed",
    "files_pic",
    "files_audio",
    "files_misc",
)


class RawFileOrganizeConfig(BaseModel):
    """Raw 收件箱整理任务强类型配置（YAML `config` 字典对应物）。

    字段名与业务目录名一致（`folders_*` / `files_*`）。`inbox_dir` 为扫描根；其余目录为分类归宿。
    不变量：凡非 None 的路径必须为 `RAW_MEDIA_ROOT`（`/media/raw_workspace`）子目录。
    """

    inbox_dir: Path | None = Field(default=None, description="inbox：BT 下载初始目录")
    folders_to_delete: Path | None = Field(
        default=None,
        description="待人工确认的疑似删除目录（Raw 阶段 2.1 命中关键字时整目录迁入）",
    )
    folders_video_huge: Path | None = Field(
        default=None,
        description="超大体积目录（人工处理）",
    )
    folders_video_complex: Path | None = Field(
        default=None,
        description="复杂视频目录（除平铺视频外另有文件或子目录）",
    )
    folders_video_movie: Path | None = Field(default=None, description="电影目录")
    folders_video_vr: Path | None = Field(default=None, description="VR 视频目录")
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
    files_movie: Path | None = Field(default=None, description="电影文件目录")
    files_video_misc: Path | None = Field(default=None, description="杂项视频文件目录")
    files_compressed: Path | None = Field(default=None, description="压缩文件目录")
    files_pic: Path | None = Field(default=None, description="图片文件目录")
    files_audio: Path | None = Field(default=None, description="音频文件目录")
    files_misc: Path | None = Field(
        default=None,
        description="无法自动分类的杂项文件目录",
    )

    @model_validator(mode="after")
    def validate_dir_paths_under_raw_media_root(self) -> RawFileOrganizeConfig:
        """所有非 None 目录路径必须位于 RAW_MEDIA_ROOT 下。"""
        raw_root = RAW_MEDIA_ROOT.resolve(strict=False)
        errors: list[str] = []
        for field_name in RAW_FILE_ORGANIZE_PATH_FIELD_NAMES:
            dir_path: Path | None = getattr(self, field_name)
            if (
                dir_path is not None
                and raw_root not in dir_path.resolve(strict=False).parents
            ):
                errors.append(
                    f"{field_name}（{dir_path}）必须是 {raw_root} 的子目录",
                )
        if errors:
            raise ValueError(
                "目录路径不符合 RAW_MEDIA_ROOT 约束：\n"
                + "\n".join(f"  - {e}" for e in errors),
            )
        return self


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
    folders_video_huge: Path | None = Field(
        default=None,
        description="超大体积目录（人工处理）",
    )
    folders_video_complex: Path | None = Field(
        default=None,
        description="复杂视频目录（除平铺视频外另有文件或子目录）",
    )
    folders_video_movie: Path | None = Field(default=None, description="电影目录")
    folders_video_vr: Path | None = Field(default=None, description="VR 视频目录")
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
    files_movie: Path | None = Field(default=None, description="电影文件目录")
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


def create_default_jav_video_organizer_task_config() -> TaskConfig:
    """生成「一份可写入 YAML」的 jav_video_organizer 默认 `TaskConfig`。

    调用方：应用 lifespan 中若配置文件缺失，则以此初始化磁盘上的 `task_config.yaml`。
    扩展名分类、站标去噪、Misc 删除扩展名不在此字典中，运行时由 `organizer_defaults` 注入 `JavAnalyzeConfig`。
    """
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": "/media/jav_workspace/inbox",
            "sorted_dir": "/media/jav_workspace/sorted",
            "unsorted_dir": "/media/jav_workspace/unsorted",
            "archive_dir": "/media/jav_workspace/archive",
            "misc_dir": "/media/jav_workspace/misc",
            "inbox_delete_rules": {
                "exact_stems": [],
                "max_size_bytes": 0,
            },
            "video_small_delete_bytes": 200 * 1024 * 1024,
            "misc_file_delete_rules": {
                "max_size": 1048576,
            },
        },
    )


def create_default_raw_file_organizer_task_config() -> TaskConfig:
    """生成 raw_file_organizer 默认 `TaskConfig`（写入 YAML 时仅含路径键，扩展名由运行时注入分析配置）。"""
    base = "/media/raw_workspace"
    return TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": f"{base}/inbox",
            "folders_to_delete": f"{base}/folders_to_delete",
            "folders_video_huge": f"{base}/folders_video_huge",
            "folders_video_complex": f"{base}/folders_video_complex",
            "folders_video_movie": f"{base}/folders_video_movie",
            "folders_video_vr": f"{base}/folders_video_vr",
            "folders_compressed": f"{base}/folders_compressed",
            "folders_pic": f"{base}/folders_pic",
            "folders_audio": f"{base}/folders_audio",
            "folders_misc": f"{base}/folders_misc",
            "files_video_jav": f"{base}/files_video_jav",
            "files_video_us": f"{base}/files_video_us",
            "files_video_vr": f"{base}/files_video_vr",
            "files_movie": f"{base}/files_movie",
            "files_video_misc": f"{base}/files_video_misc",
            "files_compressed": f"{base}/files_compressed",
            "files_pic": f"{base}/files_pic",
            "files_audio": f"{base}/files_audio",
            "files_misc": f"{base}/files_misc",
        },
    )
