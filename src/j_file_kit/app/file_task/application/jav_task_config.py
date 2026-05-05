"""JAV 视频整理任务：YAML / 存储层的强类型 `config` 模型。

与 `JavAnalyzeConfig` 分离，是因为分析阶段 DTO 由管线在运行时组装（扩展名、站标去噪等来自代码常量），
而本模型只承载用户可在 YAML 中调整的目录与删除策略；两者生命周期不同，混在一个文件里会拉高 API 与管线的耦合。
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

import j_file_kit.app.file_task.application.config_common as _config_common
from j_file_kit.app.file_task.application.config_common import InboxDeleteRules


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
        测试可通过 monkeypatch 覆盖 `application.config_common` 模块级 `JAV_MEDIA_ROOT`。
        """
        jav_media_root = _config_common.JAV_MEDIA_ROOT.resolve(strict=False)
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
