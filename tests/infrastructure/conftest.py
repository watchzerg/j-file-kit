"""infrastructure 集成测试 fixtures

适合放置：真实文件系统临时目录（tmp_path 扩展）、SQLite 连接、YAML 仓储实例。
"""

from pathlib import Path

import pytest

from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.schema import SQLiteSchemaInitializer


@pytest.fixture
def sqlite_connection_manager() -> SQLiteConnectionManager:
    manager = SQLiteConnectionManager(Path(":memory:"))
    initializer = SQLiteSchemaInitializer(manager)
    initializer.initialize()
    return manager
