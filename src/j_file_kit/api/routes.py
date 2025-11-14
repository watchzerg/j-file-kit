"""API路由

定义任务管理的HTTP API路由处理函数。
提供任务的启动、查询、取消等功能。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from ..domain.task import BaseTask
from ..infrastructure.app_state import AppState
from ..tasks.video_organizer import VideoFileOrganizer
from .models import (
    CancelTaskResponse,
    StartTaskRequest,
    StartTaskResponse,
    TaskListItem,
    TaskListResponse,
    TaskStatusResponse,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def get_task_instance(task_name: str, app_state: AppState) -> BaseTask:
    """获取任务实例

    Args:
        task_name: 任务名称
        app_state: 应用状态

    Returns:
        任务实例

    Raises:
        HTTPException: 如果任务不存在
    """
    if task_name == "video_file_organizer":
        return VideoFileOrganizer(app_state.config)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_name}",
        )


@router.post("/{task_name}/start", response_model=StartTaskResponse)
async def start_task(
    task_name: str,
    body: StartTaskRequest,
    request: Request,
) -> StartTaskResponse:
    """启动任务

    Args:
        task_name: 任务名称
        body: 启动任务请求
        request: HTTP请求对象

    Returns:
        启动任务响应

    Raises:
        HTTPException: 如果任务不存在或已有任务正在运行
    """
    app_state: AppState = request.state.app_state
    task = get_task_instance(task_name, app_state)
    task_id = app_state.task_manager.start_task(task, dry_run=body.dry_run)
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
        task_id: 任务ID
        request: HTTP请求对象

    Returns:
        任务状态响应

    Raises:
        HTTPException: 如果任务不存在
    """
    app_state: AppState = request.state.app_state
    task_model = app_state.task_manager.get_task(task_id)
    total_files = None
    if task_model.report:
        total_files = task_model.report.total_files

    return TaskStatusResponse(
        task_id=task_model.task_id,
        task_name=task_model.task_name,
        status=task_model.status,
        start_time=task_model.start_time,
        end_time=task_model.end_time,
        error_message=task_model.error_message,
        total_files=total_files,
    )


@router.post("/{task_id}/cancel", response_model=CancelTaskResponse)
async def cancel_task(
    task_id: str,
    request: Request,
) -> CancelTaskResponse:
    """取消任务

    Args:
        task_id: 任务ID
        request: HTTP请求对象

    Returns:
        取消任务响应

    Raises:
        HTTPException: 如果任务不存在
    """
    app_state: AppState = request.state.app_state
    # TaskCancelledError 会被 app.py 中的异常处理器自动处理
    app_state.task_manager.cancel_task(task_id)
    return CancelTaskResponse(
        task_id=task_id,
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
