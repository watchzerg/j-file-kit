"""默认配置初始化器。"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from j_file_kit.app.config.domain.models import (
    create_default_global_config,
    create_default_task_configs,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class DefaultConfigInitializer:
    """默认配置初始化器。

    负责在数据库为空时插入默认配置，不承担仓储读取职责。
    """

    def __init__(self, conn_manager: SQLiteConnectionManager) -> None:
        self._conn_manager = conn_manager

    def initialize(self) -> None:
        """初始化默认配置数据。"""
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM global_config")
            if cursor.fetchone()[0] == 0:
                self._insert_default_global_config(cursor)

            cursor.execute("SELECT COUNT(*) FROM task_configs")
            if cursor.fetchone()[0] == 0:
                self._insert_default_task_configs(cursor)

    def _insert_default_global_config(self, cursor: sqlite3.Cursor) -> None:
        default_global = create_default_global_config()
        updated_at = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO global_config (id, inbox_dir, sorted_dir, unsorted_dir, archive_dir, misc_dir, starred_dir, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._path_to_str(default_global.inbox_dir),
                self._path_to_str(default_global.sorted_dir),
                self._path_to_str(default_global.unsorted_dir),
                self._path_to_str(default_global.archive_dir),
                self._path_to_str(default_global.misc_dir),
                self._path_to_str(default_global.starred_dir),
                updated_at,
            ),
        )

    def _insert_default_task_configs(self, cursor: sqlite3.Cursor) -> None:
        default_tasks = create_default_task_configs()
        updated_at = datetime.now().isoformat()
        for task in default_tasks:
            config_json = json.dumps(task.config)
            cursor.execute(
                """
                INSERT INTO task_configs (name, type, enabled, config, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task.name, task.type, task.enabled, config_json, updated_at),
            )

    def _path_to_str(self, path: Path | None) -> str:
        return str(path) if path else ""
