"""操作记录仓储

提供 operations 表的 CRUD 操作。
记录文件操作日志，支持查询操作历史。
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from .connection import SQLiteConnectionManager


class OperationType:
    """操作类型常量"""

    RENAME = "rename"
    MOVE = "move"
    DELETE = "delete"
    CREATE_DIR = "create_dir"
    DELETE_DIR = "delete_dir"


class OperationRepository:
    """操作记录仓储

    提供文件操作日志的持久化操作。
    """

    def __init__(
        self, connection_manager: SQLiteConnectionManager, task_id: int
    ) -> None:
        """初始化操作记录仓储

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

    def log_operation(
        self,
        operation: str,
        source_path: Path,
        target_path: Path | None = None,
        data: dict[str, Any] | None = None,
        item_result_id: int | None = None,
    ) -> None:
        """记录操作

        Args:
            operation: 操作类型
            source_path: 源路径
            target_path: 目标路径（可选）
            data: 附加数据（可选）
            item_result_id: Item结果ID（可选）
        """
        operation_id = str(uuid.uuid4())
        timestamp = datetime.now()

        # 将路径信息合并到data JSON字段中
        operation_data = {
            "source_path": str(source_path),
            "target_path": str(target_path) if target_path else None,
            **(data or {}),  # 合并原有的data
        }

        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO operations (id, task_id, item_result_id, timestamp, operation, data)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    operation_id,
                    self.task_id,
                    item_result_id,
                    timestamp.isoformat(),
                    operation,
                    json.dumps(operation_data, ensure_ascii=False),
                ),
            )

    def log_rename(
        self,
        source_path: Path,
        target_path: Path,
        data: dict[str, Any] | None = None,
        item_result_id: int | None = None,
    ) -> None:
        """记录重命名操作

        Args:
            source_path: 源路径
            target_path: 目标路径
            data: 附加数据
            item_result_id: Item结果ID（可选）
        """
        self.log_operation(
            OperationType.RENAME, source_path, target_path, data, item_result_id
        )

    def log_move(
        self,
        source_path: Path,
        target_path: Path,
        data: dict[str, Any] | None = None,
        item_result_id: int | None = None,
    ) -> None:
        """记录移动操作

        Args:
            source_path: 源路径
            target_path: 目标路径
            data: 附加数据
            item_result_id: Item结果ID（可选）
        """
        self.log_operation(
            OperationType.MOVE, source_path, target_path, data, item_result_id
        )

    def log_delete(
        self,
        path: Path,
        data: dict[str, Any] | None = None,
        item_result_id: int | None = None,
    ) -> None:
        """记录删除操作

        Args:
            path: 删除路径
            data: 附加数据
            item_result_id: Item结果ID（可选）
        """
        self.log_operation(OperationType.DELETE, path, None, data, item_result_id)

    def log_create_dir(
        self,
        path: Path,
        data: dict[str, Any] | None = None,
        item_result_id: int | None = None,
    ) -> None:
        """记录创建目录操作

        Args:
            path: 目录路径
            data: 附加数据
            item_result_id: Item结果ID（可选）
        """
        self.log_operation(OperationType.CREATE_DIR, path, None, data, item_result_id)

    def log_delete_dir(
        self,
        path: Path,
        data: dict[str, Any] | None = None,
        item_result_id: int | None = None,
    ) -> None:
        """记录删除目录操作

        Args:
            path: 目录路径
            data: 附加数据
            item_result_id: Item结果ID（可选）
        """
        self.log_operation(OperationType.DELETE_DIR, path, None, data, item_result_id)

    def get_operations(self) -> list[dict[str, Any]]:
        """获取任务的操作记录

        Returns:
            操作记录列表
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM operations WHERE task_id = ? ORDER BY timestamp",
                (self.task_id,),
            )
            rows = cursor.fetchall()

            operations = []
            for row in rows:
                # 从data JSON字段中提取路径信息
                operation_data = json.loads(row["data"]) if row["data"] else {}
                operations.append(
                    {
                        "id": row["id"],
                        "task_id": int(row["task_id"]),
                        "timestamp": row["timestamp"],
                        "operation": row["operation"],
                        "source_path": operation_data.get("source_path"),
                        "target_path": operation_data.get("target_path"),
                        "data": operation_data,
                    }
                )

            return operations

    def get_operation_statistics(self) -> dict[str, Any]:
        """获取任务的操作统计信息

        统计操作数量，包含两个维度：
        - by_operation_type: 按操作类型统计（move, delete, delete_dir, rename, create_dir）
        - by_item_type: 按item类型统计操作数量（需要关联 item_results 表，从 item_data JSON 中提取 type）

        使用 SQL JOIN 关联 operations 和 item_results 表，通过 item_result_id 关联。
        使用 JSON_EXTRACT 从 item_data JSON 中提取类型信息。
        统计时过滤 type IS NOT NULL 的操作（目录操作没有 type）。

        Returns:
            操作统计字典，格式：
            {
                "by_operation_type": {
                    "move": 10,
                    "delete": 5,
                    "delete_dir": 3,
                    "rename": 2,
                    "create_dir": 1
                },
                "by_item_type": {
                    "video": {"move": 8, "delete": 2},
                    "image": {"move": 2},
                    ...
                }
            }
        """
        with self._get_cursor() as cursor:
            # 按操作类型统计（所有操作）
            cursor.execute(
                """
                SELECT operation, COUNT(*) as count
                FROM operations
                WHERE task_id = ?
                GROUP BY operation
                """,
                (self.task_id,),
            )
            rows = cursor.fetchall()

            by_operation_type: dict[str, int] = {}
            for row in rows:
                by_operation_type[row["operation"]] = row["count"]

            # 按item类型统计操作数量
            # 需要 JOIN item_results 表，从 item_data JSON 中提取 type 信息用于分类统计
            # 使用 JSON_EXTRACT 从 JSON 中提取类型
            # 过滤 type IS NOT NULL 的操作（目录操作没有 type）
            cursor.execute(
                """
                SELECT
                    json_extract(ir.item_data, '$.type') as item_type,
                    o.operation,
                    COUNT(*) as count
                FROM operations o
                INNER JOIN item_results ir ON o.item_result_id = ir.id
                WHERE o.task_id = ? AND json_extract(ir.item_data, '$.type') IS NOT NULL
                GROUP BY json_extract(ir.item_data, '$.type'), o.operation
                """,
                (self.task_id,),
            )
            rows = cursor.fetchall()

            by_item_type: dict[str, dict[str, int]] = {}
            for row in rows:
                item_type = row["item_type"]
                operation = row["operation"]
                count = row["count"]

                if item_type and item_type not in by_item_type:
                    by_item_type[item_type] = {}
                if item_type:
                    by_item_type[item_type][operation] = count

            return {
                "by_operation_type": by_operation_type,
                "by_item_type": by_item_type,
            }
