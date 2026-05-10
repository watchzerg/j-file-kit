"""JAV 视频整理任务：YAML / 存储层的强类型 `config` 模型。

与 `JavAnalyzeConfig` 分离：分析 DTO 在运行时由 organizer 从 ``workspace_root`` 与各归宿子目录常量组装，
扩展名与站标去噪来自 ``organizer_defaults``；本模型只承载 workspace 根路径与用户可调删除策略。
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

import j_file_kit.app.file_task.application.config_common as _config_common
from j_file_kit.app.file_task.application.config_common import (
    InboxDeleteRules,
    path_is_descendant_of,
)
from j_file_kit.shared.constants import MEDIA_ROOT


def _default_jav_workspace_root() -> Path:
    return _config_common.JAV_MEDIA_ROOT.expanduser()


class JavVideoOrganizeConfig(BaseModel):
    """JAV 收件箱整理任务配置：仅 ``workspace_root`` + 删除相关可调项。

    扫描根与 sorted/unsorted 等路径由 ``config_common.jav_workspace_paths`` 派生，不写 YAML。
    不变量：``workspace_root`` 必须位于 ``JAV_MEDIA_ROOT``（默认 ``/media/jav_workspace``）之下。
    """

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path = Field(
        default_factory=_default_jav_workspace_root,
        description="JAV 工作区根目录（其下 inbox/sorted/… 由代码约定）",
    )

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
    def validate_workspace_under_media_root(self) -> JavVideoOrganizeConfig:
        """workspace_root 须在 MEDIA_ROOT（/media）之下。"""
        media_root = MEDIA_ROOT.expanduser().resolve(strict=False)
        w = self.workspace_root.expanduser().resolve(strict=False)
        if not path_is_descendant_of(w, media_root):
            msg = f"workspace_root（{w}）必须是 {media_root} 或其子目录"
            raise ValueError(msg)
        return self
