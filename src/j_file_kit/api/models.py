"""API请求和响应模型

定义HTTP API的请求和响应数据结构。
用于API层的数据传输，与领域模型分离。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from j_file_kit.models.task import TaskStatus


class StartTaskRequest(BaseModel):
    """启动任务请求"""

    dry_run: bool = Field(False, description="是否为预览模式")
    trigger_type: str | None = Field(None, description="触发类型（manual/auto）")


class StartTaskResponse(BaseModel):
    """启动任务响应"""

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: TaskStatus = Field(..., description="任务状态")


class TaskStatusResponse(BaseModel):
    """任务状态响应"""

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: TaskStatus = Field(..., description="任务状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")
    total_items: int | None = Field(None, description="已处理item数")


class CancelTaskResponse(BaseModel):
    """取消任务响应"""

    task_id: int = Field(..., description="任务ID")
    message: str = Field(..., description="消息")


class TaskListItem(BaseModel):
    """任务列表项"""

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: TaskStatus = Field(..., description="任务状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")


class TaskListResponse(BaseModel):
    """任务列表响应"""

    tasks: list[TaskListItem] = Field(..., description="任务列表")


class UpdateGlobalConfigRequest(BaseModel):
    """更新全局配置请求（部分更新）"""

    inbox_dir: str | None = Field(None, description="待处理目录")
    sorted_dir: str | None = Field(None, description="已整理目录（有番号）")
    unsorted_dir: str | None = Field(None, description="未整理目录（无番号）")
    archive_dir: str | None = Field(None, description="归档目录")
    misc_dir: str | None = Field(None, description="杂项目录")
    starred_dir: str | None = Field(None, description="精选/收藏目录")


class UpdateTaskConfigRequest(BaseModel):
    """更新任务配置请求（部分更新）"""

    name: str | None = Field(None, description="任务名称")
    enabled: bool | None = Field(None, description="是否启用")
    config: dict[str, Any] | None = Field(None, description="任务特定配置")


class UpdateConfigRequest(BaseModel):
    """更新配置请求（部分更新）"""

    global_: UpdateGlobalConfigRequest | None = Field(
        None,
        alias="global",
        description="全局配置",
    )
    tasks: list[UpdateTaskConfigRequest] | None = Field(None, description="任务列表")


class UpdateConfigResponse(BaseModel):
    """更新配置响应"""

    message: str = Field(..., description="成功消息")
    code: str = Field("SUCCESS", description="响应代码")
