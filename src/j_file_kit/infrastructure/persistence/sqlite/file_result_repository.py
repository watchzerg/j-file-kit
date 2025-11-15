"""文件结果仓储

提供 file_results 表的 CRUD 操作。
记录文件处理结果，支持流式写入。
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ...domain.models import (  # type: ignore[import-untyped]
    FileInfo,
    FileResult,
    ProcessingContext,
    ProcessorResult,
)
from .connection import SQLiteConnectionManager


class FileResultRepository:
    """文件结果仓储

    提供文件结果的持久化操作，支持流式写入。
    """

    def __init__(
        self, connection_manager: SQLiteConnectionManager, task_id: int
    ) -> None:
        """初始化文件结果仓储

        Args:
            connection_manager: SQLite 连接管理器
            task_id: 任务ID
        """
        self._conn_manager = connection_manager
        self.task_id = task_id

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

    def save_result(self, result: FileResult) -> int:
        """保存单个文件结果

        Args:
            result: 文件结果

        Returns:
            生成的结果ID
        """
        created_at = datetime.now()
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO file_results (
                    task_id, file_path, file_name, file_type, serial_id,
                    success, has_errors, has_warnings, was_skipped,
                    error_message, total_duration_ms, processor_count,
                    context_data, processor_results, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.task_id,
                    str(result.file_info.path),
                    result.file_info.name,
                    result.context.file_type,
                    str(result.context.serial_id) if result.context.serial_id else None,
                    result.success,
                    result.has_errors,
                    result.has_warnings,
                    result.was_skipped,
                    result.error_message,
                    result.total_duration_ms,
                    len(result.processor_results),
                    result.context.model_dump_json(exclude_none=True),
                    json.dumps(
                        [
                            r.model_dump(exclude_none=True, mode="json")
                            for r in result.processor_results
                        ],
                        ensure_ascii=False,
                    ),
                    created_at.isoformat(),
                ),
            )
            result_id = cursor.lastrowid
            if result_id is None:
                raise RuntimeError("无法获取生成的结果ID")
            return int(result_id)

    def get_statistics(self) -> dict[str, Any]:
        """获取任务统计信息

        Returns:
            统计信息字典，包含 total_files, success_files, error_files,
            skipped_files, warning_files, total_duration_ms
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_files,
                    SUM(CASE WHEN success = 1 AND was_skipped = 0 AND has_warnings = 0 THEN 1 ELSE 0 END) as success_files,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_files,
                    SUM(CASE WHEN was_skipped = 1 THEN 1 ELSE 0 END) as skipped_files,
                    SUM(CASE WHEN has_warnings = 1 AND was_skipped = 0 THEN 1 ELSE 0 END) as warning_files,
                    SUM(total_duration_ms) as total_duration_ms
                FROM file_results
                WHERE task_id = ?
                """,
                (self.task_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {
                    "total_files": 0,
                    "success_files": 0,
                    "error_files": 0,
                    "skipped_files": 0,
                    "warning_files": 0,
                    "total_duration_ms": 0.0,
                }

            return {
                "total_files": row["total_files"] or 0,
                "success_files": row["success_files"] or 0,
                "error_files": row["error_files"] or 0,
                "skipped_files": row["skipped_files"] or 0,
                "warning_files": row["warning_files"] or 0,
                "total_duration_ms": row["total_duration_ms"] or 0.0,
            }

    def _row_to_file_result(self, row: sqlite3.Row) -> FileResult:
        """将数据库行转换为 FileResult 对象

        Args:
            row: 数据库行

        Returns:
            FileResult 对象
        """
        # 反序列化 ProcessingContext
        context_data = json.loads(row["context_data"]) if row["context_data"] else {}
        context = ProcessingContext.model_validate(context_data)

        # 反序列化 ProcessorResult 列表
        processor_results_data = (
            json.loads(row["processor_results"]) if row["processor_results"] else []
        )
        processor_results = [
            ProcessorResult.model_validate(r) for r in processor_results_data
        ]

        # 重建 FileInfo
        file_info = FileInfo(path=row["file_path"], name=row["file_name"])

        return FileResult(
            file_info=file_info,
            context=context,
            processor_results=processor_results,
            total_duration_ms=row["total_duration_ms"],
            success=bool(row["success"]),
            error_message=row["error_message"],
        )
