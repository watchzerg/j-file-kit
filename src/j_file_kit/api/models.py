"""API请求和响应模型

定义HTTP API的请求和响应数据结构。
"""

from __future__ import annotations

from datetime import datetime

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
