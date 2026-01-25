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


def _build_task_config(name: str, task_type: str) -> TaskConfig:
    return TaskConfig(
        name=name,
        type=task_type,
        enabled=True,
        config={},
    )


def test_config_manager_loads_config_on_init(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_global: list[object] = []
    expected_global = _build_global_config("inbox-a")
    task_type = "task-a"
    expected_task = _build_task_config("task-a", task_type)

    def _load_global_stub(conn_manager: object) -> GlobalConfig:
        loaded_global.append(conn_manager)
        return expected_global

    tasks_by_call: list[TaskConfig] = [expected_task]

    class _TaskRepositoryStub:
        def __init__(self, _conn_manager: object) -> None:
            pass

        def get_by_type(self, _task_type: str) -> TaskConfig | None:
            return tasks_by_call.pop(0)

    monkeypatch.setattr(
        config_manager_module,
        "load_global_config_from_db",
        _load_global_stub,
    )
    monkeypatch.setattr(
        config_manager_module,
        "TaskConfigRepositoryImpl",
        _TaskRepositoryStub,
    )

    conn_manager = SQLiteConnectionManager(Path(":memory:"))
    manager = ConfigManagerImpl(conn_manager)

    assert loaded_global == [conn_manager]
    assert manager.get_global_config() == expected_global
    assert tasks_by_call == [expected_task]
    assert manager.get_task_config_by_type(task_type) == expected_task


def test_config_manager_reload_refreshes_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    globals_ = [
        _build_global_config("inbox-a"),
        _build_global_config("inbox-b"),
    ]
    task_type = "task-a"
    tasks_by_call = [
        _build_task_config("task-a", task_type),
        _build_task_config("task-b", task_type),
    ]

    def _load_global_stub(_conn_manager: object) -> GlobalConfig:
        return globals_.pop(0)

    class _TaskRepositoryStub:
        def __init__(self, _conn_manager: object) -> None:
            pass

        def get_by_type(self, _task_type: str) -> TaskConfig | None:
            return tasks_by_call.pop(0)

    monkeypatch.setattr(
        config_manager_module,
        "load_global_config_from_db",
        _load_global_stub,
    )
    monkeypatch.setattr(
        config_manager_module,
        "TaskConfigRepositoryImpl",
        _TaskRepositoryStub,
    )

    manager = ConfigManagerImpl(SQLiteConnectionManager(Path(":memory:")))

    assert manager.get_global_config().inbox_dir == Path("inbox-a")
    task_config = manager.get_task_config_by_type(task_type)
    assert task_config is not None
    assert task_config.name == "task-a"

    manager.reload_global()
    manager.reload_task(task_type)

    assert manager.get_global_config().inbox_dir == Path("inbox-b")
    task_config = manager.get_task_config_by_type(task_type)
    assert task_config is not None
    assert task_config.name == "task-b"
