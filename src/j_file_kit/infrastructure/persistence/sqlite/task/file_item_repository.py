"""文件处理结果仓储

提供 file_items 表的 CRUD 操作。
记录文件处理结果，支持流式写入。
使用具体字段存储文件信息，提升查询性能和索引效率。
专门存储文件处理结果，不存储目录操作（目录操作已在 operations 表中记录）。
"""

from datetime import datetime
from typing import Any

from j_file_kit.app.file_task.domain.decisions import FileItemData
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class FileItemRepositoryImpl:
    """文件处理结果仓储实现

    提供文件处理结果的持久化操作，支持流式写入。
    使用具体字段存储文件信息，提升查询性能和索引效率。

    实现 FileItemRepository Protocol。

    设计说明：方法接收 task_id 参数，支持作为单例复用。
    """

    def __init__(
        self,
        connection_manager: SQLiteConnectionManager,
    ) -> None:
        """初始化文件处理结果仓储

        Args:
            connection_manager: SQLite 连接管理器
        """
        self._conn_manager = connection_manager

    def save_result(self, task_id: int, result: FileItemData) -> int:
        """保存单个文件处理结果

        Args:
            task_id: 任务 ID
            result: 文件处理结果数据

        Returns:
            生成的结果ID
        """
        created_at = datetime.now()

        # 提取字段
        path = str(result.path)
        stem = result.stem
        file_type = result.file_type.value if result.file_type else None
        serial_id = str(result.serial_id) if result.serial_id else None

        # 根据 decision_type 判断状态
        success = result.success
        was_skipped = result.decision_type == "skip"
        has_errors = not success
        has_warnings = False  # 简化设计，不再使用 warnings

        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO file_items (
                    task_id, path, stem, file_type, serial_id,
                    success, has_errors, has_warnings, was_skipped,
                    error_message, total_duration_ms, processor_count,
                    context_data, processor_results, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    path,
                    stem,
                    file_type,
                    serial_id,
                    success,
                    has_errors,
                    has_warnings,
                    was_skipped,
                    result.error_message,
                    result.duration_ms,
                    1,  # processor_count 固定为 1（简化设计）
                    "{}",  # context_data 不再使用
                    "[]",  # processor_results 不再使用
                    created_at.isoformat(),
                ),
            )
            result_id = cursor.lastrowid
            if result_id is None:
                raise RuntimeError("无法获取生成的结果ID")
            return int(result_id)

    def get_statistics(self, task_id: int) -> dict[str, Any]:
        """获取任务统计信息

        Args:
            task_id: 任务 ID

        Returns:
            统计信息字典，包含 total_items, success_items, error_items,
            skipped_items, warning_items, total_duration_ms
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_items,
                    SUM(CASE WHEN success = 1 AND was_skipped = 0 AND has_warnings = 0 THEN 1 ELSE 0 END) as success_items,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_items,
                    SUM(CASE WHEN was_skipped = 1 THEN 1 ELSE 0 END) as skipped_items,
                    SUM(CASE WHEN has_warnings = 1 AND was_skipped = 0 THEN 1 ELSE 0 END) as warning_items,
                    SUM(total_duration_ms) as total_duration_ms
                FROM file_items
                WHERE task_id = ?
                """,
                (task_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {
                    "total_items": 0,
                    "success_items": 0,
                    "error_items": 0,
                    "skipped_items": 0,
                    "warning_items": 0,
                    "total_duration_ms": 0.0,
                }

            return {
                "total_items": row["total_items"] or 0,
                "success_items": row["success_items"] or 0,
                "error_items": row["error_items"] or 0,
                "skipped_items": row["skipped_items"] or 0,
                "warning_items": row["warning_items"] or 0,
                "total_duration_ms": row["total_duration_ms"] or 0.0,
            }
