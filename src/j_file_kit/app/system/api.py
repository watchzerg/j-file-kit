"""System metadata API routes."""

import os

from fastapi import APIRouter, Request

import j_file_kit.app.file_task.application.config_common as config_common
from j_file_kit.api.app_state import AppState
from j_file_kit.app.system.schemas import SystemInfoResponse
from j_file_kit.shared.constants import MEDIA_ROOT

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info(request: Request) -> SystemInfoResponse:
    """Return runtime metadata needed by the frontend configuration center."""
    app_state: AppState = request.app.state.app_state
    return SystemInfoResponse(
        app_version=request.app.version,
        env=os.getenv("J_FILE_KIT_ENV", "development"),
        base_dir=str(app_state.base_dir),
        media_root=str(MEDIA_ROOT),
        jav_media_root=str(config_common.JAV_MEDIA_ROOT),
        raw_media_root=str(config_common.RAW_MEDIA_ROOT),
        media_mounted=os.path.ismount(MEDIA_ROOT),
    )
