"""Misc 类型文件：删除规则与归宿（移动到 misc 目录）。

删除条件：扩展名列表命中（优先级最高）或体积不超过 ``max_size``（若配置）。
``misc_file_delete_rules.extensions`` 在生产路径由 ``JavVideoOrganizer`` 与
``organizer_defaults`` 合并后写入 ``JavAnalyzeConfig``。
"""

from pathlib import Path
from typing import Any

from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    FileDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.file_types import FileType
from j_file_kit.shared.utils.file_utils import sanitize_surrogate_str


def check_misc_delete_rules(path: Path, rules: dict[str, Any]) -> str | None:
    """检查 Misc 文件是否符合删除规则。

    Args:
        path: 文件路径
        rules: 删除规则配置（extensions 列表、可选 max_size）

    Returns:
        删除原因；不应删除则返回 None。

    Raises:
        ValueError: ``max_size`` 非数字类型时
    """
    if not rules:
        return None

    suffix = path.suffix.lower()
    extensions = rules.get("extensions")
    if isinstance(extensions, list):
        extensions_normalized = {
            ext if ext.startswith(".") else f".{ext}".lower()
            for ext in (e.lower() for e in extensions)
        }
        if suffix in extensions_normalized:
            return f"扩展名 {suffix} 匹配删除规则"

    max_size = rules.get("max_size")
    if max_size is not None:
        if not isinstance(max_size, (int, float)):
            raise ValueError("max_size 必须为数字类型")
        try:
            file_size = path.stat().st_size
        except OSError:
            return None
        if file_size <= max_size:
            return f"文件大小 {file_size} <= {max_size}（Misc 体积删除规则）"
    return None


def decide_misc_action(
    path: Path,
    file_type: FileType,
    config: JavAnalyzeConfig,
) -> FileDecision:
    """Misc：命中删除规则则删；否则移到 ``misc_dir``；目录未配置则 Skip。

    Args:
        path: 文件路径
        file_type: 已为 ``FileType.MISC``
        config: JAV 分析配置

    Returns:
        ``DeleteDecision``、``MoveDecision`` 或 ``SkipDecision``
    """
    delete_reason = check_misc_delete_rules(path, config.misc_file_delete_rules)
    if delete_reason:
        return DeleteDecision(
            source_path=path,
            file_type=file_type,
            reason=delete_reason,
        )

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
