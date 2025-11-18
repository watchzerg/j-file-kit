"""操作记录模型

定义文件操作记录的数据结构。
用于记录任务执行过程中的文件操作历史，如移动、删除、重命名等。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class OperationType(str, Enum):
    """操作类型枚举"""

    RENAME = "rename"
    MOVE = "move"
    DELETE = "delete"
    CREATE_DIR = "create_dir"
    DELETE_DIR = "delete_dir"


class Operation(BaseModel):
    """操作记录模型

    表示一个文件操作记录，包含操作类型、路径信息、时间戳等。
    用于持久化文件操作历史，支持查询和统计。
    """

    id: str = Field(..., description="操作ID（UUID字符串）")
    task_id: int = Field(..., description="任务ID")
    item_result_id: int | None = Field(None, description="Item结果ID（可选）")
    timestamp: datetime = Field(..., description="操作时间")
    operation: OperationType = Field(..., description="操作类型")
    source_path: Path | None = Field(None, description="源路径（可选）")
    target_path: Path | None = Field(None, description="目标路径（可选）")
    data: dict[str, Any] = Field(default_factory=dict, description="附加数据")
