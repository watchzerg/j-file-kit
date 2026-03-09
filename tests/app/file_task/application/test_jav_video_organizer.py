"""JAV 视频整理任务单元测试

覆盖 task_type、run 前置校验、_create_analyze_config。
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.jav_video_organizer import JavVideoOrganizer
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import TaskConfig

pytestmark = pytest.mark.unit


@pytest.fixture
def task_config_with_inbox(tmp_path: Path) -> TaskConfig:
    inbox = tmp_path / "inbox"
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": str(inbox),
            "sorted_dir": str(tmp_path / "sorted"),
            "unsorted_dir": str(tmp_path / "unsorted"),
            "archive_dir": str(tmp_path / "archive"),
            "misc_dir": str(tmp_path / "misc"),
            "video_extensions": [".mp4", ".mkv"],
            "image_extensions": [".jpg"],
            "archive_extensions": [".zip"],
            "misc_file_delete_rules": {"keywords": ["x"], "max_size": 100},
        },
    )


@pytest.fixture
def organizer(task_config_with_inbox: TaskConfig, tmp_path: Path) -> JavVideoOrganizer:
    return JavVideoOrganizer(
        task_config=task_config_with_inbox,
        log_dir=tmp_path,
        file_result_repository=MagicMock(),
    )


class TestJavVideoOrganizerTaskType:
    """task_type 属性"""

    def test_returns_constant(self, organizer: JavVideoOrganizer) -> None:
        assert organizer.task_type == TASK_TYPE_JAV_VIDEO_ORGANIZER


class TestJavVideoOrganizerRun:
    """run 前置校验"""

    def test_inbox_dir_none_raises(self, tmp_path: Path) -> None:
        config = TaskConfig(
            type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
            enabled=True,
            config={
                "inbox_dir": None,
                "sorted_dir": None,
                "unsorted_dir": None,
                "archive_dir": None,
                "misc_dir": None,
                "video_extensions": [".mp4"],
                "image_extensions": [".jpg"],
                "archive_extensions": [".zip"],
                "misc_file_delete_rules": {},
            },
        )
        organizer = JavVideoOrganizer(
            task_config=config,
            log_dir=tmp_path,
            file_result_repository=MagicMock(),
        )
        with pytest.raises(ValueError, match="inbox_dir 未设置"):
            organizer.run(run_id=1)


class TestJavVideoOrganizerCreateAnalyzeConfig:
    """_create_analyze_config 配置映射"""

    def test_maps_all_fields(self, organizer: JavVideoOrganizer) -> None:
        config = organizer._create_analyze_config()
        assert config.video_extensions == {".mp4", ".mkv"}
        assert config.image_extensions == {".jpg"}
        assert config.archive_extensions == {".zip"}
        assert config.sorted_dir == organizer.file_config.sorted_dir
        assert config.unsorted_dir == organizer.file_config.unsorted_dir
        assert config.archive_dir == organizer.file_config.archive_dir
        assert config.misc_dir == organizer.file_config.misc_dir
        assert config.misc_file_delete_rules == {"keywords": ["x"], "max_size": 100}
