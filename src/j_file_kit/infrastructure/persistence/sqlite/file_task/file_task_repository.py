"""文件任务记录仓储

提供 file_tasks 表的 CRUD 操作。
实现 FileTaskRepository Protocol。
"""

import json
import sqlite3
from datetime import datetime
from typing import Any

from j_file_kit.app.file_task.domain.models import (
    FileTaskRecord,
    FileTaskStatus,
    FileTaskTriggerType,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class FileTaskRepositoryImpl:
    """文件任务记录仓储实现

    提供 file_tasks 表的持久化操作。
    实现 FileTaskRepository Protocol。
    """

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        """初始化文件任务仓储

        Args:
            connection_manager: SQLite 连接管理器
        """
        self._conn_manager = connection_manager

    def _row_to_record(self, row: sqlite3.Row) -> FileTaskRecord:
        """将数据库行转换为 FileTaskRecord 对象

        Args:
            row: 数据库行

        Returns:
            FileTaskRecord 对象
        """
        return FileTaskRecord(
            task_id=row["task_id"],
            task_name=row["task_name"],
            task_type=row["task_type"],
            trigger_type=FileTaskTriggerType(row["trigger_type"]),
            status=FileTaskStatus(row["status"]),
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"])
            if row["end_time"]
            else None,
            error_message=row["error_message"],
        )

    def create_task(
        self,
        task_name: str,
        task_type: str,
        trigger_type: FileTaskTriggerType,
        status: FileTaskStatus,
        start_time: datetime,
    ) -> int:
        """创建任务记录，返回生成的 task_id

        Args:
            task_name: 任务名称
            task_type: 任务类型
            trigger_type: 触发类型
            status: 任务状态
            start_time: 开始时间

        Returns:
            生成的任务ID
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO file_tasks (task_name, task_type, trigger_type, status, start_time, end_time, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_name,
                    task_type,
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
        status: FileTaskStatus | None = None,
        end_time: datetime | None = None,
        error_message: str | None = None,
        statistics: dict[str, Any] | None = None,
    ) -> None:
        """更新任务记录（仅更新非 None 字段）

        Args:
            task_id: 任务ID
            status: 任务状态（可选）
            end_time: 结束时间（可选）
            error_message: 错误消息（可选）
            statistics: 统计信息字典（可选），序列化为 JSON 存储
        """
        status_value = status.value if status is not None else None
        end_time_value = end_time.isoformat() if end_time is not None else None
        error_message_value = error_message
        statistics_value = (
            json.dumps(statistics, ensure_ascii=False)
            if statistics is not None
            else None
        )

        if (
            status_value is None
            and end_time_value is None
            and error_message_value is None
            and statistics_value is None
        ):
            return

        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE file_tasks
                SET
                    status = COALESCE(?, status),
                    end_time = COALESCE(?, end_time),
                    error_message = COALESCE(?, error_message),
                    statistics = COALESCE(?, statistics)
                WHERE task_id = ?
                """,
                (
                    status_value,
                    end_time_value,
                    error_message_value,
                    statistics_value,
                    task_id,
                ),
            )

    def get_task(self, task_id: int) -> FileTaskRecord | None:
        """获取任务记录，不存在时返回 None

        Args:
            task_id: 任务ID

        Returns:
            任务对象，如果不存在则返回 None
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute("SELECT * FROM file_tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_record(row)

    def list_tasks(self) -> list[FileTaskRecord]:
        """列出所有任务记录（按开始时间降序）

        Returns:
            任务列表
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute("SELECT * FROM file_tasks ORDER BY start_time DESC")
            rows = cursor.fetchall()

            return [self._row_to_record(row) for row in rows]

    def get_running_task(self) -> FileTaskRecord | None:
        """获取当前运行中的任务，无则返回 None

        Returns:
            运行中的任务，如果没有则返回 None
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM file_tasks WHERE status = ? LIMIT 1",
                (FileTaskStatus.RUNNING.value,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_record(row)

    def get_pending_or_running_tasks(self) -> list[FileTaskRecord]:
        """获取所有待处理或运行中的任务（用于启动时崩溃恢复）

        Returns:
            待处理或运行中的任务列表
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM file_tasks WHERE status IN (?, ?)",
                (FileTaskStatus.PENDING.value, FileTaskStatus.RUNNING.value),
            )
            rows = cursor.fetchall()

            return [self._row_to_record(row) for row in rows]
