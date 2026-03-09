from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.file_task_config_service import (
    FileTaskConfigService,
)
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import TaskConfig
from j_file_kit.app.file_task.domain.ports import TaskConfigRepository

pytestmark = pytest.mark.unit


def _task_config(*, inbox_dir: str | None = "/inbox") -> TaskConfig:
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": inbox_dir,
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


class _TaskConfigRepoStub(TaskConfigRepository):
    def __init__(self, task_config: TaskConfig | None = None) -> None:
        self._task_config = task_config
        self.updated_configs: list[TaskConfig] = []

    def get_by_type(self, task_type: str) -> TaskConfig | None:
        if self._task_config is None:
            return None
        if self._task_config.type != task_type:
            return None
        return self._task_config

    def update(self, config: TaskConfig) -> None:
        self._task_config = config
        self.updated_configs.append(config)


def test_get_jav_video_organizer_config_returns_typed_config() -> None:
    repository = _TaskConfigRepoStub(_task_config())

    config = FileTaskConfigService.get_jav_video_organizer_config(repository)

    assert isinstance(config, JavVideoOrganizeConfig)
    assert ".mp4" in config.video_extensions
    assert config.inbox_dir == Path("/inbox")


def test_merge_jav_video_organizer_config_merges_updates() -> None:
    current = JavVideoOrganizeConfig(
        inbox_dir=Path("/inbox"),
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        archive_extensions={".zip"},
        misc_file_delete_rules={"max_size": 1},
    )
    merged = FileTaskConfigService.merge_jav_video_organizer_config(
        current,
        {"misc_file_delete_rules": {"max_size": 2}},
    )

    assert merged.misc_file_delete_rules["max_size"] == 2
    assert ".mp4" in merged.video_extensions
    assert merged.inbox_dir == Path("/inbox")


def test_merge_jav_video_organizer_config_updates_directory() -> None:
    current = JavVideoOrganizeConfig(
        inbox_dir=Path("/old"),
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        archive_extensions={".zip"},
    )
    merged = FileTaskConfigService.merge_jav_video_organizer_config(
        current,
        {"inbox_dir": "/new"},
    )

    assert merged.inbox_dir == Path("/new")


def test_validate_and_save_saves_when_inbox_dir_set() -> None:
    repository = _TaskConfigRepoStub(_task_config(inbox_dir="/inbox"))
    config = FileTaskConfigService.get_jav_video_organizer_config(repository)

    FileTaskConfigService.validate_and_save_jav_video_organizer_config(
        config,
        repository,
    )

    assert repository.updated_configs


def test_validate_and_save_updates_enabled_in_single_write() -> None:
    repository = _TaskConfigRepoStub(_task_config(inbox_dir="/inbox"))
    config = FileTaskConfigService.get_jav_video_organizer_config(repository)

    FileTaskConfigService.validate_and_save_jav_video_organizer_config(
        config,
        repository,
        enabled=False,
    )

    assert len(repository.updated_configs) == 1
    assert repository.updated_configs[0].enabled is False


def test_validate_and_save_raises_when_inbox_dir_missing() -> None:
    repository = _TaskConfigRepoStub(_task_config(inbox_dir=None))
    config = FileTaskConfigService.get_jav_video_organizer_config(repository)

    with pytest.raises(ValueError, match="inbox_dir"):
        FileTaskConfigService.validate_and_save_jav_video_organizer_config(
            config,
            repository,
        )


def test_get_jav_video_organizer_config_raises_when_missing() -> None:
    repository = _TaskConfigRepoStub(None)

    with pytest.raises(ValueError, match="任务配置不存在"):
        FileTaskConfigService.get_jav_video_organizer_config(repository)
