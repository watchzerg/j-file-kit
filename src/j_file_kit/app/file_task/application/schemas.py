"""文件任务 API 请求和响应模型

定义文件任务相关的全部 HTTP API 请求和响应数据结构：
- StartTaskRequest / StartTaskResponse：启动任务
- FileTaskRunStatusResponse：查询执行实例状态
- CancelFileTaskRunResponse：取消执行实例
- FileTaskRunListItem / FileTaskRunListResponse：执行实例列表
"""

from datetime import datetime

from pydantic import BaseModel, Field

from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatus


class StartTaskRequest(BaseModel):
    """启动任务请求"""

    dry_run: bool = Field(False, description="是否为预览模式")
    trigger_type: str | None = Field(None, description="触发类型（manual/auto）")


class StartTaskResponse(BaseModel):
    """启动任务响应"""

    run_id: int = Field(..., description="执行实例ID")
    run_name: str = Field(..., description="执行实例名称")
    status: FileTaskRunStatus = Field(..., description="执行状态")


class FileTaskRunStatusResponse(BaseModel):
    """执行实例状态响应"""

    run_id: int = Field(..., description="执行实例ID")
    run_name: str = Field(..., description="执行实例名称")
    status: FileTaskRunStatus = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")
    total_items: int | None = Field(None, description="已处理item数")


class CancelFileTaskRunResponse(BaseModel):
    """取消执行实例响应"""

    run_id: int = Field(..., description="执行实例ID")
    message: str = Field(..., description="消息")


class FileTaskRunListItem(BaseModel):
    """执行实例列表项"""

    run_id: int = Field(..., description="执行实例ID")
    run_name: str = Field(..., description="执行实例名称")
    status: FileTaskRunStatus = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")


class FileTaskRunListResponse(BaseModel):
    """执行实例列表响应"""

    runs: list[FileTaskRunListItem] = Field(..., description="执行实例列表")
