"""配置API路由

定义配置管理的HTTP API路由处理函数。
提供配置的查询和更新功能，支持部分更新。
"""

from fastapi import APIRouter, HTTPException, Request, status

from j_file_kit.api.app_state import AppState
from j_file_kit.app.config.application.config_service import ConfigService
from j_file_kit.app.config.application.schemas import (
    UpdateConfigResponse,
    UpdateGlobalConfigRequest,
    UpdateTaskConfigsRequest,
)
from j_file_kit.app.config.domain.models import GlobalConfig, TaskConfig

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/global", response_model=GlobalConfig)
async def get_global_config(request: Request) -> GlobalConfig:
    """获取当前全局配置"""
    app_state: AppState = request.state.app_state
    return app_state.get_global_config()


@router.patch("/global", response_model=UpdateConfigResponse)
async def update_global_config(
    body: UpdateGlobalConfigRequest,
    request: Request,
) -> UpdateConfigResponse:
    """更新全局配置（部分更新）"""
    app_state: AppState = request.state.app_state
    current_global = app_state.get_global_config()

    try:
        merged_global = ConfigService.merge_global_config(current_global, body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_GLOBAL_CONFIG", "message": str(e)},
        ) from e

    ConfigService.validate_and_save_global_config(
        merged_global,
        app_state.global_config_repository,
        app_state.config_manager,
    )

    return UpdateConfigResponse(message="全局配置更新成功", code="SUCCESS")


@router.get("/tasks", response_model=list[TaskConfig])
async def get_task_configs(request: Request) -> list[TaskConfig]:
    """获取当前任务配置列表"""
    app_state: AppState = request.state.app_state
    return app_state.get_task_configs()


@router.patch("/tasks", response_model=UpdateConfigResponse)
async def update_task_configs(
    body: UpdateTaskConfigsRequest,
    request: Request,
) -> UpdateConfigResponse:
    """更新任务配置（批量部分更新）"""
    app_state: AppState = request.state.app_state
    current_tasks = app_state.get_task_configs()

    merged_tasks = ConfigService.merge_all_task_configs(current_tasks, body.tasks)

    ConfigService.validate_and_save_task_configs(
        merged_tasks,
        app_state.task_config_repository,
        app_state.config_manager,
    )

    return UpdateConfigResponse(message="任务配置更新成功", code="SUCCESS")
