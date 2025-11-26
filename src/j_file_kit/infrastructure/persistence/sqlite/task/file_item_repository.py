"""文件处理结果仓储

提供 file_items 表的 CRUD 操作。
记录文件处理结果，支持流式写入。
使用具体字段存储文件信息，提升查询性能和索引效率。
专门存储文件处理结果，不存储目录操作（目录操作已在 operations 表中记录）。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from j_file_kit.app.file_task.domain import (
    FileItemResult,
    FileType,
    PathEntryContext,
    PathEntryInfo,
    PathEntryType,
    SerialId,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.shared.models.results import ProcessorResult


class FileItemRepositoryImpl:
    """文件处理结果仓储实现

    提供文件处理结果的持久化操作，支持流式写入。
    使用具体字段存储文件信息，提升查询性能和索引效率。

    实现 FileItemRepository Protocol。
    """

    def __init__(
        self,
        connection_manager: SQLiteConnectionManager,
        task_id: int,
    ) -> None:
        """初始化文件处理结果仓储

        Args:
            connection_manager: SQLite 连接管理器
            task_id: 任务ID
        """
        self._conn_manager = connection_manager
        self.task_id = task_id

    def save_result(self, result: FileItemResult) -> int:
        """保存单个文件处理结果

        Args:
            result: 文件处理结果

        Returns:
            生成的结果ID
        """
        created_at = datetime.now()

        # 提取文件信息到具体字段
        path = str(result.item_info.path)
        stem = result.item_info.stem
        file_type = result.context.file_type.value if result.context.file_type else None
        serial_id = str(result.context.serial_id) if result.context.serial_id else None

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
                    self.task_id,
                    path,
                    stem,
                    file_type,
                    serial_id,
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
                (self.task_id,),
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

    def get_detailed_statistics(self) -> dict[str, Any]:
        """获取任务的详细统计信息

        包含两个部分：
        - by_item_type: 按文件类型统计（video/image/archive/misc）
          每个类型包含：total, success, error, skipped, warning
        - performance_metrics: 性能指标
          - total_duration_ms: 总耗时（所有文件处理耗时之和，单位：毫秒）
          - avg_duration_ms: 平均处理时间（total_duration_ms / total_items，单位：毫秒）
          - min_duration_ms: 最短处理时间（MIN(total_duration_ms)，单位：毫秒）
          - max_duration_ms: 最长处理时间（MAX(total_duration_ms)，单位：毫秒）
          - items_per_second: 处理速度（total_items / (total_duration_ms / 1000)，单位：item/秒）

        使用 SQL 聚合查询（SUM, AVG, MIN, MAX, COUNT）直接使用字段计算性能指标。

        Returns:
            详细统计字典，格式：
            {
                "by_item_type": {
                    "video": {"total": 10, "success": 8, "error": 1, "skipped": 1, "warning": 0},
                    "image": {"total": 5, "success": 5, "error": 0, "skipped": 0, "warning": 0},
                    ...
                },
                "performance_metrics": {
                    "total_duration_ms": 12345.6,
                    "avg_duration_ms": 123.456,
                    "min_duration_ms": 10.5,
                    "max_duration_ms": 500.0,
                    "items_per_second": 0.81
                }
            }
        """
        with self._conn_manager.get_cursor() as cursor:
            # 按文件类型统计（直接使用 file_type 字段）
            cursor.execute(
                """
                SELECT
                    file_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 AND was_skipped = 0 AND has_warnings = 0 THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error,
                    SUM(CASE WHEN was_skipped = 1 THEN 1 ELSE 0 END) as skipped,
                    SUM(CASE WHEN has_warnings = 1 AND was_skipped = 0 THEN 1 ELSE 0 END) as warning
                FROM file_items
                WHERE task_id = ? AND file_type IS NOT NULL
                GROUP BY file_type
                """,
                (self.task_id,),
            )
            rows = cursor.fetchall()

            by_item_type: dict[str, dict[str, int]] = {}
            for row in rows:
                item_type = row["file_type"]
                if item_type:
                    by_item_type[item_type] = {
                        "total": row["total"] or 0,
                        "success": row["success"] or 0,
                        "error": row["error"] or 0,
                        "skipped": row["skipped"] or 0,
                        "warning": row["warning"] or 0,
                    }

            # 性能指标
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_items,
                    SUM(total_duration_ms) as total_duration_ms,
                    AVG(total_duration_ms) as avg_duration_ms,
                    MIN(total_duration_ms) as min_duration_ms,
                    MAX(total_duration_ms) as max_duration_ms
                FROM file_items
                WHERE task_id = ?
                """,
                (self.task_id,),
            )
            row = cursor.fetchone()

            if row is None or row["total_items"] == 0:
                performance_metrics = {
                    "total_duration_ms": 0.0,
                    "avg_duration_ms": 0.0,
                    "min_duration_ms": 0.0,
                    "max_duration_ms": 0.0,
                    "items_per_second": 0.0,
                }
            else:
                total_items = row["total_items"] or 0
                total_duration_ms = row["total_duration_ms"] or 0.0
                avg_duration_ms = row["avg_duration_ms"] or 0.0
                min_duration_ms = row["min_duration_ms"] or 0.0
                max_duration_ms = row["max_duration_ms"] or 0.0

                # 计算处理速度：total_items / (total_duration_ms / 1000)
                # 如果总耗时为0，则处理速度为0
                items_per_second = (
                    total_items / (total_duration_ms / 1000.0)
                    if total_duration_ms > 0
                    else 0.0
                )

                performance_metrics = {
                    "total_duration_ms": total_duration_ms,
                    "avg_duration_ms": avg_duration_ms,
                    "min_duration_ms": min_duration_ms,
                    "max_duration_ms": max_duration_ms,
                    "items_per_second": items_per_second,
                }

            return {
                "by_item_type": by_item_type,
                "performance_metrics": performance_metrics,
            }

    def _row_to_item_result(self, row: sqlite3.Row) -> FileItemResult:
        """将数据库行转换为 FileItemResult 对象

        Args:
            row: 数据库行

        Returns:
            FileItemResult 对象
        """
        # 反序列化 PathEntryContext
        context_data = json.loads(row["context_data"]) if row["context_data"] else {}
        context = PathEntryContext.model_validate(context_data)

        # 反序列化 ProcessorResult 列表
        processor_results_data = (
            json.loads(row["processor_results"]) if row["processor_results"] else []
        )
        processor_results = [
            ProcessorResult.model_validate(r) for r in processor_results_data
        ]

        # 直接从字段读取文件信息
        item_path = row["path"]
        if not item_path:
            raise ValueError(f"path 字段为空: {row['id']}")
        path_obj = Path(item_path)

        # 表只存储文件，所以 item_type 固定为 FILE
        item_info = PathEntryInfo.from_path(path_obj, PathEntryType.FILE)

        # 从数据库字段更新 file_type 和 serial_id（数据库字段是单一数据源）
        # 优先使用数据库字段，因为它们是为了查询和索引而展开的权威数据源
        file_type_str = row["file_type"]
        if file_type_str:
            try:
                file_type = FileType(file_type_str)
                context.file_type = file_type
            except ValueError:
                # 如果 file_type 无效，保持 context 中的原值（可能来自 JSON）
                pass

        serial_id_str = row["serial_id"]
        if serial_id_str:
            try:
                serial_id = SerialId.from_string(serial_id_str)
                context.serial_id = serial_id
            except ValueError:
                # 如果 serial_id 无效，保持 context 中的原值（可能来自 JSON）
                pass

        return FileItemResult(
            item_info=item_info,
            context=context,
            processor_results=processor_results,
            total_duration_ms=row["total_duration_ms"],
            success=bool(row["success"]),
            error_message=row["error_message"],
        )
