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
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER

router = APIRouter(prefix="/api/file-task/config", tags=["file-task-config"])


@router.get("/jav-video-organizer", response_model=GetFileTaskConfigResponse)
async def get_jav_video_organizer_config(request: Request) -> GetFileTaskConfigResponse:
    """获取 JAV 视频整理任务配置"""
    app_state: AppState = request.state.app_state

    task_config = app_state.config_manager.get_task_config_by_type(
        TASK_TYPE_JAV_VIDEO_ORGANIZER,
    )
    if task_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONFIG_NOT_FOUND", "message": "任务配置不存在"},
        )

    return GetFileTaskConfigResponse(
        name=task_config.name,
        enabled=task_config.enabled,
        config=task_config.config,
    )


@router.patch("/jav-video-organizer", response_model=UpdateFileTaskConfigResponse)
async def update_jav_video_organizer_config(
    body: UpdateFileTaskConfigRequest,
    request: Request,
) -> UpdateFileTaskConfigResponse:
    """更新 JAV 视频整理任务配置（部分更新）"""
    app_state: AppState = request.state.app_state

    try:
        current_typed_config = FileTaskConfigService.get_jav_video_organizer_config(
            app_state.config_manager,
        )

        if body.config is not None:
            merged_config = FileTaskConfigService.merge_jav_video_organizer_config(
                current_typed_config,
                body.config,
            )
        else:
            merged_config = current_typed_config

        task_config = app_state.config_manager.get_task_config_by_type(
            TASK_TYPE_JAV_VIDEO_ORGANIZER,
        )
        if task_config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CONFIG_NOT_FOUND", "message": "任务配置不存在"},
            )

        update_dict: dict[str, object] = {
            "config": merged_config.model_dump(exclude_none=True),
        }
        if body.enabled is not None:
            update_dict["enabled"] = body.enabled

        updated_task_config = task_config.model_copy(update=update_dict)

        app_state.task_config_repository.update(updated_task_config)
        app_state.config_manager.reload_task(TASK_TYPE_JAV_VIDEO_ORGANIZER)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CONFIG", "message": str(e)},
        ) from e

    return UpdateFileTaskConfigResponse(
        message="JAV 视频整理任务配置更新成功",
        code="SUCCESS",
    )
