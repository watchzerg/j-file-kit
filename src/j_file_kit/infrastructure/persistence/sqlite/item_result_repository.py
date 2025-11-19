"""Item结果仓储

提供 item_results 表的 CRUD 操作。
记录item处理结果，支持流式写入。
使用JSON字段存储任务类型特定的数据，支持未来扩展不同类型的item。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from j_file_kit.models import (
    FileItemResult,
    PathItemContext,
    PathItemInfo,
    PathItemType,
    ProcessorResult,
)

from .connection import SQLiteConnectionManager


class ItemResultRepositoryImpl:
    """Item结果仓储实现

    提供item结果的持久化操作，支持流式写入。
    使用JSON字段存储任务类型特定的数据，当前支持FileItemResult。

    实现 ItemResultRepository Protocol。
    """

    def __init__(
        self, connection_manager: SQLiteConnectionManager, task_id: int
    ) -> None:
        """初始化Item结果仓储

        Args:
            connection_manager: SQLite 连接管理器
            task_id: 任务ID
        """
        self._conn_manager = connection_manager
        self.task_id = task_id

    def save_result(self, result: FileItemResult) -> int:
        """保存单个item结果

        Args:
            result: 文件item结果

        Returns:
            生成的结果ID
        """
        created_at = datetime.now()

        # 构建item_data JSON：存储任务类型特定的数据
        item_data = {
            "path": str(result.item_info.path),
            "stem": result.item_info.stem,
            "item_type": result.item_info.item_type,
            "type": result.context.file_type.value
            if result.context.file_type
            else None,
            "serial_id": str(result.context.serial_id)
            if result.context.serial_id
            else None,
        }

        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO item_results (
                    task_id, item_data,
                    success, has_errors, has_warnings, was_skipped,
                    error_message, total_duration_ms, processor_count,
                    context_data, processor_results, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.task_id,
                    json.dumps(item_data, ensure_ascii=False),
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
                FROM item_results
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
        - by_item_type: 按item类型统计（从item_data JSON中提取type字段）
          每个类型包含：total, success, error, skipped, warning
        - performance_metrics: 性能指标
          - total_duration_ms: 总耗时（所有item处理耗时之和，单位：毫秒）
          - avg_duration_ms: 平均处理时间（total_duration_ms / total_items，单位：毫秒）
          - min_duration_ms: 最短处理时间（MIN(total_duration_ms)，单位：毫秒）
          - max_duration_ms: 最长处理时间（MAX(total_duration_ms)，单位：毫秒）
          - items_per_second: 处理速度（total_items / (total_duration_ms / 1000)，单位：item/秒）

        使用 SQL 聚合查询（SUM, AVG, MIN, MAX, COUNT）和JSON函数计算性能指标。

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
            # 按item类型统计（从item_data JSON中提取type字段）
            cursor.execute(
                """
                SELECT
                    json_extract(item_data, '$.type') as item_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 AND was_skipped = 0 AND has_warnings = 0 THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error,
                    SUM(CASE WHEN was_skipped = 1 THEN 1 ELSE 0 END) as skipped,
                    SUM(CASE WHEN has_warnings = 1 AND was_skipped = 0 THEN 1 ELSE 0 END) as warning
                FROM item_results
                WHERE task_id = ? AND json_extract(item_data, '$.type') IS NOT NULL
                GROUP BY json_extract(item_data, '$.type')
                """,
                (self.task_id,),
            )
            rows = cursor.fetchall()

            by_item_type: dict[str, dict[str, int]] = {}
            for row in rows:
                item_type = row["item_type"]
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
                FROM item_results
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
        # 反序列化 PathItemContext
        context_data = json.loads(row["context_data"]) if row["context_data"] else {}
        context = PathItemContext.model_validate(context_data)

        # 反序列化 ProcessorResult 列表
        processor_results_data = (
            json.loads(row["processor_results"]) if row["processor_results"] else []
        )
        processor_results = [
            ProcessorResult.model_validate(r) for r in processor_results_data
        ]

        # 从item_data JSON中提取文件特定数据
        item_data = json.loads(row["item_data"]) if row["item_data"] else {}
        item_path = item_data.get("path", "")
        if not item_path:
            raise ValueError(f"item_data 中缺少 path 字段: {row['id']}")
        path_obj = Path(item_path)
        # 从item_data中获取item_type，如果没有则默认为FILE（向后兼容）
        item_type_str = item_data.get("item_type", PathItemType.FILE)
        item_type = (
            PathItemType(item_type_str)
            if isinstance(item_type_str, str)
            else PathItemType.FILE
        )
        item_info = PathItemInfo.from_path(path_obj, item_type)

        return FileItemResult(
            item_info=item_info,
            context=context,
            processor_results=processor_results,
            total_duration_ms=row["total_duration_ms"],
            success=bool(row["success"]),
            error_message=row["error_message"],
        )
