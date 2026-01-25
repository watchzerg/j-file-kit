"""全局配置仓储实现。"""

import sqlite3
from datetime import datetime
from pathlib import Path

from j_file_kit.app.global_config.domain.models import GlobalConfig
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class GlobalConfigRepositoryImpl:
    """全局配置仓储实现。

    仅处理全局配置的读取与更新。
    """

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        """初始化全局配置仓储。

        Args:
            connection_manager: SQLite 连接管理器
        """
        self._conn_manager = connection_manager

    def _row_to_global_config(self, row: sqlite3.Row) -> GlobalConfig:
        """将数据库行转换为 GlobalConfig 对象。

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

    def _path_to_str(self, path: Path | None) -> str:
        """将 Path 对象转换为数据库存储格式。

        Args:
            path: Path 对象或 None

        Returns:
            路径字符串，如果为 None 则返回空字符串
        """
        return str(path) if path else ""

    def get_global_config(self) -> GlobalConfig:
        """获取全局配置。

        Returns:
            全局配置对象

        Raises:
            ValueError: 如果全局配置不存在
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT inbox_dir, sorted_dir, unsorted_dir, archive_dir, misc_dir, starred_dir FROM config_global WHERE id = 1",
            )
            row = cursor.fetchone()

            if row is None:
                raise ValueError("全局配置不存在")

            return self._row_to_global_config(row)

    def update_global_config(self, config: GlobalConfig) -> None:
        """更新全局配置。

        Args:
            config: 全局配置对象
        """
        with self._conn_manager.get_cursor() as cursor:
            updated_at = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE config_global
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
