"""配置验证工具函数

提供配置验证相关的纯函数，无副作用。
仅验证配置数据本身（格式、必需字段、冲突），不涉及文件系统检查。
文件系统层面的验证（存在性、类型、权限）由 TaskResourceInitializer 负责。
"""

from pathlib import Path

from j_file_kit.app.config.domain.models import GlobalConfig


def _get_all_dir_fields(global_config: GlobalConfig) -> list[tuple[str, Path | None]]:
    """获取所有目录字段

    返回 GlobalConfig 中所有目录字段的列表，用于统一处理。

    Args:
        global_config: 全局配置对象

    Returns:
        目录字段列表，格式为 [(字段名, 路径值), ...]
    """
    return [
        ("inbox_dir", global_config.inbox_dir),
        ("sorted_dir", global_config.sorted_dir),
        ("unsorted_dir", global_config.unsorted_dir),
        ("archive_dir", global_config.archive_dir),
        ("misc_dir", global_config.misc_dir),
        ("starred_dir", global_config.starred_dir),
    ]


def validate_inbox_dir(global_config: GlobalConfig) -> list[str]:
    """验证inbox_dir配置

    仅验证配置项是否设置，不检查目录存在性或文件系统状态。

    Args:
        global_config: 全局配置对象

    Returns:
        错误列表，如果没有错误则返回空列表
    """
    errors: list[str] = []
    if global_config.inbox_dir is None:
        errors.append("待处理目录（inbox_dir）未设置")
    return errors


def check_dir_conflicts(global_config: GlobalConfig) -> list[str]:
    """检查目录路径冲突

    检查所有目录路径是否有冲突：
    - 多个配置指向同一路径
    - 目录之间互为父子目录关系

    使用 resolve(strict=False) 解析路径以处理符号链接，但不检查路径是否存在。

    Args:
        global_config: 全局配置对象

    Returns:
        错误列表，如果没有冲突则返回空列表
    """
    errors: list[str] = []
    all_dirs = _get_all_dir_fields(global_config)

    # 收集所有非 None 的目录及其解析后的路径
    dir_info: list[tuple[str, Path]] = []
    resolved_paths: dict[Path, list[str]] = {}

    for dir_name, dir_path in all_dirs:
        if dir_path is not None:
            # 使用 resolve(strict=False) 解析路径（处理符号链接），但不检查路径是否存在
            # strict=False 确保路径不存在时不会抛出异常
            resolved = dir_path.resolve(strict=False)
            dir_info.append((dir_name, resolved))
            if resolved in resolved_paths:
                resolved_paths[resolved].append(dir_name)
            else:
                resolved_paths[resolved] = [dir_name]

    # 检查是否有多个目录指向同一路径
    for resolved_path, dir_names in resolved_paths.items():
        if len(dir_names) > 1:
            errors.append(
                f"目录路径冲突: {', '.join(dir_names)} 都指向同一路径 {resolved_path}",
            )

    # 检查是否有目录之间存在父子关系
    for i, (name1, path1) in enumerate(dir_info):
        for name2, path2 in dir_info[i + 1 :]:
            # 检查 path1 是否是 path2 的父目录
            if path1 in path2.parents:
                errors.append(
                    f"目录路径冲突: {name1} ({path1}) 是 {name2} ({path2}) 的父目录",
                )
            # 检查 path2 是否是 path1 的父目录
            elif path2 in path1.parents:
                errors.append(
                    f"目录路径冲突: {name2} ({path2}) 是 {name1} ({path1}) 的父目录",
                )

    return errors


def validate_global_config(global_config: GlobalConfig) -> list[str]:
    """统一验证全局配置

    验证全局配置的有效性，包括：
    - inbox_dir 是否设置（必需字段）
    - 目录路径是否有冲突

    注意：不检查目录存在性、类型或权限，这些由 TaskResourceInitializer 负责。

    Args:
        global_config: 全局配置对象

    Returns:
        错误列表，如果没有错误则返回空列表
    """
    errors: list[str] = []
    errors.extend(validate_inbox_dir(global_config))
    errors.extend(check_dir_conflicts(global_config))
    return errors
