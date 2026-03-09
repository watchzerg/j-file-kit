"""文件任务 API 请求和响应模型

定义文件任务相关的全部 HTTP API 请求和响应数据结构：
- StartTaskRequest / StartTaskResponse：启动任务
- FileTaskStatusResponse：查询任务状态
- CancelFileTaskResponse：取消任务
- FileTaskListItem / FileTaskListResponse：任务列表
"""

from datetime import datetime

from pydantic import BaseModel, Field

from j_file_kit.app.file_task.domain.models import FileTaskStatus


class StartTaskRequest(BaseModel):
    """启动任务请求"""

    dry_run: bool = Field(False, description="是否为预览模式")
    trigger_type: str | None = Field(None, description="触发类型（manual/auto）")


class StartTaskResponse(BaseModel):
    """启动任务响应"""

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: FileTaskStatus = Field(..., description="任务状态")


class FileTaskStatusResponse(BaseModel):
    """任务状态响应"""

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: FileTaskStatus = Field(..., description="任务状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")
    total_items: int | None = Field(None, description="已处理item数")


class CancelFileTaskResponse(BaseModel):
    """取消任务响应"""

    task_id: int = Field(..., description="任务ID")
    message: str = Field(..., description="消息")


class FileTaskListItem(BaseModel):
    """任务列表项"""

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: FileTaskStatus = Field(..., description="任务状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")


class FileTaskListResponse(BaseModel):
    """任务列表响应"""

    tasks: list[FileTaskListItem] = Field(..., description="任务列表")
