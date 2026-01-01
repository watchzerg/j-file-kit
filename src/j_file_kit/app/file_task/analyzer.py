"""文件分析函数

提供文件分析的纯函数，分析单个文件并返回处理决策。
不产生副作用，只分析并返回 Decision。

设计意图：
- 纯函数设计，便于测试和推理
- 子函数以下划线开头，表示内部使用
- 主函数 analyze_file 是模块的唯一公开 API
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from j_file_kit.app.file_task.decisions import (
    DeleteDecision,
    FileDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain import FileType
from j_file_kit.app.file_task.file_util import (
    generate_jav_filename,
    generate_sorted_dir,
)


class AnalyzeConfig(BaseModel):
    """分析配置

    包含分析文件所需的所有配置信息。
    """

    # 文件类型扩展名
    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    archive_extensions: set[str] = Field(..., description="压缩文件扩展名")

    # 目标目录
    sorted_dir: Path | None = Field(None, description="整理后的视频图片存储目录")
    unsorted_dir: Path | None = Field(None, description="无番号视频图片存储目录")
    archive_dir: Path | None = Field(None, description="压缩文件存储目录")
    misc_dir: Path | None = Field(None, description="Misc文件存储目录")

    # 删除规则
    misc_file_delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Misc文件删除规则配置（keywords, extensions, max_size）",
    )


def analyze_file(path: Path, config: AnalyzeConfig) -> FileDecision:
    """分析单个文件并返回处理决策

    设计意图：纯函数，不产生副作用，只分析并返回决策。

    Args:
        path: 文件路径
        config: 分析配置

    Returns:
        文件处理决策（MoveDecision、DeleteDecision 或 SkipDecision）
    """
    # 1. 分类文件类型
    file_type = _classify_file(path, config)

    # 2. 根据文件类型决定处理方式
    if file_type == FileType.MISC:
        return _decide_misc_action(path, file_type, config)
    elif file_type == FileType.ARCHIVE:
        return _decide_archive_action(path, file_type, config)
    else:  # VIDEO or IMAGE
        return _decide_media_action(path, file_type, config)


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
        target_path=config.misc_dir / path.name,
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
        target_path=config.archive_dir / path.name,
        file_type=file_type,
        serial_id=None,
    )


def _decide_media_action(
    path: Path,
    file_type: FileType,
    config: AnalyzeConfig,
) -> FileDecision:
    """决定视频/图片文件的处理方式

    有番号的移动到 sorted 目录，无番号的移动到 unsorted 目录。

    Args:
        path: 文件路径
        file_type: 文件类型
        config: 分析配置

    Returns:
        文件处理决策
    """
    # 1. 从文件名生成新文件名和番号
    new_filename, serial_id = generate_jav_filename(path.name)

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
        # 无番号：移动到待处理目录
        if config.unsorted_dir is None:
            return SkipDecision(
                source_path=path,
                file_type=file_type,
                reason="unsorted_dir 未设置，无法移动无番号文件",
            )

        return MoveDecision(
            source_path=path,
            target_path=config.unsorted_dir / path.name,
            file_type=file_type,
            serial_id=None,
        )
