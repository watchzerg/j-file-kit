"""SQLite 连接管理

管理 SQLite 数据库连接和表结构创建。
"""

import contextlib
import sqlite3
import threading
from collections.abc import Iterator
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
            # statistics 字段使用 JSON 格式存储统计信息，便于扩展支持不同类型的任务统计需求
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

            # 删除旧的 item_results 表（如果存在）
            # 项目处于开发阶段，不需要数据迁移和向后兼容
            cursor.execute("DROP TABLE IF EXISTS item_results")
            # 删除相关索引（如果存在）
            cursor.execute("DROP INDEX IF EXISTS idx_item_results_task_id")
            cursor.execute("DROP INDEX IF EXISTS idx_item_results_success")

            # 创建 file_items 表
            # 使用具体字段替代 JSON，提升查询性能和索引效率
            # 专门存储文件处理结果，不存储目录操作（目录操作已在 operations 表中记录）
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

            # 删除旧的 operations 表（如果存在）
            cursor.execute("DROP TABLE IF EXISTS operations")
            # 删除相关索引（如果存在）
            cursor.execute("DROP INDEX IF EXISTS idx_operations_task_id")
            cursor.execute("DROP INDEX IF EXISTS idx_operations_item_result_id")
            cursor.execute("DROP INDEX IF EXISTS idx_operations_timestamp")

            # 创建 file_operations 表
            # 使用具体字段替代 JSON，提升查询性能和索引效率
            # 只记录文件操作，不记录目录操作
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS file_operations (
                    id TEXT PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    file_item_id INTEGER,
                    timestamp TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    target_path TEXT,
                    file_type TEXT,
                    serial_id TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                    FOREIGN KEY (file_item_id) REFERENCES file_items(id)
                )
                """,
            )

            # 创建索引
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

            # 创建 global_config 表（单行表，存储全局配置）
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS global_config (
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

            # 创建 task_configs 表（存储任务配置）
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS task_configs (
                    name TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL,
                    config TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """,
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

    @contextlib.contextmanager
    def get_cursor(self) -> Iterator[sqlite3.Cursor]:
        """获取数据库游标的上下文管理器

        Yields:
            数据库游标
        """
        conn = self.get_connection()
        lock = self.get_lock()
        with lock:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def close(self) -> None:
        """关闭数据库连接"""
        with self._lock:
            self._conn.close()
