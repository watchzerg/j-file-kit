"""全局配置 API 路由

定义全局配置管理的 HTTP API 路由处理函数。
提供配置的查询和更新功能，支持部分更新。
"""

from fastapi import APIRouter, HTTPException, Request, status

from j_file_kit.api.app_state import AppState
from j_file_kit.app.global_config.application.global_config_service import (
    GlobalConfigService,
)
from j_file_kit.app.global_config.application.schemas import (
    UpdateConfigResponse,
    UpdateGlobalConfigRequest,
)
from j_file_kit.app.global_config.domain.models import GlobalConfig

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
        merged_global = GlobalConfigService.merge_global_config(current_global, body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_GLOBAL_CONFIG", "message": str(e)},
        ) from e

    GlobalConfigService.validate_and_save_global_config(
        merged_global,
        app_state.global_config_repository,
    )

    return UpdateConfigResponse(message="全局配置更新成功", code="SUCCESS")
