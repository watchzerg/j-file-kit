from pathlib import Path
from typing import cast

import pytest

from j_file_kit.app.global_config.application.global_config_service import (
    GlobalConfigService,
)
from j_file_kit.app.global_config.application.schemas import (
    UpdateGlobalConfigRequest,
)
from j_file_kit.app.global_config.domain.exceptions import (
    ConfigReloadError,
    ConfigUpdateError,
    InvalidConfigError,
    InvalidPathError,
)
from j_file_kit.app.global_config.domain.models import GlobalConfig
from j_file_kit.app.global_config.domain.ports import (
    GlobalConfigManager,
    GlobalConfigRepository,
)

pytestmark = pytest.mark.unit


class _GlobalRepoStub(GlobalConfigRepository):
    def __init__(self, *, fail_update: bool = False) -> None:
        self.fail_update = fail_update
        self.updated_global: GlobalConfig | None = None

    def get_global_config(self) -> GlobalConfig:  # pragma: no cover - not used
        raise NotImplementedError

    def update_global_config(self, config: GlobalConfig) -> None:
        if self.fail_update:
            raise RuntimeError("db failure")
        self.updated_global = config


class _ManagerStub(GlobalConfigManager):
    def __init__(self, *, fail_reload: bool = False) -> None:
        self.fail_reload = fail_reload
        self.reload_global_called = False

    def get_global_config(self) -> GlobalConfig:  # pragma: no cover - not used
        return _global_config()

    def reload_global(self) -> None:
        if self.fail_reload:
            raise RuntimeError("reload failure")
        self.reload_global_called = True


def _global_config(inbox: str | None = "inbox") -> GlobalConfig:
    return GlobalConfig(
        inbox_dir=Path(inbox) if inbox is not None else None,
        sorted_dir=None,
        unsorted_dir=None,
        archive_dir=None,
        misc_dir=None,
        starred_dir=None,
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


def test_merge_global_config_returns_current_when_no_updates() -> None:
    current = _global_config()
    update = _global_update()

    merged = GlobalConfigService.merge_global_config(current, update)

    assert merged is current


def test_merge_global_config_updates_and_clears_fields() -> None:
    current = _global_config()
    update = _global_update(inbox_dir="/new/inbox", sorted_dir="")

    merged = GlobalConfigService.merge_global_config(current, update)

    assert merged.inbox_dir == Path("/new/inbox")
    assert merged.sorted_dir is None


def test_validate_and_save_global_config_success() -> None:
    global_repo = _GlobalRepoStub()
    manager = _ManagerStub()
    global_config = _global_config()

    GlobalConfigService.validate_and_save_global_config(
        merged_global=global_config,
        global_config_repository=global_repo,
        global_config_manager=manager,
    )

    assert global_repo.updated_global is global_config
    assert manager.reload_global_called is True


def test_validate_and_save_global_config_invalid_config_raises() -> None:
    global_repo = _GlobalRepoStub()
    manager = _ManagerStub()
    invalid_global = cast(GlobalConfig, "invalid")

    with pytest.raises(InvalidConfigError):
        GlobalConfigService.validate_and_save_global_config(
            merged_global=invalid_global,
            global_config_repository=global_repo,
            global_config_manager=manager,
        )


def test_validate_and_save_global_config_invalid_path_raises() -> None:
    global_repo = _GlobalRepoStub()
    manager = _ManagerStub()

    with pytest.raises(InvalidPathError):
        GlobalConfigService.validate_and_save_global_config(
            merged_global=_global_config(inbox=None),
            global_config_repository=global_repo,
            global_config_manager=manager,
        )


def test_validate_and_save_global_config_update_error_raises() -> None:
    global_repo = _GlobalRepoStub(fail_update=True)
    manager = _ManagerStub()

    with pytest.raises(ConfigUpdateError):
        GlobalConfigService.validate_and_save_global_config(
            merged_global=_global_config(),
            global_config_repository=global_repo,
            global_config_manager=manager,
        )


def test_validate_and_save_global_config_reload_error_raises() -> None:
    global_repo = _GlobalRepoStub()
    manager = _ManagerStub(fail_reload=True)

    with pytest.raises(ConfigReloadError):
        GlobalConfigService.validate_and_save_global_config(
            merged_global=_global_config(),
            global_config_repository=global_repo,
            global_config_manager=manager,
        )
