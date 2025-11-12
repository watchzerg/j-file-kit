"""API请求和响应模型

定义HTTP API的请求和响应数据结构。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..core.models import TaskStatus


class StartTaskRequest(BaseModel):
    """启动任务请求"""

    dry_run: bool = Field(False, description="是否为预览模式")


class StartTaskResponse(BaseModel):
    """启动任务响应"""

    task_id: str = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: TaskStatus = Field(..., description="任务状态")


class TaskStatusResponse(BaseModel):
    """任务状态响应"""

    task_id: str = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: TaskStatus = Field(..., description="任务状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")
    total_files: int | None = Field(None, description="已处理文件数")


class CancelTaskResponse(BaseModel):
    """取消任务响应"""

    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="消息")


class TaskListItem(BaseModel):
    """任务列表项"""

    task_id: str = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: TaskStatus = Field(..., description="任务状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")


class TaskListResponse(BaseModel):
    """任务列表响应"""

    tasks: list[TaskListItem] = Field(..., description="任务列表")


class UpdateGlobalConfigRequest(BaseModel):
    """更新全局配置请求（部分更新）"""

    scan_roots: list[str] | None = Field(None, description="扫描根目录列表")
    log_dir: str | None = Field(None, description="日志目录")
    report_dir: str | None = Field(None, description="报告目录")


class UpdateTaskConfigRequest(BaseModel):
    """更新任务配置请求（部分更新）"""

    name: str | None = Field(None, description="任务名称")
    enabled: bool | None = Field(None, description="是否启用")
    config: dict[str, Any] | None = Field(None, description="任务特定配置")


class UpdateConfigRequest(BaseModel):
    """更新配置请求（部分更新）"""

    global_: UpdateGlobalConfigRequest | None = Field(
        None, alias="global", description="全局配置"
    )
    tasks: list[UpdateTaskConfigRequest] | None = Field(None, description="任务列表")


class UpdateConfigResponse(BaseModel):
    """更新配置响应"""

    message: str = Field(..., description="成功消息")
    code: str = Field("SUCCESS", description="响应代码")
