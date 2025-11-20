"""配置API路由

定义配置管理的HTTP API路由处理函数。
提供配置的查询和更新功能，支持部分更新。
"""

from fastapi import APIRouter, HTTPException, Request, status

from ..infrastructure.app_state import AppState
from ..models.config import AppConfig
from ..services.config_service import ConfigService
from .models import (
    UpdateConfigRequest,
    UpdateConfigResponse,
)

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=AppConfig)
async def get_config(request: Request) -> AppConfig:
    """获取当前配置

    Args:
        request: HTTP请求对象

    Returns:
        当前应用配置对象
    """
    app_state: AppState = request.state.app_state
    config: AppConfig = app_state.config
    return config


@router.patch("", response_model=UpdateConfigResponse)
async def update_config(
    body: UpdateConfigRequest,
    request: Request,
) -> UpdateConfigResponse:
    """更新配置（部分更新）

    Args:
        body: 更新配置请求
        request: HTTP请求对象

    Returns:
        更新配置响应

    Raises:
        HTTPException: 如果配置更新失败或路径验证失败
    """
    app_state: AppState = request.state.app_state
    current_config = app_state.config

    # 合并全局配置
    if body.global_ is not None:
        try:
            merged_global = ConfigService.merge_global_config(
                current_config.global_, body.global_
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_GLOBAL_CONFIG", "message": str(e)},
            ) from e
    else:
        merged_global = current_config.global_

    # 合并任务配置
    merged_tasks = (
        ConfigService.merge_all_task_configs(current_config.tasks, body.tasks)
        if body.tasks is not None
        else current_config.tasks.copy()
    )

    # 验证并保存配置
    ConfigService.validate_and_save_config(merged_global, merged_tasks, app_state)

    return UpdateConfigResponse(
        message="配置更新成功",
        code="SUCCESS",
    )
