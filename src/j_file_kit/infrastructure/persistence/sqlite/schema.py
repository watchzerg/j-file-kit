"""SQLite 表结构初始化。"""

import sqlite3

from j_file_kit.app.file_task.domain.models import OperationType
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
        operation_values = ", ".join(
            f"'{operation.value}'" for operation in OperationType
        )

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
                error_message TEXT,
                statistics TEXT
            )
            """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                stem TEXT NOT NULL,
                file_type TEXT,
                serial_id TEXT,
                success BOOLEAN NOT NULL,
                has_errors BOOLEAN NOT NULL,
                has_warnings BOOLEAN NOT NULL,
                was_skipped BOOLEAN NOT NULL,
                error_message TEXT,
                total_duration_ms REAL NOT NULL,
                processor_count INTEGER NOT NULL,
                context_data TEXT,
                processor_results TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
            """,
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS file_operations (
                id TEXT PRIMARY KEY,
                task_id INTEGER NOT NULL,
                file_item_id INTEGER,
                timestamp TEXT NOT NULL,
                operation TEXT NOT NULL CHECK (operation IN ({operation_values})),
                source_path TEXT NOT NULL,
                target_path TEXT,
                file_type TEXT,
                serial_id TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                FOREIGN KEY (file_item_id) REFERENCES file_items(id)
            )
            """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS config_global (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                inbox_dir TEXT NOT NULL,
                sorted_dir TEXT NOT NULL,
                unsorted_dir TEXT NOT NULL,
                archive_dir TEXT NOT NULL,
                misc_dir TEXT NOT NULL,
                starred_dir TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS config_task (
                type TEXT PRIMARY KEY,
                enabled BOOLEAN NOT NULL,
                config TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
        )

    def _create_indexes(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_items_task_id ON file_items(task_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_items_success ON file_items(task_id, success)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_items_file_type ON file_items(file_type)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_items_serial_id ON file_items(serial_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_operations_task_id ON file_operations(task_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_operations_file_item_id ON file_operations(file_item_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_operations_file_type ON file_operations(file_type)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_operations_timestamp ON file_operations(timestamp)",
        )
