"""任务配置仓储实现。"""

import json
import sqlite3
from datetime import datetime

from j_file_kit.app.config.domain.models import TaskConfig
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class TaskConfigRepositoryImpl:
    """任务配置仓储实现。

    仅处理任务配置的读取与更新（按任务类型单条操作）。
    """

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        """初始化任务配置仓储。

        Args:
            connection_manager: SQLite 连接管理器
        """
        self._conn_manager = connection_manager

    def _row_to_task_config(self, row: sqlite3.Row) -> TaskConfig:
        """将数据库行转换为 TaskConfig 对象。

        Args:
            row: 数据库行

        Returns:
            TaskConfig 对象
        """
        config_dict = json.loads(row["config"])
        return TaskConfig(
            name=row["name"],
            type=row["type"],
            enabled=bool(row["enabled"]),
            config=config_dict,
        )

    def get_by_type(self, task_type: str) -> TaskConfig | None:
        """根据任务类型获取任务配置。

        Args:
            task_type: 任务类型

        Returns:
            任务配置对象，如果不存在则返回 None
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT name, type, enabled, config FROM config_task WHERE type = ?",
                (task_type,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_task_config(row)

    def update(self, config: TaskConfig) -> None:
        """更新任务配置。

        Args:
            config: 任务配置对象

        Raises:
            ValueError: 如果任务不存在
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT name FROM config_task WHERE type = ?",
                (config.type,),
            )
            if cursor.fetchone() is None:
                raise ValueError(f"任务配置不存在: {config.type}")

            config_json = json.dumps(config.config)
            updated_at = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE config_task
                SET name = ?, enabled = ?, config = ?, updated_at = ?
                WHERE type = ?
                """,
                (config.name, config.enabled, config_json, updated_at, config.type),
            )
