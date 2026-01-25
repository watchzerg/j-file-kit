from pathlib import Path

import pytest

from j_file_kit.app.global_config.domain.models import GlobalConfig
from j_file_kit.infrastructure.config import global_config_manager as manager_module
from j_file_kit.infrastructure.config.global_config_manager import (
    GlobalConfigManagerImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)

pytestmark = pytest.mark.unit


def _build_global_config(inbox_dir: str) -> GlobalConfig:
    return GlobalConfig.model_validate({"inbox_dir": inbox_dir})


def test_manager_loads_config_on_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试管理器在初始化时加载配置"""
    expected_config = _build_global_config("inbox-a")
    loaded_conns: list[object] = []

    class _RepositoryStub:
        def __init__(self, conn_manager: object) -> None:
            loaded_conns.append(conn_manager)

        def get_global_config(self) -> GlobalConfig:
            return expected_config

    monkeypatch.setattr(
        manager_module,
        "GlobalConfigRepositoryImpl",
        _RepositoryStub,
    )

    conn_manager = SQLiteConnectionManager(Path(":memory:"))
    manager = GlobalConfigManagerImpl(conn_manager)

    assert len(loaded_conns) == 1
    assert loaded_conns[0] is conn_manager
    assert manager.get_global_config() == expected_config


def test_manager_reload_refreshes_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试 reload 方法刷新缓存"""
    configs = [
        _build_global_config("inbox-a"),
        _build_global_config("inbox-b"),
    ]

    class _RepositoryStub:
        def __init__(self, _conn_manager: object) -> None:
            pass

        def get_global_config(self) -> GlobalConfig:
            return configs.pop(0)

    monkeypatch.setattr(
        manager_module,
        "GlobalConfigRepositoryImpl",
        _RepositoryStub,
    )

    manager = GlobalConfigManagerImpl(SQLiteConnectionManager(Path(":memory:")))

    assert manager.get_global_config().inbox_dir == Path("inbox-a")

    manager.reload_global()

    assert manager.get_global_config().inbox_dir == Path("inbox-b")


def test_manager_wraps_repository_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试管理器包装仓储异常"""

    class _RepositoryStub:
        def __init__(self, _conn_manager: object) -> None:
            pass

        def get_global_config(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        manager_module,
        "GlobalConfigRepositoryImpl",
        _RepositoryStub,
    )

    with pytest.raises(ValueError, match="从数据库加载全局配置失败"):
        GlobalConfigManagerImpl(SQLiteConnectionManager(Path(":memory:")))
