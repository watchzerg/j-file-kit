"""配置仓储

提供配置数据的持久化操作，包括全局配置和任务配置的 CRUD。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from ...config.config import GlobalConfig, TaskDefinition
from .connection import SQLiteConnectionManager


class ConfigRepository:
    """配置仓储

    提供配置数据的持久化操作。
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

    def _row_to_task_definition(self, row: sqlite3.Row) -> TaskDefinition:
        """将数据库行转换为 TaskDefinition 对象

        Args:
            row: 数据库行

        Returns:
            TaskDefinition 对象
        """
        config_dict = json.loads(row["config"])
        return TaskDefinition(
            name=row["name"],
            type=row["type"],
            enabled=bool(row["enabled"]),
            config=config_dict,
        )

    def _ensure_default_config(self) -> None:
        """确保默认配置存在

        如果配置表为空，插入默认配置。
        """
        with self._conn_manager.get_cursor() as cursor:
            # 检查 global_config 表是否为空
            cursor.execute("SELECT COUNT(*) FROM global_config")
            global_count = cursor.fetchone()[0]

            if global_count == 0:
                # 插入默认全局配置（所有目录字段为空字符串，表示未设置）
                updated_at = datetime.now().isoformat()
                cursor.execute(
                    """
                    INSERT INTO global_config (id, inbox_dir, sorted_dir, unsorted_dir, archive_dir, misc_dir, starred_dir, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("", "", "", "", "", "", updated_at),
                )

            # 检查 task_configs 表是否为空
            cursor.execute("SELECT COUNT(*) FROM task_configs")
            task_count = cursor.fetchone()[0]

            if task_count == 0:
                # 插入默认任务配置（jav_video_organizer）
                updated_at = datetime.now().isoformat()
                default_task_config = {
                    "video_extensions": [
                        ".mp4",
                        ".avi",
                        ".mkv",
                        ".mov",
                        ".wmv",
                        ".flv",
                        ".webm",
                    ],
                    "image_extensions": [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                        ".bmp",
                        ".gif",
                        ".tiff",
                    ],
                    "archive_extensions": [
                        ".zip",
                        ".rar",
                        ".7z",
                        ".tar",
                        ".gz",
                        ".bz2",
                        ".xz",
                    ],
                    "misc_file_delete_rules": {
                        "keywords": ["rarbg", "sample", "preview", "temp"],
                        "extensions": [".tmp", ".temp", ".bak", ".old"],
                        "max_size": 1048576,
                    },
                }
                config_json = json.dumps(default_task_config)
                cursor.execute(
                    """
                    INSERT INTO task_configs (name, type, enabled, config, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "jav_video_organizer",
                        "file_organize",
                        True,
                        config_json,
                        updated_at,
                    ),
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
                "SELECT inbox_dir, sorted_dir, unsorted_dir, archive_dir, misc_dir, starred_dir FROM global_config WHERE id = 1"
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
            # 将Path对象转为字符串，None转为空字符串
            def to_str(path: Path | None) -> str:
                return str(path) if path else ""

            updated_at = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE global_config
                SET inbox_dir = ?, sorted_dir = ?, unsorted_dir = ?, archive_dir = ?, misc_dir = ?, starred_dir = ?, updated_at = ?
                WHERE id = 1
                """,
                (
                    to_str(config.inbox_dir),
                    to_str(config.sorted_dir),
                    to_str(config.unsorted_dir),
                    to_str(config.archive_dir),
                    to_str(config.misc_dir),
                    to_str(config.starred_dir),
                    updated_at,
                ),
            )

    def get_all_tasks(self) -> list[TaskDefinition]:
        """获取所有任务配置

        Returns:
            任务配置列表
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT name, type, enabled, config FROM task_configs ORDER BY name"
            )
            rows = cursor.fetchall()

            return [self._row_to_task_definition(row) for row in rows]

    def get_task(self, name: str) -> TaskDefinition | None:
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

            return self._row_to_task_definition(row)

    def update_task(self, task: TaskDefinition) -> None:
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

    def create_task(self, task: TaskDefinition) -> None:
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
