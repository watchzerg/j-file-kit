import pytest

from j_file_kit.app.config.domain.models import GlobalConfig, TaskConfig
from j_file_kit.app.config.domain.ports import ConfigStateManager, TaskConfigRepository
from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.file_task_config_service import (
    FileTaskConfigService,
)
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER

pytestmark = pytest.mark.unit


def _task_config() -> TaskConfig:
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "video_extensions": [".mp4"],
            "image_extensions": [".jpg"],
            "archive_extensions": [".zip"],
            "misc_file_delete_rules": {},
        },
    )


class _ConfigManagerStub(ConfigStateManager):
    def __init__(self, task_config: TaskConfig | None) -> None:
        self._task_config = task_config
        self.reload_calls: list[str] = []

    def get_global_config(self) -> GlobalConfig:  # pragma: no cover - unused
        raise NotImplementedError

    def get_task_config_by_type(self, task_type: str) -> TaskConfig | None:
        if self._task_config is None:
            return None
        if self._task_config.type != task_type:
            return None
        return self._task_config

    def reload_global(self) -> None:  # pragma: no cover - unused
        raise NotImplementedError

    def reload_task(self, task_type: str) -> None:
        self.reload_calls.append(task_type)


class _TaskConfigRepoStub(TaskConfigRepository):
    def __init__(self) -> None:
        self.updated_configs: list[TaskConfig] = []

    def get_by_type(self, task_type: str) -> TaskConfig | None:  # pragma: no cover
        raise NotImplementedError

    def update(self, config: TaskConfig) -> None:
        self.updated_configs.append(config)


def test_get_jav_video_organizer_config_returns_typed_config() -> None:
    config_manager = _ConfigManagerStub(_task_config())

    config = FileTaskConfigService.get_jav_video_organizer_config(config_manager)

    assert isinstance(config, JavVideoOrganizeConfig)
    assert ".mp4" in config.video_extensions


def test_merge_jav_video_organizer_config_merges_updates() -> None:
    current = JavVideoOrganizeConfig(
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


def test_validate_and_save_jav_video_organizer_config_updates_repo_and_cache() -> None:
    task_config = _task_config()
    config_manager = _ConfigManagerStub(task_config)
    repository = _TaskConfigRepoStub()
    merged_config = FileTaskConfigService.get_jav_video_organizer_config(
        config_manager,
    )

    FileTaskConfigService.validate_and_save_jav_video_organizer_config(
        merged_config,
        repository,
        config_manager,
    )

    assert repository.updated_configs
    assert config_manager.reload_calls == [TASK_TYPE_JAV_VIDEO_ORGANIZER]


def test_get_jav_video_organizer_config_raises_when_missing() -> None:
    config_manager = _ConfigManagerStub(None)

    with pytest.raises(ValueError, match="任务配置不存在"):
        FileTaskConfigService.get_jav_video_organizer_config(config_manager)
