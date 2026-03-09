"""文件任务 API 路由

定义文件任务相关的全部 HTTP API 路由处理函数：
- POST /{task_type}/start：启动任务
- GET /{task_id}：查询任务状态
- POST /{task_id}/cancel：取消任务
- GET /：列出所有任务
"""

from fastapi import APIRouter, HTTPException, Request, status

from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.application.jav_video_organizer import JavVideoOrganizer
from j_file_kit.app.file_task.application.schemas import (
    CancelFileTaskResponse,
    FileTaskListItem,
    FileTaskListResponse,
    FileTaskStatusResponse,
    StartTaskRequest,
    StartTaskResponse,
)
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import (
    FileTaskRunner,
    FileTaskStatus,
    FileTaskTriggerType,
)
from j_file_kit.app.task_config.domain.models import TaskConfig

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _parse_task_id(task_id_str: str) -> int:
    """解析任务ID字符串为整数

    Args:
        task_id_str: 任务ID字符串

    Returns:
        任务ID整数

    Raises:
        HTTPException: 如果 task_id 格式无效
    """
    try:
        return int(task_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的任务ID格式: {task_id_str}",
        ) from None


def _get_task_config(task_type: str, app_state: AppState) -> TaskConfig:
    """获取指定任务配置，不存在时抛出 404

    Args:
        task_type: 任务类型
        app_state: 应用状态

    Returns:
        任务配置

    Raises:
        HTTPException: 如果任务配置不存在
    """
    task_config = app_state.task_config_repository.get_by_type(task_type)
    if task_config is not None:
        return task_config
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"任务配置不存在: {task_type}",
    )


def _new_task_instance(task_type: str, app_state: AppState) -> FileTaskRunner:
    """在 API 层组装任务实例，注入所需的 repositories

    Args:
        task_type: 任务类型
        app_state: 应用状态

    Returns:
        任务实例

    Raises:
        HTTPException: 如果任务类型未知
    """
    if task_type == TASK_TYPE_JAV_VIDEO_ORGANIZER:
        return JavVideoOrganizer(
            task_config=_get_task_config(task_type, app_state),
            log_dir=app_state.log_dir,
            file_result_repository=app_state.file_result_repository,
        )
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

    trigger_type = FileTaskTriggerType.MANUAL
    if body.trigger_type:
        try:
            trigger_type = FileTaskTriggerType(body.trigger_type)
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


@router.get("/{task_id}", response_model=FileTaskStatusResponse)
async def get_task_status(
    task_id: str,
    request: Request,
) -> FileTaskStatusResponse:
    """查询任务状态

    Args:
        task_id: 任务ID（字符串，需要转换为整数）
        request: HTTP请求对象

    Returns:
        任务状态响应

    Raises:
        HTTPException: 如果任务不存在或 task_id 格式无效
    """
    app_state: AppState = request.state.app_state
    task_id_int = _parse_task_id(task_id)
    task_model = app_state.task_manager.get_task(task_id_int)

    total_items = None
    if task_model.status in (FileTaskStatus.COMPLETED, FileTaskStatus.RUNNING):
        stats = app_state.file_result_repository.get_statistics(task_id_int)
        total_items = stats.get("total_items")

    return FileTaskStatusResponse(
        task_id=task_id_int,
        task_name=task_model.task_name,
        status=task_model.status,
        start_time=task_model.start_time,
        end_time=task_model.end_time,
        error_message=task_model.error_message,
        total_items=total_items,
    )


@router.post("/{task_id}/cancel", response_model=CancelFileTaskResponse)
async def cancel_task(
    task_id: str,
    request: Request,
) -> CancelFileTaskResponse:
    """取消任务

    Args:
        task_id: 任务ID（字符串，需要转换为整数）
        request: HTTP请求对象

    Returns:
        取消任务响应

    Raises:
        HTTPException: 如果任务不存在或 task_id 格式无效
    """
    app_state: AppState = request.state.app_state
    task_id_int = _parse_task_id(task_id)
    # FileTaskCancelledError 会被 app.py 中的异常处理器自动处理
    app_state.task_manager.cancel_task(task_id_int)
    return CancelFileTaskResponse(
        task_id=task_id_int,
        message="任务已取消",
    )


@router.get("", response_model=FileTaskListResponse)
async def list_tasks(
    request: Request,
) -> FileTaskListResponse:
    """列出所有任务

    Args:
        request: HTTP请求对象

    Returns:
        任务列表响应
    """
    app_state: AppState = request.state.app_state
    tasks = app_state.task_manager.list_tasks()
    task_items = [
        FileTaskListItem(
            task_id=task.task_id,
            task_name=task.task_name,
            status=task.status,
            start_time=task.start_time,
            end_time=task.end_time,
        )
        for task in tasks
    ]
    return FileTaskListResponse(tasks=task_items)
