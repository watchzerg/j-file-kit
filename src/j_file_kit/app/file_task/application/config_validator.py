"""文件任务配置验证（JAV / Raw）。

提供配置验证相关的纯函数，无副作用。`*_organizer_config` 在 API 更新路径中被调用，
执行完整的业务校验，包括必需字段、路径冲突和目录存在性检查。

注：`JavVideoOrganizeConfig` 与 `RawFileOrganizeConfig` 的媒体根目录约束已作为模型不变量在
各自 `model_validator` 中强制执行，构造时自动触发，无需在此重复校验。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.config import (
    RAW_FILE_ORGANIZE_PATH_FIELD_NAMES,
    JavVideoOrganizeConfig,
    RawFileOrganizeConfig,
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
    - 所有非 None 目录是否存在于文件系统

    注：/media/jav_workspace 约束已由 JavVideoOrganizeConfig.model_validator 在构造时自动校验。

    Args:
        config: 任务配置对象

    Returns:
        错误列表，如果没有错误则返回空列表
    """
    errors: list[str] = []
    errors.extend(validate_inbox_dir(config))
    errors.extend(check_dir_conflicts(config))
    errors.extend(check_dirs_exist(config))
    return errors


def _get_all_dir_fields_raw(
    config: RawFileOrganizeConfig,
) -> list[tuple[str, Path | None]]:
    """Raw 任务所有 Path 配置字段（含 inbox）。"""
    return [
        (field_name, getattr(config, field_name))
        for field_name in RAW_FILE_ORGANIZE_PATH_FIELD_NAMES
    ]


def validate_raw_inbox_dir(config: RawFileOrganizeConfig) -> list[str]:
    """验证 raw 的 inbox_dir 是否已配置。"""
    errors: list[str] = []
    if config.inbox_dir is None:
        errors.append("待处理目录（inbox_dir）未设置")
    return errors


def check_raw_dir_conflicts(config: RawFileOrganizeConfig) -> list[str]:
    """检查 Raw 任务目录路径冲突（同路径或父子包含）。"""
    errors: list[str] = []
    all_dirs = _get_all_dir_fields_raw(config)

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


def check_raw_dirs_exist(config: RawFileOrganizeConfig) -> list[str]:
    """检查 Raw 任务所有非 None 目录是否存在于文件系统。"""
    errors: list[str] = []
    for dir_name, dir_path in _get_all_dir_fields_raw(config):
        if dir_path is not None and not dir_path.exists():
            errors.append(f"目录不存在: {dir_name}（{dir_path}）")
    return errors


def validate_raw_file_organizer_config(config: RawFileOrganizeConfig) -> list[str]:
    """统一验证 raw_file_organizer 任务配置（仅在 API 更新路径调用）。"""
    errors: list[str] = []
    errors.extend(validate_raw_inbox_dir(config))
    errors.extend(check_raw_dir_conflicts(config))
    errors.extend(check_raw_dirs_exist(config))
    return errors
