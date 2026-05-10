"""文件任务执行实例仓储

提供 file_task_runs 表的 CRUD 操作。
实现 FileTaskRunRepository Protocol。
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, Literal

from j_file_kit.app.file_task.domain.task_run import (
    FileTaskRun,
    FileTaskRunStatistics,
    FileTaskRunStatus,
    FileTaskTriggerType,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)

RunListFilterKey = Literal["all", "task_type", "status", "task_type_status"]

LIST_RUN_QUERIES: dict[RunListFilterKey, str] = {
    "all": """
        SELECT * FROM file_task_runs
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    """,
    "task_type": """
        SELECT * FROM file_task_runs
        WHERE task_type = ?
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    """,
    "status": """
        SELECT * FROM file_task_runs
        WHERE status = ?
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    """,
    "task_type_status": """
        SELECT * FROM file_task_runs
        WHERE task_type = ? AND status = ?
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    """,
}

COUNT_RUN_QUERIES: dict[RunListFilterKey, str] = {
    "all": "SELECT COUNT(*) AS total FROM file_task_runs",
    "task_type": """
        SELECT COUNT(*) AS total FROM file_task_runs
        WHERE task_type = ?
    """,
    "status": """
        SELECT COUNT(*) AS total FROM file_task_runs
        WHERE status = ?
    """,
    "task_type_status": """
        SELECT COUNT(*) AS total FROM file_task_runs
        WHERE task_type = ? AND status = ?
    """,
}


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
        statistics = None
        if row["statistics"]:
            statistics = FileTaskRunStatistics.model_validate(
                json.loads(row["statistics"]),
            )

        return FileTaskRun(
            run_id=row["run_id"],
            run_name=row["run_name"],
            task_type=row["task_type"],
            trigger_type=FileTaskTriggerType(row["trigger_type"]),
            dry_run=bool(row["dry_run"]),
            status=FileTaskRunStatus(row["status"]),
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"])
            if row["end_time"]
            else None,
            error_message=row["error_message"],
            statistics=statistics,
        )

    def _build_list_filters(
        self,
        task_type: str | None,
        status: FileTaskRunStatus | None,
    ) -> tuple[RunListFilterKey, list[str]]:
        params: list[str] = []

        if task_type is None and status is None:
            return "all", params
        if task_type is not None and status is None:
            params.append(task_type)
            return "task_type", params
        if task_type is None and status is not None:
            params.append(status.value)
            return "status", params
        if task_type is not None and status is not None:
            params.extend([task_type, status.value])
            return "task_type_status", params

        raise AssertionError("unreachable filter combination")

    def create_run(
        self,
        run_name: str,
        task_type: str,
        trigger_type: FileTaskTriggerType,
        status: FileTaskRunStatus,
        start_time: datetime,
        dry_run: bool = False,
    ) -> int:
        """创建执行实例记录，返回生成的 run_id

        Args:
            run_name: 执行实例名称
            task_type: 任务类型
            trigger_type: 触发类型
            status: 执行状态
            start_time: 开始时间
            dry_run: 是否为预览模式

        Returns:
            生成的执行实例ID
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO file_task_runs (
                    run_name, task_type, trigger_type, dry_run, status,
                    start_time, end_time, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_name,
                    task_type,
                    trigger_type.value,
                    int(dry_run),
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

    def list_runs(
        self,
        task_type: str | None = None,
        status: FileTaskRunStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[FileTaskRun]:
        """列出所有执行实例记录（按开始时间降序）

        Returns:
            执行实例列表
        """
        filter_key, params = self._build_list_filters(task_type, status)
        query = LIST_RUN_QUERIES[filter_key]
        effective_limit = limit if limit is not None else -1
        effective_offset = offset if limit is not None else 0
        query_params: list[str | int] = [
            *params,
            effective_limit,
            effective_offset,
        ]

        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(query, tuple(query_params))
            rows = cursor.fetchall()

            return [self._row_to_run(row) for row in rows]

    def count_runs(
        self,
        task_type: str | None = None,
        status: FileTaskRunStatus | None = None,
    ) -> int:
        """统计符合条件的执行实例记录数。"""
        filter_key, params = self._build_list_filters(task_type, status)

        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                COUNT_RUN_QUERIES[filter_key],
                tuple(params),
            )
            row = cursor.fetchone()
            return int(row["total"])

    def delete_run(self, run_id: int) -> None:
        """删除单个执行实例记录。"""
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM file_task_runs WHERE run_id = ?",
                (run_id,),
            )

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

    def get_active_run(self) -> FileTaskRun | None:
        """获取当前待处理或运行中的执行实例，无则返回 None"""
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM file_task_runs
                WHERE status IN (?, ?)
                ORDER BY start_time DESC
                LIMIT 1
                """,
                (
                    FileTaskRunStatus.PENDING.value,
                    FileTaskRunStatus.RUNNING.value,
                ),
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
