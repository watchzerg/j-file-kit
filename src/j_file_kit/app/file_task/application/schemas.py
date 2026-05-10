"""文件任务 API 请求和响应模型

定义文件任务相关的全部 HTTP API 请求和响应数据结构：
- StartTaskRequest / StartTaskResponse：启动任务
- FileTaskRunStatusResponse：查询执行实例状态
- CancelFileTaskRunResponse：取消执行实例
- FileTaskRunListItem / FileTaskRunListResponse：执行实例列表
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from j_file_kit.app.file_task.domain.task_run import (
    FileTaskRunStatistics,
    FileTaskRunStatus,
    FileTaskTriggerType,
)


class StartTaskRequest(BaseModel):
    """启动任务请求"""

    dry_run: bool = Field(False, description="是否为预览模式")
    trigger_type: str | None = Field(None, description="触发类型（manual/auto）")


class StartTaskResponse(BaseModel):
    """启动任务响应"""

    run_id: int = Field(..., description="执行实例ID")
    run_name: str = Field(..., description="执行实例名称")
    status: FileTaskRunStatus = Field(..., description="执行状态")
    dry_run: bool = Field(..., description="是否为预览模式")


class FileTaskRunStatusResponse(BaseModel):
    """执行实例状态响应"""

    run_id: int = Field(..., description="执行实例ID")
    run_name: str = Field(..., description="执行实例名称")
    task_type: str = Field(..., description="任务类型")
    trigger_type: FileTaskTriggerType = Field(..., description="触发类型")
    dry_run: bool = Field(..., description="是否为预览模式")
    status: FileTaskRunStatus = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")
    duration_ms: float = Field(..., description="已耗时（毫秒）")
    statistics: FileTaskRunStatistics = Field(..., description="统计快照")


class ActiveFileTaskRunResponse(BaseModel):
    """当前活跃执行实例响应"""

    run_id: int = Field(..., description="执行实例ID")
    run_name: str = Field(..., description="执行实例名称")
    task_type: str = Field(..., description="任务类型")
    trigger_type: FileTaskTriggerType = Field(..., description="触发类型")
    status: FileTaskRunStatus = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")


class CancelFileTaskRunResponse(BaseModel):
    """取消执行实例响应"""

    run_id: int = Field(..., description="执行实例ID")
    message: str = Field(..., description="消息")


class DeleteFileTaskRunResponse(BaseModel):
    """删除执行实例响应"""

    run_id: int = Field(..., description="执行实例ID")
    message: str = Field(..., description="消息")


class FileTaskRunStatisticsSummary(BaseModel):
    """执行实例列表统计摘要"""

    total_items: int = Field(0, description="总item数")
    success_items: int = Field(0, description="成功item数")
    error_items: int = Field(0, description="失败item数")
    skipped_items: int = Field(0, description="跳过item数")
    warning_items: int = Field(0, description="警告item数")
    total_duration_ms: float = Field(0.0, description="总耗时（毫秒）")


class FileTaskRunListItem(BaseModel):
    """执行实例列表项"""

    run_id: int = Field(..., description="执行实例ID")
    run_name: str = Field(..., description="执行实例名称")
    task_type: str = Field(..., description="任务类型")
    trigger_type: FileTaskTriggerType = Field(..., description="触发类型")
    dry_run: bool = Field(..., description="是否为预览模式")
    status: FileTaskRunStatus = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    duration_ms: float = Field(..., description="已耗时（毫秒）")
    statistics_summary: FileTaskRunStatisticsSummary = Field(
        ...,
        description="统计摘要",
    )


class FileTaskRunListResponse(BaseModel):
    """执行实例列表响应"""

    runs: list[FileTaskRunListItem] = Field(..., description="执行实例列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页记录数")


class FileTaskRunResultItem(BaseModel):
    """单文件处理结果列表项"""

    id: int = Field(..., description="结果记录ID")
    source_path: str = Field(..., description="源文件路径")
    file_stem: str = Field(..., description="文件名（不含扩展名）")
    file_type: str | None = Field(None, description="文件类型")
    serial_id: str | None = Field(None, description="番号")
    decision_type: str = Field(..., description="处理决策类型")
    target_path: str | None = Field(None, description="目标路径")
    success: bool = Field(..., description="是否处理成功")
    error_message: str | None = Field(None, description="错误消息")
    duration_ms: float = Field(..., description="处理耗时（毫秒）")
    created_at: datetime = Field(..., description="记录创建时间")


class FileTaskRunResultsResponse(BaseModel):
    """单 run 文件处理结果分页响应"""

    results: list[FileTaskRunResultItem] = Field(..., description="文件处理结果列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页记录数")


class FileTaskRunLogLine(BaseModel):
    """单行任务日志"""

    line_no: int = Field(..., description="日志文件中的行号")
    ts: str | None = Field(None, description="日志时间")
    level: str | None = Field(None, description="日志等级")
    msg: str = Field(..., description="日志消息")
    fields: dict[str, Any] = Field(default_factory=dict, description="结构化字段")


class FileTaskRunLogsResponse(BaseModel):
    """单 run 日志分页响应"""

    total_lines: int = Field(..., description="日志总行数")
    offset: int = Field(..., description="起始偏移")
    limit: int = Field(..., description="返回数量上限")
    lines: list[FileTaskRunLogLine] = Field(..., description="日志行")
