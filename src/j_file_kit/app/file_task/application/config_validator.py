"""JAV 视频整理任务配置验证

提供配置验证相关的纯函数，无副作用。
validate_jav_video_organizer_config 在 API 更新路径中被调用，执行完整的业务校验，
包括必需字段、路径冲突、/media 根目录约束和目录存在性检查。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.config import (
    MEDIA_ROOT,
    JavVideoOrganizeConfig,
)


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


def check_media_root(config: JavVideoOrganizeConfig) -> list[str]:
    """检查所有非 None 目录路径必须是 MEDIA_ROOT 的子目录。

    使用 resolve(strict=False) 规范化路径后检查祖先关系，不检查路径是否存在。
    仅在 API 更新配置时调用，不在配置加载时调用，确保系统启动时不因路径约束失败。

    Args:
        config: 任务配置对象

    Returns:
        错误列表，如果所有目录均符合约束则返回空列表
    """
    media_root = MEDIA_ROOT.resolve(strict=False)
    errors: list[str] = []
    for field_name, dir_path in _get_all_dir_fields(config):
        if dir_path is not None:
            resolved = dir_path.resolve(strict=False)
            if media_root not in resolved.parents:
                errors.append(
                    f"{field_name}（{dir_path}）必须是 {media_root} 的子目录",
                )
    return errors


def check_dirs_exist(config: JavVideoOrganizeConfig) -> list[str]:
    """检查所有非 None 目录是否存在于文件系统

    仅在 API 更新配置时调用，确保用户指定的目录真实存在。

    Args:
        config: 任务配置对象

    Returns:
        错误列表，如果所有目录均存在则返回空列表
    """
    errors: list[str] = []
    for dir_name, dir_path in _get_all_dir_fields(config):
        if dir_path is not None and not dir_path.exists():
            errors.append(f"目录不存在: {dir_name}（{dir_path}）")
    return errors


def validate_jav_video_organizer_config(config: JavVideoOrganizeConfig) -> list[str]:
    """统一验证 JAV 视频整理任务配置（仅在 API 更新路径调用）

    执行完整的业务校验，包括：
    - inbox_dir 是否设置（必需字段）
    - 目录路径是否有冲突
    - 所有非 None 目录是否在 MEDIA_ROOT 下
    - 所有非 None 目录是否存在于文件系统

    此函数不在配置加载时调用，避免旧配置或非法配置导致系统启动失败。

    Args:
        config: 任务配置对象

    Returns:
        错误列表，如果没有错误则返回空列表
    """
    errors: list[str] = []
    errors.extend(validate_inbox_dir(config))
    errors.extend(check_dir_conflicts(config))
    errors.extend(check_media_root(config))
    errors.extend(check_dirs_exist(config))
    return errors
