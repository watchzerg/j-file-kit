"""SQLite 表结构初始化。"""

import sqlite3

from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class SQLiteSchemaInitializer:
    """SQLite 表结构初始化器。

    负责创建表结构与索引，不管理连接生命周期。
    """

    def __init__(self, conn_manager: SQLiteConnectionManager) -> None:
        self._conn_manager = conn_manager

    def initialize(self) -> None:
        """初始化数据库表结构与索引。"""
        conn = self._conn_manager.get_connection()
        lock = self._conn_manager.get_lock()
        with lock:
            cursor = conn.cursor()
            self._create_tables(cursor)
            self._create_indexes(cursor)
            conn.commit()

    def _create_tables(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_tasks (
                task_id INTEGER PRIMARY KEY,
                task_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                error_message TEXT,
                statistics TEXT
            )
            """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                source_path TEXT NOT NULL,
                file_stem TEXT NOT NULL,
                file_type TEXT,
                serial_id TEXT,
                decision_type TEXT NOT NULL,
                target_path TEXT,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                duration_ms REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES file_tasks(task_id)
            )
            """,
        )

    def _create_indexes(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_results_task_id ON file_results(task_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_results_decision_type ON file_results(task_id, decision_type)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_results_file_type ON file_results(file_type)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_results_serial_id ON file_results(serial_id)",
        )
