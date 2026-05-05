"""深度优先扫描后对空目录的收缩策略（与 `FilePipeline` 主循环配合）。"""

from pathlib import Path

from loguru import logger

from j_file_kit.shared.utils.file_utils import (
    delete_directory_if_empty,
    sanitize_surrogate_str,
)


def cleanup_empty_directory_under_scan(
    path: Path,
    scan_root: Path,
    dry_run: bool,
    run_id: int,
    run_name: str,
) -> None:
    """后序遍历到的目录：非 dry_run、且非 `scan_root` 本身时尝试删空目录。

    文件移走或删除后用于收缩空文件夹；具体是否删除由 `delete_directory_if_empty` 决定。
    """
    if dry_run:
        return

    if path.resolve() == scan_root.resolve():
        return

    if delete_directory_if_empty(path):
        logger.bind(
            run_id=str(run_id),
            run_name=run_name,
        ).info(f"清理空目录: {sanitize_surrogate_str(str(path))}")
