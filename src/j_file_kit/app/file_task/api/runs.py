"""Run 生命周期路由：启动、查询、取消、删除、列表。"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, status

from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.api._helpers import _parse_run_id, _task_log_file_path
from j_file_kit.app.file_task.application.jav_video_organizer import JavVideoOrganizer
from j_file_kit.app.file_task.application.raw_file_organizer import RawFileOrganizer
from j_file_kit.app.file_task.application.schemas import (
    ActiveFileTaskRunResponse,
    CancelFileTaskRunResponse,
    DeleteFileTaskRunResponse,
    FileTaskRunListItem,
    FileTaskRunListResponse,
    FileTaskRunStatisticsSummary,
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
    FileTaskRun,
    FileTaskRunStatistics,
    FileTaskRunStatus,
    FileTaskTriggerType,
)
from j_file_kit.app.file_task.domain.task_runner import FileTaskRunner
from j_file_kit.shared.utils.file_utils import delete_file_if_exists

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

VALID_TASK_TYPES = {
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
}

TERMINAL_STATUSES = {
    FileTaskRunStatus.COMPLETED,
    FileTaskRunStatus.FAILED,
    FileTaskRunStatus.CANCELLED,
}


def _get_task_config(task_type: str, app_state: AppState) -> TaskConfig:
    task_config = app_state.file_task_config_repository.get_by_type(task_type)
    if task_config is not None:
        return task_config
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"任务配置不存在: {task_type}",
    )


def _new_task_instance(task_type: str, app_state: AppState) -> FileTaskRunner:
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


def _duration_ms(run: FileTaskRun) -> float:
    end_time = run.end_time or datetime.now()
    return max(0.0, (end_time - run.start_time).total_seconds() * 1000)


def _statistics_for_run(run: FileTaskRun, app_state: AppState) -> FileTaskRunStatistics:
    if run.statistics is not None:
        return run.statistics
    stats = app_state.file_result_repository.get_statistics(run.run_id)
    return FileTaskRunStatistics.model_validate(stats)


def _statistics_summary_for_run(
    run: FileTaskRun,
    app_state: AppState,
) -> FileTaskRunStatisticsSummary:
    statistics = _statistics_for_run(run, app_state)
    return FileTaskRunStatisticsSummary(
        total_items=statistics.total_items,
        success_items=statistics.success_items,
        error_items=statistics.error_items,
        skipped_items=statistics.skipped_items,
        warning_items=statistics.warning_items,
        total_duration_ms=statistics.total_duration_ms,
    )


def _parse_task_type_filter(task_type: str | None) -> str | None:
    if task_type is None:
        return None
    if task_type in VALID_TASK_TYPES:
        return task_type
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"无效的任务类型: {task_type}",
    )


def _parse_status_filter(status_value: str | None) -> FileTaskRunStatus | None:
    if status_value is None:
        return None
    try:
        return FileTaskRunStatus(status_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的执行状态: {status_value}",
        ) from None


@router.post("/{task_type}/start", response_model=StartTaskResponse)
async def start_task(
    task_type: str,
    body: StartTaskRequest,
    request: Request,
) -> StartTaskResponse:
    """启动任务执行实例。

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
        dry_run=run.dry_run,
    )


@router.get("/active", response_model=ActiveFileTaskRunResponse | None)
async def get_active_run(
    request: Request,
) -> ActiveFileTaskRunResponse | None:
    """查询当前待处理或运行中的执行实例。"""
    app_state: AppState = request.app.state.app_state
    run = app_state.file_task_run_manager.get_active_run()
    if run is None:
        return None

    return ActiveFileTaskRunResponse(
        run_id=run.run_id,
        run_name=run.run_name,
        task_type=run.task_type,
        trigger_type=run.trigger_type,
        status=run.status,
        start_time=run.start_time,
        end_time=run.end_time,
        error_message=run.error_message,
    )


@router.get("/{run_id}", response_model=FileTaskRunStatusResponse)
async def get_run_status(
    run_id: str,
    request: Request,
) -> FileTaskRunStatusResponse:
    """查询执行实例状态。

    Raises:
        HTTPException: 如果执行实例不存在或 run_id 格式无效
    """
    app_state: AppState = request.app.state.app_state
    run_id_int = _parse_run_id(run_id)
    run = app_state.file_task_run_manager.get_run(run_id_int)
    statistics = _statistics_for_run(run, app_state)

    return FileTaskRunStatusResponse(
        run_id=run_id_int,
        run_name=run.run_name,
        task_type=run.task_type,
        trigger_type=run.trigger_type,
        dry_run=run.dry_run,
        status=run.status,
        start_time=run.start_time,
        end_time=run.end_time,
        error_message=run.error_message,
        duration_ms=_duration_ms(run),
        statistics=statistics,
    )


@router.post("/{run_id}/cancel", response_model=CancelFileTaskRunResponse)
async def cancel_run(
    run_id: str,
    request: Request,
) -> CancelFileTaskRunResponse:
    """取消执行实例。

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


@router.delete("/{run_id}", response_model=DeleteFileTaskRunResponse)
async def delete_run(
    run_id: str,
    request: Request,
) -> DeleteFileTaskRunResponse:
    """删除已结束的执行实例及其文件结果与日志。"""
    app_state: AppState = request.app.state.app_state
    run_id_int = _parse_run_id(run_id)
    run = app_state.file_task_run_manager.get_run(run_id_int)
    if run.status not in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TASK_NOT_TERMINAL", "message": "只能删除已结束的任务"},
        )

    app_state.file_result_repository.delete_results(run_id_int)
    app_state.file_task_run_repository.delete_run(run_id_int)
    delete_file_if_exists(_task_log_file_path(app_state.log_dir, run))

    return DeleteFileTaskRunResponse(
        run_id=run_id_int,
        message="任务已删除",
    )


@router.get("", response_model=FileTaskRunListResponse)
async def list_runs(
    request: Request,
    task_type: str | None = Query(None),
    status_value: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> FileTaskRunListResponse:
    """列出所有执行实例。"""
    app_state: AppState = request.app.state.app_state
    parsed_task_type = _parse_task_type_filter(task_type)
    parsed_status = _parse_status_filter(status_value)
    offset = (page - 1) * page_size

    runs = app_state.file_task_run_manager.list_runs(
        task_type=parsed_task_type,
        status=parsed_status,
        limit=page_size,
        offset=offset,
    )
    total = app_state.file_task_run_manager.count_runs(
        task_type=parsed_task_type,
        status=parsed_status,
    )
    run_items = [
        FileTaskRunListItem(
            run_id=run.run_id,
            run_name=run.run_name,
            task_type=run.task_type,
            trigger_type=run.trigger_type,
            dry_run=run.dry_run,
            status=run.status,
            start_time=run.start_time,
            end_time=run.end_time,
            duration_ms=_duration_ms(run),
            statistics_summary=_statistics_summary_for_run(run, app_state),
        )
        for run in runs
    ]
    return FileTaskRunListResponse(
        runs=run_items,
        total=total,
        page=page,
        page_size=page_size,
    )
