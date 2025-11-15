"""领域模型

定义文件处理过程中的所有数据结构和状态。
包含领域实体、值对象和领域异常。
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ProcessorStatus(str, Enum):
    """处理器状态枚举"""

    SUCCESS = "success"
    ERROR = "error"
    SKIP = "skip"
    WARNING = "warning"


class FileType(str, Enum):
    """文件类型枚举"""

    VIDEO = "video"
    IMAGE = "image"
    ARCHIVE = "archive"
    MISC = "misc"


class FileAction(str, Enum):
    """文件动作类型枚举"""

    MOVE_TO_ORGANIZED = "move_to_organized"  # 移动到整理目录（B/ABCD/...）
    MOVE_TO_UNORGANIZED = "move_to_unorganized"  # 移动到无番号目录（C）
    MOVE_TO_ARCHIVE = "move_to_archive"  # 移动到压缩文件目录
    MOVE_TO_MISC = "move_to_misc"  # 移动到其他目录（D）
    DELETE = "delete"  # 删除文件
    SKIP = "skip"  # 跳过处理

    @property
    def description(self) -> str:
        """获取动作的中文描述"""
        descriptions = {
            FileAction.MOVE_TO_ORGANIZED: "整理目录",
            FileAction.MOVE_TO_UNORGANIZED: "无番号目录",
            FileAction.MOVE_TO_ARCHIVE: "压缩文件目录",
            FileAction.MOVE_TO_MISC: "Misc文件目录",
            FileAction.DELETE: "删除",
            FileAction.SKIP: "跳过",
        }
        return descriptions.get(self, self.value)


class SerialId(BaseModel):
    """番号模型

    结构化表示番号，包含字母前缀和数字部分。
    支持从字符串解析（"ABC-123"、"ABC_123"、"ABC123"）和转换为字符串。
    """

    prefix: str = Field(..., description="字母前缀（2-5个大写字母）")
    number: str = Field(..., description="数字部分（2-5个数字）")

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        """验证字母前缀"""
        v_upper = v.upper()
        if not v_upper.isalpha():
            raise ValueError("前缀必须只包含字母")
        if not (2 <= len(v_upper) <= 5):
            raise ValueError("前缀长度必须在2-5个字符之间")
        return v_upper

    @field_validator("number")
    @classmethod
    def validate_number(cls, v: str) -> str:
        """验证数字部分"""
        if not v.isdigit():
            raise ValueError("数字部分必须只包含数字")
        if not (2 <= len(v) <= 5):
            raise ValueError("数字部分长度必须在2-5个字符之间")
        return v

    @classmethod
    def from_string(cls, value: str) -> SerialId:
        """从字符串解析番号

        支持格式：
        - "ABC-123"（连字符分隔）
        - "ABC_123"（下划线分隔）
        - "ABC123"（无分隔符）

        Args:
            value: 番号字符串

        Returns:
            SerialId 对象

        Raises:
            ValueError: 如果字符串格式无效

        Examples:
            >>> SerialId.from_string("ABC-123")
            SerialId(prefix='ABC', number='123')
            >>> SerialId.from_string("ABC_123")
            SerialId(prefix='ABC', number='123')
            >>> SerialId.from_string("ABC123")
            SerialId(prefix='ABC', number='123')
        """
        # 支持连字符、下划线或无分隔符
        pattern = r"^([A-Za-z]{2,5})[-_]?(\d{2,5})$"
        match = re.match(pattern, value)
        if not match:
            raise ValueError(f"无效的番号格式: {value}")
        prefix = match.group(1).upper()
        number = match.group(2)
        return cls(prefix=prefix, number=number)

    @model_validator(mode="before")
    @classmethod
    def parse_string_input(cls, data: Any) -> Any:
        """支持从字符串自动解析（向后兼容）"""
        if isinstance(data, str):
            return cls.from_string(data).model_dump()
        return data

    def __str__(self) -> str:
        """转换为字符串格式：PREFIX-NUMBER"""
        return f"{self.prefix}-{self.number}"


class FileInfo(BaseModel):
    """文件基础信息模型

    轻量级模型，仅包含文件名相关的基础信息，避免文件系统开销。
    """

    path: Path = Field(..., description="文件路径")
    name: str = Field(..., description="文件名（不含扩展名）")
    suffix: str = Field(..., description="文件扩展名（含点号）")

    @classmethod
    def from_path(cls, path: Path) -> FileInfo:
        """从路径创建 FileInfo"""
        return cls(path=path, name=path.stem, suffix=path.suffix.lower())


class DirectoryInfo(BaseModel):
    """目录基础信息模型

    用于表示目录信息，与FileInfo对应，支持统一的扫描接口。
    设计意图：在文件处理流程中，需要同时处理文件和目录，DirectoryInfo提供了目录的统一抽象。
    """

    path: Path = Field(..., description="目录路径")
    name: str = Field(..., description="目录名")

    @classmethod
    def from_path(cls, path: Path) -> DirectoryInfo:
        """从路径创建 DirectoryInfo

        Args:
            path: 目录路径

        Returns:
            DirectoryInfo 对象
        """
        return cls(path=path, name=path.name)


class ProcessingContext(BaseModel):
    """处理上下文模型

    贯穿整个处理流程的上下文对象，携带分析结果和中间状态。
    """

    file_info: FileInfo = Field(..., description="文件基础信息")
    file_type: FileType | None = Field(
        None, description="文件类型（视频/图片/压缩/其他）"
    )
    serial_id: SerialId | None = Field(None, description="提取的番号")
    target_path: Path | None = Field(None, description="计划的目标路径")
    skip_remaining: bool = Field(False, description="短路标记，跳过后续处理器")
    action: FileAction | None = Field(None, description="决策的动作类型")
    target_dir: Path | None = Field(None, description="目标目录（用于移动）")
    should_delete: bool = Field(False, description="是否应该删除")
    file_size: int | None = Field(None, description="文件大小（字节）")
    file_result_id: int | None = Field(None, description="文件结果ID")

    # 扩展字段，用于携带自定义状态
    custom_data: dict[str, Any] = Field(default_factory=dict, description="自定义数据")


class ProcessorResult(BaseModel):
    """单个处理器的处理结果"""

    status: ProcessorStatus = Field(..., description="处理状态")
    message: str = Field("", description="处理消息")
    data: dict[str, Any] = Field(default_factory=dict, description="附加数据")

    @classmethod
    def success(
        cls,
        message: str = "",
        data: dict[str, Any] | None = None,
    ) -> ProcessorResult:
        """创建成功结果"""
        return cls(
            status=ProcessorStatus.SUCCESS,
            message=message,
            data=data or {},
        )

    @classmethod
    def error(cls, message: str, data: dict[str, Any] | None = None) -> ProcessorResult:
        """创建错误结果"""
        return cls(
            status=ProcessorStatus.ERROR,
            message=message,
            data=data or {},
        )

    @classmethod
    def skip(
        cls,
        message: str = "",
        data: dict[str, Any] | None = None,
    ) -> ProcessorResult:
        """创建跳过结果"""
        return cls(
            status=ProcessorStatus.SKIP,
            message=message,
            data=data or {},
        )

    @classmethod
    def warning(
        cls, message: str, data: dict[str, Any] | None = None
    ) -> ProcessorResult:
        """创建警告结果"""
        return cls(
            status=ProcessorStatus.WARNING,
            message=message,
            data=data or {},
        )


class FileResult(BaseModel):
    """单个文件的完整处理结果"""

    file_info: FileInfo = Field(..., description="文件信息")
    context: ProcessingContext = Field(..., description="处理上下文")
    processor_results: list[ProcessorResult] = Field(
        default_factory=list, description="各处理器结果"
    )
    total_duration_ms: float = Field(0.0, description="总处理耗时（毫秒）")
    success: bool = Field(True, description="是否成功")
    error_message: str | None = Field(None, description="错误消息")

    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return any(
            result.status == ProcessorStatus.ERROR for result in self.processor_results
        )

    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return any(
            result.status == ProcessorStatus.WARNING
            for result in self.processor_results
        )

    @property
    def was_skipped(self) -> bool:
        """是否被跳过"""
        return any(
            result.status == ProcessorStatus.SKIP for result in self.processor_results
        )


class TaskReport(BaseModel):
    """任务汇总报告"""

    task_name: str = Field(..., description="任务名称")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    total_files: int = Field(0, description="总文件数")
    success_files: int = Field(0, description="成功文件数")
    error_files: int = Field(0, description="失败文件数")
    skipped_files: int = Field(0, description="跳过文件数")
    warning_files: int = Field(0, description="警告文件数")
    total_duration_ms: float = Field(0.0, description="总耗时（毫秒）")

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_files == 0:
            return 0.0
        return self.success_files / self.total_files

    @property
    def error_rate(self) -> float:
        """错误率"""
        if self.total_files == 0:
            return 0.0
        return self.error_files / self.total_files

    @property
    def duration_seconds(self) -> float:
        """耗时（秒）"""
        return self.total_duration_ms / 1000.0

    def update_from_stats(self, stats: dict[str, Any]) -> None:
        """从统计信息更新报告

        Args:
            stats: 统计信息字典，包含 total_files, success_files, error_files,
                   skipped_files, warning_files, total_duration_ms
        """
        self.total_files = stats.get("total_files", 0)
        self.success_files = stats.get("success_files", 0)
        self.error_files = stats.get("error_files", 0)
        self.skipped_files = stats.get("skipped_files", 0)
        self.warning_files = stats.get("warning_files", 0)
        self.total_duration_ms = stats.get("total_duration_ms", 0.0)


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型枚举"""

    VIDEO_ORGANIZER = "video_organizer"


class TriggerType(str, Enum):
    """触发类型枚举"""

    MANUAL = "manual"
    AUTO = "auto"


class Task(BaseModel):
    """任务模型

    表示一个执行中的任务实例。
    """

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    task_type: TaskType = Field(..., description="任务类型")
    trigger_type: TriggerType = Field(..., description="触发类型")
    status: TaskStatus = Field(..., description="任务状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")
    report: TaskReport | None = Field(None, description="任务报告")


# 领域异常
class TaskError(Exception):
    """任务相关异常基类"""

    pass


class TaskNotFoundError(TaskError):
    """任务不存在异常"""

    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"任务不存在: {task_id}")


class TaskAlreadyRunningError(TaskError):
    """任务已在运行异常"""

    def __init__(self, running_task_id: int):
        self.running_task_id = running_task_id
        super().__init__(f"已有任务正在运行: {running_task_id}")


class TaskCancelledError(TaskError):
    """任务已取消异常"""

    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"任务已取消: {task_id}")
