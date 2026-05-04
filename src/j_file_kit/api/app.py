"""FastAPI应用

创建和配置FastAPI应用实例，提供HTTP API接口。
包含应用生命周期管理和异常处理。
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.api import router as file_task_router
from j_file_kit.app.file_task.application.config import (
    create_default_jav_video_organizer_task_config,
)
from j_file_kit.app.file_task.application.file_task_config_service import (
    FileTaskConfigService,
)
from j_file_kit.app.file_task.config_api import router as file_task_config_router
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import (
    FileTaskAlreadyRunningError,
    FileTaskCancelledError,
    FileTaskError,
    FileTaskNotFoundError,
)
from j_file_kit.app.media_browser.api import router as media_browser_router
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.schema import (
    SQLiteSchemaInitializer,
)
from j_file_kit.infrastructure.persistence.yaml.default_file_task_config_initializer import (
    DefaultFileTaskConfigInitializer,
)
from j_file_kit.shared.constants import MEDIA_ROOT
from j_file_kit.shared.utils.file_utils import ensure_directory
from j_file_kit.shared.utils.logging import setup_logging

_APP_VERSION = os.getenv("APP_VERSION", "dev")


def create_app(base_dir: Path | None = None) -> FastAPI:
    """创建 FastAPI 应用实例

    设计意图：工厂函数支持测试注入 base_dir，生产环境通过环境变量读取。

    Args:
        base_dir: 应用基础目录。为 None 时使用 J_FILE_KIT_BASE_DIR 环境变量，默认 app-data

    Returns:
        配置完成的 FastAPI 实例
    """
    resolved_base_dir = (
        base_dir
        if base_dir is not None
        else Path(os.getenv("J_FILE_KIT_BASE_DIR", "/data"))
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        """应用生命周期管理"""
        setup_logging()
        logger.info("j-file-kit starting, version={}", _APP_VERSION)

        if os.getenv("J_FILE_KIT_ENV") == "production" and not os.path.ismount(
            str(MEDIA_ROOT),
        ):
            raise RuntimeError(
                f"{MEDIA_ROOT} 未挂载宿主机路径。"
                "请在 Docker 配置中将宿主媒体目录映射到容器内 /media ，"
                "例如：-v /host/media:/media（JAV 任务使用 /media/jav/ 等业务子路径）",
            )

        sqlite_dir = resolved_base_dir / "sqlite"
        log_dir = resolved_base_dir / "logs"
        config_dir = resolved_base_dir / "config"
        ensure_directory(sqlite_dir, parents=True)
        ensure_directory(log_dir, parents=True)
        ensure_directory(config_dir, parents=True)

        conn_manager = SQLiteConnectionManager(sqlite_dir / "j_file_kit.db")
        SQLiteSchemaInitializer(conn_manager).initialize()

        config_path = config_dir / "task_config.yaml"
        DefaultFileTaskConfigInitializer(
            config_path,
            default_task_configs=[create_default_jav_video_organizer_task_config()],
        ).initialize()

        app.state.app_state = AppState(
            base_dir=resolved_base_dir,
            sqlite_conn=conn_manager,
            config_path=config_path,
        )

        repo = app.state.app_state.file_task_config_repository
        if repo.get_by_type(TASK_TYPE_JAV_VIDEO_ORGANIZER) is not None:
            try:
                FileTaskConfigService.get_jav_video_organizer_config(repo)
            except ValueError as e:
                raise RuntimeError(f"启动时配置校验失败，请检查配置文件：{e}") from e

        yield

    fastapi_app = FastAPI(
        title="j-file-kit API",
        description="文件管理工具HTTP API",
        version=_APP_VERSION,
        lifespan=lifespan,
    )

    @fastapi_app.exception_handler(FileTaskNotFoundError)
    async def file_task_not_found_handler(
        request: Request,
        exc: FileTaskNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"code": "TASK_NOT_FOUND", "message": str(exc)},
        )

    @fastapi_app.exception_handler(FileTaskAlreadyRunningError)
    async def file_task_already_running_handler(
        request: Request,
        exc: FileTaskAlreadyRunningError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "TASK_ALREADY_RUNNING", "message": str(exc)},
        )

    @fastapi_app.exception_handler(FileTaskCancelledError)
    async def file_task_cancelled_handler(
        request: Request,
        exc: FileTaskCancelledError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"code": "TASK_CANCELLED", "message": str(exc)},
        )

    @fastapi_app.exception_handler(FileTaskError)
    async def file_task_error_handler(
        request: Request,
        exc: FileTaskError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": "TASK_ERROR", "message": str(exc)},
        )

    @fastapi_app.get("/health", tags=["infra"])
    async def health_check() -> dict[str, str]:
        """健康检查端点，供 Docker HEALTHCHECK 和容器编排系统使用。"""
        return {"status": "ok", "version": _APP_VERSION}

    fastapi_app.include_router(file_task_router)
    fastapi_app.include_router(file_task_config_router)
    fastapi_app.include_router(media_browser_router)

    return fastapi_app


app = create_app()
