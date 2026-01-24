from pathlib import Path
from typing import cast

import pytest

from j_file_kit.app.config.application.config_service import ConfigService
from j_file_kit.app.config.application.schemas import (
    UpdateGlobalConfigRequest,
    UpdateTaskConfigRequest,
)
from j_file_kit.app.config.domain.exceptions import (
    ConfigReloadError,
    ConfigUpdateError,
    InvalidConfigError,
    InvalidPathError,
    InvalidTaskConfigError,
    MissingTaskNameError,
    TaskConfigNotFoundError,
)
from j_file_kit.app.config.domain.models import AppConfig, GlobalConfig, TaskConfig
from j_file_kit.app.config.domain.ports import AppConfigRepository, ConfigStateManager

pytestmark = pytest.mark.unit


class _RepoStub(AppConfigRepository):
    def __init__(self, *, fail_update: bool = False) -> None:
        self.fail_update = fail_update
        self.updated_global: GlobalConfig | None = None
        self.updated_tasks: list[TaskConfig] = []

    def get_global_config(self) -> GlobalConfig:  # pragma: no cover - not used
        raise NotImplementedError

    def update_global_config(self, config: GlobalConfig) -> None:
        if self.fail_update:
            raise RuntimeError("db failure")
        self.updated_global = config

    def get_all_tasks(self) -> list[TaskConfig]:  # pragma: no cover - not used
        raise NotImplementedError

    def get_task(self, name: str) -> TaskConfig | None:  # pragma: no cover - not used
        raise NotImplementedError

    def update_task(self, task: TaskConfig) -> None:
        if self.fail_update:
            raise RuntimeError("db failure")
        self.updated_tasks.append(task)

    def create_task(self, task: TaskConfig) -> None:  # pragma: no cover - not used
        raise NotImplementedError

    def delete_task(self, name: str) -> None:  # pragma: no cover - not used
        raise NotImplementedError


class _ManagerStub(ConfigStateManager):
    def __init__(self, *, fail_reload: bool = False) -> None:
        self.fail_reload = fail_reload
        self.reload_called = False

    @property
    def config(self) -> AppConfig:  # pragma: no cover - not used
        raise NotImplementedError

    def reload(self) -> None:
        if self.fail_reload:
            raise RuntimeError("reload failure")
        self.reload_called = True


def _global_config(inbox: str | None = "inbox") -> GlobalConfig:
    return GlobalConfig(
        inbox_dir=Path(inbox) if inbox is not None else None,
        sorted_dir=None,
        unsorted_dir=None,
        archive_dir=None,
        misc_dir=None,
        starred_dir=None,
    )


def _task_config(name: str = "demo", enabled: bool = True) -> TaskConfig:
    return TaskConfig(
        name=name,
        type="file_organize",
        enabled=enabled,
        config={"a": 1, "b": 2},
    )


def _global_update(
    *,
    inbox_dir: str | None = None,
    sorted_dir: str | None = None,
    unsorted_dir: str | None = None,
    archive_dir: str | None = None,
    misc_dir: str | None = None,
    starred_dir: str | None = None,
) -> UpdateGlobalConfigRequest:
    return UpdateGlobalConfigRequest(
        inbox_dir=inbox_dir,
        sorted_dir=sorted_dir,
        unsorted_dir=unsorted_dir,
        archive_dir=archive_dir,
        misc_dir=misc_dir,
        starred_dir=starred_dir,
    )


def _task_update(
    *,
    name: str | None = None,
    enabled: bool | None = None,
    config: dict[str, int] | None = None,
) -> UpdateTaskConfigRequest:
    return UpdateTaskConfigRequest(name=name, enabled=enabled, config=config)


def test_merge_global_config_returns_current_when_no_updates() -> None:
    current = _global_config()
    update = _global_update()

    merged = ConfigService.merge_global_config(current, update)

    assert merged is current


def test_merge_global_config_updates_and_clears_fields() -> None:
    current = _global_config()
    update = _global_update(inbox_dir="/new/inbox", sorted_dir="")

    merged = ConfigService.merge_global_config(current, update)

    assert merged.inbox_dir == Path("/new/inbox")
    assert merged.sorted_dir is None


def test_merge_task_config_updates_fields_and_merges_config() -> None:
    current = _task_config()
    update = _task_update(
        name="updated",
        enabled=False,
        config={"b": 3, "c": 4},
    )

    merged = ConfigService.merge_task_config(current, update)

    assert merged.name == "updated"
    assert merged.enabled is False
    assert merged.config == {"a": 1, "b": 3, "c": 4}


def test_merge_task_config_returns_current_when_no_updates() -> None:
    current = _task_config()
    update = _task_update()

    merged = ConfigService.merge_task_config(current, update)

    assert merged is current


def test_merge_all_task_configs_requires_task_name() -> None:
    with pytest.raises(MissingTaskNameError):
        ConfigService.merge_all_task_configs(
            current_tasks=[_task_config()],
            task_updates=[_task_update()],
        )


def test_merge_all_task_configs_requires_existing_task() -> None:
    with pytest.raises(TaskConfigNotFoundError):
        ConfigService.merge_all_task_configs(
            current_tasks=[_task_config(name="a")],
            task_updates=[_task_update(name="missing")],
        )


def test_merge_all_task_configs_wraps_merge_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_error(*_args: object, **_kwargs: object) -> TaskConfig:
        raise ValueError("bad config")

    monkeypatch.setattr(ConfigService, "merge_task_config", _raise_error)

    with pytest.raises(InvalidTaskConfigError):
        ConfigService.merge_all_task_configs(
            current_tasks=[_task_config(name="a")],
            task_updates=[_task_update(name="a")],
        )


def test_validate_and_save_config_success() -> None:
    repo = _RepoStub()
    manager = _ManagerStub()
    global_config = _global_config()
    tasks = [_task_config(name="a"), _task_config(name="b")]

    ConfigService.validate_and_save_config(
        merged_global=global_config,
        merged_tasks=tasks,
        config_repository=repo,
        config_manager=manager,
    )

    assert repo.updated_global is global_config
    assert repo.updated_tasks == tasks
    assert manager.reload_called is True


def test_validate_and_save_config_invalid_config_raises() -> None:
    repo = _RepoStub()
    manager = _ManagerStub()
    global_config = _global_config()
    bad_tasks = cast(list[TaskConfig], ["invalid"])

    with pytest.raises(InvalidConfigError):
        ConfigService.validate_and_save_config(
            merged_global=global_config,
            merged_tasks=bad_tasks,
            config_repository=repo,
            config_manager=manager,
        )


def test_validate_and_save_config_invalid_path_raises() -> None:
    repo = _RepoStub()
    manager = _ManagerStub()

    with pytest.raises(InvalidPathError):
        ConfigService.validate_and_save_config(
            merged_global=_global_config(inbox=None),
            merged_tasks=[_task_config()],
            config_repository=repo,
            config_manager=manager,
        )


def test_validate_and_save_config_update_error_raises() -> None:
    repo = _RepoStub(fail_update=True)
    manager = _ManagerStub()

    with pytest.raises(ConfigUpdateError):
        ConfigService.validate_and_save_config(
            merged_global=_global_config(),
            merged_tasks=[_task_config()],
            config_repository=repo,
            config_manager=manager,
        )


def test_validate_and_save_config_reload_error_raises() -> None:
    repo = _RepoStub()
    manager = _ManagerStub(fail_reload=True)

    with pytest.raises(ConfigReloadError):
        ConfigService.validate_and_save_config(
            merged_global=_global_config(),
            merged_tasks=[_task_config()],
            config_repository=repo,
            config_manager=manager,
        )
