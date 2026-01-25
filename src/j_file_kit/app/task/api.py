"""任务管理 API 路由

定义通用任务管理的 HTTP API 路由处理函数。
提供任务的查询、取消、列表等功能。
"""

from fastapi import APIRouter, HTTPException, Request, status

from j_file_kit.api.app_state import AppState
from j_file_kit.app.task.application.schemas import (
    CancelTaskResponse,
    TaskListItem,
    TaskListResponse,
    TaskStatusResponse,
)
from j_file_kit.app.task.domain.models import TaskStatus

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
        stats = app_state.file_result_repository.get_statistics(task_id_int)
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
