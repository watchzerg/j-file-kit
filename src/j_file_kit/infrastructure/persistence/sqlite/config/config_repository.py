"""配置仓储

提供配置数据的持久化操作，包括全局配置和任务配置的 CRUD。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from j_file_kit.app.config.domain.models import (
    GlobalConfig,
    TaskConfig,
    create_default_global_config,
    create_default_task_configs,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class AppConfigRepositoryImpl:
    """应用配置仓储实现

    实现 AppConfigRepository Protocol，提供应用配置数据的持久化操作。
    包括全局配置和任务配置的 CRUD 操作。
    """

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        """初始化配置仓储

        Args:
            connection_manager: SQLite 连接管理器
        """
        self._conn_manager = connection_manager
        self._ensure_default_config()

    def _row_to_global_config(self, row: sqlite3.Row) -> GlobalConfig:
        """将数据库行转换为 GlobalConfig 对象

        Args:
            row: 数据库行

        Returns:
            GlobalConfig 对象
        """

        def to_path(value: str) -> Path | None:
            return Path(value) if value else None

        return GlobalConfig(
            inbox_dir=to_path(row["inbox_dir"]),
            sorted_dir=to_path(row["sorted_dir"]),
            unsorted_dir=to_path(row["unsorted_dir"]),
            archive_dir=to_path(row["archive_dir"]),
            misc_dir=to_path(row["misc_dir"]),
            starred_dir=to_path(row["starred_dir"]),
        )

    def _row_to_task_config(self, row: sqlite3.Row) -> TaskConfig:
        """将数据库行转换为 TaskConfig 对象

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

    def _path_to_str(self, path: Path | None) -> str:
        """将 Path 对象转换为数据库存储格式

        Args:
            path: Path 对象或 None

        Returns:
            路径字符串，如果为 None 则返回空字符串
        """
        return str(path) if path else ""

    def _ensure_default_config(self) -> None:
        """确保默认配置存在

        如果配置表为空，使用 models/config.py 中定义的默认配置进行初始化。
        """

        with self._conn_manager.get_cursor() as cursor:
            # 检查并初始化全局配置
            cursor.execute("SELECT COUNT(*) FROM global_config")
            if cursor.fetchone()[0] == 0:
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

            # 检查并初始化任务配置
            cursor.execute("SELECT COUNT(*) FROM task_configs")
            if cursor.fetchone()[0] == 0:
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

    def get_global_config(self) -> GlobalConfig:
        """获取全局配置

        Returns:
            全局配置对象

        Raises:
            ValueError: 如果全局配置不存在
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT inbox_dir, sorted_dir, unsorted_dir, archive_dir, misc_dir, starred_dir FROM global_config WHERE id = 1",
            )
            row = cursor.fetchone()

            if row is None:
                raise ValueError("全局配置不存在")

            return self._row_to_global_config(row)

    def update_global_config(self, config: GlobalConfig) -> None:
        """更新全局配置

        Args:
            config: 全局配置对象
        """
        with self._conn_manager.get_cursor() as cursor:
            updated_at = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE global_config
                SET inbox_dir = ?, sorted_dir = ?, unsorted_dir = ?, archive_dir = ?, misc_dir = ?, starred_dir = ?, updated_at = ?
                WHERE id = 1
                """,
                (
                    self._path_to_str(config.inbox_dir),
                    self._path_to_str(config.sorted_dir),
                    self._path_to_str(config.unsorted_dir),
                    self._path_to_str(config.archive_dir),
                    self._path_to_str(config.misc_dir),
                    self._path_to_str(config.starred_dir),
                    updated_at,
                ),
            )

    def get_all_tasks(self) -> list[TaskConfig]:
        """获取所有任务配置

        Returns:
            任务配置列表
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT name, type, enabled, config FROM task_configs ORDER BY name",
            )
            rows = cursor.fetchall()

            return [self._row_to_task_config(row) for row in rows]

    def get_task(self, name: str) -> TaskConfig | None:
        """获取单个任务配置

        Args:
            name: 任务名称

        Returns:
            任务配置对象，如果不存在则返回 None
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT name, type, enabled, config FROM task_configs WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_task_config(row)

    def update_task(self, task: TaskConfig) -> None:
        """更新任务配置

        Args:
            task: 任务配置对象

        Raises:
            ValueError: 如果任务不存在
        """
        with self._conn_manager.get_cursor() as cursor:
            # 检查任务是否存在
            cursor.execute("SELECT name FROM task_configs WHERE name = ?", (task.name,))
            if cursor.fetchone() is None:
                raise ValueError(f"任务不存在: {task.name}")

            config_json = json.dumps(task.config)
            updated_at = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE task_configs
                SET type = ?, enabled = ?, config = ?, updated_at = ?
                WHERE name = ?
                """,
                (task.type, task.enabled, config_json, updated_at, task.name),
            )

    def create_task(self, task: TaskConfig) -> None:
        """创建任务配置

        Args:
            task: 任务配置对象

        Raises:
            ValueError: 如果任务已存在
        """
        with self._conn_manager.get_cursor() as cursor:
            # 检查任务是否已存在
            cursor.execute("SELECT name FROM task_configs WHERE name = ?", (task.name,))
            if cursor.fetchone() is not None:
                raise ValueError(f"任务已存在: {task.name}")

            config_json = json.dumps(task.config)
            updated_at = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO task_configs (name, type, enabled, config, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task.name, task.type, task.enabled, config_json, updated_at),
            )

    def delete_task(self, name: str) -> None:
        """删除任务配置

        Args:
            name: 任务名称

        Raises:
            ValueError: 如果任务不存在
        """
        with self._conn_manager.get_cursor() as cursor:
            # 检查任务是否存在
            cursor.execute("SELECT name FROM task_configs WHERE name = ?", (name,))
            if cursor.fetchone() is None:
                raise ValueError(f"任务不存在: {name}")

            cursor.execute("DELETE FROM task_configs WHERE name = ?", (name,))
