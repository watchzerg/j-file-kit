"""文件任务 API 请求和响应模型

定义文件任务相关的 HTTP API 请求和响应数据结构。
"""

from pydantic import BaseModel, Field

from j_file_kit.app.task.domain import TaskStatus


class StartTaskRequest(BaseModel):
    """启动任务请求"""

    dry_run: bool = Field(False, description="是否为预览模式")
    trigger_type: str | None = Field(None, description="触发类型（manual/auto）")


class StartTaskResponse(BaseModel):
    """启动任务响应"""

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: TaskStatus = Field(..., description="任务状态")
