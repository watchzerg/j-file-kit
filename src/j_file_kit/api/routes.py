"""API路由

定义任务管理的HTTP API路由处理函数。
提供任务的启动、查询、取消等功能。
"""

from fastapi import APIRouter, HTTPException, Request, status

from j_file_kit.infrastructure.app_state import AppState
from j_file_kit.infrastructure.persistence.sqlite.file_item_repository import (
    FileItemRepositoryImpl,
)
from j_file_kit.interfaces.task import BaseTask
from j_file_kit.models.task import TaskStatus, TaskType, TriggerType
from j_file_kit.services.tasks.file.jav_video_organizer import JavVideoOrganizer

from .models import (
    CancelTaskResponse,
    StartTaskRequest,
    StartTaskResponse,
    TaskListItem,
    TaskListResponse,
    TaskStatusResponse,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def parse_task_id(task_id_str: str) -> int:
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


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    request: Request,
) -> TaskStatusResponse:
    """获取任务状态

    Args:
        task_id: 任务ID（字符串，需要转换为整数）
        request: HTTP请求对象

    Returns:
        任务状态响应

    Raises:
        HTTPException: 如果任务不存在或 task_id 格式无效
    """
    app_state: AppState = request.state.app_state
    task_id_int = parse_task_id(task_id)
    task_model = app_state.task_manager.get_task(task_id_int)

    # 从数据库查询 total_items
    total_items = None
    if task_model.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING):
        file_item_repository = FileItemRepositoryImpl(
            app_state.sqlite_conn,
            task_id_int,
        )
        stats = file_item_repository.get_statistics()
        # 如果统计信息存在，返回 total_items（0 也是有效值）
        total_items = stats.get("total_items")

    return TaskStatusResponse(
        task_id=task_id_int,
        task_name=task_model.task_name,
        status=task_model.status,
        start_time=task_model.start_time,
        end_time=task_model.end_time,
        error_message=task_model.error_message,
        total_items=total_items,
    )


@router.post("/{task_id}/cancel", response_model=CancelTaskResponse)
async def cancel_task(
    task_id: str,
    request: Request,
) -> CancelTaskResponse:
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
    task_id_int = parse_task_id(task_id)
    # TaskCancelledError 会被 app.py 中的异常处理器自动处理
    app_state.task_manager.cancel_task(task_id_int)
    return CancelTaskResponse(
        task_id=task_id_int,
        message="任务已取消",
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    request: Request,
) -> TaskListResponse:
    """列出所有任务

    Args:
        request: HTTP请求对象

    Returns:
        任务列表响应
    """
    app_state: AppState = request.state.app_state
    tasks = app_state.task_manager.list_tasks()
    task_items = [
        TaskListItem(
            task_id=task.task_id,
            task_name=task.task_name,
            status=task.status,
            start_time=task.start_time,
            end_time=task.end_time,
        )
        for task in tasks
    ]
    return TaskListResponse(tasks=task_items)
