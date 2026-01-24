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
from j_file_kit.app.config.api import router as config_router
from j_file_kit.app.config.domain.exceptions import (
    ConfigError,
    ConfigReloadError,
    ConfigUpdateError,
    InvalidConfigError,
    InvalidPathError,
    InvalidTaskConfigError,
    MissingTaskNameError,
    TaskConfigNotFoundError,
)
from j_file_kit.app.file_task.api import router as file_task_router
from j_file_kit.app.task.api import router as task_router
from j_file_kit.app.task.domain.models import (
    TaskAlreadyRunningError,
    TaskCancelledError,
    TaskError,
    TaskNotFoundError,
)
from j_file_kit.infrastructure.persistence.sqlite.config.default_config_initializer import (
    DefaultConfigInitializer,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.schema import (
    SQLiteSchemaInitializer,
)
from j_file_kit.shared.utils.file_utils import ensure_directory
from j_file_kit.shared.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """应用生命周期管理

    Args:
        app: FastAPI应用实例
    """
    # 启动流水线：1) 日志系统
    setup_logging()

    # 启动流水线：2) 环境与目录
    base_dir = Path(os.getenv("J_FILE_KIT_BASE_DIR", ".app-data"))
    sqlite_dir = base_dir / "sqlite"
    log_dir = base_dir / "logs"
    ensure_directory(sqlite_dir, parents=True)
    ensure_directory(log_dir, parents=True)

    # 启动流水线：3) 数据库连接与结构初始化
    conn_manager = SQLiteConnectionManager(sqlite_dir / "j_file_kit.db")
    SQLiteSchemaInitializer(conn_manager).initialize()
    DefaultConfigInitializer(conn_manager).initialize()

    # 启动流水线：4) 组装应用状态（Composition Root）
    app.state.app_state = AppState(base_dir=base_dir, sqlite_conn=conn_manager)

    yield

    # 关闭时清理资源（如果需要）


app = FastAPI(
    title="j-file-kit API",
    description="文件管理工具HTTP API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(
    request: Request,
    exc: TaskNotFoundError,
) -> JSONResponse:
    """任务不存在异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"code": "TASK_NOT_FOUND", "message": str(exc)},
    )


@app.exception_handler(TaskAlreadyRunningError)
async def task_already_running_handler(
    request: Request,
    exc: TaskAlreadyRunningError,
) -> JSONResponse:
    """任务已在运行异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"code": "TASK_ALREADY_RUNNING", "message": str(exc)},
    )


@app.exception_handler(TaskCancelledError)
async def task_cancelled_handler(
    request: Request,
    exc: TaskCancelledError,
) -> JSONResponse:
    """任务已取消异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": "TASK_CANCELLED", "message": str(exc)},
    )


@app.exception_handler(TaskError)
async def task_error_handler(request: Request, exc: TaskError) -> JSONResponse:
    """任务相关异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": "TASK_ERROR", "message": str(exc)},
    )


@app.exception_handler(MissingTaskNameError)
async def missing_task_name_handler(
    request: Request,
    exc: MissingTaskNameError,
) -> JSONResponse:
    """缺少任务名称异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": "MISSING_TASK_NAME", "message": str(exc)},
    )


@app.exception_handler(TaskConfigNotFoundError)
async def task_config_not_found_handler(
    request: Request,
    exc: TaskConfigNotFoundError,
) -> JSONResponse:
    """任务配置不存在异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"code": "TASK_CONFIG_NOT_FOUND", "message": str(exc)},
    )


@app.exception_handler(InvalidTaskConfigError)
async def invalid_task_config_handler(
    request: Request,
    exc: InvalidTaskConfigError,
) -> JSONResponse:
    """无效任务配置异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": "INVALID_TASK_CONFIG", "message": str(exc)},
    )


@app.exception_handler(InvalidConfigError)
async def invalid_config_handler(
    request: Request,
    exc: InvalidConfigError,
) -> JSONResponse:
    """无效配置异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": "INVALID_CONFIG", "message": str(exc)},
    )


@app.exception_handler(InvalidPathError)
async def invalid_path_handler(
    request: Request,
    exc: InvalidPathError,
) -> JSONResponse:
    """无效路径异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": "INVALID_PATH", "message": str(exc)},
    )


@app.exception_handler(ConfigUpdateError)
async def config_update_error_handler(
    request: Request,
    exc: ConfigUpdateError,
) -> JSONResponse:
    """配置更新失败异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": "CONFIG_UPDATE_FAILED", "message": str(exc)},
    )


@app.exception_handler(ConfigReloadError)
async def config_reload_error_handler(
    request: Request,
    exc: ConfigReloadError,
) -> JSONResponse:
    """配置重载失败异常处理器

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": "CONFIG_RELOAD_FAILED", "message": str(exc)},
    )


@app.exception_handler(ConfigError)
async def config_error_handler(request: Request, exc: ConfigError) -> JSONResponse:
    """配置相关异常处理器（兜底）

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": "CONFIG_ERROR", "message": str(exc)},
    )


# 注册路由
app.include_router(task_router)
app.include_router(file_task_router)
app.include_router(config_router)
