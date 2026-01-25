from pathlib import Path

import pytest

from j_file_kit.app.task_config.domain.models import TaskConfig
from j_file_kit.infrastructure.config import task_config_manager as manager_module
from j_file_kit.infrastructure.config.task_config_manager import (
    TaskConfigManagerImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)

pytestmark = pytest.mark.unit


def _build_task_config(task_type: str) -> TaskConfig:
    return TaskConfig(
        type=task_type,
        enabled=True,
        config={},
    )


def test_manager_lazy_loads_task_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试管理器按需加载任务配置"""
    task_type = "task-a"
    expected_config = _build_task_config(task_type)
    load_calls: list[str] = []

    class _RepositoryStub:
        def __init__(self, _conn_manager: object) -> None:
            pass

        def get_by_type(self, task_type: str) -> TaskConfig:
            load_calls.append(task_type)
            return expected_config

    monkeypatch.setattr(
        manager_module,
        "TaskConfigRepositoryImpl",
        _RepositoryStub,
    )

    manager = TaskConfigManagerImpl(SQLiteConnectionManager(Path(":memory:")))

    assert load_calls == []

    config = manager.get_task_config_by_type(task_type)
    assert config == expected_config
    assert load_calls == [task_type]

    config = manager.get_task_config_by_type(task_type)
    assert config == expected_config
    assert load_calls == [task_type]


def test_manager_reload_refreshes_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试 reload 方法刷新缓存"""
    task_type = "task-a"
    configs = [
        _build_task_config(task_type),
        _build_task_config(task_type),
    ]

    class _RepositoryStub:
        def __init__(self, _conn_manager: object) -> None:
            pass

        def get_by_type(self, _task_type: str) -> TaskConfig | None:
            return configs.pop(0)

    monkeypatch.setattr(
        manager_module,
        "TaskConfigRepositoryImpl",
        _RepositoryStub,
    )

    manager = TaskConfigManagerImpl(SQLiteConnectionManager(Path(":memory:")))

    first_config = manager.get_task_config_by_type(task_type)
    assert first_config is not None

    manager.reload_task(task_type)

    second_config = manager.get_task_config_by_type(task_type)
    assert second_config is not None
    assert second_config is not first_config


def test_manager_returns_none_for_missing_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试管理器对不存在的配置返回 None"""

    class _RepositoryStub:
        def __init__(self, _conn_manager: object) -> None:
            pass

        def get_by_type(self, _task_type: str) -> TaskConfig | None:
            return None

    monkeypatch.setattr(
        manager_module,
        "TaskConfigRepositoryImpl",
        _RepositoryStub,
    )

    manager = TaskConfigManagerImpl(SQLiteConnectionManager(Path(":memory:")))

    config = manager.get_task_config_by_type("non-existent")
    assert config is None


def test_manager_reload_raises_for_missing_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试 reload 不存在的配置时抛出异常"""

    class _RepositoryStub:
        def __init__(self, _conn_manager: object) -> None:
            pass

        def get_by_type(self, _task_type: str) -> TaskConfig | None:
            return None

    monkeypatch.setattr(
        manager_module,
        "TaskConfigRepositoryImpl",
        _RepositoryStub,
    )

    manager = TaskConfigManagerImpl(SQLiteConnectionManager(Path(":memory:")))

    with pytest.raises(ValueError, match="任务配置不存在: non-existent"):
        manager.reload_task("non-existent")
