"""SQLite 连接管理

管理 SQLite 数据库连接和表结构创建。
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path


class SQLiteConnectionManager:
    """SQLite 连接管理器

    管理 SQLite 数据库连接，负责创建表结构。
    提供线程安全的连接访问。
    """

    def __init__(self, db_path: Path) -> None:
        """初始化连接管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        # 创建表结构
        self._create_tables()

    def _create_tables(self) -> None:
        """创建数据库表结构"""
        with self._lock:
            cursor = self._conn.cursor()

            # 创建 tasks 表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    error_message TEXT
                )
                """
            )

            # 创建 operations 表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    target_path TEXT,
                    data TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
                """
            )

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_operations_task_id ON operations(task_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_operations_timestamp ON operations(timestamp)"
            )

            self._conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接

        Returns:
            SQLite 连接对象
        """
        return self._conn

    def get_lock(self) -> threading.Lock:
        """获取线程锁

        Returns:
            线程锁对象
        """
        return self._lock

    def close(self) -> None:
        """关闭数据库连接"""
        with self._lock:
            self._conn.close()
