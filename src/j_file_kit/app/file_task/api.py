"""文件任务 API 路由

定义文件任务相关的 HTTP API 路由处理函数。
提供文件任务的启动功能。
"""

from fastapi import APIRouter, HTTPException, Request, status

from j_file_kit.app.file_task.schemas import (
    StartTaskRequest,
    StartTaskResponse,
)
from j_file_kit.app.file_task.service.jav_video_organizer import JavVideoOrganizer
from j_file_kit.infrastructure.app_state import AppState
from j_file_kit.shared.interfaces.task import BaseTask
from j_file_kit.shared.models.enums import TaskType, TriggerType

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def get_task_instance(task_type: str, app_state: AppState) -> BaseTask:
    """获取任务实例

    Args:
        task_type: 任务类型
        app_state: 应用状态

    Returns:
        任务实例

    Raises:
        HTTPException: 如果任务不存在
    """
    if task_type == TaskType.JAV_VIDEO_ORGANIZER.value:
        return JavVideoOrganizer(app_state.config, app_state.log_dir)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_type}",
        )


@router.post("/{task_type}/start", response_model=StartTaskResponse)
async def start_task(
    task_type: str,
    body: StartTaskRequest,
    request: Request,
) -> StartTaskResponse:
    """启动任务

    Args:
        task_type: 任务类型
        body: 启动任务请求
        request: HTTP请求对象

    Returns:
        启动任务响应

    Raises:
        HTTPException: 如果任务不存在或已有任务正在运行
    """
    app_state: AppState = request.state.app_state
    task = get_task_instance(task_type, app_state)

    # 解析 trigger_type，默认为 MANUAL
    trigger_type = TriggerType.MANUAL
    if body.trigger_type:
        try:
            trigger_type = TriggerType(body.trigger_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的触发类型: {body.trigger_type}",
            ) from None

    task_id = app_state.task_manager.start_task(
        task,
        trigger_type=trigger_type,
        dry_run=body.dry_run,
    )
    task_model = app_state.task_manager.get_task(task_id)

    return StartTaskResponse(
        task_id=task_id,
        task_name=task_model.task_name,
        status=task_model.status,
    )
