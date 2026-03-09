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

from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.api import router as file_task_router
from j_file_kit.app.file_task.application.config import (
    create_default_jav_video_organizer_task_config,
)
from j_file_kit.app.file_task.config_api import router as file_task_config_router
from j_file_kit.app.file_task.domain.models import (
    FileTaskAlreadyRunningError,
    FileTaskCancelledError,
    FileTaskError,
    FileTaskNotFoundError,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.schema import (
    SQLiteSchemaInitializer,
)
from j_file_kit.infrastructure.persistence.yaml.default_task_config_initializer import (
    DefaultTaskConfigInitializer,
)
from j_file_kit.shared.utils.file_utils import ensure_directory
from j_file_kit.shared.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """应用生命周期管理

    Args:
        app: FastAPI应用实例
    """
    setup_logging()

    base_dir = Path(os.getenv("J_FILE_KIT_BASE_DIR", ".app-data"))
    sqlite_dir = base_dir / "sqlite"
    log_dir = base_dir / "logs"
    config_dir = base_dir / "config"
    ensure_directory(sqlite_dir, parents=True)
    ensure_directory(log_dir, parents=True)
    ensure_directory(config_dir, parents=True)

    # SQLite：仅用于任务执行记录
    conn_manager = SQLiteConnectionManager(sqlite_dir / "j_file_kit.db")
    SQLiteSchemaInitializer(conn_manager).initialize()

    # YAML：任务配置
    config_path = config_dir / "task_config.yaml"
    DefaultTaskConfigInitializer(
        config_path,
        default_task_configs=[create_default_jav_video_organizer_task_config()],
    ).initialize()

    app.state.app_state = AppState(
        base_dir=base_dir,
        sqlite_conn=conn_manager,
        config_path=config_path,
    )

    yield


app = FastAPI(
    title="j-file-kit API",
    description="文件管理工具HTTP API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(FileTaskNotFoundError)
async def file_task_not_found_handler(
    request: Request,
    exc: FileTaskNotFoundError,
) -> JSONResponse:
    """任务不存在异常处理器"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"code": "TASK_NOT_FOUND", "message": str(exc)},
    )


@app.exception_handler(FileTaskAlreadyRunningError)
async def file_task_already_running_handler(
    request: Request,
    exc: FileTaskAlreadyRunningError,
) -> JSONResponse:
    """任务已在运行异常处理器"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"code": "TASK_ALREADY_RUNNING", "message": str(exc)},
    )


@app.exception_handler(FileTaskCancelledError)
async def file_task_cancelled_handler(
    request: Request,
    exc: FileTaskCancelledError,
) -> JSONResponse:
    """任务已取消异常处理器"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": "TASK_CANCELLED", "message": str(exc)},
    )


@app.exception_handler(FileTaskError)
async def file_task_error_handler(
    request: Request,
    exc: FileTaskError,
) -> JSONResponse:
    """文件任务相关异常处理器（兜底）"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": "TASK_ERROR", "message": str(exc)},
    )


# 注册路由
app.include_router(file_task_router)
app.include_router(file_task_config_router)
