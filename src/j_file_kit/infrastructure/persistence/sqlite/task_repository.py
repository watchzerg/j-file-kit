"""任务仓储

提供 tasks 表的 CRUD 操作。
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ...domain.models import (  # type: ignore[import-untyped]
    Task,
    TaskStatus,
    TaskType,
    TriggerType,
)
from .connection import SQLiteConnectionManager


class TaskRepository:
    """任务仓储

    提供任务数据的持久化操作。
    """

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        """初始化任务仓储

        Args:
            connection_manager: SQLite 连接管理器
        """
        self._conn_manager = connection_manager

    @contextlib.contextmanager
    def _get_cursor(self) -> Iterator[sqlite3.Cursor]:
        """获取数据库游标的上下文管理器

        Yields:
            数据库游标
        """
        conn = self._conn_manager.get_connection()
        lock = self._conn_manager.get_lock()
        with lock:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise

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
            task_type=TaskType(row["task_type"]),
            trigger_type=TriggerType(row["trigger_type"]),
            status=TaskStatus(row["status"]),
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"])
            if row["end_time"]
            else None,
            error_message=row["error_message"],
            report=None,
        )

    def create_task(
        self,
        task_name: str,
        task_type: TaskType,
        trigger_type: TriggerType,
        status: TaskStatus,
        start_time: datetime,
    ) -> int:
        """创建任务记录

        Args:
            task_name: 任务名称
            task_type: 任务类型
            trigger_type: 触发类型
            status: 任务状态
            start_time: 开始时间

        Returns:
            生成的任务ID
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (task_name, task_type, trigger_type, status, start_time, end_time, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_name,
                    task_type.value,
                    trigger_type.value,
                    status.value,
                    start_time.isoformat(),
                    None,
                    None,
                ),
            )
            task_id = cursor.lastrowid
            if task_id is None:
                raise RuntimeError("无法获取生成的任务ID")
            return int(task_id)

    def update_task(
        self,
        task_id: int,
        status: TaskStatus | None = None,
        end_time: datetime | None = None,
        error_message: str | None = None,
        statistics: dict[str, Any] | None = None,
    ) -> None:
        """更新任务记录

        Args:
            task_id: 任务ID
            status: 任务状态（可选）
            end_time: 结束时间（可选）
            error_message: 错误消息（可选）
            statistics: 统计信息字典（可选），将被序列化为 JSON 格式存储
                使用 JSON 格式便于扩展支持不同类型的任务统计需求
        """
        updates: list[str] = []
        params: list[str | int] = []

        if status is not None:
            updates.append("status = ?")
            params.append(status.value)

        if end_time is not None:
            updates.append("end_time = ?")
            params.append(end_time.isoformat())

        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        if statistics is not None:
            updates.append("statistics = ?")
            # 使用 ensure_ascii=False 支持中文，便于扩展支持不同类型的任务统计需求
            params.append(json.dumps(statistics, ensure_ascii=False))

        if not updates:
            return

        # 列名是硬编码的字符串字面量，值通过参数化查询传递，因此安全
        query = "UPDATE tasks SET " + ", ".join(updates) + " WHERE task_id = ?"  # noqa: S608
        params.append(task_id)

        with self._get_cursor() as cursor:
            cursor.execute(query, params)

    def get_task(self, task_id: int) -> Task | None:
        """获取任务记录

        Args:
            task_id: 任务ID

        Returns:
            任务对象，如果不存在则返回 None
        """
        with self._get_cursor() as cursor:
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
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM tasks ORDER BY start_time DESC")
            rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]

    def get_running_task(self) -> Task | None:
        """获取运行中的任务

        Returns:
            运行中的任务，如果没有则返回 None
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM tasks WHERE status = ? LIMIT 1",
                (TaskStatus.RUNNING.value,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_task(row)

    def get_pending_or_running_tasks(self) -> list[Task]:
        """获取所有待处理或运行中的任务

        Returns:
            待处理或运行中的任务列表
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM tasks WHERE status IN (?, ?)",
                (TaskStatus.PENDING.value, TaskStatus.RUNNING.value),
            )
            rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]
