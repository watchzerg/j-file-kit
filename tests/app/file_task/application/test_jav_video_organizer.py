"""JAV 视频整理任务单元测试

覆盖 task_type、run 前置校验、_create_analyze_config。
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.config import InboxDeleteRules
from j_file_kit.app.file_task.application.jav_video_organizer import JavVideoOrganizer
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import TaskConfig
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_ARCHIVE_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS,
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
    DEFAULT_SUBTITLE_EXTENSIONS,
    DEFAULT_VIDEO_EXTENSIONS,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def task_config_with_inbox() -> TaskConfig:
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": "/media/jav_workspace/inbox",
            "sorted_dir": "/media/jav_workspace/sorted",
            "unsorted_dir": "/media/jav_workspace/unsorted",
            "archive_dir": "/media/jav_workspace/archive",
            "misc_dir": "/media/jav_workspace/misc",
            "misc_file_delete_rules": {"max_size": 100},
            "inbox_delete_rules": {
                "exact_stems": ["Thumbs"],
                "max_size_bytes": 0,
            },
        },
    )


@pytest.fixture
def organizer(
    task_config_with_inbox: TaskConfig,
    tmp_path: Path,
) -> JavVideoOrganizer:  # tmp_path used only for log_dir
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
        assert config.video_extensions == set(DEFAULT_VIDEO_EXTENSIONS)
        assert config.image_extensions == set(DEFAULT_IMAGE_EXTENSIONS)
        assert config.subtitle_extensions == set(DEFAULT_SUBTITLE_EXTENSIONS)
        assert config.archive_extensions == set(DEFAULT_ARCHIVE_EXTENSIONS)
        assert config.sorted_dir == organizer.file_config.sorted_dir
        assert config.unsorted_dir == organizer.file_config.unsorted_dir
        assert config.archive_dir == organizer.file_config.archive_dir
        assert config.misc_dir == organizer.file_config.misc_dir
        assert config.misc_file_delete_rules["max_size"] == 100
        assert config.misc_file_delete_rules["extensions"] == sorted(
            DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
        )
        assert config.inbox_delete_rules == InboxDeleteRules(
            exact_stems={"Thumbs"},
            max_size_bytes=0,
        )
        assert config.video_small_delete_bytes is None
        assert (
            config.jav_filename_strip_substrings
            == DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS
        )
