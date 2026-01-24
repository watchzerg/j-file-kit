from pathlib import Path

import pytest

from j_file_kit.app.config.domain.models import AppConfig
from j_file_kit.infrastructure.config import config_manager as config_manager_module
from j_file_kit.infrastructure.config.config_manager import ConfigManagerImpl
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)

pytestmark = pytest.mark.unit


def _build_app_config(inbox_dir: str) -> AppConfig:
    return AppConfig.model_validate(
        {"global": {"inbox_dir": inbox_dir}, "tasks": []},
    )


def test_config_manager_loads_config_on_init(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded: list[object] = []
    expected_config = _build_app_config("inbox-a")

    def _load_stub(conn_manager: object) -> AppConfig:
        loaded.append(conn_manager)
        return expected_config

    monkeypatch.setattr(config_manager_module, "load_app_config_from_db", _load_stub)

    conn_manager = SQLiteConnectionManager(Path(":memory:"))
    manager = ConfigManagerImpl(conn_manager)

    assert loaded == [conn_manager]
    assert manager.config == expected_config


def test_config_manager_reload_refreshes_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configs = [
        _build_app_config("inbox-a"),
        _build_app_config("inbox-b"),
    ]

    def _load_stub(_conn_manager: object) -> AppConfig:
        return configs.pop(0)

    monkeypatch.setattr(config_manager_module, "load_app_config_from_db", _load_stub)

    manager = ConfigManagerImpl(SQLiteConnectionManager(Path(":memory:")))

    assert manager.config.global_.inbox_dir == Path("inbox-a")

    manager.reload()

    assert manager.config.global_.inbox_dir == Path("inbox-b")
