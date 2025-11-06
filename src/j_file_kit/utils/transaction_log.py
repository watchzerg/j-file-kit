"""事务日志模块

记录所有文件操作。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class OperationType:
    """操作类型常量"""

    RENAME = "rename"
    MOVE = "move"
    DELETE = "delete"
    CREATE_DIR = "create_dir"
    DELETE_DIR = "delete_dir"


class TransactionEntry:
    """事务日志条目"""

    def __init__(
        self,
        operation: str,
        source_path: Path,
        target_path: Path | None = None,
        data: dict[str, Any] | None = None,
    ):
        """初始化事务条目

        Args:
            operation: 操作类型
            source_path: 源路径
            target_path: 目标路径（可选）
            data: 附加数据
        """
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.operation = operation
        self.source_path = source_path
        self.target_path = target_path
        self.data = data or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "source_path": str(self.source_path),
            "target_path": str(self.target_path) if self.target_path else None,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransactionEntry:
        """从字典创建（兼容旧格式）"""
        entry = cls(
            operation=data["operation"],
            source_path=Path(data["source_path"]),
            target_path=Path(data["target_path"]) if data.get("target_path") else None,
            data=data.get("data", {}),
        )
        entry.id = data["id"]
        entry.timestamp = datetime.fromisoformat(data["timestamp"])
        # 忽略旧格式中的 completed 和 rolled_back 字段
        return entry


class TransactionLog:
    """事务日志管理器"""

    def __init__(self, log_dir: Path, task_name: str):
        """初始化事务日志

        Args:
            log_dir: 日志目录
            task_name: 任务名称
        """
        self.log_dir = log_dir
        self.task_name = task_name
        self.task_id = str(uuid.uuid4())[:8]
        self.log_file = log_dir / f"transaction_{task_name}_{self.task_id}.jsonl"

        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _write_transaction(self, entry: TransactionEntry) -> None:
        """写入事务记录"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def create_rename_entry(
        self, source_path: Path, target_path: Path, data: dict[str, Any] | None = None
    ) -> TransactionEntry:
        """创建重命名事务条目

        Args:
            source_path: 源路径
            target_path: 目标路径
            data: 附加数据

        Returns:
            事务条目对象
        """
        entry = TransactionEntry(
            operation=OperationType.RENAME,
            source_path=source_path,
            target_path=target_path,
            data=data,
        )
        return entry

    def create_move_entry(
        self, source_path: Path, target_path: Path, data: dict[str, Any] | None = None
    ) -> TransactionEntry:
        """创建移动事务条目

        Args:
            source_path: 源路径
            target_path: 目标路径
            data: 附加数据

        Returns:
            事务条目对象
        """
        entry = TransactionEntry(
            operation=OperationType.MOVE,
            source_path=source_path,
            target_path=target_path,
            data=data,
        )
        return entry

    def create_delete_entry(
        self, path: Path, data: dict[str, Any] | None = None
    ) -> TransactionEntry:
        """创建删除事务条目

        Args:
            path: 删除路径
            data: 附加数据

        Returns:
            事务条目对象
        """
        entry = TransactionEntry(
            operation=OperationType.DELETE, source_path=path, data=data
        )
        return entry

    def create_dir_entry(
        self, path: Path, data: dict[str, Any] | None = None
    ) -> TransactionEntry:
        """创建目录事务条目

        Args:
            path: 目录路径
            data: 附加数据

        Returns:
            事务条目对象
        """
        entry = TransactionEntry(
            operation=OperationType.CREATE_DIR, source_path=path, data=data
        )
        return entry

    def create_delete_dir_entry(
        self, path: Path, data: dict[str, Any] | None = None
    ) -> TransactionEntry:
        """创建删除目录事务条目

        Args:
            path: 目录路径
            data: 附加数据

        Returns:
            事务条目对象
        """
        entry = TransactionEntry(
            operation=OperationType.DELETE_DIR, source_path=path, data=data
        )
        return entry

    def write_entry(self, entry: TransactionEntry) -> None:
        """写入事务条目到日志文件

        Args:
            entry: 事务条目对象
        """
        self._write_transaction(entry)
