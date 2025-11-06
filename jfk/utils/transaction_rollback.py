"""事务回滚模块

提供事务日志的回滚功能。
"""

from __future__ import annotations

from typing import List

from .transaction_log import OperationType, TransactionEntry, TransactionLog


def get_rollback_plan(transaction_log: TransactionLog) -> List[TransactionEntry]:
    """获取回滚计划
    
    按相反顺序返回已完成的事务，用于回滚操作。
    
    Args:
        transaction_log: 事务日志实例
        
    Returns:
        按相反顺序排列的事务条目列表
    """
    completed = transaction_log.read_transactions()
    return list(reversed(completed))


def rollback_all(transaction_log: TransactionLog) -> List[str]:
    """回滚所有操作
    
    回滚操作作为独立任务，写入新的日志文件。
    
    Args:
        transaction_log: 事务日志实例
        
    Returns:
        回滚的事务ID列表
    """
    rollback_plan = get_rollback_plan(transaction_log)
    if not rollback_plan:
        return []
    
    # 创建新的 TransactionLog 实例用于记录回滚操作
    rollback_log = TransactionLog(transaction_log.log_dir, f"{transaction_log.task_name}_rollback")
    rolled_back_ids = []
    
    for entry in rollback_plan:
        try:
            if entry.operation == OperationType.RENAME:
                # 重命名回滚：将目标路径重命名回源路径
                if entry.target_path and entry.target_path.exists():
                    entry.target_path.rename(entry.source_path)
                    # 记录回滚操作到新的日志文件
                    rollback_entry = rollback_log.create_rename_entry(
                        entry.target_path,
                        entry.source_path,
                        {"original_transaction_id": entry.id, "operation": "rollback_rename"}
                    )
                    rollback_log.write_entry(rollback_entry)
                    rolled_back_ids.append(entry.id)
            
            elif entry.operation == OperationType.MOVE:
                # 移动回滚：将目标路径移动回源路径
                if entry.target_path and entry.target_path.exists():
                    entry.target_path.rename(entry.source_path)
                    # 记录回滚操作到新的日志文件
                    rollback_entry = rollback_log.create_move_entry(
                        entry.target_path,
                        entry.source_path,
                        {"original_transaction_id": entry.id, "operation": "rollback_move"}
                    )
                    rollback_log.write_entry(rollback_entry)
                    rolled_back_ids.append(entry.id)
            
            elif entry.operation == OperationType.DELETE:
                # 删除回滚：无法恢复，只能记录
                rollback_entry = rollback_log.create_delete_entry(
                    entry.source_path,
                    {"original_transaction_id": entry.id, "operation": "rollback_delete", "note": "无法恢复已删除的文件"}
                )
                rollback_log.write_entry(rollback_entry)
                rolled_back_ids.append(entry.id)
            
            elif entry.operation == OperationType.CREATE_DIR:
                # 创建目录回滚：删除目录
                if entry.source_path.exists():
                    entry.source_path.rmdir()
                    rollback_entry = rollback_log.create_delete_dir_entry(
                        entry.source_path,
                        {"original_transaction_id": entry.id, "operation": "rollback_create_dir"}
                    )
                    rollback_log.write_entry(rollback_entry)
                    rolled_back_ids.append(entry.id)
            
            elif entry.operation == OperationType.DELETE_DIR:
                # 删除目录回滚：重新创建目录
                entry.source_path.mkdir(parents=True, exist_ok=True)
                rollback_entry = rollback_log.create_dir_entry(
                    entry.source_path,
                    {"original_transaction_id": entry.id, "operation": "rollback_delete_dir"}
                )
                rollback_log.write_entry(rollback_entry)
                rolled_back_ids.append(entry.id)
        
        except Exception as e:
            # 记录回滚失败，但继续处理其他事务
            print(f"回滚事务 {entry.id} 失败: {e}")
    
    return rolled_back_ids

