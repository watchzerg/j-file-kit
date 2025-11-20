"""领域结果模型

定义处理结果相关的模型，包括处理器结果和Item处理结果。
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .contexts import ItemContext, PathEntryContext
from .path_entry import PathEntryInfo


class ProcessorStatus(str, Enum):
    """处理器状态枚举"""

    SUCCESS = "success"
    ERROR = "error"
    SKIP = "skip"
    WARNING = "warning"


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


class ItemResult(BaseModel):
    """Item 处理结果基类

    所有 item 处理结果的通用基类，包含通用的处理状态和结果信息。
    支持未来扩展不同类型的 item（文件、网页、爬虫数据等）。
    """

    context: ItemContext = Field(..., description="处理上下文")
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


class FileItemResult(ItemResult):
    """文件处理结果

    文件类型的 item 处理结果，继承 ItemResult 并添加文件特定的字段。
    现在统一处理文件和文件夹，但主要用于文件处理结果。
    """

    item_info: PathEntryInfo = Field(..., description="路径项信息")
    context: PathEntryContext = Field(..., description="处理上下文")
