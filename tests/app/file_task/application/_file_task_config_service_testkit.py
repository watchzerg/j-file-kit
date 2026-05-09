"""file_task_config_service 测试辅助函数。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.domain.constants import (
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
)
from j_file_kit.app.file_task.domain.task_config import TaskConfig


def build_mock_repository() -> MagicMock:
    return MagicMock()


def build_jav_task_config(workspace_root: Path) -> TaskConfig:
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "workspace_root": str(workspace_root),
            "misc_file_delete_rules": {},
        },
    )


def build_raw_task_config(workspace_root: Path) -> TaskConfig:
    return TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={"workspace_root": str(workspace_root)},
    )


def patch_media_roots(monkeypatch: pytest.MonkeyPatch, media_root: Path) -> None:
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.config_common.JAV_MEDIA_ROOT",
        media_root,
    )
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.config_common.RAW_MEDIA_ROOT",
        media_root,
    )
