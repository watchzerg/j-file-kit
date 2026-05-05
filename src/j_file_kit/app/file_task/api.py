"""文件任务 API 路由

定义文件任务相关的全部 HTTP API 路由处理函数：
- POST /{task_type}/start：启动任务执行实例
- GET /{run_id}：查询执行实例状态
- POST /{run_id}/cancel：取消执行实例
- GET /：列出所有执行实例
"""

from fastapi import APIRouter, HTTPException, Request, status

from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.application.jav_video_organizer import JavVideoOrganizer
from j_file_kit.app.file_task.application.raw_file_organizer import RawFileOrganizer
from j_file_kit.app.file_task.application.schemas import (
    CancelFileTaskRunResponse,
    FileTaskRunListItem,
    FileTaskRunListResponse,
    FileTaskRunStatusResponse,
    StartTaskRequest,
    StartTaskResponse,
)
from j_file_kit.app.file_task.domain.constants import (
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
)
from j_file_kit.app.file_task.domain.task_config import TaskConfig
from j_file_kit.app.file_task.domain.task_run import (
    FileTaskRunStatus,
    FileTaskTriggerType,
)
from j_file_kit.app.file_task.domain.task_runner import FileTaskRunner

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _parse_run_id(run_id_str: str) -> int:
    """解析执行实例ID字符串为整数

    Args:
        run_id_str: 执行实例ID字符串

    Returns:
        执行实例ID整数

    Raises:
        HTTPException: 如果 run_id 格式无效
    """
    try:
        return int(run_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的执行实例ID格式: {run_id_str}",
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
    task_config = app_state.file_task_config_repository.get_by_type(task_type)
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
    if task_type == TASK_TYPE_RAW_FILE_ORGANIZER:
        return RawFileOrganizer(
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
    """启动任务执行实例

    Args:
        task_type: 任务类型
        body: 启动任务请求
        request: HTTP请求对象

    Returns:
        启动任务响应

    Raises:
        HTTPException: 如果任务不存在或已有执行实例正在运行
    """
    app_state: AppState = request.app.state.app_state
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

    run_id = app_state.file_task_run_manager.start_run(
        task,
        trigger_type=trigger_type,
        dry_run=body.dry_run,
    )
    run = app_state.file_task_run_manager.get_run(run_id)

    return StartTaskResponse(
        run_id=run_id,
        run_name=run.run_name,
        status=run.status,
    )


@router.get("/{run_id}", response_model=FileTaskRunStatusResponse)
async def get_run_status(
    run_id: str,
    request: Request,
) -> FileTaskRunStatusResponse:
    """查询执行实例状态

    Args:
        run_id: 执行实例ID（字符串，需要转换为整数）
        request: HTTP请求对象

    Returns:
        执行实例状态响应

    Raises:
        HTTPException: 如果执行实例不存在或 run_id 格式无效
    """
    app_state: AppState = request.app.state.app_state
    run_id_int = _parse_run_id(run_id)
    run = app_state.file_task_run_manager.get_run(run_id_int)

    total_items = None
    if run.status in (FileTaskRunStatus.COMPLETED, FileTaskRunStatus.RUNNING):
        stats = app_state.file_result_repository.get_statistics(run_id_int)
        total_items = stats.get("total_items")

    return FileTaskRunStatusResponse(
        run_id=run_id_int,
        run_name=run.run_name,
        status=run.status,
        start_time=run.start_time,
        end_time=run.end_time,
        error_message=run.error_message,
        total_items=total_items,
    )


@router.post("/{run_id}/cancel", response_model=CancelFileTaskRunResponse)
async def cancel_run(
    run_id: str,
    request: Request,
) -> CancelFileTaskRunResponse:
    """取消执行实例

    Args:
        run_id: 执行实例ID（字符串，需要转换为整数）
        request: HTTP请求对象

    Returns:
        取消执行实例响应

    Raises:
        HTTPException: 如果执行实例不存在或 run_id 格式无效
    """
    app_state: AppState = request.app.state.app_state
    run_id_int = _parse_run_id(run_id)
    app_state.file_task_run_manager.cancel_run(run_id_int)
    return CancelFileTaskRunResponse(
        run_id=run_id_int,
        message="任务已取消",
    )


@router.get("", response_model=FileTaskRunListResponse)
async def list_runs(
    request: Request,
) -> FileTaskRunListResponse:
    """列出所有执行实例

    Args:
        request: HTTP请求对象

    Returns:
        执行实例列表响应
    """
    app_state: AppState = request.app.state.app_state
    runs = app_state.file_task_run_manager.list_runs()
    run_items = [
        FileTaskRunListItem(
            run_id=run.run_id,
            run_name=run.run_name,
            status=run.status,
            start_time=run.start_time,
            end_time=run.end_time,
        )
        for run in runs
    ]
    return FileTaskRunListResponse(runs=run_items)
