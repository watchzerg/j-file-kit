"""JAV 单文件分析编排入口：``analyze_jav_file``。

纯函数，不产生副作用（规则内可能 ``stat``）。流程：
① 收件箱预删除；② 扩展名分类；③ 按类型委托 ``misc`` / ``archive`` / ``media``。

``JavAnalyzeConfig`` 由 ``JavVideoOrganizer._create_analyze_config`` 组装；
单测可直接构造 ``JavAnalyzeConfig``。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.jav_analysis.archive import (
    decide_archive_action,
)
from j_file_kit.app.file_task.application.jav_analysis.classify import classify_jav_file
from j_file_kit.app.file_task.application.jav_analysis.inbox import (
    check_inbox_delete_rules,
)
from j_file_kit.app.file_task.application.jav_analysis.media import decide_media_action
from j_file_kit.app.file_task.application.jav_analysis.misc import decide_misc_action
from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.domain.decisions import DeleteDecision, FileDecision
from j_file_kit.app.file_task.domain.file_types import FileType


def analyze_jav_file(path: Path, config: JavAnalyzeConfig) -> FileDecision:
    """分析单个 JAV 收件箱文件并返回处理决策。

    流程：① 收件箱预删除（扩展名分类前）；② 按扩展名分类；③ 按类型决定移动/删除/跳过。

    Args:
        path: 文件路径
        config: JAV 分析配置

    Returns:
        文件处理决策（``MoveDecision``、``DeleteDecision`` 或 ``SkipDecision``）
    """
    inbox_reason = check_inbox_delete_rules(path, config.inbox_delete_rules)
    if inbox_reason:
        return DeleteDecision(
            source_path=path,
            file_type=FileType.UNCLASSIFIED,
            reason=inbox_reason,
        )

    file_type = classify_jav_file(path, config)

    if file_type == FileType.MISC:
        return decide_misc_action(path, file_type, config)
    if file_type == FileType.ARCHIVE:
        return decide_archive_action(path, file_type, config)
    return decide_media_action(path, file_type, config)
