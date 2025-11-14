"""数据库管理

管理 SQLite 数据库连接和操作。
提供任务和操作记录的CRUD功能，自动创建表结构。
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ...domain.models import Task, TaskStatus


class DatabaseManager:
    """数据库管理器

    管理 SQLite 数据库连接，提供任务和操作记录的 CRUD 操作。
    """

    def __init__(self, db_path: Path) -> None:
        """初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        # 创建表结构
        self._create_tables()

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """将数据库行转换为 Task 对象

        Args:
            row: 数据库行

        Returns:
            Task 对象
        """
        return Task(
            task_id=row["task_id"],
            task_name=row["task_name"],
            status=TaskStatus(row["status"]),
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"])
            if row["end_time"]
            else None,
            error_message=row["error_message"],
            report=None,
        )

    def _create_tables(self) -> None:
        """创建数据库表结构"""
        with self._lock:
            cursor = self._conn.cursor()

            # 创建 tasks 表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_name TEXT NOT NULL,
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
                    task_id TEXT NOT NULL,
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

    def create_task(
        self,
        task_id: str,
        task_name: str,
        status: TaskStatus,
        start_time: datetime,
    ) -> None:
        """创建任务记录

        Args:
            task_id: 任务ID
            task_name: 任务名称
            status: 任务状态
            start_time: 开始时间
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO tasks (task_id, task_name, status, start_time, end_time, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    task_name,
                    status.value,
                    start_time.isoformat(),
                    None,
                    None,
                ),
            )
            self._conn.commit()

    def update_task(
        self,
        task_id: str,
        status: TaskStatus | None = None,
        end_time: datetime | None = None,
        error_message: str | None = None,
    ) -> None:
        """更新任务记录

        Args:
            task_id: 任务ID
            status: 任务状态（可选）
            end_time: 结束时间（可选）
            error_message: 错误消息（可选）
        """
        with self._lock:
            cursor = self._conn.cursor()

            updates = []
            params = []

            if status is not None:
                updates.append("status = ?")
                params.append(status.value)

            if end_time is not None:
                updates.append("end_time = ?")
                params.append(end_time.isoformat())

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if not updates:
                return

            # 列名是硬编码的字符串字面量，值通过参数化查询传递，因此安全
            query = "UPDATE tasks SET " + ", ".join(updates) + " WHERE task_id = ?"  # noqa: S608
            params.append(task_id)
            cursor.execute(query, params)
            self._conn.commit()

    def get_task(self, task_id: str) -> Task | None:
        """获取任务记录

        Args:
            task_id: 任务ID

        Returns:
            任务对象，如果不存在则返回 None
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_task(row)

    def list_tasks(self) -> list[Task]:
        """列出所有任务

        Returns:
            任务列表
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM tasks ORDER BY start_time DESC")
            rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]

    def get_running_task(self) -> Task | None:
        """获取运行中的任务

        Returns:
            运行中的任务，如果没有则返回 None
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM tasks WHERE status = ? LIMIT 1",
                (TaskStatus.RUNNING.value,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_task(row)

    def log_operation(
        self,
        task_id: str,
        operation: str,
        source_path: Path,
        target_path: Path | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """记录操作

        Args:
            task_id: 任务ID
            operation: 操作类型
            source_path: 源路径
            target_path: 目标路径（可选）
            data: 附加数据（可选）
        """
        with self._lock:
            cursor = self._conn.cursor()
            operation_id = str(uuid.uuid4())
            timestamp = datetime.now()

            cursor.execute(
                """
                INSERT INTO operations (id, task_id, timestamp, operation, source_path, target_path, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operation_id,
                    task_id,
                    timestamp.isoformat(),
                    operation,
                    str(source_path),
                    str(target_path) if target_path else None,
                    json.dumps(data, ensure_ascii=False) if data else None,
                ),
            )
            self._conn.commit()

    def get_operations(self, task_id: str) -> list[dict[str, Any]]:
        """获取任务的操作记录

        Args:
            task_id: 任务ID

        Returns:
            操作记录列表
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM operations WHERE task_id = ? ORDER BY timestamp",
                (task_id,),
            )
            rows = cursor.fetchall()

            operations = []
            for row in rows:
                operations.append(
                    {
                        "id": row["id"],
                        "task_id": row["task_id"],
                        "timestamp": row["timestamp"],
                        "operation": row["operation"],
                        "source_path": row["source_path"],
                        "target_path": row["target_path"],
                        "data": json.loads(row["data"]) if row["data"] else None,
                    }
                )

            return operations

    def close(self) -> None:
        """关闭数据库连接"""
        with self._lock:
            self._conn.close()
