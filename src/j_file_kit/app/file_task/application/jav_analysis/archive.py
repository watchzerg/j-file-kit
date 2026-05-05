"""压缩包文件：移动到 ``archive_dir`` 或 Skip（目录未配置）。"""

from pathlib import Path

from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.domain.decisions import (
    FileDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.file_types import FileType
from j_file_kit.shared.utils.file_utils import sanitize_surrogate_str


def decide_archive_action(
    path: Path,
    file_type: FileType,
    config: JavAnalyzeConfig,
) -> FileDecision:
    """压缩文件移动到 ``archive_dir``（文件名经 surrogate 安全化）。

    Args:
        path: 文件路径
        file_type: 已为 ``FileType.ARCHIVE``
        config: JAV 分析配置

    Returns:
        ``MoveDecision`` 或 ``SkipDecision``（``archive_dir`` 未设置）
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
