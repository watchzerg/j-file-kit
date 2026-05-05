"""视频 / 图片 / 字幕：小体积视频删除、番号解析与 sorted / unsorted / 删除分支。

番号与文件名重构见 ``jav_filename_util``；站标去噪子串由 ``JavAnalyzeConfig`` 提供。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
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
from j_file_kit.app.file_task.domain.file_types import FileType
from j_file_kit.shared.utils.file_utils import sanitize_surrogate_str


def decide_media_action(
    path: Path,
    file_type: FileType,
    config: JavAnalyzeConfig,
) -> FileDecision:
    """视频/图片/字幕：可选按体积删小视频；有番号进 sorted；无番号时图删、视频字幕进 unsorted。

    ``VIDEO`` 且配置 ``video_small_delete_bytes``：体积严格小于阈值则 ``DeleteDecision``（不解析番号）。
    ``stat`` 失败时跳过该规则，继续走番号逻辑。

    Args:
        path: 文件路径
        file_type: ``VIDEO`` / ``IMAGE`` / ``SUBTITLE``
        config: JAV 分析配置

    Returns:
        ``MoveDecision``、``DeleteDecision`` 或 ``SkipDecision``
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

    safe_name = sanitize_surrogate_str(path.name)
    new_filename, serial_id = generate_jav_filename(
        safe_name,
        strip_substrings=config.jav_filename_strip_substrings,
    )

    if serial_id:
        if config.sorted_dir is None:
            return SkipDecision(
                source_path=path,
                file_type=file_type,
                reason="sorted_dir 未设置，无法移动有番号文件",
            )

        sub_dir = generate_sorted_dir(serial_id)
        target_path = config.sorted_dir / sub_dir / new_filename

        return MoveDecision(
            source_path=path,
            target_path=target_path,
            file_type=file_type,
            serial_id=serial_id,
        )

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
