"""SQLite 连接管理。

管理 SQLite 数据库连接。
"""

import contextlib
import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path


class SQLiteConnectionManager:
    """SQLite 连接管理器

    管理 SQLite 数据库连接，提供线程安全的连接访问。
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
