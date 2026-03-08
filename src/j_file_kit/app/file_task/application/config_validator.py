"""JAV 视频整理任务配置验证

提供配置验证相关的纯函数，无副作用。
仅验证配置数据本身（格式、必需字段、冲突），不涉及文件系统检查。
从原 global_config_validator 迁移，改为基于 JavVideoOrganizeConfig 入参。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig


def _get_all_dir_fields(
    config: JavVideoOrganizeConfig,
) -> list[tuple[str, Path | None]]:
    """获取所有目录字段

    Args:
        config: 任务配置对象

    Returns:
        目录字段列表，格式为 [(字段名, 路径值), ...]
    """
    return [
        ("inbox_dir", config.inbox_dir),
        ("sorted_dir", config.sorted_dir),
        ("unsorted_dir", config.unsorted_dir),
        ("archive_dir", config.archive_dir),
        ("misc_dir", config.misc_dir),
    ]


def validate_inbox_dir(config: JavVideoOrganizeConfig) -> list[str]:
    """验证 inbox_dir 配置

    仅验证配置项是否设置，不检查目录存在性或文件系统状态。

    Args:
        config: 任务配置对象

    Returns:
        错误列表，如果没有错误则返回空列表
    """
    errors: list[str] = []
    if config.inbox_dir is None:
        errors.append("待处理目录（inbox_dir）未设置")
    return errors


def check_dir_conflicts(config: JavVideoOrganizeConfig) -> list[str]:
    """检查目录路径冲突

    检查所有目录路径是否有冲突：
    - 多个配置指向同一路径
    - 目录之间互为父子目录关系

    使用 resolve(strict=False) 解析路径以处理符号链接，但不检查路径是否存在。

    Args:
        config: 任务配置对象

    Returns:
        错误列表，如果没有冲突则返回空列表
    """
    errors: list[str] = []
    all_dirs = _get_all_dir_fields(config)

    dir_info: list[tuple[str, Path]] = []
    resolved_paths: dict[Path, list[str]] = {}

    for dir_name, dir_path in all_dirs:
        if dir_path is not None:
            resolved = dir_path.resolve(strict=False)
            dir_info.append((dir_name, resolved))
            if resolved in resolved_paths:
                resolved_paths[resolved].append(dir_name)
            else:
                resolved_paths[resolved] = [dir_name]

    for _resolved_path, dir_names in resolved_paths.items():
        if len(dir_names) > 1:
            errors.append(
                f"目录路径冲突: {', '.join(dir_names)} 都指向同一路径 {_resolved_path}",
            )

    for i, (name1, path1) in enumerate(dir_info):
        for name2, path2 in dir_info[i + 1 :]:
            if path1 in path2.parents:
                errors.append(
                    f"目录路径冲突: {name1} ({path1}) 是 {name2} ({path2}) 的父目录",
                )
            elif path2 in path1.parents:
                errors.append(
                    f"目录路径冲突: {name2} ({path2}) 是 {name1} ({path1}) 的父目录",
                )

    return errors


def validate_jav_video_organizer_config(config: JavVideoOrganizeConfig) -> list[str]:
    """统一验证 JAV 视频整理任务配置

    验证配置的有效性，包括：
    - inbox_dir 是否设置（必需字段）
    - 目录路径是否有冲突

    Args:
        config: 任务配置对象

    Returns:
        错误列表，如果没有错误则返回空列表
    """
    errors: list[str] = []
    errors.extend(validate_inbox_dir(config))
    errors.extend(check_dir_conflicts(config))
    return errors
