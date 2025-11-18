"""配置API路由

定义配置管理的HTTP API路由处理函数。
提供配置的查询和更新功能，支持部分更新。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from ..infrastructure.app_state import AppState
from ..infrastructure.filesystem.operations import is_directory, path_exists
from ..models.config import GlobalConfig, TaskConfig, TaskDefinition
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
    if update.inbox_dir is not None:
        update_dict["inbox_dir"] = Path(update.inbox_dir) if update.inbox_dir else None
    if update.sorted_dir is not None:
        update_dict["sorted_dir"] = (
            Path(update.sorted_dir) if update.sorted_dir else None
        )
    if update.unsorted_dir is not None:
        update_dict["unsorted_dir"] = (
            Path(update.unsorted_dir) if update.unsorted_dir else None
        )
    if update.archive_dir is not None:
        update_dict["archive_dir"] = (
            Path(update.archive_dir) if update.archive_dir else None
        )
    if update.misc_dir is not None:
        update_dict["misc_dir"] = Path(update.misc_dir) if update.misc_dir else None
    if update.starred_dir is not None:
        update_dict["starred_dir"] = (
            Path(update.starred_dir) if update.starred_dir else None
        )

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


def _validate_single_dir(
    dir_name: str, dir_path: Path | None, required: bool
) -> list[str]:
    """验证单个目录

    Args:
        dir_name: 目录名称
        dir_path: 目录路径
        required: 是否必须设置

    Returns:
        错误列表
    """
    errors: list[str] = []
    if dir_path is None:
        if required:
            errors.append(f"{dir_name} 未设置")
        return errors

    if not path_exists(dir_path):
        errors.append(f"{dir_name} 不存在: {dir_path}")
    elif not is_directory(dir_path):
        errors.append(f"{dir_name} 不是目录: {dir_path}")
    return errors


def _check_dir_conflicts(config: GlobalConfig) -> list[str]:
    """检查目录路径冲突

    Args:
        config: 全局配置对象

    Returns:
        错误列表
    """
    errors: list[str] = []
    all_dirs = [
        ("inbox_dir", config.inbox_dir),
        ("sorted_dir", config.sorted_dir),
        ("unsorted_dir", config.unsorted_dir),
        ("archive_dir", config.archive_dir),
        ("misc_dir", config.misc_dir),
        ("starred_dir", config.starred_dir),
    ]
    resolved_paths: dict[Path, list[str]] = {}
    for dir_name, dir_path in all_dirs:
        if dir_path is not None:
            resolved = dir_path.resolve()
            if resolved in resolved_paths:
                resolved_paths[resolved].append(dir_name)
            else:
                resolved_paths[resolved] = [dir_name]

    for resolved_path, dir_names in resolved_paths.items():
        if len(dir_names) > 1:
            errors.append(
                f"目录路径冲突: {', '.join(dir_names)} 都指向同一路径 {resolved_path}"
            )
    return errors


def _validate_global_dirs(config: GlobalConfig) -> None:
    """验证全局目录配置

    Args:
        config: 全局配置对象

    Raises:
        HTTPException: 如果路径验证失败
    """
    errors: list[str] = []

    # inbox_dir 必须设置
    errors.extend(
        _validate_single_dir("待处理目录（inbox_dir）", config.inbox_dir, True)
    )

    # 验证其他目录（如果已设置）
    dirs_to_check = {
        "sorted_dir": config.sorted_dir,
        "unsorted_dir": config.unsorted_dir,
        "archive_dir": config.archive_dir,
        "misc_dir": config.misc_dir,
        "starred_dir": config.starred_dir,
    }

    for dir_name, dir_path in dirs_to_check.items():
        errors.extend(_validate_single_dir(dir_name, dir_path, False))

    # 检查路径冲突
    errors.extend(_check_dir_conflicts(config))

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_PATH",
                "message": "目录配置验证失败:\n"
                + "\n".join(f"  - {e}" for e in errors),
            },
        )


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
    # 验证配置模型
    try:
        TaskConfig.model_validate({"global": merged_global, "tasks": merged_tasks})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CONFIG", "message": f"配置验证失败: {str(e)}"},
        ) from e

    # 验证路径（HTTP 更新时验证）
    _validate_global_dirs(merged_global)

    # 更新数据库
    try:
        app_state.config_repository.update_global_config(merged_global)
        for task in merged_tasks:
            app_state.config_repository.update_task(task)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "CONFIG_UPDATE_FAILED",
                "message": f"更新配置失败: {str(e)}",
            },
        ) from e

    # 重新加载配置到内存
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


@router.get("", response_model=TaskConfig)
async def get_config(request: Request) -> TaskConfig:
    """获取当前配置

    Args:
        request: HTTP请求对象

    Returns:
        当前配置对象
    """
    app_state: AppState = request.state.app_state
    config: TaskConfig = app_state.config
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
