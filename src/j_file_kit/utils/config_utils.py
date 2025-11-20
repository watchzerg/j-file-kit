"""配置验证工具函数

提供配置验证相关的纯函数，无副作用。
用于统一配置验证逻辑，消除重复代码。
"""

from pathlib import Path

from ..models.config import GlobalConfig


def validate_inbox_dir(global_config: GlobalConfig) -> list[str]:
    """验证inbox_dir配置

    仅验证配置项是否设置，不检查目录存在性。

    Args:
        global_config: 全局配置对象

    Returns:
        错误列表，如果没有错误则返回空列表
    """
    errors: list[str] = []
    inbox_dir = global_config.inbox_dir
    if inbox_dir is None:
        errors.append("待处理目录（inbox_dir）未设置")
    elif inbox_dir.exists() and not inbox_dir.is_dir():
        # 如果路径已存在但不是目录，这是配置错误
        errors.append(f"待处理目录路径不是目录: {inbox_dir}")
    return errors


def validate_other_dirs(global_config: GlobalConfig) -> list[str]:
    """验证其他目录配置

    仅验证路径格式，如果路径已存在则检查是否为目录类型。
    不检查目录存在性。

    Args:
        global_config: 全局配置对象

    Returns:
        错误列表，如果没有错误则返回空列表
    """
    errors: list[str] = []
    target_dirs = {
        "sorted_dir": global_config.sorted_dir,
        "unsorted_dir": global_config.unsorted_dir,
        "archive_dir": global_config.archive_dir,
        "misc_dir": global_config.misc_dir,
        "starred_dir": global_config.starred_dir,
    }

    for dir_name, dir_path in target_dirs.items():
        if dir_path is not None:
            # 如果路径已存在但不是目录，这是配置错误
            if dir_path.exists() and not dir_path.is_dir():
                errors.append(f"{dir_name} 路径不是目录: {dir_path}")
    return errors


def check_dir_conflicts(global_config: GlobalConfig) -> list[str]:
    """检查目录路径冲突

    检查所有目录路径是否有冲突（多个配置指向同一路径）。

    Args:
        global_config: 全局配置对象

    Returns:
        错误列表，如果没有冲突则返回空列表
    """
    errors: list[str] = []
    all_dirs = [
        ("inbox_dir", global_config.inbox_dir),
        ("sorted_dir", global_config.sorted_dir),
        ("unsorted_dir", global_config.unsorted_dir),
        ("archive_dir", global_config.archive_dir),
        ("misc_dir", global_config.misc_dir),
        ("starred_dir", global_config.starred_dir),
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


def validate_global_config(global_config: GlobalConfig) -> list[str]:
    """统一验证全局配置

    验证全局配置的有效性，包括：
    - inbox_dir 是否设置
    - 所有目录路径格式是否正确
    - 目录路径是否有冲突

    Args:
        global_config: 全局配置对象

    Returns:
        错误列表，如果没有错误则返回空列表
    """
    errors: list[str] = []
    errors.extend(validate_inbox_dir(global_config))
    errors.extend(validate_other_dirs(global_config))
    errors.extend(check_dir_conflicts(global_config))
    return errors
