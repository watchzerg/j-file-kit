"""文件任务配置验证（JAV / Raw）。

保存配置前调用：校验 ``workspace_root`` 媒体边界已由 Pydantic 模型保证；
此处补充文件系统层面的收件箱就绪检查（根目录与 inbox 须存在且 inbox 为目录）。

副作用由 ``FileTaskConfigService`` 在调用本模块前完成（``ensure_workspace_root_and_inbox``）。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.config_common import (
    jav_workspace_paths,
    raw_workspace_paths,
)
from j_file_kit.app.file_task.application.jav_task_config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.raw_task_config import RawFileOrganizeConfig


def _errors_workspace_and_inbox(
    paths_root: Path, paths_inbox: Path, label: str
) -> list[str]:
    errors: list[str] = []
    if not paths_root.exists():
        errors.append(
            f"{label} workspace_root 不存在（{paths_root}），保存配置后应已创建"
        )
    elif not paths_root.is_dir():
        errors.append(f"{label} workspace_root 不是目录（{paths_root}）")

    if not paths_inbox.exists():
        errors.append(f"{label} inbox 不存在（{paths_inbox}），保存配置后应已创建")
    elif not paths_inbox.is_dir():
        errors.append(f"{label} inbox 不是目录（{paths_inbox}）")
    return errors


def validate_jav_video_organizer_config(config: JavVideoOrganizeConfig) -> list[str]:
    """验证 JAV 任务 workspace 与收件箱目录就绪。"""
    paths = jav_workspace_paths(config.workspace_root)
    return _errors_workspace_and_inbox(paths.root, paths.inbox, "JAV")


def validate_raw_file_organizer_config(config: RawFileOrganizeConfig) -> list[str]:
    """验证 Raw 任务 workspace 与收件箱目录就绪。"""
    paths = raw_workspace_paths(config.workspace_root)
    return _errors_workspace_and_inbox(paths.root, paths.inbox, "Raw")
