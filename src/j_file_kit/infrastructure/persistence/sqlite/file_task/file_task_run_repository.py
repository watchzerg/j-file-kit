"""文件任务执行实例仓储

提供 file_task_runs 表的 CRUD 操作。
实现 FileTaskRunRepository Protocol。
"""

import json
import sqlite3
from datetime import datetime
from typing import Any

from j_file_kit.app.file_task.domain.task_run import (
    FileTaskRun,
    FileTaskRunStatus,
    FileTaskTriggerType,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class FileTaskRunRepositoryImpl:
    """文件任务执行实例仓储实现

    提供 file_task_runs 表的持久化操作。
    实现 FileTaskRunRepository Protocol。
    """

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        """初始化文件任务执行实例仓储

        Args:
            connection_manager: SQLite 连接管理器
        """
        self._conn_manager = connection_manager

    def _row_to_run(self, row: sqlite3.Row) -> FileTaskRun:
        """将数据库行转换为 FileTaskRun 对象

        Args:
            row: 数据库行

        Returns:
            FileTaskRun 对象
        """
        return FileTaskRun(
            run_id=row["run_id"],
            run_name=row["run_name"],
            task_type=row["task_type"],
            trigger_type=FileTaskTriggerType(row["trigger_type"]),
            status=FileTaskRunStatus(row["status"]),
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"])
            if row["end_time"]
            else None,
            error_message=row["error_message"],
        )

    def create_run(
        self,
        run_name: str,
        task_type: str,
        trigger_type: FileTaskTriggerType,
        status: FileTaskRunStatus,
        start_time: datetime,
    ) -> int:
        """创建执行实例记录，返回生成的 run_id

        Args:
            run_name: 执行实例名称
            task_type: 任务类型
            trigger_type: 触发类型
            status: 执行状态
            start_time: 开始时间

        Returns:
            生成的执行实例ID
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO file_task_runs (run_name, task_type, trigger_type, status, start_time, end_time, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_name,
                    task_type,
                    trigger_type.value,
                    status.value,
                    start_time.isoformat(),
                    None,
                    None,
                ),
            )
            run_id = cursor.lastrowid
            if run_id is None:
                raise RuntimeError("无法获取生成的执行实例ID")
            return int(run_id)

    def update_run(
        self,
        run_id: int,
        status: FileTaskRunStatus | None = None,
        end_time: datetime | None = None,
        error_message: str | None = None,
        statistics: dict[str, Any] | None = None,
    ) -> None:
        """更新执行实例记录（仅更新非 None 字段）

        Args:
            run_id: 执行实例ID
            status: 执行状态（可选）
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
                UPDATE file_task_runs
                SET
                    status = COALESCE(?, status),
                    end_time = COALESCE(?, end_time),
                    error_message = COALESCE(?, error_message),
                    statistics = COALESCE(?, statistics)
                WHERE run_id = ?
                """,
                (
                    status_value,
                    end_time_value,
                    error_message_value,
                    statistics_value,
                    run_id,
                ),
            )

    def get_run(self, run_id: int) -> FileTaskRun | None:
        """获取执行实例记录，不存在时返回 None

        Args:
            run_id: 执行实例ID

        Returns:
            执行实例对象，如果不存在则返回 None
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM file_task_runs WHERE run_id = ?",
                (run_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_run(row)

    def list_runs(self) -> list[FileTaskRun]:
        """列出所有执行实例记录（按开始时间降序）

        Returns:
            执行实例列表
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM file_task_runs ORDER BY start_time DESC",
            )
            rows = cursor.fetchall()

            return [self._row_to_run(row) for row in rows]

    def get_running_run(self) -> FileTaskRun | None:
        """获取当前运行中的执行实例，无则返回 None

        Returns:
            运行中的执行实例，如果没有则返回 None
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM file_task_runs WHERE status = ? LIMIT 1",
                (FileTaskRunStatus.RUNNING.value,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_run(row)

    def get_pending_or_running_runs(self) -> list[FileTaskRun]:
        """获取所有待处理或运行中的执行实例（用于启动时崩溃恢复）

        Returns:
            待处理或运行中的执行实例列表
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM file_task_runs WHERE status IN (?, ?)",
                (
                    FileTaskRunStatus.PENDING.value,
                    FileTaskRunStatus.RUNNING.value,
                ),
            )
            rows = cursor.fetchall()

            return [self._row_to_run(row) for row in rows]
