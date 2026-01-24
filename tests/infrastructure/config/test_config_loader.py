from pathlib import Path

import pytest

from j_file_kit.app.config.domain.models import (
    AppConfig,
    create_default_global_config,
    create_default_task_configs,
)
from j_file_kit.infrastructure.config.config_loader import load_app_config_from_db
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)

pytestmark = pytest.mark.unit


def test_load_app_config_from_db_returns_default_config() -> None:
    conn_manager = SQLiteConnectionManager(Path(":memory:"))

    config = load_app_config_from_db(conn_manager)

    assert isinstance(config, AppConfig)
    assert config.global_.model_dump() == create_default_global_config().model_dump()
    assert [task.model_dump() for task in config.tasks] == [
        task.model_dump() for task in create_default_task_configs()
    ]


def test_load_app_config_from_db_wraps_repository_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RepositoryStub:
        def __init__(self, _conn_manager: SQLiteConnectionManager) -> None:
            pass

        def get_global_config(self) -> None:
            raise RuntimeError("boom")

        def get_all_tasks(self) -> list[object]:
            return []

    monkeypatch.setattr(
        "j_file_kit.infrastructure.config.config_loader.AppConfigRepositoryImpl",
        _RepositoryStub,
    )

    conn_manager = SQLiteConnectionManager(Path(":memory:"))

    with pytest.raises(ValueError, match="从数据库加载配置失败"):
        load_app_config_from_db(conn_manager)
