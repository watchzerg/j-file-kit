"""文件处理决策模型

定义文件处理的决策类型，使用 Discriminated Union 模式。
每个 Decision 类型只包含该操作所需的字段，避免冗余。

设计意图：
- 分析阶段返回具体的 Decision 对象，而不是修改共享 Context
- 每个 Decision 自包含执行所需的全部信息
- 支持 dry_run 预览：生成 Decision 后决定是否执行
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from j_file_kit.app.file_task.domain.models import FileType, SerialId


class MoveDecision(BaseModel):
    """移动文件决策

    用于将文件移动到目标目录（sorted/unsorted/archive/misc）。
    """

    decision_type: Literal["move"] = Field(
        default="move",
        description="决策类型标识，用于 Discriminated Union",
    )
    source_path: Path = Field(..., description="源文件路径")
    target_path: Path = Field(..., description="目标文件路径")
    file_type: FileType = Field(..., description="文件类型，用于日志和统计")
    serial_id: SerialId | None = Field(None, description="番号，用于日志和统计")


class DeleteDecision(BaseModel):
    """删除文件决策

    用于删除符合删除规则的文件（如小体积 misc 文件）。
    """

    decision_type: Literal["delete"] = Field(
        default="delete",
        description="决策类型标识，用于 Discriminated Union",
    )
    source_path: Path = Field(..., description="源文件路径")
    file_type: FileType = Field(..., description="文件类型，用于日志和统计")
    reason: str = Field(..., description="删除原因")


class SkipDecision(BaseModel):
    """跳过文件决策

    用于跳过不需要处理的文件。
    """

    decision_type: Literal["skip"] = Field(
        default="skip",
        description="决策类型标识，用于 Discriminated Union",
    )
    source_path: Path = Field(..., description="源文件路径")
    file_type: FileType | None = Field(None, description="文件类型，用于日志和统计")
    reason: str = Field(..., description="跳过原因")


# Discriminated Union：通过 decision_type 字段区分类型
FileDecision = MoveDecision | DeleteDecision | SkipDecision


class FileItemData(BaseModel):
    """文件处理结果数据

    用于持久化文件处理结果的数据模型。
    替代原来的 FileItemResult，不依赖 Context。
    """

    path: Path = Field(..., description="文件路径")
    stem: str = Field(..., description="文件名（不含扩展名）")
    file_type: FileType | None = Field(None, description="文件类型")
    serial_id: SerialId | None = Field(None, description="番号")
    decision_type: str = Field(..., description="决策类型（move/delete/skip）")
    target_path: Path | None = Field(None, description="目标路径（移动操作时有值）")
    success: bool = Field(True, description="是否成功")
    error_message: str | None = Field(None, description="错误消息")
    duration_ms: float = Field(0.0, description="处理耗时（毫秒）")
