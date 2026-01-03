"""文件处理操作仓储

提供 file_operations 表的 CRUD 操作。
记录文件操作日志，支持查询操作历史。
只处理文件操作，不处理目录操作。
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from j_file_kit.app.file_task.domain.models import Operation, OperationType
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class FileProcessorRepositoryImpl:
    """文件处理操作仓储实现

    提供文件操作日志的持久化操作。
    只处理文件操作（MOVE、DELETE、RENAME），拒绝目录操作。

    实现 FileProcessorRepository Protocol。

    设计说明：方法接收 task_id 参数，支持作为单例复用。
    """

    def __init__(
        self,
        connection_manager: SQLiteConnectionManager,
    ) -> None:
        """初始化文件处理操作仓储

        Args:
            connection_manager: SQLite 连接管理器
        """
        self._conn_manager = connection_manager

    def _row_to_operation(self, row: sqlite3.Row) -> Operation:
        """将数据库行转换为操作记录对象

        Args:
            row: 数据库行

        Returns:
            Operation 对象
        """
        source_path = Path(row["source_path"])
        target_path = Path(row["target_path"]) if row["target_path"] else None

        return Operation(
            id=row["id"],
            task_id=int(row["task_id"]),
            file_item_id=row["file_item_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            operation=OperationType(row["operation"]),
            source_path=source_path,
            target_path=target_path,
            file_type=row["file_type"],
            serial_id=row["serial_id"],
        )

    def create_operation(
        self,
        task_id: int,
        operation: OperationType,
        source_path: Path,
        target_path: Path | None = None,
        file_item_id: int | None = None,
        file_type: str | None = None,
        serial_id: str | None = None,
    ) -> str:
        """创建操作记录

        只接受文件操作类型（MOVE、DELETE、RENAME），拒绝目录操作类型。

        Args:
            task_id: 任务 ID
            operation: 操作类型（必须是文件操作，不能是 CREATE_DIR 或 DELETE_DIR）
            source_path: 源路径
            target_path: 目标路径（可选）
            file_item_id: 文件项ID（可选）
            file_type: 文件类型（冗余字段，避免 JOIN）
            serial_id: 番号（冗余字段，避免 JOIN）

        Returns:
            生成的操作ID（UUID字符串）

        Raises:
            ValueError: 如果操作类型是目录操作（CREATE_DIR 或 DELETE_DIR）
        """
        # 检查操作类型，拒绝目录操作
        # 注意：由于 OperationType 枚举中已删除 CREATE_DIR 和 DELETE_DIR，
        # 这里主要是防御性检查，如果未来有人尝试传入这些值会抛出异常
        if operation.value in ("create_dir", "delete_dir"):
            raise ValueError(f"不支持目录操作类型: {operation.value}")

        operation_id = str(uuid.uuid4())
        timestamp = datetime.now()

        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO file_operations (
                    id, task_id, file_item_id, timestamp, operation,
                    source_path, target_path, file_type, serial_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operation_id,
                    task_id,
                    file_item_id,
                    timestamp.isoformat(),
                    operation.value,
                    str(source_path),
                    str(target_path) if target_path else None,
                    file_type,
                    serial_id,
                ),
            )

        return operation_id

    def get_operations(self, task_id: int) -> list[Operation]:
        """获取任务的操作记录

        Args:
            task_id: 任务 ID

        Returns:
            操作记录列表
        """
        with self._conn_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM file_operations WHERE task_id = ? ORDER BY timestamp",
                (task_id,),
            )
            rows = cursor.fetchall()

            return [self._row_to_operation(row) for row in rows]

    def get_operation_statistics(self, task_id: int) -> dict[str, Any]:
        """获取任务的操作统计信息

        统计操作数量，包含两个维度：
        - by_operation_type: 按操作类型统计
        - by_item_type: 按文件类型统计操作数量

        使用冗余字段 file_type 直接统计，无需 JOIN file_items 表。

        Args:
            task_id: 任务 ID

        Returns:
            操作统计字典，格式：
            {
                "by_operation_type": {
                    "move": 10,
                    "delete": 5,
                    "rename": 2
                },
                "by_item_type": {
                    "video": {"move": 8, "delete": 2},
                    "image": {"move": 2},
                    ...
                }
            }
        """
        with self._conn_manager.get_cursor() as cursor:
            # 按操作类型统计
            cursor.execute(
                """
                SELECT operation, COUNT(*) as count
                FROM file_operations
                WHERE task_id = ?
                GROUP BY operation
                """,
                (task_id,),
            )
            rows = cursor.fetchall()

            by_operation_type: dict[str, int] = {}
            for row in rows:
                by_operation_type[row["operation"]] = row["count"]

            # 按文件类型统计操作数量
            # 直接使用 file_type 字段，无需 JOIN
            cursor.execute(
                """
                SELECT
                    file_type,
                    operation,
                    COUNT(*) as count
                FROM file_operations
                WHERE task_id = ? AND file_type IS NOT NULL
                GROUP BY file_type, operation
                """,
                (task_id,),
            )
            rows = cursor.fetchall()

            by_item_type: dict[str, dict[str, int]] = {}
            for row in rows:
                file_type = row["file_type"]
                operation = row["operation"]
                count = row["count"]

                if file_type and file_type not in by_item_type:
                    by_item_type[file_type] = {}
                if file_type:
                    by_item_type[file_type][operation] = count

            return {
                "by_operation_type": by_operation_type,
                "by_item_type": by_item_type,
            }
