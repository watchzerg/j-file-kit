"""file_task 领域测试 fixtures

适合放置：mock 仓储实现、示例 TaskConfig、通用领域对象构造器。
"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.task_config import TaskConfig


@pytest.fixture
def task_config_factory(tmp_path: Path):
    """构造 ``TaskConfig``（JAV 为 ``workspace_root`` 契约）。

    若测试会 ``get_config(JavVideoOrganizeConfig)``，需 monkeypatch ``JAV_MEDIA_ROOT`` 为
    包含 ``workspace_root`` 的目录（见 ``tests/app/file_task/application/test_jav_video_organizer.py``）。
    """

    def _create(
        task_type: str = TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled: bool = True,
        workspace_root: Path | None = None,
        **config_overrides: object,
    ) -> TaskConfig:
        root = workspace_root if workspace_root is not None else tmp_path / "jav_ws"
        config: dict[str, object] = {
            "workspace_root": str(root),
            "misc_file_delete_rules": {},
        }
        config.update(config_overrides)
        return TaskConfig(type=task_type, enabled=enabled, config=config)

    return _create
