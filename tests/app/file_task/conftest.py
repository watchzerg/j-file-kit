"""file_task 领域测试 fixtures

适合放置：mock 仓储实现、示例 TaskConfig、通用领域对象构造器。
"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import TaskConfig


@pytest.fixture
def task_config_factory(tmp_path: Path):
    """创建 TaskConfig 的工厂，支持覆盖默认配置。"""

    def _create(
        task_type: str = TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled: bool = True,
        inbox_dir: Path | None = None,
        **config_overrides: object,
    ) -> TaskConfig:
        inbox = inbox_dir if inbox_dir is not None else tmp_path / "inbox"
        config = {
            "inbox_dir": str(inbox),
            "sorted_dir": str(tmp_path / "sorted"),
            "unsorted_dir": str(tmp_path / "unsorted"),
            "archive_dir": str(tmp_path / "archive"),
            "misc_dir": str(tmp_path / "misc"),
            "video_extensions": [".mp4"],
            "image_extensions": [".jpg"],
            "subtitle_extensions": [".srt"],
            "archive_extensions": [".zip"],
            "serial_id_combinations": [[3, 3]],
            "misc_file_delete_rules": {},
            **config_overrides,
        }
        return TaskConfig(type=task_type, enabled=enabled, config=config)

    return _create
