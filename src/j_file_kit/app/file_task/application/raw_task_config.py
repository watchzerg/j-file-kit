"""Raw 收件箱整理任务：YAML / 存储层的强类型 `config` 模型。

路径字段不再持久化：仅 ``workspace_root``；``inbox``、``folders_*``、``files_*`` 由
``config_common.raw_workspace_paths`` 从根目录派生，与 `RawAnalyzeConfig` 的分工保持不变。
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

import j_file_kit.app.file_task.application.config_common as _config_common
from j_file_kit.app.file_task.application.config_common import path_is_descendant_of
from j_file_kit.shared.constants import MEDIA_ROOT


def _default_raw_workspace_root() -> Path:
    return _config_common.RAW_MEDIA_ROOT.expanduser()


class RawFileOrganizeConfig(BaseModel):
    """Raw 收件箱整理任务配置：仅 workspace 根。

    不变量：``workspace_root`` 必须位于 ``RAW_MEDIA_ROOT``（默认 ``/media/raw_workspace``）之下。
    """

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path = Field(
        default_factory=_default_raw_workspace_root,
        description="Raw 工作区根目录（其下 inbox/folders_* / files_* 由代码约定）",
    )

    @model_validator(mode="after")
    def validate_workspace_under_raw_media_root(self) -> RawFileOrganizeConfig:
        media_root = MEDIA_ROOT.expanduser().resolve(strict=False)
        w = self.workspace_root.expanduser().resolve(strict=False)
        if not path_is_descendant_of(w, media_root):
            msg = f"workspace_root（{w}）必须是 {media_root} 或其子目录"
            raise ValueError(msg)
        return self
