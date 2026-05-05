"""File task 配置 API 路由。

定义 file task 配置管理的 HTTP API 路由处理函数。
"""

from fastapi import APIRouter, HTTPException, Request, status

from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.application.config_schemas import (
    GetFileTaskConfigResponse,
    UpdateFileTaskConfigRequest,
    UpdateFileTaskConfigResponse,
)
from j_file_kit.app.file_task.application.file_task_config_service import (
    FileTaskConfigService,
)
from j_file_kit.app.file_task.domain.constants import (
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
)

router = APIRouter(prefix="/api/file-task/config", tags=["file-task-config"])


@router.get("/jav-video-organizer", response_model=GetFileTaskConfigResponse)
async def get_jav_video_organizer_config(request: Request) -> GetFileTaskConfigResponse:
    """获取 JAV 视频整理任务配置（仓储原始 dict；扩展名与站标去噪等见 `organizer_defaults`）。"""
    app_state: AppState = request.app.state.app_state

    task_config = app_state.file_task_config_repository.get_by_type(
        TASK_TYPE_JAV_VIDEO_ORGANIZER,
    )
    if task_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONFIG_NOT_FOUND", "message": "任务配置不存在"},
        )

    return GetFileTaskConfigResponse(
        type=task_config.type,
        enabled=task_config.enabled,
        config=task_config.config,
    )


@router.patch("/jav-video-organizer", response_model=UpdateFileTaskConfigResponse)
async def update_jav_video_organizer_config(
    body: UpdateFileTaskConfigRequest,
    request: Request,
) -> UpdateFileTaskConfigResponse:
    """更新 JAV 视频整理任务配置（部分更新）"""
    app_state: AppState = request.app.state.app_state

    task_config = app_state.file_task_config_repository.get_by_type(
        TASK_TYPE_JAV_VIDEO_ORGANIZER,
    )
    if task_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONFIG_NOT_FOUND", "message": "任务配置不存在"},
        )

    try:
        merged_config = FileTaskConfigService.merge_jav_video_organizer_config(
            task_config.config,
            body.config or {},
        )
        FileTaskConfigService.validate_and_save_jav_video_organizer_config(
            merged_config,
            app_state.file_task_config_repository,
            enabled=body.enabled,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CONFIG", "message": str(e)},
        ) from e

    return UpdateFileTaskConfigResponse(
        message="JAV 视频整理任务配置更新成功",
        code="SUCCESS",
    )


@router.get("/raw-file-organizer", response_model=GetFileTaskConfigResponse)
async def get_raw_file_organizer_config(request: Request) -> GetFileTaskConfigResponse:
    """获取 Raw 收件箱整理任务配置（仓储原始 dict）。"""
    app_state: AppState = request.app.state.app_state

    task_config = app_state.file_task_config_repository.get_by_type(
        TASK_TYPE_RAW_FILE_ORGANIZER,
    )
    if task_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONFIG_NOT_FOUND", "message": "任务配置不存在"},
        )

    return GetFileTaskConfigResponse(
        type=task_config.type,
        enabled=task_config.enabled,
        config=task_config.config,
    )


@router.patch("/raw-file-organizer", response_model=UpdateFileTaskConfigResponse)
async def update_raw_file_organizer_config(
    body: UpdateFileTaskConfigRequest,
    request: Request,
) -> UpdateFileTaskConfigResponse:
    """更新 Raw 收件箱整理任务配置（部分更新）。"""
    app_state: AppState = request.app.state.app_state

    task_config = app_state.file_task_config_repository.get_by_type(
        TASK_TYPE_RAW_FILE_ORGANIZER,
    )
    if task_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONFIG_NOT_FOUND", "message": "任务配置不存在"},
        )

    try:
        merged_config = FileTaskConfigService.merge_raw_file_organizer_config(
            task_config.config,
            body.config or {},
        )
        FileTaskConfigService.validate_and_save_raw_file_organizer_config(
            merged_config,
            app_state.file_task_config_repository,
            enabled=body.enabled,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CONFIG", "message": str(e)},
        ) from e

    return UpdateFileTaskConfigResponse(
        message="Raw 收件箱整理任务配置更新成功",
        code="SUCCESS",
    )
