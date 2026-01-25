from pathlib import Path

import pytest

from j_file_kit.app.config.domain.models import GlobalConfig, TaskConfig
from j_file_kit.infrastructure.config import config_manager as config_manager_module
from j_file_kit.infrastructure.config.config_manager import ConfigManagerImpl
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)

pytestmark = pytest.mark.unit


def _build_global_config(inbox_dir: str) -> GlobalConfig:
    return GlobalConfig.model_validate({"inbox_dir": inbox_dir})


def _build_task_configs(name: str) -> list[TaskConfig]:
    return [
        TaskConfig(
            name=name,
            type="file_organize",
            enabled=True,
            config={},
        ),
    ]


def test_config_manager_loads_config_on_init(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_global: list[object] = []
    loaded_tasks: list[object] = []
    expected_global = _build_global_config("inbox-a")
    expected_tasks = _build_task_configs("task-a")

    def _load_global_stub(conn_manager: object) -> GlobalConfig:
        loaded_global.append(conn_manager)
        return expected_global

    def _load_tasks_stub(conn_manager: object) -> list[TaskConfig]:
        loaded_tasks.append(conn_manager)
        return expected_tasks

    monkeypatch.setattr(
        config_manager_module,
        "load_global_config_from_db",
        _load_global_stub,
    )
    monkeypatch.setattr(
        config_manager_module,
        "load_task_configs_from_db",
        _load_tasks_stub,
    )

    conn_manager = SQLiteConnectionManager(Path(":memory:"))
    manager = ConfigManagerImpl(conn_manager)

    assert loaded_global == [conn_manager]
    assert loaded_tasks == [conn_manager]
    assert manager.get_global_config() == expected_global
    assert manager.get_task_configs() == expected_tasks


def test_config_manager_reload_refreshes_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    globals_ = [
        _build_global_config("inbox-a"),
        _build_global_config("inbox-b"),
    ]
    tasks = [
        _build_task_configs("task-a"),
        _build_task_configs("task-b"),
    ]

    def _load_global_stub(_conn_manager: object) -> GlobalConfig:
        return globals_.pop(0)

    def _load_tasks_stub(_conn_manager: object) -> list[TaskConfig]:
        return tasks.pop(0)

    monkeypatch.setattr(
        config_manager_module,
        "load_global_config_from_db",
        _load_global_stub,
    )
    monkeypatch.setattr(
        config_manager_module,
        "load_task_configs_from_db",
        _load_tasks_stub,
    )

    manager = ConfigManagerImpl(SQLiteConnectionManager(Path(":memory:")))

    assert manager.get_global_config().inbox_dir == Path("inbox-a")
    assert manager.get_task_configs()[0].name == "task-a"

    manager.reload_global()
    manager.reload_tasks()

    assert manager.get_global_config().inbox_dir == Path("inbox-b")
    assert manager.get_task_configs()[0].name == "task-b"
