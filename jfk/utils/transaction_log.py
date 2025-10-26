"""事务日志模块

记录所有文件操作，支持手动回滚。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..core.models import FileInfo, ProcessingContext, ProcessorResult


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
        data: Dict[str, Any] | None = None
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
        self.completed = False
        self.rolled_back = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "source_path": str(self.source_path),
            "target_path": str(self.target_path) if self.target_path else None,
            "data": self.data,
            "completed": self.completed,
            "rolled_back": self.rolled_back
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TransactionEntry:
        """从字典创建"""
        entry = cls(
            operation=data["operation"],
            source_path=Path(data["source_path"]),
            target_path=Path(data["target_path"]) if data.get("target_path") else None,
            data=data.get("data", {})
        )
        entry.id = data["id"]
        entry.timestamp = datetime.fromisoformat(data["timestamp"])
        entry.completed = data.get("completed", False)
        entry.rolled_back = data.get("rolled_back", False)
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
        
        # 内存中的事务列表
        self.transactions: List[TransactionEntry] = []
    
    def _write_transaction(self, entry: TransactionEntry) -> None:
        """写入事务记录"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
    
    def log_rename(self, source_path: Path, target_path: Path, data: Dict[str, Any] | None = None) -> str:
        """记录重命名操作
        
        Args:
            source_path: 源路径
            target_path: 目标路径
            data: 附加数据
            
        Returns:
            事务ID
        """
        entry = TransactionEntry(
            operation=OperationType.RENAME,
            source_path=source_path,
            target_path=target_path,
            data=data
        )
        self.transactions.append(entry)
        self._write_transaction(entry)
        return entry.id
    
    def log_move(self, source_path: Path, target_path: Path, data: Dict[str, Any] | None = None) -> str:
        """记录移动操作
        
        Args:
            source_path: 源路径
            target_path: 目标路径
            data: 附加数据
            
        Returns:
            事务ID
        """
        entry = TransactionEntry(
            operation=OperationType.MOVE,
            source_path=source_path,
            target_path=target_path,
            data=data
        )
        self.transactions.append(entry)
        self._write_transaction(entry)
        return entry.id
    
    def log_delete(self, path: Path, data: Dict[str, Any] | None = None) -> str:
        """记录删除操作
        
        Args:
            path: 删除路径
            data: 附加数据
            
        Returns:
            事务ID
        """
        entry = TransactionEntry(
            operation=OperationType.DELETE,
            source_path=path,
            data=data
        )
        self.transactions.append(entry)
        self._write_transaction(entry)
        return entry.id
    
    def log_create_dir(self, path: Path, data: Dict[str, Any] | None = None) -> str:
        """记录创建目录操作
        
        Args:
            path: 目录路径
            data: 附加数据
            
        Returns:
            事务ID
        """
        entry = TransactionEntry(
            operation=OperationType.CREATE_DIR,
            source_path=path,
            data=data
        )
        self.transactions.append(entry)
        self._write_transaction(entry)
        return entry.id
    
    def log_delete_dir(self, path: Path, data: Dict[str, Any] | None = None) -> str:
        """记录删除目录操作
        
        Args:
            path: 目录路径
            data: 附加数据
            
        Returns:
            事务ID
        """
        entry = TransactionEntry(
            operation=OperationType.DELETE_DIR,
            source_path=path,
            data=data
        )
        self.transactions.append(entry)
        self._write_transaction(entry)
        return entry.id
    
    def mark_completed(self, transaction_id: str) -> None:
        """标记事务为已完成
        
        Args:
            transaction_id: 事务ID
        """
        for entry in self.transactions:
            if entry.id == transaction_id:
                entry.completed = True
                self._write_transaction(entry)
                break
    
    def mark_rolled_back(self, transaction_id: str) -> None:
        """标记事务为已回滚
        
        Args:
            transaction_id: 事务ID
        """
        for entry in self.transactions:
            if entry.id == transaction_id:
                entry.rolled_back = True
                self._write_transaction(entry)
                break
    
    def get_completed_transactions(self) -> List[TransactionEntry]:
        """获取已完成的事务"""
        return [entry for entry in self.transactions if entry.completed and not entry.rolled_back]
    
    def get_rollback_plan(self) -> List[TransactionEntry]:
        """获取回滚计划
        
        按相反顺序返回已完成的事务，用于回滚操作。
        """
        completed = self.get_completed_transactions()
        return list(reversed(completed))
    
    def rollback_all(self) -> List[str]:
        """回滚所有操作
        
        Returns:
            回滚的事务ID列表
        """
        rollback_plan = self.get_rollback_plan()
        rolled_back_ids = []
        
        for entry in rollback_plan:
            try:
                if entry.operation == OperationType.RENAME:
                    # 重命名回滚：将目标路径重命名回源路径
                    if entry.target_path and entry.target_path.exists():
                        entry.target_path.rename(entry.source_path)
                        self.mark_rolled_back(entry.id)
                        rolled_back_ids.append(entry.id)
                
                elif entry.operation == OperationType.MOVE:
                    # 移动回滚：将目标路径移动回源路径
                    if entry.target_path and entry.target_path.exists():
                        entry.target_path.rename(entry.source_path)
                        self.mark_rolled_back(entry.id)
                        rolled_back_ids.append(entry.id)
                
                elif entry.operation == OperationType.DELETE:
                    # 删除回滚：无法恢复，只能记录
                    self.mark_rolled_back(entry.id)
                    rolled_back_ids.append(entry.id)
                
                elif entry.operation == OperationType.CREATE_DIR:
                    # 创建目录回滚：删除目录
                    if entry.source_path.exists():
                        entry.source_path.rmdir()
                        self.mark_rolled_back(entry.id)
                        rolled_back_ids.append(entry.id)
                
                elif entry.operation == OperationType.DELETE_DIR:
                    # 删除目录回滚：重新创建目录
                    entry.source_path.mkdir(parents=True, exist_ok=True)
                    self.mark_rolled_back(entry.id)
                    rolled_back_ids.append(entry.id)
            
            except Exception as e:
                # 记录回滚失败，但继续处理其他事务
                print(f"回滚事务 {entry.id} 失败: {e}")
        
        return rolled_back_ids
    
    def load_from_file(self) -> None:
        """从文件加载事务记录"""
        if not self.log_file.exists():
            return
        
        self.transactions.clear()
        
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    entry = TransactionEntry.from_dict(data)
                    self.transactions.append(entry)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取事务摘要"""
        total = len(self.transactions)
        completed = len([t for t in self.transactions if t.completed])
        rolled_back = len([t for t in self.transactions if t.rolled_back])
        
        return {
            "task_name": self.task_name,
            "task_id": self.task_id,
            "total_transactions": total,
            "completed_transactions": completed,
            "rolled_back_transactions": rolled_back,
            "pending_transactions": total - completed - rolled_back
        }
