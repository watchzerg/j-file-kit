"""默认任务配置初始化器。"""

import json
import sqlite3
from datetime import datetime

from j_file_kit.app.config.domain.models import create_default_task_configs
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class DefaultTaskConfigInitializer:
    """默认任务配置初始化器。

    仅负责在任务配置表为空时插入默认数据。
    """

    def __init__(self, conn_manager: SQLiteConnectionManager) -> None:
        self._conn_manager = conn_manager

    def initialize(self) -> None:
        """初始化默认任务配置数据。"""
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM config_task")
            if cursor.fetchone()[0] == 0:
                self._insert_default_task_configs(cursor)

    def _insert_default_task_configs(self, cursor: sqlite3.Cursor) -> None:
        default_tasks = create_default_task_configs()
        updated_at = datetime.now().isoformat()
        for task in default_tasks:
            config_json = json.dumps(task.config)
            cursor.execute(
                """
                INSERT INTO config_task (name, type, enabled, config, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task.name, task.type, task.enabled, config_json, updated_at),
            )
