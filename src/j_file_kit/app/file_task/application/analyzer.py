"""文件分析函数

提供文件分析的纯函数，分析单个文件并返回处理决策。
不产生副作用，只分析并返回 Decision。

设计意图：
- 纯函数设计，便于测试和推理
- 子函数以下划线开头，表示内部使用
- 主函数 analyze_file 是模块的唯一公开 API
- 收件箱预删除（inbox_delete_rules）在扩展名分类之前执行，OR 语义；评估顺序为完全匹配
  stem → 关键字子串 → stat 体积，以减少 I/O。
- `AnalyzeConfig` 的四类扩展名、`misc_file_delete_rules.extensions`、站标去噪列表在生产路径由
  `JavVideoOrganizer` 从 `jav_organizer_defaults` 注入；单测可直接构造 `AnalyzeConfig`。
"""

from pathlib import Path
from typing import Any

from j_file_kit.app.file_task.application.config import AnalyzeConfig, InboxDeleteRules
from j_file_kit.app.file_task.application.jav_filename_util import (
    generate_jav_filename,
    generate_sorted_dir,
)
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    FileDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.models import FileType
from j_file_kit.shared.utils.file_utils import sanitize_surrogate_str


def analyze_file(path: Path, config: AnalyzeConfig) -> FileDecision:
    """分析单个文件并返回处理决策

    设计意图：纯函数，不产生副作用，只分析并返回决策。

    流程：① 收件箱预删除（扩展名分类前）；② 按扩展名分类；③ 按类型决定移动/删除/跳过。

    Args:
        path: 文件路径
        config: 分析配置

    Returns:
        文件处理决策（MoveDecision、DeleteDecision 或 SkipDecision）
    """
    inbox_reason = _check_inbox_delete_rules(path, config.inbox_delete_rules)
    if inbox_reason:
        return DeleteDecision(
            source_path=path,
            file_type=FileType.UNCLASSIFIED,
            reason=inbox_reason,
        )

    file_type = _classify_file(path, config)

    if file_type == FileType.MISC:
        return _decide_misc_action(path, file_type, config)
    elif file_type == FileType.ARCHIVE:
        return _decide_archive_action(path, file_type, config)
    else:  # VIDEO, IMAGE or SUBTITLE
        return _decide_media_action(path, file_type, config)


def _check_inbox_delete_rules(path: Path, rules: InboxDeleteRules) -> str | None:
    """收件箱预删除判定（扩展名分类之前）。

    OR 语义：stem 完全匹配、stem 含任一关键字、或体积不超过 max_size_bytes（若配置）。
    评估顺序：完全匹配 → 关键字 → stat（减少磁盘访问）。

    Args:
        path: 文件路径
        rules: 收件箱删除规则

    Returns:
        删除原因；不应删除则返回 None
    """
    stem = path.stem
    if stem in rules.exact_stems:
        return f"stem 完全匹配收件箱删除规则: {stem!r}"
    for kw in rules.keywords:
        if kw in stem:
            return f"stem 包含收件箱删除关键字: {kw!r}"
    if rules.max_size_bytes is not None:
        try:
            file_size = path.stat().st_size
        except OSError:
            return None
        if file_size <= rules.max_size_bytes:
            return f"文件大小 {file_size} <= {rules.max_size_bytes}（收件箱删除规则）"
    return None


def _classify_file(path: Path, config: AnalyzeConfig) -> FileType:
    """分类文件类型

    根据文件扩展名判断文件类型（视频/图片/压缩/其他）。

    Args:
        path: 文件路径
        config: 分析配置

    Returns:
        文件类型枚举
    """
    suffix = path.suffix.lower()

    if suffix in config.video_extensions:
        return FileType.VIDEO
    if suffix in config.image_extensions:
        return FileType.IMAGE
    if suffix in config.subtitle_extensions:
        return FileType.SUBTITLE
    if suffix in config.archive_extensions:
        return FileType.ARCHIVE
    return FileType.MISC


def _decide_misc_action(
    path: Path,
    file_type: FileType,
    config: AnalyzeConfig,
) -> FileDecision:
    """决定 Misc 文件的处理方式

    Misc 文件可能被删除或移动到 misc 目录。
    删除条件：扩展名匹配 或 (体积 <= max_size 且 文件名包含关键字)

    Args:
        path: 文件路径
        file_type: 文件类型
        config: 分析配置

    Returns:
        文件处理决策
    """
    # 检查是否应该删除
    delete_reason = _check_misc_delete_rules(path, config.misc_file_delete_rules)
    if delete_reason:
        return DeleteDecision(
            source_path=path,
            file_type=file_type,
            reason=delete_reason,
        )

    # 不删除，移动到 misc 目录
    if config.misc_dir is None:
        return SkipDecision(
            source_path=path,
            file_type=file_type,
            reason="misc_dir 未设置，无法移动 Misc 文件",
        )

    return MoveDecision(
        source_path=path,
        target_path=config.misc_dir / sanitize_surrogate_str(path.name),
        file_type=file_type,
        serial_id=None,
    )


