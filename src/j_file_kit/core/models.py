"""核心数据模型

定义文件处理过程中的所有数据结构和状态。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


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
    OTHER = "other"


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


class ProcessingContext(BaseModel):
    """处理上下文模型

    贯穿整个处理流程的上下文对象，携带分析结果和中间状态。
    """

    file_info: FileInfo = Field(..., description="文件基础信息")
    file_type: FileType | None = Field(None, description="文件类型（视频/图片/其他）")
    serial_id: str | None = Field(None, description="提取的番号（统一大写）")
    target_path: Path | None = Field(None, description="计划的目标路径")
    skip_remaining: bool = Field(False, description="短路标记，跳过后续处理器")

    # 扩展字段，用于携带自定义状态
    custom_data: dict[str, Any] = Field(default_factory=dict, description="自定义数据")


class ProcessorResult(BaseModel):
    """单个处理器的处理结果"""

    status: ProcessorStatus = Field(..., description="处理状态")
    message: str = Field("", description="处理消息")
    duration_ms: float = Field(0.0, description="处理耗时（毫秒）")
    data: dict[str, Any] = Field(default_factory=dict, description="附加数据")

    @classmethod
    def success(
        cls, message: str = "", data: dict[str, Any] | None = None
    ) -> ProcessorResult:
        """创建成功结果"""
        return cls(status=ProcessorStatus.SUCCESS, message=message, data=data or {})

    @classmethod
    def error(cls, message: str, data: dict[str, Any] | None = None) -> ProcessorResult:
        """创建错误结果"""
        return cls(status=ProcessorStatus.ERROR, message=message, data=data or {})

    @classmethod
    def skip(
        cls, message: str = "", data: dict[str, Any] | None = None
    ) -> ProcessorResult:
        """创建跳过结果"""
        return cls(status=ProcessorStatus.SKIP, message=message, data=data or {})

    @classmethod
    def warning(
        cls, message: str, data: dict[str, Any] | None = None
    ) -> ProcessorResult:
        """创建警告结果"""
        return cls(status=ProcessorStatus.WARNING, message=message, data=data or {})


class TaskResult(BaseModel):
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
    results: list[TaskResult] = Field(default_factory=list, description="详细结果")

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

    def add_result(self, result: TaskResult) -> None:
        """添加处理结果"""
        self.results.append(result)
        self.total_files += 1

        if result.success:
            if result.was_skipped:
                self.skipped_files += 1
            elif result.has_warnings:
                self.warning_files += 1
            else:
                self.success_files += 1
        else:
            self.error_files += 1

        self.total_duration_ms += result.total_duration_ms


class TaskStats(BaseModel):
    """任务统计信息"""

    processed_files: int = Field(0, description="已处理文件数")
    current_file: str | None = Field(None, description="当前处理文件")
    start_time: datetime = Field(default_factory=datetime.now, description="开始时间")
    last_update: datetime = Field(
        default_factory=datetime.now, description="最后更新时间"
    )

    @property
    def elapsed_seconds(self) -> float:
        """已耗时（秒）"""
        return (datetime.now() - self.start_time).total_seconds()

    def update(self, current_file: str | None = None) -> None:
        """更新统计信息"""
        self.processed_files += 1
        self.current_file = current_file
        self.last_update = datetime.now()
