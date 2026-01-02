"""FastAPI应用

创建和配置FastAPI应用实例，提供HTTP API接口。
包含应用生命周期管理和异常处理。
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from j_file_kit.app.app_config.api import router as config_router
from j_file_kit.app.file_task.api import router as file_task_router
from j_file_kit.app.task.api import router as task_router
from j_file_kit.infrastructure.app_state import AppState
from j_file_kit.infrastructure.logging.logging_setup import setup_logging
from j_file_kit.shared.models.exceptions import (
    TaskAlreadyRunningError,
    TaskCancelledError,
    TaskError,
    TaskNotFoundError,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """应用生命周期管理

    Args:
        app: FastAPI应用实例
    """
    # 启动时初始化日志系统
    setup_logging()

    # 启动时初始化应用状态
    app.state.app_state = AppState()

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


# 注册路由
app.include_router(task_router)
app.include_router(file_task_router)
app.include_router(config_router)