def _check_misc_delete_rules(path: Path, rules: dict[str, Any]) -> str | None:
    """检查 Misc 文件是否符合删除规则

    删除条件：扩展名匹配 或 (体积 <= max_size 且 文件名包含关键字)

    Args:
        path: 文件路径
        rules: 删除规则配置

    Returns:
        删除原因，如果不应删除则返回 None
    """
    if not rules:
        return None

    suffix = path.suffix.lower()
    stem = path.stem

    # 检查扩展名（优先级最高）
    extensions = rules.get("extensions")
    if isinstance(extensions, list):
        extensions_normalized = {
            ext if ext.startswith(".") else f".{ext}".lower()
            for ext in (e.lower() for e in extensions)
        }
        if suffix in extensions_normalized:
            return f"扩展名 {suffix} 匹配删除规则"

    # 检查体积和文件名关键字组合
    max_size = rules.get("max_size")
    keywords = rules.get("keywords")
    if keywords is not None and max_size is not None:
        if not isinstance(keywords, list) or not all(
            isinstance(kw, str) for kw in keywords
        ):
            return None
        if not isinstance(max_size, (int, float)):
            raise ValueError("max_size 必须为数字类型")
        try:
            file_size = path.stat().st_size
        except OSError:
            return None
        if file_size <= max_size:
            if any(kw in stem for kw in keywords):
                return f"文件大小 {file_size} <= {max_size} 且文件名包含关键字"
    return None


def _decide_archive_action(
    path: Path,
    file_type: FileType,
    config: AnalyzeConfig,
) -> FileDecision:
    """决定压缩文件的处理方式

    压缩文件移动到 archive 目录。

    Args:
        path: 文件路径
        file_type: 文件类型
        config: 分析配置

    Returns:
        文件处理决策
    """
    if config.archive_dir is None:
        return SkipDecision(
            source_path=path,
            file_type=file_type,
            reason="archive_dir 未设置，无法移动压缩文件",
        )

    return MoveDecision(
        source_path=path,
        target_path=config.archive_dir / sanitize_surrogate_str(path.name),
        file_type=file_type,
        serial_id=None,
    )


def _decide_media_action(
    path: Path,
    file_type: FileType,
    config: AnalyzeConfig,
) -> FileDecision:
    """决定视频/图片/字幕文件的处理方式

    有番号的移动到 sorted 目录。无番号时：图片直接删除；视频与字幕移动到 unsorted 目录。
    视频在配置启用时：体积严格小于阈值则直接删除（不看文件名、不解析番号）。

    Args:
        path: 文件路径
        file_type: 文件类型
        config: 分析配置

    Returns:
        文件处理决策
    """
    if file_type == FileType.VIDEO and config.video_small_delete_bytes is not None:
        try:
            file_size = path.stat().st_size
        except OSError:
            pass
        else:
            if file_size < config.video_small_delete_bytes:
                return DeleteDecision(
                    source_path=path,
                    file_type=file_type,
                    reason=(
                        f"视频大小 {file_size} < {config.video_small_delete_bytes} "
                        "（小体积直接删除）"
                    ),
                )

    # 1. 从文件名生成新文件名和番号；先 sanitize 确保输出文件名为合法 UTF-8
    safe_name = sanitize_surrogate_str(path.name)
    new_filename, serial_id = generate_jav_filename(
        safe_name,
        strip_substrings=config.jav_filename_strip_substrings,
    )

    if serial_id:
        # 有番号：移动到整理目录
        if config.sorted_dir is None:
            return SkipDecision(
                source_path=path,
                file_type=file_type,
                reason="sorted_dir 未设置，无法移动有番号文件",
            )

        # 2. 用番号生成子目录
        sub_dir = generate_sorted_dir(serial_id)

        # 3. 组装最终路径：基础目录 / 子目录 / 新文件名
        target_path = config.sorted_dir / sub_dir / new_filename

        return MoveDecision(
            source_path=path,
            target_path=target_path,
            file_type=file_type,
            serial_id=serial_id,
        )
    else:
        # 无番号
        if file_type == FileType.IMAGE:
            return DeleteDecision(
                source_path=path,
                file_type=file_type,
                reason="图片无番号，直接删除",
            )
        if config.unsorted_dir is None:
            return SkipDecision(
                source_path=path,
                file_type=file_type,
                reason="unsorted_dir 未设置，无法移动无番号文件",
            )

        return MoveDecision(
            source_path=path,
            target_path=config.unsorted_dir / safe_name,
            file_type=file_type,
            serial_id=None,
        )
