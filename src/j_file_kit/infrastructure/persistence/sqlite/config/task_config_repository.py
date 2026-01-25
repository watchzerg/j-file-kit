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

    仅处理任务配置的读取、创建、更新与删除。
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

    def get_all_task_configs(self) -> list[TaskConfig]:
        """获取所有任务配置。

        Returns:
            任务配置列表
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT name, type, enabled, config FROM config_task ORDER BY name",
            )
            rows = cursor.fetchall()

            return [self._row_to_task_config(row) for row in rows]

    def get_task_config(self, name: str) -> TaskConfig | None:
        """获取单个任务配置。

        Args:
            name: 任务名称

        Returns:
            任务配置对象，如果不存在则返回 None
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT name, type, enabled, config FROM config_task WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_task_config(row)

    def update_task_config(self, task: TaskConfig) -> None:
        """更新任务配置。

        Args:
            task: 任务配置对象

        Raises:
            ValueError: 如果任务不存在
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute("SELECT name FROM config_task WHERE name = ?", (task.name,))
            if cursor.fetchone() is None:
                raise ValueError(f"任务不存在: {task.name}")

            config_json = json.dumps(task.config)
            updated_at = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE config_task
                SET type = ?, enabled = ?, config = ?, updated_at = ?
                WHERE name = ?
                """,
                (task.type, task.enabled, config_json, updated_at, task.name),
            )

    def create_task_config(self, task: TaskConfig) -> None:
        """创建任务配置。

        Args:
            task: 任务配置对象

        Raises:
            ValueError: 如果任务已存在
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute("SELECT name FROM config_task WHERE name = ?", (task.name,))
            if cursor.fetchone() is not None:
                raise ValueError(f"任务已存在: {task.name}")

            config_json = json.dumps(task.config)
            updated_at = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO config_task (name, type, enabled, config, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task.name, task.type, task.enabled, config_json, updated_at),
            )

    def delete_task_config(self, name: str) -> None:
        """删除任务配置。

        Args:
            name: 任务名称

        Raises:
            ValueError: 如果任务不存在
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute("SELECT name FROM config_task WHERE name = ?", (name,))
            if cursor.fetchone() is None:
                raise ValueError(f"任务不存在: {name}")

            cursor.execute("DELETE FROM config_task WHERE name = ?", (name,))
