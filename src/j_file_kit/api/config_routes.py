"""配置API路由

定义配置管理的HTTP API路由处理函数。
提供配置的查询和更新功能，支持部分更新。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from ..infrastructure.app_state import AppState
from ..infrastructure.config.config import (
    GlobalConfig,
    TaskConfig,
    TaskDefinition,
    ensure_directories_exist,
    save_config,
)
from .models import (
    UpdateConfigRequest,
    UpdateConfigResponse,
    UpdateGlobalConfigRequest,
    UpdateTaskConfigRequest,
)

router = APIRouter(prefix="/api/config", tags=["config"])


def _merge_global_config(
    current: GlobalConfig, update: UpdateGlobalConfigRequest
) -> GlobalConfig:
    """合并全局配置更新

    Args:
        current: 当前全局配置
        update: 更新请求

    Returns:
        合并后的全局配置
    """
    update_dict: dict[str, Any] = {}
    if update.scan_roots is not None:
        update_dict["scan_roots"] = [Path(p) for p in update.scan_roots]
    if update.log_dir is not None:
        update_dict["log_dir"] = Path(update.log_dir)
    if update.report_dir is not None:
        update_dict["report_dir"] = Path(update.report_dir)

    if not update_dict:
        return current

    return current.model_copy(update=update_dict)


def _merge_task_config_dict(
    current: dict[str, Any], update: dict[str, Any]
) -> dict[str, Any]:
    """合并任务配置字典更新

    Args:
        current: 当前任务配置字典
        update: 更新字典

    Returns:
        合并后的任务配置字典
    """
    if not update:
        return current

    merged = current.copy()
    merged.update(update)
    return merged


def _merge_task_config(
    current: TaskDefinition, update: UpdateTaskConfigRequest
) -> TaskDefinition:
    """合并任务配置更新

    Args:
        current: 当前任务定义
        update: 更新请求

    Returns:
        合并后的任务定义
    """
    update_dict: dict[str, Any] = {}
    if update.name is not None:
        update_dict["name"] = update.name
    if update.enabled is not None:
        update_dict["enabled"] = update.enabled
    if update.config is not None:
        merged_config = _merge_task_config_dict(current.config, update.config)
        update_dict["config"] = merged_config

    if not update_dict:
        return current

    return current.model_copy(update=update_dict)


def _merge_all_task_configs(
    current_tasks: list[TaskDefinition], task_updates: list[UpdateTaskConfigRequest]
) -> list[TaskDefinition]:
    """合并所有任务配置更新

    Args:
        current_tasks: 当前任务列表
        task_updates: 任务更新请求列表

    Returns:
        合并后的任务列表

    Raises:
        HTTPException: 如果任务更新失败
    """
    merged_tasks = current_tasks.copy()
    for task_update in task_updates:
        if task_update.name is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "MISSING_TASK_NAME",
                    "message": "更新任务配置时必须提供任务名称",
                },
            )

        task_index = None
        for i, task in enumerate(merged_tasks):
            if task.name == task_update.name:
                task_index = i
                break

        if task_index is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TASK_NOT_FOUND",
                    "message": f"任务不存在: {task_update.name}",
                },
            )

        try:
            merged_task = _merge_task_config(merged_tasks[task_index], task_update)
            merged_tasks[task_index] = merged_task
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_TASK_CONFIG",
                    "message": f"更新任务 '{task_update.name}' 配置失败: {str(e)}",
                },
            ) from e

    return merged_tasks


def _validate_and_save_config(
    merged_global: GlobalConfig,
    merged_tasks: list[TaskDefinition],
    app_state: AppState,
) -> None:
    """验证并保存配置

    Args:
        merged_global: 合并后的全局配置
        merged_tasks: 合并后的任务列表
        app_state: 应用状态

    Raises:
        HTTPException: 如果配置验证或保存失败
    """
    try:
        new_config = TaskConfig.model_validate(
            {"global": merged_global, "tasks": merged_tasks}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CONFIG", "message": f"配置验证失败: {str(e)}"},
        ) from e

    try:
        ensure_directories_exist(new_config)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "DIRECTORY_CREATION_FAILED", "message": str(e)},
        ) from e

    try:
        save_config(new_config, app_state._config_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CONFIG_SAVE_FAILED", "message": f"保存配置失败: {str(e)}"},
        ) from e

    try:
        app_state.reload_config()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "CONFIG_RELOAD_FAILED",
                "message": f"重新加载配置失败: {str(e)}",
            },
        ) from e


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
        HTTPException: 如果配置更新失败或目录创建失败
    """
    app_state: AppState = request.state.app_state
    current_config = app_state.config

    # 合并全局配置
    if body.global_ is not None:
        try:
            merged_global = _merge_global_config(current_config.global_, body.global_)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_GLOBAL_CONFIG", "message": str(e)},
            ) from e
    else:
        merged_global = current_config.global_

    # 合并任务配置
    merged_tasks = (
        _merge_all_task_configs(current_config.tasks, body.tasks)
        if body.tasks is not None
        else current_config.tasks.copy()
    )

    # 验证并保存配置
    _validate_and_save_config(merged_global, merged_tasks, app_state)

    return UpdateConfigResponse(
        message="配置更新成功",
        code="SUCCESS",
    )
