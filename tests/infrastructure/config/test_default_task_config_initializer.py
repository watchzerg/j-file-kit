import json
from datetime import datetime
from pathlib import Path

import pytest

from j_file_kit.app.task_config.domain.models import TaskConfig
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


def _build_default_task_config(task_type: str) -> TaskConfig:
    return TaskConfig(
        type=task_type,
        enabled=True,
        config={"video_extensions": [".mp4"]},
    )


def test_default_task_config_initializer_inserts_defaults() -> None:
    conn_manager = SQLiteConnectionManager(Path(":memory:"))
    SQLiteSchemaInitializer(conn_manager).initialize()

    default_configs = [_build_default_task_config("task-a")]
    DefaultTaskConfigInitializer(conn_manager, default_configs).initialize()

    with conn_manager.get_cursor() as cursor:
        cursor.execute("SELECT type, enabled, config FROM config_task")
        rows = cursor.fetchall()

    assert len(rows) == 1
    task_type, enabled, config_json = rows[0]
    assert task_type == "task-a"
    assert bool(enabled) is True
    assert json.loads(config_json) == {"video_extensions": [".mp4"]}


def test_default_task_config_initializer_skips_when_table_not_empty() -> None:
    conn_manager = SQLiteConnectionManager(Path(":memory:"))
    SQLiteSchemaInitializer(conn_manager).initialize()

    with conn_manager.get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO config_task (type, enabled, config, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                "task-existing",
                True,
                json.dumps({"video_extensions": [".avi"]}),
                datetime.now().isoformat(),
            ),
        )

    default_configs = [_build_default_task_config("task-new")]
    DefaultTaskConfigInitializer(conn_manager, default_configs).initialize()

    with conn_manager.get_cursor() as cursor:
        cursor.execute("SELECT type FROM config_task")
        rows = cursor.fetchall()

    assert [row[0] for row in rows] == ["task-existing"]
