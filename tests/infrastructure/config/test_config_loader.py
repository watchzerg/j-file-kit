from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.config import (
    create_default_jav_video_organizer_task_config,
)
from j_file_kit.app.global_config.domain.models import create_default_global_config
from j_file_kit.infrastructure.config.config_loader import (
    load_global_config_from_db,
)
from j_file_kit.infrastructure.persistence.sqlite.config.default_global_config_initializer import (
    DefaultGlobalConfigInitializer,
)
from j_file_kit.infrastructure.persistence.sqlite.config.default_task_config_initializer import (
    DefaultTaskConfigInitializer,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.schema import (
    SQLiteSchemaInitializer,
)

pytestmark = pytest.mark.unit


def test_load_global_config_from_db_returns_default_config() -> None:
    conn_manager = SQLiteConnectionManager(Path(":memory:"))
    SQLiteSchemaInitializer(conn_manager).initialize()
    DefaultGlobalConfigInitializer(conn_manager).initialize()
    DefaultTaskConfigInitializer(
        conn_manager,
        [create_default_jav_video_organizer_task_config()],
    ).initialize()

    config = load_global_config_from_db(conn_manager)

    assert config.model_dump() == create_default_global_config().model_dump()


def test_load_global_config_from_db_wraps_repository_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _GlobalRepositoryStub:
        def __init__(self, _conn_manager: SQLiteConnectionManager) -> None:
            pass

        def get_global_config(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "j_file_kit.infrastructure.config.config_loader.GlobalConfigRepositoryImpl",
        _GlobalRepositoryStub,
    )

    conn_manager = SQLiteConnectionManager(Path(":memory:"))
    SQLiteSchemaInitializer(conn_manager).initialize()
    DefaultGlobalConfigInitializer(conn_manager).initialize()
    DefaultTaskConfigInitializer(
        conn_manager,
        [create_default_jav_video_organizer_task_config()],
    ).initialize()

    with pytest.raises(ValueError, match="从数据库加载全局配置失败"):
        load_global_config_from_db(conn_manager)
