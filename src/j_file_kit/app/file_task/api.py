"""文件任务 API 路由

定义文件任务相关的 HTTP API 路由处理函数。
提供文件任务的启动功能。
"""

from fastapi import APIRouter, HTTPException, Request, status

from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.application.jav_video_organizer import JavVideoOrganizer
from j_file_kit.app.file_task.application.schemas import (
    StartTaskRequest,
    StartTaskResponse,
)
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.task.domain.models import TaskRunner, TriggerType
from j_file_kit.app.task_config.domain.models import TaskConfig

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _get_task_config(task_type: str, app_state: AppState) -> TaskConfig:
    """获取指定任务配置"""
    task_config = app_state.task_config_repository.get_by_type(task_type)
    if task_config is not None:
        return task_config
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"任务配置不存在: {task_type}",
    )


def _new_task_instance(task_type: str, app_state: AppState) -> TaskRunner:
    """获取任务实例

    在 API 层组装任务实例，注入所需的 repositories。

    Args:
        task_type: 任务类型
        app_state: 应用状态

    Returns:
        任务实例

    Raises:
        HTTPException: 如果任务不存在
    """
    if task_type == TASK_TYPE_JAV_VIDEO_ORGANIZER:
        return JavVideoOrganizer(
            global_config=app_state.get_global_config(),
            task_config=_get_task_config(task_type, app_state),
            log_dir=app_state.log_dir,
            file_result_repository=app_state.file_result_repository,
        )
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
    task = _new_task_instance(task_type, app_state)

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
